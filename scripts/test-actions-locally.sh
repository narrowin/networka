#!/usr/bin/env bash
# Local test script that mimics GitHub Actions workflow
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

echo "🧪 Testing GitHub Actions workflow locally..."
echo "Project root: $PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_step() {
    echo -e "${YELLOW}📋 $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to test wheel installation
test_wheel_installation() {
    print_step "Testing wheel installation..."
    
    # Create a temporary virtual environment
    TEMP_VENV=$(mktemp -d)
    python3 -m venv "$TEMP_VENV"
    source "$TEMP_VENV/bin/activate"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Find and install wheel file
    wheel_file=$(find dist/ -name "*.whl" | head -1)
    if [ -n "$wheel_file" ]; then
        echo "Found wheel: $wheel_file"
        python -m pip install "$wheel_file"
        print_success "Wheel installation successful"
    else
        print_error "No wheel file found!"
        ls -la dist/
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    # Test the installed package
    print_step "Testing installed package..."
    if nw --help >/dev/null 2>&1; then
        print_success "CLI command works"
    else
        print_error "CLI command failed"
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    if python -c "import network_toolkit; print('✅ Import successful')" 2>/dev/null; then
        print_success "Python import works"
    else
        print_error "Python import failed"
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    # Cleanup
    deactivate
    rm -rf "$TEMP_VENV"
    print_success "Wheel test completed successfully"
}

# Function to test source distribution installation
test_source_installation() {
    print_step "Testing source distribution installation..."
    
    # Create a temporary virtual environment
    TEMP_VENV=$(mktemp -d)
    python3 -m venv "$TEMP_VENV"
    source "$TEMP_VENV/bin/activate"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Find and install source distribution
    tar_file=$(find dist/ -name "*.tar.gz" | head -1)
    if [ -n "$tar_file" ]; then
        echo "Found source dist: $tar_file"
        python -m pip install "$tar_file"
        print_success "Source distribution installation successful"
    else
        print_error "No source distribution found!"
        ls -la dist/
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    # Test the installed package
    print_step "Testing installed package from source..."
    if nw --help >/dev/null 2>&1; then
        print_success "CLI command works"
    else
        print_error "CLI command failed"
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    if python -c "import network_toolkit; print('✅ Source distribution import successful')" 2>/dev/null; then
        print_success "Python import works"
    else
        print_error "Python import failed"
        deactivate
        rm -rf "$TEMP_VENV"
        return 1
    fi
    
    # Cleanup
    deactivate
    rm -rf "$TEMP_VENV"
    print_success "Source distribution test completed successfully"
}

# Function to test git installation
test_git_installation() {
    print_step "Testing Git installation (if repo is accessible)..."
    
    # Create a temporary virtual environment
    TEMP_VENV=$(mktemp -d)
    python3 -m venv "$TEMP_VENV"
    source "$TEMP_VENV/bin/activate"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    
    # Try to install from current directory (simulates git install)
    if python -m pip install . 2>/dev/null; then
        print_success "Local directory installation successful"
        
        # Test the installed package
        if nw --help >/dev/null 2>&1; then
            print_success "CLI command works"
        else
            print_error "CLI command failed"
        fi
        
        if python -c "import network_toolkit; print('✅ Git-style installation successful')" 2>/dev/null; then
            print_success "Python import works"
        else
            print_error "Python import failed"
        fi
    else
        print_error "Local directory installation failed"
    fi
    
    # Cleanup
    deactivate
    rm -rf "$TEMP_VENV"
}

# Main execution
main() {
    # Check if dist directory exists
    if [ ! -d "dist" ]; then
        print_error "dist/ directory not found. Run 'task build' first."
        exit 1
    fi
    
    print_step "Found build artifacts:"
    ls -la dist/
    echo ""
    
    # Run tests
    if test_wheel_installation; then
        print_success "Wheel installation test PASSED"
    else
        print_error "Wheel installation test FAILED"
        exit 1
    fi
    
    echo ""
    
    if test_source_installation; then
        print_success "Source distribution test PASSED"
    else
        print_error "Source distribution test FAILED"
        exit 1
    fi
    
    echo ""
    
    test_git_installation
    
    echo ""
    print_success "🎉 All local tests completed successfully!"
    echo ""
    echo "This simulates what the GitHub Actions workflow will do."
    echo "Your package should work correctly when released!"
}

# Run main function
main "$@"
