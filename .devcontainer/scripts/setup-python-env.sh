#!/bin/bash
set -e

echo "Setting up Python development environment..."

# Ensure cache directories exist and have correct permissions
echo "Setting up cache directories..."
mkdir -p "$HOME/.cache/uv" "$HOME/.cache/pip" "$HOME/.cache/mypy"
sudo chown -R $(id -u):$(id -g) "$HOME/.cache"
chmod -R 755 "$HOME/.cache"

# Install uv - ultra-fast Python package manager
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

# Add uv to PATH for current session
export PATH="$HOME/.cargo/bin:$PATH"

# Add to shell profiles for persistence
for shell_rc in "$HOME/.bashrc" "$HOME/.zshrc"; do
    if [ -f "$shell_rc" ] && [ -w "$shell_rc" ]; then
        grep -q '.cargo/bin' "$shell_rc" || echo 'export PATH="$HOME/.cargo/bin:$PATH"' >> "$shell_rc"
        grep -q '.local/bin' "$shell_rc" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$shell_rc"
    fi
done

# Install global Python tools via uv that are needed for pre-commit and development
echo "Installing Python development tools..."
uv tool install pre-commit  # Git hooks
uv tool install ipython     # Enhanced Python REPL
uv tool install rich-cli    # Better terminal output
uv tool install httpie      # Better HTTP client for API testing

# Install project dependencies using uv sync (reads pyproject.toml)
if [ -f "pyproject.toml" ]; then
    echo "Found pyproject.toml, setting up project environment..."

    # Create virtual environment if it doesn't exist
    if [ ! -d ".venv" ]; then
        echo "Creating virtual environment..."
        uv venv .venv
    fi

    # Install project dependencies including dev dependencies
    echo "Installing project dependencies..."
    uv sync --all-extras
fi

# Setup SSH keys from host (if available)
if [ -d "/home/vscode/.ssh-host" ] && [ -f "/home/vscode/.ssh-host/id_rsa-md-git" ]; then
    echo "Configuring Git with host SSH keys..."
    # Configure Git to use the host SSH signing key
    git config --global user.signingkey "/home/vscode/.ssh-host/id_rsa-md-git"
    git config --global gpg.format ssh
    git config --global gpg.ssh.program ssh-keygen
    git config --global commit.gpgsign true
    echo "✓ Git configured with SSH signing key from host"
elif [ -d "/home/vscode/.ssh-host" ]; then
    echo "⚠ Host SSH directory mounted but signing key not found"
    echo "Available keys in host .ssh:"
    ls -la /home/vscode/.ssh-host/ 2>/dev/null || echo "Cannot list host SSH directory"
else
    echo "⚠ Host SSH directory not mounted - commit signing disabled"
    git config --global commit.gpgsign false
fi

# Setup pre-commit hooks if config exists
if [ -f ".pre-commit-config.yaml" ]; then
    echo "Setting up pre-commit hooks..."
    # Make sure we use uv run for consistency with local repo setup
    uv run pre-commit install --install-hooks
fi

echo "Python development environment setup complete!"
echo "To activate the virtual environment: source .venv/bin/activate"
echo "Or use 'uv run <command>' to run commands in the project environment"
