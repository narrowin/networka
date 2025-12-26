#!/usr/bin/env python3
"""
Lab Validation Script
=====================

This script performs basic health and validation checks on lab devices using the
Networka library. It is designed to be simple, robust, and easy to extend.

Usage:
    python3 scripts/lab_validation.py [options]

Options:
    --target <name>   Target a specific device by name.
    --tag <tag>       Target devices with a specific tag.
    --list            List available devices and exit.

"""

import argparse
import sys

from network_toolkit import NetworkaClient
from network_toolkit.api.run import RunResult


def main() -> None:
    """Main entry point for the lab validation script."""
    parser = argparse.ArgumentParser(description="Lab Validation Script")
    parser.add_argument("--target", help="Target a specific device by name")
    parser.add_argument("--tag", help="Target devices with a specific tag")
    parser.add_argument("--list", action="store_true", help="List available devices")
    args = parser.parse_args()

    # Initialize the client
    # The client automatically loads configuration from standard locations
    try:
        client = NetworkaClient()
    except Exception as e:
        print(f"Error initializing Networka client: {e}")
        sys.exit(1)

    # List devices if requested
    if args.list:
        print("Available Devices:")
        for name, device in client.devices.items():
            print(f"  - {name} ({device.platform})")
        return

    # Determine targets
    targets: list[str] = []
    if args.target:
        if args.target in client.devices:
            targets.append(args.target)
        else:
            print(f"Error: Device '{args.target}' not found in configuration.")
            sys.exit(1)
    elif args.tag:
        for name, device in client.devices.items():
            if device.tags and args.tag in device.tags:
                targets.append(name)
        if not targets:
            print(f"No devices found with tag '{args.tag}'.")
            sys.exit(1)
    else:
        # Default to all devices if no specific target is given
        targets = list(client.devices.keys())

    if not targets:
        print("No targets selected.")
        return

    print(f"Starting validation for {len(targets)} devices...")
    print("-" * 60)

    # Execute checks
    success_count = 0
    failure_count = 0

    for target_name in targets:
        device_config = client.devices[target_name]
        platform = device_config.platform

        print(f"Checking {target_name} ({platform})...")

        # Define commands based on platform
        commands: list[str] = []
        if "linux" in platform.lower():
            commands = ["uname -r", "uptime"]
        elif "mikrotik" in platform.lower() or "routeros" in platform.lower():
            commands = ["/system resource print", "/system identity print"]
        elif "cisco" in platform.lower() or "ios" in platform.lower():
            commands = ["show version", "show ip int brief"]
        else:
            print(f"  [WARN] Unknown platform '{platform}', skipping specific checks.")
            continue

        # Run commands
        device_failed = False
        for cmd in commands:
            try:
                # Run the command using the client
                # We use the client.run() method which handles connection management
                result: RunResult = client.run(
                    target=target_name, command_or_sequence=cmd
                )

                # Process results
                # client.run returns a RunResult object which contains a list of DeviceCommandResult objects
                # Since we targeted a single device, we expect one result
                if not result.command_results:
                    print(f"  [FAIL] No results returned for command '{cmd}'")
                    device_failed = True
                    break

                device_result = result.command_results[0]

                if device_result.error:
                    print(f"  [FAIL] Command '{cmd}' failed: {device_result.error}")
                    device_failed = True
                else:
                    # Basic validation: check if output is not empty
                    output = (
                        device_result.output.strip() if device_result.output else ""
                    )
                    if output:
                        print(f"  [PASS] {cmd}")
                        # Optional: Print first line of output for verification
                        first_line = output.split("\n")[0]
                        print(f"         > {first_line[:50]}...")
                    else:
                        print(f"  [WARN] Command '{cmd}' returned empty output")

            except Exception as e:
                print(f"  [ERR] Exception running '{cmd}': {e}")
                device_failed = True

        if device_failed:
            failure_count += 1
        else:
            success_count += 1

        print("-" * 60)

    # Summary
    print("Validation Summary")
    print(f"Total Devices: {len(targets)}")
    print(f"Successful:    {success_count}")
    print(f"Failed:        {failure_count}")

    if failure_count > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
