#!/bin/bash
#
# HyperFlow Workflow Execution Helper Script
#
# Usage:
#   ./run-workflow.sh <workflow-directory>
#
# This script:
#   1. Validates workflow directory structure
#   2. Downloads remote input files (if needed)
#   3. Prepares directory structure for HyperFlow
#   4. Runs workflow using Docker Compose
#
# Example:
#   ./run-workflow.sh ~/montage-workflows/M17_0.2deg_20251026_212533
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

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check arguments
if [ $# -ne 1 ]; then
    echo "Usage: $0 <workflow-directory>"
    echo ""
    echo "Example:"
    echo "  $0 ~/montage-workflows/M17_0.2deg_20251026_212533"
    exit 1
fi

WORKFLOW_DIR="$1"

# Validate workflow directory
if [ ! -d "$WORKFLOW_DIR" ]; then
    log_error "Workflow directory not found: $WORKFLOW_DIR"
    exit 1
fi

# Change to workflow directory and get absolute path
cd "$WORKFLOW_DIR"
WORKFLOW_DIR="$PWD"  # Convert to absolute path

log_info "Workflow directory: $WORKFLOW_DIR"

# Check for workflow.json
if [ ! -f "workflow.json" ]; then
    log_error "workflow.json not found in $WORKFLOW_DIR"
    exit 1
fi
log_success "Found workflow.json"

# Check for rc.txt
if [ ! -f "rc.txt" ]; then
    log_warning "rc.txt not found - skipping download step"
else
    log_success "Found rc.txt"

    # Count remote files that need downloading
    REMOTE_COUNT=$(grep -v 'pool="local"' rc.txt | wc -l)

    if [ $REMOTE_COUNT -gt 0 ]; then
        log_info "Found $REMOTE_COUNT remote files to download"

        # Check if FITS files already exist
        FITS_COUNT=$(ls -1 *.fits 2>/dev/null | wc -l)

        if [ $FITS_COUNT -ge $REMOTE_COUNT ]; then
            log_success "All $REMOTE_COUNT FITS files already downloaded (found $FITS_COUNT)"
        else
            log_info "Downloading remote input files ($FITS_COUNT/$REMOTE_COUNT present)..."

            if [ -f "$SCRIPT_DIR/download-rc-files.py" ]; then
                python3 "$SCRIPT_DIR/download-rc-files.py" rc.txt .

                if [ $? -eq 0 ]; then
                    log_success "Downloaded all remote files"
                else
                    log_error "Failed to download some files"
                    exit 1
                fi
            else
                log_error "download-rc-files.py not found at: $SCRIPT_DIR/download-rc-files.py"
                log_info "Please download files manually or provide the download script"
                exit 1
            fi
        fi
    else
        log_info "No remote files to download (all inputs are local)"
    fi
fi

# Verify input files are present
log_info "Verifying input files..."

FITS_COUNT=$(ls -1 *.fits 2>/dev/null | wc -l)
TBL_COUNT=$(ls -1 *.tbl 2>/dev/null | wc -l)
HDR_COUNT=$(ls -1 *.hdr 2>/dev/null | wc -l)
INPUT_FILES=$((FITS_COUNT + TBL_COUNT + HDR_COUNT))

if [ $INPUT_FILES -eq 0 ]; then
    log_error "No input files found in workflow directory"
    exit 1
fi
log_success "Found $INPUT_FILES input files (*.fits, *.tbl, *.hdr)"

# Check for docker-compose.yml
if [ ! -f "$SCRIPT_DIR/docker-compose.yml" ]; then
    log_error "docker-compose.yml not found at: $SCRIPT_DIR/docker-compose.yml"
    exit 1
fi

# Summary
echo ""
echo "=================================="
echo "Workflow Execution Summary"
echo "=================================="
echo "Workflow directory: $WORKFLOW_DIR"
echo "Input files: $INPUT_FILES (*.fits, *.tbl, *.hdr)"
echo "Workflow file: workflow.json"
echo "Docker Compose: $SCRIPT_DIR/docker-compose.yml"
echo "=================================="
echo ""

# Ask for confirmation
read -p "Start workflow execution? [Y/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]] && [[ ! -z $REPLY ]]; then
    log_warning "Execution cancelled"
    exit 0
fi

# Run Docker Compose
log_info "Starting HyperFlow workflow execution..."
echo ""

# Export environment variables for Docker Compose
# WORKFLOW_DIR is already absolute path from earlier
export WORKFLOW_DIR
export USER_ID=$(id -u)
export USER_GID=$(id -g)

docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up

# Check exit code
COMPOSE_EXIT=$?

echo ""
if [ $COMPOSE_EXIT -eq 0 ]; then
    log_success "Workflow execution completed"

    # Show generated output files (mosaics, etc.)
    echo ""
    log_info "Generated files in workflow directory:"
    ls -lht *.fits *.jpg 2>/dev/null | head -10 || echo "  (no output files found)"
else
    log_error "Workflow execution failed (exit code: $COMPOSE_EXIT)"
    exit $COMPOSE_EXIT
fi

# Clean up
echo ""
read -p "Remove Docker containers and networks? [Y/n] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]] || [[ -z $REPLY ]]; then
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down
    log_success "Cleaned up Docker resources"
fi

log_success "Done!"
