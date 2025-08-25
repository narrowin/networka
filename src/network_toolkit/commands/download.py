# SPDX-License-Identifier: MIT
"""`nw download` command implementation."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.styles import StyleManager, StyleName
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
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Download a file from a device or all devices in a group."""
        setup_logging("DEBUG" if verbose else "INFO")

        # ACTION command - use global config theme
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=None,  # Use global config theme
        )

        # Setup style manager for consistent theming
        style_manager = StyleManager(OutputMode.DEFAULT)
        console = style_manager.console

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
                    style_manager.format_message(
                        f"Error: '{target_name}' not found as device or group in configuration",
                        StyleName.ERROR,
                    )
                )
                raise typer.Exit(1)

            if is_device:
                # Show summary
                transport_type = config.get_transport_type(target_name)
                console.print(
                    style_manager.format_message(
                        "File Download Details:", StyleName.INFO
                    )
                )
                console.print(
                    style_manager.format_message(
                        f"  Device: {target_name}", StyleName.BOLD
                    )
                )
                console.print(
                    style_manager.format_message(
                        f"  Transport: {transport_type}", StyleName.BOLD
                    )
                )
                console.print(
                    style_manager.format_message(
                        f"  Remote file: {remote_file}", StyleName.BOLD
                    )
                )
                console.print(
                    style_manager.format_message(
                        f"  Local path: {local_path}", StyleName.BOLD
                    )
                )
                console.print(
                    style_manager.format_message(
                        "  Delete remote after download: "
                        + ("Yes" if delete_remote else "No"),
                        StyleName.BOLD,
                    )
                )
                console.print(
                    style_manager.format_message(
                        "  Verify download: " + ("Yes" if verify_download else "No"),
                        StyleName.BOLD,
                    )
                )
                console.print()

                with console.status(f"Downloading {remote_file} from {target_name}..."):
                    with device_session(target_name, config) as session:
                        success = session.download_file(
                            remote_filename=remote_file,
                            local_path=local_path,
                            delete_remote=delete_remote,
                            verify_download=verify_download,
                        )

                if success:
                    console.print(
                        style_manager.format_message(
                            "OK Download successful!", StyleName.SUCCESS
                        )
                    )
                    ctx.print_success(
                        f"File '{remote_file}' downloaded to '{local_path}'"
                    )
                else:
                    console.print(
                        style_manager.format_message(
                            "FAIL Download failed!", StyleName.ERROR
                        )
                    )
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
                    style_manager.format_message(
                        f"Error: No devices found in group '{target_name}'",
                        StyleName.ERROR,
                    )
                )
                raise typer.Exit(1)

            console.print(
                style_manager.format_message(
                    "Group File Download Details:", StyleName.INFO
                )
            )
            console.print(
                style_manager.format_message(f"  Group: {target_name}", StyleName.BOLD)
            )
            console.print(
                style_manager.format_message(
                    f"  Devices: {len(members)}", StyleName.BOLD
                )
            )
            console.print(
                style_manager.format_message(
                    f"  Remote file: {remote_file}", StyleName.BOLD
                )
            )
            console.print(
                style_manager.format_message(
                    f"  Base path: {local_path} (files saved under <base>/<device>/{remote_file})",
                    StyleName.BOLD,
                )
            )
            console.print(
                style_manager.format_message(
                    "  Delete remote after download: "
                    + ("Yes" if delete_remote else "No"),
                    StyleName.BOLD,
                )
            )
            console.print(
                style_manager.format_message(
                    "  Verify download: " + ("Yes" if verify_download else "No"),
                    StyleName.BOLD,
                )
            )
            console.print()

            successes = 0
            results: dict[str, bool] = {}

            for dev in members:
                dest = (local_path / dev / remote_file).resolve()
                with console.status(f"Downloading {remote_file} from {dev}..."):
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
                                ctx.print_success(f"OK {dev}: downloaded to {dest}")
                            else:
                                ctx.print_error(f"FAIL {dev}: download failed")
                    except Exception as e:  # pragma: no cover - unexpected
                        results[dev] = False
                        console.print(
                            style_manager.format_message(
                                f"FAIL {dev}: error during download: {e}",
                                StyleName.ERROR,
                            )
                        )

            total = len(members)
            console.print(
                style_manager.format_message("Group Download Results:", StyleName.INFO)
            )
            console.print(
                style_manager.format_message(
                    f"  Successful: {successes}/{total}", StyleName.SUCCESS
                )
            )
            console.print(
                style_manager.format_message(
                    f"  Failed: {total - successes}/{total}", StyleName.ERROR
                )
            )

            if successes < total:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and getattr(e, "details", None):
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
