# Quickstart

## Installation

Install with uv or pip:

```bash
uv pip install networka
# or
pip install networka
```

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

See User guide for configuration details.

## Next steps

- Define more devices and groups → CSV configuration
- Learn how to run common operations → Running commands
- Control formatting and capture outputs → Output modes and Results
- Troubleshooting connection/auth issues → Troubleshooting
