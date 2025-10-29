# Installation

## Installation (not on PyPI yet)

Install from GitHub using an isolated tool installer.

```bash
uv tool install git+https://github.com/narrowin/networka.git
# or
pipx install git+https://github.com/narrowin/networka.git
```

Short install video (30s):

[asciinema placeholder – will be embedded here]

## Verify installation

```bash
nw --help
nw --version
```

## Minimal configuration

Option 1 (recommended): bootstrap the default config tree and follow the prompts.

```bash
nw config init
```

This creates a modular configuration at the platform-specific application path:

- Linux: `~/.config/networka`
- macOS: `~/Library/Application Support/networka`
- Windows: `%APPDATA%\networka` (typically `C:\Users\<you>\AppData\Roaming\networka`)

Option 2: copy the repository’s `config/` directory into that application path if you prefer to start from the examples committed in source control. Make sure the destination contains `config.yml`, `devices/`, `groups/`, and `sequences/` exactly as expected by the loader.

With the configuration in place, add a device definition under `devices/` (for example, `devices/router1.yml`):

```yaml
host: 192.0.2.10
device_type: mikrotik_routeros
```

Run a command:

```bash
nw run router1 "/system/identity/print"
```

Expected output (trimmed):

```text
Executing on router1: /system/identity/print
name="MikroTik"
Command completed successfully
```

See the User guide for additional configuration options.

## Next steps

- Define more devices and groups → Configuration
- Learn how to run common operations → Running commands
- Control formatting and capture outputs → Output modes and Results
- Troubleshooting connection/auth issues → Troubleshooting
