# SPDX-License-Identifier: MIT
"""`netkit config-backup` command implementation (device or group).

Runs the configured backup command sequence and optionally downloads artifacts.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import DeviceConfig, NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError

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
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Create device backup and export; optionally download artifacts.

        Runs the 'backup_config' command sequence and downloads files to
        the configured backup_dir unless disabled.
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
                console.print(f"[yellow]Transport:[/yellow] {transport_type}")

                try:
                    with device_session(dev, config) as session:
                        for cmd in seq_cmds:
                            console.print(f"[cyan]Running:[/cyan] {cmd}")
                            session.execute_command(cmd)

                        if download:
                            downloads: list[dict[str, Any]] = [
                                {
                                    "remote_file": "netkit-backup.backup",
                                    "local_path": str(config.general.backup_dir),
                                    "local_filename": ("{device}_{date}_netkit.backup"),
                                    "delete_remote": delete_remote,
                                },
                                {
                                    "remote_file": "netkit-export.rsc",
                                    "local_path": str(config.general.backup_dir),
                                    "local_filename": (
                                        "{device}_{date}_netkit-export.rsc"
                                    ),
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
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and e.details:
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None

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
        ] = Path("devices.yml"),
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
        ] = Path("devices.yml"),
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
