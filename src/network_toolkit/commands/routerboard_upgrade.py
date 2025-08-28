# SPDX-License-Identifier: MIT
"""`nw routerboard-upgrade` command implementation (device or group).

Platform-agnostic BIOS/firmware upgrade using vendor-specific implementations.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import OutputMode
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Executing Operations")
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
        output_mode: Annotated[
            OutputMode | None,
            typer.Option("--output-mode", "-o", help="Output decoration mode"),
        ] = None,
    ) -> None:
        """Upgrade device BIOS/RouterBOOT and reboot to apply.

        Uses platform-specific implementations to handle vendor differences
        in BIOS upgrade procedures.
        """
        # Create command context with automatic config loading
        ctx = CommandContext.from_standard_kwargs(
            config_file=config_file, verbose=verbose, output_mode=output_mode
        )

        try:
            config = ctx.config

            module = import_module("network_toolkit.cli")
            device_session = cast(Any, module).DeviceSession

            devices = config.devices or {}
            groups = config.device_groups or {}
            is_device = target_name in devices
            is_group = target_name in groups

            if not (is_device or is_group):
                ctx.print_error(
                    f"Error: '{target_name}' not found as device or group in configuration"
                )
                if devices:
                    dev_names = sorted(devices.keys())
                    preview = ", ".join(dev_names[:MAX_LIST_PREVIEW])
                    if len(dev_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    ctx.print_info("Known devices: " + preview)
                if groups:
                    grp_names = sorted(groups.keys())
                    preview = ", ".join(grp_names[:MAX_LIST_PREVIEW])
                    if len(grp_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    ctx.print_info("Known groups: " + preview)
                raise typer.Exit(1)

            def process_device(dev: str) -> bool:
                try:
                    with device_session(dev, config) as session:
                        # Get platform-specific operations
                        try:
                            platform_ops = get_platform_operations(session)
                        except UnsupportedOperationError as e:
                            ctx.print_error(f"Error on {dev}: {e}")
                            return False

                        if precheck_sequence and not skip_precheck:
                            ctx.print_info(
                                f"Running precheck sequence '{precheck_sequence}' on {dev}"
                            )
                            seq_cmds: list[str] = []
                            dcfg = (config.devices or {}).get(dev)
                            if (
                                dcfg
                                and dcfg.command_sequences
                                and precheck_sequence in dcfg.command_sequences
                            ):
                                seq_cmds = dcfg.command_sequences[precheck_sequence]
                            elif (
                                config.global_command_sequences
                                and precheck_sequence in config.global_command_sequences
                            ):
                                seq_cmds = config.global_command_sequences[
                                    precheck_sequence
                                ].commands

                            for cmd in seq_cmds:
                                session.execute_command(cmd)

                        ctx.print_warning(
                            f"Upgrading BIOS/RouterBOOT on {dev} and rebooting..."
                        )
                        try:
                            platform_name_obj = platform_ops.get_platform_name()
                            platform_name = str(platform_name_obj)
                        except Exception:  # pragma: no cover - defensive
                            platform_name = "unknown"
                        ctx.print_info(f"Platform: {platform_name}")

                        # Use platform-specific BIOS upgrade
                        ok = platform_ops.bios_upgrade()
                        if ok:
                            ctx.print_success(
                                f"OK BIOS upgrade scheduled; device rebooting: {dev}"
                            )
                            return True
                        ctx.print_error(f"FAIL BIOS upgrade failed to start on {dev}")
                        return False
                except NetworkToolkitError as e:
                    ctx.print_error(f"Error on {dev}: {e.message}")
                    if verbose and e.details:
                        ctx.print_error(f"Details: {e.details}")
                    return False
                except Exception as e:  # pragma: no cover - unexpected
                    ctx.print_error(f"Unexpected error on {dev}: {e}")
                    return False

            if is_device:
                ok = process_device(target_name)
                if not ok:
                    raise typer.Exit(1)
                return

            members: list[str] = []
            try:
                members = config.get_group_members(target_name)
            except Exception:
                grp = groups.get(target_name)
                if grp and getattr(grp, "members", None):
                    members = grp.members or []

            if not members:
                ctx.print_error(f"Error: No devices found in group '{target_name}'")
                raise typer.Exit(1)

            ctx.print_info(
                f"Starting RouterBOARD upgrade for group '{target_name}' ({len(members)} devices)"
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            # Keep summary formatting consistent with other commands
            ctx.output_manager.print_info(
                f"Completed: {total - failures}/{total} initiated"
            )
            if failures:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
