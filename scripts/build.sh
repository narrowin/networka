#!/usr/bin/env bash
# Build script for networka
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🏗️  Building networka..."
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
rm -rf -- dist/ build/ *.egg-info/

# Install dependencies
echo "📦 Installing dependencies..."
uv sync --locked --group dev --extra docs

# Run quality checks
echo "🔍 Running quality checks..."
echo "  - Linting with ruff..."
uv run --locked --extra docs ruff check .

echo "  - Formatting check with ruff..."
uv run --locked --extra docs ruff format --check .

echo "  - Type checking with mypy..."
uv run --locked --extra docs mypy src/

# Run tests
echo "🧪 Running tests..."
uv run --locked --extra docs pytest --cov=network_toolkit --cov-report=term-missing

# Build the package
echo "🏗️  Building package..."
uv build --no-sources

# Check the build
echo "🔍 Checking build artifacts..."
echo "📦 Build artifacts:"
ls -la dist/
echo ""

# Validate package structure
echo "📋 Package validation:"
echo "Source distribution contents:"
tar -tzf dist/*.tar.gz | sed -n '1,10p'
echo ""
echo "Wheel contents:"
unzip -l dist/*.whl | sed -n '1,10p'
echo ""

echo "✅ Build completed successfully!"
echo ""
echo "� Ready for GitHub release!"
echo "   1. Create a new release at: https://github.com/narrowin/networka/releases/new"
echo "   2. Attach the files from dist/ directory"
echo "   3. Users can install with:"
echo "      uv tool install networka"
echo "      # or"
echo "      pip install networka"
echo "   4. Or download and install the wheel file"
