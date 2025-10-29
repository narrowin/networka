<div align="center"><img src="docs/assets/images/networka_readme.png" alt="Networka Logo" width="320"/>

  <p><a href="https://narrowin.github.io/networka/">Full documentation →</a></p>
</div>

<br/>

**Networka: `Eierlegende Wollmilchsau` of network operations — optimized for your daily workflows.**

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey.svg)](https://github.com/narrowin/networka)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![Code style: ruff](https://img.shields.io/badge/code%20style-ruff-000000.svg)](https://github.com/astral-sh/ruff)
[![Type checked with mypy](https://img.shields.io/badge/mypy-checked-blue.svg)](http://mypy-lang.org/)
[![CI](https://github.com/narrowin/networka/actions/workflows/ci.yml/badge.svg)](https://github.com/narrowin/networka/actions/workflows/ci.yml)
[![Docs](https://img.shields.io/github/actions/workflow/status/narrowin/networka/docs.yml?label=Docs&logo=github)](https://narrowin.github.io/networka/)

Networka is a modern CLI tool for automating network devices across multiple vendors. Designed for network engineers who want fast, scalable automation with full cross-platform support.

Built entirely with Sonett 4 and GPT-5, this is an agent-mode experiment that turned into something genuinely useful.

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

<div align="center">
  <img src="https://narrowin.github.io/networka/assets/gifs/networka-setup.gif" alt="Networka Setup Demo" width="800"/>
  <p><em>Networka setup and command execution demo</em></p>
</div>

## Features

### **Core Capabilities**

- **Multi-vendor network automation**: Native support for MikroTik RouterOS, Cisco IOS/IOS-XE/NX-OS, Arista EOS, Juniper JunOS, and more
- **Scalable device management**: Execute commands across individual devices or groups
- **Cross-platform compatibility**: Full support for Linux, macOS, and Windows environments
- **Flexible configuration**: YAML and CSV configuration options with powerful device tagging and grouping

### **Operational Features**

- **Command execution**: Run single commands or predefined sequences across devices and groups
- **File management**: Upload/download files to/from network devices with verification and error handling
- **Device backup**: Automated configuration and comprehensive backups with vendor-specific implementations
- **Firmware management**: Upgrade, downgrade, and BIOS operations with platform validation
- **CLI session management**: Direct CLI access with tmux integration for interactive sessions

### **Advanced Features**

- **Intelligent completions**: Context-aware shell completions for devices, groups, and sequences
- **Vendor-aware sequences**: Predefined command sets optimized for different network platforms
- **Results management**: Organized storage with multiple output formats and automatic timestamping
- **Configuration validation**: Schema-based validation with detailed error reporting
- **Credential management**: Secure credential handling via environment variables with device-specific overrides

### **Developer & Integration Features**

- **Type safety**: Full mypy type checking for reliability and maintainability
- **Modern architecture**: Built with scalable scrapli and nornir support
- **Extensible design**: Plugin-friendly architecture for adding new vendors and operations
- **Rich output**: Professional CLI interface with color coding and structured information display

## Installation

### System Requirements

- **Operating System**: Linux, macOS, or Windows
- **Python**: 3.11, 3.12, or 3.13
- **Network Access**: SSH connectivity to target devices
- **Package Manager**: uv (recommended) or pip

### Quick Install (recommended)

Not on PyPI yet — install from GitHub.

```bash
# Recommended (isolated, user-wide)
uv tool install git+https://github.com/narrowin/networka.git

# Alternative
pipx install git+https://github.com/narrowin/networka.git

# Verify installation
nw --help
```

#### If `nw` is not found

- Check: `command -v nw` (Linux/macOS) or `where nw` (Windows)
- If using pipx: ensure PATH is set, then reload shell
  ```bash
  pipx ensurepath
  exec $SHELL
  ```
- Linux/macOS: add user bin to PATH if needed
  ```bash
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
  exec $SHELL
  ```
- Windows (native, best-effort): prefer WSL2; if native, run `pipx ensurepath` and restart the terminal

More → PATH troubleshooting: https://narrowin.github.io/networka/troubleshooting/#path-nw-not-found

### Upgrade & Remove

```bash
# Upgrade to latest version (from GitHub)
uv tool install --force git+https://github.com/narrowin/networka.git
# or
pipx install --force git+https://github.com/narrowin/networka.git

# Remove installation
uv tool uninstall nw
# or
pipx uninstall networka
```

### Platform-Specific Notes

**Linux/macOS**: No additional dependencies required

**Windows**: Scrapli (the default transport) does not officially support native Windows. While it may work with Paramiko or ssh2-python drivers, the recommended approach is to run Networka on WSL2 (Ubuntu) for a fully supported POSIX environment. Native Windows usage is best-effort.

WSL2 quickstart (recommended):

```bash
# In Ubuntu on WSL2
curl -LsSf https://astral.sh/uv/install.sh | sh
exec $SHELL
uv tool install git+https://github.com/narrowin/networka.git
nw --help
```

Details → https://narrowin.github.io/networka/platform-compatibility/#wsl2-quickstart-recommended

## Quick Start

Get up and running with config init command:

```bash
# Initialize in default location with interactive prompts
nw config init

```

### One-liners (no config)

Run directly against an IP without creating files. `--platform` selects the network OS driver; `--interactive-auth` prompts for credentials.

```bash
# MikroTik RouterOS
nw run --platform mikrotik_routeros 192.0.2.10 "/system/identity/print" --interactive-auth
```

```bash
# Cisco IOS-XE
nw run --platform cisco_iosxe 198.51.100.20 "show version" --interactive-auth
```

## Terminology: device_type vs hardware platform vs transport

- device_type: Network OS driver used for connections and commands (Scrapli "platform"). Examples: mikrotik_routeros, cisco_iosxe, arista_eos, juniper_junos.
- platform (hardware/firmware): Hardware architecture used for firmware-related operations (x86, x86_64, arm, mipsbe, tile).
- transport: Connection backend. Default is scrapli.

Note: When targeting IPs directly, `--platform` refers to the network driver (device_type), not hardware architecture.

## Quick links

- Getting started → https://narrowin.github.io/networka/getting-started/
- Running commands → https://narrowin.github.io/networka/running-commands/
- Configuration → https://narrowin.github.io/networka/configuration/
- Environment variables → https://narrowin.github.io/networka/environment-variables/
- Results → https://narrowin.github.io/networka/results/
- Output modes → https://narrowin.github.io/networka/output-modes/
- Backups → https://narrowin.github.io/networka/backups/
- CLI reference → https://narrowin.github.io/networka/reference/cli/
- API reference → https://narrowin.github.io/networka/reference/api/

## CLI overview

- For current usage and commands, see the CLI reference:
  - https://narrowin.github.io/networka/reference/cli/
  - Quick checks: `nw --help` and `nw --version`

## Community & support

- Visit our [documentation](https://narrowin.github.io/networka/) for detailed guides and examples
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
