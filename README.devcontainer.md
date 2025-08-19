# Hardened DevContainer for Network Toolkit

This devcontainer provides a **production-ready, security-hardened** development environment for the Network Toolkit Python project. It enforces strict security boundaries while maintaining full VS Code development experience.

## Quick Start

1. **Open in Container**: `Ctrl+Shift+P` -> "Dev Containers: Reopen in Container"
2. **Seed Environment**: `Ctrl+Shift+P` -> "Tasks: Run Task" -> "Seed Environment"
3. **Edit `.env`**: Add your network device credentials
4. **Start Coding**: Dependencies auto-install, debugging and testing ready

## Security Guarantees

### Container Hardening

- **Read-only workspace**: Container cannot modify host repository
- **No host writes**: All writable data in named Docker volumes
- **Isolated network**: `--network=none` by default (port-forwarding works)
- **Least privilege**: `--read-only`, `--cap-drop=ALL`, `--security-opt=no-new-privileges`
- **Resource limits**: Memory (2GB), CPU (2 cores), PIDs (100)
- **No privileged access**: Non-root user, no Docker socket
- **Secrets isolation**: `.env` in read-only volume, never in image

### Data Persistence Strategy

All persistent data lives in **named Docker volumes**:

| Volume                    | Purpose                    | Mount Point       |
| ------------------------- | -------------------------- | ----------------- |
| `venv-net-worker`         | Python virtual environment | `.venv/`          |
| `pip-cache-net-worker`    | Package download cache     | `~/.cache/pip`    |
| `uv-cache-net-worker`     | UV package cache           | `~/.cache/uv`     |
| `outputs-net-worker`      | Application outputs        | `outputs/`        |
| `test-results-net-worker` | Test artifacts             | `test_results/`   |
| `results-net-worker`      | Command results            | `results/`        |
| `env-net-worker`          | Environment variables      | `.env` (readonly) |

## Configuration Profiles

### Default Profile (Network Enabled)

- **File**: `.devcontainer/devcontainer.json`
- **Network**: Full internet and local network access
- **Use case**: Normal development, device connections, package installation
- **Security**: Still hardened with read-only filesystem, no capabilities, resource limits

### Network Isolated Profile

- **File**: `.devcontainer/devcontainer.relaxed.json`
- **Network**: Completely isolated (`--network=none`)
- **Use case**: Air-gapped development, security testing
- **Switch**: `Ctrl+Shift+P` -> "Dev Containers: Rebuild and Reopen in Container" -> select isolated config

**Note**: The isolated profile prevents all network access including device connections. Use only for offline development.

## Essential Tasks

### Environment Setup

```bash
# Run via VS Code Task (recommended)
Ctrl+Shift+P -> Tasks: Run Task -> "Seed Environment"

# Or manually
bash .devcontainer/scripts/seed-env.sh
```

### Export Artifacts to Host

```bash
# Export outputs without overwriting
Ctrl+Shift+P -> Tasks: Run Task -> "Export Outputs"

# Force overwrite existing files
Ctrl+Shift+P -> Tasks: Run Task -> "Export Outputs (Force)"

# Or manually
bash .devcontainer/scripts/export-outputs.sh [--force]
```

### Development Tasks

```bash
# Install/update dependencies
uv sync

# Run tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/network_toolkit --cov-report=html

# Type checking
uv run mypy src/network_toolkit

# Linting and formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Security audit
uv run pip-audit
```

## Debugging & Testing

### VS Code Integration

- **Python Interpreter**: Auto-configured to `.venv/bin/python`
- **Test Discovery**: Pytest enabled for `tests/` directory
- **Debugging**: Multiple launch configurations available
- **Jupyter**: Notebooks run in container with full environment

### Debug Configurations

1. **Python: Current File** - Debug currently open Python file
2. **Python: Network Toolkit CLI** - Debug CLI commands
3. **Python: Pytest Current File** - Debug individual test files
4. **Python: Pytest All Tests** - Debug full test suite
5. **Python: Attach to debugpy** - Remote debugging on port 5678

### Port Forwarding

Even with `--network=none`, VS Code forwards these ports:

- **5678**: Python debugpy (debug server)
- **8000**: Web development server
- **8888**: Jupyter notebook server

## Acceptance Tests

Run these commands in the container terminal to verify security:

```bash
# Check container security status
Ctrl+Shift+P -> Tasks: Run Task -> "Container Security Check"
```

Expected output:

```
=== Container Security Status ===
Read-only root: ro
Capabilities: CapEff: 0000000000000000
NoNewPrivs: 1
Network: Network enabled (required for device connections)
Workspace write test: PASS: Workspace is read-only
```

### Manual Verification

```bash
# Verify read-only workspace
touch test.tmp 2>/dev/null && echo "FAIL: Can write!" || echo "PASS: Read-only"

# Check capabilities (should be empty)
grep CapEff /proc/self/status

# Check NoNewPrivs flag (should be 1)
grep NoNewPrivs /proc/self/status

# Test network access (should work in default profile)
ping -c1 8.8.8.8 2>/dev/null && echo "Network enabled" || echo "Network disabled"
```

## Adding Software Safely

### Method 1: Dev Container Features (Recommended)

Add to `.devcontainer/devcontainer.json`:

```json
{
  "features": {
    "ghcr.io/devcontainers/features/node:1": {
      "version": "20"
    }
  }
}
```

### Method 2: Dockerfile Updates

Edit `.devcontainer/Dockerfile`:

```dockerfile
# Add pinned system packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    package-name=version \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean
```

### Method 3: Python Dependencies

Update `pyproject.toml`:

```toml
[dependency-groups]
dev = [
    "new-package>=1.0.0",
    # ... existing packages
]
```

Then run: `uv sync`

## Troubleshooting

### Common Issues

**Q**: "Cannot write to workspace" error
**A**: Expected behavior - use volumes for persistent data, export when needed

**Q**: "Network unreachable" error
**A**: Check if you're using the isolated profile - switch to default profile for device access

**Q**: "Dependencies not found" error
**A**: Run `uv sync` or "Install Dependencies" task

**Q**: ".env file missing" error
**A**: Run "Seed Environment" task to create template

### Performance Optimization

- **Volume cleanup**: `docker volume prune` (removes unused volumes)
- **Image rebuild**: `Ctrl+Shift+P` -> "Dev Containers: Rebuild Container"
- **Cache reset**: Delete and recreate named volumes

### Switching Profiles

```bash
# To isolated profile (no network access)
Ctrl+Shift+P -> "Dev Containers: Rebuild and Reopen in Container"
# Select: .devcontainer/devcontainer.relaxed.json

# Back to default profile (network enabled)
Ctrl+Shift+P -> "Dev Containers: Rebuild and Reopen in Container"
# Select: .devcontainer/devcontainer.json
```

## Security Best Practices

1. **Never commit `.env`** - Always in `.gitignore`
2. **Use device-specific credentials** - `NW_{DEVICE}_USER/PASSWORD`
3. **Regular security audits** - Run `uv run pip-audit`
4. **Export selectively** - Only export necessary artifacts to host
5. **Monitor volumes** - Periodically clean up unused volumes
6. **Update regularly** - Keep base images and tools current

## Production Readiness

This devcontainer enforces production-grade practices:

- **Type safety**: MyPy strict mode
- **Code quality**: Ruff linting with comprehensive rules
- **Security scanning**: detect-secrets, pip-audit
- **Test coverage**: pytest with coverage reporting
- **Pre-commit hooks**: Automated quality checks
- **Dependency management**: Locked with uv.lock

## License

This devcontainer configuration is part of the Network Toolkit project and follows the same Apache-2.0 license.
