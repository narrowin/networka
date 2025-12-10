# Ad-Hoc IP Targeting

Connect to devices by IP address without adding them to your configuration files.

## Quick Example

```python
from network_toolkit import NetworkaClient, DeviceSession, create_ip_based_config

client = NetworkaClient()

# Create temporary config for this IP
config = create_ip_based_config(
    ips=["192.168.1.100"],
    device_type="mikrotik_routeros",
    base_config=client.config,
)

# Generated device name: ip_<ip_with_underscores>
device_name = "ip_192_168_1_100"

with DeviceSession(device_name, config,
                   username_override="admin",
                   password_override="password") as session:  # pragma: allowlist secret
    output = session.execute_command("/system/identity/print")
    print(output)
```

## Device Naming Convention

`create_ip_based_config` generates device names automatically:

- `192.168.1.1` becomes `ip_192_168_1_1`
- `10.0.0.5` becomes `ip_10_0_0_5`
- `2001:db8::1` becomes `ip_2001_db8__1`

## Multiple IPs

Connect to several devices at once:

```python
from network_toolkit import NetworkaClient, DeviceSession, create_ip_based_config

client = NetworkaClient()

ips = ["192.168.1.100", "192.168.1.101", "192.168.1.102"]

config = create_ip_based_config(
    ips=ips,
    device_type="mikrotik_routeros",
    base_config=client.config,
)

for ip in ips:
    device_name = f"ip_{ip.replace('.', '_')}"
    with DeviceSession(device_name, config,
                       username_override="admin",
                       password_override="password") as session:  # pragma: allowlist secret
        identity = session.execute_command("/system/identity/print")
        print(f"{ip}: {identity}")
```

## Parameters

### Required

- `ips`: List of IP addresses (strings)
- `device_type`: Platform identifier (e.g., `"mikrotik_routeros"`, `"cisco_iosxe"`)
- `base_config`: Base configuration from NetworkaClient

### Optional

- `hardware_platform`: Hardware architecture (e.g., `"x86"`, `"arm"`) - used for firmware operations
- `port`: SSH port (default: 22)
- `transport_type`: Transport protocol (default: `"scrapli"`)

## Supported Device Types

```python
from network_toolkit.ip_device import get_supported_device_types

types = get_supported_device_types()
for device_type, description in types.items():
    print(f"{device_type}: {description}")
```

Common types:

- `mikrotik_routeros` - MikroTik RouterOS
- `cisco_iosxe` - Cisco IOS-XE
- `cisco_ios` - Cisco IOS
- `arista_eos` - Arista EOS
- `juniper_junos` - Juniper JunOS
- `linux` - Linux SSH

## Custom Port

```python
config = create_ip_based_config(
    ips=["192.168.1.100"],
    device_type="mikrotik_routeros",
    base_config=client.config,
    port=2222,  # Custom SSH port
)
```

## Using with NetworkaClient

NetworkaClient also supports IP targets directly:

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()

result = client.run(
    target="192.168.1.100",
    command_or_sequence="/system/identity/print",
    device_type="mikrotik_routeros",  # Required for IP targets
    interactive_creds={"username": "admin", "password": "password"},  # pragma: allowlist secret
)

print(result.output)
```

## Credentials from Environment

Avoid hardcoding credentials:

```python
import os
from network_toolkit import NetworkaClient, DeviceSession, create_ip_based_config

username = os.getenv("DEVICE_USER", "admin")
password = os.getenv("DEVICE_PASS")

client = NetworkaClient()
config = create_ip_based_config(
    ips=["192.168.1.100"],
    device_type="mikrotik_routeros",
    base_config=client.config,
)

device_name = "ip_192_168_1_100"

with DeviceSession(device_name, config,
                   username_override=username,
                   password_override=password) as session:
    output = session.execute_command("/system/identity/print")
```

## Mixing IPs and Configured Devices

Combine ad-hoc IPs with your existing configuration:

```python
from network_toolkit import NetworkaClient, DeviceSession, create_ip_based_config

client = NetworkaClient()

# Add ad-hoc IPs to existing config
new_ips = ["192.168.1.200", "192.168.1.201"]
config = create_ip_based_config(
    ips=new_ips,
    device_type="mikrotik_routeros",
    base_config=client.config,  # Preserves existing devices
)

# Now you have both configured devices and ad-hoc IPs
print(f"Total devices: {len(config.devices)}")

# Use configured device
with DeviceSession("my_router", config) as session:
    print(session.execute_command("show version"))

# Use ad-hoc IP
with DeviceSession("ip_192_168_1_200", config,
                   username_override="admin",
                   password_override="password") as session:  # pragma: allowlist secret
    print(session.execute_command("show version"))
```

## When to Use

**Use ad-hoc IPs when:**

- Testing against devices you don't regularly access
- One-time migrations or audits
- Scanning networks for compliance
- Temporary troubleshooting

**Use configuration files when:**

- Working with the same devices regularly
- Sharing device lists across teams
- Managing credentials centrally
- Using device tags and groups

## Next Steps

- See [recipes](recipes.md) for complete examples
- Learn about [persistent sessions](sessions.md) for efficient multi-command workflows
- Check the [API reference](../reference/api.md) for all options
