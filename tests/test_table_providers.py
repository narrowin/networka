# SPDX-License-Identifier: MIT
"""Tests for centralized table providers system."""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from network_toolkit.common.table_providers import (
    DeviceInfoTableProvider,
    DeviceListTableProvider,
    DeviceTypesInfoTableProvider,
    GlobalSequenceInfoTableProvider,
    GlobalSequencesTableProvider,
    GroupInfoTableProvider,
    GroupListTableProvider,
    SupportedPlatformsTableProvider,
    TransportInfoTableProvider,
    TransportTypesTableProvider,
    VendorSequenceInfoTableProvider,
    VendorSequencesTableProvider,
)
from network_toolkit.config import (
    DeviceConfig,
    DeviceGroup,
    GeneralConfig,
    NetworkConfig,
)
from network_toolkit.sequence_manager import SequenceRecord, SequenceSource


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
            global_command_sequences={},
        )

        provider = DeviceListTableProvider(config=config)

        assert provider.config == config

    def test_device_list_table_definition(self) -> None:
        """Test table definition for device list."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
            global_command_sequences={},
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
            global_command_sequences={},
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
            global_command_sequences={},
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
            global_command_sequences={},
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
            global_command_sequences={},
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
            global_command_sequences={},
        )

        provider = GroupListTableProvider(config=config)

        assert provider.config == config

    def test_group_list_table_definition(self) -> None:
        """Test table definition for group list."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
            global_command_sequences={},
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
            global_command_sequences={},
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
        assert definition.columns[0].header == "Transport"
        assert definition.columns[1].header == "Device Type"
        assert definition.columns[2].header == "Vendor"
        assert definition.columns[3].header == "OS/Platform"

    def test_supported_platforms_table_rows(self) -> None:
        """Test table rows for supported platforms."""
        provider = SupportedPlatformsTableProvider()

        rows = provider.get_table_rows()

        assert len(rows) > 0
        # Should include MikroTik RouterOS
        mikrotik_rows = [row for row in rows if "mikrotik" in row[2].lower()]
        assert len(mikrotik_rows) > 0

    def test_supported_platforms_verbose_info(self) -> None:
        """Test verbose info for supported platforms."""
        provider = SupportedPlatformsTableProvider()

        verbose_info = provider.get_verbose_info()

        assert verbose_info is not None
        assert "Usage Examples:" in verbose_info
        assert "scrapli_sync" in verbose_info


class TestTransportTypesTableProvider:
    """Test TransportTypesTableProvider implementation."""

    def test_transport_types_table_definition(self) -> None:
        """Test table definition for transport types."""
        provider = TransportTypesTableProvider()

        definition = provider.get_table_definition()

        assert definition.title == "Transport Types"
        assert len(definition.columns) == 4
        assert definition.columns[0].header == "Transport"
        assert definition.columns[1].header == "Library"
        assert definition.columns[2].header == "Protocol"
        assert definition.columns[3].header == "Description"

    def test_transport_types_table_rows(self) -> None:
        """Test table rows for transport types."""
        provider = TransportTypesTableProvider()

        rows = provider.get_table_rows()

        assert len(rows) >= 2
        # Should include scrapli_sync and nornir_netmiko
        transport_names = [row[0] for row in rows]
        assert "scrapli_sync" in transport_names
        assert "nornir_netmiko" in transport_names


class TestSequenceTableProviders:
    """Test sequence-related table providers."""

    def test_global_sequences_table_provider(self) -> None:
        """Test GlobalSequencesTableProvider implementation."""
        sequences = {
            "test_sequence": Mock(
                description="Test sequence",
                commands=["command1", "command2"],
                tags=["test", "system"],
            )
        }

        provider = GlobalSequencesTableProvider(sequences=sequences)

        definition = provider.get_table_definition()
        assert definition.title == "Global Command Sequences"

        rows = provider.get_table_rows()
        assert len(rows) == 1
        assert rows[0][0] == "test_sequence"
        assert rows[0][1] == "Test sequence"

    def test_vendor_sequences_table_provider(self) -> None:
        """Test VendorSequencesTableProvider implementation."""
        sequence_record = SequenceRecord(
            name="test_sequence",
            commands=["command1"],
            description="Test vendor sequence",
            category="system",
            timeout=30,
            device_types=["mikrotik_routeros"],
            source=SequenceSource(origin="builtin", path=None),
        )

        sequences = {"mikrotik_routeros": {"test_sequence": sequence_record}}

        provider = VendorSequencesTableProvider(
            sequences=sequences, vendor_filter=None, category_filter=None
        )

        definition = provider.get_table_definition()
        assert definition.title == "Vendor Command Sequences"

        rows = provider.get_table_rows()
        assert len(rows) == 1
        assert rows[0][0] == "test_sequence"
        assert rows[0][1] == "mikrotik_routeros"

    def test_global_sequence_info_provider(self) -> None:
        """Test GlobalSequenceInfoTableProvider implementation."""
        sequence = Mock(
            description="Test sequence info",
            commands=["command1", "command2"],
            tags=["test"],
        )

        provider = GlobalSequenceInfoTableProvider(
            sequence_name="test_sequence", sequence=sequence
        )

        definition = provider.get_table_definition()
        assert definition.title == "Global Sequence: test_sequence"

        rows = provider.get_table_rows()
        assert len(rows) >= 3  # Should have description, command count, tags

    def test_vendor_sequence_info_provider(self) -> None:
        """Test VendorSequenceInfoTableProvider implementation."""
        sequence_record = SequenceRecord(
            name="test_sequence",
            commands=["command1", "command2"],
            description="Test vendor sequence info",
            category="system",
            timeout=30,
            device_types=["mikrotik_routeros", "arista_eos"],
            source=SequenceSource(origin="builtin", path=None),
        )

        provider = VendorSequenceInfoTableProvider(
            sequence_name="test_sequence", sequence_record=sequence_record
        )

        definition = provider.get_table_definition()
        assert definition.title == "Vendor Sequence: test_sequence"

        rows = provider.get_table_rows()
        assert len(rows) >= 5  # Should have description, category, timeout, etc.


