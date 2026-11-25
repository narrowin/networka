# Development Guide

For project governance, see
[GOVERNANCE.md](https://github.com/narrowin/networka/blob/main/GOVERNANCE.md).

## Quick start

Install git and the [uv](https://docs.astral.sh/uv/) version pinned in
`pyproject.toml`. uv selects Python 3.15.2 from `.python-version`. Networka
requires Python 3.15 or later, and CI uses Python 3.15.

```bash
git clone https://github.com/narrowin/networka.git
cd networka
uv sync --locked --group dev --extra docs
uv run --locked pre-commit install
```

## Development checks

```bash
uv run --locked ruff check .
uv run --locked ruff format --check .
uv run --locked mypy src/
uv run --locked pytest
```

For a targeted check, run an existing file or test, such as
`uv run --locked pytest tests/test_api_run.py`. When investigating coverage,
use `uv run --locked pytest --cov=network_toolkit --cov-report=term-missing`.
Choose cases that assert the public result, output, or lifecycle that changed.

Run `bash scripts/test-like-ci.sh` for local lint, format, type, and coverage
checks. Use `task test:ci` for the coverage run alone. If editing workflows,
run `actionlint` when available.

### Documentation

Regenerate the CLI reference after changing help or commands. MkDocs uses
the generated file in `docs/reference/cli.md`.

```bash
uv run --locked python scripts/generate_cli_docs.py
uv run --locked --extra docs mkdocs build --clean --strict
```

With go-task, use `task docs` to regenerate the references and build the
site, or `task docs:serve` to preview it.

## Functional verification

### Offline CLI walkthrough

From the checkout after the locked setup, run this Bash block. It uses
a temporary example inventory and keeps optional sequences, schema,
and shell completion installation disabled. It clears color overrides
inside the block to exercise default rendering with redirected output.

```bash
(
    set -eu
    work_dir=$(mktemp -d "${TMPDIR:-/tmp}/networka-offline.XXXXXX")
    trap 'rm -rf -- "$work_dir"' EXIT
    export COLUMNS=200
    unset FORCE_COLOR NO_COLOR NW_OUTPUT_MODE

    config_dir="$work_dir/config"
    uv run --locked nw config init "$config_dir" --yes \
        --no-install-sequences --no-install-completions \
        --no-activate-completions --no-install-schemas
    uv run --locked nw config validate --config "$config_dir" > "$work_dir/validate.txt"
    uv run --locked nw list devices --config "$config_dir" > "$work_dir/devices.txt"
    uv run --locked nw list groups --config "$config_dir" > "$work_dir/groups.txt"
    uv run --locked nw list sequences --config "$config_dir" --vendor mikrotik_routeros \
        > "$work_dir/sequences.txt"
    uv run --locked nw info health_check --config "$config_dir" > "$work_dir/health-check.txt"
    uv run --locked nw info system_info --config "$config_dir" --vendor mikrotik_routeros \
        > "$work_dir/system-info.txt"

    uv run --locked nw --help > "$work_dir/help.txt"
    uv run --locked nw platforms --help > "$work_dir/platforms-help.txt"
    uv run --locked nw run -h > "$work_dir/run-help.txt"
    status=0
    uv run --locked nw run --not-an-option > "$work_dir/bad-option.txt" 2>&1 || status=$?
    test "$status" -eq 2
    grep -F -- 'No such option: --not-an-option' "$work_dir/bad-option.txt"

    grep -F 'Configuration is valid!' "$work_dir/validate.txt"
    grep -Fw router1 "$work_dir/devices.txt"
    grep -Fw switch1 "$work_dir/devices.txt"
    grep -Fw office "$work_dir/groups.txt"
    grep -Fw critical "$work_dir/groups.txt"
    grep -Fw system_info "$work_dir/sequences.txt"
    grep -F 'Usage:' "$work_dir/help.txt" "$work_dir/platforms-help.txt" "$work_dir/run-help.txt"
    grep -F -- '--port' "$work_dir/run-help.txt"
    grep -F '/system resource print' "$work_dir/health-check.txt"
    grep -F '/interface print brief' "$work_dir/health-check.txt"
    grep -F "$(cd "$config_dir" && pwd -P)/sequences/sequences.yml" "$work_dir/health-check.txt"
    if LC_ALL=C grep -l $'\033' "$work_dir/"*.txt; then
        printf 'Unexpected ANSI escape in redirected output\n' >&2
        exit 1
    fi
    cat "$work_dir/system-info.txt"
)
```

Record the `Source` and commands from the displayed `system_info` table.
A temporary inventory still consults user-level sequences. Compare the
commands to the reported file, or to
`src/network_toolkit/builtin_sequences/mikrotik_routeros/common.yml` if
the table reports the built-in file. The `health_check` assertions check
the generated, global sequence and its temporary source.

### Clean installation

```bash
bash scripts/test-local-install.sh
```

The script builds the current working tree with `uv build --no-sources`.
It installs the exact new wheel and source archive into separate temporary
uv environments outside the checkout. Package dependencies resolve from the
configured index or uv cache. The script reports SHA-256 hashes, the tested
Python version, dependency consistency, CLI help and version, SDK and native
Scrapli imports, and packaged typing and YAML resources.

### Authorized lab check

For an explicitly approved device and operation, pass the lab config and
exact target name. Inspect the actual identity and OS version output.

```bash
uv run --locked python scripts/lab_validation.py --config /path/to/lab-config --target lab-router
```

The script checks for command errors and nonempty output. With `--list` it
only lists configured devices. For live checks, keep `--target` explicit.
The script selects every device without either selector, and `--tag` can
select several.

| Check | Evidence |
| --- | --- |
| Unit and service tests | Named code contracts with the boundaries used by the cases |
| Offline CLI walkthrough | Startup, parsing, config generation and loading, sequence inspection, and redirected output |
| Clean artifact installation | Packaging, dependencies, resources, imports, and startup for the tested Python and OS |
| Authorized lab check | Results from the specific commands on the recorded device and OS |

## Code and project structure

- `src/network_toolkit/cli.py` registers the Typer application. Command
  implementations in `commands/` own parsing and Rich presentation.
- `src/network_toolkit/api/` returns structured results to CLI and SDK
  callers. `config.py` owns the Pydantic models and configuration loading.
- `src/network_toolkit/device.py`, `session_pool.py`, and `transport/`
  handle sessions, native Scrapli CLI transport, and Paramiko SFTP.
- `src/network_toolkit/platforms/` and `builtin_sequences/` hold
  platform-specific operations and packaged YAML.
- `tests/`, `docs/`, and `scripts/` contain the existing tests,
  documentation, and development automation.

Follow existing typing, exception, and session lifecycle patterns. Keep
vendor-specific behavior in its existing layer. Use current APIs and carry
backward compatibility requirements only when explicitly requested. See
[CONTRIBUTING.md](https://github.com/narrowin/networka/blob/main/CONTRIBUTING.md)
for contribution and commit conventions.

## Building and releasing

For local distribution checks, use `uv build --no-sources` followed by
`uv run --locked twine check dist/*` on the resulting artifacts. Use the
clean installation check to verify package behavior from the working tree.

For an authorized release, first update the unreleased changelog on the
intended branch and start from a clean checkout. Run the pre-release
quality checks and dry run for the intended version.

```bash
./scripts/pre-release-check.sh
./scripts/release.sh --version 1.0.0 --dry-run
```

Pre-release verification records the commit checked. A real release updates
version and changelog metadata, commits those changes, and pushes the branch
and tag. GitHub Actions checks the release artifacts on Python 3.15 on
Ubuntu and macOS and routes stable and prerelease
publication to their respective indexes. For previous release evidence, see
[Networka release qualification](development/networka-release-qualification.md).

## Getting help

Use the GitHub issue template for bugs, questions, and feature requests.
Follow [SECURITY.md](https://github.com/narrowin/networka/blob/main/SECURITY.md)
for vulnerability reports.
