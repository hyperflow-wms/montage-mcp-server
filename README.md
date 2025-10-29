# Montage MCP Server

[![Version](https://img.shields.io/badge/version-1.1.0-blue.svg)](https://github.com/hyperflow-wms/montage-mcp-server/releases/tag/v1.1.0)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-hyperflowwms%2Fmontage--mcp--server-blue.svg)](https://hub.docker.com/r/hyperflowwms/montage-mcp-server)

An MCP (Model Context Protocol) server that generates astronomical image mosaic workflows using the [Montage toolkit](http://montage.ipac.caltech.edu). Use natural language in Claude Desktop to create complex workflows for processing astronomical survey data.

**Version:** 1.1.0

## Features

- **Natural Language Interface**: Generate workflows using conversational commands in Claude Desktop
- **Object Name Resolution**: Use astronomical object names (M31, NGC 7293) instead of coordinates
- **Multiple Survey Support**: 2MASS (near-infrared), DSS (optical), SDSS (multi-band optical)
- **Dual Output Formats**: Export as YAML (WMS-agnostic) or HyperFlow JSON
- **Large Workflow Support**: Handles workflows >1MB via file-based output with volume mounts
- **Complete Montage v6.0**: All 70+ Montage binaries compiled and ready to use

## Quick Start

### 1. Run with Docker (Recommended)

```bash
# Pull the pre-built image (once available)
docker pull hyperflowwms/montage-mcp-server:latest

# Or build locally
docker build -t montage-mcp-server:latest .
```

### 2. Configure Claude Desktop

Add to your `claude_desktop_config.json`:

**Linux/Mac:**
```json
{
  "mcpServers": {
    "montage-workflow": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "-v", "/path/to/workflows:/workflows",
        "montage-mcp-server:latest"
      ]
    }
  }
}
```

**Windows (WSL):**
```json
{
  "mcpServers": {
    "montage-workflow": {
      "command": "wsl.exe",
      "args": [
        "-e", "docker", "run", "--rm", "-i",
        "-v", "/home/username/montage-workflows:/workflows",
        "montage-mcp-server:latest"
      ]
    }
  }
}
```

Replace `/path/to/workflows` with your desired workflow output directory.

### 3. Restart Claude Desktop

### 4. Use Natural Language

```
"Generate a Montage workflow for the Orion Nebula using 2MASS J, H, K bands"
"Create a 0.5 degree mosaic of M31 in HyperFlow format"
"What astronomical surveys are supported?"
```

## MCP Tools

### `generate_montage_workflow`
Generate a complete Montage workflow.

**Parameters:**
- `center` (required): Object name ("M31") or coordinates ("10.68 41.27")
- `degrees` (required): Mosaic size in degrees (0.1 to 10)
- `bands` (required): Array of survey bands (e.g., `["2mass:j:red"]`)
- `output_format` (optional): "yaml" (default) or "hyperflow"
- `workflow_name` (optional): Custom workflow name

**Returns:** Workflow summary with file location and statistics

### `list_supported_surveys`
List all available astronomical surveys and their bands.

### `validate_workflow`
Validate workflow YAML structure.

### `analyze_workflow`
Generate statistics about a workflow.

### `compile_to_hyperflow`
Convert YAML workflow to HyperFlow JSON format.

## Supported Surveys

### 2MASS (Two Micron All-Sky Survey)
Near-infrared survey covering the entire sky.
- **Bands**: `j` (1.25 μm), `h` (1.65 μm), `k` (2.17 μm)
- **Example**: `2mass:j:red`

### DSS (Digitized Sky Survey)
Optical sky survey from photographic plates.
- **Bands**: `DSS2B` (Blue), `DSS2R` (Red), `DSS2IR` (Infrared)
- **Example**: `dss:DSS2R:red`

### SDSS (Sloan Digital Sky Survey)
Modern multi-band optical survey.
- **Bands**: `u`, `g`, `r`, `i`, `z`
- **Example**: `sdss:g:green`

### Color Mapping
The third component maps to RGB channels:
- `:red` → Red channel
- `:green` → Green channel
- `:blue` → Blue channel

**Example RGB workflow:**
```json
{
  "center": "M17",
  "degrees": 0.5,
  "bands": ["2mass:j:blue", "2mass:h:green", "2mass:k:red"]
}
```

## Architecture

### Components

1. **MCP Server** (mcp-server/server.py) - FastMCP-based server implementing MCP protocol
2. **Workflow Generator** (montage-workflow-yaml.py) - Creates WMS-agnostic YAML workflows
3. **HyperFlow Compiler** (yaml2hyperflow.py) - Converts YAML to HyperFlow JSON
4. **Validators** - validate-workflow.py, workflow-stats.py

### Workflow Output

Large workflows (>1MB) are saved to `/workflows` directory:

**Format:** `{object}_{size}deg_{timestamp}.{ext}`

Example: `M31_0.5deg_20251026_143022.json`

## Development

### Local Setup

```bash
git clone https://github.com/hyperflow-wms/montage-mcp-server.git
cd montage-mcp-server
docker build -t montage-mcp-server:latest .
python3 tests/test_mcp_server.py
```

### Project Structure

```
montage-mcp-server/
├── Dockerfile                   # Container definition
├── README.md                    # This file
├── montage-workflow-yaml.py     # Workflow generator
├── yaml2hyperflow.py            # HyperFlow compiler
├── validate-workflow.py         # Validator
├── workflow-stats.py            # Analyzer
├── example-*.sh                 # Usage examples
├── mcp-server/
│   ├── server.py                # MCP server
│   └── requirements.txt         # Dependencies
└── tests/
    └── test_mcp_server.py       # Tests
```

## Troubleshooting

### "Error generating workflow" with no details
**Cause**: Network issue or invalid coordinates  
**Solution**: Verify object name, check network, try explicit coordinates

### "No images found"
**Cause**: Survey has no coverage for region  
**Solution**: Try 2MASS (best coverage), reduce region size

### Volume mount not working (Windows)
**Cause**: Path format or WSL issues  
**Solution**: Use WSL paths (`/home/user/workflows`), enable WSL integration in Docker Desktop

### Large workflows timing out
**Cause**: Complex workflows take time  
**Solution**: Start small (0.2-0.5 degrees), use single band initially

## Performance

| Region | Bands | Tasks | Time | Size |
|--------|-------|-------|------|------|
| 0.1°   | 1     | 10-20 | 5-10s | 10-20 KB |
| 0.2°   | 1     | 30-50 | 10-20s | 30-50 KB |
| 0.5°   | 1     | 100-200 | 30-60s | 100-200 KB |
| 0.5°   | 3     | 300-600 | 1-2min | 300-600 KB |
| 1.0°   | 3     | 1000-2000 | 2-5min | 1-2 MB |

**Resources**: Image ~920 MB, Memory 1 GB recommended

## Testing

### Quick Test

```bash
# Test workflow generation in all formats
cd tests/integration
./test-all-formats.sh

# Run a generated workflow
./run-workflow.sh ../../test-output/M17_0.2deg_YYYYMMDD_HHMMSS
```

### Test Cases

| Test Case | Description | Time | Purpose |
|-----------|-------------|------|---------|
| `small-1band` | M17, 0.2°, 1 band | ~6min | Quick validation |
| `medium-3band` | M17, 0.2°, 3 bands | ~17min | Full feature test |
| `large-3band` | NGC 7293, 0.5°, 3 bands | ~50min | Stress test |

See [tests/integration/README.md](tests/integration/README.md) for detailed testing documentation.

## Contributing

Contributions welcome! Fork, create feature branch, add tests, submit PR.

**Testing Requirements**: All PRs should include tests and pass `./tests/integration/test-all-formats.sh`

## License

MIT License - See LICENSE file

## Credits

- **Montage**: http://montage.ipac.caltech.edu
- **MCP Protocol**: https://modelcontextprotocol.io
- **HyperFlow**: https://github.com/hyperflow-wms
- **Astropy**: https://www.astropy.org

## Citation

```bibtex
@software{montage_mcp_server,
  title = {Montage MCP Server},
  author = {HyperFlow WMS Team},
  year = {2025},
  url = {https://github.com/hyperflow-wms/montage-mcp-server}
}
```

## Support

- **Issues**: https://github.com/hyperflow-wms/montage-mcp-server/issues
- **Discussions**: https://github.com/hyperflow-wms/montage-mcp-server/discussions
- **HyperFlow**: https://hyperflow-wms.github.io
