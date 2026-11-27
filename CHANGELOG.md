# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- Separate deliberate host silence and host power loss from failover measurements in lab reports and summaries, retaining every numerical limit and verdict check. Report MAC relearning and power recovery against their existing separate limits.
- Lead site power-loss reports with forwarding and failover on surviving streams, and show restart and rejoin after power returns separately.
- `nw test summary` highlights outages that exceed their configured limits before longer outages that remain within their limits.
- `nw test summary` counts a saved run whose starting state check did not pass, instead of exiting 2 because it has no traffic.

## [0.5.2] - 2026-11-27

### Added

- Power off several lab nodes together and measure streams to a fixed IP address, including VRRP addresses.
- Generate a lab results section with `nw test summary` from saved run evidence.

### Fixed

- Measure recovery deadlines from action dispatch and judge ping send pauses against each step's limit.
- Bound one-way cable cuts by their action markers and require delivered pings around the cut.
- Measure host silence and relearning from the filter action marker.

## [0.5.1] - 2026-11-26

### Added

- Extend `nw test run` and `nw test replay` for the Small MLAG lab. Lab plans can exercise traffic delay and loss, one-way calibration, silent LACP, abrupt CHR power loss, and active-backup host movement and silence. Saved action, recovery, capture, and host-table evidence lets replay evaluate these steps offline.

### Fixed

- Record how to restore lab state before starting fault actions so cleanup can recover from an interruption. Report cleanup failures in the run result.
- Mark traffic rows as unverified when a step stops early or the evidence cannot support a verdict. Keep measured bounds visible as diagnostics when available.

## [0.5.0] - 2026-11-26

### Added

- Run containerlab tests with `nw test run FILE... --lab DIR --save DIR`. Tests check device state before and after cable changes or RouterOS CHR reboots. They measure outages on named IPv4 ping streams and check switch logs against test- and step-level rules. A reboot step verifies a new boot and waits for lab state to recover.
- Replay lab evidence offline with `nw test replay DIR`. Replay rebuilds the Markdown report from saved test inputs, device observations, packet captures, logs, and action events, and checks the result against the saved JSON verdict. See the [lab test guide](docs/lab-tests.md) for the Small lab examples and evidence format.
- Check device state with `nw intent run FILE [--save DIR]` and replay saved readings with `nw intent replay DIR`. The Python API in `network_toolkit.intent` provides the same validation, collection, and replay, and `intent.parse_item` loads one check from a mapping. Checks return `pass`, `fail` or `error` with exit statuses 0, 1 or 2.
- Add vendor-neutral intent checks for bridge and spanning-tree state, MLAG, LACP, bond membership, host entries, interface state, and ping reachability. RouterOS checks consume native JSON. Linux bond checks consume iproute2 JSON. The [intent guide](docs/intent.md) describes the checks and shows how to add a platform.

### Changed

- The offline intent example uses the library check to replay one RouterOS evidence file per port with `--routeros-stp-port BRIDGE INTERFACE EVIDENCE_JSON`.

### Fixed

- `nw run` prints the command error before exiting 1 for a failed single command. Raw output is unchanged.
- LACP member checks fail when no partner is present. Linux LACP partner-system checks return `error` if the expected priority is unavailable in iproute2 JSON or the member is outside the active aggregator.

## [0.4.1] - 2026-11-25

### Added

- Replay native RouterOS JSON in the experimental offline intent example. Verify bridge-port forwarding from saved statistics and monitor replies, including results from the read-only Medium lab check on RouterOS CHR 7.26beta7.

## [0.4.0] - 2026-11-25

### Added

- Inspect the commands and source selected for a sequence with `nw info <sequence> --device <device>`. Packaged sequences are also discoverable without a local config.
- List active Scrapli definitions and their packaged or override source with `nw platforms list`. Use `nw platforms info` to inspect a definition, registered operations, and the selected sequence sources.
- Add an experimental offline example that compares intended interface and MLAG state against archived lab evidence.

### Changed

- Require Python 3.15 or later. Use one locked uv workflow for development and CI, and update libtmux to the 0.68 series.
- Align the installation, CLI, platform, results, and SDK guides with the current workflows.

### Fixed

- Resolve applicable sequences consistently across execution, diff, inspection, and completion. Keep an inline sequence on its owning device and reject inapplicable sequence names before connecting.
- Accept exact active Scrapli definition names for ad hoc targets and preserve explicit platform names in CSV inventory.
- Restore inherited CLI help, validate SSH CLI ports, and validate upload parallelism in the CLI and SDK.

### Removed

- Remove unused legacy transport code and the internal Textual interface. The `nw` CLI, Rich output, and Python SDK remain available.

## [0.3.0] - 2026-11-25

### Changed

