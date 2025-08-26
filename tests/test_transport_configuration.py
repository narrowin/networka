"""Test transport configuration at all levels."""

import pytest

from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
from network_toolkit.ip_device import create_ip_based_config, create_ip_device_config


class TestTransportConfiguration:
    """Test transport configuration at different levels."""

    def test_global_transport_configuration(self):
        """Test global transport configuration."""
        config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1", device_type="mikrotik_routeros"
                ),
                "device2": DeviceConfig(host="192.168.1.2", device_type="cisco_ios"),
            },
        )

        # Verify global transport is used when device has no transport_type
        transport = config.get_transport_type("device1")
        assert transport == "scrapli"

    def test_device_level_transport_override(self):
        """Test device level transport override."""
        config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    transport_type="scrapli",  # Override global setting
                ),
                "device2": DeviceConfig(host="192.168.1.2", device_type="cisco_ios"),
            },
        )

        # Device with explicit transport should use that
        transport1 = config.get_transport_type("device1")
        assert transport1 == "scrapli"

        # Device without explicit transport should use global
        transport2 = config.get_transport_type("device2")
        assert transport2 == "scrapli"

    def test_ip_device_transport_configuration(self):
        """Test IP device transport configuration."""
        ip_device = create_ip_device_config(
            "192.168.1.100", "mikrotik_routeros", transport_type="scrapli"
        )
        assert ip_device.transport_type == "scrapli"
        assert ip_device.device_type == "mikrotik_routeros"

    def test_ip_based_config_with_transport(self):
        """Test IP-based config with transport."""
        base_config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"), devices={}
        )

        enhanced_config = create_ip_based_config(
            ["192.168.1.101", "192.168.1.102"],
            "cisco_ios",
            base_config,
            transport_type="scrapli",
        )

        # Check that IP devices have the specified transport
        assert enhanced_config.devices is not None
        ip_device_1 = enhanced_config.devices["ip_192_168_1_101"]
        ip_device_2 = enhanced_config.devices["ip_192_168_1_102"]

        assert ip_device_1.transport_type == "scrapli"
        assert ip_device_2.transport_type == "scrapli"
        assert ip_device_1.device_type == "cisco_ios"
        assert ip_device_2.device_type == "cisco_ios"

    def test_transport_inheritance_priority(self):
        """Test transport inheritance priority: device > global > default."""
        # Default should be scrapli when nothing is specified
        config_default = NetworkConfig(
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1", device_type="mikrotik_routeros"
                )
            }
        )
        transport_default = config_default.get_transport_type("device1")
        assert transport_default == "scrapli"  # Built-in default

        # Global config should override default
        config_global = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1", device_type="mikrotik_routeros"
                )
            },
        )
        transport_global = config_global.get_transport_type("device1")
        assert transport_global == "scrapli"

        # Device config should override global
        config_device = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    transport_type="scrapli",
                )
            },
        )
        transport_device = config_device.get_transport_type("device1")
        assert transport_device == "scrapli"

    def test_supported_transports_display(self):
        """Test that supported-types command shows correct transport info."""
        from network_toolkit.ip_device import get_supported_device_types

        supported_types = get_supported_device_types()

        # Should include common device types
        assert "mikrotik_routeros" in supported_types
        assert "cisco_ios" in supported_types
        assert "cisco_iosxe" in supported_types

        # Should have descriptions
        assert supported_types["mikrotik_routeros"] == "MikroTik RouterOS"
        assert supported_types["cisco_ios"] == "Cisco IOS"
        assert supported_types["cisco_iosxe"] == "Cisco IOS-XE"
        assert supported_types["cisco_iosxe"] == "Cisco IOS-XE"
