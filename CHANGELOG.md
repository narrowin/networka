# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- Return exit status `1` when any resolved device fails during `nw run` on a group or device list. Keep the per-device results and summary.

### Removed

- Remove unused legacy transport code and the internal Textual interface. The `nw` CLI, Rich output, and Python SDK remain available.

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
