#!/usr/bin/env python3
"""Run Networka SDK smoke checks on explicitly authorized lab devices.

For a live check, name the approved device and inspect the command output::

    uv run python scripts/lab_validation.py --config /path/to/lab-config --target lab-router

Use `--list` to inspect the inventory without connecting. Without `--target`
or `--tag`, the script selects every device. A pass means a command returned
nonempty output. Verify device identity and OS version in that output.
"""

import argparse

from network_toolkit import NetworkaClient


def _check_devices(client: NetworkaClient, targets: list[str]) -> int:
    print(f"Starting smoke checks for {len(targets)} devices...")
    print("-" * 60)

    success_count = 0
    failure_count = 0

    for target_name in targets:
        platform = client.devices[target_name].device_type
        print(f"Checking {target_name} ({platform})...")

        if "linux" in platform.lower():
            commands = ["uname -r", "uptime"]
        elif "mikrotik" in platform.lower() or "routeros" in platform.lower():
            commands = ["/system resource print", "/system identity print"]
        elif "cisco" in platform.lower() or "ios" in platform.lower():
            commands = ["show version", "show ip int brief"]
        else:
            print(f"  [FAIL] No validation commands for {platform}")
            failure_count += 1
            continue

        device_failed = False
        for command in commands:
            try:
                result = client.run(target=target_name, command_or_sequence=command)
            except Exception as exc:
                print(f"  [ERR] Exception running '{command}': {exc}")
                device_failed = True
                continue

            if not result.command_results:
                print(f"  [FAIL] No results returned for command '{command}'")
                device_failed = True
                break

            device_result = result.command_results[0]
            if device_result.error:
                print(f"  [FAIL] Command '{command}' failed: {device_result.error}")
                device_failed = True
                continue

            output = (device_result.output or "").strip()
            if output:
                print(f"  [PASS] {command} returned output")
                print(output)
            else:
                print(f"  [FAIL] Command '{command}' returned empty output")
                device_failed = True

        if device_failed:
            failure_count += 1
        else:
            success_count += 1

        print("-" * 60)

    print("Smoke Check Summary")
    print(f"Total Devices: {len(targets)}")
    print(f"Successful:    {success_count}")
    print(f"Failed:        {failure_count}")
    return int(failure_count > 0)


def main() -> int:
    """Load inventory, select devices, and close the client on every exit."""
    parser = argparse.ArgumentParser(description="Lab Validation Script")
    parser.add_argument("--config", help="Inventory configuration file or directory")
    parser.add_argument("--target", help="Target a specific device by name")
    parser.add_argument("--tag", help="Target devices with a specific tag")
    parser.add_argument("--list", action="store_true", help="List available devices")
    args = parser.parse_args()

    with NetworkaClient(config_path=args.config) as client:
        try:
            devices = client.devices
        except Exception as exc:
            print(f"Error loading inventory: {exc}")
            return 1

        if args.list:
            print("Available Devices:")
            for name, device in devices.items():
                print(f"  - {name} ({device.device_type})")
            return 0

        if args.target:
            if args.target not in devices:
                print(f"Error: Device '{args.target}' not found in configuration.")
                return 1
            targets = [args.target]
        elif args.tag:
            targets = [
                name
                for name, device in devices.items()
                if device.tags and args.tag in device.tags
            ]
            if not targets:
                print(f"No devices found with tag '{args.tag}'.")
                return 1
        else:
            targets = list(devices)

        if not targets:
            print("No targets selected.")
            return 1

        return _check_devices(client, targets)


if __name__ == "__main__":
    raise SystemExit(main())
