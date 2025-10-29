"""Tests for completion helper functions."""

from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.commands.complete import (
    _list_commands,
    _list_devices,
    _list_groups,
    _list_sequence_groups,
    _list_sequences,
    _list_tags,
)
from network_toolkit.config import DeviceConfig, NetworkConfig


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock NetworkConfig for testing."""
    config = MagicMock(spec=NetworkConfig)

    # Setup devices
    device1 = MagicMock(spec=DeviceConfig)
    device1.tags = ["switch", "office"]
    device1.device_type = "mikrotik_routeros"
    device1.command_sequences = {"test_seq": ["cmd1", "cmd2"]}

    device2 = MagicMock(spec=DeviceConfig)
    device2.tags = ["router", "edge"]
    device2.device_type = "cisco_iosxe"
    device2.command_sequences = {"cisco_seq": ["show version"]}

    config.devices = {"sw-acc1": device1, "rt-edge1": device2}

    # Setup groups
    config.device_groups = {
        "office_switches": ["sw-acc1"],
        "edge_routers": ["rt-edge1"],
    }

    # Setup sequence groups
    config.command_sequence_groups = {
        "monitoring": ["health_check", "status"],
        "maintenance": ["backup", "update"],
    }

    # Setup global command sequences (vendor-agnostic)
    config.global_command_sequences = {
        "global_health": MagicMock(commands=["global health cmd"]),
        "global_backup": MagicMock(commands=["global backup cmd"]),
    }

    # Setup get_group_members method
    config.get_group_members.return_value = ["sw-acc1"]

    return config


class TestListCommands:
    """Test _list_commands function."""

    def test_list_commands_returns_expected_commands(self) -> None:
        """Test that all expected CLI commands are returned."""
        commands = _list_commands()

        expected_commands = [
            "info",
            "run",
            "upload",
            "download",
            "backup",
            "firmware",
            "cli",
            "diff",
            "list",
            "config",
            "schema",
            "complete",
        ]

        assert commands == expected_commands

    def test_list_commands_returns_list(self) -> None:
        """Test that _list_commands returns a list."""
        result = _list_commands()
        assert isinstance(result, list)
        assert len(result) > 0


class TestListDevices:
    """Test _list_devices function."""

    def test_list_devices_with_devices(self, mock_config: MagicMock) -> None:
        """Test listing devices when devices exist."""
        devices = _list_devices(mock_config)

        assert devices == ["sw-acc1", "rt-edge1"]

    def test_list_devices_with_empty_config(self) -> None:
        """Test listing devices when no devices exist."""
        config = MagicMock(spec=NetworkConfig)
        config.devices = None

        devices = _list_devices(config)
        assert devices == []

    def test_list_devices_with_empty_devices_dict(self) -> None:
        """Test listing devices with empty devices dictionary."""
        config = MagicMock(spec=NetworkConfig)
        config.devices = {}

        devices = _list_devices(config)
        assert devices == []


class TestListGroups:
    """Test _list_groups function."""

    def test_list_groups_with_groups(self, mock_config: MagicMock) -> None:
        """Test listing groups when groups exist."""
        groups = _list_groups(mock_config)

        assert groups == ["office_switches", "edge_routers"]

    def test_list_groups_with_empty_config(self) -> None:
        """Test listing groups when no groups exist."""
        config = MagicMock(spec=NetworkConfig)
        config.device_groups = None

        groups = _list_groups(config)
        assert groups == []

    def test_list_groups_with_empty_groups_dict(self) -> None:
        """Test listing groups with empty groups dictionary."""
        config = MagicMock(spec=NetworkConfig)
        config.device_groups = {}

        groups = _list_groups(config)
        assert groups == []


class TestListSequenceGroups:
    """Test _list_sequence_groups function."""

    def test_list_sequence_groups_with_groups(self, mock_config: MagicMock) -> None:
        """Test listing sequence groups when they exist."""
        seq_groups = _list_sequence_groups(mock_config)

        assert seq_groups == ["monitoring", "maintenance"]

    def test_list_sequence_groups_with_empty_config(self) -> None:
        """Test listing sequence groups when none exist."""
        config = MagicMock(spec=NetworkConfig)
        config.command_sequence_groups = None

        seq_groups = _list_sequence_groups(config)
        assert seq_groups == []


class TestListTags:
    """Test _list_tags function."""

    def test_list_tags_with_devices(self, mock_config: MagicMock) -> None:
        """Test listing tags when devices have tags."""
        tags = _list_tags(mock_config)

        # Should be sorted
        assert tags == ["edge", "office", "router", "switch"]

    def test_list_tags_with_no_devices(self) -> None:
        """Test listing tags when no devices exist."""
        config = MagicMock(spec=NetworkConfig)
        config.devices = None

        tags = _list_tags(config)
        assert tags == []

    def test_list_tags_with_devices_no_tags(self) -> None:
        """Test listing tags when devices have no tags."""
        config = MagicMock(spec=NetworkConfig)
        device = MagicMock(spec=DeviceConfig)
        device.tags = None
        config.devices = {"test_device": device}

        tags = _list_tags(config)
        assert tags == []


class TestListSequences:
    """Test _list_sequences function."""

    def test_list_sequences_global_only(self, mock_config: MagicMock) -> None:
        """Test listing sequences when only global sequences exist."""
        mock_config.devices = None

        with patch("network_toolkit.commands.complete.SequenceManager"):
            sequences = _list_sequences(mock_config, target=None)

            assert "global_health" in sequences
            assert "global_backup" in sequences

    def test_list_sequences_with_device_target(self, mock_config: MagicMock) -> None:
        """Test listing sequences for specific device."""
        with patch("network_toolkit.commands.complete.SequenceManager") as mock_sm:
            mock_sm_instance = MagicMock()
            mock_sm.return_value = mock_sm_instance
            mock_sm_instance.list_vendor_sequences.return_value = {
                "vendor_seq": ["vendor_cmd"]
            }

            sequences = _list_sequences(mock_config, target="sw-acc1")

            # Should include global, device-specific, and vendor sequences
            assert "global_health" in sequences
            assert "test_seq" in sequences
            assert "vendor_seq" in sequences

    def test_list_sequences_with_group_target(self, mock_config: MagicMock) -> None:
        """Test listing sequences for device group."""
        with patch("network_toolkit.commands.complete.SequenceManager") as mock_sm:
            mock_sm_instance = MagicMock()
            mock_sm.return_value = mock_sm_instance
            mock_sm_instance.list_vendor_sequences.return_value = {}

            sequences = _list_sequences(mock_config, target="office_switches")

            # Should include global and device sequences from group members
            assert "global_health" in sequences
            assert "test_seq" in sequences

    def test_list_sequences_all_devices(self, mock_config: MagicMock) -> None:
        """Test listing sequences across all devices."""
        with patch("network_toolkit.commands.complete.SequenceManager"):
            sequences = _list_sequences(mock_config, target=None)

            # Should include global and all device sequences
            assert "global_health" in sequences
            assert "test_seq" in sequences
            assert "cisco_seq" in sequences

    def test_list_sequences_no_sequences(self) -> None:
        """Test listing sequences when no sequences exist."""
        config = MagicMock(spec=NetworkConfig)
        config.devices = None
        config.global_command_sequences = None

        with patch("network_toolkit.commands.complete.SequenceManager"):
            sequences = _list_sequences(config, target=None)

            assert len(sequences) == 0

    def test_list_sequences_complex_group_logic(self, mock_config: MagicMock) -> None:
        """Test complex group member logic in _list_sequences."""
        # Test when getattr returns None for device_groups
        mock_config.device_groups = None

        with patch("network_toolkit.commands.complete.SequenceManager"):
            sequences = _list_sequences(mock_config, target="nonexistent_group")

            # Should still include global and all device sequences
            assert "global_health" in sequences
            assert "test_seq" in sequences

    def test_list_sequences_vendor_sequences_multiple_platforms(
        self, mock_config: MagicMock
    ) -> None:
        """Test vendor sequences with multiple device platforms."""
        with patch("network_toolkit.commands.complete.SequenceManager") as mock_sm:
            mock_sm_instance = MagicMock()
            mock_sm.return_value = mock_sm_instance

            # Mock list_vendor_sequences for different platforms
            def mock_list_vendor(platform: str) -> dict[str, list[str]]:
                if platform == "mikrotik_routeros":
                    return {"mikrotik_health": ["system clock print"]}
                elif platform == "cisco_iosxe":
                    return {"cisco_health": ["show version"]}
                return {}

            mock_sm_instance.list_vendor_sequences.side_effect = mock_list_vendor

            # Test without specific target - should collect from all platforms
            sequences = _list_sequences(mock_config, target=None)

            assert "global_health" in sequences
            assert "test_seq" in sequences
            assert "cisco_seq" in sequences
