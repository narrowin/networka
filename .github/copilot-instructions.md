# Networka (nw) - LLM Development Guide

NO MATTER WHAT RUN THE TESTS DIRECTLY THROUGH VS CODE TEST FEATURE, NOT TERMINAL!!!
ALL IMPORTS ONLY GO TO THE TOP OF THE FILE, NO EXCEPTIONS!!!

## CRITICAL PRINCIPLES

1. **KISS (Keep It Simple, Stupid)** - Simplicity and clarity above all
2. **No backward compatibility concerns** - Project has no users yet
3. **Production-ready code** - Not a prototype
4. **No emojis or decorative symbols** in code, help text, or markdown
5. **Test via VS Code test feature**, not terminal

## QUALITY STANDARDS

### User Experience

- **ALWAYS test actual command output** - Run commands and evaluate formatting
- **Clean, professional output** - Every character must serve a purpose
- **No duplicate messages** - One clear message per action
- **Proper exception handling** - Framework exceptions (typer.Exit) pass through, never log as "unexpected"
- **Separation of concerns** - Low-level functions use logger.debug(), high-level use user messages

### Code Quality

- **Question inherited patterns** - Don't accept bad code without improvement
- **Remove rather than add** - Prefer deletion over complexity
- **Test realistic scenarios** - Cover actual user workflows, not implementation details
- **Follow project standards** - Read and apply existing patterns consistently

### Before Any Commit

1. Run the actual commands and check output formatting
2. Verify no duplicate or confusing messages
3. Ensure proper exception handling separation
4. Confirm tests cover real user scenarios

## PROJECT CONTEXT

- **Purpose**: Async Python CLI for MikroTik RouterOS automation
- **Stack**: Python 3.11+, Typer, Scrapli, Pydantic v2, uv package manager
- **Testing**: pytest with async support, VS Code integration
- **Architecture**: Modern async/await, full type safety, 3000+ LOC mature codebase

## CODE STANDARDS

### Required Patterns

```python
# Type hints everywhere
async def execute_command(device: str, command: str) -> CommandResult:
    """NumPy-style docstring with clear purpose."""
    pass

# Async context managers
async with DeviceSession(device_name, config) as session:
    result = await session.execute_command(command)

# Custom exceptions from hierarchy
try:
    result = await operation()
except DeviceConnectionError as e:
    logger.error(f"Connection failed: {e}")
    raise

# Pydantic models for validation
class DeviceConfig(BaseModel):
    host: str
    port: int = 22
```

### Project Structure

```
network_toolkit/
├── cli.py           # Typer CLI commands
├── device.py        # Device session management
├── config.py        # Pydantic configuration models
├── exceptions.py    # Custom exception hierarchy
└── results.py       # Results management

tests/
├── conftest.py      # Shared fixtures
└── test_*.py        # Test files with mocked network ops
```

## EXCEPTION HIERARCHY

```
NetworkToolkitError (base)
├── ConfigurationError
├── DeviceConnectionError
├── DeviceExecutionError
├── FileTransferError
├── DeviceAuthError
└── DeviceTimeoutError
```

## SECURITY PATTERNS

- Credentials via environment variables only:
  - `NW_USER_DEFAULT` / `NW_PASSWORD_DEFAULT` (defaults)
  - `NW_{DEVICE}_USER` / `NW_{DEVICE}_PASSWORD` (overrides)
- No hardcoded credentials ever

## TESTING REQUIREMENTS

```python
@pytest.mark.asyncio
async def test_feature(mock_config):
    """All network operations must be mocked."""
    with patch('scrapli.AsyncScrapli') as mock:
        # Test implementation
```

## CLI COMMAND TEMPLATE

````python
## CLI COMMAND TEMPLATE

```python
@app.command()
def command_name(
    device: Annotated[str, typer.Argument(help="Device name")],
    config_file: Annotated[Path, typer.Option("--config", "-c")] = Path("devices.yml"),
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Clear, concise description."""
    setup_logging("DEBUG" if verbose else "INFO")

    try:
        config = load_config(config_file)
        ctx = CommandContext()
        # Implementation
        ctx.print_success("Operation completed")
    except NetworkToolkitError as e:
        ctx = CommandContext()
        ctx.print_error(str(e))
        raise typer.Exit(1)
````

## TESTING REQUIREMENTS

```python
@pytest.mark.asyncio
async def test_feature(mock_config):
    """All external dependencies must be mocked: network, filesystem, subprocess."""
    with patch('scrapli.AsyncScrapli') as mock:
        # Test implementation
```

**Mock everything external:**

- Network operations (scrapli, requests, etc.)
- File system operations when testing edge cases
- Subprocess calls (git, shell commands)
- Environment variables and user input

```

## NETWORK DEVICE SPECIFICS

- Account for device resource limitations
- Proper timeout handling for slow devices

## KEY LIBRARIES

- **CLI**: Typer with Rich output
- **Network**: Scrapli (AsyncScrapli for async)
- **Validation**: Pydantic v2
- **Package Management**: uv
- **Testing**: pytest, pytest-asyncio
- **Quality**: Ruff (lint/format), mypy (types)
```
