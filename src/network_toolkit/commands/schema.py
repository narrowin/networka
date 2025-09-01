# SPDX-License-Identifier: MIT
"""Schema management commands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.logging import setup_logging
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    """Register schema commands with the CLI app."""
    schema_app = typer.Typer(
        name="schema",
        help="JSON schema management commands",
        no_args_is_help=True,
    )

    @schema_app.command("update")
    def update(
        verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    ) -> None:
        """Update JSON schemas for YAML editor validation.

        Regenerates the JSON schema files used by VS Code and other YAML editors
        to provide validation and auto-completion for configuration files.

        Creates/updates:
        - schemas/network-config.schema.json (full config)
        - schemas/device-config.schema.json (device collections)
        - schemas/groups-config.schema.json (group collections)
        - .vscode/settings.json (VS Code YAML validation)
        """
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            _schema_update_impl(verbose=verbose)
        except NetworkToolkitError as e:
            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            raise
        except Exception as e:
            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @schema_app.command("info")
    def info(
        verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    ) -> None:
        """Display JSON schema status.

        Shows the status of JSON schema files used for YAML validation in editors
        like VS Code. These schemas provide auto-completion and error checking
        for network toolkit configuration files.
        """
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            _schema_info_impl(verbose=verbose)
        except NetworkToolkitError as e:
            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            raise
        except Exception as e:
            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    app.add_typer(schema_app, name="schema", rich_help_panel="Info & Configuration")


def _schema_update_impl(verbose: bool = False) -> None:
    """Update JSON schemas for YAML editor validation.

    Args:
        verbose: Enable verbose output

    Raises:
        NetworkToolkitError: If schema update fails
    """
    ctx = CommandContext()

    try:
        from network_toolkit.config import export_schemas_to_workspace

        export_schemas_to_workspace()
        ctx.print_success("JSON schemas updated successfully")

    except Exception as e:
        msg = f"Failed to update schemas: {e}"
        raise NetworkToolkitError(msg) from e


def _schema_info_impl(verbose: bool = False) -> None:
    """Display information about JSON schema files.

    Args:
        verbose: Enable verbose output
    """
    ctx = CommandContext()

    # Always explain what schemas are for
    ctx.print_info(
        "JSON schemas provide YAML validation and auto-completion in editors"
    )
    ctx.print_info(
        "They enable error checking and IntelliSense for configuration files"
    )

    schema_dir = Path("schemas")
    schema_files = [
        "network-config.schema.json",
        "device-config.schema.json",
        "groups-config.schema.json",
    ]
    vscode_settings = Path(".vscode/settings.json")

    missing_files: list[str] = []
    for filename in schema_files:
        if not (schema_dir / filename).exists():
            missing_files.append(filename)

    if not vscode_settings.exists():
        missing_files.append(".vscode/settings.json")

    if not missing_files:
        ctx.print_success("All schema files present and configured")
    else:
        ctx.print_warning(f"Missing {len(missing_files)} schema files")
        if verbose:
            for missing in missing_files:
                ctx.print_info(f"Missing: {missing}")
        ctx.print_info("Run 'nw schema update' to generate missing files")
