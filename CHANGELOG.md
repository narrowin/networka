# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
