# IP Address Support```bash
# Multiple IPs separated by commas (no spaces)
nw run "192.168.1.1,192.168.1.2,192.168.1.3" "/system/clock/print" --platform mikrotik_routeros

# SSH to multiple devices by IP
nw ssh "192.168.1.1,192.168.1.2" --platform mikrotik_routeros

# Mix configured devices and IPs
nw run "192.168.1.1,sw-acc1,192.168.1.2" "/system/clock/print" --platform mikrotik_routeroswork Toolkit

The network toolkit now supports using IP addresses directly in commands instead of requiring predefined device configurations.

## Usage Examples

### Single IP Address
```bash
```bash
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros

# SSH to device by IP
nw ssh 192.168.1.1 --platform mikrotik_routeros

# Check device info by IP
nw info 192.168.1.1 --platform mikrotik_routeros
```

### Multiple IP Addresses
```bash
# Execute command on multiple IPs
nw run "192.168.1.1,192.168.1.2,192.168.1.3" "/system/clock/print" --platform mikrotik_routeros

# SSH to multiple IPs (opens tmux with multiple panes)
nw ssh "192.168.1.1,192.168.1.2" --platform mikrotik_routeros

# Mixed: IPs and predefined devices
nw run "192.168.1.1,sw-acc1,192.168.1.2" "/system/clock/print" --platform mikrotik_routeros
```

### With Custom Port
```bash
# Use custom SSH port
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros --port 2222
```

### Interactive Authentication
```bash
# Prompt for credentials interactively
nw run 192.168.1.1 "/system/clock/print" --platform mikrotik_routeros --interactive-auth
```

## Required Parameters

When using IP addresses, you **must** specify:

- `--platform`: The device platform type (required for Scrapli to know how to connect)

Optional parameters:
- `--port`: SSH port (defaults to 22)
- `--interactive-auth`: Prompt for username/password instead of using environment variables

## Supported Platforms

- `mikrotik_routeros`: MikroTik RouterOS
- `cisco_iosxe`: Cisco IOS-XE
- `cisco_iosxr`: Cisco IOS-XR
- `cisco_nxos`: Cisco NX-OS
- `juniper_junos`: Juniper JunOS
- `arista_eos`: Arista EOS
- `linux`: Linux SSH

## Authentication

IP-based connections use the same authentication mechanisms as predefined devices:

1. Environment variables: `NT_DEFAULT_USER` and `NT_DEFAULT_PASSWORD`
2. Interactive mode: Use `--interactive-auth` flag to be prompted
3. SSH keys: Standard SSH key authentication is supported

## Error Handling

If you forget to specify the platform when using IP addresses:

```bash
$ nw run 192.168.1.1 "/system/clock/print"
Error: When using IP addresses, --platform is required
Supported platforms:
  mikrotik_routeros: MikroTik RouterOS
  cisco_iosxe: Cisco IOS-XE
  cisco_iosxr: Cisco IOS-XR
  cisco_nxos: Cisco NX-OS
  juniper_junos: Juniper JunOS
  arista_eos: Arista EOS
  linux: Linux SSH
```

## Implementation Details

When you use IP addresses:

1. The toolkit detects IP addresses in the target parameter
2. Creates temporary device configurations with generated names (e.g., `ip_192_168_1_1`)
3. Uses the specified platform for Scrapli connection parameters
4. Combines these with any existing device configurations
5. Executes commands normally using the enhanced configuration

This allows seamless mixing of predefined devices and ad-hoc IP addresses in the same command.
