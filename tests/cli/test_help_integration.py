"""Integration tests for CLI help output."""

from unittest.mock import Mock, patch

from network_toolkit.cli.help_formatter import HelpGenerator, TyperHelpFormatter
from network_toolkit.cli.metadata import CommandCategory
from network_toolkit.cli.typer_integration import CategorizedHelpGroup


class TestHelpFormatter:
    """Test the help formatting system."""

    def test_typer_help_formatter_basic(self):
        """Test basic help formatting with TyperHelpFormatter."""
        formatter = TyperHelpFormatter()
        mock_typer_formatter = Mock()

        commands = [
            ("run", "Execute commands"),
            ("cli", "CLI to devices"),
        ]

        formatter.format_category_section(
            mock_typer_formatter, CommandCategory.EXECUTING_OPERATIONS, commands
        )

        # Should write category header and command list
        mock_typer_formatter.write_text.assert_called_once_with(
            "\nExecuting Operations"
        )
        mock_typer_formatter.write_dl.assert_called_once_with(commands)

    def test_typer_help_formatter_empty_commands(self):
        """Test that empty command lists don't produce output."""
        formatter = TyperHelpFormatter()
        mock_typer_formatter = Mock()

        formatter.format_category_section(
            mock_typer_formatter, CommandCategory.EXECUTING_OPERATIONS, []
        )

        # Should not call any formatter methods
        mock_typer_formatter.write_text.assert_not_called()
        mock_typer_formatter.write_dl.assert_not_called()


class TestHelpGenerator:
    """Test the help generation logic."""

    def test_help_generator_initialization(self):
        """Test help generator initialization with default formatter."""
        generator = HelpGenerator()
        assert isinstance(generator.formatter, TyperHelpFormatter)

    def test_help_generator_custom_formatter(self):
        """Test help generator with custom formatter."""
        custom_formatter = Mock()
        generator = HelpGenerator(custom_formatter)
        assert generator.formatter is custom_formatter

    def test_get_command_description_priority(self):
        """Test that command description extraction follows correct priority."""
        generator = HelpGenerator()

        # Mock command object with get_short_help_str
        cmd_obj = Mock()
        cmd_obj.get_short_help_str.return_value = "Short help"
        cmd_obj.help = "Long help"

        metadata = Mock()
        metadata.description = "Metadata description"

        description = generator._get_command_description(cmd_obj, metadata)
        assert description == "Short help"

    def test_get_command_description_fallback(self):
        """Test description fallback when command object has no help."""
        generator = HelpGenerator()

        # Mock command object with no help
        cmd_obj = Mock()
        cmd_obj.get_short_help_str.return_value = None
        cmd_obj.help = None

        metadata = Mock()
        metadata.description = "Metadata description"

        description = generator._get_command_description(cmd_obj, metadata)
        assert description == "Metadata description"


class TestCategorizedHelpGroup:
    """Test the Typer integration."""

    def test_list_commands_returns_correct_order(self):
        """Test that list_commands returns commands in correct order."""
        help_group = CategorizedHelpGroup()
        ctx = Mock()

        commands = help_group.list_commands(ctx)

        # Should start with executing operations
        assert commands[0] == "run"
        assert "cli" in commands[:4]  # Should be early in the list

        # Should end with hidden commands
        assert commands[-1] == "complete"

    def test_format_commands_integration(self):
        """Test that format_commands integrates correctly."""
        help_group = CategorizedHelpGroup()

        # Mock the formatter and context
        mock_formatter = Mock()
        mock_ctx = Mock()

        # Mock get_command to return command objects
        def mock_get_command(ctx, name):
            cmd = Mock()
            cmd.get_short_help_str.return_value = f"Description for {name}"
            return cmd

        # Patch the get_command method
        with patch.object(help_group, "get_command", side_effect=mock_get_command):
            # Call format_commands
            help_group.format_commands(mock_ctx, mock_formatter)

        # Should have written category headers
        write_text_calls = mock_formatter.write_text.call_args_list
        category_headers = [call[0][0] for call in write_text_calls]

        assert "\nExecuting Operations" in category_headers
        assert "\nVendor-Specific Operations" in category_headers
        assert "\nInfo & Configuration" in category_headers

        # Should have written command lists
        assert (
            mock_formatter.write_dl.call_count >= 3
        )  # At least one per visible category


class TestCLICommandPlacement:
    """Specific tests for CLI command placement."""

    def test_cli_in_executing_operations_help(self):
        """Test that CLI appears in Executing Operations in help output."""
        help_group = CategorizedHelpGroup()
        mock_formatter = Mock()
        mock_ctx = Mock()

        # Track which commands are placed in which categories
        category_commands = {}

        def capture_write_dl(commands):
            current_category = getattr(mock_formatter, "_current_category", None)
            if current_category:
                category_commands[current_category] = [cmd[0] for cmd in commands]

        def capture_write_text(text):
            if text.startswith("\n"):
                mock_formatter._current_category = text.strip()

        mock_formatter.write_dl.side_effect = capture_write_dl
        mock_formatter.write_text.side_effect = capture_write_text

        # Mock get_command
        def mock_get_command(ctx, name):
            cmd = Mock()
            cmd.get_short_help_str.return_value = f"Description for {name}"
            return cmd

        # Generate help with patched get_command
        with patch.object(help_group, "get_command", side_effect=mock_get_command):
            help_group.format_commands(mock_ctx, mock_formatter)

        # CLI should be in Executing Operations
        executing_commands = category_commands.get("Executing Operations", [])
        assert "cli" in executing_commands

        # CLI should NOT be in other categories
        vendor_commands = category_commands.get("Vendor-Specific Operations", [])
        info_commands = category_commands.get("Info & Configuration", [])

        assert "cli" not in vendor_commands
        assert "cli" not in info_commands
