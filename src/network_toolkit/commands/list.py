# SPDX-License-Identifier: MIT
"""`nw list` command implementation with subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    """Register the list command group with the Typer app."""

    # Create the list subcommand group
    list_app = typer.Typer(
        name="list",
        help="List network devices, groups, sequences, and platform information",
    )

    @list_app.command("devices")
    def devices(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
    ) -> None:
        """List all configured network devices."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            if not config.devices:
                ctx.print_warning("No devices configured.")
                return

            # Import the device listing logic from the existing command
            from network_toolkit.commands.list_devices import _list_devices_impl

            _list_devices_impl(config, ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("groups")
    def groups(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all configured device groups and their members."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            if not config.device_groups:
                ctx.print_warning("No device groups configured.")
                return

            # Import the group listing logic from the existing command
            from network_toolkit.commands.list_groups import _list_groups_impl

            _list_groups_impl(config, ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("sequences")
    def sequences(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        vendor: Annotated[
            str | None,
            typer.Option("--vendor", "-v", help="Filter by vendor platform"),
        ] = None,
        category: Annotated[
            str | None,
            typer.Option("--category", help="Filter by sequence category"),
        ] = None,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", help="Show detailed information")
        ] = False,
    ) -> None:
        """List all available command sequences, optionally filtered by vendor or category."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            # Import the sequence listing logic from the existing command
            from network_toolkit.commands.list_sequences import _list_sequences_impl

            _list_sequences_impl(config, ctx, vendor, category, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @list_app.command("supported-types")
    def supported_types(
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Show detailed information")
        ] = False,
    ) -> None:
        """Show supported device types and platform information."""
        setup_logging("DEBUG" if verbose else "INFO")

        ctx = CommandContext()

        try:
            # Import the supported types logic from the existing command
            from network_toolkit.commands.info import _show_supported_types_impl

            _show_supported_types_impl(ctx, verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    # Register the list command group with the main app
    app.add_typer(list_app, name="list", rich_help_panel="Info & Configuration")
