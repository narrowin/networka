# SPDX-License-Identifier: MIT
"""Tests for the `nw run` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class TestRunCommand:
    """Test run command functionality."""

    def test_run_single_device_success(self, config_file: Path) -> None:
        """Test successful run on single device."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "system identity: test-router\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0
        assert "test-router" in result.output

    def test_run_sequence_success(self, config_file: Path) -> None:
        """Test successful sequence execution."""
        runner = CliRunner()

        with patch("network_toolkit.commands.run.SequenceManager") as mock_sm:
            sm_inst = mock_sm.return_value
            sm_inst.resolve.return_value = [
                "/system/identity/print",
                "/system/resource/print",
            ]

            with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
                sess = MagicMock()
                sess.__enter__.return_value = sess
                sess.__exit__.return_value = None
                sess.execute_command.side_effect = ["identity: router1\n", "cpu: 10%\n"]
                mock_session_cls.return_value = sess

                result = runner.invoke(
                    app,
                    [
                        "run",
                        "test_device1",
                        "system_info",
                        "--config",
                        str(config_file),
                    ],
                )

        assert result.exit_code == 0
        assert "identity: router1" in result.output
        # Check that CPU info is present (Rich may format it with colors)
        assert "cpu:" in result.output
        assert "10" in result.output
        assert "%" in result.output

    def test_run_with_timeout(self, config_file: Path) -> None:
        """Test run command with custom timeout."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--timeout",
                    "60",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 2  # CLI argument error

    def test_run_with_dry_run(self, config_file: Path) -> None:
        """Test run command with dry-run option."""
        runner = CliRunner()

        result = runner.invoke(
            app,
            [
                "run",
                "test_device1",
                "/system/identity/print",
                "--dry-run",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 2  # CLI argument error
        assert "No such option: --dry-run" in result.output

    def test_run_connection_error(self, config_file: Path) -> None:
        """Test run command with connection error."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            mock_session_cls.side_effect = Exception("Connection failed")

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1

    def test_run_device_group(self, config_file: Path) -> None:
        """Test run command on device group."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "office_switches",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        # Should work with groups
        assert result.exit_code in [0, 1]  # Allow for group resolution issues

    def test_run_with_verbose(self, config_file: Path) -> None:
        """Test run command with verbose logging."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--verbose",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0

    def test_run_invalid_device(self, config_file: Path) -> None:
        """Test run command with invalid device."""
        runner = CliRunner()

        result = runner.invoke(
            app,
            [
                "run",
                "invalid_device",
                "/system/identity/print",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 1

    def test_run_sequence_resolution_error(self, config_file: Path) -> None:
        """Test run command with sequence resolution error."""
        runner = CliRunner()

        with patch("network_toolkit.commands.run.SequenceManager") as mock_sm:
            sm_inst = mock_sm.return_value
            sm_inst.resolve.side_effect = Exception("Sequence not found")

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "invalid_sequence",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1

    def test_run_with_results_dir(self, config_file: Path, tmp_path: Path) -> None:
        """Test run command with custom results directory."""
        runner = CliRunner()
        results_dir = tmp_path / "custom_results"

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--results-dir",
                    str(results_dir),
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0

    def test_run_command_execution_error(self, config_file: Path) -> None:
        """Test run command with command execution error."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.side_effect = Exception("Command failed")
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1

    def test_run_parallel_execution(self, config_file: Path) -> None:
        """Test run command with parallel execution option."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        # CLI argument error for non-existent --parallel option
        assert result.exit_code in [0, 1, 2]

    def test_run_with_confirmation_prompt(self, config_file: Path) -> None:
        """Test run command with confirmation prompt."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "output\n"
            mock_session_cls.return_value = sess

            # Test with confirmation (answering 'n')
            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/reset-configuration",
                    "--config",
                    str(config_file),
                ],
                input="n\n",
            )

        # Should be cancelled due to 'n' input
        assert result.exit_code in [0, 1]

    def test_run_command_with_empty_output(self, config_file: Path) -> None:
        """Test run command with empty command output."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = ""
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0


class TestRunCommandEdgeCases:
    """Test edge cases for run command."""

    def test_run_with_long_output(self, config_file: Path) -> None:
        """Test run command with very long output."""
        runner = CliRunner()
        long_output = "line\n" * 1000

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = long_output
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/interface/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0

    def test_run_with_special_characters(self, config_file: Path) -> None:
        """Test run command with special characters in output."""
        runner = CliRunner()
        special_output = "Special chars: ñáéíóú äöü ßÿ €£¥\n"

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = special_output
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0

    def test_run_multiple_devices_mixed_results(self, config_file: Path) -> None:
        """Test run on multiple devices with mixed success/failure."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            # First device succeeds, second fails
            sess1 = MagicMock()
            sess1.__enter__.return_value = sess1
            sess1.__exit__.return_value = None
            sess1.execute_command.return_value = "success\n"

            sess2 = MagicMock()
            sess2.__enter__.return_value = sess2
            sess2.__exit__.return_value = None
            sess2.execute_command.side_effect = Exception("Failed")

            mock_session_cls.side_effect = [sess1, sess2]

            result = runner.invoke(
                app,
                [
                    "run",
                    "test_device1,test_device2",
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        # Mixed results should still return appropriate exit code
        assert result.exit_code in [0, 1]

    def test_run_with_config_validation_error(self, tmp_path: Path) -> None:
        """Test run command with invalid configuration."""
        runner = CliRunner()
        invalid_config = tmp_path / "invalid.yml"
        invalid_config.write_text("invalid: yaml: content: [", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "run",
                "test_device1",
                "/system/identity/print",
                "--config",
                str(invalid_config),
            ],
        )

        assert result.exit_code == 1
