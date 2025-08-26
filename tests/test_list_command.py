# SPDX-License-Identifier: MIT
"""Tests for the `nw list` command and its subcommands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

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
        assert "devices" in result.output
        assert "groups" in result.output
        assert "sequences" in result.output
        assert "supported-types" in result.output

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
        result = runner.invoke(
            app, ["list", "sequences", "--config", str(config_file), "--verbose"]
        )

        assert result.exit_code == 0

    def test_list_supported_types_basic(self) -> None:
        """Test list supported-types subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "supported-types"])

        assert result.exit_code == 0
        assert "Transport Types" in result.output or "Device Types" in result.output

    def test_list_supported_types_verbose(self) -> None:
        """Test list supported-types with verbose output."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "supported-types", "--verbose"])

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

    @patch("network_toolkit.commands.list._list_devices_impl")
    def test_list_devices_implementation_called(
        self, mock_impl: Mock, config_file: Path
    ) -> None:
        """Test that the devices implementation is called correctly."""
        mock_impl.return_value = None

        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "--config", str(config_file)])

        assert result.exit_code == 0
        mock_impl.assert_called_once()

    @patch("network_toolkit.commands.list._list_groups_impl")
    def test_list_groups_implementation_called(
        self, mock_impl: Mock, config_file: Path
    ) -> None:
        """Test that the groups implementation is called correctly."""
        mock_impl.return_value = None

        runner = CliRunner()
        result = runner.invoke(app, ["list", "groups", "--config", str(config_file)])

        assert result.exit_code == 0
        mock_impl.assert_called_once()

    @patch("network_toolkit.commands.list._list_sequences_impl")
    def test_list_sequences_implementation_called(
        self, mock_impl: Mock, config_file: Path
    ) -> None:
        """Test that the sequences implementation is called correctly."""
        mock_impl.return_value = None

        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences", "--config", str(config_file)])

        assert result.exit_code == 0
        mock_impl.assert_called_once()

    @patch("network_toolkit.commands.list._show_supported_types_impl")
    def test_list_supported_types_implementation_called(self, mock_impl: Mock) -> None:
        """Test that the supported types implementation is called correctly."""
        mock_impl.return_value = None

        runner = CliRunner()
        result = runner.invoke(app, ["list", "supported-types"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()

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
        """Test that list supported-types works end-to-end."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "supported-types"])

        assert result.exit_code == 0
        # Should show device types and transport information
        assert "transport" in result.output.lower() or "device" in result.output.lower()


@pytest.fixture
def empty_config_file(tmp_path: Path) -> Path:
    """Create an empty config file for testing."""
    config_content = """
general:
  backup_dir: /tmp/backups
  output_mode: default

devices: {}
device_groups: {}
global_command_sequences: {}
"""
    config_file = tmp_path / "empty_config.yml"
    config_file.write_text(config_content)
    return config_file
