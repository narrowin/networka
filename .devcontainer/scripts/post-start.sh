#!/bin/bash
# Quick environment validation on container start
# Don't exit on errors to prevent startup failure
set +e

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
            git config --local gpg.format ssh
            git config --local gpg.ssh.program ssh-keygen
            git config --local commit.gpgsign true
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

# Check if virtual environment exists and has dependencies
if [ -f ".venv/bin/activate" ]; then
    echo "Python virtual environment ready at .venv"

    # Quick check if dependencies are installed, sync if needed
    if [ -f "pyproject.toml" ]; then
        if ! uv run python -c "import pytest, ruff, mypy" 2>/dev/null; then
            echo "Some dependencies missing, running uv sync..."
            uv sync --all-extras --quiet
        fi
    fi
else
    echo "No virtual environment found - run setup script if needed"
fi

# Quick tool check
echo "Development tools status:"
command -v uv &>/dev/null && echo "  uv $(uv version)"
command -v pre-commit &>/dev/null && echo "  pre-commit $(pre-commit --version)"

# Check project tools (via uv run to ensure proper environment)
if [ -f ".venv/bin/activate" ] && [ -f "pyproject.toml" ]; then
    # Use uv run to ensure dependencies are available
    uv run ruff --version 2>/dev/null | head -n1 | sed 's/^/  /' || echo "  ruff (not available)"
    uv run python -c "import mypy.version; print(f'  mypy {mypy.version.__version__}')" 2>/dev/null || echo "  mypy (not available)"
    uv run python -c "import pytest; print(f'  pytest {pytest.__version__}')" 2>/dev/null || echo "  pytest (not available)"
fi

# Show Python version
echo "Python: $(python3 --version)"

# Show available development commands
echo "Development workflow:"
echo "Use VS Code tasks: Ctrl+Shift+P -> 'Tasks: Run Task'"
echo "Available: Test, Lint, Format, Type Check"
