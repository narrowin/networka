"""Tests for the unified `nw schema` command and its subcommands."""

from __future__ import annotations

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class TestSchemaCommand:
    """Test the nw schema command group and its subcommands."""

    def test_schema_command_help(self) -> None:
        """Test that schema command shows its subcommands."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema", "--help"])

        assert result.exit_code == 0
        assert "update" in result.output
        assert "info" in result.output

    @patch("network_toolkit.commands.schema._schema_update_impl")
    def test_schema_update_basic(self, mock_impl: Mock) -> None:
        """Test schema update subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema", "update"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["verbose"] is False

    @patch("network_toolkit.commands.schema._schema_update_impl")
    def test_schema_update_verbose(self, mock_impl: Mock) -> None:
        """Test schema update with verbose option."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema", "update", "--verbose"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["verbose"] is True

    @patch("network_toolkit.commands.schema._schema_info_impl")
    def test_schema_info_basic(self, mock_impl: Mock) -> None:
        """Test schema info subcommand."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema", "info"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["verbose"] is False

    @patch("network_toolkit.commands.schema._schema_info_impl")
    def test_schema_info_verbose(self, mock_impl: Mock) -> None:
        """Test schema info with verbose option."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema", "info", "--verbose"])

        assert result.exit_code == 0
        mock_impl.assert_called_once()
        call_args = mock_impl.call_args
        assert call_args.kwargs["verbose"] is True

    def test_schema_no_subcommand(self) -> None:
        """Test that schema without subcommand shows help."""
        runner = CliRunner()
        result = runner.invoke(app, ["schema"])

        # Should exit with error since no_args_is_help=True
        assert result.exit_code != 0
        assert "JSON schema management commands" in result.output
