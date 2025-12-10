# Persistent Sessions

## Automatic Session Management

`NetworkaClient` automatically manages SSH sessions for you. When you run a command, it checks if a connection to that device already exists. If so, it reuses it; if not, it opens a new one.

To ensure these connections are closed properly when you are done, you should use the client as a context manager.

**Recommended Pattern:**

```python
from network_toolkit import NetworkaClient

# The 'with' block ensures all connections are closed when done
with NetworkaClient() as client:
    # First command opens the connection
    client.run("router1", "show version")

    # Subsequent commands reuse the same connection automatically
    client.run("router1", "show ip int brief")

    # You can switch between devices freely
    client.run("switch1", "show vlan")  # Opens new connection to switch1
    client.run("router1", "show clock") # Reuses existing connection to router1

# All sessions (router1, switch1) are closed here
```

## Manual Management (Not Recommended)

If you do not use the context manager, connections will remain open until the script terminates or you manually close them. This can lead to resource leaks in long-running scripts.

```python
client = NetworkaClient()

# Opens connection and keeps it open
client.run("router1", "show version")

# Reuses connection
client.run("router1", "show ip int brief")

# You must manually close sessions to free resources
client.close()
```

## Advanced: Low-Level Session Control

For very specific use cases where you need direct control over a single session (bypassing the client's pool), you can use `DeviceSession` directly.

```python
from network_toolkit import DeviceSession

# Manually manage a single session
with DeviceSession("router1", client.config) as session:
    output = session.execute_command("show version")
```### upload_file

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
                   password_override="secret") as session:  # pragma: allowlist secret
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
