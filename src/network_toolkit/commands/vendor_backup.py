# SPDX-License-Identifier: MIT
"""`nw backup` command implementation (device or group).

Vendor-specific comprehensive backup using platform-specific implementations.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import DeviceConfig, NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

MAX_LIST_PREVIEW = 10


def _resolve_backup_sequence(
    config: NetworkConfig, device_name: str
) -> list[str] | None:
    """Resolve the comprehensive backup command sequence for a device.

    Preference order: device-specific sequence named 'backup' then
    global command sequence 'backup'.
    """
    # Device-specific override
    devices = config.devices or {}
    dev_cfg: DeviceConfig | None = devices.get(device_name)
    if dev_cfg and dev_cfg.command_sequences:
        seq = dev_cfg.command_sequences.get("backup")
        if seq:
            return list(seq)

    # Global sequence
    global_seqs = config.global_command_sequences or {}
    if "backup" in global_seqs:
        return list(global_seqs["backup"].commands)

    return None


def register(app: typer.Typer) -> None:
    """Register backup command with the application."""

    def _backup_impl(
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
                help=("Download created backup files after running the sequence"),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=("Delete remote backup files after successful download"),
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Create comprehensive device backup using vendor-specific commands.

        Creates both text and binary backups of the device using
        platform-specific implementations to handle vendor differences
        in backup procedures.

        MikroTik RouterOS: Uses /export and /system/backup commands
        Cisco IOS/IOS-XE: Uses show running-config, show startup-config, show version, etc.
        """
        setup_logging("DEBUG" if verbose else "INFO")
        try:
            config = load_config(config_file)

            # Resolve DeviceSession from cli to preserve tests patching path
            module = import_module("network_toolkit.cli")
            device_session = cast(Any, module).DeviceSession
            handle_downloads = cast(Any, module)._handle_file_downloads

            devices = config.devices or {}
            groups = config.device_groups or {}
            is_device = target_name in devices
            is_group = target_name in groups

            if not (is_device or is_group):
                console.print(
                    f"[red]Error: '{target_name}' not found as device or group in "
                    "configuration[/red]"
                )
                if devices:
                    dev_names = sorted(devices.keys())
                    preview = ", ".join(dev_names[:MAX_LIST_PREVIEW])
                    if len(dev_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    console.print("[yellow]Known devices:[/yellow] " + preview)
                if groups:
                    grp_names = sorted(groups.keys())
                    preview = ", ".join(grp_names[:MAX_LIST_PREVIEW])
                    if len(grp_names) > MAX_LIST_PREVIEW:
                        preview += " ..."
                    console.print("[yellow]Known groups:[/yellow] " + preview)
                raise typer.Exit(1)

            def process_device(dev: str) -> bool:
                try:
                    with device_session(dev, config) as session:
                        # Get platform-specific operations
                        try:
                            platform_ops = get_platform_operations(session)
                        except UnsupportedOperationError as e:
                            console.print(f"[red]Error on {dev}: {e}[/red]")
                            return False

                        # Resolve backup sequence (device-specific or global)
                        seq_cmds = _resolve_backup_sequence(config, dev)
                        if not seq_cmds:
                            console.print(
                                "[red]Error: comprehensive backup sequence 'backup' not defined "
                                f"for {dev}[/red]"
                            )
                            return False

                        console.print(
                            f"[bold cyan]Creating comprehensive backup on {dev}[/bold cyan]"
                        )
                        transport_type = config.get_transport_type(dev)
                        platform_name = platform_ops.get_platform_name()
                        console.print(f"[yellow]Platform:[/yellow] {platform_name}")
                        console.print(f"[yellow]Transport:[/yellow] {transport_type}")

                        # Use platform-specific backup creation
                        backup_success = platform_ops.backup(
                            backup_sequence=seq_cmds,
                            download_files=None,  # Will handle downloads separately
                        )

                        if not backup_success:
                            console.print(
                                f"[red]Error: Comprehensive backup creation failed on {dev}[/red]"
                            )
                            return False

                        if download:
                            # Platform-specific download files for comprehensive backup
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
                                    {
                                        "remote_file": "nw-system-backup.backup",
                                        "local_path": str(config.general.backup_dir),
                                        "local_filename": (
                                            "{device}_{date}_system.backup"
                                        ),
                                        "delete_remote": delete_remote,
                                    },
                                ]
                            elif "cisco" in platform_name.lower():
                                # For Cisco devices, information is typically displayed, not saved to file
                                console.print(
                                    f"[yellow]Note: Cisco platform '{platform_name}' typically shows backup information rather than saving to files[/yellow]"
                                )
                                downloads = []

                            if downloads:
                                handle_downloads(
                                    session=session,
                                    device_name=dev,
                                    download_files=downloads,
                                    config=config,
                                )
                        return True
                except NetworkToolkitError as e:
                    console.print(f"[red]Error on {dev}: {e.message}[/red]")
                    if verbose and e.details:
                        console.print(f"[red]Details: {e.details}[/red]")
                    return False
                except Exception as e:  # pragma: no cover - unexpected
                    console.print(f"[red]Unexpected error on {dev}: {e}[/red]")
                    return False

            if is_device:
                ok = process_device(target_name)
                if not ok:
                    raise typer.Exit(1)
                console.print("[bold green]Comprehensive backup completed[/bold green]")
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
                console.print(
                    f"[red]Error: No devices found in group '{target_name}'[/red]",
                )
                raise typer.Exit(1)

            console.print(
                "[bold cyan]Starting comprehensive backups for group:[/bold cyan] "
                + target_name
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            console.print(
                (
                    f"[bold]Completed:[/bold] {total - failures}/{total} "
                    "successful comprehensive backups"
                ),
            )
            if failures:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and e.details:
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from e

    # Register the main backup command
    @app.command(rich_help_panel="Vendor-Specific Operations", name="backup")
    def backup(
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
                help=("Download created backup files after running the sequence"),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=("Delete remote backup files after successful download"),
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Create comprehensive device backup using vendor-specific commands."""
        _backup_impl(
            target_name,
            download=download,
            delete_remote=delete_remote,
            config_file=config_file,
            verbose=verbose,
        )
