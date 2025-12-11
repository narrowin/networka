# Ad-Hoc IP Targeting

Connect to devices by IP address without adding them to your configuration files.

## Quick Example

Use `client.run()` directly with an IP address. You must specify the `device_type`.

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()

# Connect to an IP address
result = client.run(
    target="192.168.1.100",
    command_or_sequence="/system/identity/print",
    device_type="mikrotik_routeros"
)

print(result.output)
```

## Multiple IPs

You can pass a comma-separated list of IPs to `target`.

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()

# Run on multiple IPs in parallel
result = client.run(
    target="192.168.1.100,192.168.1.101",
    command_or_sequence="/system/identity/print",
    device_type="mikrotik_routeros"
)

# Access results
for cmd_result in result.command_results:
    print(f"{cmd_result.device}: {cmd_result.output}")
```

## Credentials

You can provide credentials directly if they differ from your defaults or environment variables.

```python
from network_toolkit import NetworkaClient
from network_toolkit.common.credentials import InteractiveCredentials

client = NetworkaClient()

creds = InteractiveCredentials(username="admin", password="secret_password")

client.run(
    target="192.168.1.100",
    command_or_sequence="show version",
    device_type="cisco_iosxe",
    interactive_creds=creds
)
```

## Supported Device Types

Common types include:

- `mikrotik_routeros` - MikroTik RouterOS
- `cisco_iosxe` - Cisco IOS-XE
- `cisco_ios` - Cisco IOS
- `arista_eos` - Arista EOS
- `juniper_junos` - Juniper JunOS
- `linux` - Linux SSH

To see all supported types programmatically:

```python
from network_toolkit.ip_device import get_supported_device_types

types = get_supported_device_types()
for device_type, description in types.items():
    print(f"{device_type}: {description}")
```

## Custom Port

You can specify a custom SSH port:

```python
client.run(
    target="192.168.1.100",
    command_or_sequence="show version",
    device_type="mikrotik_routeros",
    port=2222
)
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
