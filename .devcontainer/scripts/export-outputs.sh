#!/bin/bash
set -euo pipefail

# Export artifacts from container volumes to host
# Usage: ./export-outputs.sh [--force]

FORCE=false
if [[ "${1:-}" == "--force" ]]; then
    FORCE=true
    echo "WARNING: Force mode enabled - will overwrite existing host files"
fi

HOST_WORKSPACE="${LOCAL_WORKSPACE_FOLDER:-$(pwd)}"
CONTAINER_WORKSPACE="${WORKSPACE_FOLDER:-/workspace}"

echo "=== Exporting artifacts from container volumes to host ==="
echo "Host workspace: $HOST_WORKSPACE"
echo "Container workspace: $CONTAINER_WORKSPACE"

# Function to export directory if it exists and has content
export_directory() {
    local volume_dir="$1"
    local host_dir="$2"
    local description="$3"

    if [[ ! -d "$volume_dir" ]]; then
        echo "SKIP: $description: $volume_dir not found"
        return 0
    fi

    local file_count=$(find "$volume_dir" -type f 2>/dev/null | wc -l)
    if [[ $file_count -eq 0 ]]; then
        echo "SKIP: $description: no files found in $volume_dir"
        return 0
    fi

    if [[ -d "$host_dir" ]] && [[ "$FORCE" != "true" ]]; then
        echo "WARNING: Skipping $description: $host_dir exists (use --force to overwrite)"
        return 0
    fi

    echo "Exporting $description ($file_count files)..."
    mkdir -p "$(dirname "$host_dir")"

    if [[ "$FORCE" == "true" ]] && [[ -d "$host_dir" ]]; then
        rm -rf "$host_dir"
    fi

    cp -r "$volume_dir" "$host_dir"
    echo "DONE: Exported $description to $host_dir"
}

# Function to export individual files
export_file() {
    local volume_file="$1"
    local host_file="$2"
    local description="$3"

    if [[ ! -f "$volume_file" ]]; then
        echo "SKIP: $description: $volume_file not found"
        return 0
    fi

    if [[ -f "$host_file" ]] && [[ "$FORCE" != "true" ]]; then
        echo "WARNING: Skipping $description: $host_file exists (use --force to overwrite)"
        return 0
    fi

    echo "Exporting $description..."
    mkdir -p "$(dirname "$host_file")"
    cp "$volume_file" "$host_file"
    echo "DONE: Exported $description to $host_file"
}

# Export outputs directory
export_directory \
    "$CONTAINER_WORKSPACE/outputs" \
    "$HOST_WORKSPACE/outputs" \
    "outputs directory"

# Export test results
export_directory \
    "$CONTAINER_WORKSPACE/test_results" \
    "$HOST_WORKSPACE/test_results" \
    "test results"

# Export results directory
export_directory \
    "$CONTAINER_WORKSPACE/results" \
    "$HOST_WORKSPACE/results" \
    "results directory"

# Export lock files if they exist
export_file \
    "$CONTAINER_WORKSPACE/uv.lock" \
    "$HOST_WORKSPACE/uv.lock" \
    "uv.lock file"

export_file \
    "$CONTAINER_WORKSPACE/requirements.txt" \
    "$HOST_WORKSPACE/requirements.txt" \
    "requirements.txt file"

# Export coverage reports if they exist
if [[ -f "$CONTAINER_WORKSPACE/.coverage" ]]; then
    export_file \
        "$CONTAINER_WORKSPACE/.coverage" \
        "$HOST_WORKSPACE/.coverage" \
        "coverage data"
fi

if [[ -d "$CONTAINER_WORKSPACE/htmlcov" ]]; then
    export_directory \
        "$CONTAINER_WORKSPACE/htmlcov" \
        "$HOST_WORKSPACE/htmlcov" \
        "HTML coverage report"
fi

echo ""
echo "DONE: Export complete!"
echo ""
echo "Exported artifacts are now available on your host machine."
echo "Use 'git status' to see what files were created/modified."
