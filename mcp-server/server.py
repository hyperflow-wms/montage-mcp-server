#!/usr/bin/env python3
"""
MCP Server for Montage Workflow Generation

This server provides tools for generating astronomical image processing workflows
using the Montage toolkit. It exposes workflow generation, validation, compilation,
and analysis capabilities through the Model Context Protocol.

Requires:
    - mcp (pip install mcp)
    - pyyaml
    - astropy
"""

import json
import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any, List

# Add parent directory to path to import our modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.stdio

# Import our workflow generator components
try:
    import yaml
    from astropy.io import ascii
except ImportError as e:
    print(f"Warning: Missing dependency: {e}", file=sys.stderr)

# Initialize MCP server
app = Server("montage-workflow-generator")


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools for Montage workflow generation."""
    return [
        Tool(
            name="generate_montage_workflow",
            description="""Generate a Montage astronomical image processing workflow.

            This tool creates workflows for mosaicking astronomical images from various sky surveys.
            The workflow performs image reprojection, background matching, and mosaic generation.

            Parameters:
            - center: Sky coordinates (RA Dec in degrees or object name like 'M17')
            - degrees: Size of output mosaic in degrees (e.g., 0.2, 0.5, 1.0)
            - bands: List of band definitions in format 'survey:band:color'
              Examples: '2mass:j:red', 'dss:DSS2B:blue'
            - output_format: Optional output format: 'yaml' (default) or 'hyperflow' (JSON)

            Returns: Workflow in YAML or HyperFlow JSON format
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "center": {
                        "type": "string",
                        "description": "Center coordinates (e.g., '56.5 23.75' or 'M17')"
                    },
                    "degrees": {
                        "type": "number",
                        "description": "Size of mosaic in degrees (0.1 to 2.0 recommended)"
                    },
                    "bands": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Band definitions (e.g., ['2mass:j:red', '2mass:h:green', '2mass:k:blue'])"
                    },
                    "workflow_name": {
                        "type": "string",
                        "description": "Optional workflow name (default: 'montage')"
                    },
                    "output_format": {
                        "type": "string",
                        "enum": ["yaml", "hyperflow"],
                        "description": "Output format: 'yaml' (default) or 'hyperflow' (JSON)"
                    }
                },
                "required": ["center", "degrees", "bands"]
            }
        ),
        Tool(
            name="compile_to_hyperflow",
            description="""Compile an abstract YAML workflow to HyperFlow JSON format.

            Takes a workflow in abstract YAML format and converts it to HyperFlow's
            signal-based dataflow representation for execution.

            Parameters:
            - yaml_workflow: The YAML workflow content as a string

            Returns: HyperFlow JSON workflow as a string
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_workflow": {
                        "type": "string",
                        "description": "YAML workflow content"
                    }
                },
                "required": ["yaml_workflow"]
            }
        ),
        Tool(
            name="validate_workflow",
            description="""Validate a YAML workflow for correctness.

            Checks workflow syntax, structure, required fields, and file references.
            Returns validation results with any errors or warnings.

            Parameters:
            - yaml_workflow: The YAML workflow content as a string

            Returns: Validation results with status, errors, and warnings
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_workflow": {
                        "type": "string",
                        "description": "YAML workflow content"
                    }
                },
                "required": ["yaml_workflow"]
            }
        ),
        Tool(
            name="analyze_workflow",
            description="""Analyze a YAML workflow and return statistics.

            Provides detailed statistics about the workflow including:
            - File counts (total, inputs, outputs, intermediate)
            - Task counts by executable type
            - Workflow inputs and outputs
            - Task dependencies
            - Most-used files

            Parameters:
            - yaml_workflow: The YAML workflow content as a string

            Returns: Workflow statistics as structured data
            """,
            inputSchema={
                "type": "object",
                "properties": {
                    "yaml_workflow": {
                        "type": "string",
                        "description": "YAML workflow content"
                    }
                },
                "required": ["yaml_workflow"]
            }
        ),
        Tool(
            name="list_supported_surveys",
            description="""List supported astronomical surveys and their available bands.

            Returns information about which surveys can be used in workflow generation.

            Returns: List of surveys with their available bands
            """,
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> list[TextContent]:
    """Handle tool calls."""

    try:
        if name == "generate_montage_workflow":
            return await generate_montage_workflow(arguments)
        elif name == "compile_to_hyperflow":
            return await compile_to_hyperflow(arguments)
        elif name == "validate_workflow":
            return await validate_workflow(arguments)
        elif name == "analyze_workflow":
            return await analyze_workflow(arguments)
        elif name == "list_supported_surveys":
            return await list_supported_surveys(arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


def _generate_workflow_summary(workflow_dict: dict, format_name: str) -> str:
    """Generate a summary for large workflows."""
    from collections import Counter

    name = workflow_dict.get('name', 'Unknown')
    files = workflow_dict.get('files', {})
    tasks = workflow_dict.get('tasks', [])
    inputs = workflow_dict.get('inputs', [])
    outputs = workflow_dict.get('outputs', [])

    # Count tasks by executable
    executables = Counter(task.get('executable', 'unknown') for task in tasks)

    summary = f"Successfully generated Montage workflow ({format_name})\n"
    summary += "=" * 70 + "\n\n"
    summary += f"Workflow: {name}\n\n"
    summary += f"Statistics:\n"
    summary += f"  Files: {len(files):,}\n"
    summary += f"  Tasks: {len(tasks):,}\n"
    summary += f"  Inputs: {len(inputs)}\n"
    summary += f"  Outputs: {len(outputs)}\n\n"
    summary += f"Tasks by executable:\n"
    for exe, count in sorted(executables.items(), key=lambda x: -x[1])[:10]:
        summary += f"  {exe:20s}: {count:4,}\n"
    if len(executables) > 10:
        summary += f"  ... and {len(executables) - 10} more\n"

    return summary


async def generate_montage_workflow(args: Dict[str, Any]) -> list[TextContent]:
    """Generate a Montage workflow in YAML or HyperFlow format."""

    center = args["center"]
    degrees = args["degrees"]
    bands = args["bands"]
    workflow_name = args.get("workflow_name", "montage")
    output_format = args.get("output_format", "yaml")

    # Validate inputs
    if not isinstance(bands, list) or len(bands) == 0:
        return [TextContent(type="text", text="Error: bands must be a non-empty array")]

    if degrees <= 0 or degrees > 10:
        return [TextContent(type="text", text="Error: degrees must be between 0 and 10")]

    if output_format not in ["yaml", "hyperflow"]:
        return [TextContent(type="text", text="Error: output_format must be 'yaml' or 'hyperflow'")]

    # Create a temporary directory for generation
    with tempfile.TemporaryDirectory() as tmpdir:
        # Build command
        parent_dir = Path(__file__).parent.parent
        generator_script = parent_dir / "montage-workflow-yaml.py"

        if not generator_script.exists():
            return [TextContent(type="text", text=f"Error: Generator script not found at {generator_script}")]

        cmd = [
            "python3",
            str(generator_script),
            "--work-dir", tmpdir,
            "--center", center,
            "--degrees", str(degrees)
        ]

        for band in bands:
            cmd.extend(["--band", band])

        # Run the generator
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode != 0:
                error_msg = "Error generating workflow:\n"
                error_msg += f"Return code: {result.returncode}\n\n"

                if result.stderr:
                    error_msg += f"Error output:\n{result.stderr}\n"

                if result.stdout:
                    error_msg += f"\nStandard output:\n{result.stdout}\n"

                if not result.stderr and not result.stdout:
                    error_msg += "No error message captured. Command executed but failed silently.\n"
                    error_msg += f"Command: {' '.join(cmd)}\n"

                return [TextContent(
                    type="text",
                    text=error_msg
                )]

            # Read the generated YAML
            yaml_file = Path(tmpdir) / "data" / "montage-workflow.yml"
            if not yaml_file.exists():
                return [TextContent(
                    type="text",
                    text=f"Error: Workflow file not generated at {yaml_file}"
                )]

            with open(yaml_file, 'r') as f:
                yaml_content = f.read()

            # Create output directory for workflows
            output_dir = Path("/workflows")
            if not output_dir.exists():
                output_dir = Path("/tmp/workflows")
            output_dir.mkdir(exist_ok=True, parents=True)

            # Generate unique filename
            import time
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            safe_center = center.replace(" ", "_").replace(":", "").replace("/", "_")[:50]
            base_name = f"{safe_center}_{degrees}deg_{timestamp}"

            # Convert to HyperFlow if requested
            if output_format == "hyperflow":
                try:
                    # Parse YAML (use UnsafeLoader for numpy objects)
                    workflow_dict = yaml.load(yaml_content, Loader=yaml.UnsafeLoader)

                    # Import compiler
                    from yaml2hyperflow import HyperFlowCompiler

                    # Compile to HyperFlow
                    compiler = HyperFlowCompiler(workflow_dict)
                    hyperflow_dict = compiler.compile()

                    # Save to file
                    json_output = json.dumps(hyperflow_dict, indent=2)
                    output_file = output_dir / f"{base_name}.json"

                    with open(output_file, 'w') as f:
                        f.write(json_output)

                    # Generate summary
                    summary = _generate_workflow_summary(workflow_dict, "HyperFlow JSON")
                    summary += f"\n📁 Workflow saved to: {output_file}\n"
                    summary += f"📊 Size: {len(json_output):,} bytes ({len(json_output)/1024:.1f} KB)\n"

                    return [TextContent(type="text", text=summary)]
                except Exception as e:
                    return [TextContent(
                        type="text",
                        text=f"Error converting to HyperFlow format: {str(e)}"
                    )]
            else:
                # Save YAML to file
                output_file = output_dir / f"{base_name}.yml"

                with open(output_file, 'w') as f:
                    f.write(yaml_content)

                # Generate summary (use UnsafeLoader for numpy objects)
                workflow_dict = yaml.load(yaml_content, Loader=yaml.UnsafeLoader)
                summary = _generate_workflow_summary(workflow_dict, "YAML")
                summary += f"\n📁 Workflow saved to: {output_file}\n"
                summary += f"📊 Size: {len(yaml_content):,} bytes ({len(yaml_content)/1024:.1f} KB)\n"

                return [TextContent(type="text", text=summary)]

        except subprocess.TimeoutExpired:
            return [TextContent(
                type="text",
                text="Error: Workflow generation timed out (>5 minutes)"
            )]
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            return [TextContent(
                type="text",
                text=f"Error running generator: {str(e)}\n\nFull traceback:\n{error_details}"
            )]


async def compile_to_hyperflow(args: Dict[str, Any]) -> list[TextContent]:
    """Compile YAML workflow to HyperFlow JSON."""

    yaml_workflow = args["yaml_workflow"]

    try:
        # Parse YAML
        workflow_dict = yaml.safe_load(yaml_workflow)

        # Import compiler
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from yaml2hyperflow import HyperFlowCompiler

        # Compile
        compiler = HyperFlowCompiler(workflow_dict)
        hyperflow_dict = compiler.compile()

        # Convert to JSON
        json_output = json.dumps(hyperflow_dict, indent=2)

        return [TextContent(
            type="text",
            text=f"Successfully compiled to HyperFlow:\n\n```json\n{json_output}\n```"
        )]

    except yaml.YAMLError as e:
        return [TextContent(type="text", text=f"YAML parsing error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Compilation error: {str(e)}")]


async def validate_workflow(args: Dict[str, Any]) -> list[TextContent]:
    """Validate a YAML workflow."""

    yaml_workflow = args["yaml_workflow"]

    try:
        # Parse YAML
        workflow_dict = yaml.safe_load(yaml_workflow)

        errors = []
        warnings = []

        # Check required fields
        required_fields = ['name', 'files', 'tasks']
        for field in required_fields:
            if field not in workflow_dict:
                errors.append(f"Missing required field: {field}")

        # Validate files
        files = workflow_dict.get('files', {})
        for fname, finfo in files.items():
            if not isinstance(finfo, dict):
                errors.append(f"File '{fname}': should be a dictionary")
                continue

            if 'name' not in finfo:
                errors.append(f"File '{fname}': missing 'name' field")

            if finfo.get('is_input') and not finfo.get('source'):
                warnings.append(f"File '{fname}': input file has no source URL")

        # Validate tasks
        tasks = workflow_dict.get('tasks', [])
        file_names = set(files.keys())

        for i, task in enumerate(tasks):
            if not isinstance(task, dict):
                errors.append(f"Task {i}: should be a dictionary")
                continue

            # Check required task fields
            for field in ['name', 'executable', 'inputs', 'outputs']:
                if field not in task:
                    errors.append(f"Task {i}: missing '{field}' field")

            # Check file references
            for inp in task.get('inputs', []):
                if inp not in file_names:
                    errors.append(f"Task {i}: references undefined input '{inp}'")

            for out in task.get('outputs', []):
                if out not in file_names:
                    errors.append(f"Task {i}: references undefined output '{out}'")

        # Build result
        result = {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "stats": {
                "files": len(files),
                "tasks": len(tasks)
            }
        }

        result_text = "Validation Results:\n\n"
        if result["valid"]:
            result_text += "✅ VALID\n\n"
        else:
            result_text += "❌ INVALID\n\n"

        if errors:
            result_text += f"Errors ({len(errors)}):\n"
            for error in errors:
                result_text += f"  • {error}\n"
            result_text += "\n"

        if warnings:
            result_text += f"Warnings ({len(warnings)}):\n"
            for warning in warnings:
                result_text += f"  • {warning}\n"
            result_text += "\n"

        result_text += f"Statistics:\n"
        result_text += f"  Files: {result['stats']['files']}\n"
        result_text += f"  Tasks: {result['stats']['tasks']}\n"

        return [TextContent(type="text", text=result_text)]

    except yaml.YAMLError as e:
        return [TextContent(type="text", text=f"YAML parsing error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Validation error: {str(e)}")]


async def analyze_workflow(args: Dict[str, Any]) -> list[TextContent]:
    """Analyze a YAML workflow and return statistics."""

    yaml_workflow = args["yaml_workflow"]

    try:
        from collections import Counter

        # Parse YAML
        workflow_dict = yaml.safe_load(yaml_workflow)

        name = workflow_dict.get('name', 'Unknown')
        files = workflow_dict.get('files', {})
        tasks = workflow_dict.get('tasks', [])
        inputs = workflow_dict.get('inputs', [])
        outputs = workflow_dict.get('outputs', [])

        # Calculate statistics
        input_files = [f for f, info in files.items() if info.get('is_input', False)]
        output_files = [f for f, info in files.items() if info.get('is_output', False)]
        intermediate_files = [f for f in files.keys() if f not in input_files and f not in output_files]

        # Count tasks by executable
        executables = Counter(task.get('executable', 'unknown') for task in tasks)

        # Build analysis
        analysis = {
            "name": name,
            "files": {
                "total": len(files),
                "inputs": len(input_files),
                "outputs": len(output_files),
                "intermediate": len(intermediate_files)
            },
            "tasks": {
                "total": len(tasks),
                "by_executable": dict(executables)
            },
            "workflow_inputs": inputs[:10],  # First 10
            "workflow_outputs": outputs
        }

        # Format output
        text = f"Workflow Analysis: {name}\n"
        text += "=" * 60 + "\n\n"

        text += "Files:\n"
        text += f"  Total: {analysis['files']['total']}\n"
        text += f"  Inputs: {analysis['files']['inputs']}\n"
        text += f"  Outputs: {analysis['files']['outputs']}\n"
        text += f"  Intermediate: {analysis['files']['intermediate']}\n\n"

        text += "Tasks:\n"
        text += f"  Total: {analysis['tasks']['total']}\n"
        text += "  By executable:\n"
        for exe, count in sorted(analysis['tasks']['by_executable'].items()):
            text += f"    {exe}: {count}\n"
        text += "\n"

        text += f"Workflow Inputs ({len(inputs)}):\n"
        for inp in analysis['workflow_inputs']:
            text += f"  - {inp}\n"
        if len(inputs) > 10:
            text += f"  ... and {len(inputs) - 10} more\n"
        text += "\n"

        text += f"Workflow Outputs ({len(outputs)}):\n"
        for out in analysis['workflow_outputs']:
            text += f"  - {out}\n"

        return [TextContent(type="text", text=text)]

    except yaml.YAMLError as e:
        return [TextContent(type="text", text=f"YAML parsing error: {str(e)}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Analysis error: {str(e)}")]


async def list_supported_surveys(args: Dict[str, Any]) -> list[TextContent]:
    """List supported surveys and their bands."""

    surveys = {
        "2MASS": {
            "name": "Two Micron All-Sky Survey",
            "description": "Near-infrared survey covering the entire sky",
            "bands": {
                "j": "J-band (1.25 μm)",
                "h": "H-band (1.65 μm)",
                "k": "K-band (2.17 μm)"
            },
            "example": "2mass:j:red"
        },
        "DSS": {
            "name": "Digitized Sky Survey",
            "description": "Optical sky survey from photographic plates",
            "bands": {
                "DSS2B": "DSS2 Blue (B-band)",
                "DSS2R": "DSS2 Red (R-band)",
                "DSS2IR": "DSS2 Infrared (I-band)"
            },
            "example": "dss:DSS2B:blue"
        },
        "SDSS": {
            "name": "Sloan Digital Sky Survey",
            "description": "Modern multi-band optical survey",
            "bands": {
                "u": "Ultraviolet",
                "g": "Green",
                "r": "Red",
                "i": "Near-infrared",
                "z": "Infrared"
            },
            "example": "sdss:g:green"
        }
    }

    text = "Supported Astronomical Surveys\n"
    text += "=" * 60 + "\n\n"

    for survey_key, survey_info in surveys.items():
        text += f"{survey_key}: {survey_info['name']}\n"
        text += f"  {survey_info['description']}\n"
        text += "  Available bands:\n"
        for band, desc in survey_info['bands'].items():
            text += f"    - {band}: {desc}\n"
        text += f"  Example usage: '{survey_info['example']}'\n\n"

    text += "Color Mapping:\n"
    text += "  The third component maps survey bands to RGB colors:\n"
    text += "  - red: Red channel in final color image\n"
    text += "  - green: Green channel in final color image\n"
    text += "  - blue: Blue channel in final color image\n\n"

    text += "Example: Create RGB image from 2MASS:\n"
    text += "  ['2mass:j:blue', '2mass:h:green', '2mass:k:red']\n"

    return [TextContent(type="text", text=text)]


async def main():
    """Run the MCP server."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
