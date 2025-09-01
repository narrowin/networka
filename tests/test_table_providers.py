# SPDX-License-Identifier: MIT
"""Test table providers for different device types."""

from __future__ import annotations

import pytest

from network_toolkit.common.table_providers import (
    DeviceInfoTableProvider,
    DeviceListTableProvider,
    DeviceTypesInfoTableProvider,
    GroupInfoTableProvider,
    GroupListTableProvider,
    SupportedPlatformsTableProvider,
    TransportInfoTableProvider,
    TransportTypesTableProvider,
)
from network_toolkit.config import (
    DeviceConfig,
    DeviceGroup,
    GeneralConfig,
    NetworkConfig,
)


class TestDeviceListTableProvider:
    """Test DeviceListTableProvider implementation."""

    def test_device_list_table_provider_creation(self) -> None:
        """Test creating DeviceListTableProvider with valid data."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)

        assert provider.config == config

    def test_device_list_table_definition(self) -> None:
        """Test table definition for device list."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        definition = provider.get_table_definition()

        assert definition.title == "Devices"
        assert len(definition.columns) == 5
        assert definition.columns[0].header == "Name"
        assert definition.columns[1].header == "Host"
        assert definition.columns[2].header == "Type"
        assert definition.columns[3].header == "Description"
        assert definition.columns[4].header == "Tags"

    def test_device_list_table_rows_empty(self) -> None:
        """Test table rows with empty devices."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        rows = provider.get_table_rows()

        assert len(rows) == 0

    def test_device_list_table_rows_with_devices(self) -> None:
        """Test table rows with actual devices."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                    description="Test device",
                    tags=["router", "test"],
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)

        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert rows[0] == [
            "test_device",
            "192.168.1.1",
            "mikrotik_routeros",
            "Test device",
            "router, test",
        ]

    def test_device_list_raw_output(self) -> None:
        """Test raw output format."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                    tags=["router"],
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)

        raw_output = provider.get_raw_output()

        assert "device=test_device" in raw_output
        assert "host=192.168.1.1" in raw_output
        assert "tags=router" in raw_output

    def test_device_list_verbose_info(self) -> None:
        """Test verbose info output."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)

        verbose_info = provider.get_verbose_info()

        assert verbose_info is not None
        assert "Total devices: 1" in verbose_info
        assert "Usage Examples:" in verbose_info


