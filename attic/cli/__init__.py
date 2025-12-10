"""CLI package for command organization and help formatting.

This package provides a clean, maintainable system for organizing CLI commands
into logical categories with proper help formatting.
"""

from .command_config import (
    COMMAND_REGISTRY,
    get_commands_by_category,
    get_visible_categories,
)
from .help_formatter import HelpGenerator, TyperHelpFormatter
from .metadata import CommandCategory, CommandMetadata
from .typer_integration import CategorizedHelpGroup

__all__ = [
    "COMMAND_REGISTRY",
    "CategorizedHelpGroup",
    "CommandCategory",
    "CommandMetadata",
    "HelpGenerator",
    "TyperHelpFormatter",
    "get_commands_by_category",
    "get_visible_categories",
]
