# Networka upgrade plan

Networka 0.2.0 combines the infrastructure refresh with Scrapli 2 as the sole CLI driver. The branch names and release order below record the earlier staging plan.

The [final release qualification](networka-release-qualification.md) records the follow-up fixes and OrbStack checks.

The [upgrade report](networka-upgrade-report-2026-11-24.md) records the dependency trials, alternatives, and compatibility risks. Each stage below has a separate acceptance check.

1. **Repair the published line.** Prepare 0.1.14 from the 0.1.13 tag. Constrain the legacy driver and tmux API, correct stable and prerelease routing, and install the resulting wheel and sdist in fresh environments.
2. **Refresh the maintained line.** Unify uv, run the actual Python matrix, upgrade the lock and developer tools, modernize tmux, restore the typing marker, and repair the existing inventory and lab checks. Keep the legacy transport available on this line. Verify the CLI, SDK, existing suite, docs, types, and built packages.
3. **Build the Scrapli 2 candidate.** Use a separate branch and environment for the native driver. Port construction, command and confirmation handling, SSH settings, timeouts, and session lifecycle. Check wheel installation, available definitions, and existing CLI and SDK behavior.
4. **Review release readiness.** Compare read-only command results on approved lab devices, record uncovered platforms and operations, and retain the compatibility release for rollback. Tagging, pushing, publishing, and device changes require operator approval.

## Implementation and local qualification, 24 November 2026

All three versions are local branches. The checked-out development branch is `codex/networka-refresh`. The 0.1.14 patch starts from the published v0.1.13 tag. The native candidate builds on the maintained refresh.

| Local branch and package | Changes | Local acceptance results on Apple Silicon |
| --- | --- | --- |
| `codex/networka-0.1.14` · 0.1.14 | Bound the released API to legacy Scrapli 2026.2.20, Paramiko 3.x and libtmux 0.46.2. Fixed TestPyPI/PyPI routing and artifact checks. | Python 3.13 had 891 passing tests and 39 skips. The wheel and source archive each installed and started in their own environment. |
| `codex/networka-refresh` · 0.2.0.dev0 | Pinned uv 0.13.9, refreshed dependencies and CI, restored the SDK typing marker, migrated tmux, fixed backup summaries, and corrected inventory validation. | Each interpreter from Python 3.11 through 3.15 had 1,123 passing tests and 42 skips. Ruff, mypy, strict docs, and creation of two panes on an isolated local tmux server passed. |
| `codex/networka-scrapli2` · 0.3.0.dev0 | Ported the synchronous adapter to Scrapli 2.0.4. Mapped SSH and Telnet options, deadlines and RouterOS console settings, serialized session access, and handled interrupted confirmations. Paramiko 5 handles SFTP independently. | Each interpreter from Python 3.11 through 3.15 had 1,123 passing tests and 42 skips. The native driver opened a local shell, returned exact command output, answered a literal confirmation and closed the session. Construction succeeded for all registry device types plus Linux and generic. |

Each of the six final archives was installed in its own Python 3.13 environment. CLI help and version ran outside the source tree. Both development builds also exposed the SDK, the typing marker, and the built-in RouterOS sequences. The release workflow checks the artifacts before publishing and creates the GitHub release after publication succeeds.

The matrix used the existing suite with the network marker excluded. Some tests are already skipped for legacy CLI signatures and missing operator inventories. The local shell exercises the native library and pseudo-terminal. It does not exercise SSH authentication, SFTP, RouterOS echo and paging, or Cisco privilege transitions on equipment.

### Running the local builds

From the repository root with uv 0.13.9, use `uv sync --locked --all-extras` and `uv run nw --version` for the checked-out development branch. To compare packages without switching branches or installing over an operator's CLI, create an environment for each wheel. For example:

```bash
uv venv --python 3.13 .venv-rebirth-preview
uv pip install --python .venv-rebirth-preview/bin/python dist/rebirth/scrapli2/networka-0.3.0.dev0-py3-none-any.whl
.venv-rebirth-preview/bin/nw --version
```

The local artifacts are under `dist/rebirth/patch/`, `dist/rebirth/refresh/`, and `dist/rebirth/scrapli2/`. Rebuild any of them from its branch with `uv build --no-sources`.

### Release order and remaining decisions

1. **Ship the compatibility fix first.** Review the 0.1.14 branch and confirm PyPI/TestPyPI trusted publisher configuration for the repository workflow and GitHub environments. After operator approval, run the pre-release checks and select the patch branch with `scripts/release.sh --branch codex/networka-0.1.14 --version 0.1.14`. The helper supports a dry run. Package publication and hosted CI still await operator action.
2. **Adopt the refresh for ongoing development.** Keep the Python matrix and the two fresh artifact installs on release changes. Restore the existing skipped upload cases against today's CLI signature, starting with the tests that currently accept both success and failure. The skips reduce the transfer coverage of a green suite.
3. **Qualify Scrapli 2 before promoting it.** Compare read-only output with the refresh on RouterOS and Cisco IOS/IOS-XE, then qualify file transfer, confirmations, Linux wheels, and WSL2. The upstream release supplies macOS arm64 and Linux x86-64/arm64 wheels. Keep the compatibility line available to Intel macOS and native Windows users. For deployments that require strict SSH trust, qualify the separate SFTP path as well. [Upstream release files](https://pypi.org/project/scrapli2/2.0.4/#files)
4. **Schedule the documentation migration separately.** Compare the generated CLI and SDK pages with Zensical while the current strict build still passes. Material for MkDocs lists 5 May 2027 as the end of maintenance. [Material maintenance notice](https://squidfunk.github.io/mkdocs-material/) · [Zensical migration guide](https://zensical.org/docs/compatibility/mkdocs/migration/)
