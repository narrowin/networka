"""Clean help formatting system for CLI commands.

This module provides a clean separation between data and presentation,
making help generation testable and maintainable.
"""

from __future__ import annotations

from typing import Any, Protocol

from .command_config import get_commands_by_category, get_visible_categories
from .metadata import CommandCategory, CommandMetadata


class HelpFormatter(Protocol):
    """Protocol for help formatting implementations."""

    def format_category_section(
        self, formatter: Any, category: CommandCategory, commands: list[tuple[str, str]]
    ) -> None:
        """Format a single category section.

        Args:
            formatter: The Typer/Click formatter object
            category: The category being formatted
            commands: List of (command_name, description) tuples
        """
        ...


class TyperHelpFormatter:
    """Help formatter that works with Typer's Rich formatting."""

    def format_category_section(
        self, formatter: Any, category: CommandCategory, commands: list[tuple[str, str]]
    ) -> None:
        """Format a category section using Typer's formatter.

        Args:
            formatter: The Typer/Click formatter object
            category: The category being formatted
            commands: List of (command_name, description) tuples
        """
        if not commands:
            return

        formatter.write_text(f"\n{category.value}")
        formatter.write_dl(commands)


class HelpGenerator:
    """Generates help output by combining metadata with actual command objects."""

    def __init__(self, formatter: HelpFormatter | None = None) -> None:
        """Initialize with optional custom formatter.

        Args:
            formatter: Custom formatter, defaults to TyperHelpFormatter
        """
        self.formatter = formatter or TyperHelpFormatter()

    def format_commands(self, ctx: Any, formatter: Any, get_command_func: Any) -> None:
        """Format all command help sections.

        Args:
            ctx: The Typer/Click context
            formatter: The Typer/Click formatter object
            get_command_func: Function to get actual command objects
        """
        for category in get_visible_categories():
            commands = self._get_category_commands(category, ctx, get_command_func)
            self.formatter.format_category_section(formatter, category, commands)

    def _get_category_commands(
        self, category: CommandCategory, ctx: Any, get_command_func: Any
    ) -> list[tuple[str, str]]:
        """Get command tuples for a specific category.

        Args:
            category: The category to get commands for
            ctx: The Typer/Click context
            get_command_func: Function to get actual command objects

        Returns:
            List of (command_name, description) tuples
        """
        metadata_commands = get_commands_by_category(category)
        command_tuples = []

        for cmd_metadata in metadata_commands:
            if cmd_metadata.hidden:
                continue

            # Get the actual command object to extract real description
            cmd_obj = get_command_func(ctx, cmd_metadata.name)
            if cmd_obj:
                # Prefer actual command description over metadata
                description = self._get_command_description(cmd_obj, cmd_metadata)
                command_tuples.append((cmd_metadata.name, description))

        return command_tuples

    def _get_command_description(self, cmd_obj: Any, metadata: CommandMetadata) -> str:
        """Extract the best description from a command object.

        Args:
            cmd_obj: The actual Typer/Click command object
            metadata: The command metadata with fallback description

        Returns:
            The best available description string
        """
        # Try different sources in order of preference
        if hasattr(cmd_obj, "get_short_help_str"):
            short_help = cmd_obj.get_short_help_str()
            if short_help:
                return short_help

        if hasattr(cmd_obj, "help") and cmd_obj.help:
            return cmd_obj.help

        # Fallback to metadata description
        return metadata.description
