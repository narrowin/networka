# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

### Changed

## [Unreleased]

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
