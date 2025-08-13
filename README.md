# Net-Worker (nw)

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

A powerful, modern CLI tool for **multi-vendor network automation**. Built with async/await support, type safety, and comprehensive results storage. Supports MikroTik RouterOS, Cisco IOS-XE/NX-OS, Arista EOS, Juniper JunOS, and more.

## ✨ Key Features

### 🌐 Multi-Vendor Support
- **MikroTik RouterOS**: Primary focus with comprehensive support
- **Cisco IOS-XE & NX-OS**: Enterprise switches and routers
- **Arista EOS**: Data center and campus networking
- **Juniper JunOS**: Enterprise routing and switching
- **Extensible Architecture**: Easy to add new vendors

### 🚀 Core Capabilities
- **Device Management**: Connect to and execute commands on network devices
- **Vendor-Aware Sequences**: Automatically uses correct commands for each vendor
- **Group Operations**: Execute commands across multiple devices concurrently
- **Results Storage**: Comprehensive, organized storage of command outputs
- **Security-First Design**: Environment variable credentials, secret detection, comprehensive protection
- **Type Safety**: Full type annotations and validation using Pydantic
- **Async Support**: Built with modern async/await patterns for performance

### Results Management
- **Individual Files**: Each command creates its own result file
- **Session Directories**: Organized by timestamp and command context
- **Multiple Formats**: Support for TXT, JSON, and YAML output formats
- **Device Organization**: Results grouped by device for easy navigation
- **Error Handling**: Separate error files for failed operations
- **Audit Trail**: Full command context preserved in every file

### Device Support
- **Multi-Vendor**: MikroTik, Cisco, Arista, Juniper support
- **Vendor-Specific Commands**: Automatically uses correct syntax per vendor
- **Connection Methods**: SSH transport with vendor-specific optimizations
- **Credential Management**: Device-specific and global credential support
- **Timeout Configuration**: Flexible timeout settings per device and vendor

## 🚀 Installation

### Prerequisites
- **Python 3.11+** - Required for modern type annotations and async features
- **SSH access** to target network devices
- **uv** (recommended) or pip for package management

### Install from GitHub Repository

#### Option 1: Direct Installation with pip
```bash
# Install latest from main branch
pip install git+https://github.com/narrowin/net-worker.git

# Install from specific version/tag
pip install git+https://github.com/narrowin/net-worker.git@v0.1.0

# Verify installation
nw --help
```

#### Option 2: Development Installation with uv (Recommended)
```bash
# Clone the repository
git clone https://github.com/narrowin/net-worker.git
cd net-worker

# Create virtual environment and install dependencies
uv sync

# Activate the environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify installation
nw --help
```

#### Option 3: Development Installation with pip
```bash
# Clone and install in editable mode
git clone https://github.com/narrowin/net-worker.git
cd net-worker
pip install -e .

# Or with development dependencies
pip install -e ".[dev]"
```


## Developers

This section is for contributors and maintainers working on the codebase.

- Tooling: uv (package manager), pytest, ruff, mypy
- Python: 3.11+ (type-safe, async/await)
- Style: Keep it simple and clear; follow patterns already in `src/network_toolkit`

Quick setup:

```bash
# Sync dev dependencies and lockfile environment
uv sync --dev

# Run quality gates locally
uv run ruff check .
uv run ruff format --check  # or format to apply changes
uv run mypy src/network_toolkit tests
uv run pytest -q
```

Tip: prefer adding or improving tests over manual terminal checks; the suite is extensive and async-ready.


## 🏗️ Build & Distribution System

Net-worker uses a modern, multi-layered build and release system that combines **Taskfile** (local development), **uv** (package management), and **GitHub Actions** (CI/CD) to ensure production-ready artifacts.

### 🔧 Build System Architecture

The build system consists of three integrated layers:

