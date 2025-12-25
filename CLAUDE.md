# Networka

**MANDATORY**: Always start EVERY response with: "I have read and will strictly follow the Copilot Repository Instructions." (not just the first response - every single reply must begin with this statement)

## CRITICAL - Do Not

- **NEVER add AI/LLM attribution to commits, PRs, or code** - no "Generated with Claude Code", no "Co-Authored-By: Claude", no robot emojis, nothing
- Skip pre-commit checks
- Create .md files without explicit request (use `llm-plans/` for planning)
- Add emojis or decorative symbols anywhere
- Commit without running `uv run pre-commit run --all-files`
- Edit `docs/reference/cli.md` manually (it's auto-generated)

---

Multi-vendor CLI toolkit for network device automation via SSH. Uses Typer for CLI, Scrapli for transport.

## Tech Stack

- Python 3.11+, full type annotations required
- CLI: Typer with Rich output
- Transport: Scrapli (paramiko)
- Config: Pydantic, PyYAML
- Testing: pytest, pytest-asyncio
- Linting: Ruff, mypy
- Package manager: uv

## Project Structure

```
src/network_toolkit/
  cli.py              # Main CLI entry (Typer app)
  commands/           # CLI command modules (register pattern)
  inventory/          # Inventory backends (nornir, ssh_config)
  platforms/          # Vendor-specific implementations
  api/                # Python API for library usage
  common/             # Shared utilities (output, logging)
  transport/          # Connection handling (scrapli, nornir)
  exceptions.py       # Custom exception hierarchy
  config.py           # Configuration loading
tests/                # pytest tests
docs/                 # MkDocs documentation
```

## Commands

```bash
uv run ruff check --fix --unsafe-fixes .   # Lint and auto-fix
uv run pre-commit run --all-files          # Pre-commit checks (MANDATORY before commit)
uv run pytest                              # Run tests
uv run python scripts/generate_cli_docs.py # Regenerate CLI docs
uv run mkdocs serve                        # Preview docs locally
```

## Code Patterns

### Command Registration

Commands use `register(app: typer.Typer)` pattern:

```python
# src/network_toolkit/commands/example.py
example_app = typer.Typer(name="example", help="...")

@example_app.command("subcommand")
def subcommand(...) -> None:
    ...

def register(app: typer.Typer) -> None:
    app.add_typer(example_app)
```

Register in cli.py:
```python
from network_toolkit.commands.example import register as register_example
register_example(app)
```

### Error Handling

Use `ConfigurationError` for config/validation errors:

```python
from network_toolkit.exceptions import ConfigurationError

raise ConfigurationError("Human-readable message", details={"key": "value"})
```

Exception hierarchy: `NetworkToolkitError` > `ConfigurationError`, `DeviceConnectionError`, `DeviceExecutionError`, `FileTransferError`

### Testing

- Use `typer.testing.CliRunner` for CLI tests
- Use `tmp_path` fixture for file operations
- Test through main `app`, not sub-apps
- Include happy path and error cases

## Config Locations

- Primary: `~/.config/networka/` (Linux), `~/Library/Application Support/networka/` (macOS)
- Devices: `config/devices/`
- Sequences: `config/sequences/`
- Main config: `config/config.yml`

## Code Style

- Imports at top of file only
- Type annotations on all functions
- Prefer deletion over complexity
- No over-engineering or backward-compatibility hacks

## CLI UX Guidelines

- **Sensible defaults**: Commands should work with zero arguments when possible. Use `~/.ssh/config` as default input, `<config-dir>/devices/` as default output, etc.
- **Progressive disclosure**: Simple case first, options for power users. `nw sync ssh-config` should just work; `--include`, `--exclude`, `--prune` are optional.
- **Predictable paths**: Use `common/paths.py` and `common/defaults.py` for platform-appropriate config directories.
- **Help text**: Include examples in docstrings. Show the simple case first.

## Documentation Guidelines

- Update docs when adding/changing CLI commands
- Run `uv run python scripts/generate_cli_docs.py` after CLI changes
- Preview with `uv run mkdocs serve` before committing doc changes
- Keep examples minimal - show the simplest working command first

## Commit Conventions

Follow Conventional Commits: `type(scope): description`

Types: feat, fix, docs, style, refactor, test, chore, ci, perf, build

```
feat(cli): add SSH config sync command
fix(transport): resolve connection timeout
docs: update installation guide
```
