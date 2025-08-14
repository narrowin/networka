<h2 align="center">
    Net-Worker (nw)
    <br>
    Modern CLI tool for multi-vendor network automation
</h2>

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/narrowin/net-worker)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

</div>

Net-Worker is a modern async CLI tool for automating network devices across multiple vendors. Built with async/await patterns for high performance and reliability. Designed for network engineers who want fast, scalable automation with full cross-platform support.

**Cross-Platform Support**: Runs on Linux, macOS, and Windows with Python

## Getting started

- [Installation instructions →](#installation)
- [Platform compatibility →](docs/platform-compatibility.md)
- [CLI overview →](#cli-overview)
- [Quick start guide →](#quick-start)
- [Configuration →](#configuration)
- [Examples →](#examples)

## Features

- **Cross-platform**: Full support for Linux, macOS, and Windows
- **Multi-vendor support**: MikroTik RouterOS, Cisco IOS-XE/NX-OS, Arista EOS, Juniper JunOS, and more
- **Modern async architecture**: Built with async/await for high performance
- **Device/Group operations**: Execute commands across devices or groups concurrently
- **Command sequences**: Vendor-aware predefined command sets
- **Results management**: Organized storage with multiple output formats
- **Type safety**: Full type checking with mypy for reliability

## Installation

### System Requirements
- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.11, 3.12, or 3.13
- **Network Access**: SSH connectivity to target devices
- **Package Manager**: uv (recommended) or pip

### Quick Install

```bash
# Install from GitHub (latest)
pip install git+https://github.com/narrowin/net-worker.git

# Verify installation works
nw --help
```

### Platform-Specific Notes

**Linux/macOS**: No additional dependencies required

**Windows**: All dependencies include pre-built wheels for seamless installation

### Development Installation

```bash
# Clone repository
git clone https://github.com/narrowin/net-worker.git
cd net-worker

# Install with uv (recommended)
uv sync --all-extras

# Or with pip
pip install -e ".[dev]"

# Verify installation
nw --help
```

### Alternative Installation Methods

```bash
# Install specific version
pip install git+https://github.com/narrowin/net-worker.git@v0.1.0

# Install from local clone
git clone https://github.com/narrowin/net-worker.git
cd net-worker
uv pip install .
```

## Quick Start

Get up and running in 3 steps:

```bash
# 1. Set up credentials (automatically loaded)
cp .env.example .env
nano .env  # Add your actual device credentials

# 2. Configure your devices
nano config/devices/devices.yml

# 3. Start managing your network
nw run sw-acc1 "/system/identity/print"
nw run office_switches system_info
```

## CLI overview

```
Usage: nw [OPTIONS] COMMAND [ARGS]...

🌐 Network Worker (nw)

A powerful multi-vendor CLI tool for automating network devices based on ssh protocol.
Built with async/await support and type safety in mind.

📋 QUICK START:
  nw run sw-acc1 '/system/clock/print'  # Execute command
  nw run office_switches system_info    # Run sequence on group

📖 For detailed help on any command: nw <command> --help
📁 Default config directory: config/ (use --config to override)

╭─ Options ──────────────────────────────────────────────────────────────────╮
│ --help  -h        Show this message and exit.                              │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ─────────────────────────────────────────────────────────────────╮
│ ssh                  Open tmux with SSH panes for a device or group.       │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Info & Configuration ─────────────────────────────────────────────────────╮
│ info                 Show comprehensive device information and connection  │
│                      status.                                               │
│ list-devices         List all configured network devices.                  │
│ list-groups          List all configured device groups and their members.  │
│ list-sequences       List all available command sequences, optionally      │
│                      filtered by vendor or category.                       │
│ config-validate      Validate the configuration file and show any issues.  │
│ diff                 Diff config, a command, or a sequence.               │
╰────────────────────────────────────────────────────────────────────────────╯
╭─ Executing Operations ─────────────────────────────────────────────────────╮
│ run                  Execute a single command or a sequence on a device or │
│                      a group.                                              │
│ upload               Upload a file to a device or to all devices in a      │
│                      group.                                                │
│ download             Download a file from a device or all devices in a     │
│                      group.                                                │
│ config-backup        Create configuration backup                           │
│ backup               Create device backup                                  │
│ firmware-upgrade     Upload firmware package and reboot device to apply    │
│                      it.                                                   │
│ firmware-downgrade   Upload older firmware package, schedule downgrade,    │
│                      and reboot to apply.                                  │
│ bios-upgrade         Upgrade RouterBOARD (RouterBOOT/BIOS) and reboot to   │
│                      apply.                                                │
╰────────────────────────────────────────────────────────────────────────────╯
```

## Quick start

### 1. Set up credentials

**Option A: Use .env file (Recommended)**
```bash
# Copy and edit the example file
cp .env.example .env
nano .env  # Add your actual credentials
```

**Option B: Export environment variables**
```bash
# Set environment variables for security
export NW_USER_DEFAULT="admin"
export NW_PASSWORD_DEFAULT="your_secure_password"  # pragma: allowlist secret

# Device-specific overrides (optional)
export NW_PASSWORD_SW_ACC1="switch1_password"  # pragma: allowlist secret
```

### 2. Create configuration files

Create `config/config.yml` for general settings:

```yaml
general:
  results_dir: "./results"
  timeout: 30
```

Create `config/devices/devices.yml` for your devices:

```yaml
devices:
  sw-acc1:
    host: "10.10.1.11"
    device_type: "mikrotik_routeros"
    description: "Access Switch 1"
    tags: ["access", "critical"]

  cisco-sw1:
    host: "10.10.1.20"
    device_type: "cisco_iosxe"
    description: "Cisco Switch"
    tags: ["core", "cisco"]
```

Create `config/groups/groups.yml` for device groups:

```yaml
groups:
  all_switches:
    description: "All network switches"
    members: ["sw-acc1", "cisco-sw1"]
```

### 3. Run your first commands

```bash
# Test connectivity
nw run sw-acc1 "/system/identity/print"

# Execute on device group
nw run all_switches "show version"

# Store results automatically
nw run sw-acc1 health_check --store-results
```

## Configuration

Net-Worker uses a flexible configuration system supporting both YAML and CSV formats, with hierarchical loading from directories and subdirectories.

### Enhanced Configuration Features

- **Multiple formats**: YAML and CSV files supported
- **Subdirectory organization**: Split configurations across directories
- **Hierarchical loading**: More specific configs override general ones
- **Mixed format support**: Use both YAML and CSV in the same project

### Environment variables

**Automatic .env Loading** - The toolkit automatically loads credentials from `.env` files:

```bash
# Copy the example and edit with your credentials
cp .env.example .env

# Credentials are loaded automatically when you run commands
nw run system_info sw-acc1
```

**Manual Environment Variables** - You can also set them manually:

```bash
# Default credentials (required)
export NW_USER_DEFAULT="admin"
export NW_PASSWORD_DEFAULT="your_secure_password"  # pragma: allowlist secret

# Device-specific overrides (optional)
export NW_PASSWORD_SW_ACC1="switch1_password"  # pragma: allowlist secret
```

### Configuration Structure

#### Modular Directory Structure
```
config/
├── config.yml              # Main configuration (required)
├── devices/                # Device definitions (all files here)
│   ├── devices.yml         # Main devices file
│   ├── devices.csv         # CSV format devices
│   ├── production.yml      # YAML format devices
│   └── customer-a.yml      # Customer-specific devices
├── groups/                 # Group definitions (all files here)
│   ├── groups.yml          # Main groups file
│   ├── groups.csv          # CSV format groups
│   └── production.yml      # YAML format groups
├── sequences/              # Sequence definitions (all files here)
│   ├── sequences.yml       # Main sequences file
│   ├── sequences.csv       # CSV format sequences
│   ├── advanced.yml        # YAML format sequences
│   └── vendor_sequences/   # Vendor-specific sequences
└── examples/               # Templates and examples
    ├── devices/
    ├── groups/
    └── sequences/
```

#### CSV Format Reference

**Devices CSV Headers:**
```csv
name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Lab Switch,mipsbe,CRS326,Lab,switch;access;lab
```

**Groups CSV Headers:**
```csv
name,description,members,match_tags
lab_devices,Lab environment,sw-01;sw-02,lab;test
```

**Sequences CSV Headers:**
```csv
name,description,commands,tags
system_info,Get system info,/system/identity/print;/system/clock/print,system;info
```

### Configuration Structure

#### Modular Directory Structure
```
config/
├── config.yml              # Main configuration (required)
├── devices/                # Device definitions (all files here)
│   ├── devices.yml         # Main devices file
│   ├── devices.csv         # CSV format devices
│   ├── production.yml      # YAML format devices
│   └── customer-a.yml      # Customer-specific devices
├── groups/                 # Group definitions (all files here)
│   ├── groups.yml          # Main groups file
│   ├── groups.csv          # CSV format groups
│   └── production.yml      # YAML format groups
├── sequences/              # Sequence definitions (all files here)
│   ├── sequences.yml       # Main sequences file
│   ├── sequences.csv       # CSV format sequences
│   ├── advanced.yml        # YAML format sequences
│   └── vendor_sequences/   # Vendor-specific sequences
└── examples/               # Templates and examples
    ├── devices/
    ├── groups/
    └── sequences/
```

#### CSV Format Reference

**Devices CSV Headers:**
```csv
name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Lab Switch,mipsbe,CRS326,Lab,switch;access;lab
```

**Groups CSV Headers:**
```csv
name,description,members,match_tags
lab_devices,Lab environment,sw-01;sw-02,lab;test
```

**Sequences CSV Headers:**
```csv
name,description,commands,tags
system_info,Get system info,/system/identity/print;/system/clock/print,system;info
```

### Configuration file structure

**Main Configuration (`config/config.yml`):**
```yaml
general:
  results_dir: "./results"
  timeout: 30
  output_mode: "dark"  # default, light, dark, no-color, raw
```

**Device Configuration (`config/devices/*.yml`):**
```yaml
devices:
  device_name:
    host: "IP_ADDRESS"
    device_type: "mikrotik_routeros"  # or cisco_iosxe, arista_eos, juniper_junos
    description: "Device description"
    tags: ["tag1", "tag2"]
```

**Group Configuration (`config/groups/*.yml`):**
```yaml
groups:
  group_name:
    description: "Group description"
    match_tags: ["tag1"]  # Include devices with these tags
    # OR
    members: ["device1", "device2"]  # Explicit device list
```

**Sequence Configuration (`config/sequences/*.yml`):**
```yaml
sequences:
  sequence_name:
    description: "Sequence description"
    commands:
      - "/system/identity/print"
      - "/system/clock/print"
    tags: ["system", "info"]
```

### Loading Priority

Configuration files are loaded from their respective subdirectories. All files in each subdirectory are combined (later files override earlier ones):

1. **Device files**: All files in `config/devices/` (*.yml, *.yaml, *.csv)
2. **Group files**: All files in `config/groups/` (*.yml, *.yaml, *.csv)
3. **Sequence files**: All files in `config/sequences/` (*.yml, *.yaml, *.csv)

Within each directory, files are loaded alphabetically, so later files can override earlier ones.

### Getting Started

1. **Copy examples**: Start with the templates in `config/examples/`
2. **Create your configs**: Place your configurations in the appropriate subdirectories:
   - `config/devices/` for device definitions
   - `config/groups/` for group definitions
   - `config/sequences/` for sequence definitions
3. **Mix formats**: Use YAML for complex configs and CSV for bulk data
4. **Organize by purpose**: Create multiple files organized by site, customer, or environment

See `config/examples/` for detailed examples and migration guides.

### Output modes

Control colors and formatting with the `output_mode` setting:

```yaml
general:
  output_mode: "dark"  # default, light, dark, no-color, raw
```

**Modes:**
- `default` - Rich's built-in styling (adapts to terminal)
- `light` - Dark colors optimized for light terminal themes
- `dark` - Bright colors optimized for dark terminal themes
- `no-color` - Structured output without colors (accessibility)
- `raw` - Machine-readable format for scripts/automation

**Override precedence:**
1. CLI flag: `nw info device1 --output-mode raw`
2. Environment: `export NW_OUTPUT_MODE=light`
3. Config file: `general.output_mode`

## Examples

### Single device operations

```bash
# Execute a command on a device
nw run sw-acc1 "/system/resource/print"

# Run a predefined sequence
nw run sw-acc1 health_check

# Upload firmware file
nw upload sw-acc1 firmware.npk

# Download configuration backup
nw download sw-acc1 config.backup
```

### Multi-vendor automation

```bash
# Automatically uses correct vendor commands
nw run mikrotik-sw1 system_info    # Uses RouterOS commands
nw run cisco-sw1 system_info       # Uses IOS-XE commands
nw run arista-sw1 system_info      # Uses EOS commands

# Run on mixed-vendor groups
nw run all_switches health_check   # Each device gets vendor-specific commands
```

### Group operations

```bash
# Execute command on device group
nw run access_switches "/interface/print stats"

# Run sequence on entire group with results storage
nw run critical_devices security_audit --store-results
```

### Results management

```bash
# Store results with timestamps
nw run sw-acc1 health_check --store-results

# Custom results directory
nw run sw-acc1 diagnostic --results-dir ./maintenance-2025-08

# Different output formats
nw run sw-acc1 system_info --store-results --results-format json
```

## Community & support

- Visit our [documentation](docs/) for detailed guides and examples
- Create [GitHub Issues](https://github.com/narrowin/net-worker/issues) for bug reports and feature requests
- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Check [SECURITY.md](SECURITY.md) for security policy and reporting vulnerabilities

## Contributing

Have a look through existing [Issues](https://github.com/narrowin/net-worker/issues) and [Pull Requests](https://github.com/narrowin/net-worker/pulls) that you could help with. If you'd like to request a feature or report a bug, please create a GitHub Issue using one of the templates provided.

[See contribution guide →](CONTRIBUTING.md)

## Documentation

- [Platform Compatibility](docs/platform-compatibility.md) - Cross-platform support details
- [Development Guide](docs/development.md) - Contributing and extending the toolkit
- [Multi-Vendor Support](docs/multi-vendor-support.md) - Using multiple network vendors
- [Environment Variables](docs/environment-variables.md) - Secure credential management
- [File Upload Guide](docs/file_upload.md) - Firmware and configuration management
- [Interactive Credentials](docs/interactive-credentials.md) - Alternative authentication methods

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Scrapli](https://github.com/carlmontanari/scrapli) - Network device connections
- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Rich](https://github.com/Textualize/rich) - Terminal formatting

---

*Built for network engineers who value clean, reliable automation*
