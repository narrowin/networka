# SPDX-License-Identifier: MIT
"""`netkit download` command implementation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Executing Operations")
    def download(  # pyright: ignore[reportUnusedFunction]
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        remote_file: Annotated[
            str, typer.Argument(help="Remote filename on the device (e.g. export.rsc)")
        ],
        local_path: Annotated[
            Path,
            typer.Argument(
                help=(
                    "Destination path. For groups, treated as a directory and files "
                    "are saved under <local_path>/<device>/<remote_file>"
                )
            ),
        ],
        *,
        delete_remote: Annotated[
            bool,
            typer.Option(
                "--delete-remote/--keep-remote",
                help="Delete remote file after successful download",
            ),
        ] = False,
        verify_download: Annotated[
            bool,
            typer.Option(
                "--verify/--no-verify",
                help="Verify download by comparing file sizes",
            ),
        ] = True,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = Path("devices.yml"),
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Download a file from a device or all devices in a group."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            config = load_config(config_file)

            # Resolve DeviceSession from cli to preserve test patching path
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
                raise typer.Exit(1)

            if is_device:
                # Show summary
                transport_type = config.get_transport_type(target_name)
                console.print("[bold cyan]File Download Details:[/bold cyan]")
                console.print(f"  [bold]Device:[/bold] {target_name}")
                console.print(
                    f"  [bold]Transport:[/bold] [yellow]{transport_type}[/yellow]"
                )
                console.print(f"  [bold]Remote file:[/bold] {remote_file}")
                console.print(f"  [bold]Local path:[/bold] {local_path}")
                console.print(
                    "  [bold]Delete remote after download:[/bold] "
                    + ("Yes" if delete_remote else "No")
                )
                console.print(
                    "  [bold]Verify download:[/bold] "
                    + ("Yes" if verify_download else "No")
                )
                console.print()

                with console.status(
                    f"[bold green]Downloading {remote_file} from {target_name}..."
                ):
                    with device_session(target_name, config) as session:
                        success = session.download_file(
                            remote_filename=remote_file,
                            local_path=local_path,
                            delete_remote=delete_remote,
                            verify_download=verify_download,
                        )

                if success:
                    console.print("[bold green]✓ Download successful![/bold green]")
                    console.print(
                        f"[green]File '{remote_file}' downloaded to "
                        f"'{local_path}'[/green]"
                    )
                else:
                    console.print("[bold red]✗ Download failed![/bold red]")
                    raise typer.Exit(1)
                return

            # Group path
            try:
                members: list[str] = config.get_group_members(target_name)
            except Exception:
                group_obj = groups.get(target_name)
                members = group_obj.members if group_obj and group_obj.members else []

            if not members:
                console.print(
                    f"[red]Error: No devices found in group '{target_name}'[/red]",
                )
                raise typer.Exit(1)

            console.print("[bold cyan]Group File Download Details:[/bold cyan]")
            console.print(f"  [bold]Group:[/bold] {target_name}")
            console.print(f"  [bold]Devices:[/bold] {len(members)}")
            console.print(f"  [bold]Remote file:[/bold] {remote_file}")
            console.print(
                "  [bold]Base path:[/bold] "
                f"{local_path} (files saved under <base>/<device>/{remote_file})"
            )
            console.print(
                "  [bold]Delete remote after download:[/bold] "
                + ("Yes" if delete_remote else "No")
            )
            console.print(
                "  [bold]Verify download:[/bold] "
                + ("Yes" if verify_download else "No")
            )
            console.print()

            successes = 0
            results: dict[str, bool] = {}

            for dev in members:
                dest = (local_path / dev / remote_file).resolve()
                with console.status(
                    f"[bold green]Downloading {remote_file} from {dev}..."
                ):
                    try:
                        with device_session(dev, config) as session:
                            ok = session.download_file(
                                remote_filename=remote_file,
                                local_path=dest,
                                delete_remote=delete_remote,
                                verify_download=verify_download,
                            )
                            results[dev] = ok
                            if ok:
                                successes += 1
                                console.print(
                                    f"[green]✓ {dev}: downloaded to {dest}[/green]"
                                )
                            else:
                                console.print(f"[red]✗ {dev}: download failed[/red]")
                    except Exception as e:  # pragma: no cover - unexpected
                        results[dev] = False
                        console.print(f"[red]✗ {dev}: error during download: {e}[/red]")

            total = len(members)
            console.print("[bold cyan]Group Download Results:[/bold cyan]")
            console.print(f"  [bold green]Successful:[/bold green] {successes}/{total}")
            console.print(f"  [bold red]Failed:[/bold red] {total - successes}/{total}")

            if successes < total:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            console.print(f"[red]Error: {e.message}[/red]")
            if verbose and getattr(e, "details", None):
                console.print(f"[red]Details: {e.details}[/red]")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            console.print(f"[red]Unexpected error: {e}[/red]")
            raise typer.Exit(1) from None
