# SPDX-License-Identifier: MIT
"""`nw routerboard-upgrade` command implementation (device or group).

Platform-agnostic BIOS/firmware upgrade using vendor-specific implementations.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH

# For backward compatibility with tests
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def routerboard_upgrade(  # pyright: ignore[reportUnusedFunction]
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        *,
        precheck_sequence: Annotated[
            str,
            typer.Option(
                "--precheck-sequence",
                help=("Sequence to run before upgrade (default: 'pre_maintenance')"),
            ),
        ] = "pre_maintenance",
        skip_precheck: Annotated[
            bool,
            typer.Option(
                "--skip-precheck/--no-skip-precheck",
                help="Skip running precheck sequence",
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Upgrade device BIOS/RouterBOOT and reboot to apply.

        Uses platform-specific implementations to handle vendor differences
        in BIOS upgrade procedures.
        """
        setup_logging("DEBUG" if verbose else "WARNING")

        # ACTION command - use global config theme
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=None,  # Use global config theme
        )

        try:
            config = load_config(config_file)
            from network_toolkit.api.routerboard_upgrade import (
                RouterboardUpgradeOptions,
                upgrade_routerboard,
            )

            options = RouterboardUpgradeOptions(
                target=target_name,
                config=config,
                precheck_sequence=precheck_sequence,
                skip_precheck=skip_precheck,
                verbose=verbose,
            )

            result = upgrade_routerboard(options)

            # Render results
            is_group = result.success_count + result.failed_count > 1
            if is_group:
                ctx.print_info(
                    f"Starting RouterBOARD upgrade for group '{target_name}' ({len(result.results)} devices)"
                )

            for dev_res in result.results:
                if dev_res.success:
                    if dev_res.platform != "unknown":
                        ctx.print_info(f"Platform: {dev_res.platform}")
                    ctx.print_success(f"OK {dev_res.message}: {dev_res.device_name}")
                elif "BIOS upgrade failed to start" in dev_res.message:
                    if dev_res.platform != "unknown":
                        ctx.print_info(f"Platform: {dev_res.platform}")
                    ctx.print_error(f"FAIL {dev_res.message} on {dev_res.device_name}")
                else:
                    ctx.print_error(
                        f"Error on {dev_res.device_name}: {dev_res.message}"
                    )
                    if verbose and dev_res.error_details:
                        ctx.print_error(f"Details: {dev_res.error_details}")

            if is_group:
                total = len(result.results)
                ctx.output_manager.print_info(
                    f"Completed: {result.success_count}/{total} initiated"
                )

            if result.failed_count > 0:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
