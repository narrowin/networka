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
echo "Configuring Git signing from host configuration..."
if [ -f "/home/vscode/.gitconfig" ]; then
    # Read the signing key from the mounted host .gitconfig
    host_signing_key=$(git config --file /home/vscode/.gitconfig user.signingkey 2>/dev/null || echo "")

    if [ -n "$host_signing_key" ] && [ -d "/home/vscode/.ssh-host" ]; then
        # Extract just the key filename to make it portable
        key_filename=$(basename "$host_signing_key")
        host_key_path="/home/vscode/.ssh-host/keys/$key_filename"

        if [ -f "$host_key_path" ]; then
            echo "Found host signing key: $key_filename"
            # Configure Git to use the host SSH signing key
            git config --global user.signingkey "$host_key_path"
            git config --global gpg.format ssh
            git config --global gpg.ssh.program ssh-keygen
            git config --global commit.gpgsign true
            echo "Git configured with SSH signing key from host"
        else
            echo "Signing key referenced in host .gitconfig not found: $key_filename"
            echo "Available keys in host SSH:"
            ls -la /home/vscode/.ssh-host/keys/ 2>/dev/null || echo "No keys directory found"
            git config --global commit.gpgsign false
        fi
    else
        echo "No signing key configured in host .gitconfig or SSH directory not mounted"
        git config --global commit.gpgsign false
    fi
else
    echo "Host .gitconfig not mounted - commit signing disabled"
    git config --global commit.gpgsign false
fi

# Verify Git configuration is available
echo "Verifying Git identity configuration..."
if [ -f "/home/vscode/.gitconfig" ]; then
    echo "Git configuration mounted from host"
    user_name=$(git config --global --get user.name 2>/dev/null || echo "Not set")
    user_email=$(git config --global --get user.email 2>/dev/null || echo "Not set")
    echo "Git user: $user_name <$user_email>"

    # Show signing status
    if git config --global --get commit.gpgsign &>/dev/null; then
        signing_key=$(git config --global --get user.signingkey 2>/dev/null || echo "None")
        echo "Commit signing: enabled with key $(basename "$signing_key")"
    else
        echo "Commit signing: disabled"
    fi
else
    echo "Host .gitconfig not mounted - Git identity may need to be configured manually"
    echo "Use: git config --global user.name 'Your Name'"
    echo "Use: git config --global user.email 'your.email@example.com'"
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
