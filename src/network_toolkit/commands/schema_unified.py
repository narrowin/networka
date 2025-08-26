"""Unified schema commands for the network toolkit CLI."""

from __future__ import annotations

from typing import Annotated

import typer

from network_toolkit.common.logging import setup_logging
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    """Register the unified schema command group with the main CLI app."""
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
            from network_toolkit.commands.schema import _schema_update_impl

            _schema_update_impl(verbose=verbose)

        except NetworkToolkitError as e:
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @schema_app.command("info")
    def info(
        verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
    ) -> None:
        """Display information about JSON schema files."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            from network_toolkit.commands.schema import _schema_info_impl

            _schema_info_impl(verbose=verbose)

        except NetworkToolkitError as e:
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    app.add_typer(schema_app, name="schema")
