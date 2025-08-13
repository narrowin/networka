# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed project from "netkit" to "net-worker"
- Changed CLI command from "netkit" to "nw"
- Updated all documentation and examples to use new command name
- Maintained backward compatibility for environment variables (NETKIT_*)
- Maintained backward compatibility for config directory (~/.config/netkit/)

### Added
- Professional CI/CD pipeline with multi-platform testing (Linux, Windows, macOS)
- Automated PyPI publishing with trusted publishing
- Comprehensive security scanning and quality checks
- Shell completion for bash, fish, and zsh with new "nw" command
- Modern packaging standards with uv build system
- Automated release workflows with GitHub Actions

### Technical
- Enhanced pyproject.toml with modern Python packaging standards
- Multi-platform test matrix (Python 3.11, 3.12, 3.13)
- Security scanning with TruffleHog and Bandit
- Test coverage reporting with Codecov
- Proper artifact management and retention policies
