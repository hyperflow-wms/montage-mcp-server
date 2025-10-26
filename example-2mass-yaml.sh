#!/bin/bash

set -e

# Example: Generate Montage workflow using MCP server (2MASS RGB)
# This demonstrates the recommended way to use the Montage workflow generator via MCP server

echo "========================================="
echo "2MASS RGB Workflow Example"
echo "========================================="
echo ""
echo "Generating workflow for Orion Nebula region"
echo "  Center: RA=83.8°, Dec=-5.4° (M42/Orion Nebula)"
echo "  Size: 0.5 degrees"
echo "  Bands: 2MASS J (blue), H (green), K (red)"
echo "  Format: YAML"
echo ""

# Create output directory
mkdir -p workflows

# Create MCP request
cat > /tmp/example-2mass.json << 'EOF'
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"example","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"83.8 -5.4","degrees":0.5,"bands":["2mass:j:blue","2mass:h:green","2mass:k:red"],"output_format":"yaml","workflow_name":"2mass_orion"}}}
EOF

# Call MCP server via Docker
echo "Calling MCP server..."
cat /tmp/example-2mass.json | docker run --rm -i -v "$PWD/workflows:/workflows" montage-mcp-server:latest | \
    jq -r 'select(.id==2) | .result.content[]?.text // empty'

echo ""
echo "========================================="
echo "Success!"
echo "========================================="
echo ""
echo "Workflow saved to: workflows/"
ls -lh workflows/*.yml | tail -1
echo ""
echo "To execute with HyperFlow, first convert to HyperFlow format:"
echo "  docker run --rm -i -v \$PWD/workflows:/workflows montage-mcp-server:latest << EOF"
echo '  {"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"cli","version":"1.0"}}}'
echo '  {"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"83.8 -5.4","degrees":0.5,"bands":["2mass:j:blue","2mass:h:green","2mass:k:red"],"output_format":"hyperflow"}}}'
echo "  EOF"
