# SPDX-License-Identifier: MIT
"""CLI validation, sequence discovery and minimal configuration contracts."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit import __version__
from network_toolkit.cli import app
from network_toolkit.config import load_config
from network_toolkit.sequence_manager import SequenceManager


class TestBasicCommandCoverage:
    """Test command help without loading a configuration."""

    @pytest.mark.parametrize(
        ("command", "expected"),
        [
            (["list", "devices"], "List all configured network devices."),
            (["run"], "Execute a single command or a sequence"),
            (["info"], "Show comprehensive information"),
            (["upload"], "--remote-name"),
            (["diff"], "--ignore"),
            (["backup", "config"], "backup"),
        ],
    )
    def test_help_commands(self, command: list[str], expected: str) -> None:
        """Leaf help works without loading a configuration."""
        result = CliRunner().invoke(app, [*command, "--help"])

        assert result.exit_code == 0, result.output
        assert expected in result.output

    def test_root_version(self) -> None:
        result = CliRunner().invoke(app, ["--version"])

        assert result.exit_code == 0, result.output
        assert result.output.strip() == f"Networka (nw) version {__version__}"

    def test_root_without_arguments_shows_help(self) -> None:
        result = CliRunner().invoke(app, [])

        assert result.exit_code == 0, result.output
        assert "Networka" in result.output
        assert "--inventory" in result.output


class TestSequenceManagerCoverage:
    """Test resolution and vendor sequence discovery."""

    def test_sequence_manager_resolve_nonexistent(self, config_file: Path) -> None:
        """Test resolving nonexistent sequence."""
        config = load_config(config_file)
        sm = SequenceManager(config)
        result = sm.resolve("nonexistent_sequence")
        assert result is None

    def test_sequence_manager_list_sequences(self, config_file: Path) -> None:
        """Test listing sequences functionality."""
        config = load_config(config_file)
        sm = SequenceManager(config)

        # Test listing all sequences
        all_sequences = sm.list_all_sequences()
        assert "system_info" in all_sequences["mikrotik_routeros"]

        # Test listing vendor sequences
        vendor_sequences = sm.list_vendor_sequences("mikrotik_routeros")
        assert vendor_sequences["system_info"].commands[0] == "/system/identity/print"


class TestConfigurationPaths:
    """Test configuration loading and path handling."""

    def test_config_loading_edge_cases(self, tmp_path: Path) -> None:
        """Test configuration loading with edge cases."""
        # Test minimal valid config
        minimal_config = tmp_path / "minimal.yml"
        minimal_config.write_text(
            """
general:
  timeout: 30
devices:
  test_device:
    host: "192.168.1.1"
    device_type: "mikrotik_routeros"
""",
            encoding="utf-8",
        )

        config = load_config(minimal_config)
        assert config.general.timeout == 30
        assert config.devices is not None
        assert "test_device" in config.devices

    def test_config_with_sequences(self, tmp_path: Path) -> None:
        """Test configuration with sequences."""
        config_with_seqs = tmp_path / "config_seqs.yml"
        config_with_seqs.write_text(
            """
general:
  timeout: 30
devices:
  test_device:
    host: "192.168.1.1"
    device_type: "mikrotik_routeros"
global_command_sequences:
  test_seq:
    description: "Test sequence"
    commands:
      - "/system/identity/print"
      - "/system/clock/print"
""",
            encoding="utf-8",
        )

        config = load_config(config_with_seqs)
        assert config.global_command_sequences is not None
        assert "test_seq" in config.global_command_sequences
        assert config.global_command_sequences["test_seq"].commands == [
            "/system/identity/print",
            "/system/clock/print",
        ]


class TestErrorHandling:
    """Test error handling paths."""

    def test_cli_with_invalid_command(self) -> None:
        """Test CLI with invalid command."""
        runner = CliRunner()
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code == 2, result.output
        assert "No such command" in result.output
        assert "invalid-command" in result.output

    def test_missing_required_arguments(self) -> None:
        """Test commands with missing required arguments."""
        runner = CliRunner()

        # Test run command without arguments
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 2, result.output
        assert "Missing argument" in result.output

        # Test info command without device
        result = runner.invoke(app, ["info"])
        assert result.exit_code == 2, result.output
        assert "Missing argument" in result.output
