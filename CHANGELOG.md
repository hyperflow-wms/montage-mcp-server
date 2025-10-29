# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2025-10-29

### Changed
- **Default workflow generation now produces both HyperFlow and WfFormat in same directory**
  - Default `output_format` changed from 'yaml' to 'both'
  - Generates `workflow.json` (HyperFlow) and `workflow-wfformat.json` (WfFormat) together
  - Reduces directory clutter by consolidating formats in single workflow directory
  - YAML format (workflow.yml) now legacy, maintained for backward compatibility

### Added
- **WORKFLOW-INFO.txt file** - Auto-generated metadata file in each workflow directory
  - Generation parameters (center, size, bands, format)
  - Workflow statistics (task count, file count, inputs/outputs)
  - Task breakdown by executable type
  - Generated file listings with sizes
  - Usage instructions for HyperFlow execution
  - Download instructions for remote FITS files
- **File ownership support** - Generated files now owned by host user instead of root
  - Use Docker's `--user` flag to run container as current user
  - Simpler than environment variables, works automatically
  - Test scripts automatically pass `--user $(id -u):$(id -g)`
- New 'both' output format option to generate HyperFlow + WfFormat simultaneously
- Updated test suite to use 'both' as default format
- Enhanced test script to accept format override via command-line argument

### Technical Details
- Workflow generators run in separate temporary directories when producing multiple formats
- Auxiliary files (*.tbl, *.hdr, rc.txt) copied from first generator (identical across formats)
- Tool schema updated to support 'both' enum value with proper validation
- Test script supports: `./test-all-formats.sh <test-case> [both|yaml|wfformat|hyperflow]`
- WORKFLOW-INFO.txt provides human-readable documentation for each generated workflow

## [1.1.0] - 2025-10-26

### Added
- WfCommons WfFormat support as third output format option
- New `montage-workflow-wfformat.py` generator for WfFormat JSON (schema v1.5)
- New `wfformat2hyperflow.py` compiler to convert WfFormat to HyperFlow JSON
- Support for 'wfformat' output_format parameter in generate_montage_workflow tool
- WfCommons dependency (wfcommons>=1.1) for workflow research community standards
- Parent-child task dependency computation based on file producers/consumers
- Complete workflow specification with tasks and files sections
- Execution metadata section with makespan and runtime information

### Changed
- Updated MCP server to support three output formats: 'yaml', 'wfformat', 'hyperflow'
- Dockerfile now includes both YAML and WfFormat workflow generators
- Enhanced tool descriptions to document WfFormat option

### Technical Details
- WfFormat follows WfCommons schema version 1.5
- Full backward compatibility with existing 'yaml' and 'hyperflow' formats
- WfFormat provides standardized JSON representation for workflow research
- Docker image size remains optimized with cached layers

## [1.0.0] - 2025-01-26

### Added
- Initial release of Montage MCP Server
- MCP (Model Context Protocol) server for workflow generation via Claude Desktop
- Support for astronomical object name resolution (M31, NGC 7293, etc.) via Astropy
- Multiple survey support: 2MASS (near-infrared), DSS (optical), SDSS (multi-band)
- Dual output formats: YAML (WMS-agnostic) and HyperFlow JSON
- File-based workflow output for large workflows (>1MB) with volume mount support
- Complete Montage v6.0 toolkit (70+ binaries) compiled with GCC 10+ compatibility
- Docker containerization for easy deployment
- Comprehensive error handling with detailed diagnostic messages
- Example scripts demonstrating MCP server usage
- Test suite for validation

### Features
- `generate_montage_workflow` - Generate complete Montage workflows
- `list_supported_surveys` - List available astronomical surveys
- `validate_workflow` - Validate workflow YAML structure
- `analyze_workflow` - Generate workflow statistics
- `compile_to_hyperflow` - Convert YAML to HyperFlow JSON

### Documentation
- Comprehensive README with quick start guide
- Installation and configuration instructions for Claude Desktop
- Usage examples and troubleshooting guide
- MIT License

[1.0.0]: https://github.com/hyperflow-wms/montage-mcp-server/releases/tag/v1.0.0
