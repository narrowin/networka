#!/usr/bin/env python3
"""Example script demonstrating IP address functionality."""

import os
import sys
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from network_toolkit.config import load_config
from network_toolkit.ip_device import (
    create_ip_device_config,
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_list,
)


def demonstrate_ip_functionality():
    """Demonstrate the IP address functionality."""
    print("🔧 Network Toolkit IP Address Support Demo")
    print("=" * 50)

    # Test IP detection
    print("\n1. IP Address Detection:")
    test_targets = [
        "192.168.1.1",
        "192.168.1.1,192.168.1.2",
        "sw-acc1",
        "192.168.1.1,sw-acc1,192.168.1.2",
    ]

    for target in test_targets:
        is_ip = is_ip_list(target)
        print(f"   '{target}' -> IP list: {is_ip}")
        if is_ip:
            ips = extract_ips_from_target(target)
            print(f"      Extracted IPs: {ips}")

    # Show supported platforms
    print("\n2. Supported Platforms:")
    platforms = get_supported_platforms()
    for platform, description in platforms.items():
        print(f"   {platform}: {description}")

    # Create example IP device config
    print("\n3. Example IP Device Configuration:")
    ip_device = create_ip_device_config(
        ip="192.168.1.100", platform="mikrotik_routeros", port=22
    )
    print(f"   Host: {ip_device.host}")
    print(f"   Platform: {ip_device.platform}")
    print(f"   Device Type: {ip_device.device_type}")
    print(f"   Port: {ip_device.port}")
    print(f"   Description: {ip_device.description}")

    # Usage examples
    print("\n4. Command Examples:")
    print("   # Single IP address:")
    print("   nw run 192.168.1.1 '/system/clock/print' --platform mikrotik_routeros")
    print()
    print("   # Multiple IP addresses:")
    print(
        "   nw run '192.168.1.1,192.168.1.2' '/system/identity/print' --platform mikrotik_routeros"
    )
    print()
    print("   # Mixed IPs and device names:")
    print(
        "   nw run '192.168.1.1,sw-acc1' '/system/clock/print' --platform mikrotik_routeros"
    )
    print()
    print("   # Custom port:")
    print(
        "   nw run 192.168.1.1 '/system/clock/print' --platform mikrotik_routeros --port 2222"
    )
    print()
    print("   # Interactive authentication:")
    print(
        "   nw run 192.168.1.1 '/system/clock/print' --platform mikrotik_routeros --interactive-auth"
    )

    print("\n✅ IP address functionality ready to use!")
    print("\nNote: Set NT_DEFAULT_USER and NT_DEFAULT_PASSWORD environment variables")
    print("      or use --interactive-auth for authentication.")


if __name__ == "__main__":
    demonstrate_ip_functionality()
