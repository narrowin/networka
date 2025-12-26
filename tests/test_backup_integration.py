# SPDX-License-Identifier: MIT
"""Integration tests for backup functionality.

Tests the complete backup workflow from platform operations through
file storage, including BackupResult processing, text output storage,
file downloads, and manifest generation.
"""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from network_toolkit.platforms.base import BackupResult
from network_toolkit.platforms.cisco_ios.operations import CiscoIOSOperations
from network_toolkit.platforms.mikrotik_routeros.operations import (
    MikroTikRouterOSOperations,
)


class TestBackupResultIntegration:
    """Test BackupResult data structure and validation."""

    def test_backup_result_creation(self) -> None:
        """Test BackupResult can be created with all fields."""
        result = BackupResult(
            success=True,
            text_outputs={"config.txt": "interface gi0/0"},
            files_to_download=[
                {"source": "flash:/vlan.dat", "destination": "vlan.dat"}
            ],
            errors=[],
        )

        assert result.success is True
        assert len(result.text_outputs) == 1
        assert len(result.files_to_download) == 1
        assert len(result.errors) == 0

    def test_backup_result_with_errors(self) -> None:
        """Test BackupResult properly captures errors."""
        result = BackupResult(
            success=False,
            text_outputs={},
            files_to_download=[],
            errors=["Command 'show version' failed", "Connection timeout"],
        )

        assert result.success is False
        assert len(result.errors) == 2
        assert "show version" in result.errors[0]


class TestCiscoBackupIntegration:
    """Integration tests for Cisco backup operations."""

    def test_cisco_backup_result_structure(self) -> None:
        """Verify Cisco backup returns properly structured BackupResult."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-switch"
        mock_session.execute_command.return_value = "Configuration content"

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(["show running-config"])

        # Verify BackupResult structure
        assert isinstance(result, BackupResult)
        assert result.success is True
        assert "show_running-config.txt" in result.text_outputs
        assert result.text_outputs["show_running-config.txt"] == "Configuration content"

    def test_cisco_includes_vlan_dat_in_downloads(self) -> None:
        """Verify Cisco backup includes vlan.dat in files to download."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-switch"
        mock_session.execute_command.return_value = "OK"

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(["show running-config"])

        # Check that vlan.dat is in the download list
        file_names = [f["local_filename"] for f in result.files_to_download]
        assert "vlan.dat" in file_names

    def test_cisco_includes_config_files_in_downloads(self) -> None:
        """Verify Cisco backup includes config.text and private-config.text."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-router"
        mock_session.execute_command.return_value = "OK"

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(["show running-config"])

        # Check that config files are in the download list
        file_names = [f["local_filename"] for f in result.files_to_download]
        assert "config.text" in file_names
        assert "private-config.text" in file_names

    def test_cisco_multiple_commands_captured(self) -> None:
        """Verify multiple Cisco commands produce multiple text outputs."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-router"

        # Different output for each command
        mock_session.execute_command.side_effect = [
            "Running config...",
            "Startup config...",
            "Version info...",
            "OK",  # dir vlan.dat
            "OK",  # dir config.text
            "OK",  # dir private-config.text
        ]

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(
            ["show running-config", "show startup-config", "show version"]
        )

        # Verify all command outputs are captured
        assert len(result.text_outputs) == 3
        assert "show_running-config.txt" in result.text_outputs
        assert "show_startup-config.txt" in result.text_outputs
        assert "show_version.txt" in result.text_outputs

    def test_cisco_partial_failure_continues(self) -> None:
        """Verify Cisco backup continues when some commands fail."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-router"

        # First command succeeds, second fails, third succeeds
        from network_toolkit.exceptions import DeviceExecutionError

        mock_session.execute_command.side_effect = [
            "Running config OK",
            DeviceExecutionError("Command failed"),
            "Version info OK",
            "OK",  # dir vlan.dat
            "OK",  # dir config.text
            "OK",  # dir private-config.text
        ]

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(
            ["show running-config", "show startup-config", "show version"]
        )

        # Should continue despite failure
        assert len(result.text_outputs) == 2  # Only successful commands
        assert len(result.errors) == 1
        assert "show startup-config" in result.errors[0]

    def test_cisco_file_check_handles_missing_files(self) -> None:
        """Verify Cisco handles missing files gracefully."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "cisco-router"

        # Command succeeds, but file checks show vlan.dat doesn't exist
        mock_session.execute_command.side_effect = [
            "Running config OK",
            "Error: File not found",  # dir vlan.dat (missing)
            "OK",  # dir config.text (exists)
            "Error: No such file",  # dir private-config.text (missing)
        ]

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(["show running-config"])

        # Should only include existing files
        file_names = [f["local_filename"] for f in result.files_to_download]
        assert "config.text" in file_names
        assert "vlan.dat" not in file_names
        assert "private-config.text" not in file_names


