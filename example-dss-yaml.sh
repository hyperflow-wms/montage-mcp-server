#!/bin/bash

set -e

# Example: Generate Montage workflow using MCP server (DSS optical data)
# This demonstrates using Digitized Sky Survey data

echo "========================================="
echo "DSS Optical Workflow Example"
echo "========================================="
echo ""
echo "Generating workflow for Pleiades (M45)"
echo "  Center: M45 (Pleiades star cluster)"
echo "  Size: 0.3 degrees"
echo "  Bands: DSS2B (blue), DSS2R (green), DSS2IR (red)"
echo "  Format: HyperFlow JSON"
echo ""

# Create output directory
mkdir -p workflows

# Create MCP request - using object name "M45"
cat > /tmp/example-dss.json << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"example","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"M45","degrees":0.3,"bands":["dss:DSS2B:blue","dss:DSS2R:green","dss:DSS2IR:red"],"output_format":"hyperflow","workflow_name":"dss_pleiades"}}}
EOF

# Call MCP server via Docker
echo "Calling MCP server..."
cat /tmp/example-dss.json | docker run --rm -i -v "$PWD/workflows:/workflows" montage-mcp-server:latest | \
    jq -r 'select(.id==2) | .result.content[]?.text // empty'

echo ""
echo "========================================="
echo "Success!"
echo "========================================="
echo ""
echo "Workflow saved to: workflows/"
ls -lh workflows/*.json | tail -1
echo ""
echo "To execute with HyperFlow:"
echo "  hflow run workflows/<workflow-file>.json"
