# Integration Testing

This directory contains integration tests for the Montage MCP Server, including workflow generation and execution testing.

## Quick Start

```bash
# Test all workflow formats (yaml, wfformat, hyperflow)
cd tests/integration
./test-all-formats.sh

# Test with specific test case
./test-all-formats.sh medium-3band

# Run a generated workflow with HyperFlow
./run-workflow.sh ../../test-output/M17_0.2deg_YYYYMMDD_HHMMSS
```

## Files

### Testing Scripts
- **test-all-formats.sh** - Main integration test script
  - Tests workflow generation in all three formats
  - Validates generated files
  - Optionally executes workflows

- **run-workflow.sh** - Workflow execution helper
  - Downloads remote input files
  - Prepares workflow directory
  - Runs workflow with Docker Compose + HyperFlow

- **download-rc-files.py** - Download remote FITS files
  - Parses replica catalog (rc.txt)
  - Downloads files from IPAC archive
  - Handles .gz decompression

### Configuration
- **docker-compose.yml** - Docker Compose configuration
  - Redis server for job queue
  - HyperFlow engine
  - Worker containers spawned dynamically

## Test Cases

Test cases are defined in `../fixtures/test-params.json`:

| Name | Description | Center | Size | Bands | Time |
|------|-------------|--------|------|-------|------|
| **small-1band** | Quick test | M17 | 0.2° | J-band | ~10min |
| **medium-3band** | Full test | M17 | 0.2° | J+H+K | ~30min |
| **large-3band** | Stress test | NGC 7293 | 0.5° | J+H+K | ~60min |
| **dss-optical** | Optical survey | M31 | 0.2° | DSS2B | ~15min |

## Usage

### Test All Formats

```bash
./test-all-formats.sh [test-case-name]
```

**Example output:**
```
========================================
  Montage MCP Server Integration Test
========================================

Test case: small-1band
Description: Small 1-band workflow for quick testing
Center: M17
Degrees: 0.2
Bands: ["2mass:j:red"]

----------------------------------------
[INFO] Testing yaml format generation...
[SUCCESS] Generated yaml workflow in /path/to/test-output/M17_0.2deg_20251029_120000
[INFO]   Files generated: 10
[SUCCESS] ✓ yaml generation test passed

----------------------------------------
[INFO] Testing wfformat format generation...
[SUCCESS] Generated wfformat workflow in /path/to/test-output/M17_0.2deg_20251029_120030
[INFO]   Files generated: 10
[SUCCESS] ✓ wfformat generation test passed

----------------------------------------
[INFO] Testing hyperflow format generation...
[SUCCESS] Generated hyperflow workflow in /path/to/test-output/M17_0.2deg_20251029_120100
[INFO]   Files generated: 10
[SUCCESS] ✓ hyperflow generation test passed

========================================
  Test Summary
========================================
[SUCCESS] All tests passed! (3/3)

[INFO] Generated workflows are in: /path/to/test-output
```

### Execute a Workflow

```bash
# After generating workflows with test-all-formats.sh
./run-workflow.sh ../../test-output/M17_0.2deg_YYYYMMDD_HHMMSS
```

**What it does:**
1. Validates workflow directory structure
2. Downloads remote FITS files (if not already present)
3. Verifies all input files are present
4. Runs workflow with Docker Compose + HyperFlow
5. Shows generated output files
6. Cleans up Docker containers

### Manual Workflow Execution

```bash
# 1. Generate workflow
cd ../..
cat > /tmp/test.json << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"M17","degrees":0.2,"bands":["2mass:j:red"],"output_format":"hyperflow"}}}
EOF

cat /tmp/test.json | docker run --rm -i \
  -v ~/montage-workflows:/workflows \
  montage-mcp-server:latest

# 2. Run workflow
cd tests/integration
./run-workflow.sh ~/montage-workflows/M17_0.2deg_YYYYMMDD_HHMMSS
```

## Requirements

### For Testing
- Docker
- Docker Compose
- `jq` (optional - for test parameter parsing)

### For Workflow Execution
- Docker socket access (`/var/run/docker.sock`)
- ~2GB RAM minimum
- Network access to IPAC archive (for downloading FITS files)

## Directory Structure

```
tests/integration/
├── README.md                   # This file
├── test-all-formats.sh         # Main test script
├── run-workflow.sh             # Workflow execution helper
├── download-rc-files.py        # File download utility
└── docker-compose.yml          # Docker Compose config

tests/fixtures/
└── test-params.json            # Test case definitions

test-output/                    # Generated workflows (created during tests)
└── M17_0.2deg_YYYYMMDD_HHMMSS/
    ├── workflow.json
    ├── rc.txt
    ├── *.fits
    ├── *.tbl
    └── *.hdr
```

## Troubleshooting

### Tests Fail with "Docker not running"
```bash
# Check Docker is running
docker ps

# Start Docker if needed
sudo systemctl start docker
```

### Tests Fail with "Permission denied on Docker socket"
```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Or run with sudo (not recommended)
sudo ./test-all-formats.sh
```

### Workflow Files Not Generated
```bash
# Check Docker image exists
docker images | grep montage-mcp-server

# Rebuild if needed
cd ../..
docker build -t montage-mcp-server:latest .
```

### Workflow Execution Hangs
```bash
# Check Redis is running
docker-compose logs redis

# Check HyperFlow logs
docker-compose logs hyperflow

# Check worker containers
docker ps | grep montage

# Stop and clean up
docker-compose down -v
```

### Input Files Download Fails
```bash
# Test IPAC connectivity
curl -I http://irsa.ipac.caltech.edu

# Download files manually
cd ../../test-output/M17_0.2deg_YYYYMMDD_HHMMSS
python3 ../../tests/integration/download-rc-files.py rc.txt .
```

## Continuous Integration

### GitHub Actions (Example)

```yaml
# .github/workflows/test.yml
name: Integration Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Build Docker image
        run: docker build -t montage-mcp-server:latest .

      - name: Run integration tests
        run: |
          cd tests/integration
          ./test-all-formats.sh small-1band
```

## Performance Benchmarks

Typical execution times on modern hardware:

| Test Case | Generation | Download | Execution | Total |
|-----------|------------|----------|-----------|-------|
| small-1band | ~5s | ~30s | ~5min | ~6min |
| medium-3band | ~10s | ~90s | ~15min | ~17min |
| large-3band | ~20s | ~5min | ~45min | ~50min |

## Adding New Test Cases

Edit `../fixtures/test-params.json`:

```json
{
  "test_cases": [
    {
      "name": "my-test",
      "description": "My custom test case",
      "center": "M42",
      "degrees": 0.3,
      "bands": ["2mass:j:red"],
      "timeout_minutes": 20
    }
  ]
}
```

Then run:
```bash
./test-all-formats.sh my-test
```

## Best Practices

1. **Start Small** - Test with `small-1band` first
2. **Check Logs** - Use `docker-compose logs -f` to monitor execution
3. **Clean Up** - Remove old test outputs regularly
4. **Resource Limits** - Limit Docker resources for large workflows
5. **Network** - Ensure stable connection for FITS downloads

## Support

For issues or questions:
- GitHub Issues: https://github.com/hyperflow-wms/montage-mcp-server/issues
- Documentation: https://github.com/hyperflow-wms/montage-mcp-server#readme
