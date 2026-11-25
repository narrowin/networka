#!/bin/bash
# Run the quality and test checks on one local interpreter.
# Usage: bash scripts/test-like-ci.sh

set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")/.."

export FORCE_COLOR=1 PYTHONUNBUFFERED=1

uv sync --locked --group dev --extra docs
uv run --locked --extra docs python --version
uv run --locked --extra docs ruff check .
uv run --locked --extra docs ruff format --check .
uv run --locked --extra docs mypy src/
CI=true COLUMNS=150 uv run --locked --extra docs pytest --cov=network_toolkit --cov-report=xml --cov-report=term-missing
