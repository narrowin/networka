"""Clean Typer integration for categorized help.

This module provides a minimal, clean integration with Typer's help system
that follows the framework's design rather than fighting it.
"""

from __future__ import annotations

from typing import Any

from typer.core import TyperGroup

from .command_config import get_all_command_names
from .help_formatter import HelpGenerator


class CategorizedHelpGroup(TyperGroup):
    """Typer group that displays commands in organized categories.

    This class provides a clean, minimal override of Typer's help system
    to organize commands into logical categories while maintaining all
    of Typer's existing functionality.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize the help group with our help generator."""
        super().__init__(*args, **kwargs)
        self._help_generator = HelpGenerator()

    def list_commands(self, ctx: Any) -> list[str]:
        """Return all command names in the correct display order.

        Args:
            ctx: The Typer/Click context

        Returns:
            List of command names in category and order sequence
        """
        return get_all_command_names()

    def format_commands(self, ctx: Any, formatter: Any) -> None:
        """Format command help using our categorized system.

        Args:
            ctx: The Typer/Click context
            formatter: The Typer/Click formatter object
        """
        self._help_generator.format_commands(ctx, formatter, self.get_command)
