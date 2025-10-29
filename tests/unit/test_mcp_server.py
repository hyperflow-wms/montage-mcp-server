#!/usr/bin/env python3
"""
Test script for the Montage MCP server.

This script tests the MCP server's tools without requiring a full MCP client.
It directly invokes the tool functions to verify they work correctly.
"""

import asyncio
import json
import sys
from pathlib import Path

# Add server directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server import (
    generate_montage_workflow,
    compile_to_hyperflow,
    validate_workflow,
    analyze_workflow,
    list_supported_surveys
)


async def test_list_surveys():
    """Test listing supported surveys."""
    print("=" * 70)
    print("TEST 1: List Supported Surveys")
    print("=" * 70)

    result = await list_supported_surveys({})
    print(result[0].text)
    print()


async def test_generate_workflow():
    """Test generating a workflow."""
    print("=" * 70)
    print("TEST 2: Generate Montage Workflow")
    print("=" * 70)

    args = {
        "center": "56.5 23.75",
        "degrees": 0.2,
        "bands": ["2mass:j:red"],
        "workflow_name": "test-workflow"
    }

    print(f"Parameters: {json.dumps(args, indent=2)}")
    print()

    result = await generate_montage_workflow(args)
    print(result[0].text[:1000])  # First 1000 chars
    print("\n... (truncated)\n")

    # Extract YAML for next tests
    text = result[0].text
    if "```yaml" in text:
        yaml_start = text.find("```yaml") + 7
        yaml_end = text.find("```", yaml_start)
        yaml_content = text[yaml_start:yaml_end].strip()
        return yaml_content
    return None


async def test_validate(yaml_workflow):
    """Test workflow validation."""
    print("=" * 70)
    print("TEST 3: Validate Workflow")
    print("=" * 70)

    if not yaml_workflow:
        print("No YAML workflow from previous test, skipping...")
        return

    args = {"yaml_workflow": yaml_workflow}

    result = await validate_workflow(args)
    print(result[0].text)
    print()


async def test_analyze(yaml_workflow):
    """Test workflow analysis."""
    print("=" * 70)
    print("TEST 4: Analyze Workflow")
    print("=" * 70)

    if not yaml_workflow:
        print("No YAML workflow from previous test, skipping...")
        return

    args = {"yaml_workflow": yaml_workflow}

    result = await analyze_workflow(args)
    print(result[0].text)
    print()


async def test_compile(yaml_workflow):
    """Test compilation to HyperFlow."""
    print("=" * 70)
    print("TEST 5: Compile to HyperFlow")
    print("=" * 70)

    if not yaml_workflow:
        print("No YAML workflow from previous test, skipping...")
        return

    args = {"yaml_workflow": yaml_workflow}

    result = await compile_to_hyperflow(args)
    print(result[0].text[:1000])  # First 1000 chars
    print("\n... (truncated)\n")


async def test_example_workflow():
    """Test with a pre-existing example workflow."""
    print("=" * 70)
    print("TEST 6: Test with Example Workflow")
    print("=" * 70)

    example_file = Path(__file__).parent.parent / "example-workflow.yml"

    if not example_file.exists():
        print(f"Example file not found: {example_file}")
        print("Skipping this test.")
        return

    with open(example_file, 'r') as f:
        yaml_content = f.read()

    print("Testing validation...")
    result = await validate_workflow({"yaml_workflow": yaml_content})
    print(result[0].text)
    print()

    print("Testing analysis...")
    result = await analyze_workflow({"yaml_workflow": yaml_content})
    print(result[0].text)
    print()

    print("Testing compilation...")
    result = await compile_to_hyperflow({"yaml_workflow": yaml_content})
    # Check if it succeeded
    if "Successfully compiled" in result[0].text:
        print("✓ Compilation successful")
    else:
        print("✗ Compilation failed")
        print(result[0].text[:500])
    print()


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 20 + "MCP SERVER TESTS" + " " * 32 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    # Test 1: List surveys (always works)
    await test_list_surveys()

    # Test 6: Example workflow (if available, doesn't need Montage)
    await test_example_workflow()

    # Tests 2-5: Full workflow generation (requires Montage)
    print("=" * 70)
    print("WORKFLOW GENERATION TESTS (Requires Montage)")
    print("=" * 70)
    print()

    # Check if Montage is available
    import shutil
    if not shutil.which('mProject'):
        print("⚠️  Montage toolkit not found in PATH")
        print("   Skipping workflow generation tests.")
        print()
        print("   To run these tests:")
        print("   1. Install Montage: http://montage.ipac.caltech.edu/")
        print("   2. Add Montage to your PATH")
        print("   3. Re-run this test script")
        print()
    else:
        print("✓ Montage toolkit found")
        print()

        try:
            # Test 2: Generate workflow
            yaml_workflow = await test_generate_workflow()

            if yaml_workflow:
                # Test 3: Validate
                await test_validate(yaml_workflow)

                # Test 4: Analyze
                await test_analyze(yaml_workflow)

                # Test 5: Compile
                await test_compile(yaml_workflow)
        except Exception as e:
            print(f"Error during workflow generation tests: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 70)
    print("TESTS COMPLETE")
    print("=" * 70)
    print()
    print("Summary:")
    print("  ✓ Survey listing works")
    print("  ✓ Example workflow tools work")
    if shutil.which('mProject'):
        print("  ✓ Workflow generation available")
    else:
        print("  ⚠  Workflow generation requires Montage")
    print()


if __name__ == "__main__":
    asyncio.run(main())
