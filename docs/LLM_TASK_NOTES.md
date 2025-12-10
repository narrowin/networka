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
- Migrate remaining commands (upload, download, backup, firmware, config, list, info, etc.) into `network_toolkit/api/<command>.py` with matching slim CLI wrappers.
- Add API-level tests for each migrated command and expand `api/__init__.py` exports.
- Document programmatic usage and API stability policy once more commands are migrated.
- Optional: update tooling/docs to encourage direct API use (e.g., enrich `scripts/compliance_report.py` or add examples).

## Quick Usage Examples
- Programmatic: `from network_toolkit.api.run import RunOptions, run_commands`
- CLI remains: `nw run ...` (delegates to API internally)

## Distilled Next-Session Focus (download/upload)
- Goal: apply the established API/CLI split to file transfer commands.
- Targets: move logic out of `network_toolkit/commands/download.py` and `network_toolkit/commands/upload.py` into `network_toolkit/api/download.py` and `network_toolkit/api/upload.py`.
- API: return typed dataclasses (e.g., `DownloadOptions/DownloadResult`, `UploadOptions/UploadResult`), raise `NetworkToolkitError` on failures, no printing or exits.
- CLI: Typer wrappers only parse args, call the API, format output (Rich/raw/JSON), and map exceptions to exit codes.
- Tests: add API-level tests (`tests/test_api_download.py`, `tests/test_api_upload.py`) and keep existing integration tests passing (e.g., `tests/test_file_downloads.py`, `tests/test_file_upload.py`).
- Reference pattern: follow `api/run.py` + `commands/run.py` for structure and separation of concerns (no backup refactor yet in this codebase; adjust references accordingly).
