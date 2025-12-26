# SPDX-License-Identifier: MIT
"""`nw list` command implementation with subcommands."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.table_providers import (
    DeviceListTableProvider,
    GroupListTableProvider,
    VendorSequencesTableProvider,
)
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError

if TYPE_CHECKING:
    pass


def _list_devices_impl(
    config: NetworkConfig, ctx: CommandContext, *, verbose: bool
) -> None:
    """Implementation logic for listing devices."""
    from network_toolkit.api.list import get_device_list

    devices = get_device_list(config)
    if not devices:
        ctx.print_warning("No devices configured")
        return

    provider = DeviceListTableProvider(devices=devices)
    ctx.render_table(provider, verbose)


def _list_groups_impl(
    config: NetworkConfig, ctx: CommandContext, *, verbose: bool
) -> None:
    """Implementation logic for listing groups."""
    from network_toolkit.api.list import get_group_list

    groups = get_group_list(config)
    if not groups:
        ctx.print_warning("No device groups configured")
        return

    provider = GroupListTableProvider(groups=groups)
    ctx.render_table(provider, verbose)


def _list_sequences_impl(
    config: NetworkConfig,
    ctx: CommandContext,
    vendor: str | None,
    category: str | None,
    *,
    verbose: bool,
) -> None:
    """Implementation logic for listing sequences."""
    from network_toolkit.api.list import get_sequence_list

    sequences = get_sequence_list(config, vendor=vendor, category=category)

    if not sequences:
        if vendor:
            ctx.print_warning(f"No sequences found for vendor '{vendor}'.")
        elif category:
            ctx.print_warning(f"No sequences found for category '{category}'.")
        else:
            ctx.print_warning("No vendor-specific sequences found.")
        return

    provider = VendorSequencesTableProvider(
        sequences=sequences, vendor_filter=vendor, verbose=verbose
    )
    ctx.render_table(provider, verbose)


def register(app: typer.Typer) -> None:
    """Register the list command group with the Typer app."""

    # Create the list subcommand group
    list_app = typer.Typer(
        name="list",
        help="List network devices, groups, sequences, and platform information",
        no_args_is_help=True,
        context_settings={"help_option_names": ["-h", "--help"]},
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
        setup_logging("DEBUG" if verbose else "WARNING")

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

            # Use the local implementation
            _list_devices_impl(config, ctx, verbose=verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
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
        setup_logging("DEBUG" if verbose else "WARNING")

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

            # Use the local implementation
            _list_groups_impl(config, ctx, verbose=verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
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
        """List all available command sequences, optionally filtered by vendor
        or category."""
        setup_logging("DEBUG" if verbose else "WARNING")

        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )

        try:
            config = load_config(config_file)

            # Use the local implementation
            _list_sequences_impl(config, ctx, vendor, category, verbose=verbose)

        except NetworkToolkitError as e:
            ctx.print_error(str(e))
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    # Register the list command group with the main app
    app.add_typer(list_app, name="list", rich_help_panel="Info & Configuration")
