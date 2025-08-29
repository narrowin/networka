# SPDX-License-Identifier: MIT
"""`nw config-backup` command implementation (device or group).

Vendor-specific configuration backup using platform-specific implementations.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.styles import StyleName
from network_toolkit.config import DeviceConfig, NetworkConfig
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

MAX_LIST_PREVIEW = 10


def _resolve_config_backup_sequence(
    config: NetworkConfig, device_name: str
) -> list[str] | None:
    """Resolve the configuration backup command sequence for a device.

    Preference order: device-specific sequence named 'config_backup' then
    global command sequence 'config_backup'.
    """
    # Device-specific override
    devices = config.devices or {}
    dev_cfg: DeviceConfig | None = devices.get(device_name)
    if dev_cfg and dev_cfg.command_sequences:
        seq = dev_cfg.command_sequences.get("config_backup")
        if seq:
            return list(seq)

    # Global sequence
    global_seqs = config.global_command_sequences or {}
    if "config_backup" in global_seqs:
        return list(global_seqs["config_backup"].commands)

    return None


def register(app: typer.Typer) -> None:
    """Register config-backup command with the application."""

    def _config_backup_impl(
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        *,
        download: Annotated[
            bool,
            typer.Option(
                "--download/--no-download",
                help=(
                    "Download created configuration backup files after running the sequence"
                ),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=(
                    "Delete remote configuration backup files after successful download"
                ),
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
        """Create device configuration backup using vendor-specific commands.

        Creates a text representation of the device configuration using
        platform-specific implementations to handle vendor differences
        in configuration backup procedures.

        MikroTik RouterOS: Uses /export commands
        Cisco IOS/IOS-XE: Uses show running-config commands
        """
        ctx = CommandContext.from_standard_kwargs(
            config_file=config_file, verbose=verbose, output_mode=output_mode
        )
        style_manager = ctx.style_manager

        try:
            config = ctx.config

            # Resolve DeviceSession from cli to preserve tests patching path
            module = import_module("network_toolkit.cli")
            device_session = cast(Any, module).DeviceSession
            handle_downloads = cast(Any, module)._handle_file_downloads

            devices = config.devices or {}
            groups = config.device_groups or {}
            is_device = target_name in devices
            is_group = target_name in groups

            if not (is_device or is_group):
                ctx.output_manager.print_text(
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
                    ctx.output_manager.print_text(
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
                    ctx.output_manager.print_text(
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
                            ctx.output_manager.print_text(
                                style_manager.format_message(
                                    f"Error on {dev}: {e}", StyleName.ERROR
                                )
                            )
                            return False

                        # Resolve config backup sequence (device-specific or global)
                        seq_cmds = _resolve_config_backup_sequence(config, dev)
                        if not seq_cmds:
                            ctx.output_manager.print_text(
                                style_manager.format_message(
                                    f"Error: configuration backup sequence 'config_backup' not defined for {dev}",
                                    StyleName.ERROR,
                                )
                            )
                            return False

                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"Creating configuration backup on {dev}",
                                StyleName.INFO,
                            )
                        )
                        transport_type = config.get_transport_type(dev)
                        # Be defensive with platform name when mocks are used
                        try:
                            platform_name_obj = platform_ops.get_platform_name()
                            platform_name = str(platform_name_obj)
                        except Exception:  # pragma: no cover - defensive
                            platform_name = "unknown"
                        ctx.output_manager.print_text(
                            style_manager.format_message("Platform:", StyleName.WARNING)
                            + f" {platform_name}"
                        )
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                "Transport:", StyleName.WARNING
                            )
                            + f" {transport_type}"
                        )

                        # Use platform-specific config backup creation
                        backup_success = platform_ops.config_backup(
                            backup_sequence=seq_cmds,
                            download_files=None,  # Will handle downloads separately
                        )

                        if not backup_success:
                            ctx.output_manager.print_text(
                                style_manager.format_message(
                                    f"Error: Configuration backup creation failed on {dev}",
                                    StyleName.ERROR,
                                )
                            )
                            return False

                        if download:
                            # Platform-specific download files for config backup
                            downloads: list[dict[str, Any]] = []

                            # Determine platform-specific file names
                            if "mikrotik" in platform_name.lower():
                                downloads = [
                                    {
                                        "remote_file": "nw-config-export.rsc",
                                        "local_path": str(config.general.backup_dir),
                                        "local_filename": (
                                            "{device}_{date}_config.rsc"
                                        ),
                                        "delete_remote": delete_remote,
                                    },
                                ]
                            elif "cisco" in platform_name.lower():
                                # For Cisco devices, configuration is typically displayed, not saved to file
                                ctx.output_manager.print_text(
                                    style_manager.format_message(
                                        f"Note: Cisco platform '{platform_name}' typically shows configuration output rather than saving to files",
                                        StyleName.WARNING,
                                    )
                                )
                                downloads = []

                            if downloads:
                                # Only call helper if available to satisfy legacy tests
                                if hasattr(module, "_handle_file_downloads"):
                                    handle_downloads(
                                        session=session,
                                        device_name=dev,
                                        download_files=downloads,
                                        config=config,
                                    )
                                else:  # pragma: no cover - defensive
                                    ctx.output_manager.print_text(
                                        style_manager.format_message(
                                            "Download helper not available; skipping file downloads",
                                            StyleName.WARNING,
                                        )
                                    )
                        return True
                except NetworkToolkitError as e:
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Error on {dev}: {e.message}", StyleName.ERROR
                        )
                    )
                    if verbose and e.details:
                        ctx.output_manager.print_text(
                            style_manager.format_message(
                                f"Details: {e.details}", StyleName.ERROR
                            )
                        )
                    return False
                except Exception as e:  # pragma: no cover - unexpected
                    ctx.output_manager.print_text(
                        style_manager.format_message(
                            f"Unexpected error on {dev}: {e}", StyleName.ERROR
                        )
                    )
                    return False

            if is_device:
                ok = process_device(target_name)
                if not ok:
                    raise typer.Exit(1)
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        "Configuration backup completed", StyleName.SUCCESS
                    )
                )
                return

            # Group path
            members: list[str] = []
            try:
                members = config.get_group_members(target_name)
            except Exception:
                grp = groups.get(target_name)
                if grp and getattr(grp, "members", None):
                    members = grp.members or []

            if not members:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Error: No devices found in group '{target_name}'",
                        StyleName.ERROR,
                    )
                )
                raise typer.Exit(1)

            ctx.output_manager.print_text(
                style_manager.format_message(
                    f"Starting configuration backups for group: {target_name}",
                    StyleName.INFO,
                )
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            ctx.output_manager.print_text(
                style_manager.format_message("Completed:", StyleName.BOLD)
                + f" {total - failures}/{total} successful configuration backups"
            )
            if failures:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.output_manager.print_text(
                style_manager.format_message(f"Error: {e.message}", StyleName.ERROR)
            )
            if verbose and e.details:
                ctx.output_manager.print_text(
                    style_manager.format_message(
                        f"Details: {e.details}", StyleName.ERROR
                    )
                )
            raise typer.Exit(1) from e

    # Register the main config-backup command
    @app.command(
        rich_help_panel="Vendor-Specific Remote Operations", name="config-backup"
    )
    def config_backup(
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration", metavar="<device|group>"
            ),
        ],
        *,
        download: Annotated[
            bool,
            typer.Option(
                "--download/--no-download",
                help=(
                    "Download created configuration backup files after running the sequence"
                ),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=(
                    "Delete remote configuration backup files after successful download"
                ),
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
        """Create device configuration backup using vendor-specific commands."""
        _config_backup_impl(
            target_name,
            download=download,
            delete_remote=delete_remote,
            config_file=config_file,
            verbose=verbose,
            output_mode=output_mode,
        )
