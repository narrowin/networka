# IP Address Support

Networka lets you target devices directly by IP address (single or comma-separated list) without predefining them in configuration files.

## Usage examples

### Single IP address

```bash
# Run a command
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros

# SSH to device by IP
nw ssh 192.168.1.1 --platform mikrotik_routeros

# Show device info by IP
nw info 192.168.1.1 --platform mikrotik_routeros
```

### Multiple IP addresses

```bash
# Execute command on multiple IPs (comma-separated, no spaces)
nw run "192.168.1.1,192.168.1.2,192.168.1.3" "/system/clock/print" --platform mikrotik_routeros

# SSH to multiple IPs (opens tmux with multiple panes)
nw ssh "192.168.1.1,192.168.1.2" --platform mikrotik_routeros

# Mix IPs and configured device names
nw run "192.168.1.1,sw-acc1,192.168.1.2" "/system/clock/print" --platform mikrotik_routeros
```

### With custom port

```bash
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros --port 2222
```

### Interactive authentication

```bash
# Prompt for credentials at runtime
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros --interactive-auth
```

## Required parameters

When using IP addresses, you must specify:

- `--platform`: The device type (network driver), e.g. `mikrotik_routeros`, `cisco_iosxe`.

Optional parameters:

- `--port`: SSH port (defaults to 22)
- `--interactive-auth`: Prompt for username/password instead of environment
- `--transport`: Transport driver to use for the session; defaults to configuration or Scrapli. Note: nornir-netmiko is not yet supported but coming soon.

## Supported platforms

- mikrotik_routeros — MikroTik RouterOS
- cisco_iosxe — Cisco IOS-XE
- cisco_ios — Cisco IOS
- cisco_iosxr — Cisco IOS-XR
- cisco_nxos — Cisco NX-OS
- juniper_junos — Juniper JunOS
- arista_eos — Arista EOS
- nokia_srlinux — Nokia SR Linux
- linux — Linux SSH

## Authentication

IP-based connections use the same authentication as configured devices:

1. Environment variables: `NW_USER_DEFAULT` and `NW_PASSWORD_DEFAULT`
2. Interactive mode with `--interactive-auth`
3. SSH keys (via the underlying transport)

## Error handling

If you omit the platform when using IPs:

```text
Error: When using IP addresses, --platform is required
Supported platforms:
  mikrotik_routeros: MikroTik RouterOS
  cisco_iosxe: Cisco IOS-XE
  cisco_ios: Cisco IOS
  cisco_iosxr: Cisco IOS-XR
  cisco_nxos: Cisco NX-OS
  juniper_junos: Juniper JunOS
  arista_eos: Arista EOS
  nokia_srlinux: Nokia SR Linux
  linux: Linux SSH
```

## Implementation details

When IPs are used as the target:

1. Networka detects the IPs in the target argument
2. Creates temporary devices with generated names (e.g. `ip_192_168_1_1`)
3. Applies the specified `--platform` for connection parameters
4. Merges with any configured devices so you can mix both
5. Executes commands as usual and supports results storage
