#!/bin/bash
# Quick environment validation on container start

# Source cargo env for uv
source "$HOME/.cargo/env" 2>/dev/null || true

# Check if virtual environment exists
if [ -f ".venv/bin/activate" ]; then
    echo "✓ Python virtual environment ready at .venv"
else
    echo "⚠ No virtual environment found - run setup script if needed"
fi

# Quick tool check
echo "Development tools status:"
command -v uv &>/dev/null && echo "  ✓ uv $(uv version)"
command -v pre-commit &>/dev/null && echo "  ✓ pre-commit $(pre-commit --version)"

# Check project tools (via virtual environment)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    command -v ruff &>/dev/null && echo "  ✓ ruff $(ruff version)"
    command -v mypy &>/dev/null && echo "  ✓ mypy $(mypy --version | cut -d' ' -f2)"
    command -v pytest &>/dev/null && echo "  ✓ pytest $(pytest --version | head -n1 | cut -d' ' -f2)"
    deactivate
fi

# Show Python version
echo "Python: $(python3 --version)"

# Show available development commands
echo "Development workflow:"
echo "  → Use VS Code tasks: Ctrl+Shift+P → 'Tasks: Run Task'"
echo "  → Available: Test, Lint, Format, Type Check"
