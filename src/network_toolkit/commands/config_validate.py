# SPDX-License-Identifier: MIT
"""`nw config-validate` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command("config-validate", rich_help_panel="Info & Configuration")
    def config_validate(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose", "-v", help="Show detailed validation information"
            ),
        ] = False,
    ) -> None:
        """Validate the configuration file and show any issues."""
        setup_logging("DEBUG" if verbose else "INFO")
        
        # ACTION command - use global config theme
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=None  # Use global config theme
        )

        try:
            console.print(
                f"[bold blue]Validating Configuration: {config_file}[/bold blue]"
            )
            console.print()

            config = load_config(config_file)

            console.print("[bold green]OK Configuration is valid![/bold green]")
            console.print()

            device_count = len(config.devices) if config.devices else 0
            group_count = len(config.device_groups) if config.device_groups else 0
            global_seq_count = (
                len(config.global_command_sequences)
                if config.global_command_sequences
                else 0
            )

            console.print(f"📱 Devices: {device_count}")
            console.print(f"👥 Device Groups: {group_count}")
            console.print(f"🔄 Global Sequences: {global_seq_count}")

            if verbose and device_count > 0 and config.devices:
                console.print("\n[bold]Device Summary:[/bold]")
                for name, device in config.devices.items():
                    console.print(f"  • {name} ({device.host}) - {device.device_type}")

        except NetworkToolkitError as e:
            ctx.print_error("FAIL Configuration validation failed!")
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"FAIL Unexpected error during validation: {e}")
            raise typer.Exit(1) from None
