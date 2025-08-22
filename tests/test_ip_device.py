# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for IP device functionality."""

from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.config import NetworkConfig
from network_toolkit.ip_device import (
    create_ip_based_config,
    create_ip_device_config,
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_address,
    is_ip_list,
    validate_platform,
)


class TestIPDetection:
    """Test IP address detection functions."""

    def test_is_ip_address_valid_ipv4(self) -> None:
        """Test valid IPv4 addresses."""
        assert is_ip_address("192.168.1.1")
        assert is_ip_address("10.0.0.1")
        assert is_ip_address("172.16.0.1")
        assert is_ip_address("127.0.0.1")

    def test_is_ip_address_valid_ipv6(self) -> None:
        """Test valid IPv6 addresses."""
        assert is_ip_address("2001:db8::1")
        assert is_ip_address("::1")
        assert is_ip_address("::")

    def test_is_ip_address_invalid(self) -> None:
        """Test invalid IP addresses."""
        assert not is_ip_address("not.an.ip")
        assert not is_ip_address("device-name")
        assert not is_ip_address("192.168.1")
        assert not is_ip_address("192.168.1.256")

    def test_is_ip_list_single_ip(self) -> None:
        """Test single IP address detection."""
        assert is_ip_list("192.168.1.1")
        assert is_ip_list("10.0.0.1")
        assert not is_ip_list("device-name")

    def test_is_ip_list_multiple_ips(self) -> None:
        """Test multiple IP addresses detection."""
        assert is_ip_list("192.168.1.1,192.168.1.2")
        assert is_ip_list("192.168.1.1, 192.168.1.2, 192.168.1.3")

    def test_is_ip_list_mixed_invalid(self) -> None:
        """Test mixed valid and invalid addresses."""
        assert not is_ip_list("192.168.1.1,device-name")
        assert not is_ip_list("device-name,192.168.1.1")

    def test_extract_ips_from_target_single(self) -> None:
        """Test IP extraction from single IP."""
        result = extract_ips_from_target("192.168.1.1")
        assert result == ["192.168.1.1"]

    def test_extract_ips_from_target_multiple(self) -> None:
        """Test IP extraction from multiple IPs."""
        result = extract_ips_from_target("192.168.1.1,192.168.1.2")
        assert result == ["192.168.1.1", "192.168.1.2"]

    def test_extract_ips_from_target_with_spaces(self) -> None:
        """Test IP extraction with spaces."""
        result = extract_ips_from_target("192.168.1.1, 192.168.1.2, 192.168.1.3")
        assert result == ["192.168.1.1", "192.168.1.2", "192.168.1.3"]


class TestPlatformValidation:
    """Test platform validation functions."""

    def test_get_supported_platforms(self) -> None:
        """Test getting supported platforms."""
        platforms = get_supported_platforms()
        assert isinstance(platforms, dict)
        assert "mikrotik_routeros" in platforms
        assert "cisco_iosxe" in platforms

    def test_validate_platform_valid(self) -> None:
        """Test validation of valid platforms."""
        assert validate_platform("mikrotik_routeros")
        assert validate_platform("cisco_iosxe")
        assert validate_platform("linux")

    def test_validate_platform_invalid(self) -> None:
        """Test validation of invalid platforms."""
        assert not validate_platform("invalid_platform")
        assert not validate_platform("unknown")
        assert not validate_platform("")


class TestIPDeviceConfig:
    """Test IP device configuration creation."""

    def test_create_ip_device_config_basic(self) -> None:
        """Test basic IP device config creation."""
        config = create_ip_device_config("192.168.1.1", "mikrotik_routeros")

        assert config.host == "192.168.1.1"
        assert (
            config.platform is None
        )  # platform is hardware architecture, not device type
        assert config.device_type == "mikrotik_routeros"
        assert config.port == 22
        assert config.description is not None
        assert "192.168.1.1" in config.description

    def test_create_ip_device_config_with_custom_type(self) -> None:
        """Test IP device config with custom hardware platform."""
        config = create_ip_device_config(
            "192.168.1.1", "mikrotik_routeros", hardware_platform="arm"
        )

        assert config.device_type == "mikrotik_routeros"
        assert config.platform == "arm"

    def test_create_ip_device_config_with_custom_port(self) -> None:
        """Test IP device config with custom port."""
        config = create_ip_device_config("192.168.1.1", "mikrotik_routeros", port=2222)

        assert config.port == 2222

    def test_create_ip_device_config_invalid_ip(self) -> None:
        """Test IP device config with invalid IP."""
        with pytest.raises(ValueError, match="Invalid IP address"):
            create_ip_device_config("not.an.ip", "mikrotik_routeros")

    def test_create_ip_device_config_ipv6(self) -> None:
        """Test IP device config with IPv6."""
        config = create_ip_device_config("2001:db8::1", "mikrotik_routeros")

        assert config.host == "2001:db8::1"
        assert (
            config.platform is None
        )  # platform is hardware architecture, not device type


class TestIPBasedConfig:
    """Test IP-based configuration creation."""

    @pytest.fixture
    def base_config(self, sample_config_data: dict[str, Any]) -> NetworkConfig:
        """Create a base configuration for testing."""
        return NetworkConfig.model_validate(sample_config_data)

    def test_create_ip_based_config_single_ip(self, base_config: NetworkConfig) -> None:
        """Test creating config with single IP."""
        ips = ["192.168.1.1"]
        config = create_ip_based_config(ips, "mikrotik_routeros", base_config)

        assert config is not None
        assert config.devices is not None
        assert "ip_192_168_1_1" in config.devices

        ip_device = config.devices["ip_192_168_1_1"]
        assert ip_device.host == "192.168.1.1"
        assert (
            ip_device.platform is None
        )  # platform is hardware architecture, not device type
        assert ip_device.device_type == "mikrotik_routeros"

    def test_create_ip_based_config_multiple_ips(
        self, base_config: NetworkConfig
    ) -> None:
        """Test creating config with multiple IPs."""
        ips = ["192.168.1.1", "192.168.1.2", "192.168.1.3"]
        config = create_ip_based_config(ips, "mikrotik_routeros", base_config)

        assert config.devices is not None
        assert "ip_192_168_1_1" in config.devices
        assert "ip_192_168_1_2" in config.devices
        assert "ip_192_168_1_3" in config.devices

    def test_create_ip_based_config_with_custom_port(
        self, base_config: NetworkConfig
    ) -> None:
        """Test creating config with custom port."""
        ips = ["192.168.1.1"]
        config = create_ip_based_config(
            ips, "mikrotik_routeros", base_config, port=2222
        )

        assert config.devices is not None
        ip_device = config.devices["ip_192_168_1_1"]
        assert ip_device.port == 2222
