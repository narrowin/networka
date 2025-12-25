# Library API Overview

Networka provides both a CLI and a Python library. Use the library when you need custom automation logic, parallel operations, or integration with existing Python applications.

## CLI vs Library

**Use the CLI when:**

- Running ad-hoc commands or sequences
- Working interactively with devices
- Standard workflows fit your needs

**Use the Library when:**

- Building custom automation workflows
- Integrating with existing Python applications
- Implementing custom business logic or validation
- Running parallel operations across devices
- Parsing and processing command output programmatically

## Feature Support

The Python library supports the core automation features of Networka. Some management and interactive features are currently CLI-only.

| Feature | CLI Command | Library Method |
|---------|-------------|----------------|
| **Command Execution** | `nw run` | `client.run()` |
| **Sequence Execution** | `nw run` | `client.run()` |
| **File Upload** | `nw upload` | `client.upload()` |
| **File Download** | `nw download` | `client.download()` |
| **Config Backup** | `nw backup` | `client.backup()` |
| **Config Diff** | `nw diff` | `client.diff()` |
| **Firmware Upgrade** | `nw firmware upgrade` | *Not yet supported* |
| **RouterOS Upgrade** | `nw routerboard-upgrade` | *Not yet supported* |
| **Interactive SSH** | `nw cli` | *Not supported (interactive)* |
| **Config Management** | `nw config ...` | *Not supported* |
| **Inventory List** | `nw list` | *Access via `client.devices`* |

## Key Classes

### NetworkaClient

High-level client that loads configuration and provides methods for all operations. It supports context manager usage for automatic session reuse.

```python
from network_toolkit import NetworkaClient

# Simple usage
client = NetworkaClient()
result = client.run("router1", "show version")

# Efficient usage (reuses connections)
with NetworkaClient() as client:
    client.run("router1", "show version")
    client.run("router1", "show ip int brief")
```

See [NetworkaClient API reference](../reference/api.md#network_toolkit.client.NetworkaClient)

### DeviceSession

Low-level persistent connection manager. Generally you should use `NetworkaClient` as a context manager instead, as it handles session pooling automatically.

```python
from network_toolkit import NetworkaClient, DeviceSession

# Only use DeviceSession directly if you need to bypass the client's session management
client = NetworkaClient()
with DeviceSession("router1", client.config) as session:
    version = session.execute_command("show version")
```

See [DeviceSession API reference](../reference/api.md#network_toolkit.device.DeviceSession)

## Quick Links

- [60-second quickstart](quickstart.md) - Get started immediately
- [Persistent sessions](sessions.md) - Efficient multi-command workflows
- [Ad-hoc IP targeting](adhoc-targets.md) - Connect without configuration
- [Code recipes](recipes.md) - Common patterns and examples

## Installation

For installation instructions, please refer to the [Getting Started Guide](../getting-started.md#installation).

## Next Steps

Start with the [quickstart guide](quickstart.md) to run your first commands, then explore [sessions](sessions.md) for more advanced patterns.
