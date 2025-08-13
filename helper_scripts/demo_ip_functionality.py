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

    # Test IP detection
    test_targets = [
        "192.168.1.1",
        "192.168.1.1,192.168.1.2",
        "sw-acc1",
        "192.168.1.1,sw-acc1,192.168.1.2",
    ]

    for target in test_targets:
        is_ip = is_ip_list(target)
        if is_ip:
            extract_ips_from_target(target)

    # Show supported platforms
    platforms = get_supported_platforms()
    for _platform, _description in platforms.items():
        pass

    # Create example IP device config
    create_ip_device_config(ip="192.168.1.100", platform="mikrotik_routeros", port=22)

    # Usage examples


if __name__ == "__main__":
    demonstrate_ip_functionality()
