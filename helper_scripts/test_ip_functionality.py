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

    # Test single IPs
    assert is_ip_address("192.168.1.1")
    assert is_ip_address("10.0.0.1")
    assert not is_ip_address("not.an.ip")
    assert not is_ip_address("device-name")

    # Test IP lists
    assert is_ip_list("192.168.1.1")
    assert is_ip_list("192.168.1.1,192.168.1.2")
    assert is_ip_list("192.168.1.1, 192.168.1.2, 192.168.1.3")
    assert not is_ip_list("device-name")
    assert not is_ip_list("192.168.1.1,device-name")


def test_ip_extraction():
    """Test IP address extraction."""

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


def test_platform_validation():
    """Test platform validation."""

    get_supported_platforms()

    assert validate_platform("mikrotik_routeros")
    assert validate_platform("cisco_iosxe")
    assert not validate_platform("invalid_platform")


if __name__ == "__main__":
    test_ip_detection()
    test_ip_extraction()
    test_platform_validation()
