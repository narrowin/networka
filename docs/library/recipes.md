# Code Recipes

Common patterns for Networka library usage.

## Multi-Command Workflow

Execute a sequence of commands with validation using `client.run()`:

```python
from network_toolkit import NetworkaClient

with NetworkaClient() as client:
    # Check current state
    identity = client.run("router1", "/system/identity/print")
    print(f"Connected to: {identity.output}")

    # Get system info
    resources = client.run("router1", "/system/resource/print")
    print(f"Resources: {resources.output}")

    # Check interfaces
    interfaces = client.run("router1", "/interface/print")
    print(f"Interfaces: {interfaces.output}")
```

## Parallel Device Operations

Run the same command on multiple devices simultaneously. Note that `NetworkaClient` is not thread-safe, so we create a new instance for each thread.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
from network_toolkit import NetworkaClient

def get_device_info(device_name):
    """Execute command on a single device."""
    # Create a new client for each thread
    client = NetworkaClient()
    try:
        result = client.run(device_name, "/system/identity/print")
        return {"device": device_name, "output": result.output, "error": None}
    except Exception as e:
        return {"device": device_name, "output": None, "error": str(e)}

devices = ["router1", "router2", "router3", "router4"]

results = []
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = {executor.submit(get_device_info, dev): dev
               for dev in devices}

    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        if result["error"]:
            print(f"ERROR on {result['device']}: {result['error']}")
        else:
            print(f"SUCCESS on {result['device']}: {result['output']}")

# Summary
success = sum(1 for r in results if not r["error"])
print(f"\nCompleted: {success}/{len(devices)} successful")
```

## Automated Compliance Check

Parse command output and validate against requirements:

```python
from network_toolkit import NetworkaClient

def check_compliance(device_name):
    """Run compliance checks on a device."""
    checks = {
        "identity": "/system/identity/print",
        "uptime": "/system/resource/print",
        "firewall": "/ip/firewall/filter/print",
    }

    results = {}
    # Use context manager for efficient session reuse across checks
    with NetworkaClient() as client:
        for check_name, command in checks.items():
            result = client.run(device_name, command)
            # Example validation
            results[check_name] = {
                "passed": len(result.output) > 0,
                "output": result.output
            }

    return results

compliance = check_compliance("router1")

for check, result in compliance.items():
    status = "PASS" if result["passed"] else "FAIL"
    print(f"{check}: {status}")
```

## Backup and Download

Create a backup and download it:

```python
from pathlib import Path
from network_toolkit import NetworkaClient

client = NetworkaClient()

# Method 1: Using NetworkaClient.backup()
result = client.backup(
    target="router1",
    download=True,
    delete_remote=True,  # Clean up after download
)

if result.totals.succeeded > 0:
    print(f"Backup saved to: {result.results[0].local_path}")

# Method 2: Using DeviceSession for more control
from network_toolkit import DeviceSession

with DeviceSession("router1", client.config) as session:
    # Create backup
    session.execute_command("/system/backup/save name=mybackup")

    # Download it
    local_path = Path("./backups/router1-backup.backup")
    session.download_file(
        remote_file="mybackup.backup",
        local_path=local_path
    )

    # Delete remote backup
    session.execute_command("/file/remove mybackup.backup")

    print(f"Backup downloaded to: {local_path}")
```

## Upload and Execute Script

Upload a RouterOS script and run it:

```python
from pathlib import Path
from network_toolkit import NetworkaClient, DeviceSession

client = NetworkaClient()

script_content = """
/system identity set name=NewHostname
/log info "Script executed successfully"
"""

# Save script locally
script_file = Path("temp_script.rsc")
script_file.write_text(script_content)

try:
    with DeviceSession("router1", client.config) as session:
        # Upload script
        session.upload_file(
            local_file=script_file,
            remote_path="temp_script.rsc"
        )

        # Execute it
        output = session.execute_command("/import temp_script.rsc")
        print(f"Script output: {output}")

        # Clean up
        session.execute_command("/file/remove temp_script.rsc")
finally:
    # Clean up local file
    script_file.unlink()
```

## Configuration Diff

Compare current config against a baseline:

```python
from network_toolkit import NetworkaClient

client = NetworkaClient()

result = client.diff(
    targets="router1",
    subject="/export",
    baseline=Path("./baselines/router1-baseline.rsc"),
)

for item in result.diff_items:
    if item.has_diff:
        print(f"Drift detected on {item.device}!")
        print(item.diff_output)
    else:
        print(f"{item.device}: No drift")
```

## Error Handling Pattern

Robust error handling for production use:

```python
from network_toolkit import NetworkaClient, DeviceSession
from network_toolkit.exceptions import (
    DeviceConnectionError,
    DeviceExecutionError,
    NetworkToolkitError
)

client = NetworkaClient()

def safe_execute(device_name, command, config):
    """Execute command with comprehensive error handling."""
    try:
        with DeviceSession(device_name, config) as session:
            output = session.execute_command(command)
            return {"success": True, "output": output, "error": None}

    except DeviceConnectionError as e:
        return {
            "success": False,
            "output": None,
            "error": f"Connection failed: {e.message}"
        }

    except DeviceExecutionError as e:
        return {
            "success": False,
            "output": None,
            "error": f"Command failed: {e.message}"
        }

    except NetworkToolkitError as e:
        return {
            "success": False,
            "output": None,
            "error": f"Networka error: {e.message}"
        }

    except Exception as e:
        return {
            "success": False,
            "output": None,
            "error": f"Unexpected error: {str(e)}"
        }

result = safe_execute("router1", "/system/identity/print", client.config)
if result["success"]:
    print(f"Output: {result['output']}")
else:
    print(f"Error: {result['error']}")
```

## Credential Management

Load credentials from environment or vault:

```python
import os
from network_toolkit import NetworkaClient, DeviceSession, InteractiveCredentials

def get_credentials():
    """Load credentials from environment."""
    return InteractiveCredentials(
        username=os.getenv("DEVICE_USER", "admin"),
        password=os.getenv("DEVICE_PASSWORD", ""),
    )

client = NetworkaClient()
creds = get_credentials()

with DeviceSession("router1", client.config,
                   username_override=creds.username,
                   password_override=creds.password) as session:
    output = session.execute_command("/system/identity/print")
    print(output)
```

## Reference Implementation

See `scripts/lib_demo_networka_programmatic.py` in the repository for a complete example that demonstrates:

- Target selection strategies (config vs ad-hoc IP)
- Persistent sessions for multiple commands
- Progress tracking with Rich
- Compliance validation
- Table-formatted results
- Error handling

Run it with:

```bash
uv run scripts/lib_demo_networka_programmatic.py
```

## Next Steps

- Review the [API reference](../reference/api.md) for all available methods
- See [sessions documentation](sessions.md) for connection management details
- Check [ad-hoc targeting](adhoc-targets.md) for IP-based connections
