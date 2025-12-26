# SPDX-License-Identifier: MIT
"""`nw download` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.api.download import DownloadOptions, download_file
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets, select_named_target


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
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
        setup_logging("DEBUG" if verbose else "WARNING")

        # ACTION command - use global config theme
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=None,  # Use global config theme
        )

        try:
            config = load_config(config_file)

            target_kind = select_named_target(config, target_name)
            if target_kind not in {"device", "group"}:
                ctx.print_error(
                    f"'{target_name}' not found as device or group in configuration"
                )
                raise typer.Exit(1)

            if target_kind == "device":
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
            else:
                # Group summary
                members = resolve_named_targets(config, target_name).resolved_devices

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
                ctx.print_detail_line(
                    "Verify download", "Yes" if verify_download else "No"
                )
                ctx.print_blank_line()

            options = DownloadOptions(
                target=target_name,
                remote_file=remote_file,
                local_path=local_path,
                config=config,
                delete_remote=delete_remote,
                verify_download=verify_download,
                verbose=verbose,
            )

            with ctx.output_manager.status(
                f"Downloading {remote_file} from {target_name}..."
            ):
                result = download_file(options)

            if result.is_group:
                successes = result.totals.succeeded
                total = result.totals.total

                for res in result.device_results:
                    if res.success:
                        ctx.print_success(
                            f"OK {res.device}: downloaded to {res.local_path}"
                        )
                    else:
                        ctx.print_error(f"FAIL {res.device}: download failed")
                        if verbose and res.error:
                            ctx.print_error(f"  Error: {res.error}")

                ctx.print_info("Group Download Results:")
                ctx.print_success(f"  Successful: {successes}/{total}")
                ctx.print_error(f"  Failed: {total - successes}/{total}")

                if successes < total:
                    raise typer.Exit(1)
            elif result.totals.succeeded > 0:
                ctx.print_success("Download successful!")
                res = result.device_results[0]
                ctx.print_success(
                    f"File '{res.remote_file}' downloaded to '{res.local_path}'"
                )
            else:
                ctx.print_error("Download failed!")
                if result.device_results and result.device_results[0].error:
                    if verbose:
                        ctx.print_error(f"Error: {result.device_results[0].error}")
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
