# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
