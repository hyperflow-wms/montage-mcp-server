#!/usr/bin/env python3

'''
Compiler to convert abstract YAML workflow representation to HyperFlow JSON format.

This compiler reads a workflow in the abstract YAML format and generates
a HyperFlow-compatible JSON workflow description.

Usage:
    python yaml2hyperflow.py <input.yml> <output.json>
'''

import sys
import yaml
import json
import argparse


class HyperFlowCompiler:
    """Compiles abstract YAML workflow to HyperFlow JSON format"""

    def __init__(self, workflow_dict):
        self.workflow = workflow_dict
        self.name = workflow_dict.get('name', 'workflow')
        self.files = workflow_dict.get('files', {})
        self.tasks = workflow_dict.get('tasks', [])

        # Mapping from file names to signal IDs
        self.file_to_signal = {}
        self.signals = []

        # HyperFlow processes
        self.processes = []

        # Input and output signal IDs
        self.input_signals = []
        self.output_signals = []

    def compile(self):
        """Compile the workflow to HyperFlow format"""
        self._build_signal_map()
        self._build_processes()
        return self._generate_hyperflow_dict()

    def _build_signal_map(self):
        """Build mapping from filenames to signal IDs"""
        signal_id = 0

        # Create signals for all files
        for fname, finfo in self.files.items():
            self.file_to_signal[fname] = signal_id

            signal = {'name': fname}

            # Input files have initial data
            if finfo.get('is_input', False):
                signal['data'] = [{}]
                self.input_signals.append(signal_id)

            self.signals.append(signal)
            signal_id += 1

    def _build_processes(self):
        """Build HyperFlow processes from tasks"""
        for task in self.tasks:
            process = self._task_to_process(task)
            self.processes.append(process)

            # Check if this task produces final outputs
            for output in task.get('outputs', []):
                file_info = self.files.get(output, {})
                if file_info.get('is_output', False):
                    signal_id = self.file_to_signal.get(output)
                    if signal_id is not None and signal_id not in self.output_signals:
                        self.output_signals.append(signal_id)

    def _task_to_process(self, task):
        """Convert a task to a HyperFlow process"""
        executable = task.get('executable', task.get('name', 'unknown'))
        args = task.get('arguments', [])

        # Convert inputs to signal IDs
        input_signals = []
        for input_file in task.get('inputs', []):
            signal_id = self.file_to_signal.get(input_file)
            if signal_id is not None:
                input_signals.append(signal_id)

        # Convert outputs to signal IDs
        output_signals = []
        for output_file in task.get('outputs', []):
            signal_id = self.file_to_signal.get(output_file)
            if signal_id is not None:
                output_signals.append(signal_id)

        # Build the process
        process = {
            'name': executable,
            'type': 'dataflow',
            'function': '{{function}}',
            'firingLimit': 1,
            'config': {
                'executor': {
                    'executable': executable,
                    'args': args
                }
            },
            'ins': input_signals,
            'outs': output_signals
        }

        return process

    def _generate_hyperflow_dict(self):
        """Generate the final HyperFlow dictionary"""
        return {
            'name': self.name,
            'processes': self.processes,
            'signals': self.signals,
            'ins': self.input_signals,
            'outs': self.output_signals
        }


def compile_yaml_to_hyperflow(yaml_file, output_file):
    """
    Compile a YAML workflow to HyperFlow JSON format

    Args:
        yaml_file: Path to input YAML file
        output_file: Path to output JSON file
    """
    # Load YAML workflow
    with open(yaml_file, 'r') as f:
        workflow_dict = yaml.safe_load(f)

    # Compile to HyperFlow
    compiler = HyperFlowCompiler(workflow_dict)
    hyperflow_dict = compiler.compile()

    # Write output JSON
    with open(output_file, 'w') as f:
        json.dump(hyperflow_dict, f, indent=4)

    print(f"Compiled {yaml_file} to {output_file}")
    print(f"  Tasks: {len(workflow_dict.get('tasks', []))}")
    print(f"  Files: {len(workflow_dict.get('files', {}))}")
    print(f"  Processes: {len(hyperflow_dict['processes'])}")
    print(f"  Signals: {len(hyperflow_dict['signals'])}")


def main():
    parser = argparse.ArgumentParser(
        description='Compile abstract YAML workflow to HyperFlow JSON format'
    )
    parser.add_argument('input', help='Input YAML workflow file')
    parser.add_argument('output', help='Output HyperFlow JSON file')
    args = parser.parse_args()

    compile_yaml_to_hyperflow(args.input, args.output)


if __name__ == '__main__':
    main()
