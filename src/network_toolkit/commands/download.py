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
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Remote Operations")
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
                ctx.print_error(
                    f"'{target_name}' not found as device or group in configuration"
                )
                raise typer.Exit(1)

            if is_device:
                # Show summary
                transport_type = config.get_transport_type(target_name)
                ctx.print_info("File Download Details:")
                ctx.print_detail_line("Device", target_name)
                ctx.print_detail_line("Transport", transport_type)
                ctx.print_detail_line("Remote file", remote_file)
                ctx.print_detail_line("Local path", str(local_path))
                ctx.print_detail_line(
                    "Delete remote after download", "Yes" if delete_remote else "No"
                )
                ctx.print_detail_line(
                    "Verify download", "Yes" if verify_download else "No"
                )
                ctx.print_blank_line()

                with ctx.output_manager.status(
                    f"Downloading {remote_file} from {target_name}..."
                ):
                    with device_session(target_name, config) as session:
                        success = session.download_file(
                            remote_filename=remote_file,
                            local_path=local_path,
                            delete_remote=delete_remote,
                            verify_download=verify_download,
                        )

                if success:
                    ctx.print_success("Download successful!")
                    ctx.print_success(
                        f"File '{remote_file}' downloaded to '{local_path}'"
                    )
                else:
                    ctx.print_error("Download failed!")
                    raise typer.Exit(1)
                return

            # Group path
            try:
                members: list[str] = config.get_group_members(target_name)
            except Exception:
                group_obj = groups.get(target_name)
                members = group_obj.members if group_obj and group_obj.members else []

            if not members:
                ctx.print_error(f"No devices found in group '{target_name}'")
                raise typer.Exit(1)

            ctx.print_info("Group File Download Details:")
            ctx.print_detail_line("Group", target_name)
            ctx.print_detail_line("Devices", str(len(members)))
            ctx.print_detail_line("Remote file", remote_file)
            ctx.print_detail_line(
                "Base path",
                f"{local_path} (files saved under <base>/<device>/{remote_file})",
            )
            ctx.print_detail_line(
                "Delete remote after download", "Yes" if delete_remote else "No"
            )
            ctx.print_detail_line("Verify download", "Yes" if verify_download else "No")
            ctx.print_blank_line()

            successes = 0
            results: dict[str, bool] = {}

            for dev in members:
                dest = (local_path / dev / remote_file).resolve()
                with ctx.output_manager.status(
                    f"Downloading {remote_file} from {dev}..."
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
                                ctx.print_success(f"OK {dev}: downloaded to {dest}")
                            else:
                                ctx.print_error(f"FAIL {dev}: download failed")
                    except Exception as e:  # pragma: no cover - unexpected
                        results[dev] = False
                        ctx.print_error(f"FAIL {dev}: error during download: {e}")

            total = len(members)
            ctx.print_info("Group Download Results:")
            ctx.print_success(f"  Successful: {successes}/{total}")
            ctx.print_error(f"  Failed: {total - successes}/{total}")

            if successes < total:
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and getattr(e, "details", None):
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
