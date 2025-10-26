#!/usr/bin/env python3

'''
Utility to display statistics and information about a workflow in YAML format.

Usage:
    python workflow-stats.py <workflow.yml>
'''

import sys
import yaml
import argparse
from collections import Counter


def analyze_workflow(workflow_file):
    """Analyze and display workflow statistics"""

    with open(workflow_file, 'r') as f:
        workflow = yaml.safe_load(f)

    name = workflow.get('name', 'Unknown')
    files = workflow.get('files', {})
    tasks = workflow.get('tasks', [])
    inputs = workflow.get('inputs', [])
    outputs = workflow.get('outputs', [])

    print(f"Workflow: {name}")
    print(f"=" * 60)
    print()

    # File statistics
    input_files = [f for f, info in files.items() if info.get('is_input', False)]
    output_files = [f for f, info in files.items() if info.get('is_output', False)]
    intermediate_files = [f for f in files.keys() if f not in input_files and f not in output_files]

    print(f"Files:")
    print(f"  Total: {len(files)}")
    print(f"  Inputs: {len(input_files)}")
    print(f"  Outputs: {len(output_files)}")
    print(f"  Intermediate: {len(intermediate_files)}")
    print()

    # Task statistics
    print(f"Tasks:")
    print(f"  Total: {len(tasks)}")

    # Count tasks by executable
    executables = Counter(task.get('executable', 'unknown') for task in tasks)
    print(f"  By executable:")
    for exe, count in sorted(executables.items()):
        print(f"    {exe}: {count}")
    print()

    # Workflow inputs
    print(f"Workflow Inputs ({len(inputs)}):")
    for inp in inputs[:10]:  # Show first 10
        file_info = files.get(inp, {})
        source = file_info.get('source', 'N/A')
        print(f"  - {inp}")
        if source and source != 'N/A':
            print(f"    Source: {source}")
    if len(inputs) > 10:
        print(f"  ... and {len(inputs) - 10} more")
    print()

    # Workflow outputs
    print(f"Workflow Outputs ({len(outputs)}):")
    for out in outputs:
        print(f"  - {out}")
    print()

    # Task dependencies analysis
    print("Task Dependencies:")
    for i, task in enumerate(tasks[:5]):  # Show first 5 tasks
        task_id = task.get('id', f'task_{i}')
        name = task.get('name', 'unknown')
        task_inputs = task.get('inputs', [])
        task_outputs = task.get('outputs', [])
        print(f"  {task_id} ({name}):")
        print(f"    Inputs: {len(task_inputs)}")
        print(f"    Outputs: {len(task_outputs)}")
    if len(tasks) > 5:
        print(f"  ... and {len(tasks) - 5} more tasks")
    print()

    # File dependencies
    print("File Usage:")
    file_usage = {}
    for task in tasks:
        for inp in task.get('inputs', []):
            file_usage[inp] = file_usage.get(inp, 0) + 1

    most_used = sorted(file_usage.items(), key=lambda x: x[1], reverse=True)[:5]
    print("  Most used files:")
    for fname, count in most_used:
        print(f"    {fname}: used by {count} tasks")
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Display statistics about a YAML workflow'
    )
    parser.add_argument('workflow', help='YAML workflow file')
    args = parser.parse_args()

    analyze_workflow(args.workflow)


if __name__ == '__main__':
    main()
