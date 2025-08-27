#!/usr/bin/env bash
# Local test script that mimics GitHub Actions workflow
set -euo pipefail

echo "🧪 Testing local installation process..."

# Clean up any previous test environments
rm -rf .test-env-*

# Test 1: Build and install wheel
echo "📦 Building package..."
uv build

echo "🔍 Testing wheel installation..."
python -m venv .test-env-wheel
source .test-env-wheel/bin/activate
pip install --upgrade pip

# Find and install wheel (same logic as GitHub Actions)
wheel_file=$(find dist/ -name "*.whl" | head -1)
if [ -n "$wheel_file" ]; then
    pip install "$wheel_file"
    echo "✅ Wheel installation successful"
else
    echo "❌ No wheel file found!"
    exit 1
fi

# Test CLI
echo "🧪 Testing CLI..."
nw --help
python -c "import network_toolkit; print('✅ Import successful')"

deactivate

# Test 2: Test source distribution
echo "🔍 Testing source distribution..."
python -m venv .test-env-source
source .test-env-source/bin/activate
pip install --upgrade pip

tar_file=$(find dist/ -name "*.tar.gz" | head -1)
if [ -n "$tar_file" ]; then
    pip install "$tar_file"
    echo "✅ Source distribution installation successful"
else
    echo "❌ No source distribution found!"
    exit 1
fi

# Test CLI again
nw --help
python -c "import network_toolkit; print('✅ Source install import successful')"

deactivate

# Test 3: Git installation (if we're in a git repo)
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "🔍 Testing git installation..."
    python -m venv .test-env-git
    source .test-env-git/bin/activate
    pip install --upgrade pip

    # Install from current git repo
    pip install git+file://$(pwd)
    nw --help
    python -c "import network_toolkit; print('✅ Git install successful')"

    deactivate
fi

# Cleanup
rm -rf .test-env-*

echo "🎉 All local tests passed!"
