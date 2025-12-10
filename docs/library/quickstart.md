# Quickstart: 60 Seconds to Your First Command

## Minimal Example

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    output = client.run("my_router", "show version")
    print(output)
```

That's it. One connection, execute commands, automatic cleanup.

## Prerequisites

1. Networka installed (see [Installation Guide](../getting-started.md#installation))
2. Device configured in `~/.config/networka/devices/devices.yml`:

```yaml
devices:
  my_router:
    host: 192.168.1.1
    device_type: mikrotik_routeros
    username: admin
    password: your_password
```

## Running the Example

Save this as `test.py`:

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    # Run a command
    result = client.run("my_router", "/system/identity/print")
    print(f"Device identity: {result}")

    # Run another command (reuses the same connection!)
    result2 = client.run("my_router", "/system/resource/print")
    print(f"Resources: {result2}")
```

Run it (ensure networka is installed in your current environment):

```bash
python test.py
```

## Using NetworkaClient Instead

For single commands, NetworkaClient is even simpler:

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()
result = client.run("my_router", "/system/identity/print")
print(result.output)
```

NetworkaClient opens and closes connections automatically. Use `DeviceSession` directly only if you need low-level control over the connection lifecycle or are building a custom integration.

## Without Configuration Files

Don't have a config file? Connect directly to an IP:

```python
from network_toolkit import NetworkaClient, create_ip_based_config

client = NetworkaClient()

config = create_ip_based_config(
    ips=["192.168.1.1"],
    device_type="mikrotik_routeros",
    base_config=client.config,
)

device_name = "ip_192_168_1_1"  # Auto-generated name

from network_toolkit import DeviceSession
with DeviceSession(device_name, config,
                   username_override="admin",
                   password_override="password") as session:  # pragma: allowlist secret
    output = session.execute_command("show version")
    print(output)
```

See [ad-hoc targets](adhoc-targets.md) for details.

## Next Steps

- [Persistent sessions](sessions.md) - Run multiple commands efficiently
- [Recipes](recipes.md) - Common patterns and workflows
- [API Reference](../reference/api.md) - Complete class documentation
