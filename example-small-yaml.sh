#!/bin/bash

set -e

# Example: Generate a small Montage workflow using MCP server
# Quick test/demonstration with M17 (Swan Nebula)

echo "========================================="
echo "Small Workflow Example"
echo "========================================="
echo ""
echo "Generating workflow for M17 (Swan Nebula)"
echo "  Center: M17"
echo "  Size: 0.2 degrees (small, fast)"
echo "  Band: 2MASS J-band only"
echo "  Format: YAML"
echo ""

# Create output directory
mkdir -p workflows

# Create MCP request
cat > /tmp/example-small.json << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"example","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"M17","degrees":0.2,"bands":["2mass:j:red"],"output_format":"yaml","workflow_name":"small_m17"}}}
EOF

# Call MCP server via Docker
echo "Calling MCP server..."
cat /tmp/example-small.json | docker run --rm -i -v "$PWD/workflows:/workflows" montage-mcp-server:latest | \
    jq -r 'select(.id==2) | .result.content[]?.text // empty'

echo ""
echo "========================================="
echo "Success!"
echo "========================================="
echo ""
echo "Workflow saved to: workflows/"
ls -lh workflows/*.yml | tail -1
echo ""
echo "This is a small workflow (~30-40 tasks) suitable for testing."
echo ""
echo "To convert to HyperFlow format, use:"
echo "  docker run --rm -i -v \$PWD/workflows:/workflows montage-mcp-server:latest << EOF"
echo '  {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}'
echo '  {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"M17","degrees":0.2,"bands":["2mass:j:red"],"output_format":"hyperflow"}}}'
echo "  EOF"
