"""Command structure configuration - Single Source of Truth.

This module defines the complete structure of all CLI commands,
their categories, ordering, and metadata in one centralized location.
"""

from __future__ import annotations

from .metadata import CommandCategory, CommandMetadata

# SINGLE SOURCE OF TRUTH for all command organization
# This is the ONLY place where command categories and ordering are defined
COMMAND_REGISTRY = [
    # Executing Operations - Commands that perform actions on devices
    CommandMetadata(
        name="run",
        category=CommandCategory.EXECUTING_OPERATIONS,
        description="Execute a single command or a sequence on a device or a group.",
        order=10,
    ),
    CommandMetadata(
        name="ssh",
        category=CommandCategory.EXECUTING_OPERATIONS,
        description="Open tmux with SSH panes for a device or group.",
        order=20,
    ),
    CommandMetadata(
        name="upload",
        category=CommandCategory.EXECUTING_OPERATIONS,
        description="Upload a file to a device or to all devices in a group.",
        order=30,
    ),
    CommandMetadata(
        name="download",
        category=CommandCategory.EXECUTING_OPERATIONS,
        description="Download a file from a device or all devices in a group.",
        order=40,
    ),
    # Vendor-Specific Operations - Hardware/firmware specific operations
    CommandMetadata(
        name="backup",
        category=CommandCategory.VENDOR_SPECIFIC,
        description="Backup operations for network devices",
        order=10,
    ),
    CommandMetadata(
        name="firmware",
        category=CommandCategory.VENDOR_SPECIFIC,
        description="Firmware management operations",
        order=20,
    ),
    # Info & Configuration - Information and management commands
    CommandMetadata(
        name="info",
        category=CommandCategory.INFO_CONFIGURATION,
        description="Show comprehensive information for devices, groups, or sequences.",
        order=10,
    ),
    CommandMetadata(
        name="list",
        category=CommandCategory.INFO_CONFIGURATION,
        description="List network devices, groups, sequences, and platform information",
        order=20,
    ),
    CommandMetadata(
        name="config",
        category=CommandCategory.INFO_CONFIGURATION,
        description="Configuration management commands",
        order=30,
    ),
    CommandMetadata(
        name="schema",
        category=CommandCategory.INFO_CONFIGURATION,
        description="JSON schema management commands",
        order=40,
    ),
    CommandMetadata(
        name="diff",
        category=CommandCategory.INFO_CONFIGURATION,
        description="Diff config, a command, or a sequence.",
        order=50,
    ),
    # Hidden commands - Internal/completion commands not shown in help
    CommandMetadata(
        name="complete",
        category=CommandCategory.HIDDEN,
        description="Shell completion support",
        order=10,
        hidden=True,
    ),
]

# Validate the registry at module load time
from .metadata import validate_command_list

validate_command_list(COMMAND_REGISTRY)


def get_commands_by_category(category: CommandCategory) -> list[CommandMetadata]:
    """Get all commands in a specific category, sorted by order.

    Args:
        category: The category to filter by

    Returns:
        List of commands in the category, sorted by order
    """
    commands = [cmd for cmd in COMMAND_REGISTRY if cmd.category == category]
    return sorted(commands, key=lambda cmd: cmd.order)


def get_visible_categories() -> list[CommandCategory]:
    """Get all categories that have visible (non-hidden) commands.

    Returns:
        List of categories that should be shown in help output
    """
    visible_commands = [cmd for cmd in COMMAND_REGISTRY if not cmd.hidden]
    categories = {cmd.category for cmd in visible_commands}

    # Return in display order
    ordered_categories = [
        CommandCategory.EXECUTING_OPERATIONS,
        CommandCategory.VENDOR_SPECIFIC,
        CommandCategory.INFO_CONFIGURATION,
    ]

    return [cat for cat in ordered_categories if cat in categories]


def get_command_metadata(command_name: str) -> CommandMetadata | None:
    """Get metadata for a specific command by name.

    Args:
        command_name: Name of the command to look up

    Returns:
        Command metadata if found, None otherwise
    """
    for cmd in COMMAND_REGISTRY:
        if cmd.name == command_name:
            return cmd
    return None


def get_all_command_names() -> list[str]:
    """Get all command names in display order.

    Returns:
        List of all command names sorted by category and order
    """
    commands = []
    for category in get_visible_categories():
        commands.extend(get_commands_by_category(category))

    # Add hidden commands at the end
    hidden_commands = get_commands_by_category(CommandCategory.HIDDEN)
    commands.extend(hidden_commands)

    return [cmd.name for cmd in commands]
