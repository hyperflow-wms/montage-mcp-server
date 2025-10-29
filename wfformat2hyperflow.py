#!/usr/bin/env python3

'''
Compiler to convert WfFormat JSON workflow to HyperFlow JSON format.

This compiler reads a workflow in WfCommons WfFormat (schema v1.5) and generates
a HyperFlow-compatible JSON workflow description.

Usage:
    python wfformat2hyperflow.py <input.json> <output.json>
'''

import sys
import json
import argparse


class WfFormatToHyperFlowCompiler:
    """Compiles WfFormat JSON workflow to HyperFlow JSON format"""

    def __init__(self, wfformat_dict):
        self.wfformat = wfformat_dict
        self.name = wfformat_dict.get('name', 'workflow')
        
        # Extract specification section
        spec = wfformat_dict.get('workflow', {}).get('specification', {})
        self.spec_files = {f['id']: f for f in spec.get('files', [])}
        self.spec_tasks = spec.get('tasks', [])

        # Mapping from file IDs to signal IDs
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
        """Build mapping from file IDs to signal IDs"""
        signal_id = 0

        # Create signals for all files
        for file_id, file_info in self.spec_files.items():
            self.file_to_signal[file_id] = signal_id

            signal = {'name': file_id}

            # Files with no producers are inputs (have no parents producing them)
            is_input = True
            for task in self.spec_tasks:
                if file_id in task.get('outputFiles', []):
                    is_input = False
                    break
            
            if is_input and file_id in [f for t in self.spec_tasks for f in t.get('inputFiles', [])]:
                signal['data'] = [{}]
                self.input_signals.append(signal_id)

            self.signals.append(signal)
            signal_id += 1

    def _build_processes(self):
        """Build HyperFlow processes from WfFormat tasks"""
        # Determine workflow outputs (files that are not consumed by any task)
        all_inputs = set()
        all_outputs = set()
        
        for task in self.spec_tasks:
            all_inputs.update(task.get('inputFiles', []))
            all_outputs.update(task.get('outputFiles', []))
        
        # Workflow outputs are files that are produced but never consumed
        workflow_outputs = all_outputs - all_inputs
        
        for task in self.spec_tasks:
            process = self._task_to_process(task)
            self.processes.append(process)

            # Check if this task produces final outputs
            for output in task.get('outputFiles', []):
                if output in workflow_outputs:
                    signal_id = self.file_to_signal.get(output)
                    if signal_id is not None and signal_id not in self.output_signals:
                        self.output_signals.append(signal_id)

    def _task_to_process(self, task):
        """Convert a WfFormat task to a HyperFlow process"""
        executable = task.get('name', 'unknown').split('_')[0]  # Extract base name
        
        # Convert inputs to signal IDs
        input_signals = []
        for input_file in task.get('inputFiles', []):
            signal_id = self.file_to_signal.get(input_file)
            if signal_id is not None:
                input_signals.append(signal_id)

        # Convert outputs to signal IDs
        output_signals = []
        for output_file in task.get('outputFiles', []):
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
                    'args': []  # WfFormat doesn't store args in same way
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


def compile_wfformat_to_hyperflow(wfformat_file, output_file):
    """
    Compile a WfFormat JSON workflow to HyperFlow JSON format

    Args:
        wfformat_file: Path to input WfFormat JSON file
        output_file: Path to output HyperFlow JSON file
    """
    # Load WfFormat workflow
    with open(wfformat_file, 'r') as f:
        wfformat_dict = json.load(f)

    # Compile to HyperFlow
    compiler = WfFormatToHyperFlowCompiler(wfformat_dict)
    hyperflow_dict = compiler.compile()

    # Write output JSON
    with open(output_file, 'w') as f:
        json.dump(hyperflow_dict, f, indent=4)

    spec = wfformat_dict.get('workflow', {}).get('specification', {})
    print(f"Compiled {wfformat_file} to {output_file}")
    print(f"  WfFormat tasks: {len(spec.get('tasks', []))}")
    print(f"  WfFormat files: {len(spec.get('files', []))}")
    print(f"  HyperFlow processes: {len(hyperflow_dict['processes'])}")
    print(f"  HyperFlow signals: {len(hyperflow_dict['signals'])}")


def main():
    parser = argparse.ArgumentParser(
        description='Compile WfFormat JSON to HyperFlow JSON'
    )
    parser.add_argument('input', help='Input WfFormat JSON file')
    parser.add_argument('output', help='Output HyperFlow JSON file')
    args = parser.parse_args()

    compile_wfformat_to_hyperflow(args.input, args.output)


if __name__ == '__main__':
    main()