- `nw run` on a group or a device list exits with code 1 when the command or sequence failed on any device. Single-device runs already did. Scripts that run groups now see device failures.
- RouterOS replies that start with `syntax error`, `bad command name`, `expected end of command`, `input does not match any value`, `failure:` or `no such item` count as failed commands in the CLI and the library.
- When a pooled library session loses its connection during a command, Networka closes the session, removes it from the pool and reports the error. It does not send the command again, because the device may already have run it. The next call opens a new session.
- Importing `network_toolkit` no longer configures logging in the calling program. Networka and Scrapli log records go only to the handlers the application sets up. Programs that relied on the default printing of these warnings need to configure logging, for example with `logging.basicConfig()`. The `nw` CLI still prints warnings to stderr.
- `NetworkaClient.run()` reuses the client's sequence manager instead of building a new one for each call.

### Added

- `general.ssh_known_hosts_file` sets the known-hosts file for CLI SSH sessions. The `system` transport always uses it and the `ssh2` transport uses it in strict mode. SFTP transfers still check `~/.ssh/known_hosts`.

### Fixed

- A failed sequence command keeps the outputs of the commands that ran before it in `DeviceSequenceResult.outputs`.
- Connection errors include the reason. A rejected login raises `DeviceAuthError`, a subclass of `DeviceConnectionError`. The device password is masked in the message and the logs.
- Command errors include the device's reply, for example `bad command name bogus (line 1 column 12)`.
- A new pooled session that cannot connect is connected once per call, with the configured `connection_retries`, instead of twice.
- Concurrent library calls to the same device open at most one pooled session. Calls to other devices do not wait.
- Containerlab `mikrotik_chr` nodes map to `mikrotik_routeros` with `platform_mapping: netmiko_to_networka`.
- Name clash errors between inventories name the `--inventory-prefer` option. The documentation no longer describes the unused `inventory.merge_mode` setting.

## [0.2.0] - 2026-11-24

### Changed

- Use Scrapli 2.0.4 for device CLI sessions. The `scrapli` distribution replaces the legacy driver in place during dependency resolution.
- Support OpenSSH, native SSH2, and Telnet for device CLI sessions. Keep Paramiko for SFTP.
- Update uv, CI, and tmux. Target Linux and Apple Silicon macOS.

### Added

- Read the optional Cisco IOS and IOS-XE enable secret from `NW_ENABLE_PASSWORD_<DEVICE>` or `NW_ENABLE_PASSWORD_DEFAULT`.

### Fixed

- Keep RouterOS replies aligned with their commands and collect monitoring output for every configured bridge.
- Verify SFTP host keys in strict mode, verify uploads to remote directories, and remove requested files through SFTP.
- Limit pooled retries to connection setup and restore output from backup summaries.
- Track restart replies before accepting a session disconnect.

## [0.1.13] - 2025-12-04

### Added
-

### Changed
-

### Fixed
-


## [0.1.13] - 2025-12-04

### Fixed

- Fixed tmux availability checking to verify binary existence before attempting libtmux import
- Fixed IP address resolution to properly pass platform/port/transport_type parameters
- Improved graceful fallback to sequential SSH when tmux is unavailable
- Resolved issue where IP-based device connections failed despite providing --platform flag

## [0.1.12] - 2025-10-30

### Added
-

### Changed
-

### Fixed
-


## [0.1.11] - 2025-10-27

### Added
-

### Changed
-

### Fixed
-


## [0.1.10] - 2025-09-01

### Added
-

### Changed
-

### Fixed
-


## [0.1.9] - 2025-08-29

### Added
-

### Changed
-

### Fixed
-


## [0.1.8] - 2025-08-29

### Added
-

### Changed
-

### Fixed
-


## [0.1.8] - 2025-08-29

### Added
-

### Changed
-

### Fixed
-


## [0.1.7] - 2025-08-28

### Added
-

### Changed
-

### Fixed
-


- Renamed project from "netkit" to "networka"
- Changed CLI command from "netkit" to "nw"
- Updated all documentation and examples to use new command name
- Maintained backward compatibility for environment variables (NETKIT\_\*)
- Maintained backward compatibility for config directory (~/.config/netkit/)

### Added

- Professional CI/CD pipeline with multi-platform testing (Linux, Windows, macOS)
- Automated PyPI publishing with trusted publishing
- Comprehensive security scanning and quality checks
- **Automatic .env file loading**: Added support for loading credentials from `.env` files automatically
  - Supports multiple .env file locations with proper precedence (environment variables > config dir .env > cwd .env)
  - No need to manually source .env files - they're loaded automatically when running commands
  - Updated documentation and examples to showcase new .env workflow
  - Maintains full backward compatibility with existing environment variable usage
- Shell completion for bash, fish, and zsh with new "nw" command
- Modern packaging standards with uv build system
- Automated release workflows with GitHub Actions
- Global `--version` flag to display version information
- CLI now properly handles top-level flags without requiring a subcommand

### Technical

- Enhanced pyproject.toml with modern Python packaging standards
- Multi-platform test matrix (Python 3.11, 3.12, 3.13)
- Security scanning with TruffleHog and Bandit
- Test coverage reporting with Codecov
- Proper artifact management and retention policies

### Fixed

- GitHub Actions CI test failure for version command support
