#!/usr/bin/env python3

'''
Validate a YAML workflow for correctness.

Checks:
- YAML syntax
- Required fields
- File references
- Task input/output consistency

Usage:
    python validate-workflow.py <workflow.yml>
'''

import sys
import yaml
import argparse


class WorkflowValidator:
    """Validates abstract YAML workflows"""

    def __init__(self, workflow_file):
        self.workflow_file = workflow_file
        self.errors = []
        self.warnings = []
        self.workflow = None

    def validate(self):
        """Run all validation checks"""
        if not self._load_yaml():
            return False

        self._check_structure()
        self._check_files()
        self._check_tasks()
        self._check_references()

        return len(self.errors) == 0

    def _load_yaml(self):
        """Load and parse YAML file"""
        try:
            with open(self.workflow_file, 'r') as f:
                self.workflow = yaml.safe_load(f)
            return True
        except yaml.YAMLError as e:
            self.errors.append(f"YAML syntax error: {e}")
            return False
        except FileNotFoundError:
            self.errors.append(f"File not found: {self.workflow_file}")
            return False

    def _check_structure(self):
        """Check top-level structure"""
        required_fields = ['name', 'files', 'tasks']
        for field in required_fields:
            if field not in self.workflow:
                self.errors.append(f"Missing required field: {field}")

        if 'name' in self.workflow and not self.workflow['name']:
            self.errors.append("Workflow name is empty")

    def _check_files(self):
        """Check file definitions"""
        files = self.workflow.get('files', {})

        if not files:
            self.warnings.append("No files defined in workflow")
            return

        for fname, finfo in files.items():
            if not isinstance(finfo, dict):
                self.errors.append(f"File '{fname}': should be a dictionary")
                continue

            # Check required fields
            if 'name' not in finfo:
                self.errors.append(f"File '{fname}': missing 'name' field")

            # Check name consistency
            if finfo.get('name') != fname:
                self.warnings.append(
                    f"File '{fname}': name field '{finfo.get('name')}' doesn't match key"
                )

            # Check input files have sources
            if finfo.get('is_input', False) and not finfo.get('source'):
                self.warnings.append(
                    f"File '{fname}': marked as input but has no source URL"
                )

    def _check_tasks(self):
        """Check task definitions"""
        tasks = self.workflow.get('tasks', [])

        if not tasks:
            self.errors.append("No tasks defined in workflow")
            return

        task_ids = set()
        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                self.errors.append(f"Task {i}: should be a dictionary")
                continue

            # Check required fields
            required = ['name', 'executable', 'inputs', 'outputs']
            for field in required:
                if field not in task:
                    self.errors.append(f"Task {i} ({task.get('name', 'unknown')}): missing '{field}' field")

            # Check task ID uniqueness
            task_id = task.get('id')
            if task_id:
                if task_id in task_ids:
                    self.errors.append(f"Duplicate task ID: {task_id}")
                task_ids.add(task_id)

            # Check inputs/outputs are lists
            if 'inputs' in task and not isinstance(task['inputs'], list):
                self.errors.append(f"Task {i}: 'inputs' should be a list")

            if 'outputs' in task and not isinstance(task['outputs'], list):
                self.errors.append(f"Task {i}: 'outputs' should be a list")

            # Check for tasks with no outputs
            if not task.get('outputs'):
                self.warnings.append(
                    f"Task {i} ({task.get('name', 'unknown')}): has no outputs"
                )

    def _check_references(self):
        """Check that all file references are valid"""
        files = self.workflow.get('files', {})
        tasks = self.workflow.get('tasks', [])

        for i, task in enumerate(tasks):
            task_name = task.get('name', f'task_{i}')

            # Check input file references
            for inp in task.get('inputs', []):
                if inp not in files:
                    self.errors.append(
                        f"Task {i} ({task_name}): references undefined input file '{inp}'"
                    )

            # Check output file references
            for out in task.get('outputs', []):
                if out not in files:
                    self.errors.append(
                        f"Task {i} ({task_name}): references undefined output file '{out}'"
                    )

        # Check for unused files
        used_files = set()
        for task in tasks:
            used_files.update(task.get('inputs', []))
            used_files.update(task.get('outputs', []))

        for fname in files:
            if fname not in used_files:
                self.warnings.append(f"File '{fname}' is defined but never used")

    def print_results(self):
        """Print validation results"""
        if self.errors:
            print(f"❌ VALIDATION FAILED")
            print(f"\nErrors ({len(self.errors)}):")
            for error in self.errors:
                print(f"  • {error}")

        if self.warnings:
            print(f"\n⚠️  Warnings ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  • {warning}")

        if not self.errors and not self.warnings:
            print("✅ VALIDATION PASSED")
            print("No errors or warnings found.")
        elif not self.errors:
            print(f"\n✅ VALIDATION PASSED")
            print(f"No errors found (but {len(self.warnings)} warnings).")


def main():
    parser = argparse.ArgumentParser(
        description='Validate a YAML workflow'
    )
    parser.add_argument('workflow', help='YAML workflow file to validate')
    parser.add_argument('--strict', action='store_true',
                        help='Treat warnings as errors')
    args = parser.parse_args()

    validator = WorkflowValidator(args.workflow)
    is_valid = validator.validate()

    validator.print_results()

    # Exit with error code if validation failed
    if not is_valid:
        sys.exit(1)
    elif args.strict and validator.warnings:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()
