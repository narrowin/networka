#!/usr/bin/env python3
"""Simple test script to verify IP device functionality."""

from network_toolkit.ip_device import (
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_address,
    is_ip_list,
    validate_platform,
)


def test_ip_detection():
    """Test IP address detection."""
    print("Testing IP address detection...")

    # Test single IPs
    assert is_ip_address("192.168.1.1") == True
    assert is_ip_address("10.0.0.1") == True
    assert is_ip_address("not.an.ip") == False
    assert is_ip_address("device-name") == False

    # Test IP lists
    assert is_ip_list("192.168.1.1") == True
    assert is_ip_list("192.168.1.1,192.168.1.2") == True
    assert is_ip_list("192.168.1.1, 192.168.1.2, 192.168.1.3") == True
    assert is_ip_list("device-name") == False
    assert is_ip_list("192.168.1.1,device-name") == False

    print("✓ IP detection tests passed")


def test_ip_extraction():
    """Test IP address extraction."""
    print("Testing IP address extraction...")

    assert extract_ips_from_target("192.168.1.1") == ["192.168.1.1"]
    assert extract_ips_from_target("192.168.1.1,192.168.1.2") == [
        "192.168.1.1",
        "192.168.1.2",
    ]
    assert extract_ips_from_target("192.168.1.1, 192.168.1.2, 192.168.1.3") == [
        "192.168.1.1",
        "192.168.1.2",
        "192.168.1.3",
    ]

    print("✓ IP extraction tests passed")


def test_platform_validation():
    """Test platform validation."""
    print("Testing platform validation...")

    platforms = get_supported_platforms()
    print(f"Supported platforms: {list(platforms.keys())}")

    assert validate_platform("mikrotik_routeros") == True
    assert validate_platform("cisco_iosxe") == True
    assert validate_platform("invalid_platform") == False

    print("✓ Platform validation tests passed")


if __name__ == "__main__":
    test_ip_detection()
    test_ip_extraction()
    test_platform_validation()
    print("\n🎉 All tests passed!")
