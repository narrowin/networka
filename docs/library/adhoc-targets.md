# Ad hoc IP targets

Use an IP address when the device has no entry in your inventory. Supply the
logical platform as `device_type`. Use
[platform inspection](../platform-compatibility.md#inspect-connection-definitions-and-capabilities)
to find the active definition names.

## With an existing configuration

A `NetworkaClient` loads its configuration for every target type. It can
apply those connection defaults to an IP absent from the inventory.

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    result = client.run(
        target="192.0.2.10",
        command_or_sequence="/system/identity/print",
        device_type="mikrotik_routeros",
        port=2222,
    )
    for command in result.command_results:
        print(command.output if command.error is None else command.error)
```

You can pass a comma-separated list of IPs. `device_type` and `port` apply
to every address in that invocation.

## Without configuration files

Use the programmatic run operation with a minimal configuration and
the connection credentials.

```python
from getpass import getpass

from network_toolkit.api import RunOptions, run_commands
from network_toolkit.common.credentials import InteractiveCredentials
from network_toolkit.config import create_minimal_config

credentials = InteractiveCredentials(
    username=input("Username: "),
    password=getpass("Password: "),
)
result = run_commands(
    RunOptions(
        target="192.0.2.10",
        command_or_sequence="/system/identity/print",
        config=create_minimal_config(),
        device_type="mikrotik_routeros",
        interactive_creds=credentials,
    )
)
for command in result.command_results:
    print(command.output if command.error is None else command.error)
```

Use configured device names for recurring work or when different targets need
different platforms. See [credentials](../environment-variables.md) and
[IP address support](../ip-address-support.md).
