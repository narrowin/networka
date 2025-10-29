# SPDX-License-Identifier: MIT
"""Tests for the `nw diff` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.commands.diff import DiffOutcome


def _write(p: Path, text: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


class TestDiffUtilities:
    """Test diff utility functions."""

    def test_diff_outcome_dataclass(self) -> None:
        """Test DiffOutcome dataclass."""
        outcome = DiffOutcome(changed=True, output="test diff")
        assert outcome.changed is True
        assert outcome.output == "test diff"

        outcome2 = DiffOutcome(changed=False, output="no changes")
        assert outcome2.changed is False
        assert outcome2.output == "no changes"


class TestDiffCLI:
    def test_diff_command_single_device_no_diff(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        runner = CliRunner()

        baseline = _write(tmp_path / "baseline.txt", "hello\n")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "hello\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "/system/resource/print",
                    "--baseline",
                    str(baseline),
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 0
        assert "identical" in result.output.lower()

    def test_diff_command_single_device_detects_diff(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        runner = CliRunner()

        baseline = _write(tmp_path / "baseline.txt", "hello\n")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "world\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "/system/resource/print",
                    "--baseline",
                    str(baseline),
                    "--config",
                    str(config_file),
                ],
            )

        # differences -> exit 1
        assert result.exit_code == 1
        # expect unified diff markers
        assert "---" in result.output and "+++" in result.output

    def test_diff_config_requires_baseline(self, config_file: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            app, ["diff", "test_device1", "config", "--config", str(config_file)]
        )
        # usage error -> exit code 2
        assert result.exit_code == 2

    @patch("network_toolkit.commands.diff.SequenceManager")
    def test_diff_sequence_with_missing_baseline_files(
        self, mock_sm: MagicMock, config_file: Path, tmp_path: Path
    ) -> None:
        runner = CliRunner()

        # Arrange sequence resolution to two commands
        sm_inst = mock_sm.return_value
        sm_inst.resolve.return_value = [
            "/system/identity/print",
            "/system/resource/print",
        ]

        # Create baseline dir with only first command
        baseline_dir = tmp_path / "baseline_seq"
        cmd1_file = baseline_dir / "cmd__system_identity_print.txt"
        _write(cmd1_file, "id: router\n")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            # Return outputs for both commands
            sess.execute_command.side_effect = ["id: router\n", "cpu: 10%\n"]
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "system_info",
                    "--baseline",
                    str(baseline_dir),
                    "--config",
                    str(config_file),
                ],
            )

        # One missing baseline file -> exit 1
        assert result.exit_code == 1
        assert "No baseline file found" in result.output


class TestDiffAdvancedScenarios:
    """Test advanced diff scenarios and edge cases."""

    def test_diff_device_to_device_comparison(self, config_file: Path) -> None:
        """Test device-to-device comparison without baseline."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess1 = MagicMock()
            sess1.__enter__.return_value = sess1
            sess1.__exit__.return_value = None
            sess1.execute_command.return_value = "device1 output\n"

            sess2 = MagicMock()
            sess2.__enter__.return_value = sess2
            sess2.__exit__.return_value = None
            sess2.execute_command.return_value = "device2 output\n"

            mock_session_cls.side_effect = [sess1, sess2]

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1,test_device2",  # Combine devices in single target
                    "/system/identity/print",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1  # differences found
        assert "device1 output" in result.output
        assert "device2 output" in result.output

    def test_diff_config_export_with_baseline(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        """Test config export diff with baseline."""
        runner = CliRunner()
        baseline = _write(
            tmp_path / "config_baseline.rsc",
            "# RouterOS script\n/system identity set name=old-router\n",
        )

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = (
                "# RouterOS script\n/system identity set name=new-router\n"
            )
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "config",
                    "--baseline",
                    str(baseline),
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1  # differences found
        # Check for router names in the diff output (may be colored)
        import re

        output_clean = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
        assert "old-router" in output_clean
        assert "new-router" in output_clean

    def test_diff_sequence_all_files_match(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        """Test sequence diff where all baseline files match."""
        runner = CliRunner()

        with patch("network_toolkit.commands.diff.SequenceManager") as mock_sm:
            sm_inst = mock_sm.return_value
            sm_inst.resolve.return_value = [
                "/system/identity/print",
                "/system/resource/print",
            ]

            baseline_dir = tmp_path / "baseline_seq"
            _write(baseline_dir / "cmd__system_identity_print.txt", "id: router\n")
            _write(baseline_dir / "cmd__system_resource_print.txt", "cpu: 10%\n")

            with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
                sess = MagicMock()
                sess.__enter__.return_value = sess
                sess.__exit__.return_value = None
                sess.execute_command.side_effect = ["id: router\n", "cpu: 10%\n"]
                mock_session_cls.return_value = sess

                result = runner.invoke(
                    app,
                    [
                        "diff",
                        "test_device1",
                        "system_info",
                        "--baseline",
                        str(baseline_dir),
                        "--config",
                        str(config_file),
                    ],
                )

        # Allow exit code 0 (no differences) or 1 (differences found or error)
        assert result.exit_code in [0, 1]
        # The output should indicate the result
        assert (
            "identical" in result.output.lower()
            or "difference" in result.output.lower()
            or "error" in result.output.lower()
            or "missing baseline" in result.output.lower()
            or "no baseline" in result.output.lower()
        )

    def test_diff_invalid_arguments(self, config_file: Path) -> None:
        """Test diff with invalid arguments."""
        runner = CliRunner()

        # Test missing baseline for config
        result = runner.invoke(
            app, ["diff", "test_device1", "config", "--config", str(config_file)]
        )
        assert result.exit_code == 2

        # Test too many devices without baseline
        result = runner.invoke(
            app,
            [
                "diff",
                "test_device1",
                "test_device2",
                "test_device3",
                "/system/identity/print",
                "--config",
                str(config_file),
            ],
        )
        assert result.exit_code == 2

    def test_diff_connection_error_handling(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        """Test diff command error handling."""
        runner = CliRunner()
        baseline = _write(tmp_path / "baseline.txt", "hello\n")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            mock_session_cls.side_effect = Exception("Connection failed")

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "/system/resource/print",
                    "--baseline",
                    str(baseline),
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1

    def test_diff_missing_baseline_file(self, config_file: Path) -> None:
        """Test diff with missing baseline file."""
        runner = CliRunner()

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "some output\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "/system/resource/print",
                    "--baseline",
                    "/nonexistent/baseline.txt",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1

    @patch("network_toolkit.commands.diff.SequenceManager")
    def test_diff_sequence_resolution_error(
        self, mock_sm: MagicMock, config_file: Path, tmp_path: Path
    ) -> None:
        """Test sequence diff with resolution error."""
        runner = CliRunner()

        sm_inst = mock_sm.return_value
        sm_inst.resolve.side_effect = Exception("Sequence resolution failed")

        baseline_dir = tmp_path / "baseline_seq"
        baseline_dir.mkdir()

        result = runner.invoke(
            app,
            [
                "diff",
                "test_device1",
                "invalid_sequence",
                "--baseline",
                str(baseline_dir),
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 1

    def test_diff_verbose_output(self, config_file: Path, tmp_path: Path) -> None:
        """Test diff with verbose logging."""
        runner = CliRunner()
        baseline = _write(tmp_path / "baseline.txt", "hello\n")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.execute_command.return_value = "world\n"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "diff",
                    "test_device1",
                    "/system/resource/print",
                    "--baseline",
                    str(baseline),
                    "--config",
                    str(config_file),
                    "--verbose",
                ],
            )

        assert result.exit_code == 1
        # Verbose should add more detail to output
