"""Tests for MikroTik RouterOS platform operations."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit import intent
from network_toolkit.api.run import DeviceCommandResult
from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.base import BackupResult
from network_toolkit.platforms.mikrotik_routeros.intent import (
    PORT_MONITOR,
    PORT_STATS,
    RESOURCE,
    UPTIME,
    bond_monitor,
    bridge_monitor,
    bridge_print,
    check_property,
    check_version,
    collect,
    collect_bridge_port,
    ethernet_monitor,
    host_print,
    menu_print,
)
from network_toolkit.platforms.mikrotik_routeros.operations import (
    MikroTikRouterOSOperations,
)


class TestMikroTikRouterOSOperations:
    """Test MikroTik RouterOS platform operations."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_router"
        self.mock_session._connected = True
        self.mock_session._transport = MagicMock()

        self.platform_ops = MikroTikRouterOSOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "MikroTik RouterOS"
        assert self.platform_ops.get_device_types() == ["mikrotik_routeros"]
        assert self.platform_ops.get_supported_file_extensions() == [".npk"]

    def test_firmware_upgrade_success(self) -> None:
        """Test successful firmware upgrade."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload
        self.mock_session.upload_file.return_value = True
        self.mock_session.execute_command.return_value = "package list output"

        # Mock successful reboot
        self.mock_session._transport.send_interactive.return_value = "reboot response"

        # Test firmware upgrade
        result = self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert result is True
        self.mock_session.upload_file.assert_called_once()
        self.mock_session._transport.send_interactive.assert_called_once()
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_firmware_upgrade_invalid_extension(self) -> None:
        """Test firmware upgrade with invalid file extension."""
        # Mock file with wrong extension
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".bin"  # Wrong extension for RouterOS

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Invalid firmware file for RouterOS" in str(exc_info.value)
        assert ".npk" in str(exc_info.value)

    def test_firmware_upgrade_file_not_found(self) -> None:
        """Test firmware upgrade with missing file."""
        # Mock non-existent file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = False

        # Should raise FileNotFoundError
        with pytest.raises(FileNotFoundError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Firmware file not found" in str(exc_info.value)

    def test_firmware_upgrade_not_connected(self) -> None:
        """Test firmware upgrade when device not connected."""
        self.mock_session._connected = False
        mock_firmware_path = MagicMock(spec=Path)

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Device not connected" in str(exc_info.value)

    def test_firmware_upgrade_upload_failed(self) -> None:
        """Test firmware upgrade when upload fails."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True

        # Mock failed upload
        self.mock_session.upload_file.return_value = False

        # Should raise DeviceExecutionError
        with pytest.raises(DeviceExecutionError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "Firmware file upload failed" in str(exc_info.value)

    def test_firmware_downgrade_success(self) -> None:
        """Test successful firmware downgrade."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload
        self.mock_session.upload_file.return_value = True
        self.mock_session.execute_command.return_value = "package list output"

        # Mock successful downgrade
        self.mock_session._transport.send_interactive.return_value = (
            "downgrade response"
        )

        # Test firmware downgrade
        result = self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert result is True
        self.mock_session.upload_file.assert_called_once()
        self.mock_session._transport.send_interactive.assert_called_once()
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_bios_upgrade_success(self) -> None:
        """Test successful BIOS/RouterBOARD upgrade."""
        # Mock successful routerboard status check
        self.mock_session.execute_command.return_value = "routerboard status"

        # Mock successful upgrade and reboot
        self.mock_session._transport.send_interactive.side_effect = [
            "upgrade response",  # RouterBOARD upgrade
            "reboot response",  # Reboot
        ]

        # Test BIOS upgrade
        result = self.platform_ops.bios_upgrade()

        assert result is True
        assert self.mock_session._transport.send_interactive.call_count == 2
        assert self.mock_session._connected is False  # Should disconnect after reboot

    def test_bios_upgrade_not_connected(self) -> None:
        """Test BIOS upgrade when device not connected."""
        self.mock_session._connected = False

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "Device not connected" in str(exc_info.value)

    def test_create_backup_success(self) -> None:
        """Test successful backup creation."""
        backup_sequence = ["/system backup save name=test", "/export file=test"]

        # Mock successful command execution
        self.mock_session.execute_command.side_effect = [
            "backup saved",
            "export created",
        ]

        # Test backup creation
        result = self.platform_ops.create_backup(backup_sequence)

        assert isinstance(result, BackupResult)
        assert result.success is True
        assert len(result.text_outputs) == 2
        assert self.mock_session.execute_command.call_count == 2
        self.mock_session.execute_command.assert_any_call(
            "/system backup save name=test"
        )
        self.mock_session.execute_command.assert_any_call("/export file=test")

    def test_create_backup_not_connected(self) -> None:
        """Test backup creation when device not connected."""
        self.mock_session.is_connected = False
        backup_sequence = ["/system backup save"]

        # Should raise DeviceConnectionError
        with pytest.raises(DeviceConnectionError) as exc_info:
            self.platform_ops.create_backup(backup_sequence)

        assert "Device not connected" in str(exc_info.value)

    def test_create_backup_command_failed(self) -> None:
        """Test backup creation when command fails."""
        backup_sequence = ["/system backup save"]

        # Mock command failure
        self.mock_session.execute_command.side_effect = DeviceExecutionError(
            "Command failed"
        )

        # Should return failed BackupResult (not raise exception)
        result = self.platform_ops.create_backup(backup_sequence)

        assert isinstance(result, BackupResult)
        assert result.success is False
        assert len(result.errors) > 0
        assert "Command failed" in str(result.errors)

    def test_create_backup_with_default_sequence(self) -> None:
        """Test backup creation with empty sequence (uses default)."""
        # Mock successful command execution
        self.mock_session.execute_command.side_effect = [
            "backup saved",
            "export created",
        ]

        # Test backup creation with empty sequence
        result = self.platform_ops.create_backup([])

        assert isinstance(result, BackupResult)
        assert result.success is True
        # Should use default sequence
        assert self.mock_session.execute_command.call_count == 2

    @patch("time.sleep")  # Mock sleep to speed up tests
    def test_firmware_upgrade_with_delays(self, mock_sleep: MagicMock) -> None:
        """Test firmware upgrade respects delay parameters."""
        # Mock file
        mock_firmware_path = MagicMock(spec=Path)
        mock_firmware_path.suffix = ".npk"
        mock_firmware_path.exists.return_value = True
        mock_firmware_path.is_file.return_value = True
        mock_firmware_path.name = "firmware.npk"

        # Mock successful upload and reboot
        self.mock_session.upload_file.return_value = True
        self.mock_session._transport.send_interactive.return_value = "reboot response"

        # Test firmware upgrade with custom delay
        result = self.platform_ops.firmware_upgrade(
            mock_firmware_path,
            pre_reboot_delay=5.0,
        )

        assert result is True
        # Should have called sleep with the specified delay
        mock_sleep.assert_called_with(5.0)

    def test_operation_support_checking(self) -> None:
        """Test that all operations are reported as supported."""
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )


PORTS = '[{".id":"*1","bridge":"bridge","interface":"ether1"}]'


def test_bridge_port_forwarding_collects_and_replays() -> None:
    """Collected replies replay to a verdict without the device."""
    replies = {
        PORT_STATS: PORTS,
        PORT_MONITOR.format(port_id="*1"): '{".id":"*1","forwarding":false}',
    }
    client = MagicMock()
    client.run.side_effect = lambda device, command, **_: MagicMock(
        command_results=[DeviceCommandResult(device, command, replies[command])]
    )

    evidence = collect_bridge_port(client, "r1", "bridge", "ether1")

    def forwarding(port: str, *, expected: bool = True) -> intent.IntentResult:
        return intent.check_bridge_port(
            evidence, "mikrotik_routeros", "bridge", port, {"forwarding": expected}
        )

    assert forwarding("ether1").verdict == "fail"
    assert (
        forwarding("ether1", expected=False).observed,
        forwarding("ether1", expected=False).verdict,
    ) == (
        {"forwarding": False},
        "pass",
    )
    missing = forwarding("ether2")
    assert missing.verdict == "error"
    assert missing.reason == "expected one bridge port bridge/ether2, found 0"
    failed = {"stats": {"command": PORT_STATS, "output": None, "error": "timeout"}}
    assert (
        intent.check_bridge_port(
            failed, "mikrotik_routeros", "bridge", "ether1", {"forwarding": True}
        ).reason
        == "timeout"
    )


# RouterOS JSON replies of a Small lab MLAG peer, one per command.
BRIDGE = {
    "bridge-id": "0x1000.52:54:00:E1:0B:01",
    "root-bridge": True,
    "root-bridge-id": "0x1000.52:54:00:E1:0B:01",
    "root-port": "none",
    "topology-changes": 2,
    "mlag-state": "connected",
    "mlag-active-role": "primary",
}
BOND = [
    {
        "port": "ether4",
        "flags": "ATGSCD--",
        "partner-sys-id": "02:00:00:11:00:12",
        "partner-sys-priority": 65535,
        "partner-flags": "ATG---F-",
        "partner": True,
    },
    # A member whose partner is unknown, as RouterOS 7.26beta7 returned it.
    {"active": True, "flags": "ATG---FE", "key": 15, "port": "ether3"},
]
HOST = [
    {
        "mac-address": "02:00:00:11:00:12",
        "bridge": "bridge",
        "interface": "client2",
        "on-interface": "client2",
    }
]
REPLIES = {
    bridge_monitor("bridge"): BRIDGE,
    PORT_STATS: json.loads(PORTS),
    bond_monitor("client2"): BOND,
    host_print("02:00:00:11:00:12"): HOST,
    ethernet_monitor("ether2"): {"name": "ether2", "status": "no-link"},
    UPTIME: 75000000000,
    bridge_print("bridge"): [{"name": "bridge", "protocol-mode": "rstp"}],
}


def routeros_evidence(*commands: str) -> dict:
    return {
        c: {"command": c, "output": json.dumps(REPLIES[c]), "error": None}
        for c in commands
    }


ROS = "mikrotik_routeros"
STATE = routeros_evidence(*REPLIES)


def test_collect_splits_one_read_into_replies() -> None:
    commands = (UPTIME, bridge_monitor("bridge"))
    client = MagicMock()
    output = "\n".join(json.dumps(REPLIES[c]) for c in commands)
    client.run.return_value = MagicMock(
        command_results=[DeviceCommandResult("r1", "x", output)]
    )
    assert collect(client, "r1", *commands) == routeros_evidence(*commands)
    client.run.return_value = MagicMock(
        command_results=[DeviceCommandResult("r1", "x", "1")]
    )
    short = collect(client, "r1", *commands)
    assert short[UPTIME]["error"] == "the joined read returned 1 lines for 2 commands"


def test_bridge_port() -> None:
    replies = {
        PORT_STATS: PORTS,
        PORT_MONITOR.format(port_id="*1"): (
            '{".id":"*1","forwarding":true,"role":"root-port","edge-port":false}'
        ),
    }
    evidence = {
        "stats": {"command": PORT_STATS, "output": replies[PORT_STATS], "error": None},
        "monitor": {
            "command": PORT_MONITOR.format(port_id="*1"),
            "output": replies[PORT_MONITOR.format(port_id="*1")],
            "error": None,
        },
    }
    result = intent.check_bridge_port(
        evidence, ROS, "bridge", "ether1", {"role": "root", "edge": False}
    )
    assert (result.observed, result.verdict) == (
        {"role": "root", "edge": False},
        "pass",
    )


def test_bridge_ports() -> None:
    evidence = {
        "stats": STATE[PORT_STATS],
        **routeros_evidence(bridge_monitor("bridge")),
    }
    result = intent.check_bridge_ports(evidence, ROS, "bridge", {"ether2"})
    assert (result.observed, result.verdict) == (["ether1"], "fail")


def test_stp_bridge() -> None:
    expected = {
        "root_bridge_id": "0x1000.52:54:00:e1:0b:01",
        "root_bridge": True,
        "root_port": None,
        "topology_changes": 2,
    }
    assert intent.check_stp_bridge(STATE, ROS, "bridge", expected).verdict == "pass"


def test_mlag() -> None:
    result = intent.check_mlag(
        STATE, ROS, "bridge", {"connected": True, "role": "secondary"}
    )
    assert (result.observed, result.verdict) == (
        {"connected": True, "role": "primary"},
        "fail",
    )


def test_lacp_member_and_partner_system() -> None:
    scd = {"synchronization": True, "collecting": True, "distributing": True}
    result = intent.check_lacp_member(STATE, ROS, "client2", "ether4", scd)
    assert result.verdict == "fail"
    assert result.observed["partner"] == {
        "synchronization": False,
        "collecting": False,
        "distributing": False,
    }
    system = {"priority": 65535, "mac": "02:00:00:11:00:12"}
    partner = intent.check_lacp_partner_system(STATE, ROS, "client2", "ether4", system)
    assert partner.verdict == "pass"
    alone = intent.check_lacp_member(STATE, ROS, "client2", "ether3", scd)
    assert (alone.verdict, alone.reason) == ("error", "no LACP partner")


def test_host_entry() -> None:
    mac = "02:00:00:11:00:12"
    assert intent.check_host_entry(STATE, ROS, "bridge", mac, "client2").verdict == (
        "pass"
    )
    missing = intent.check_host_entry(STATE, ROS, "bridge", "02:00:00:11:00:11", None)
    assert missing.verdict == "error"


def test_interface_up() -> None:
    result = intent.check_interface_up(STATE, ROS, "ether2", expected=False)
    assert (result.observed, result.verdict) == (False, "pass")


BRIDGE_PRINT = '[{"name":"bridge","protocol-mode":"none","mlag-lacp-fallback":true}]'
PORT_PRINT = '[{"interface":"client2","bridge":"bridge","pvid":110,"bpdu-guard":false}]'
CONFIG = {
    bridge_print("bridge"): {
        "command": bridge_print("bridge"),
        "output": BRIDGE_PRINT,
        "error": None,
    },
    menu_print("/interface/bridge/port"): {
        "command": menu_print("/interface/bridge/port"),
        "output": PORT_PRINT,
        "error": None,
    },
}


def test_stp_mode() -> None:
    result = intent.check_stp_mode(CONFIG, ROS, "bridge", "rstp")
    assert (result.observed, result.verdict) == ("none", "fail")


def test_property() -> None:
    port = "/interface/bridge/port"
    where = {"interface": "client2"}
    assert check_property(CONFIG, port, where, "pvid", 110).verdict == "pass"
    assert check_property(CONFIG, port, where, "bpdu-guard", False).verdict == "pass"
    assert check_property(CONFIG, port, {"interface": "x"}, "pvid", 1).reason == (
        "expected one entry with interface=x, found 0"
    )


def test_version() -> None:
    output = '{"uptime":"4m19s","version":"7.26beta7 (testing)"}'
    evidence = {RESOURCE: {"command": RESOURCE, "output": output, "error": None}}
    assert check_version(evidence, "7.26beta7").verdict == "pass"
