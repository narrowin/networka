# Networka repository guidance

Networka is a multi-vendor device automation CLI (`nw`) and Python SDK
(`NetworkaClient`). Use the current runtime and APIs. Carry backward
compatibility requirements only when the user explicitly requests them.

## Repository map

- `src/network_toolkit/cli.py` registers the Typer app and global options.
  `commands/` implements commands, using Rich for presentation.
- `src/network_toolkit/api/` implements operations and returns structured
  results. `client.py` exposes them through the SDK and owns the session pool.
- `src/network_toolkit/config.py` owns Pydantic models and config loading.
  `inventory/` handles inventory import, including Nornir's simple inventory.
- `src/network_toolkit/device.py`, `session_pool.py`, and `transport/` handle
  connection lifecycle, the native Scrapli command transport, and Paramiko SFTP.
- `src/network_toolkit/platforms/` and `builtin_sequences/` contain platform
  operations and packaged command sequences. `tui/` contains the Textual UI.
- `tests/` contains pytest cases. `docs/` is the MkDocs site.
  `scripts/` and `Taskfile.yml` provide development checks.

## Setup and checks

Use the uv version pinned in `pyproject.toml`. Runtime requires Python 3.15
or later. CI uses Python 3.15, and `.python-version` pins Python 3.15.2 for
development. Run project CLIs, scripts, tests, and Python subprocesses through uv.

```bash
uv sync --locked --group dev --extra docs
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src/
uv run --locked pytest
```

For help changes, regenerate `docs/reference/cli.md` with
`uv run --locked python scripts/generate_cli_docs.py`. For doc changes, use
`uv run --locked --extra docs mkdocs build --strict`. See the
[development guide](../docs/development.md) for the offline CLI and clean
artifact installation procedures.

## Code boundaries and tests

- Keep command parsing and presentation in the CLI. Reuse shared command
  context and output handling. Check exit status and the applicable stdout,
  stderr, raw, and JSON behavior when it changes.
- Keep API results structured. Put config data and shared validation in existing
  models. Verify config discovery and sequence precedence when changing them.
- Make first use work from a clean install on a qualified platform. Bundle a
  qualified starter sequence and use the installed platform definition by
  default. Require target and access details, plus the platform when inventory
  cannot supply it. Keep custom YAML, driver overrides, and catalog management
  optional. Show the selected command, source, and result, and make errors
  actionable.
- Follow the existing sync and async boundaries. Close device sessions
  explicitly through the client, pool, or transport that owns them.
- Review the contract in the existing tests before choosing a check.
  `test_api_run.py` covers operation results, and `test_cli.py` and
  `test_output_manager.py` cover CLI and output behavior.
  `test_client_session_reuse.py` and `test_session_pool.py` cover connection
  ownership. `test_nornir_simple_inventory_import.py` covers inventory mapping.
  `test_tui_services_cancellation.py` covers TUI cancellation.
- Repair existing tests and use existing entry points. Assert specific results
  and isolate network access at the boundary where a case needs it. Create or
  expand automated suites, fixtures, mock harnesses, or failure-injection
  scripts only when the user explicitly requests those artifacts.

## Scope and completion evidence

- Inspect git status and the relevant diff before editing. Preserve unrelated
  changes and untracked files. Keep ordinary local fixes focused and proceed.
- For meaningful decisions, classify the change as Two-way door, One-way door,
  or No action/change. State the problem and desired outcome, compare real
  options, then recommend one before acting. Score ICE = Impact × Confidence ×
  Ease on 1–10 scales and explain each score. Rate the outcome, evidence behind
  the estimates, and implementation effort. A Two-way door is contained and
  reversible. Proceed with reasonable confidence. A One-way door is hard to
  reverse or has broad impact. Get operator confirmation before crossing it.
- Obtain explicit authorization for live device access, with a named target and
  operation, and for pushes, deployments, or publication. A local verification
  request authorizes ordinary local checks.
- Use [networka-verify](skills/networka-verify/SKILL.md) to verify a
  code or package change. Match the checks to the changed contract. Record
  commands, concrete observations, skips or warnings, and layers left untested.
- Run `git diff --check` before handing off changes. For commit and contribution
  conventions, see [CONTRIBUTING.md](../CONTRIBUTING.md).
