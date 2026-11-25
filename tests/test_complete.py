"""Tests for completion helper functions."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.commands.complete import (
    _list_commands,
    _list_devices,
    _list_groups,
    _list_sequence_groups,
    _list_sequences,
    _list_tags,
)
from network_toolkit.config import (
    CommandSequenceGroup,
    DeviceConfig,
    DeviceGroup,
    NetworkConfig,
    VendorSequence,
)


@pytest.fixture
def completion_config() -> NetworkConfig:
    """Give completion a configured device in each platform and a restricted global."""
    return NetworkConfig(
        devices={
            "sw-acc1": DeviceConfig(
                host="192.0.2.1",
                tags=["switch", "office"],
                device_type="mikrotik_routeros",
                command_sequences={"test_seq": ["cmd1", "cmd2"]},
            ),
            "rt-edge1": DeviceConfig(
                host="192.0.2.2",
                tags=["router", "edge"],
                device_type="cisco_iosxe",
                command_sequences={"cisco_seq": ["show version"]},
            ),
        },
        device_groups={
            "office_switches": DeviceGroup(description="Office", match_tags=["office"]),
            "edge_routers": DeviceGroup(description="Edge", members=["rt-edge1"]),
        },
        command_sequence_groups={
            "monitoring": CommandSequenceGroup(
                description="Monitoring", match_tags=["health"]
            ),
            "maintenance": CommandSequenceGroup(
                description="Maintenance", match_tags=["update"]
            ),
        },
        global_command_sequences={
            "global_health": VendorSequence(
                description="Health", commands=["global health cmd"]
            ),
            "global_backup": VendorSequence(
                description="Backup",
                commands=["global backup cmd"],
                device_types=["cisco_iosxe"],
            ),
        },
    )


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

    def test_cli_completes_commands(self) -> None:
        """The shell completion entry point emits one candidate per line."""
        result = CliRunner().invoke(app, ["__complete", "--for", "commands"])

        assert result.exit_code == 0, result.output
        assert result.stdout.splitlines() == _list_commands()


class TestListDevices:
    """Test _list_devices function."""

    def test_list_devices_with_devices(self, completion_config: NetworkConfig) -> None:
        """Test listing devices when devices exist."""
        devices = _list_devices(completion_config)

        assert devices == ["rt-edge1", "sw-acc1"]

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

    def test_list_groups_with_groups(self, completion_config: NetworkConfig) -> None:
        """Test listing groups when groups exist."""
        groups = _list_groups(completion_config)

        assert groups == ["edge_routers", "office_switches"]

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

    def test_list_sequence_groups_with_groups(
        self, completion_config: NetworkConfig
    ) -> None:
        """Test listing sequence groups when they exist."""
        seq_groups = _list_sequence_groups(completion_config)

        assert seq_groups == ["monitoring", "maintenance"]

    def test_list_sequence_groups_with_empty_config(self) -> None:
        """Test listing sequence groups when none exist."""
        config = MagicMock(spec=NetworkConfig)
        config.command_sequence_groups = None

        seq_groups = _list_sequence_groups(config)
        assert seq_groups == []


class TestListTags:
    """Test _list_tags function."""

    def test_list_tags_with_devices(self, completion_config: NetworkConfig) -> None:
        """Test listing tags when devices have tags."""
        tags = _list_tags(completion_config)

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
    """Complete only sequences eligible for the selected scope."""

    def test_list_sequences_global_only(self, completion_config: NetworkConfig) -> None:
        completion_config.devices = None
        sequences = _list_sequences(completion_config, target=None)
        assert {"global_health", "global_backup"}.issubset(sequences)

    def test_list_sequences_with_device_target(
        self, completion_config: NetworkConfig
    ) -> None:
        sequences = _list_sequences(completion_config, target="sw-acc1")
        assert {"global_health", "test_seq", "system_info"}.issubset(sequences)
        assert "global_backup" not in sequences
        assert "cisco_seq" not in sequences

    def test_list_sequences_with_group_target(
        self, completion_config: NetworkConfig
    ) -> None:
        sequences = _list_sequences(completion_config, target="office_switches")
        assert {"global_health", "test_seq"}.issubset(sequences)
        assert "global_backup" not in sequences
        assert "cisco_seq" not in sequences

    def test_list_sequences_all_devices(self, completion_config: NetworkConfig) -> None:
        sequences = _list_sequences(completion_config, target=None)
        assert {"global_health", "test_seq", "cisco_seq"}.issubset(sequences)

    def test_list_sequences_no_sequences(self) -> None:
        with patch("network_toolkit.commands.complete.SequenceManager") as manager:
            manager.return_value.catalog_records.return_value = []
            assert _list_sequences(NetworkConfig(), target=None) == []

    def test_list_sequences_unknown_group(
        self, completion_config: NetworkConfig
    ) -> None:
        assert _list_sequences(completion_config, target="nonexistent_group") == []

    def test_list_sequences_vendor_sequences_multiple_platforms(
        self, completion_config: NetworkConfig
    ) -> None:
        sequences = _list_sequences(
            completion_config, target="office_switches,edge_routers"
        )
        assert {
            "global_health",
            "global_backup",
            "test_seq",
            "cisco_seq",
            "system_info",
        }.issubset(sequences)
