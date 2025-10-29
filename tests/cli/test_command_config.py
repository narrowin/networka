"""Tests for command configuration and registry."""

from network_toolkit.cli.command_config import (
    COMMAND_REGISTRY,
    get_all_command_names,
    get_command_metadata,
    get_commands_by_category,
    get_visible_categories,
)
from network_toolkit.cli.metadata import CommandCategory


class TestCommandRegistry:
    """Test the command registry configuration."""

    def test_registry_is_valid(self):
        """Test that the command registry is valid and well-formed."""
        # Should not raise any exceptions (validation runs at import time)
        assert len(COMMAND_REGISTRY) > 0

        # All commands should have unique names
        names = [cmd.name for cmd in COMMAND_REGISTRY]
        assert len(names) == len(set(names))

    def test_cli_in_executing_operations(self):
        """Test that CLI command is in the Executing Operations category."""
        cli_metadata = get_command_metadata("cli")

        assert cli_metadata is not None
        assert cli_metadata.category == CommandCategory.EXECUTING_OPERATIONS
        assert cli_metadata.name == "cli"
        assert "tmux" in cli_metadata.description.lower()

    def test_all_expected_commands_present(self):
        """Test that all expected commands are in the registry."""
        expected_commands = {
            "run",
            "cli",
            "upload",
            "download",  # Executing Operations
            "backup",
            "firmware",  # Vendor-Specific
            "info",
            "list",
            "config",
            "schema",
            "diff",  # Info & Configuration
            "complete",  # Hidden
        }

        actual_commands = {cmd.name for cmd in COMMAND_REGISTRY}
        assert actual_commands == expected_commands

    def test_command_categories_logical(self):
        """Test that commands are in logical categories."""
        # Test executing operations
        executing_commands = get_commands_by_category(
            CommandCategory.EXECUTING_OPERATIONS
        )
        executing_names = {cmd.name for cmd in executing_commands}
        assert executing_names == {"run", "cli", "upload", "download"}

        # Test vendor-specific operations
        vendor_commands = get_commands_by_category(CommandCategory.VENDOR_SPECIFIC)
        vendor_names = {cmd.name for cmd in vendor_commands}
        assert vendor_names == {"backup", "firmware"}

        # Test info & configuration
        info_commands = get_commands_by_category(CommandCategory.INFO_CONFIGURATION)
        info_names = {cmd.name for cmd in info_commands}
        assert info_names == {"info", "list", "config", "schema", "diff"}

        # Test hidden commands
        hidden_commands = get_commands_by_category(CommandCategory.HIDDEN)
        hidden_names = {cmd.name for cmd in hidden_commands}
        assert hidden_names == {"complete"}


class TestCommandLookup:
    """Test command lookup functions."""

    def test_get_command_metadata_existing(self):
        """Test getting metadata for existing commands."""
        cli_metadata = get_command_metadata("cli")
        assert cli_metadata is not None
        assert cli_metadata.name == "cli"

        run_metadata = get_command_metadata("run")
        assert run_metadata is not None
        assert run_metadata.name == "run"

    def test_get_command_metadata_nonexistent(self):
        """Test getting metadata for non-existent commands."""
        result = get_command_metadata("nonexistent_command")
        assert result is None

    def test_get_commands_by_category_ordering(self):
        """Test that commands are returned in correct order within categories."""
        executing_commands = get_commands_by_category(
            CommandCategory.EXECUTING_OPERATIONS
        )

        # Should be sorted by order field
        orders = [cmd.order for cmd in executing_commands]
        assert orders == sorted(orders)

        # CLI should come after run (order 20 vs 10)
        names = [cmd.name for cmd in executing_commands]
        cli_index = names.index("cli")
        run_index = names.index("run")
        assert cli_index > run_index


class TestVisibleCategories:
    """Test visible category logic."""

    def test_get_visible_categories(self):
        """Test that visible categories excludes hidden commands."""
        visible_categories = get_visible_categories()

        # Should include all categories except HIDDEN
        expected_categories = [
            CommandCategory.EXECUTING_OPERATIONS,
            CommandCategory.VENDOR_SPECIFIC,
            CommandCategory.INFO_CONFIGURATION,
        ]

        assert visible_categories == expected_categories
        assert CommandCategory.HIDDEN not in visible_categories

    def test_category_display_order(self):
        """Test that categories are returned in correct display order."""
        visible_categories = get_visible_categories()

        expected_order = [
            CommandCategory.EXECUTING_OPERATIONS,
            CommandCategory.VENDOR_SPECIFIC,
            CommandCategory.INFO_CONFIGURATION,
        ]

        assert visible_categories == expected_order


class TestCommandNames:
    """Test command name listing."""

    def test_get_all_command_names_ordering(self):
        """Test that command names are returned in correct display order."""
        all_names = get_all_command_names()

        # Should start with executing operations
        assert all_names[0] == "run"  # First in executing operations
        assert "cli" in all_names[:4]  # Should be in first 4 (executing operations)

        # Hidden commands should be at the end
        assert all_names[-1] == "complete"

    def test_all_command_names_complete(self):
        """Test that all commands are included in the name list."""
        all_names = get_all_command_names()
        registry_names = {cmd.name for cmd in COMMAND_REGISTRY}

        assert set(all_names) == registry_names
        assert len(all_names) == len(registry_names)  # No duplicates
