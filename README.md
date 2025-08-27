<div align="center">
  <img src="https://narrowin.github.io/networka/assets/images/networka.png" alt="Networka Logo" width="320"/>

  <p><a href="https://narrowin.github.io/networka/">Full documentation →</a></p>
</div>

<br/>

**Networka: `Eierlegende Wollmilchsau` of network operations — optimized for your daily workflows.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/narrowin/networka)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)

Networka is a modern async CLI tool for automating network devices across multiple vendors. Built with async/await patterns for high performance and reliability. Designed for network engineers who want fast, scalable automation with full cross-platform support.

---

## _The Networka Monologue_

_“People ask the question…_ <br>
**what’s a Networka?** <br>

And I tell 'em — <br>
it's **not** about cables, configs, and pings. <br>
_Oh no._ <br>
There’s more to it than that, my friend. <br>

We all like a bit of the good life — <br>
some the uptime, some the security, <br>
others the automation, the visibility, or the compliance. <br>

But a **Networka**, oh, they're different. <br>
Why? <br>
Because a real **Networka** wants the f\*ing lot.”<br><br>
(inspired by: [RockNRolla](https://www.youtube.com/watch?v=s4YLBqMJYOo))

## Getting Started

- Installation: see the docs → https://narrowin.github.io/networka/getting-started/
- Platform compatibility → https://narrowin.github.io/networka/platform-compatibility/
- Shell completion → https://narrowin.github.io/networka/shell-completion/
- CLI reference → https://narrowin.github.io/networka/reference/cli/
- API reference → https://narrowin.github.io/networka/reference/api/

## Features

### **Core Capabilities**

- **Multi-vendor network automation**: Native support for MikroTik RouterOS, Cisco IOS/IOS-XE/NX-OS, Arista EOS, Juniper JunOS, and more
- **Scalable device management**: Execute commands across individual devices or groups concurrently with async/await architecture
- **Cross-platform compatibility**: Full support for Linux, macOS, and Windows environments
- **Flexible configuration**: YAML and CSV configuration options with powerful device tagging and grouping

### **Operational Features**

- **Command execution**: Run single commands or predefined sequences across devices and groups
- **File management**: Upload/download files to/from network devices with verification and error handling
- **Device backup**: Automated configuration and comprehensive backups with vendor-specific implementations
- **Firmware management**: Upgrade, downgrade, and BIOS operations with platform validation
- **SSH session management**: Direct SSH access with tmux integration for interactive sessions

### **Advanced Features**

- **Intelligent completions**: Context-aware shell completions for devices, groups, and sequences
- **Vendor-aware sequences**: Predefined command sets optimized for different network platforms
- **Results management**: Organized storage with multiple output formats and automatic timestamping
- **Configuration validation**: Schema-based validation with detailed error reporting
- **Credential management**: Secure credential handling via environment variables with device-specific overrides

### **Developer & Integration Features**

- **Type safety**: Full mypy type checking for reliability and maintainability
- **Modern architecture**: Built with async/await patterns for high performance
- **Extensible design**: Plugin-friendly architecture for adding new vendors and operations
- **Rich output**: Professional CLI interface with color coding and structured information display

## Installation

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.11, 3.12, or 3.13
- **Network Access**: SSH connectivity to target devices
- **Package Manager**: uv (recommended) or pip

### Quick Install

```bash
# Easiest (user-wide, isolated)
uv tool install git+https://github.com/narrowin/networka.git
# or
pipx install git+https://github.com/narrowin/networka.git

# If you prefer plain pip (user-wide, no sudo)
pip install --user git+https://github.com/narrowin/networka.git
# ensure ~/.local/bin (or platform-specific bin) is on PATH

# Verify installation works
nw --help
```

### Upgrade & Remove

```bash
# Upgrade to latest version
uv tool upgrade networka
# or
pipx upgrade networka
# or
pip install --user --upgrade git+https://github.com/narrowin/networka.git

# Remove installation
uv tool uninstall networka
# or
pipx uninstall networka
# or
pip uninstall networka
```

### Platform-Specific Notes

**Linux/macOS**: No additional dependencies required

**Windows**: Scrapli (the default transport) does not officially support native Windows. While it may work with Paramiko or ssh2-python drivers, the recommended approach is to run Networka on WSL2 (Ubuntu) for a fully supported POSIX environment. Native Windows usage is best-effort.

## Quick Start

Get up and running with config init command:

```bash
# Initialize in default location with interactive prompts
nw config init

## Terminology: device_type vs hardware platform vs transport

- device_type: Network OS driver used for connections and commands (Scrapli "platform"). Examples: mikrotik_routeros, cisco_iosxe, arista_eos, juniper_junos. Set per device and used to resolve vendor-aware sequences.
- platform (hardware/firmware): Hardware architecture used for firmware-related operations. Examples: x86, x86_64, arm, mipsbe, tile. Not used for SSH connections or command execution.
- transport: Connection backend used by Networka. Default is scrapli; nornir-netmiko transport is planned (not yet supported).

Note about flags: When targeting IP addresses directly, the CLI flag --platform refers to the network driver (device_type), not the hardware architecture.

## Connection transports

- Default: Scrapli (stable)
- CLI override: use --transport to select the connection backend per run
- Planned: nornir-netmiko integration. Note: nornir-netmiko is not yet supported but coming soon.

## CLI overview

```

Usage: nw [OPTIONS] COMMAND [ARGS]...

Networka (nw)

A powerful multi-vendor CLI tool for automating network devices based on ssh protocol.
Built with async/await support and type safety in mind.

QUICK START:
nw run sw-acc1 '/system/clock/print' # Execute command
nw run office_switches system_info # Run sequence on group

For detailed help on any command: nw <command> --help
Default config directory: config/ (use --config to override)

Options:
--version Show version information
--help -h Show this message and exit.

Commands:
ssh Open tmux with SSH panes for a device or group.

Info & Configuration:
info Show comprehensive information for devices, groups, or sequences.
list List network devices, groups, sequences, and platform information
devices List all configured network devices.
groups List all configured device groups and their members.
sequences List all available command sequences, optionally filtered by vendor or category.
supported-types List supported device types.
config Configuration management commands
init Initialize a minimal working configuration environment.
validate Validate the configuration file and show any issues.
schema JSON schema management commands
update Update JSON schemas for YAML editor validation.
info Display information about JSON schema files.
diff Diff config, a command, or a sequence.

Executing Operations:
run Execute a single command or a sequence on a device or a group.
upload Upload a file to a device or to all devices in a group.
download Download a file from a device or all devices in a group.

Vendor-Specific Operations:
backup Device backup operations (config and comprehensive)
firmware Firmware and BIOS management operations

````

## networka environment

### 1. Set up credentials for network device logins

**Option A: Use .env file (Recommended)**

```bash
# Copy and edit the example file
cp .env.example .env
nano .env  # Add your actual credentials
````

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

Networka uses a flexible configuration system supporting both YAML and CSV formats, with hierarchical loading from directories and subdirectories.

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

Notes:

- device_type = network driver (Scrapli platform); controls connection behavior and command semantics
- platform = hardware architecture for firmware tasks (upgrade/downgrade/bootloader)

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
  output_mode: "dark" # default, light, dark, no-color, raw
```

**Device Configuration (`config/devices/*.yml`):**

```yaml
devices:
  device_name:
    host: "IP_ADDRESS"
  device_type: "mikrotik_routeros" # network driver (Scrapli platform): cisco_iosxe, arista_eos, juniper_junos, ...
  # platform: "mipsbe"            # hardware architecture for firmware ops (optional)
    description: "Device description"
    tags: ["tag1", "tag2"]
```

**Group Configuration (`config/groups/*.yml`):**

```yaml
groups:
  group_name:
    description: "Group description"
    match_tags: ["tag1"] # Include devices with these tags
    # OR
    members: ["device1", "device2"] # Explicit device list
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

1. **Device files**: All files in `config/devices/` (_.yml, _.yaml, \*.csv)
2. **Group files**: All files in `config/groups/` (_.yml, _.yaml, \*.csv)
3. **Sequence files**: All files in `config/sequences/` (_.yml, _.yaml, \*.csv)

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
  output_mode: "dark" # default, light, dark, no-color, raw
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

### Information and discovery

```bash
# Show device information and connection details
nw info sw-acc1

# Show group information and members
nw info access_switches

# Show sequence information and commands
nw info health_check

# Show information for multiple targets
nw info sw-acc1,access_switches,health_check
```

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

### Vendor-specific backup operations

Networka provides vendor-specific backup operations that automatically use the correct commands and file formats for each platform:

```bash
# Configuration backup (text-only configuration export)
nw backup config sw-acc1                     # MikroTik: /export commands
nw backup config cisco-sw1                  # Cisco: show running-config
nw backup config --no-download sw-acc1      # Create but don't download files

# Comprehensive backup (configuration + system data)
nw backup comprehensive sw-acc1             # MikroTik: /export + /system/backup
nw backup comprehensive cisco-sw1           # Cisco: show commands (running/startup/version/inventory)
nw backup comprehensive office_switches     # Run on device group

# Options for backup operations
nw backup config sw-acc1 --delete-remote    # Remove remote files after download
nw backup comprehensive sw-acc1 --verbose   # Detailed operation logging
```

**Platform-specific behavior:**

- **MikroTik RouterOS**: Creates .rsc (export) and .backup (system) files
- **Cisco IOS/IOS-XE**: Displays configuration and system information (typically not saved to files)
- **Download handling**: Automatically determines which files to download based on platform

## Community & support

- Visit our [documentation](docs/) for detailed guides and examples
- Create [GitHub Issues](https://github.com/narrowin/networka/issues) for bug reports and feature requests
- See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines
- Check [SECURITY.md](SECURITY.md) for security policy and reporting vulnerabilities

## Contributing

Have a look through existing [Issues](https://github.com/narrowin/networka/issues) and [Pull Requests](https://github.com/narrowin/networka/pulls) that you could help with. If you'd like to request a feature or report a bug, please create a GitHub Issue using one of the templates provided.

[See contribution guide →](CONTRIBUTING.md)

## Documentation

- Docs Home → https://narrowin.github.io/networka/
- Platform Compatibility → https://narrowin.github.io/networka/platform-compatibility/
- Development Guide → https://narrowin.github.io/networka/development/
- Multi-Vendor Support → https://narrowin.github.io/networka/multi-vendor-support/
- IP Address Support → https://narrowin.github.io/networka/ip-address-support/
- Transport Selection → https://narrowin.github.io/networka/transport/
- Environment Variables → https://narrowin.github.io/networka/environment-variables/
- File Upload Guide → https://narrowin.github.io/networka/file_upload/
- Interactive Credentials → https://narrowin.github.io/networka/interactive-credentials/

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [Scrapli](https://github.com/carlmontanari/scrapli) - Network device connections
- [Nornir](https://github.com/nornir-automation/nornir) - Network automation framework
- [Netmiko](https://github.com/ktbyers/netmiko) - Multi-vendor CLI connections to network devices
- [Typer](https://github.com/tiangolo/typer) - CLI framework
- [Pydantic](https://github.com/pydantic/pydantic) - Data validation
- [Rich](https://github.com/Textualize/rich) - Terminal formatting

---

_Built for network engineers who value clean, reliable automation_
