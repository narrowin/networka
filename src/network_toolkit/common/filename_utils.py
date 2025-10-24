# SPDX-License-Identifier: MIT
"""Centralized filename normalization utilities for backup and results."""

from __future__ import annotations

import re


def normalize_filename(text: str, max_length: int = 100) -> str:
    """Normalize text for use as a filename.

    Creates clean, readable filenames by:
    - Removing or replacing special characters
    - Collapsing whitespace and separators
    - Removing redundant parts from command strings
    - Limiting length

    Parameters
    ----------
    text : str
        Text to normalize (command, description, etc.)
    max_length : int, default=100
        Maximum length for the resulting filename

    Returns
    -------
    str
        Normalized filename safe for filesystem use

    Examples
    --------
    >>> normalize_filename("/export compact file=nw-export")
    'export_compact'
    >>> normalize_filename("/system/backup/save name=nw-backup")
    'system_backup_save'
    >>> normalize_filename("/system resource print")
    'system_resource_print'
    """
    # Strip leading/trailing whitespace
    text = text.strip()

    # Remove leading slash (common in RouterOS commands)
    if text.startswith("/"):
        text = text[1:]

    # Extract command name before file parameters
    # For commands like "/export file=name" or "/system/backup/save name=file"
    # we want just the command part, not the file parameters
    # Also handle RouterOS 'where' clauses
    parts = text.split()
    if len(parts) > 1:
        # Find where file/name parameters or where clauses start
        command_parts = []
        for part in parts:
            # Stop at parameter assignments (file=, name=, etc.) or where clauses
            if "=" in part or part.lower() == "where":
                break
            command_parts.append(part)
        if command_parts:
            text = " ".join(command_parts)

    # Replace path separators and special chars with underscores
    text = re.sub(r'[/\\:*?"<>|=]', "_", text)

    # Replace spaces and multiple underscores with single underscores
    text = re.sub(r"[\s_]+", "_", text)

    # Remove leading/trailing underscores and dots
    text = text.strip("_.")

    # Limit length
    if len(text) > max_length:
        text = text[:max_length].rstrip("_.")

    # Ensure we have something
    if not text:
        text = "output"

    return text


def normalize_command_output_filename(command: str) -> str:
    """Create a normalized filename for command output.

    Specifically designed for command output files, adds .txt extension.

    Parameters
    ----------
    command : str
        Command string to create filename from

    Returns
    -------
    str
        Normalized filename with .txt extension

    Examples
    --------
    >>> normalize_command_output_filename("/system resource print")
    'system_resource_print.txt'
    >>> normalize_command_output_filename("/export compact file=nw-export")
    'export_compact.txt'
    """
    base = normalize_filename(command)
    return f"{base}.txt"
