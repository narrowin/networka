# Python library quickstart

## Prerequisites

Install Networka and create a [configuration](../configuration.md) for the
device. This example uses a RouterOS device with the configuration name
`router1`.

```yaml
# devices/router1.yml
devices:
  router1:
    host: 192.0.2.10
    device_type: mikrotik_routeros
```

Set the [credentials](../environment-variables.md) for the device and replace
the example address.

## Run a command

Save this example as `example.py`.

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    result = client.run("router1", "/system/identity/print")
    for command in result.command_results:
        print(command.output if command.error is None else command.error)
```

From the checkout after `uv sync --locked`, use
`uv run --locked python example.py`. The client can reuse a connection
between operations in the same context. Leaving the context closes its pool.

## Run a packaged sequence

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    result = client.run("router1", "system_info")
    for sequence in result.sequence_results:
        if sequence.error is not None:
            print(sequence.error)
        for command, output in (sequence.outputs or {}).items():
            print(command, output)
```

## Without configuration files

To use only an IP, platform, and credentials, call the
[run operation with a minimal configuration](adhoc-targets.md#without-configuration-files).

## Next steps

- [Persistent sessions](sessions.md)
- [Python recipes](recipes.md)
- [API reference](../reference/api.md)
