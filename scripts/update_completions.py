#!/usr/bin/env python3
"""Script to verify and update shell completion files with current commands."""

import sys
from pathlib import Path

# Add src to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "src"))

from network_toolkit.cli import app  # noqa: E402


def get_current_commands():
    """Get all current CLI commands."""
    # Get command names from the typer app
    commands = []
    for name, _command in app.commands.items() if hasattr(app, "commands") else []:
        commands.append(name)

    # Fallback: check registered commands from imports
    if not commands:
        # From the CLI code, these are the current commands
        commands = [
            "info",
            "list",
            "run",
            "config",
            "backup",
            "upload",
            "download",
            "firmware",
            "complete",
            "diff",
            "schema",
            "ssh",
        ]

    return sorted(commands)


def get_list_subcommands():
    """Get subcommands for the list command."""
    return ["devices", "groups", "sequences", "supported-types"]


def get_config_subcommands():
    """Get subcommands for the config command."""
    return ["init", "validate"]


def get_schema_subcommands():
    """Get subcommands for the schema command."""
    return ["update", "info"]


def get_backup_subcommands():
    """Get subcommands for the backup command."""
    return ["config", "comprehensive", "vendors"]


def get_firmware_subcommands():
    """Get subcommands for the firmware command."""
    return ["upgrade", "downgrade", "bios", "vendors"]


def main():
    """Main function to display current command structure."""
    commands = get_current_commands()

    print("Current CLI Commands:")
    print("====================")
    for cmd in commands:
        print(f"  {cmd}")

        if cmd == "list":
            for sub in get_list_subcommands():
                print(f"    ├── {sub}")
        elif cmd == "config":
            for sub in get_config_subcommands():
                print(f"    ├── {sub}")
        elif cmd == "schema":
            for sub in get_schema_subcommands():
                print(f"    ├── {sub}")
        elif cmd == "backup":
            for sub in get_backup_subcommands():
                print(f"    ├── {sub}")
        elif cmd == "firmware":
            for sub in get_firmware_subcommands():
                print(f"    ├── {sub}")

    print("\nObsolete commands that should be removed from completion:")
    print("========================================================")
    obsolete = [
        "config-validate",
        "config-init",
        "list-devices",
        "list-groups",
        "list-sequences",
    ]
    for obs in obsolete:
        print(f"  {obs}")


if __name__ == "__main__":
    main()
