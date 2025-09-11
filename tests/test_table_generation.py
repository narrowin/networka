# SPDX-License-Identifier: MIT
"""Tests for table generation and formatting functionality."""

from __future__ import annotations

from network_toolkit.common.table_providers import (
    DeviceListTableProvider,
    GroupListTableProvider,
    SupportedPlatformsTableProvider,
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

    def test_device_list_provider_creation(self) -> None:
        """Test creating a DeviceListTableProvider."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)
        assert provider.config == config

    def test_device_list_table_definition(self) -> None:
        """Test table definition structure."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        definition = provider.get_table_definition()
        assert definition.title == "Devices"
        assert len(definition.columns) >= 3

    def test_device_list_empty_data(self) -> None:
        """Test handling of empty device data."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        rows = provider.get_table_rows()
        assert rows == []

    def test_device_list_with_devices(self) -> None:
        """Test device list with actual devices."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "router1": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    description="Test router",
                ),
                "switch1": DeviceConfig(
                    host="10.0.0.1",
                    device_type="cisco_iosxe",
                    tags=["switch", "access"],
                ),
            },
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        rows = provider.get_table_rows()
        assert len(rows) == 2
        assert any("router1" in row for row in rows)
        assert any("switch1" in row for row in rows)

    def test_device_list_raw_output(self) -> None:
        """Test raw output generation."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.100",
                    device_type="mikrotik_routeros",
                )
            },
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        raw_output = provider.get_raw_output()
        assert "test_device" in raw_output
        assert "192.168.1.100" in raw_output

    def test_device_list_verbose_info(self) -> None:
        """Test verbose information generation."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "device1": DeviceConfig(
                    host="10.0.0.1", device_type="mikrotik_routeros"
                ),
                "device2": DeviceConfig(host="10.0.0.2", device_type="cisco_iosxe"),
            },
            device_groups={},
        )
        provider = DeviceListTableProvider(config=config)

        verbose_info = provider.get_verbose_info()
        assert verbose_info is not None
        assert "Total devices: 2" in verbose_info


class TestGroupListTableProvider:
    """Test GroupListTableProvider implementation."""

    def test_group_list_provider_creation(self) -> None:
        """Test creating a GroupListTableProvider."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )

        provider = GroupListTableProvider(config=config)
        assert provider.config == config

    def test_group_list_table_definition(self) -> None:
        """Test table definition structure."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = GroupListTableProvider(config=config)

        definition = provider.get_table_definition()
        assert definition.title == "Groups"
        assert len(definition.columns) >= 3

    def test_group_list_empty_data(self) -> None:
        """Test handling of empty group data."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )
        provider = GroupListTableProvider(config=config)

        rows = provider.get_table_rows()
        assert rows == []

    def test_group_list_with_groups(self) -> None:
        """Test group list with actual groups."""
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
                "routers": DeviceGroup(
                    description="All routers",
                    members=["device1", "device2"],
                ),
                "switches": DeviceGroup(
                    description="All switches",
                    match_tags=["switch"],
                ),
            },
        )
        provider = GroupListTableProvider(config=config)

        rows = provider.get_table_rows()
        assert len(rows) == 2
        assert any("routers" in row for row in rows)
        assert any("switches" in row for row in rows)


class TestSupportedPlatformsTableProvider:
    """Test SupportedPlatformsTableProvider implementation."""

    def test_supported_platforms_provider_creation(self) -> None:
        """Test creating a SupportedPlatformsTableProvider."""
        provider = SupportedPlatformsTableProvider()
        assert provider is not None

    def test_supported_platforms_table_definition(self) -> None:
        """Test table definition structure."""
        provider = SupportedPlatformsTableProvider()

        definition = provider.get_table_definition()
        assert definition.title == "Supported Platforms"
        assert len(definition.columns) >= 3

    def test_supported_platforms_has_data(self) -> None:
        """Test that supported platforms returns data."""
        provider = SupportedPlatformsTableProvider()

        rows = provider.get_table_rows()
        assert len(rows) > 0
        # Should include network platforms
        assert any("cisco" in str(row).lower() for row in rows)

    def test_supported_platforms_verbose_info(self) -> None:
        """Test verbose information generation."""
        provider = SupportedPlatformsTableProvider()

        verbose_info = provider.get_verbose_info()
        if verbose_info:  # May be None for some providers
            assert isinstance(verbose_info, list)


class TestTransportTypesTableProvider:
    """Test TransportTypesTableProvider implementation."""

    def test_transport_types_provider_creation(self) -> None:
        """Test creating a TransportTypesTableProvider."""
        provider = TransportTypesTableProvider()
        assert provider is not None

    def test_transport_types_table_definition(self) -> None:
        """Test table definition structure."""
        provider = TransportTypesTableProvider()

        definition = provider.get_table_definition()
        assert definition.title == "Available Transport Types"
        assert len(definition.columns) >= 3

    def test_transport_types_has_data(self) -> None:
        """Test that transport types returns data."""
        provider = TransportTypesTableProvider()

        rows = provider.get_table_rows()
        assert len(rows) > 0
        # Should include scrapli
        transport_names = [row[0] for row in rows]
        assert "scrapli" in transport_names

    def test_transport_types_raw_output(self) -> None:
        """Test raw output generation."""
        provider = TransportTypesTableProvider()

        raw_output = provider.get_raw_output()
        assert "scrapli" in raw_output


class TestTableProviderIntegration:
    """Integration tests for table providers working together."""

    def test_providers_handle_edge_cases(self) -> None:
        """Test that providers handle edge cases gracefully."""
        # Empty configuration
        empty_config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )

        # All providers should handle empty data
        device_provider = DeviceListTableProvider(config=empty_config)
        assert device_provider.get_table_rows() == []

        group_provider = GroupListTableProvider(config=empty_config)
        assert group_provider.get_table_rows() == []

        # Platform and transport providers should still return data
        platform_provider = SupportedPlatformsTableProvider()
        assert len(platform_provider.get_table_rows()) > 0

        transport_provider = TransportTypesTableProvider()
        assert len(transport_provider.get_table_rows()) > 0

    def test_table_definitions_are_consistent(self) -> None:
        """Test that table definitions follow consistent patterns."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
        )

        providers = [
            DeviceListTableProvider(config=config),
            GroupListTableProvider(config=config),
            SupportedPlatformsTableProvider(),
            TransportTypesTableProvider(),
        ]

        for provider in providers:
            definition = provider.get_table_definition()
            # All should have a title
            assert definition.title
            # All should have columns
            assert len(definition.columns) > 0
            # All columns should have headers
            for column in definition.columns:
                assert column.header


class TestTableProviderErrorHandling:
    """Test error handling in table providers."""

    def test_device_provider_with_minimal_device_config(self) -> None:
        """Test device provider with minimal device configuration."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={
                "minimal": DeviceConfig(
                    host="192.168.1.1",
                    device_type="mikrotik_routeros",
                    # Only required fields
                )
            },
            device_groups={},
        )

        provider = DeviceListTableProvider(config=config)
        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert "minimal" in rows[0]
        assert "192.168.1.1" in rows[0]

    def test_group_provider_with_empty_members(self) -> None:
        """Test group provider with groups that have no members."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={
                "empty_group": DeviceGroup(
                    description="Empty group",
                    members=[],  # Empty members list
                ),
            },
        )

        provider = GroupListTableProvider(config=config)
        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert "empty_group" in rows[0]
        assert "Empty group" in rows[0]
