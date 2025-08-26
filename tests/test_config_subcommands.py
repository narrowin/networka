"""Tests for the unified `nw config` command and its subcommands."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class TestConfigCommand:
    """Test the nw config command group and its subcommands."""

    def test_config_command_help(self) -> None:
        """Test that config command shows its subcommands."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "init" in result.output
        assert "validate" in result.output

    @patch("network_toolkit.commands.config._config_init_impl")
    def test_config_init_basic(self, mock_impl: Mock) -> None:
        """Test config init subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "init", "--yes", "--dry-run"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        # Verify the parameters passed to the implementation
        call_args = mock_impl.call_args
        assert call_args.kwargs["yes"] is True
        assert call_args.kwargs["dry_run"] is True

    @patch("network_toolkit.commands.config._config_init_impl")
    def test_config_init_with_options(self, mock_impl: Mock) -> None:
        """Test config init with various options."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "config",
                "init",
                "/tmp/test",
                "--force",
                "--verbose",
                "--install-completions",
                "--shell",
                "bash",
            ],
        )

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["target_dir"] == Path("/tmp/test")
        assert call_args.kwargs["force"] is True
        assert call_args.kwargs["verbose"] is True
        assert call_args.kwargs["install_completions"] is True
        assert call_args.kwargs["shell"] == "bash"

    @patch("network_toolkit.commands.config._config_validate_impl")
    def test_config_validate_basic(self, mock_impl: Mock) -> None:
        """Test config validate subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "validate"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()

    @patch("network_toolkit.commands.config._config_validate_impl")
    def test_config_validate_with_options(
        self, mock_impl: Mock, config_file: Path
    ) -> None:
        """Test config validate with various options."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "config",
                "validate",
                "--config",
                str(config_file),
                "--verbose",
                "--output-mode",
                "raw",
            ],
        )

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["config_file"] == config_file
        assert call_args.kwargs["verbose"] is True
        assert call_args.kwargs["output_mode"].value == "raw"

    def test_config_no_subcommand(self) -> None:
        """Test that config without subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(app, ["config"])

        # Should exit with error since no_args_is_help=True
        assert result.exit_code != 0
        assert "Configuration management commands" in result.output