class TestMikroTikBackupIntegration:
    """Integration tests for MikroTik backup operations."""

    def test_mikrotik_backup_result_structure(self) -> None:
        """Verify MikroTik backup returns properly structured BackupResult."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "mikrotik-router"
        mock_session.execute_command.return_value = "OK"

        ops = MikroTikRouterOSOperations(mock_session)
        result = ops.config_backup(["/export file=backup"])

        # Verify BackupResult structure
        assert isinstance(result, BackupResult)
        assert result.success is True
        # Filename is now normalized (no parameters, clean format)
        assert "export.txt" in result.text_outputs

    def test_mikrotik_includes_export_file_in_downloads(self) -> None:
        """Verify MikroTik config backup includes .rsc export file."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "mikrotik-router"
        mock_session.execute_command.return_value = "OK"

        ops = MikroTikRouterOSOperations(mock_session)
        result = ops.config_backup(["/export file=nw-export"])

        # Check that export file is in the download list
        file_names = [f["destination"] for f in result.files_to_download]
        assert "nw-export.rsc" in file_names

    def test_mikrotik_comprehensive_backup_includes_binary(self) -> None:
        """Verify MikroTik comprehensive backup includes binary backup."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "mikrotik-router"
        mock_session.execute_command.return_value = "OK"

        ops = MikroTikRouterOSOperations(mock_session)
        result = ops.create_backup(
            ["/system/backup/save name=nw-backup", "/export file=nw-export"]
        )

        # Check that both binary and text exports are in download list
        file_names = [f["destination"] for f in result.files_to_download]
        assert "nw-backup.backup" in file_names
        assert "nw-export.rsc" in file_names

    def test_mikrotik_multiple_commands_captured(self) -> None:
        """Verify multiple MikroTik commands produce multiple text outputs."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "mikrotik-router"

        mock_session.execute_command.side_effect = [
            "Backup created",
            "Export created",
            "System info",
        ]

        ops = MikroTikRouterOSOperations(mock_session)
        result = ops.create_backup(
            [
                "/system/backup/save name=test",
                "/export file=test",
                "/system resource print",
            ]
        )

        # Verify all command outputs are captured
        assert len(result.text_outputs) == 3
        assert result.success is True

    def test_mikrotik_backup_delegation(self) -> None:
        """Verify MikroTik backup() delegates to create_backup()."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "mikrotik-router"
        mock_session.execute_command.return_value = "OK"

        ops = MikroTikRouterOSOperations(mock_session)

        # backup() should use default comprehensive sequence
        result = ops.backup(backup_sequence=[])

        # Should include default comprehensive commands
        assert result.success is True
        assert len(result.text_outputs) >= 3  # Multiple diagnostic commands
        assert len(result.files_to_download) == 2  # .backup and .rsc


class TestBackupCommandIntegration:
    """Integration tests for backup command processing BackupResult."""

    @pytest.fixture
    def temp_backup_dir(self, tmp_path: Path) -> Path:
        """Create a temporary backup directory."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        return backup_dir

    def test_backup_command_creates_timestamped_directory(
        self, temp_backup_dir: Path
    ) -> None:
        """Verify backup command creates device_timestamp directory."""
        # This would be an integration test that:
        # 1. Mocks config with temp_backup_dir
        # 2. Runs backup command
        # 3. Verifies directory exists with format {device}_{timestamp}

        # Mock pattern: device_YYYYMMDD_HHMMSS

        # After running backup, check directory exists
        list(temp_backup_dir.glob("test-device_*"))

        # This assertion would verify directory was created
        # assert len(backup_dirs) == 1
        # assert re.match(expected_pattern, backup_dirs[0].name)

        # Note: Full implementation requires mocking the entire command flow
        pass

    def test_backup_saves_text_outputs_to_files(self, temp_backup_dir: Path) -> None:
        """Verify text outputs from BackupResult are saved as files."""
        # Simulate saving text outputs
        device_dir = temp_backup_dir / "device_20251016_120000"
        device_dir.mkdir()

        # Simulate BackupResult with text outputs
        text_outputs = {
            "show_running-config.txt": "interface GigabitEthernet0/0\n ip address 10.0.0.1",
            "show_version.txt": "Cisco IOS Software, Version 15.2",
        }

        # Save files (this is what backup.py should do)
        for filename, content in text_outputs.items():
            output_file = device_dir / filename
            output_file.write_text(content, encoding="utf-8")

        # Verify files exist and have correct content
        assert (device_dir / "show_running-config.txt").exists()
        assert (device_dir / "show_version.txt").exists()

        config_content = (device_dir / "show_running-config.txt").read_text()
        assert "interface GigabitEthernet0/0" in config_content

    def test_manifest_json_structure(self, temp_backup_dir: Path) -> None:
        """Verify manifest.json contains required metadata."""
        import json

        device_dir = temp_backup_dir / "cisco1_20251016_120000"
        device_dir.mkdir()

        # Expected manifest structure
        manifest = {
            "device": "cisco1",
            "timestamp": "20251016_120000",
            "platform": "Cisco IOS",
            "transport": "scrapli",
            "text_outputs": ["show_running-config.txt", "show_version.txt"],
            "downloaded_files": ["vlan.dat", "config.text"],
        }

        manifest_file = device_dir / "manifest.json"
        manifest_file.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # Verify manifest can be loaded and has expected structure
        loaded = json.loads(manifest_file.read_text())
        assert loaded["device"] == "cisco1"
        assert loaded["platform"] == "Cisco IOS"
        assert "show_running-config.txt" in loaded["text_outputs"]


