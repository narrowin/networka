#!/bin/bash
# Quick environment validation on container start

# Source cargo env for uv
source "$HOME/.cargo/env" 2>/dev/null || true

# Setup SSH keys from host for Git signing
echo "Setting up SSH environment..."
if [ -d "/home/vscode/.ssh-host" ]; then
    # Create SSH directory structure
    mkdir -p ~/.ssh/keys

    # Create symlinks to host SSH keys and config
    if [ -d "/home/vscode/.ssh-host/keys" ]; then
        ln -sf /home/vscode/.ssh-host/keys/* ~/.ssh/keys/ 2>/dev/null || true
        echo "SSH keys linked from host"
    fi

    if [ -f "/home/vscode/.ssh-host/config" ]; then
        ln -sf /home/vscode/.ssh-host/config ~/.ssh/config 2>/dev/null || true
        echo "SSH config linked from host"
    fi

    # Fix Git signing key path for container environment
    current_signing_key=$(git config user.signingkey 2>/dev/null || echo "")
    if [ -n "$current_signing_key" ] && [[ "$current_signing_key" == /* ]]; then
        # Convert any absolute host path to container path using the filename
        key_filename=$(basename "$current_signing_key")
        container_key_path="$HOME/.ssh/keys/$key_filename"

        if [ -f "$container_key_path" ]; then
            git config --local user.signingkey "$container_key_path"
            echo "Git signing key path updated for container: $key_filename"
        else
            echo "Git signing key not found in container: $key_filename"
        fi
    fi

    # Set correct permissions for SSH directory
    chmod 700 ~/.ssh 2>/dev/null || true
    chmod 600 ~/.ssh/keys/* 2>/dev/null || true
else
    echo "No host SSH directory found - Git signing may not work"
fi

# Check if virtual environment exists
if [ -f ".venv/bin/activate" ]; then
    echo "Python virtual environment ready at .venv"
else
    echo "No virtual environment found - run setup script if needed"
fi

# Quick tool check
echo "Development tools status:"
command -v uv &>/dev/null && echo "  uv $(uv version)"
command -v pre-commit &>/dev/null && echo "  pre-commit $(pre-commit --version)"

# Check project tools (via virtual environment)
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    command -v ruff &>/dev/null && echo "  ruff $(ruff version)"
    command -v mypy &>/dev/null && echo "  mypy $(mypy --version | cut -d' ' -f2)"
    command -v pytest &>/dev/null && echo "  pytest $(pytest --version | head -n1 | cut -d' ' -f2)"
    deactivate
fi

# Show Python version
echo "Python: $(python3 --version)"

# Show available development commands
echo "Development workflow:"
echo "Use VS Code tasks: Ctrl+Shift+P -> 'Tasks: Run Task'"
echo "Available: Test, Lint, Format, Type Check"
