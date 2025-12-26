#!/usr/bin/env bash
# Pre-release validation script
# This script ensures all quality checks pass BEFORE creating a release tag
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "==================================="
echo "Pre-Release Quality Checks"
echo "==================================="
echo ""

# Check if we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [[ "$CURRENT_BRANCH" != "main" ]]; then
    echo "WARNING: Not on main branch. Current branch: $CURRENT_BRANCH"
    echo "   Quality checks can run on any branch, but releases must be from main"
    echo ""
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo "ERROR: There are uncommitted changes. Commit or stash them first."
    exit 1
fi

# Ensure we're up to date with remote (only enforce on main branch)
if [[ "$CURRENT_BRANCH" == "main" ]]; then
    echo "Checking if main branch is up to date with remote..."
    git fetch origin main
    LOCAL=$(git rev-parse @)
    REMOTE=$(git rev-parse @{u})

    if [[ "$LOCAL" != "$REMOTE" ]]; then
        echo "ERROR: Your local main branch is not up to date with remote"
        echo "   Run: git pull origin main"
        exit 1
    fi
else
    echo "Skipping remote sync check (not on main branch)"
fi

# Check if task is available
if ! command -v task >/dev/null 2>&1; then
    echo "ERROR: 'task' command not found. Install go-task first."
    exit 1
fi

echo "Running quality checks locally..."
echo ""

# Run lint
echo "[1/4] Running lint checks..."
if ! task lint; then
    echo ""
    echo "ERROR: Lint checks failed. Fix issues and try again."
    exit 1
fi
echo "   ✓ Lint passed"
echo ""

# Run format check
echo "[2/4] Running format checks..."
if ! task format:check; then
    echo ""
    echo "ERROR: Format checks failed. Run 'task format' to fix."
    exit 1
fi
echo "   ✓ Format check passed"
echo ""

# Run type check
echo "[3/4] Running type checks..."
if ! task typecheck; then
    echo ""
    echo "ERROR: Type checks failed. Fix issues and try again."
    exit 1
fi
echo "   ✓ Type check passed"
echo ""

# Run test suite
echo "[4/4] Running test suite..."
if ! task test:ci; then
    echo ""
    echo "ERROR: Tests failed. Fix issues and try again."
    exit 1
fi
echo "   ✓ Tests passed"
echo ""

# Create a marker file with timestamp and commit hash
COMMIT_HASH=$(git rev-parse HEAD)
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
MARKER_FILE=".pre-release-passed"

cat > "$MARKER_FILE" << EOF
# Pre-release checks passed
# This file is used by release.sh to verify quality checks were run
COMMIT_HASH=$COMMIT_HASH
TIMESTAMP=$TIMESTAMP
EOF

echo "==================================="
echo "All Quality Checks Passed!"
echo "==================================="
echo ""
echo "Commit: $COMMIT_HASH"
echo "Time:   $TIMESTAMP"
echo ""
echo "You can now run the release script:"
echo "   ./scripts/release.sh --version X.Y.Z"
echo ""
echo "Note: If you make any changes to the code, you must"
echo "      run this script again before releasing."
echo ""
