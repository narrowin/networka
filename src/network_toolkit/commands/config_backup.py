# SPDX-License-Identifier: MIT
"""`nw config-backup` command implementation (device or group).

Platform-agnostic backup using vendor-specific implementations.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.config import DeviceConfig, NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import UnsupportedOperationError, get_platform_operations

MAX_LIST_PREVIEW = 10


def _resolve_backup_sequence(
    config: NetworkConfig, device_name: str
) -> list[str] | None:
    """Resolve the backup command sequence for a device.

    Preference order: device-specific sequence named 'backup_config' then
    global command sequence 'backup_config'.
    """
    # Device-specific override
    devices = config.devices or {}
    dev_cfg: DeviceConfig | None = devices.get(device_name)
    if dev_cfg and dev_cfg.command_sequences:
        seq = dev_cfg.command_sequences.get("backup_config")
        if seq:
            return list(seq)

    # Global sequence
    global_seqs = config.global_command_sequences or {}
    if "backup_config" in global_seqs:
        return list(global_seqs["backup_config"].commands)

    return None


def register(app: typer.Typer) -> None:
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
                    "Download created backup/export files after running the sequence"
                ),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=("Delete remote backup/export files after successful download"),
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Create device backup and export; optionally download artifacts.

        Uses platform-specific implementations to handle vendor differences
        in backup procedures.
        """
        # Create command context with proper styling (respects global config theme)
        # Create command context with proper styling
        ctx = CommandContext(
            output_mode=None,  # Use global config theme
            verbose=verbose,
            config_file=config_file,
        )

        # Use themed console for all output
        console = ctx.console

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

                        # Resolve backup sequence (device-specific or global)
                        seq_cmds = _resolve_backup_sequence(config, dev)
                        if not seq_cmds:
                            console.print(
                                "[red]Error: backup sequence 'backup_config' not defined "
                                f"for {dev}[/red]"
                            )
                            return False

                        console.print(
                            f"[bold cyan]Creating configuration backup on {dev}[/bold cyan]"
                        )
                        transport_type = config.get_transport_type(dev)
                        platform_name = platform_ops.get_platform_name()
                        ctx.print_info(f"Platform: {platform_name}")
                        ctx.print_info(f"Transport: {transport_type}")

                        # Use platform-specific backup creation
                        backup_success = platform_ops.create_backup(
                            backup_sequence=seq_cmds,
                            download_files=None,  # Will handle downloads separately
                        )

                        if not backup_success:
                            console.print(
                                f"[red]Error: Backup creation failed on {dev}[/red]"
                            )
                            return False

                        if download:
                            downloads: list[dict[str, Any]] = [
                                {
                                    "remote_file": "nw-backup.backup",
                                    "local_path": str(config.general.backup_dir),
                                    "local_filename": ("{device}_{date}_nw.backup"),
                                    "delete_remote": delete_remote,
                                },
                                {
                                    "remote_file": "nw-export.rsc",
                                    "local_path": str(config.general.backup_dir),
                                    "local_filename": ("{device}_{date}_nw-export.rsc"),
                                    "delete_remote": delete_remote,
                                },
                            ]
                            handle_downloads(
                                session=session,
                                device_name=dev,
                                download_files=downloads,
                                config=config,
                            )
                        return True
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
                console.print("[bold green]Backup completed[/bold green]")
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
                "[bold cyan]Starting backups for group:[/bold cyan] " + target_name
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            console.print(
                (
                    f"[bold]Completed:[/bold] {total - failures}/{total} "
                    "successful backups"
                ),
            )
            if failures:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.handle_error(e)
        except Exception as e:  # pragma: no cover - unexpected
            ctx.handle_error(e)

    # Register the default hyphenated command
    @app.command(rich_help_panel="Executing Operations", name="config-backup")
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
                    "Download created backup/export files after running the sequence"
                ),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=("Delete remote backup/export files after successful download"),
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        _config_backup_impl(
            target_name,
            download=download,
            delete_remote=delete_remote,
            config_file=config_file,
            verbose=verbose,
        )

    # Register a friendly alias used by tests
    @app.command(rich_help_panel="Executing Operations", name="backup")
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
                help=(
                    "Download created backup/export files after running the sequence"
                ),
            ),
        ] = True,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help=("Delete remote backup/export files after successful download"),
            ),
        ] = False,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        _config_backup_impl(
            target_name,
            download=download,
            delete_remote=delete_remote,
            config_file=config_file,
            verbose=verbose,
        )
