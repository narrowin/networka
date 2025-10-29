# Contributing to Network Toolkit

Thank you for your interest in contributing to the Network Toolkit!

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/narrowin/networka.git
cd networka
```

2. Install development dependencies:

```bash
uv sync --dev
```

3. Install pre-commit hooks:

```bash
pre-commit install
```

## Code Standards

- Python 3.11+ with full type annotations
- Use async/await for all I/O operations
- Follow existing patterns in the codebase
- Add tests for new functionality
- Update documentation as needed

## Testing

Run tests using VS Code test feature or:

```bash
pytest
```

## Code Quality

We use several tools to maintain code quality:

- **Ruff**: Linting and formatting
- **mypy**: Type checking
- **pytest**: Testing framework

Run quality checks:

```bash
ruff check .
ruff format .
mypy src/
```

## Documentation

- `docs/reference/cli.md` is generated. Do not edit it manually.
- Regenerate the CLI docs with `task docs:generate` (or `uv run python scripts/generate_cli_docs.py`).
- Always commit the updated `docs/reference/cli.md` alongside CLI changes so reviewers can see the diff.

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Ensure all checks pass
5. Submit a pull request

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
