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

## Key Classes

### NetworkaClient

High-level client that loads configuration and provides methods for all operations.

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()
result = client.run("router1", "show version")
```

See [NetworkaClient API reference](../reference/api.md#network_toolkit.client.NetworkaClient)

### DeviceSession

Persistent connection manager for executing multiple commands efficiently.

```python
from network_toolkit import NetworkaClient, DeviceSession

client = NetworkaClient()
with DeviceSession("router1", client.config) as session:
    version = session.execute_command("show version")
    uptime = session.execute_command("show uptime")
```

See [DeviceSession API reference](../reference/api.md#network_toolkit.device.DeviceSession)

## Quick Links

- [60-second quickstart](quickstart.md) - Get started immediately
- [Persistent sessions](sessions.md) - Efficient multi-command workflows
- [Ad-hoc IP targeting](adhoc-targets.md) - Connect without configuration
- [Code recipes](recipes.md) - Common patterns and examples

## Installation

```bash
pip install networka
```

Or with uv:

```bash
uv pip install networka
```

## Next Steps

Start with the [quickstart guide](quickstart.md) to run your first commands, then explore [sessions](sessions.md) for more advanced patterns.