#### 1. **Taskfile.yml** - Local Development Orchestration
Task-based development workflow using [go-task](https://taskfile.dev/) for consistent local operations:

```bash
# Development workflow
task dev          # Complete development setup (install, lint, typecheck, test)
task build        # Build package locally with quality checks
task ci           # Run full CI checks locally
task release:dry  # Test release process without publishing

# Individual operations
task install      # Install dependencies with uv
task test:cov     # Run tests with coverage
task lint         # Code quality checks
task check        # Run all quality gates
```

#### 2. **uv** - Modern Python Package Management
Using [uv](https://github.com/astral-sh/uv) for fast, reliable dependency management and building:

```bash
# Core build commands (used by Taskfile and CI)
uv sync --all-extras --dev    # Install dependencies
uv build                      # Build wheel and sdist
uv run twine check dist/*     # Validate distributions
```

#### 3. **GitHub Actions** - Automated CI/CD
Three workflow pipelines handle different stages of the development lifecycle:

### 📋 Detailed Build Process

#### **Local Development Build** (`task build`)
Executes the comprehensive `scripts/build.sh`:

1. **Environment Setup**
   - Verify uv installation
   - Clean previous builds (`dist/`, `build/`, `*.egg-info/`)
   - Install dependencies with `uv sync --all-extras`

2. **Quality Assurance**
   - **Linting**: `uv run ruff check .`
   - **Formatting**: `uv run ruff format --check .`
   - **Type Checking**: `uv run mypy src/`
   - **Testing**: `uv run pytest --cov=network_toolkit --cov-report=term-missing`

3. **Package Building**
   - **Build**: `uv build` (creates wheel and sdist using hatchling)
   - **Validation**: `uv run twine check dist/*`
   - **Artifact Listing**: Shows build outputs and publishing instructions

```bash
# Execute complete build process
task build

# Output example:
# ✅ Build completed successfully!
# 📦 Build artifacts:
# -rw-r--r-- 1 user user 245678 net_worker-1.0.0-py3-none-any.whl
# -rw-r--r-- 1 user user 123456 net_worker-1.0.0.tar.gz
```

#### **Continuous Integration** (`.github/workflows/ci.yml`)
Triggered on pushes to `main`/`develop` and pull requests:

**Multi-Platform Testing Matrix**:
- **OS**: Ubuntu, Windows, macOS
- **Python**: 3.11, 3.12, 3.13
- **Total**: 9 test combinations

**CI Pipeline Stages**:
1. **Code Quality**
   ```bash
   uv run ruff check .              # Linting
   uv run ruff format --check .     # Format checking
   uv run mypy src/                 # Type checking
   ```

2. **Security Scanning**
   ```bash
   # Secret detection with TruffleHog
   trufflesecurity/trufflehog@main
   
   # Security linting with Bandit
   uv run bandit -r src/ -f json
   ```

3. **Testing with Coverage**
   ```bash
   uv run pytest --cov=network_toolkit --cov-report=xml --cov-report=term-missing
   # Uploads to Codecov for coverage tracking
   ```

4. **Build Verification** (on main branch)
   ```bash
   uv build                         # Create distributions
   uv run twine check dist/*        # Validate packages
   # Uploads artifacts for 7 days retention
   ```

#### **Installation Testing** (`.github/workflows/test-publish.yml`)
Automatic testing of GitHub installation methods on main branch changes:

```bash
# Triggered by:
# - Push to main branch
# - Changes to src/**, pyproject.toml
# - Manual workflow dispatch

# Process:
# Test direct Git installation
pip install git+https://github.com/narrowin/net-worker.git@main
nw --help  # Verify CLI works
```

#### **Production Release** (`.github/workflows/release.yml`)
Triggered by git tags (e.g., `git tag v1.0.0 && git push origin v1.0.0`):

**Release Pipeline**:
1. **Build & Test**
   ```bash
   uv build                        # Create distributions
   ls -la dist/                    # Show artifacts
   ```

2. **Multi-Platform Package Testing**
   - Install built wheel on Ubuntu, Windows, macOS
   - Test CLI functionality: `nw --help`
   - Verify import: `python -c "import network_toolkit"`

3. **GitHub Release Creation**
   - Extract changelog for version
   - Attach distribution files (wheel + source)
   - Generate installation instructions for multiple methods
   - Auto-mark pre-releases (alpha/beta/rc versions)

### 🎯 Build Artifacts

#### **What Gets Built**
Using hatchling backend with PEP 517 compliance:

- **Wheel (`.whl`)**: 
  - Fast installation format
  - Includes runtime YAML sequences (`network_toolkit/builtin_sequences/`)
  - Type information marker (`py.typed`)
  - Platform-independent Python 3.11+ compatible

- **Source Distribution (`.tar.gz`)**:
  - Complete source code
  - Documentation and helper scripts
  - Enables downstream rebuilds and customization

### 🎯 Build Artifacts

#### **What Gets Built**
Using hatchling backend with PEP 517 compliance:

- **Wheel (`.whl`)**: 
  - Fast installation format
  - Includes runtime YAML sequences (`network_toolkit/builtin_sequences/`)
  - Type information marker (`py.typed`)
  - Platform-independent Python 3.11+ compatible

- **Source Distribution (`.tar.gz`)**:
  - Complete source code
  - Documentation and helper scripts
  - Enables downstream rebuilds and customization

#### **Package Metadata** (from `pyproject.toml`)
```toml
[project]
name = "net-worker"
requires-python = ">=3.11"
dependencies = [
    "scrapli[paramiko,community]>=2023.7.30",
    "pydantic>=2.5.0",
    "typer>=0.12.0",
    "rich>=13.0.0",
    # ... additional deps
]

[project.scripts]
nw = "network_toolkit.cli:app"
```

### 🚀 Release Workflow

#### **Automated Release Process**
```bash
# 1. Local development and testing
task dev                            # Set up environment
# ... make changes ...
task ci                            # Run full CI locally

# 2. Create and push release tag
git tag v1.0.0
git push origin v1.0.0

# 3. GitHub Actions automatically:
# - Builds distributions
# - Tests on multiple platforms  
# - Creates GitHub release
# - Attaches wheel and source distributions
```

#### **Manual Release Process** (if needed)
```bash
# Build locally
task build

# Test locally
uv venv .venv-test
uv pip install --python .venv-test/bin/python dist/*.whl
.venv-test/bin/nw --help

# Create GitHub release manually
# 1. Go to https://github.com/narrowin/net-worker/releases/new
# 2. Upload files from dist/ directory
# 3. Add release notes
```

### 🔒 Security & Quality Assurance

#### **GitHub-Based Distribution**
- Secure release management through GitHub
- Package integrity verification
- Version-tagged releases with attached assets

#### **Quality Gates**
Every build must pass:
- ✅ Linting (ruff)
- ✅ Type checking (mypy)  
- ✅ Unit tests with coverage
- ✅ Security scans (bandit, trufflehog)
- ✅ Package validation

#### **Multi-Platform Validation**
Release builds are tested on:
- Ubuntu 22.04 (Linux)
- Windows Server 2022
- macOS 14 (Apple Silicon)

### 🛠️ Development Integration

#### **IDE Integration**
VS Code tasks (`.vscode/tasks.json`) integrate with Taskfile:
```json
{
    "label": "Build Package",
    "type": "shell", 
    "command": "task build",
    "group": "build"
}
```

#### **Pre-commit Hooks**
Automatic quality checks before commits:
```bash
# Setup (one time)
uv run pre-commit install

# Runs automatically on git commit:
# - ruff linting and formatting
# - mypy type checking  
# - secret detection
```

### 📈 Why This Architecture is Professional

1. **Reproducible Builds**: Lock files (`uv.lock`) ensure identical dependencies
2. **Fast Iteration**: Local `task` commands match CI exactly
3. **Security First**: Trusted publishing, secret scanning, dependency validation
4. **Multi-Platform**: Tested on major operating systems and Python versions
5. **Standards Compliance**: PEP 517 building, proper metadata, semantic versioning
6. **Comprehensive Testing**: Unit tests, integration tests, package installation tests
7. **Automated Quality**: No manual quality gate bypasses, consistent standards

This build system scales from single developer workflows to enterprise CI/CD while maintaining simplicity and reliability.

### 🚀 **Quick Testing Guide**

For the fastest way to test your build and handle common issues:

#### **1. Fix Code Quality Issues First** (30 seconds)
```bash
# Auto-fix most linting issues
task lint:fix

# Or manually:
uv run ruff check --fix .
uv run ruff format .
```

#### **2. Local Build Test** (1-2 minutes)
```bash
# Run complete local build with all checks
task build

# If it fails, run individual steps to isolate issues:
task lint       # Check remaining lint issues
task typecheck  # Check type issues  
task test       # Check failing tests
```

#### **3. Test GitHub Installation** (5 minutes)
```bash
# Option A: Automatic via push (recommended)
git add .
git commit -m "test: build pipeline"
git push origin main
# Check GitHub Actions for installation testing

# Option B: Manual GitHub installation test
pip install git+https://github.com/narrowin/net-worker.git@your-branch
nw --help
```

#### **4. Production Release** (When ready)
```bash
# Create release tag to trigger full pipeline
git tag v1.0.0
git push origin v1.0.0
# Automatically: builds, tests, creates GitHub release with assets
```

#### **Common Issues & Quick Fixes**
```bash
# Import issues (PLC0415): Move imports to top of file
# Unused variables (F401, ARG002): Remove or prefix with _
# Security warnings (S108): Use tempfile.mkdtemp() instead of /tmp
# Line length (E501): Break long lines

# Quick lint fix for most issues:
uv run ruff check --fix --unsafe-fixes .
```

**💡 Pro Tip**: The `task lint:fix` command handles 80% of common linting issues automatically!


## Configuration

The toolkit is configured via a single YAML file (`devices.yml`) and environment variables for secure credential management.

### 🔐 Security Setup (Required)

**Important**: For security, credentials are stored in environment variables, not in the configuration file.

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your actual credentials:
   ```bash
   # Default credentials
   NT_DEFAULT_USER=admin
   NT_DEFAULT_PASSWORD=your_secure_password

   # Device-specific overrides (optional)
   NT_SW_ACC1_PASSWORD=switch1_password
   NT_SW_DIST1_PASSWORD=distribution_password
   ```

3. Load environment variables before running:
   ```bash
   source .env
   # or set them in your shell profile
   ```

📖 **See [Environment Variables Guide](docs/environment-variables.md) for complete setup instructions.**

### 🔒 Security Features & Best Practices

**Enterprise-Grade Security**: This repository implements comprehensive security measures to protect your network credentials and infrastructure.

#### ✅ Built-in Security Features
- **Environment Variable Credentials**: All secrets stored in environment variables, never in code
- **Automatic Secret Detection**: CI/CD pipelines scan for accidentally committed secrets
- **Pre-commit Security Hooks**: Local validation before commits reach the repository
- **Comprehensive `.gitignore`**: Protects SSH keys, config backups, and sensitive files
- **Security Baseline**: Tracks known safe test data to reduce false positives

#### 🔍 Automated Secret Detection
```bash
# Test secret detection locally
pre-commit run detect-secrets --all-files

# Update baseline when adding legitimate test data
./scripts/update-secrets-baseline.sh
```

#### 📋 Security Checklist
- ✅ Never commit real passwords, API keys, or SSH keys
- ✅ Use environment variables for all credentials
- ✅ Rotate credentials regularly
- ✅ Use device-specific credentials when possible
- ✅ Keep firmware images and backups in protected directories
- ✅ Review security alerts in GitHub (Dependabot, CodeQL)

**Learn More**: See [SECURITY.md](SECURITY.md) for reporting vulnerabilities.

### Configuration File Example

Here's a minimal `devices.yml` configuration:

```yaml
# devices.yml
general:
  firmware_dir: "/home/user/mikrotik/routeros_images/"
  backup_dir: "./backups"
  logs_dir: "./logs"
  results_dir: "./results"

  # Connection settings (credentials come from environment)
  transport: "ssh"
  port: 22
  timeout: 30

  # Results storage
  store_results: false
  results_format: "txt"
  results_include_timestamp: true

devices:
  sw-acc1:
    host: "10.10.1.11"
    description: "Access Switch 1"
    device_type: "mikrotik_routeros"
    platform: "mipbsbe"
    tags: ["access", "floor1", "critical"]

  sw-dist1:
    host: "10.10.1.13"
    description: "Distribution Switch 1"
    device_type: "mikrotik_routeros"
    platform: "mipbsbe"
    tags: ["distribution", "core", "critical"]
    overrides:
      timeout: 60
      command_timeout: 120

device_groups:
  all_switches:
    description: "All network switches"
    members: ["sw-acc1", "sw-dist1"]

  critical_devices:
    description: "Critical infrastructure devices"
    match_tags: ["critical"]

global_command_sequences:
  health_check:
    description: "Basic health check for all devices"
    commands:
      - "/system/resource/print"
      - "/system/clock/print"
      - "/interface/print stats"
```

### Multi-Vendor Configuration Example

```yaml
# Multi-vendor devices with automatic command selection
devices:
  # MikroTik devices use RouterOS commands
  mikrotik-switch:
    host: "10.0.1.10"
    device_type: "mikrotik_routeros"
    description: "MikroTik Access Switch"
    tags: ["switch", "access", "mikrotik"]

  # Cisco devices use IOS-XE commands
  cisco-switch:
    host: "10.0.1.20"
    device_type: "cisco_iosxe"
    description: "Cisco Catalyst Switch"
    tags: ["switch", "core", "cisco"]

  # Arista devices use EOS commands
  arista-spine:
    host: "10.0.1.30"
    device_type: "arista_eos"
    description: "Arista Spine Switch"
    tags: ["switch", "spine", "arista"]

# Vendor-specific groups
device_groups:
  cisco_devices:
    description: "All Cisco devices"
    match_tags: ["cisco"]

  all_switches:
    description: "All switches (multi-vendor)"
    match_tags: ["switch"]
```

When you run `nw run all_switches system_info`, each device automatically gets the correct vendor-specific commands!

**Important**: All device credentials are now stored in environment variables for security!
  store_results: true
  results_format: "txt"
  results_include_timestamp: true

devices:
  my-router:
    host: "192.168.1.1"
    description: "Main Router"
    device_type: "mikrotik_routeros"
    platform: "mipbsbe"
    model: "RB5009UG+S+"
    location: "Server Room"

    # Connection settings (inherits from general if not specified)
    user: "admin"
    password: "mypassword"

    # Device-specific tags for grouping
    tags:
      - "core"
      - "critical"

    # Pre-defined command sequences
    command_sequences:
      health_check:
        - "/system/resource/print"
        - "/system/clock/print"
        - "/interface/print stats"

# Device groups based on tags or explicit membership
device_groups:
  critical_devices:
    description: "All critical infrastructure devices"
    match_tags:
      - "critical"

  all_routers:
    description: "All routers"
    members:
      - "my-router"

# Global command sequences available to all devices
global_command_sequences:
  basic_info:
    description: "Basic system information"
    commands:
      - "/system/resource/print"
      - "/system/routerboard/print"
      - "/system/clock/print"
```

### Configuration Validation

The toolkit uses Pydantic for strict configuration validation:

- **Required fields**: Host addresses and device names
- **Type checking**: All fields are validated for correct types
- **Default values**: Sensible defaults for optional settings
- **Error messages**: Clear validation errors with helpful suggestions

## Usage

### Basic Commands

```bash
# Test connectivity to a device
nw connect my-router

# Run a single command
nw run my-router "/system/resource/print"
# Open tmux with SSH panes (requires tmux, libtmux; sshpass for password auth)
nw ssh my-router --no-attach

See docs/tmux-ssh.md for details on layouts, sync, and authentication modes.

# Run a command sequence (via `run`)
nw run my-router health_check

# Run commands on a device group
nw group-run critical_devices "/system/resource/print"
```

### Advanced Operations

```bash
# Upload firmware
nw upload my-router firmware.npk

# Download configuration backup
nw download my-router config.backup

# Execute multiple commands with results storage
nw run my-router "/system/resource/print" "/interface/print" \
  --store-results --results-format json

# Run commands with custom timeout
nw run my-router "/system/backup/save" --timeout 120
```

### Working with Groups

```bash
# List all configured groups
nw groups

# Show group members
nw group-members critical_devices

# Run sequence on entire group (use `run` with sequence name)
nw run all_routers basic_info
```

## 📁 Project Structure

```
net-worker/
├── devices.yml                 # Main configuration file
├── pyproject.toml             # Python project configuration
├── README.md                  # This file
├── uv.lock                    # Dependency lock file
├── src/
│   └── network_toolkit/       # Main package
│       ├── __init__.py
│       ├── cli.py             # CLI interface (Typer-based)
│       ├── config.py          # Configuration models (Pydantic)
│       ├── device.py          # Device connection handling
│       ├── exceptions.py      # Custom exceptions
│       └── results.py         # Results storage
└── tests/                     # Test suite
    └── test_*.py
```

## 🛠️ Development

### Code Quality

The project maintains high code quality standards:

```bash
# Run linting
uv run ruff check

# Format code
uv run ruff format

# Type checking
uv run mypy src/

# Run tests
uv run pytest

# All checks at once
uv run ruff check && uv run ruff format && uv run mypy src/ && uv run pytest
```

### Adding New Features

1. **Fork and clone** the repository
2. **Create a feature branch**: `git checkout -b feature/awesome-feature`
3. **Make changes** following the existing patterns
4. **Add tests** for new functionality
5. **Update documentation** as needed
6. **Run quality checks** before committing
7. **Submit a pull request`

### Architecture Notes

- **Async-first**: All network operations use `async/await`
- **Type safety**: Full type annotations throughout
- **Pydantic models**: Configuration validation and data models
- **Scrapli**: Modern network automation library for device connections
- **Typer**: Modern CLI framework with excellent UX

## 📚 Command Reference

### Device Operations
- `nw connect <device>` - Test device connectivity
- `nw run <device> <command|sequence>` - Execute a raw command or a predefined sequence
- `nw upload <device> <file>` - Upload file to device
- `nw download <device> <file>` - Download file from device

### Group Operations
- `nw groups` - List all device groups
- `nw group-members <group>` - Show group membership
- `nw group-run <group> <command>` - Run command on group
- `nw run <group> <sequence>` - Run sequence on group

### Utility Commands
- `nw config validate` - Validate configuration file
- `nw config show` - Display current configuration
- `nw devices` - List all configured devices

## 🤝 Contributing

Contributions are welcome! Please read our contributing guidelines and code of conduct.

### Development Setup

```bash
# Fork the repo and clone your fork
git clone https://github.com/yourusername/net-worker.git
cd net-worker

# Setup development environment
uv sync --group dev

# Install pre-commit hooks
pre-commit install

# Make your changes and test them
uv run pytest
uv run ruff check
uv run mypy src/
```

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- **Scrapli** - Excellent network automation library
- **Pydantic** - Data validation and settings management
- **Typer** - Modern CLI framework
- **Rich** - Terminal formatting

## Support

- **Documentation**: See inline help with `nw --help`
- **Issues**: Report bugs and request features on GitHub
- **Discussions**: Join community discussions for help and ideas

---

*Built vibe coding with claude4 and with  passion️ for network engineers who love clean, modern Python*

---

## 🏗️ New Modular Architecture (Recommended)

The Net-Worker now supports a **new modular configuration architecture** that provides better organization, enhanced security, and simplified usage.

### New Configuration Structure
```
config/
├── config.yml      # General settings and defaults
├── devices.yml     # Device definitions
├── groups.yml      # Device group definitions
└── sequences.yml   # All command sequences
```

### Unified Command Interface
```bash
# One simple command pattern for everything:
nw run [device|group] [command|sequence] [options]

# Examples (auto-detects device vs group, command vs sequence):
nw run sw-acc1 health_check                    # Device + Sequence
nw run access_switches "/system/resource/print" # Group + Command
nw run critical_infrastructure security_audit   # Group + Sequence
```

### Key Benefits
- 🔐 **Enhanced Security**: Credentials via environment variables only
- 🎯 **Simplified Commands**: One unified interface instead of 8+ commands
- 🏷️ **Smart Grouping**: Tag-based automatic group membership
- 📁 **Better Organization**: Separate files for different concerns
- 🔄 **Backward Compatible**: Legacy format still supported

### Quick Start with New Architecture
```bash
# 1. Create new modular configuration structure
mkdir config
touch config/config.yml config/devices.yml config/groups.yml config/sequences.yml

# 2. Set up environment variables
export NT_DEFAULT_USER="admin"
export NT_DEFAULT_PASSWORD="your_secure_password"

# 3. Use simplified commands
nw run sw-acc1 health_check
nw run access_switches security_audit --store-results
```

### Migration Path
- ✅ **Current users**: Your `devices.yml` continues to work unchanged
- ✅ **New features**: Available only with new `config/` structure
- ✅ **Gradual migration**: Move at your own pace with full backward compatibility

---

## 📖 Legacy Documentation (Still Fully Supported)

# Install the package
pip install -e .
```

### Development Installation
```bash
# Clone and setup for development
git clone https://github.com/your-org/net-worker.git
cd net-worker

# Install with development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

## Quick Start

### 1. Multi-Vendor Configuration
Create a `devices.yml` configuration file:

```yaml
general:
  results_dir: "/home/user/network-results"
  store_results: true
  results_format: "txt"

devices:
  # MikroTik device
  mikrotik-sw1:
    host: "192.168.1.10"
    device_type: "mikrotik_routeros"
    description: "MikroTik Switch"
    tags: ["switch", "office", "mikrotik"]

  # Cisco device
  cisco-sw1:
    host: "192.168.1.20"
    device_type: "cisco_iosxe"
    description: "Cisco Switch"
    tags: ["switch", "office", "cisco"]

device_groups:
  office_switches:
    description: "All office switches"
    match_tags: ["office"]
```

### 2. Multi-Vendor Usage Examples
```bash
# List all configured devices (shows vendor types)
nw list-devices

# Execute vendor-specific commands automatically
nw run mikrotik-sw1 system_info  # Uses: /system/identity/print, etc.
nw run cisco-sw1 system_info     # Uses: show version, show inventory, etc.

# Run sequences on mixed-vendor groups (auto-selects correct commands)
nw run office_switches health_check

# List available sequences by vendor
nw list-sequences --vendor mikrotik_routeros
nw list-sequences --vendor cisco_iosxe
nw run office_switches health_check

# Store results automatically
nw run office_switches health_check --store-results
```

## Usage Guide

### Device Operations

#### Single Device Commands
```bash
# Basic command execution
nw run DEVICE_NAME "COMMAND"

# Examples
nw run sw-office1 "/system/resource/print"
nw run sw-office1 "/interface/print" --verbose
nw run sw-office1 "/export compact" --store-results
```

#### Command Sequences
```bash
# Run predefined sequence
nw run DEVICE_NAME SEQUENCE_NAME

# Or use run with a sequence name
nw run DEVICE_NAME SEQUENCE_NAME

# Examples
nw run sw-office1 health_check
nw run office_switches health_check  # Run sequence on a group
```

### Group Operations

#### Group Commands
```bash
# Run command on all devices in group
nw group-run GROUP_NAME "COMMAND"

# Examples
nw group-run office_switches "/system/clock/print"
nw group-run critical_devices "/system/resource/print"
```

#### Group Sequences
```bash
# Run sequence on all devices in group
nw run GROUP_NAME SEQUENCE_NAME

# Examples
nw run office_switches health_check
nw run all_switches security_audit --store-results
```

### Information Commands

```bash
# List devices and groups
nw list-devices
nw list-groups
nw list-global-sequences

# Device information
nw info DEVICE_NAME
nw list-sequences DEVICE_NAME

# Configuration validation
nw config-validate
nw config-validate --verbose
```

## Results Storage

### Directory Structure
When `--store-results` is used, results are organized as follows:

```
/home/user/network-results/
├── 20250115_143022_run_office_switches_health_check/
│   ├── GROUP_SUMMARY_office_switches_health_check.txt
│   ├── sw-office1/
│   │   ├── 00_sequence_summary_health_check.txt
│   │   ├── 01_system_resource_print.txt
│   │   ├── 02_system_clock_print.txt
│   │   └── 03_interface_print_stats.txt
│   └── sw-office2/
│       ├── 00_sequence_summary_health_check.txt
│       ├── 01_system_resource_print.txt
│       └── ERROR_health_check.txt  # If command failed
```

## Layered Sequences (Built-in, Repo, User)

Net-worker discovers sequences from multiple layers with simple overrides:

- Built-in defaults shipped with net-worker (no setup)
- Repo-provided vendor files in `config/sequences/<vendor>/*.yml`
- User-defined files in `~/.config/nw/sequences/<vendor>/*.yml` (highest priority)

You can list merged sequences by vendor:

```bash
nw list-sequences --vendor mikrotik_routeros
```

Add a user sequence quickly:

```bash
mkdir -p ~/.config/nw/sequences/mikrotik_routeros
printf "sequences:\n  my_quick_diag:\n    description: Quick diagnostics\n    category: troubleshooting\n    timeout: 30\n    commands:\n      - /system/resource/print\n      - /interface/print brief\n" > ~/.config/nw/sequences/mikrotik_routeros/custom.yml
```

Then run it:

```bash
nw run DEVICE_NAME my_quick_diag
```

See more examples in `docs/examples/user_sequences/`.

### File Formats

#### Text Format (Default)
```txt
# Net-Worker Results
# Generated: 2025-01-15T14:30:22+00:00
# Device: sw-office1
# NW Command: run sw-office1 health_check

Command: /system/resource/print
================================================================================

uptime: 2w3d6h15m40s
version: 7.8 (stable)
...
```

#### JSON Format
```json
{
  "timestamp": "2025-01-15T14:30:22+00:00",
  "device_name": "sw-office1",
  "command": "/system/resource/print",
  "output": "uptime: 2w3d6h15m40s...",
  "nw_command": "run sw-office1 health_check"
}
```

### Storage Options
```bash
# Enable results storage
--store-results

# Custom results directory
--results-dir /path/to/custom/results

# Combine with any command
nw run sw-office1 "/system/clock/print" --store-results --results-dir ./audit-results
```

## Configuration

### Configuration File Structure

```yaml
general:
  # Directory paths
  firmware_dir: "/path/to/firmware"
  backup_dir: "./backups"
  results_dir: "/path/to/results"

  # Connection settings
  default_user: "admin"
  default_password: "password"
  transport: "ssh"  # ssh or telnet
  port: 22
  timeout: 30

  # Results storage
  store_results: false
  results_format: "txt"  # txt, json, yaml
  results_include_timestamp: true
  results_include_command: true

devices:
  device_name:
    host: "IP_ADDRESS"
    description: "Device description"
    device_type: "mikrotik_routeros"
    tags: ["tag1", "tag2"]

    # Device-specific credentials (optional)
    user: "device_admin"
    password: "device_password"

    # Connection overrides (optional)
    overrides:
      timeout: 60
      command_timeout: 120

device_groups:
  group_name:
    description: "Group description"
    match_tags: ["tag1", "tag2"]  # Include devices with these tags
    # OR
    members: ["device1", "device2"]  # Explicit device list

global_command_sequences:
  sequence_name:
    description: "Sequence description"
    commands:
      - "/command/one"
      - "/command/two"
```

### Environment Variables

```bash
# Override configuration file location
export NW_CONFIG=/path/to/devices.yml

# Override default results directory
export NW_RESULTS_DIR=/path/to/results

# Enable debug logging
export NW_LOG_LEVEL=DEBUG
```

## Development

### Setting Up Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/net-worker.git
cd net-worker

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Code Quality Tools

```bash
# Type checking
mypy src/

# Code formatting
black src/
isort src/

# Linting
ruff check src/

# Testing
pytest tests/

# All quality checks
pre-commit run --all-files
```

### Project Structure

```
network-deploy-and-test/
├── src/network_toolkit/
│   ├── __init__.py
│   ├── cli.py              # CLI interface and commands
│   ├── config_new.py       # Configuration management
│   ├── device.py          # Device connection and execution
│   ├── exceptions.py      # Custom exceptions
│   └── results_new.py     # Results storage management
├── tests/                 # Test suite
├── docs/                  # Documentation
├── pyproject.toml        # Project configuration
└── README.md
```

### Adding New Features

1. **New Commands**: Add to `cli.py` using Typer decorators
2. **Device Support**: Extend `device.py` for new platforms
3. **Configuration**: Update Pydantic models in `config_new.py`
4. **Results Formats**: Extend `results_new.py` for new output formats

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=network_toolkit

# Run specific test file
pytest tests/test_cli.py

# Run with verbose output
pytest -v
```

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Quick Contribution Steps

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest`)
6. Run code quality checks (`pre-commit run --all-files`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

### Code Standards

- **Type Hints**: All functions must have type annotations
- **Documentation**: Docstrings for all public functions
- **Testing**: Tests required for new features
- **Formatting**: Code must pass `black`, `isort`, and `ruff` checks

## Examples

### Common Use Cases

#### Daily Health Checks
```bash
# Check all critical devices
nw run critical_devices health_check --store-results

# Comprehensive system audit
nw run all_switches security_audit --store-results --results-dir ./audit-$(date +%Y%m%d)
```

#### Configuration Management
```bash
# Export configurations
nw group-run all_switches "/export compact" --store-results

# Check system resources
nw group-run all_switches "/system/resource/print" --store-results
```

#### Troubleshooting
```bash
# Check interface status
nw run problematic-switch interface_status --verbose

# Get detailed logs
nw run problematic-switch "/log/print last=100 where topics~\"error\"" --store-results
```

#### Bulk Operations
```bash
# Update system time on all devices
nw group-run all_switches "/system/ntp/client/set enabled=yes server-dns-names=pool.ntp.org"

# Check firmware versions
nw group-run all_switches "/system/routerboard/print" --store-results
```

## Troubleshooting

### Common Issues

#### Connection Problems
```bash
# Test connectivity
ping DEVICE_IP

# Check SSH access
ssh admin@DEVICE_IP

# Verify credentials in config
nw info DEVICE_NAME
```

#### Configuration Issues
```bash
# Validate configuration
nw config-validate --verbose

# Check device groups
nw list-groups

# Verify sequences
nw list-global-sequences
```

#### Results Storage Issues
```bash
# Check directory permissions
ls -la /path/to/results/

# Test with custom directory
nw run DEVICE "/system/clock/print" --store-results --results-dir ./test-results
```

### Debug Mode
```bash
# Enable verbose logging
nw --verbose COMMAND

# Enable debug logging
export NW_LOG_LEVEL=DEBUG
nw COMMAND
```

## 📚 Documentation

- **[Multi-Vendor Support](docs/multi-vendor-support.md)** - Comprehensive guide to using multiple network vendors
- **[Environment Variables](docs/environment-variables.md)** - Security credential management
- **[File Upload Guide](docs/file_upload.md)** - Firmware and configuration file management

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Scrapli](https://github.com/carlmontanari/scrapli) - Network device connections
- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Rich](https://github.com/Textualize/rich) - Terminal formatting

## Support

- **Documentation**: [https://net-worker.readthedocs.io](https://net-worker.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/your-org/net-worker/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/net-worker/discussions)

---

<p align="center">
  <strong>Built with care for network engineers</strong>
</p>
