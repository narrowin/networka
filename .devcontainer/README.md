# Python 3.13 Development Container Template

A production-ready Python development environment with modern tooling and VS Code integration.

## Features

### Python 3.13

- Latest production-ready Python version
- Virtual environment management with `uv`
- Type checking with `mypy`

### Modern Tooling

- **uv**: Ultra-fast Python package manager (10-100x faster than pip)
- **ruff**: Lightning-fast linter and formatter (replaces black, isort, flake8)
- **pre-commit**: Git hooks for code quality enforcement
- **pytest**: Testing framework with async support
- **go-task**: Task runner for VS Code integration

### VS Code Integration

- Pre-configured tasks (Test, Lint, Format, Type Check)
- Essential Python extensions installed
- Debugging configuration ready
- IntelliSense and auto-completion

### Development Workflow

- Persistent package caches for faster rebuilds
- Automatic environment setup on container start
- Code quality enforcement via pre-commit hooks
- One-click testing and linting via VS Code tasks

## Quick Start

1. **Open in VS Code**: Use "Reopen in Container" when prompted
2. **Wait for setup**: Environment configures automatically
3. **Start coding**: All tools are ready to use

## Available Commands

### VS Code Tasks (Recommended)

- `Ctrl+Shift+P` → "Tasks: Run Task"
- **Test**: Run pytest with verbose output
- **Lint**: Check code with ruff
- **Format**: Auto-format code with ruff
- **Type Check**: Validate types with mypy

### Manual Commands

```bash
# Using uv (recommended for project commands)
uv run pytest tests/
uv run ruff check src/
uv run mypy src/

# Direct commands (for global tools)
pre-commit run --all-files
python --version
```

## Project Structure

Your Python project should include:

```text
pyproject.toml          # Python project configuration
.pre-commit-config.yaml # Git hooks configuration (optional)
src/                    # Source code
tests/                  # Test files
```

## Customization

### Adding Dependencies

1. Edit `pyproject.toml`
2. Run: `uv sync` or use VS Code task "Install Dependencies"

### Adding Pre-commit Hooks

1. Create `.pre-commit-config.yaml`
2. Run: `uv run pre-commit install`

### VS Code Extensions

Edit `.devcontainer/devcontainer.json` extensions list.

## Performance Notes

- **uv**: 10-100x faster than pip for package operations
- **ruff**: 10-100x faster than traditional Python linters
- **Persistent caches**: Docker layers cached for faster rebuilds
- **Virtual environment**: Isolated dependencies, no conflicts

## Container Features

- **Base**: Microsoft's Python 3.13 devcontainer image
- **Docker-in-Docker**: For containerized development
- **Git**: Latest version built from source
- **SSH Integration**: Host SSH keys mounted read-only for Git signing
- **Security**: Non-root user, proper permissions

## SSH Key Integration

This devcontainer automatically mounts your host SSH directory as read-only and configures Git signing:

- **Host SSH keys**: Available at `/home/vscode/.ssh-host` (read-only)
- **Git signing**: Auto-configured if `id_rsa-md-git` key found
- **Fallback**: Disables commit signing if keys not available

To customize the SSH key used for signing, edit `.devcontainer/scripts/setup-python-env.sh`.

## Troubleshooting

### Virtual Environment Issues

```bash
# Recreate environment
rm -rf .venv
uv venv .venv
uv sync
```

### Tool Not Found

```bash
# Ensure tools are installed
source ~/.cargo/env
uv tool install <tool-name>
```

### VS Code Tasks Not Working

- Ensure go-task is installed: `task --version`
- Check task definitions in workspace root

## Template Usage

This devcontainer is designed to be generic for any Python project:

1. Copy `.devcontainer/` folder to your project
2. Ensure you have `pyproject.toml` in project root
3. Open in VS Code and select "Reopen in Container"
4. Start developing!

## Tools Versions

- Python: 3.13.x
- uv: Latest stable
- ruff: Latest stable
- mypy: Latest stable
- pre-commit: Latest stable
- go-task: Latest stable

---

*This template follows KISS principles: Keep It Simple, Stupid*