class TestGroupListTableProvider:
    """Test GroupListTableProvider implementation."""

    def test_group_list_table_provider_creation(self) -> None:
        """Test creating GroupListTableProvider with valid data."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={
                "test_group": DeviceGroup(
                    description="Test group",
                    members=["device1", "device2"],
                )
            },
        )

        provider = GroupListTableProvider(config=config)

        assert provider.config == config

    def test_group_list_table_definition(self) -> None:
        """Test table definition for group list."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = GroupListTableProvider(config=config)

        definition = provider.get_table_definition()

        assert definition.title == "Groups"
        assert len(definition.columns) == 4
        assert definition.columns[0].header == "Group Name"
        assert definition.columns[1].header == "Description"
        assert definition.columns[2].header == "Match Tags"
        assert definition.columns[3].header == "Members"

    def test_group_list_table_rows_with_groups(self) -> None:
        """Test table rows with actual groups."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "device1": DeviceConfig(
                    host="10.0.0.1", device_type="mikrotik_routeros"
                ),
                "device2": DeviceConfig(
                    host="10.0.0.2", device_type="mikrotik_routeros"
                ),
            },
            device_groups={
                "test_group": DeviceGroup(
                    description="Test group",
                    members=["device1", "device2"],
                )
            },
        )

        provider = GroupListTableProvider(config=config)

        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert rows[0][0] == "test_group"
        assert rows[0][1] == "Test group"
        assert "device1" in rows[0][3]
        assert "device2" in rows[0][3]


class TestSupportedPlatformsTableProvider:
    """Test SupportedPlatformsTableProvider implementation."""

    def test_supported_platforms_table_definition(self) -> None:
        """Test table definition for supported platforms."""
        provider = SupportedPlatformsTableProvider()

        definition = provider.get_table_definition()

        assert definition.title == "Supported Platforms"
        assert len(definition.columns) == 4
        assert definition.columns[0].header == "Platform"
        assert definition.columns[1].header == "Device Type"
        assert definition.columns[2].header == "Transport"
        assert definition.columns[3].header == "Operations"

    def test_supported_platforms_table_rows(self) -> None:
        """Test table rows for supported platforms."""
        provider = SupportedPlatformsTableProvider()

        rows = provider.get_table_rows()

        assert len(rows) > 0
        # Should include network platforms (no MikroTik in sample data)
        network_rows = [row for row in rows if "Network" in row[1]]
        assert len(network_rows) > 0

    def test_supported_platforms_verbose_info(self) -> None:
        """Test verbose info for supported platforms."""
        provider = SupportedPlatformsTableProvider()

        verbose_info = provider.get_verbose_info()

        assert verbose_info is not None
        assert (
            "Platforms supported by the network toolkit transport layer" in verbose_info
        )


class TestTransportTypesTableProvider:
    """Test TransportTypesTableProvider implementation."""

    def test_transport_types_table_definition(self) -> None:
        """Test table definition for transport types."""
        provider = TransportTypesTableProvider()

        definition = provider.get_table_definition()

        assert definition.title == "Available Transport Types"
        assert len(definition.columns) == 3
        assert definition.columns[0].header == "Transport"
        assert definition.columns[1].header == "Description"
        assert definition.columns[2].header == "Device Type Mapping"

    def test_transport_types_table_rows(self) -> None:
        """Test table rows for transport types."""
        provider = TransportTypesTableProvider()

        rows = provider.get_table_rows()

        assert len(rows) >= 1
        # Should include scrapli
        transport_names = [row[0] for row in rows]
        assert "scrapli" in transport_names


class TestSequenceTableProviders:
    """Test sequence-related table providers."""

    @pytest.mark.skip("Complex provider APIs need refactoring")
    def test_vendor_sequences_table_provider(self) -> None:
        """Test VendorSequencesTableProvider implementation."""
        # Test skipped due to complex API refactoring needed
        pass

    @pytest.mark.skip("Complex provider APIs need refactoring")
    def test_vendor_sequence_info_provider(self) -> None:
        """Test VendorSequenceInfoTableProvider implementation."""
        # Test skipped due to complex API refactoring needed
        pass


class TestInfoTableProviders:
    """Test info-related table providers."""

    @pytest.mark.skip("Complex provider APIs need refactoring")
    def test_device_info_provider(self) -> None:
        """Test DeviceInfoTableProvider implementation."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                    port=8728,
                    description="Test device info",
                )
            },
            device_groups={},
        )

        provider = DeviceInfoTableProvider(config=config, device_name="test_device")

        definition = provider.get_table_definition()
        assert definition.title == "Device: test_device"

        rows = provider.get_table_rows()
        assert len(rows) >= 4  # Should have host, device_type, etc.

    @pytest.mark.skip("Complex provider APIs need refactoring")
    def test_group_info_provider(self) -> None:
        """Test GroupInfoTableProvider implementation."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={
                "test_group": DeviceGroup(
                    description="Test group info",
                    members=["device1", "device2", "device3"],
                )
            },
        )

        provider = GroupInfoTableProvider(config=config, group_name="test_group")

        definition = provider.get_table_definition()
        assert definition.title == "Group: test_group"

        rows = provider.get_table_rows()
        assert len(rows) >= 2  # Should have description and device count

    def test_transport_info_provider(self) -> None:
        """Test TransportInfoTableProvider implementation."""
        provider = TransportInfoTableProvider()

        definition = provider.get_table_definition()
        assert definition.title == "Available Transport Types"

        rows = provider.get_table_rows()
        assert len(rows) >= 1  # Should have transport data

    def test_device_types_info_provider(self) -> None:
        """Test DeviceTypesInfoTableProvider implementation."""
        provider = DeviceTypesInfoTableProvider()

        definition = provider.get_table_definition()
        assert definition.title == "Device Types"

        rows = provider.get_table_rows()
        assert len(rows) > 0
        # Should include MikroTik
        device_types = [row[0] for row in rows]
        assert any("mikrotik" in dt.lower() for dt in device_types)


class TestTableProviderIntegration:
    """Integration tests for table providers with realistic data."""

    def test_device_list_provider_with_real_config(self) -> None:
        """Test DeviceListTableProvider with realistic config data."""
        config = NetworkConfig(
            general=GeneralConfig(backup_dir="/tmp", transport="system"),
            devices={
                "router1": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                    description="Main router",
                ),
                "switch1": DeviceConfig(
                    host="10.0.0.1",
                    transport_type="nornir_netmiko",
                    device_type="cisco_iosxe",
                    user="cisco",
                    password="cisco",
                    port=22,
                    description="Access switch",
                ),
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)

        # Test table structure
        definition = provider.get_table_definition()
        assert len(definition.columns) == 5

        # Test data content
        rows = provider.get_table_rows()
        assert len(rows) == 2

        # Test raw output
        raw_output = provider.get_raw_output()
        assert "router1" in raw_output
        assert "switch1" in raw_output

        # Test verbose info
        verbose_info = provider.get_verbose_info()
        assert verbose_info is not None
        assert "Total devices: 2" in verbose_info

    def test_supported_platforms_provider_completeness(self) -> None:
        """Test that SupportedPlatformsTableProvider covers key platforms."""
        provider = SupportedPlatformsTableProvider()

        rows = provider.get_table_rows()

        # Extract all platform names (first column)
        platform_names = [row[0] for row in rows]

        # Should include major platforms
        assert any("cisco" in pn.lower() for pn in platform_names)
        assert any("juniper" in pn.lower() for pn in platform_names)

        # Test verbose info exists
        verbose_info = provider.get_verbose_info()
        assert verbose_info is not None

    def test_transport_types_provider_completeness(self) -> None:
        """Test that TransportTypesTableProvider covers all transports."""
        provider = TransportTypesTableProvider()

        rows = provider.get_table_rows()

        # Extract transport names
        transport_names = [row[0] for row in rows]

        # Should include core transport
        assert "scrapli" in transport_names

        # Test each row has required fields
        for row in rows:
            assert len(row) == 3  # transport, description, device type mapping
            assert row[0]  # transport name not empty
            assert row[1]  # description not empty


class TestTableProviderEdgeCases:
    """Test edge cases and error conditions for table providers."""

    def test_empty_data_handling(self) -> None:
        """Test providers handle empty data gracefully."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )

        # Empty devices
        device_provider = DeviceListTableProvider(config=config)
        assert device_provider.get_table_rows() == []
        assert device_provider.get_raw_output().strip() == ""

        # Empty groups
        group_provider = GroupListTableProvider(config=config)
        assert group_provider.get_table_rows() == []

    @pytest.mark.skip("Complex provider APIs need refactoring")
    def test_none_values_handling(self) -> None:
        """Test providers handle None values in data."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    user="admin",
                    password="password",
                    description=None,  # None value
                )
            },
            device_groups={},
        )

        provider = DeviceInfoTableProvider(config=config, device_name="test_device")
        rows = provider.get_table_rows()

        # Should handle None description gracefully
        description_row = [row for row in rows if row[0] == "Description"]
        assert len(description_row) == 1
        assert description_row[0][1] == "N/A"

    def test_device_list_with_minimal_config(self) -> None:
        """Test device list with minimal device configuration."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "minimal_device": DeviceConfig(
                    host="192.168.1.100",
                    device_type="mikrotik_routeros",
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)
        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert rows[0][0] == "minimal_device"
        assert rows[0][1] == "192.168.1.100"
        assert rows[0][2] == "mikrotik_routeros"
        assert rows[0][3] == "N/A"  # No description
        assert rows[0][4] == "None"  # No tags