class TestInfoTableProviders:
    """Test info-related table providers."""

    def test_device_info_provider(self) -> None:
        """Test DeviceInfoTableProvider implementation."""
        device = DeviceConfig(
            host="192.168.1.1",
            device_type="mikrotik_routeros",
            user="admin",
            password="password",
            port=8728,
            description="Test device info",
        )

        provider = DeviceInfoTableProvider(device_name="test_device", device=device)

        definition = provider.get_table_definition()
        assert definition.title == "Device: test_device"

        rows = provider.get_table_rows()
        assert len(rows) >= 4  # Should have host, device_type, etc.

    def test_group_info_provider(self) -> None:
        """Test GroupInfoTableProvider implementation."""
        group = DeviceGroup(
            description="Test group info",
            members=["device1", "device2", "device3"],
        )

        provider = GroupInfoTableProvider(group_name="test_group", group=group)

        definition = provider.get_table_definition()
        assert definition.title == "Group: test_group"

        rows = provider.get_table_rows()
        assert len(rows) >= 2  # Should have description and device count

    def test_transport_info_provider(self) -> None:
        """Test TransportInfoTableProvider implementation."""
        provider = TransportInfoTableProvider(transport_name="scrapli_sync")

        definition = provider.get_table_definition()
        assert definition.title == "Transport: scrapli_sync"

        rows = provider.get_table_rows()
        assert len(rows) >= 3  # Should have library, protocol, description

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
            general=GeneralConfig(backup_dir="/tmp", transport="scrapli"),
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
            global_command_sequences={},
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

        # Extract all device types
        device_types = [row[1] for row in rows]

        # Should include major platforms
        assert any("mikrotik" in dt.lower() for dt in device_types)
        assert any("cisco" in dt.lower() for dt in device_types)
        assert any("arista" in dt.lower() for dt in device_types)

        # Test verbose info includes examples
        verbose_info = provider.get_verbose_info()
        assert verbose_info is not None
        assert "scrapli_sync" in str(verbose_info)

    def test_transport_types_provider_completeness(self) -> None:
        """Test that TransportTypesTableProvider covers all transports."""
        provider = TransportTypesTableProvider()

        rows = provider.get_table_rows()

        # Extract transport names
        transport_names = [row[0] for row in rows]

        # Should include core transports
        assert "scrapli_sync" in transport_names
        assert "nornir_netmiko" in transport_names

        # Test each row has required fields
        for row in rows:
            assert len(row) == 4  # transport, library, protocol, description
            assert row[0]  # transport name not empty
            assert row[3]  # description not empty


class TestTableProviderEdgeCases:
    """Test edge cases and error conditions for table providers."""

    def test_empty_data_handling(self) -> None:
        """Test providers handle empty data gracefully."""
        config = NetworkConfig(
            general=GeneralConfig(),
            devices={},
            device_groups={},
            global_command_sequences={},
        )

        # Empty devices
        provider = DeviceListTableProvider(config=config)
        assert provider.get_table_rows() == []
        assert provider.get_raw_output().strip() == ""

        # Empty groups
        provider = GroupListTableProvider(config=config)
        assert provider.get_table_rows() == []

        # Empty sequences
        provider = GlobalSequencesTableProvider(sequences={})
        assert provider.get_table_rows() == []

    def test_none_values_handling(self) -> None:
        """Test providers handle None values in data."""
        device = DeviceConfig(
            host="192.168.1.1",
            device_type="mikrotik_routeros",
            user="admin",
            password="password",
            description=None,  # None value
        )

        provider = DeviceInfoTableProvider(device_name="test_device", device=device)
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
            global_command_sequences={},
        )

        provider = DeviceListTableProvider(config=config)
        rows = provider.get_table_rows()

        assert len(rows) == 1
        assert rows[0][0] == "minimal_device"
        assert rows[0][1] == "192.168.1.100"
        assert rows[0][2] == "mikrotik_routeros"
        assert rows[0][3] == "N/A"  # No description
        assert rows[0][4] == "None"  # No tags
