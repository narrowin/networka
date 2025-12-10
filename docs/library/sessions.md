# Persistent Sessions

## Why Use Sessions

Opening an SSH connection is expensive. If you need to run multiple commands, open one connection and reuse it:

**Bad (N connections):**
```python
client = NetworkaClient()
client.run("router1", "command1")  # Opens connection, runs, closes
client.run("router1", "command2")  # Opens connection, runs, closes
client.run("router1", "command3")  # Opens connection, runs, closes
```

**Good (1 connection):**
```python
client = NetworkaClient()
with DeviceSession("router1", client.config) as session:
    session.execute_command("command1")
    session.execute_command("command2")
    session.execute_command("command3")
# Connection closes automatically
```

## Basic Pattern

```python
from network_toolkit import NetworkaClient, DeviceSession

client = NetworkaClient()

with DeviceSession("router1", client.config) as session:
    # Connection is now open
    output1 = session.execute_command("/interface/print")
    output2 = session.execute_command("/system/resource/print")
    output3 = session.execute_command("/system/clock/print")
    # All on the same connection
# Connection automatically closes here
```

## Session Methods

### execute_command

Run a single command and get output:

```python
with DeviceSession("router1", client.config) as session:
    output = session.execute_command("/system/identity/print")
    print(output)
```

### upload_file

Transfer a file to the device:

```python
from pathlib import Path

with DeviceSession("router1", client.config) as session:
    session.upload_file(
        local_file=Path("firmware.npk"),
        remote_path="firmware.npk"
    )
```

### download_file

Download a file from the device:

```python
from pathlib import Path

with DeviceSession("router1", client.config) as session:
    session.download_file(
        remote_file="backup.rsc",
        local_path=Path("./backups/backup.rsc")
    )
```

## Custom Credentials

Override credentials without changing configuration:

```python
with DeviceSession("router1", client.config,
                   username_override="admin",
                   password_override="secret") as session:
    output = session.execute_command("show version")
```

## Error Handling

Sessions automatically handle connection cleanup, even on errors:

```python
try:
    with DeviceSession("router1", client.config) as session:
        output = session.execute_command("/some/command")
        # Process output...
        if "error" in output.lower():
            raise ValueError("Command returned error")
except ValueError as e:
    print(f"Command failed: {e}")
# Connection still closes properly
```

## Parallel Sessions

Run commands on multiple devices simultaneously:

```python
from concurrent.futures import ThreadPoolExecutor
from network_toolkit import NetworkaClient, DeviceSession

def check_device(device_name, config):
    with DeviceSession(device_name, config) as session:
        return session.execute_command("/system/identity/print")

client = NetworkaClient()
devices = ["router1", "router2", "router3"]

with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [executor.submit(check_device, dev, client.config) for dev in devices]
    for future in futures:
        print(future.result())
```

See [recipes](recipes.md) for more parallel operation patterns.

## Configuration

Sessions respect configuration settings:

```yaml
general:
  connection_retries: 3
  retry_delay: 2
  ssh_strict_host_key_checking: true
```

Disable strict host key checking programmatically:

```python
client = NetworkaClient()
client.config.general.ssh_strict_host_key_checking = False

with DeviceSession("router1", client.config) as session:
    output = session.execute_command("show version")
```

## Next Steps

- See [recipes](recipes.md) for complete workflow examples
- Check [ad-hoc targets](adhoc-targets.md) for connecting without configuration
- Review [API reference](../reference/api.md) for all methods and parameters
