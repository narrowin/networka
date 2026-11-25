# Contributing to Network Toolkit

Thank you for your interest in contributing to the Network Toolkit!

For information about project governance, decision-making, and stability commitments, see [GOVERNANCE.md](GOVERNANCE.md).

## Development Setup

1. Clone the repository:

```bash
git clone https://github.com/narrowin/networka.git
cd networka
```

2. Use the uv version pinned in `pyproject.toml` and sync the locked development
   and documentation tools. uv selects Python 3.15.2 from `.python-version`.

```bash
uv sync --locked --group dev --extra docs
```

3. Install pre-commit hooks:

```bash
uv run --locked pre-commit install
```

## Code Standards

- Use Python 3.15 and current repository APIs.
- Follow the existing synchronous and asynchronous boundaries.
- Follow existing patterns in the codebase
- Verify changed behavior with the appropriate tests and CLI or package checks.
- Update documentation as needed

## Testing

Run the existing suite with:

```bash
uv run --locked pytest
```

## Code Quality

We use several tools to maintain code quality:

- **Ruff**: Linting and formatting
- **mypy**: Type checking
- **pytest**: Testing framework

Run quality checks:

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src/
```

## Commit Message Conventions

This project follows [Conventional Commits](https://www.conventionalcommits.org/) format:

```text
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, no logic change)
- **refactor**: Code refactoring (no feature or bug fix)
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, config)
- **ci**: CI/CD changes
- **perf**: Performance improvements
- **build**: Build system changes

### Examples

```text
feat(cli): add support for Nokia SR Linux
fix(transport): resolve SSH connection timeout
docs: update installation instructions
chore: bump version to v0.1.11
ci(deps): bump astral-sh/setup-uv from 4 to 7
```

### Scope

Optional but recommended. Use component names like: `cli`, `transport`, `config`, `backup`, `deps`

## Documentation

- `docs/reference/cli.md` is generated. Do not edit it manually.
- Regenerate the CLI docs with `task docs:generate` (or `uv run --locked python scripts/generate_cli_docs.py`).
- Always commit the updated `docs/reference/cli.md` alongside CLI changes so reviewers can see the diff.

## Pull Request Process

1. Fork the repository
2. Create a feature branch
3. Verify your changes
4. Ensure all checks pass
5. Submit a pull request

## Reporting Issues

Please use GitHub Issues to report bugs or request features. Include:

- Clear description of the issue
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS, etc.)
