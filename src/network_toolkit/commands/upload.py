# SPDX-License-Identifier: MIT
"""`nw upload` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.api.upload import UploadOptions, upload_file
from network_toolkit.common.command import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.inventory.resolve import resolve_named_targets, select_named_target

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def upload(  # pyright: ignore[reportUnusedFunction]
        target_name: Annotated[
            str,
            typer.Argument(
                help="Device or group name from configuration",
                metavar="<device|group>",
            ),
        ],
        local_file: Annotated[
            Path, typer.Argument(help="Path to local file to upload")
        ],
        *,
        remote_filename: Annotated[
            str | None,
            typer.Option(
                "--remote-name",
                "-r",
                help="Remote filename (default: same as local)",
            ),
        ] = None,
        verify: Annotated[
            bool,
            typer.Option(
                "--verify/--no-verify",
                help="Verify upload by checking file exists",
            ),
        ] = True,
        checksum_verify: Annotated[
            bool,
            typer.Option(
                "--checksum-verify/--no-checksum-verify",
                help=(
                    "Verify file integrity using checksums (uses config default if not"
                    " specified)"
                ),
            ),
        ] = False,
        max_concurrent: Annotated[
            int,
            typer.Option(
                "--max-concurrent",
                "-j",
                help="Maximum concurrent uploads when target is a group",
            ),
        ] = 5,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose output")
        ] = False,
    ) -> None:
        """Upload a file to a device or to all devices in a group."""
        setup_logging("DEBUG" if verbose else "WARNING")

        # ACTION command - use global config theme
        ctx = CommandContext(
            config_file=config_file,
            verbose=verbose,
            output_mode=None,  # Use global config theme
        )

        output = ctx.output

        try:
            config = load_config(config_file)

            if not local_file.exists():
                ctx.print_error(f"Local file not found: {local_file}")
                raise typer.Exit(1)
            if not local_file.is_file():
                ctx.print_error(f"Path is not a file: {local_file}")
                raise typer.Exit(1)

            file_size = local_file.stat().st_size
            remote_name = remote_filename or local_file.name

            devices = config.devices or {}
            groups = config.device_groups or {}
            target_kind = select_named_target(config, target_name)
            if target_kind not in {"device", "group"}:
                ctx.print_error(
                    f"'{target_name}' not found as device or group in configuration"
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

            if target_kind == "device":
                transport_type = config.get_transport_type(target_name)
                ctx.print_info("File Upload Details:")
                ctx.print_info(f"  Device: {target_name}")
                ctx.print_info(f"  Transport: {transport_type}")
                ctx.print_info(f"  Local file: {local_file}")
                ctx.print_info(f"  Remote name: {remote_name}")
                ctx.print_info(f"  File size: {file_size:,} bytes")
                ctx.print_info(f"  Verify upload: {'Yes' if verify else 'No'}")
                ctx.print_info(
                    f"  Checksum verify: {'Yes' if checksum_verify else 'No'}"
                )
                output.print_blank_line()
            else:
                # Group path
                members = resolve_named_targets(config, target_name).resolved_devices

                if not members:
                    ctx.print_error(f"No devices found in group '{target_name}'")
                    raise typer.Exit(1)

                ctx.print_info("Group File Upload Details:")
                ctx.print_info(f"  Group: {target_name}")
                ctx.print_info(f"  Devices: {len(members)} ({', '.join(members)})")
                ctx.print_info(f"  Local file: {local_file}")
                ctx.print_info(f"  Remote name: {remote_name}")
                ctx.print_info(f"  File size: {file_size:,} bytes")
                ctx.print_info(f"  Max concurrent: {max_concurrent}")
                ctx.print_info(f"  Verify upload: {'Yes' if verify else 'No'}")
                ctx.print_info(
                    f"  Checksum verify: {'Yes' if checksum_verify else 'No'}"
                )
                output.print_blank_line()

            options = UploadOptions(
                target=target_name,
                local_file=local_file,
                config=config,
                remote_filename=remote_filename,
                verify=verify,
                checksum_verify=checksum_verify,
                max_concurrent=max_concurrent,
                verbose=verbose,
            )

            with output.status(f"Uploading {local_file.name} to {target_name}..."):
                result = upload_file(options)

            if result.is_group:
                successful = result.totals.succeeded
                total = result.totals.total

                ctx.print_info("Group Upload Results:")
                ctx.print_success(f"  Successful: {successful}/{total}")
                if total - successful > 0:
                    ctx.print_error(f"  Failed: {total - successful}/{total}")
                output.print_blank_line()

                ctx.print_info("Per-Device Results:")
                for res in result.device_results:
                    if res.success:
                        ctx.print_success(f"  {res.device}")
                    else:
                        ctx.print_error(f"  {res.device}")

                if successful < total:
                    ctx.print_warning("Warning:")
                    ctx.print_warning(f"{total - successful} device(s) failed")
                    raise typer.Exit(1)
                else:
                    ctx.print_success("All uploads completed successfully!")
            elif result.totals.succeeded > 0:
                ctx.print_success("Upload successful")
                res = result.device_results[0]
                ctx.print_success(
                    f"File '{local_file.name}' uploaded to {target_name} as '{res.remote_path}'"
                )
            else:
                ctx.print_error("Upload failed")
                raise typer.Exit(1)

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except FileNotFoundError as e:  # pragma: no cover
            ctx.print_error(f"File not found: {e}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
