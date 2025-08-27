# Development Guide

This guide is for contributors and maintainers working on the Networka codebase.

## Quick start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- git

### Setup development environment

```bash
# Clone the repository
git clone https://github.com/narrowin/networka.git
cd networka

# Install dependencies with development tools
uv sync

# Install pre-commit hooks
uv run pytest --version
uv run ruff --version
uv run mypy --version
```

### Development workflow

```bash
# Run all quality checks
uv run ruff check .              # Linting
uv run ruff format .             # Code formatting
uv run mypy src/                 # Type checking
uv run pytest                   # Run tests

# Or use the convenience script
./scripts/build.sh               # Run all checks + build

# Or use task runner (if you have go-task installed)
task dev                         # Complete development setup
task test                        # Run tests
### CI workflow checks locally

- Lint workflows (fast):
    - With Docker: `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest`
    - Or with act: `act pull_request -W .github/workflows/ci.yml -j workflow-lint`

Why run as a PR? Pull requests trigger different paths/conditions (e.g., `pull_request` filters, PR-only jobs). Simulating PR avoids surprises that don’t appear on `push`.

### Docs

- Strict docs build:
    - `uv run mkdocs build --strict`

Link checking runs in CI only.
task lint                        # Run linting
task build                       # Build package
```

## Code standards

### Style guidelines

- **Type hints**: All functions must have type annotations
- **Docstrings**: Use NumPy-style docstrings for public functions
- **Async patterns**: Use async/await for all I/O operations
- **Error handling**: Use custom exceptions from `exceptions.py`
- **Testing**: Write tests for all new features

### Code quality tools

- **Linting**: ruff (replaces flake8, isort, black)
- **Type checking**: mypy with strict settings
- **Testing**: pytest with async support
- **Security**: bandit for security linting

### Example code patterns

```python
# Async function with proper typing
async def execute_command(
    device_name: str,
    command: str,
    config: NetworkConfig
) -> CommandResult:
    """Execute a command on a network device.

    Parameters
    ----------
    device_name : str
        Name of the device to execute command on
    command : str
        Command to execute
    config : NetworkConfig
        Device configuration

    Returns
    -------
    CommandResult
        Result of command execution

    Raises
    ------
    DeviceConnectionError
        If connection to device fails
    DeviceExecutionError
        If command execution fails
    """
    try:
        async with DeviceSession(device_name, config) as session:
            return await session.execute_command(command)
    except ScrapliException as e:
        raise DeviceConnectionError(f"Failed to connect to {device_name}") from e
```

## Testing

### Running tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=network_toolkit --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_device.py

# Run with verbose output
uv run pytest -v

# Run async tests only
uv run pytest -m asyncio
```

### Writing tests

```python
import pytest
from unittest.mock import patch, AsyncMock
from network_toolkit.device import DeviceSession
from network_toolkit.config import NetworkConfig

@pytest.mark.asyncio
async def test_device_connection(mock_config: NetworkConfig):
    """Test device connection establishment."""
    with patch('scrapli.AsyncScrapli') as mock_scrapli:
        mock_scrapli.return_value.__aenter__.return_value.send_command = AsyncMock(
            return_value=MockResponse(result="test output")
        )

        async with DeviceSession("test_device", mock_config) as session:
            result = await session.execute_command("/system/identity/print")
            assert result.output == "test output"

@pytest.fixture
def mock_config() -> NetworkConfig:
    """Provide test configuration."""
    return NetworkConfig(
        general=GeneralConfig(timeout=30),
        devices={"test": DeviceConfig(host="192.168.1.1")}
    )
```

## Building and releasing

### Local build

```bash
# Build package locally
uv build

