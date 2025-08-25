# SPDX-License-Identifier: MIT
"""`nw firmware-downgrade` command implementation (device or group).

Platform-agnostic firmware downgrade using ve                            console.print(
                                style_manager.format_message(
                                    f"Running precheck sequence '{precheck_sequence}' on {dev}...",
                                    StyleName.INFO,
                                )
                            )specific implementations.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.styles import StyleManager, StyleName
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Vendor-Specific Operations")
    def firmware_downgrade(  # pyright: ignore[reportUnusedFunction]
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        firmware_file: Annotated[
            Path,
            typer.Argument(help="Path to local firmware package"),
        ],
        *,
        precheck_sequence: Annotated[
            str,
            typer.Option(
                "--precheck-sequence",
                help=("Sequence to run before downgrade (default: 'pre_maintenance')"),
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
        """Upload older firmware package, schedule downgrade, and reboot to apply.

        Uses platform-specific implementations to handle vendor differences
        in firmware downgrade procedures.
        """
        setup_logging("DEBUG" if verbose else "INFO")

        # Create style manager for consistent theming
        style_manager = StyleManager(mode=OutputMode.DEFAULT)
        console = style_manager.console

        try:
            if not firmware_file.exists() or not firmware_file.is_file():
                console.print(
                    style_manager.format_message(
                        f"Error: Firmware file not found: {firmware_file}",
                        StyleName.ERROR,
                    )
                )
                raise typer.Exit(1)

            # Validate firmware file extension using platform-specific logic
            config = load_config(config_file)

            module = import_module("network_toolkit.cli")
            device_session = cast(Any, module).DeviceSession

            devices = config.devices or {}
            groups = config.device_groups or {}
            is_device = target_name in devices
            is_group = target_name in groups

            if not (is_device or is_group):
                console.print(
                    style_manager.format_message(
                        f"Error: '{target_name}' not found as device or group in configuration",
                        StyleName.ERROR,
                    )
                )
                if devices:
                    dev_names = sorted(devices.keys())
                    preview = ", ".join(dev_names[:MAX_LIST_PREVIEW])
                    if len(dev_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    console.print(
                        style_manager.format_message(
                            "Known devices:", StyleName.WARNING
                        )
                        + " "
                        + preview
                    )
                if groups:
                    grp_names = sorted(groups.keys())
                    preview = ", ".join(grp_names[:MAX_LIST_PREVIEW])
                    if len(grp_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    console.print(
                        style_manager.format_message("Known groups:", StyleName.WARNING)
                        + " "
                        + preview
                    )
                raise typer.Exit(1)

            def process_device(dev: str) -> bool:
                try:
                    with device_session(dev, config) as session:
                        # Get platform-specific operations
                        try:
                            platform_ops = get_platform_operations(session)
                        except UnsupportedOperationError as e:
                            console.print(
                                style_manager.format_message(
                                    f"Error on {dev}: {e}", StyleName.ERROR
                                )
                            )
                            return False

                        # Validate firmware file extension for this platform
                        supported_exts = platform_ops.get_supported_file_extensions()
                        if firmware_file.suffix.lower() not in supported_exts:
                            ext_list = ", ".join(supported_exts)
                            console.print(
                                style_manager.format_message(
                                    f"Error: Invalid firmware file for {platform_ops.get_platform_name()}. "
                                    f"Expected {ext_list}, got {firmware_file.suffix}",
                                    StyleName.ERROR,
                                )
                            )
                            return False

                        if precheck_sequence and not skip_precheck:
                            console.print(
                                style_manager.format_message(
                                    f"Running precheck sequence '{precheck_sequence}' on {dev}",
                                    StyleName.INFO,
                                )
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

                        console.print(
                            style_manager.format_message(
                                f"Downgrading firmware on {dev} and rebooting...",
                                StyleName.WARNING,
                            )
                        )
                        platform_name = platform_ops.get_platform_name()
                        console.print(
                            style_manager.format_message("Platform:", StyleName.WARNING)
                            + f" {platform_name}"
                        )

                        # Use platform-specific firmware downgrade
                        ok = platform_ops.firmware_downgrade(
                            local_firmware_path=firmware_file
                        )
                        if ok:
                            console.print(
                                style_manager.format_message(
                                    f"OK Firmware downgrade initiated; device rebooting: {dev}",
                                    StyleName.SUCCESS,
                                )
                            )
                            return True
                        console.print(
                            style_manager.format_message(
                                f"FAIL Firmware downgrade failed to start on {dev}",
                                StyleName.ERROR,
                            )
                        )
                        return False
                except NetworkToolkitError as e:
                    console.print(
                        style_manager.format_message(
                            f"Error on {dev}: {e.message}", StyleName.ERROR
                        )
                    )
                    if verbose and e.details:
                        console.print(
                            style_manager.format_message(
                                f"Details: {e.details}", StyleName.ERROR
                            )
                        )
                    return False
                except Exception as e:  # pragma: no cover - unexpected
                    console.print(
                        style_manager.format_message(
                            f"Unexpected error on {dev}: {e}", StyleName.ERROR
                        )
                    )
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
                console.print(
                    style_manager.format_message(
                        f"Error: No devices found in group '{target_name}'",
                        StyleName.ERROR,
                    )
                )
                raise typer.Exit(1)

            console.print(
                style_manager.format_message(
                    f"Starting firmware downgrade for group '{target_name}' ({len(members)} devices)",
                    StyleName.INFO,
                )
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            console.print(
                style_manager.format_message("Completed:", StyleName.BOLD)
                + f" {total - failures}/{total} initiated"
            )
            if failures:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            console.print(
                style_manager.format_message(f"Error: {e.message}", StyleName.ERROR)
            )
            if verbose and e.details:
                console.print(
                    style_manager.format_message(
                        f"Details: {e.details}", StyleName.ERROR
                    )
                )
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(
                style_manager.format_message(f"Unexpected error: {e}", StyleName.ERROR)
            )
            raise typer.Exit(1) from None
