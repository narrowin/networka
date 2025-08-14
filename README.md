<h2 align="center">
    Net-Worker (nw)
    <br>
    Modern CLI tool for multi-vendor network automation
</h2>

<div align="center">

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

</div>

Net-Worker is a CLI tool for automating network devices across multiple vendors. Built with modern async/await patterns. Designed for network engineers who want fast, reliable, scalable automation. Stands on the shoulders for mutlivendor-support of scrapli and netmiko.

## Getting started

- [Installation instructions →](#installation)
- [CLI overview →](#cli-overview)  
- [Quick start guide →](#quick-start)
- [Configuration →](#configuration)
- [Examples →](#examples)

## Features

- **Multi-vendor support**: MikroTik RouterOS, Cisco IOS-XE/NX-OS, Arista EOS, Juniper JunOS
- **Group operations**: Execute commands across device groups concurrently  
- **Command sequences**: Vendor-aware predefined command sets
- **Results management**: Organized storage with multiple output formats
- **Security-first**: Environment variable credentials and comprehensive protection

## Installation

### Prerequisites
- Python 3.11+
- SSH access to target network devices
- uv (recommended) or pip for package management

### Install from GitHub

```bash
# Install latest version
pip install git+https://github.com/narrowin/net-worker.git

# Install specific version
pip install git+https://github.com/narrowin/net-worker.git@v0.1.0

# Verify installation
nw --help
```

### Development installation

```bash
# Clone and install in development mode
git clone https://github.com/narrowin/net-worker.git
cd net-worker
uv sync

# Activate environment and verify
source .venv/bin/activate
nw --help
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

```bash
# Set environment variables for security
export NT_DEFAULT_USER="admin"
export NT_DEFAULT_PASSWORD="your_secure_password"

# Device-specific overrides (optional)
export NT_SW_ACC1_PASSWORD="switch1_password"
```

### 2. Create configuration file

Create `devices.yml`:

```yaml
general:
  results_dir: "./results"
  timeout: 30

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

device_groups:
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

Net-Worker uses YAML configuration files and environment variables for secure credential management.

### Environment variables

```bash
# Default credentials (required)
export NT_DEFAULT_USER="admin"
export NT_DEFAULT_PASSWORD="your_secure_password"

# Device-specific overrides (optional)
export NT_SW_ACC1_PASSWORD="switch1_password"
```

### Configuration file structure

```yaml
general:
  results_dir: "./results"
  timeout: 30

devices:
  device_name:
    host: "IP_ADDRESS"
    device_type: "mikrotik_routeros"  # or cisco_iosxe, arista_eos, juniper_junos
    description: "Device description"
    tags: ["tag1", "tag2"]

device_groups:
  group_name:
    description: "Group description"
    match_tags: ["tag1"]  # Include devices with these tags
    # OR
    members: ["device1", "device2"]  # Explicit device list
```

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
