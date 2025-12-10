"""Command metadata and categorization system.

This module provides the core data structures for organizing CLI commands
into logical categories with proper ordering and metadata.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable


class CommandCategory(Enum):
    """Categories for organizing CLI commands in help output."""

    EXECUTING_OPERATIONS = "Executing Operations"
    VENDOR_SPECIFIC = "Vendor-Specific Operations"
    INFO_CONFIGURATION = "Info & Configuration"
    HIDDEN = "Hidden"  # For internal/completion commands


@dataclass(frozen=True)
class CommandMetadata:
    """Metadata for a single CLI command.

    Attributes:
        name: The command name as it appears in CLI
        category: Which help section this command belongs to
        description: Short help text for the command
        order: Sort order within the category (lower = earlier)
        hidden: Whether to hide this command from help output
    """

    name: str
    category: CommandCategory
    description: str
    order: int = 50  # Default middle ordering
    hidden: bool = False

    def __post_init__(self) -> None:
        """Validate metadata after creation."""
        if not self.name:
            raise ValueError("Command name cannot be empty")
        if not self.description and not self.hidden:
            raise ValueError(
                f"Command '{self.name}' must have a description unless hidden"
            )
        if self.order < 0:
            raise ValueError(f"Command '{self.name}' order must be non-negative")


def validate_command_list(commands: list[CommandMetadata]) -> None:
    """Validate a list of command metadata for consistency.

    Args:
        commands: List of command metadata to validate

    Raises:
        ValueError: If there are duplicate command names or other issues
    """
    names = [cmd.name for cmd in commands]
    duplicates = [name for name in names if names.count(name) > 1]
    if duplicates:
        raise ValueError(f"Duplicate command names found: {set(duplicates)}")

    for cmd in commands:
        # Additional validation can be added here
        if cmd.category == CommandCategory.HIDDEN and not cmd.hidden:
            raise ValueError(
                f"Command '{cmd.name}' in HIDDEN category must have hidden=True"
            )
