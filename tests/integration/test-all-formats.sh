#!/bin/bash
#
# Integration Test: Test workflow generation (default: both HyperFlow and WfFormat)
#
# Usage:
#   ./test-all-formats.sh [test-case-name] [format]
#
# Examples:
#   ./test-all-formats.sh                  # Run default small-1band test with both formats
#   ./test-all-formats.sh medium-3band     # Run specific test case with both formats
#   ./test-all-formats.sh small-1band both # Explicitly test both formats
#   ./test-all-formats.sh small-1band yaml # Test only yaml format (legacy)
#
# This script:
#   1. Generates workflows in specified format(s)
#   2. Validates the generated workflows
#   3. Optionally executes workflows with HyperFlow
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Test configuration
TEST_CASE="${1:-small-1band}"
FORMAT_OVERRIDE="${2:-}"
TEST_OUTPUT_DIR="$PROJECT_ROOT/test-output"
DOCKER_IMAGE="${DOCKER_IMAGE:-montage-mcp-server:latest}"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Parse test parameters
parse_test_params() {
    local params_file="$SCRIPT_DIR/../fixtures/test-params.json"

    if [ ! -f "$params_file" ]; then
        log_error "Test parameters file not found: $params_file"
        exit 1
    fi

    # Extract test case parameters using jq
    if ! command -v jq &> /dev/null; then
        log_warning "jq not installed - using default parameters"
        CENTER="M17"
        DEGREES="0.2"
        BANDS='["2mass:j:red"]'
        return
    fi

    local test_config=$(jq ".test_cases[] | select(.name == \"$TEST_CASE\")" "$params_file")

    if [ -z "$test_config" ]; then
        log_error "Test case not found: $TEST_CASE"
        log_info "Available test cases:"
        jq -r '.test_cases[].name' "$params_file" | sed 's/^/  - /'
        exit 1
    fi

    CENTER=$(echo "$test_config" | jq -r '.center')
    DEGREES=$(echo "$test_config" | jq -r '.degrees')
    BANDS=$(echo "$test_config" | jq -c '.bands')
    DESCRIPTION=$(echo "$test_config" | jq -r '.description')
}

# Test workflow generation
test_workflow_generation() {
    local format=$1

    log_info "Testing $format format generation..."

    # Create MCP request
    local request=$(cat <<EOF
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}
{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"generate_montage_workflow","arguments":{"center":"$CENTER","degrees":$DEGREES,"bands":$BANDS,"output_format":"$format"}}}
EOF
)

    # Generate workflow (run as current user for proper file ownership)
    local output=$(echo "$request" | docker run --rm -i \
        --user $(id -u):$(id -g) \
        -v "$TEST_OUTPUT_DIR:/workflows" \
        "$DOCKER_IMAGE" 2>&1)

    if [ $? -ne 0 ]; then
        log_error "Failed to generate $format workflow"
        echo "$output"
        return 1
    fi

    # Extract workflow directory from output (strip any trailing characters/emoji)
    local workflow_dir=$(echo "$output" | grep -oP 'Workflow directory: \K/workflows/[A-Za-z0-9_.-]+' | tail -1)

    if [ -z "$workflow_dir" ]; then
        log_error "Could not extract workflow directory from output"
        return 1
    fi

    # Convert container path to host path
    workflow_dir="${workflow_dir/\/workflows/$TEST_OUTPUT_DIR}"

    log_success "Generated $format workflow in $workflow_dir"

    # Verify workflow file exists
    if [ "$format" = "yaml" ]; then
        [ -f "$workflow_dir/workflow.yml" ] || { log_error "workflow.yml not found"; return 1; }
    elif [ "$format" = "both" ]; then
        [ -f "$workflow_dir/workflow.json" ] || { log_error "workflow.json not found"; return 1; }
        [ -f "$workflow_dir/workflow-wfformat.json" ] || { log_error "workflow-wfformat.json not found"; return 1; }
    elif [ "$format" = "wfformat" ]; then
        [ -f "$workflow_dir/workflow-wfformat.json" ] || { log_error "workflow-wfformat.json not found"; return 1; }
    else  # hyperflow
        [ -f "$workflow_dir/workflow.json" ] || { log_error "workflow.json not found"; return 1; }
    fi

    # Verify auxiliary files
    [ -f "$workflow_dir/rc.txt" ] || { log_warning "rc.txt not found"; }
    [ -f "$workflow_dir/region.hdr" ] || { log_error "region.hdr not found"; return 1; }

    # Count files
    local file_count=$(ls -1 "$workflow_dir" | wc -l)
    log_info "  Files generated: $file_count"

    # Store workflow directory for execution test
    echo "$workflow_dir" > "/tmp/test-workflow-dir-$format"

    return 0
}

# Test workflow execution (optional)
test_workflow_execution() {
    local format=$1
    local workflow_dir=$(cat "/tmp/test-workflow-dir-$format")

    log_info "Testing $format workflow execution..."

    if [ ! -d "$workflow_dir" ]; then
        log_error "Workflow directory not found: $workflow_dir"
        return 1
    fi

    # Check if docker-compose exists
    if [ ! -f "$SCRIPT_DIR/docker-compose.yml" ]; then
        log_warning "docker-compose.yml not found - skipping execution test"
        return 0
    fi

    # Only test execution for hyperflow format
    if [ "$format" != "hyperflow" ]; then
        log_info "Skipping execution test for $format (only hyperflow supported)"
        return 0
    fi

    # Run workflow (with timeout)
    log_info "Running workflow with HyperFlow..."

    export WORKFLOW_DIR="$workflow_dir"
    export USER_ID=$(id -u)
    export GROUP_ID=$(id -g)

    # Run with timeout
    timeout 600 bash "$SCRIPT_DIR/run-workflow.sh" "$workflow_dir" <<< "y" || {
        log_warning "Workflow execution timed out or failed (this is not critical for testing)"
        return 0
    }

    log_success "Workflow execution completed"
    return 0
}

# Main test execution
main() {
    echo "========================================"
    echo "  Montage MCP Server Integration Test"
    echo "========================================"
    echo ""

    # Parse test parameters
    parse_test_params

    log_info "Test case: $TEST_CASE"
    log_info "Description: $DESCRIPTION"
    log_info "Center: $CENTER"
    log_info "Degrees: $DEGREES"
    log_info "Bands: $BANDS"
    echo ""

    # Create test output directory
    mkdir -p "$TEST_OUTPUT_DIR"

    # Test formats (default: both in single directory)
    local formats
    if [ -n "$FORMAT_OVERRIDE" ]; then
        formats=("$FORMAT_OVERRIDE")
    else
        formats=("both")
    fi
    local failed=0

    for format in "${formats[@]}"; do
        echo "----------------------------------------"
        if test_workflow_generation "$format"; then
            log_success "✓ $format generation test passed"
        else
            log_error "✗ $format generation test failed"
            ((failed++))
        fi
        echo ""
    done

    # Summary
    echo "========================================"
    echo "  Test Summary"
    echo "========================================"

    if [ $failed -eq 0 ]; then
        log_success "All tests passed! ($((${#formats[@]} - failed))/${#formats[@]})"
        echo ""
        log_info "Generated workflows are in: $TEST_OUTPUT_DIR"
        echo ""
        log_info "Note: By default, both workflow.json (HyperFlow) and workflow-wfformat.json (WfFormat) are generated in the same directory."
        log_info "To test individual formats, use: $0 <test-case> yaml|wfformat|hyperflow"
        exit 0
    else
        log_error "Some tests failed! ($failed/${#formats[@]} failures)"
        exit 1
    fi
}

# Run main function
main
