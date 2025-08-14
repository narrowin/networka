# SPDX-License-Identifier: MIT
"""`nw firmware-upgrade` command implementation (device or group).

Uploads a RouterOS .npk package and triggers reboot to apply it.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Executing Operations")
    def firmware_upgrade(  # pyright: ignore[reportUnusedFunction]
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        firmware_file: Annotated[
            Path,
            typer.Argument(help="Path to local RouterOS firmware package (.npk)"),
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
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Upload firmware package and reboot device to apply it.

        Uses DeviceSession.upload_firmware_and_reboot to ensure proper handling of
        confirmation prompts and connection drops during reboot.
        """
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            if not firmware_file.exists() or not firmware_file.is_file():
                console.print(
                    f"[red]Error: Firmware file not found: {firmware_file}[/red]"
                )
                raise typer.Exit(1)

            if firmware_file.suffix.lower() != ".npk":
                console.print(
                    f"[red]Error: Firmware file must be a .npk: {firmware_file}[/red]"
                )
                raise typer.Exit(1)

            config = load_config(config_file)

            module = import_module("network_toolkit.cli")
            device_session = cast(Any, module).DeviceSession

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
                        if precheck_sequence and not skip_precheck:
                            console.print(
                                "[cyan]Running precheck sequence '"
                                + precheck_sequence
                                + f"' on {dev}[/cyan]"
                            )
                            # Run sequence via CLI sequence resolver logic
                            # Keep simple: resolve from global or device sequences
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
                            "[bold yellow]Uploading firmware to "
                            f"{dev} and rebooting...[/bold yellow]"
                        )
                        transport_type = config.get_transport_type(dev)
                        console.print(f"[yellow]Transport:[/yellow] {transport_type}")
                        ok = session.upload_firmware_and_reboot(
                            local_firmware_path=firmware_file
                        )
                        if ok:
                            console.print(
                                "[green]OK Firmware upload initiated; device rebooting: "
                                f"{dev}[/green]"
                            )
                            return True
                        console.print(
                            f"[red]FAIL Firmware upgrade failed to start on {dev}[/red]"
                        )
                        return False
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
                    f"[red]Error: No devices found in group '{target_name}'[/red]",
                )
                raise typer.Exit(1)

            console.print(
                "[bold cyan]Starting firmware upgrade for group '"
                + target_name
                + "' ("
                + str(len(members))
                + ") devices)[/bold cyan]"
            )
            failures = 0
            for dev in members:
                ok = process_device(dev)
                failures += 0 if ok else 1

            total = len(members)
            console.print(
                f"[bold]Completed:[/bold] {total - failures}/{total} initiated"
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
