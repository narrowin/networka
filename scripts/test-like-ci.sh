#!/bin/bash
# Script to run tests exactly like CI does
# Usage: ./scripts/test-like-ci.sh

set -euo pipefail

echo "=== Running tests exactly like CI does ==="
echo "Current directory: $(pwd)"
echo "Git root: $(git rev-parse --show-toplevel)"

# Ensure we're in the repository root (like CI)
cd "$(git rev-parse --show-toplevel)"

echo "Working directory: $(pwd)"
echo

# Set the same environment variables as CI
export FORCE_COLOR="1"
export PYTHONUNBUFFERED="1"

echo "=== Step 1: Ruff check (like CI) ==="
uv run ruff check src/ tests/

echo
echo "=== Step 2: Ruff format check (like CI) ==="
uv run ruff format --check src/ tests/

echo
echo "=== Step 3: MyPy check (like CI) ==="
uv run mypy src/

echo
echo "=== Step 4: Run tests with coverage (EXACTLY like CI) ==="
uv run pytest --cov=network_toolkit --cov-report=xml --cov-report=term-missing

echo
echo "=== All checks passed - matches CI! ==="
