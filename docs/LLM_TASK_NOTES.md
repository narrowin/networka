# Networka CLI → Library Refactor Notes

Purpose: compact context for LLMs continuing the refactor so the Typer CLI (`nw`) becomes a thin layer over an importable library without regressing behavior or tests.

## Current Architecture
- Package namespace: `network_toolkit` under `src/`.
- CLI entrypoint: `[project.scripts] nw = "network_toolkit.cli:app"` (unchanged).
- CLI pattern: Typer commands in `network_toolkit/commands/*` that should only parse args, call library functions, format output, and map exceptions to exit codes.
- Library pattern: Logic modules under `network_toolkit/api/*` returning typed data structures; no printing, no `sys.exit`/`typer.Exit`.
- Public surface: `network_toolkit/api/__init__.py` re-exports API types/functions.
- Example library module implemented: `network_toolkit/api/run.py` (`run_commands`, typed result dataclasses, `TargetResolutionError`).
- CLI wrapper updated: `network_toolkit/commands/run.py` now delegates to the API and only handles presentation/exit behavior.
- Helper tool: `scripts/api_test_tool.py` demonstrates calling the API directly via argparse (no Typer).

## Testing Status
- New API tests: `tests/test_api_run.py` (dummy DeviceSession) cover single-device command, group sequence, and unknown-target error handling with deterministic ordering.
- Full suite not run in this environment (pytest not available); rerun `pytest` once dependencies are present.

## Goals (keep these invariant)
- Separate heavy logic into `network_toolkit/api/*`; CLI files stay thin.
- Functions return typed data (dataclasses or Pydantic models) and raise typed exceptions; no printing/exit in library code.
- Reuse existing helpers (config/device/transport/sequence/results) instead of duplicating logic.
- Preserve existing behavior, output modes (including raw/JSON), and tests.
- Maintain API stability via `network_toolkit/api/__init__.py` exports and versioned result/exception types.

## Outstanding Work
- Add API-level tests for each migrated command and expand `api/__init__.py` exports.
- Document programmatic usage and API stability policy once more commands are migrated.
- Optional: update tooling/docs to encourage direct API use (e.g., enrich `scripts/compliance_report.py` or add examples).

## Quick Usage Examples
- Programmatic: `from network_toolkit.api.run imuv run nw list devicesport RunOptions, run_commands`
- CLI remains: `nw run ...` (delegates to API internally)

## Distilled Next-Session Focus (config)
- There is no need to migragte remaining commands (`config`, `ssh`, `schema`)!
- **`vendor_config_backup`**: Investigate `commands/vendor_config_backup.py`. It appears to be a command implementation but is not currently registered in `cli.py`. Determine if it should be refactored to `api/vendor_backup.py` or removed if obsolete.