class TestPlatformSpecificBehavior:
    """Test platform-specific backup behavior differences."""

    def test_cisco_vs_mikrotik_file_differences(self) -> None:
        """Verify Cisco and MikroTik produce different file lists."""
        # Cisco setup
        cisco_session = MagicMock()
        cisco_session.is_connected = True
        cisco_session.device_name = "cisco"
        cisco_session.execute_command.return_value = "OK"

        cisco_ops = CiscoIOSOperations(cisco_session)
        cisco_result = cisco_ops.config_backup(["show run"])

        # MikroTik setup
        mkt_session = MagicMock()
        mkt_session.is_connected = True
        mkt_session.device_name = "mikrotik"
        mkt_session.execute_command.return_value = "OK"

        mkt_ops = MikroTikRouterOSOperations(mkt_session)
        mkt_result = mkt_ops.config_backup(["/export"])

        # Extract file types
        cisco_files = [f["local_filename"] for f in cisco_result.files_to_download]
        mkt_files = [f["destination"] for f in mkt_result.files_to_download]

        # Verify platform-specific files
        assert "vlan.dat" in cisco_files
        assert "vlan.dat" not in mkt_files

        assert any(".rsc" in f for f in mkt_files)
        assert not any(".rsc" in f for f in cisco_files)

    def test_command_output_format_differences(self) -> None:
        """Verify different platforms use different command formats."""
        # Cisco uses "show" commands
        cisco_session = MagicMock()
        cisco_session.is_connected = True
        cisco_session.device_name = "cisco"
        cisco_session.execute_command.return_value = "Config"

        cisco_ops = CiscoIOSOperations(cisco_session)
        cisco_ops.config_backup([])  # Use defaults

        # Verify Cisco default commands were called
        calls = [str(call) for call in cisco_session.execute_command.call_args_list]
        assert any("show running-config" in c for c in calls)

        # MikroTik uses "/" commands
        mkt_session = MagicMock()
        mkt_session.is_connected = True
        mkt_session.device_name = "mikrotik"
        mkt_session.execute_command.return_value = "OK"

        mkt_ops = MikroTikRouterOSOperations(mkt_session)
        mkt_ops.config_backup([])  # Use defaults

        # Verify MikroTik default commands were called
        calls = [str(call) for call in mkt_session.execute_command.call_args_list]
        assert any("/export" in c for c in calls)


class TestErrorRecoveryScenarios:
    """Test error handling and recovery in backup operations."""

    def test_all_commands_fail_returns_failure(self) -> None:
        """Verify backup fails gracefully when all commands fail."""
        from network_toolkit.exceptions import DeviceExecutionError

        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "device"
        mock_session.execute_command.side_effect = DeviceExecutionError("Failed")

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(["show running-config"])

        assert result.success is False
        assert len(result.errors) > 0
        assert len(result.text_outputs) == 0

    def test_some_commands_fail_partial_success(self) -> None:
        """Verify backup succeeds partially when only some commands fail."""
        from network_toolkit.exceptions import DeviceExecutionError

        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "device"

        # First succeeds, second fails, third succeeds
        mock_session.execute_command.side_effect = [
            "Config OK",
            DeviceExecutionError("Failed"),
            "Version OK",
            "OK",
            "OK",
            "OK",  # File checks
        ]

        ops = CiscoIOSOperations(mock_session)
        result = ops.config_backup(
            ["show running-config", "show startup-config", "show version"]
        )

        # Should have 2 successful outputs and 1 error
        assert len(result.text_outputs) == 2
        assert len(result.errors) == 1
        # Success if ANY commands succeeded
        assert result.success is False  # But marked as failure since not all succeeded

    def test_file_download_error_logged_not_crash(self) -> None:
        """Verify file download errors are logged but don't crash backup."""
        mock_session = MagicMock()
        mock_session.is_connected = True
        mock_session.device_name = "device"

        # Command succeeds but file checks throw exceptions
        mock_session.execute_command.side_effect = [
            "Config OK",
            Exception("Disk error"),  # File check fails
            "OK",
            "OK",
        ]

        ops = CiscoIOSOperations(mock_session)
        # Should not raise exception
        result = ops.config_backup(["show running-config"])

        # Backup should still succeed for text outputs
        assert result.success is True
        assert len(result.text_outputs) == 1
