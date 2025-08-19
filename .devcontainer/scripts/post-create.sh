#!/bin/bash
set -euo pipefail

echo "=== Post-create setup ==="

# Make scripts executable
chmod +x .devcontainer/scripts/*.sh

# Create necessary directories in volumes
mkdir -p outputs test_results results

# Check if .env exists, if not prompt to create it
if [[ ! -f .env ]]; then
    echo ""
    echo "INFO: No .env file found."
    echo "You can copy .env.example to .env and customize it:"
    echo "  cp .env.example .env"
    echo ""
fi

# Verify Python and uv installation
echo "Python version: $(python --version)"
echo "uv version: $(uv --version)"

# Install dependencies if pyproject.toml exists and .venv doesn't have packages
if [[ -f pyproject.toml ]]; then
    echo "Found pyproject.toml"

    # Check if virtual environment has packages installed
    if [[ ! -f .venv/pyvenv.cfg ]] || ! uv pip list --quiet > /dev/null 2>&1; then
        echo "Installing dependencies with uv..."
        uv sync
        echo "DONE: Dependencies installed"
    else
        echo "DONE: Dependencies already installed"
    fi
else
    echo "WARNING: No pyproject.toml found - skipping dependency installation"
fi

# Install pre-commit hooks if .pre-commit-config.yaml exists
if [[ -f .pre-commit-config.yaml ]] && [[ -f .venv/bin/pre-commit ]]; then
    echo "Installing pre-commit hooks..."
    .venv/bin/pre-commit install
    echo "DONE: Pre-commit hooks installed"
fi

echo ""
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Seed .env file: Ctrl+Shift+P -> Tasks: Run Task -> Seed Environment"
echo "2. Edit .env with your credentials"
echo "3. Start coding!"