# Verify build
uv run twine check dist/*

# Test installation
pip install dist/*.whl
nw --help
```

### Release process

**IMPORTANT**: Always use the release script. Manual tag creation will fail due to version validation.

1. **Prepare for release**

   ```bash
   # Ensure you're on main branch with clean working directory
   git checkout main
   git pull origin main
   git status  # Should show no uncommitted changes

   # Run quality checks
   task test
   task lint
   task format
   ```

2. **Update CHANGELOG.md**

   Manually update the changelog with new features, fixes, and changes for the upcoming version.

3. **Execute release**

   ```bash
   # Test the release process first
   ./scripts/release.sh --version 1.0.0 --dry-run

   # Execute the actual release
   ./scripts/release.sh --version 1.0.0
   ```

   The release script automatically:

   - Updates version in `src/network_toolkit/__about__.py`
   - Updates `CHANGELOG.md` with release date
   - Commits changes with `chore: bump version to v1.0.0`
   - Pushes the commit to main
   - Creates and pushes the release tag

4. **Automated GitHub Actions**
   - Validates version consistency between tag and code
   - Builds and tests package on multiple platforms (Linux, Windows, macOS)
   - Creates GitHub release with build artifacts
   - Attaches wheel and source distribution files

**Never manually create release tags** - this will cause version mismatch errors in the build process.

## Project structure

```
networka/
├── src/network_toolkit/     # Main package
│   ├── cli.py              # CLI interface
│   ├── config.py           # Configuration models
│   ├── device.py           # Device connections
│   ├── exceptions.py       # Custom exceptions
│   └── results_enhanced.py # Results management
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Build and utility scripts
├── config/                 # Example configurations
└── pyproject.toml         # Project configuration
```

## Adding new features

### 1. Plan the feature

- Create or discuss GitHub issue
- Design API and data models
- Consider backward compatibility

### 2. Implement the feature

- Follow existing code patterns
- Add proper type annotations
- Include comprehensive error handling
- Write docstrings

### 3. Add tests

- Unit tests for core functionality
- Integration tests for CLI commands
- Mock external dependencies (network calls)
- Aim for >90% coverage

### 4. Update documentation

- Update relevant docs in `docs/`
- Add examples if applicable
- Update CLI help text

### 5. Submit pull request

- Run all quality checks locally
- Write clear commit messages
- Include tests and documentation
- Reference related issues

## Common development tasks

### Adding a new CLI command

```python
@app.command()
def new_command(
    device: Annotated[str, typer.Argument(help="Device name")],
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Description of the new command."""
    setup_logging("DEBUG" if verbose else "INFO")

    try:
        config = load_config()
        # Implementation here
        console.print("[green]Success[/green]")
    except NetworkToolkitError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
```

### Adding device type support

1. Add device type to `DeviceType` enum in `config.py`
2. Add scrapli platform mapping in `device.py`
3. Add vendor-specific sequences in `builtin_sequences/`
4. Write tests for the new device type

### Debugging tips

```bash
# Enable debug logging
export NW_LOG_LEVEL=DEBUG
nw your-command

# Use pytest debugging
uv run pytest --pdb tests/test_file.py::test_function

# Profile performance
uv run python -m cProfile -o profile.stats -m network_toolkit.cli run device command
```

## Continuous integration

The project uses GitHub Actions for CI/CD:

- **Tests**: Run on Python 3.11-3.13 across Ubuntu, Windows, macOS
- **Quality**: Linting, type checking, security scans
- **Build**: Package building and validation
- **Release**: Automated releases on git tags

### Local CI simulation

```bash
# Run the same checks as CI
./scripts/build.sh

# Or with task runner
task ci
```

## Getting help

- **Code questions**: Create GitHub issue with "question" label
- **Bugs**: Use bug report template in GitHub issues
- **Features**: Use feature request template
- **Security**: See SECURITY.md for reporting process

## Code review guidelines

### For contributors

- Keep PRs focused and small
- Write clear commit messages
- Include tests for new functionality
- Update documentation as needed
- Be responsive to feedback

### For reviewers

- Focus on code correctness and maintainability
- Check that tests adequately cover new code
- Verify documentation updates
- Ensure adherence to coding standards
- Be constructive and helpful in feedback
