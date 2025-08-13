#!/usr/bin/env bash
# Build script for net-worker
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🏗️  Building net-worker..."
echo "Project root: $PROJECT_ROOT"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ uv version: $(uv --version)"

# Clean previous builds
echo "🧹 Cleaning previous builds..."
rm -rf dist/ build/ *.egg-info/

# Install dependencies
echo "📦 Installing dependencies..."
uv sync --all-extras

# Run quality checks
echo "🔍 Running quality checks..."
echo "  - Linting with ruff..."
uv run ruff check .

echo "  - Formatting check with ruff..."
uv run ruff format --check .

echo "  - Type checking with mypy..."
uv run mypy src/

# Run tests
echo "🧪 Running tests..."
uv run pytest --cov=network_toolkit --cov-report=term-missing

# Build the package
echo "🏗️  Building package..."
uv build

# Check the build
echo "🔍 Checking build artifacts..."
uv run twine check dist/*

echo "✅ Build completed successfully!"
echo ""
echo "📦 Build artifacts:"
ls -la dist/
echo ""
echo "🚀 To publish to PyPI:"
echo "   uv run twine upload dist/*"
echo ""
echo "🧪 To publish to Test PyPI:"
echo "   uv run twine upload --repository testpypi dist/*"
