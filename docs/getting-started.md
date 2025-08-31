# Installation

## Quick Install

Install from PyPI using an isolated tool installer.

```bash
# Stable release from PyPI
uv tool install networka

# Latest development from GitHub
uv tool install git+https://github.com/narrowin/networka.git

# Alternative with pipx
pipx install networka
```

Short install video (30s):

[asciinema placeholder – will be embedded here]

## Verify installation

```bash
nw --help
nw --version
```

## Minimal configuration

Create a devices file `config/devices/router1.yml`:

```yaml
host: 192.0.2.10
device_type: mikrotik_routeros
```

Run a command:

```bash
nw run router1 "/system/identity/print"
```

Expected output (trimmed):

```
Executing on router1: /system/identity/print
name="MikroTik"
Command completed successfully
```

See User guide for configuration details.

## Next steps

- Define more devices and groups → Configuration
- Learn how to run common operations → Running commands
- Control formatting and capture outputs → Output modes and Results
- Troubleshooting connection/auth issues → Troubleshooting
