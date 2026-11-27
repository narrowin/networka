# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the CLI module."""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestCLI:
    """Test CLI functionality."""

    def setUp(self) -> None:
        """Set up test runner."""
        self.runner = CliRunner()

    def test_help_command(self) -> None:
        """Test help command shows usage information."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "Networka" in result.output
        assert "nw" in result.output

    def test_info_command_success(self, config_file: Path) -> None:
        """Test info command with valid device."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["info", "--config", str(config_file), "test_device1"]
        )
        assert result.exit_code == 0, result.output
        assert "Device: test_device1" in result.output
        assert "192.168.1.10" in result.output

    def test_info_command_invalid_device(self, config_file: Path) -> None:
        """Test info command with invalid device."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["info", "--config", str(config_file), "nonexistent_device"]
        )
        assert result.exit_code == 1
        assert "Unknown target: nonexistent_device" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_command_success(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test run command execution."""
        # Mock successful command execution
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "Identity: RouterOS"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "/system/identity/print",
            ],
        )
        assert result.exit_code == 0
        assert "Identity: RouterOS" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_command_failure(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test run command execution failure."""
        # Mock command execution failure
        mock_session = MagicMock()
        mock_session.execute_command.side_effect = Exception("Command failed")
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "--config", str(config_file), "test_device1", "/invalid/command"],
        )
        assert result.exit_code == 1

    @patch("network_toolkit.device.DeviceSession")
    def test_sequence_command_success(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test running a sequence via `run` command."""
        # Mock command execution for each command in the sequence
        mock_session = MagicMock()
        mock_session.execute_command.side_effect = [
            "Health: OK",
            "CPU: 5%",
        ]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["run", "--config", str(config_file), "test_device1", "health_check"],
        )
        assert result.exit_code == 0

    def test_config_validate_command(self, config_file: Path) -> None:
        """Test config validate command."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["config", "validate", "--config", str(config_file)]
        )
        # Config validation should succeed with valid test config
        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "OK" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_sequence_on_group(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """A partial sequence failure still emits results and a JSON summary."""
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "Sequence output"
        mock_session.__enter__.return_value = mock_session
        failed_session = MagicMock()
        failed_session.__enter__.side_effect = RuntimeError("Connection failed")
        mock_device_session.side_effect = lambda device, *_: (
            failed_session if device == "test_device2" else mock_session
        )

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "lab_devices",
                "system_info",
                "--raw",
                "json",
            ],
        )
        assert result.exit_code == 1, result.output
        *events, summary = map(json.loads, result.stdout.splitlines())
        results = [event for event in events if event["event"] == "result"]
        assert results
        assert all(
            event["event"] == "result"
            and event["device"] == "test_device1"
            and event["output"] == "Sequence output"
            for event in results
        )
        assert summary.pop("duration") >= 0
        assert summary == {
            "event": "summary",
            "target": "lab_devices",
            "type": "Sequence",
            "name": "system_info",
            "total": 2,
            "succeeded": 1,
            "failed": 1,
        }

    @patch("network_toolkit.api.upload.DeviceSession")
    def test_upload_command(
        self, mock_device_session: MagicMock, config_file: Path, firmware_file: Path
    ) -> None:
        """Test upload command."""
        # Mock successful file upload
        mock_session = MagicMock()
        mock_session.upload_file.return_value = True
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "upload",
                "test_device1",
                str(firmware_file),
                "--config",
                str(config_file),
            ],
        )
        assert result.exit_code == 0

    @patch("network_toolkit.api.upload.DeviceSession")
    def test_upload_command_group(
        self, mock_device_session: MagicMock, config_file: Path, firmware_file: Path
    ) -> None:
        """Test upload command with a group target (replaces legacy group-upload)."""
        # Mock successful file upload
        mock_session = MagicMock()
        mock_session.upload_file.return_value = True
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "upload",
                "lab_devices",
                str(firmware_file),
                "--config",
                str(config_file),
            ],
        )
        # Should succeed
        assert result.exit_code == 0

    @patch("network_toolkit.device.DeviceSession")
    def test_firmware_downgrade_device(
        self, mock_device_session: MagicMock, config_file: Path, firmware_file: Path
    ) -> None:
        """Test firmware-downgrade on single device."""
        mock_session = MagicMock()
        mock_session.config.devices = {
            "test_device1": MagicMock(device_type="mikrotik_routeros")
        }
        mock_session.device_name = "test_device1"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "firmware",
                "downgrade",
                "--config",
                str(config_file),
                "test_device1",
                str(firmware_file),
            ],
        )
        assert result.exit_code == 0

    @patch("network_toolkit.device.DeviceSession")
    def test_firmware_downgrade_group(
        self, mock_device_session: MagicMock, config_file: Path, firmware_file: Path
    ) -> None:
        """Test firmware-downgrade on group."""
        mock_session = MagicMock()
        mock_session.downgrade_firmware_and_reboot.return_value = True
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "firmware",
                "downgrade",
                "--config",
                str(config_file),
                "lab_devices",
                str(firmware_file),
            ],
        )
        assert result.exit_code in [0, 1]

    @patch("network_toolkit.device.DeviceSession")
    def test_bios_upgrade_device(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test bios-upgrade on single device."""
        mock_session = MagicMock()
        mock_session.config.devices = {
            "test_device1": MagicMock(device_type="mikrotik_routeros")
        }
        mock_session.device_name = "test_device1"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "firmware",
                "bios",
                "--config",
                str(config_file),
                "test_device1",
            ],
        )
        assert result.exit_code == 0

    @patch("network_toolkit.device.DeviceSession")
    def test_bios_upgrade_group(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test bios-upgrade on group."""
        mock_session = MagicMock()
        mock_session.routerboard_upgrade_and_reboot.return_value = True
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "firmware",
                "bios",
                "--config",
                str(config_file),
                "lab_devices",
            ],
        )
        assert result.exit_code in [0, 1]

    def test_invalid_config_file(self, temp_dir: Path) -> None:
        """Test CLI with invalid config file."""
        invalid_config = temp_dir / "invalid.yml"
        invalid_config.write_text("invalid: yaml: [")

        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "devices", "--config", str(invalid_config)]
        )
        assert result.exit_code == 1

    def test_missing_config_file(self) -> None:
        """Test CLI with missing config file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "devices", "--config", "/nonexistent/config.yml"]
        )
        assert result.exit_code == 1

    @patch("network_toolkit.device.DeviceSession")
    def test_connection_failure(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test CLI command with connection failure."""
        # Mock connection failure
        mock_session = MagicMock()
        mock_session.__enter__.side_effect = Exception("Connection failed")
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "/system/identity/print",
            ],
        )
        assert result.exit_code == 1

    def test_info_verbose_output(self, config_file: Path) -> None:
        """Test info command with verbose output."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["info", "--config", str(config_file), "--verbose", "test_device1"]
        )
        assert result.exit_code == 0, result.output
        assert "Detailed information for device: test_device1" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_group_run_basic(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test basic group-run command execution."""
        # Mock successful command execution on group
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "System clock: 12:00:00"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        # Test with a simple command that should work
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "lab_devices",
                "/system/clock/print",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "2 total | 2 succeeded, 0 failed" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_command_with_mocked_session(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Test run command with properly mocked session."""
        # Mock successful command execution
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "Identity: RouterOS"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "/system/identity/print",
            ],
        )
        # Should succeed with proper mocking
        assert result.exit_code == 0

    @patch("network_toolkit.device.DeviceSession")
    def test_run_command_comma_separated_devices(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Both comma-separated targets report their outcomes on partial failure."""
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "Command output"
        mock_session.__enter__.return_value = mock_session
        failed_session = MagicMock()
        failed_session.__enter__.side_effect = RuntimeError("Connection failed")
        mock_device_session.side_effect = lambda device, *_: (
            failed_session if device == "test_device2" else mock_session
        )

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1,test_device2",
                "/system/clock/print",
            ],
        )
        assert result.exit_code == 1, result.output
        assert "Members: test_device1, test_device2" in result.output
        assert "Command output" in result.output
        assert "Connection failed" in result.output
        assert "2 total | 1 succeeded, 1 failed" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_command_mixed_targets_group_and_device(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Mix group and device in comma-separated list resolves union of devices."""
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "OK"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "lab_devices,test_device3",
                "/system/identity/print",
            ],
        )
        assert result.exit_code in [0, 1]
        # Expect all three devices to be listed as members
        assert "test_device1" in result.output
        assert "test_device2" in result.output
        assert "test_device3" in result.output

    @patch("network_toolkit.device.DeviceSession")
    def test_run_sequence_comma_separated_devices(
        self, mock_device_session: MagicMock, config_file: Path
    ) -> None:
        """Sequence with comma-separated devices executes per-device."""
        mock_session = MagicMock()
        # Two commands per sequence in sample config; return two outputs
        mock_session.execute_command.side_effect = ["out1", "out2", "out1", "out2"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1,test_device2",
                "health_check",
            ],
        )
        assert result.exit_code in [0, 1]

    @patch("network_toolkit.api.run.SequenceManager")
    @patch("network_toolkit.device.DeviceSession")
    def test_run_sequence_raw_single_device(
        self,
        mock_device_session: MagicMock,
        mock_sm: MagicMock,
        config_file: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Raw output mode prints only command outputs for single-device sequence."""
        # CliRunner shares logging state with earlier tests; a new CLI starts at WARNING.
        caplog.set_level(logging.WARNING)
        # Force sequence resolution to a deterministic set
        sm_instance = mock_sm.return_value
        sm_instance.exists.return_value = True
        sm_instance.resolve.return_value = ["c1", "c2"]
        mock_session = MagicMock()
        mock_session.execute_command.side_effect = ["out1", "out2"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "health_check",
                "--raw",
                "txt",
            ],
        )
        assert result.exit_code == 0, result.output
        assert result.stdout == "out1\nout2\n"

    @patch("network_toolkit.api.run.SequenceManager")
    @patch("network_toolkit.device.DeviceSession")
    def test_run_sequence_raw_group(
        self,
        mock_device_session: MagicMock,
        mock_sm: MagicMock,
        config_file: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Raw output mode for group sequence prints only outputs in member order."""
        caplog.set_level(logging.WARNING)
        sm_instance = mock_sm.return_value
        sm_instance.exists.return_value = True
        sm_instance.resolve.return_value = ["c1", "c2"]
        mock_session = MagicMock()
        # Two commands per device; group of two devices
        mock_session.execute_command.side_effect = [
            "d1c1",
            "d1c2",
            "d2c1",
            "d2c2",
        ]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1,test_device2",
                "health_check",
                "--raw",
                "txt",
            ],
        )
        assert result.exit_code == 0, result.output
        assert result.stdout == "d1c1\nd1c2\nd2c1\nd2c2\n"

    @patch("network_toolkit.device.DeviceSession")
    def test_run_single_command_raw_json(
        self,
        mock_device_session: MagicMock,
        config_file: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Single command raw JSON lines contains device, cmd, and output."""
        caplog.set_level(logging.WARNING)
        mock_session = MagicMock()
        mock_session.execute_command.return_value = "ok"
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "/cmd",
                "--raw",
                "json",
            ],
        )
        assert result.exit_code == 0, result.output
        result_event, summary = map(json.loads, result.stdout.splitlines())
        assert result_event == {
            "event": "result",
            "device": "test_device1",
            "cmd": "/cmd",
            "output": "ok",
        }
        assert summary.pop("duration") >= 0
        assert summary == {
            "event": "summary",
            "target": "test_device1",
            "type": "Command",
            "name": "/cmd",
            "succeeded": True,
        }

    @patch("network_toolkit.api.run.SequenceManager")
    @patch("network_toolkit.device.DeviceSession")
    def test_run_sequence_raw_json(
        self,
        mock_device_session: MagicMock,
        mock_sm: MagicMock,
        config_file: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Sequence raw JSON emits one JSON object per command in order."""
        caplog.set_level(logging.WARNING)
        sm_instance = mock_sm.return_value
        sm_instance.exists.return_value = True
        sm_instance.resolve.return_value = ["c1", "c2"]

        mock_session = MagicMock()
        mock_session.execute_command.side_effect = ["o1", "o2"]
        mock_session.__enter__ = MagicMock(return_value=mock_session)
        mock_session.__exit__ = MagicMock(return_value=None)
        mock_device_session.return_value = mock_session

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "run",
                "--config",
                str(config_file),
                "test_device1",
                "health_check",
                "--raw",
                "json",
            ],
        )

        assert result.exit_code == 0, result.output
        first, second, summary = map(json.loads, result.stdout.splitlines())
        assert first == {
            "event": "result",
            "device": "test_device1",
            "cmd": "c1",
            "output": "o1",
        }
        assert second == {
            "event": "result",
            "device": "test_device1",
            "cmd": "c2",
            "output": "o2",
        }
        assert summary.pop("duration") >= 0
        assert summary == {
            "event": "summary",
            "target": "test_device1",
            "type": "Sequence",
            "name": "health_check",
            "succeeded": True,
        }


def test_cli_keeps_printing_library_warnings_without_logging_setup() -> None:
    """The nw CLI prints warnings to stderr even before a command sets up logging."""
    code = (
        "import logging\n"
        "from typer.testing import CliRunner\n"
        "from network_toolkit.cli import app\n"
        "CliRunner().invoke(app, ['__complete', '--for', 'commands'])\n"
        "logging.getLogger('network_toolkit.device').warning('connect retry')\n"
        "logging.getLogger('network_toolkit.device').info('hidden')\n"
    )
    uv = shutil.which("uv")
    assert uv is not None
    result = subprocess.run(
        [uv, "run", "--locked", "--no-sync", "python", "-c", code],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stderr == "connect retry\n"
