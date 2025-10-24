# SPDX-License-Identifier: MIT
"""Tests for the `nw list` command and its subcommands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestListCommand:
    """Test the nw list command group and its subcommands."""

    def test_list_command_help(self) -> None:
        """Test that list command shows its subcommands."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "--help"])

        assert result.exit_code == 0
        # Should list available subcommands
        assert "devices" in result.output
        assert "groups" in result.output
        assert "sequences" in result.output
        # supported-types should NOT be here anymore - it's moved to config
        assert "supported-types" not in result.output

    def test_list_devices_basic(self, config_file: Path) -> None:
        """Test list devices subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "--config", str(config_file)])

        assert result.exit_code == 0
        assert (
            "test_device1" in result.output or "No devices configured" in result.output
        )

    def test_list_devices_verbose(self, config_file: Path) -> None:
        """Test list devices with verbose output."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "devices", "--config", str(config_file), "--verbose"]
        )

        assert result.exit_code == 0

    def test_list_devices_output_modes(self, config_file: Path) -> None:
        """Test list devices with different output modes."""
        runner = CliRunner()

        # Test raw mode
        result = runner.invoke(
            app,
            ["list", "devices", "--config", str(config_file), "--output-mode", "raw"],
        )
        assert result.exit_code == 0

        # Test no-color mode
        result = runner.invoke(
            app,
            [
                "list",
                "devices",
                "--config",
                str(config_file),
                "--output-mode",
                "no-color",
            ],
        )
        assert result.exit_code == 0

    def test_list_groups_basic(self, config_file: Path) -> None:
        """Test list groups subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "groups", "--config", str(config_file)])

        assert result.exit_code == 0
        assert (
            "all_switches" in result.output
            or "No device groups configured" in result.output
        )

    def test_list_groups_verbose(self, config_file: Path) -> None:
        """Test list groups with verbose output."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "groups", "--config", str(config_file), "--verbose"]
        )

        assert result.exit_code == 0

    def test_list_sequences_basic(self, config_file: Path) -> None:
        """Test list sequences subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences", "--config", str(config_file)])

        assert result.exit_code == 0

    def test_list_sequences_with_vendor_filter(self, config_file: Path) -> None:
        """Test list sequences with vendor filter."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["list", "sequences", "--config", str(config_file), "--vendor", "mikrotik"],
        )

        assert result.exit_code == 0

    def test_list_sequences_with_category_filter(self, config_file: Path) -> None:
        """Test list sequences with category filter."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "list",
                "sequences",
                "--config",
                str(config_file),
                "--category",
                "maintenance",
            ],
        )

        assert result.exit_code == 0

    def test_list_sequences_verbose(self, config_file: Path) -> None:
        """Test list sequences with verbose output."""
        runner = CliRunner()

        with patch("network_toolkit.commands.list.SequenceManager") as mock_sm_class:
            # Mock the SequenceManager class and its instance methods
            mock_sm_instance = mock_sm_class.return_value
            mock_sm_instance.list_all_sequences.return_value = {}
            mock_sm_instance.list_vendor_sequences.return_value = {}

            # Also mock the CommandContext to avoid any issues
            with patch(
                "network_toolkit.commands.list.CommandContext"
            ) as mock_ctx_class:
                mock_ctx = mock_ctx_class.return_value
                mock_ctx.print_warning = MagicMock()
                mock_ctx.output_manager.print_blank_line = MagicMock()

                result = runner.invoke(
                    app,
                    ["list", "sequences", "--config", str(config_file), "--verbose"],
                )

        if result.exit_code != 0:
            print(f"Exit code: {result.exit_code}")
            print(f"Output: {result.output}")
            print(f"Exception: {result.exception}")
            if result.exception:
                import traceback

                print(
                    f"Exception traceback: {''.join(traceback.format_exception(type(result.exception), result.exception, result.exception.__traceback__))}"
                )

        assert result.exit_code == 0

    def test_list_supported_types_basic(self) -> None:
        """Test config supported-types subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "supported-types"])

        assert result.exit_code == 0
        assert "Transport Types" in result.output or "Device Types" in result.output

    def test_list_supported_types_verbose(self) -> None:
        """Test config supported-types with verbose output."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "supported-types", "--verbose"])

        assert result.exit_code == 0
        assert "Usage Examples" in result.output or "Transport Types" in result.output

    def test_list_devices_with_invalid_config(self) -> None:
        """Test list devices with invalid config file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "devices", "--config", "/nonexistent/config.yml"]
        )

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_list_groups_with_invalid_config(self) -> None:
        """Test list groups with invalid config file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "groups", "--config", "/nonexistent/config.yml"]
        )

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_list_sequences_with_invalid_config(self) -> None:
        """Test list sequences with invalid config file."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "sequences", "--config", "/nonexistent/config.yml"]
        )

        assert result.exit_code == 1
        assert "Unexpected error" in result.output

    def test_list_devices_no_devices_configured(self, empty_config_file: Path) -> None:
        """Test list devices when no devices are configured."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "devices", "--config", str(empty_config_file)]
        )

        assert result.exit_code == 0
        assert "No devices configured" in result.output

    def test_list_groups_no_groups_configured(self, empty_config_file: Path) -> None:
        """Test list groups when no groups are configured."""
        runner = CliRunner()
        result = runner.invoke(
            app, ["list", "groups", "--config", str(empty_config_file)]
        )

        assert result.exit_code == 0
        assert "No device groups configured" in result.output

    def test_list_command_backwards_compatibility(self, config_file: Path) -> None:
        """Test that old command patterns fail gracefully."""
        runner = CliRunner()

        # These should fail because the old commands don't exist anymore
        result = runner.invoke(app, ["list-devices", "--config", str(config_file)])
        assert result.exit_code != 0

        result = runner.invoke(app, ["list-groups", "--config", str(config_file)])
        assert result.exit_code != 0

        # This should work because it's the new correct syntax
        result = runner.invoke(app, ["list", "sequences", "--config", str(config_file)])
        assert result.exit_code == 0


class TestListCommandIntegration:
    """Integration tests for the list command with actual implementations."""

    def test_list_devices_integration(self, config_file: Path) -> None:
        """Test that list devices works end-to-end."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "--config", str(config_file)])

        assert result.exit_code == 0
        # Should show either device info or "no devices" message
        assert (
            "device" in result.output.lower()
            or "no devices configured" in result.output.lower()
        )

    def test_list_groups_integration(self, config_file: Path) -> None:
        """Test that list groups works end-to-end."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "groups", "--config", str(config_file)])

        assert result.exit_code == 0
        # Should show either group info or "no groups" message
        assert (
            "group" in result.output.lower()
            or "no device groups configured" in result.output.lower()
        )

    def test_list_sequences_integration(self, config_file: Path) -> None:
        """Test that list sequences works end-to-end."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences", "--config", str(config_file)])

        assert result.exit_code == 0
        # Should either show sequences or handle empty sequences gracefully

    def test_list_supported_types_integration(self) -> None:
        """Test that config supported-types works end-to-end."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "supported-types"])

        assert result.exit_code == 0
        # Should show device types and transport information
        assert "transport" in result.output.lower() or "device" in result.output.lower()


@pytest.fixture
def empty_config_file(tmp_path: Path) -> Path:
    """Create a minimal modular config directory with empty sections.

    Returns the path to config.yml inside the temp config/ directory.
    """
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "devices").mkdir(exist_ok=True)
    (cfg_dir / "groups").mkdir(exist_ok=True)
    (cfg_dir / "sequences").mkdir(exist_ok=True)

    config_content = {
        "general": {
            "backup_dir": "/tmp/backups",
            "output_mode": "default",
        },
        "devices": {},
        "device_groups": {},
        "global_command_sequences": {},
    }
    config_file = cfg_dir / "config.yml"
    import yaml as _yaml

    with config_file.open("w", encoding="utf-8") as f:
        _yaml.dump(config_content, f)
    return config_file
