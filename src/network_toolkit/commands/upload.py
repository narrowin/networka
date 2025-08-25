# SPDX-License-Identifier: MIT
"""`nw upload` command implementation."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

MAX_LIST_PREVIEW = 10


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Executing Operations")
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
        setup_logging("DEBUG" if verbose else "INFO")

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

            # Late import to allow tests to patch `network_toolkit.cli.DeviceSession`
            from network_toolkit.cli import DeviceSession

            # Use DeviceSession from CLI module so tests can patch that symbol
            device_session = DeviceSession

            # Determine if target is a device or a group
            devices = config.devices or {}
            groups = config.device_groups or {}
            is_device = target_name in devices
            is_group = target_name in groups

            if not (is_device or is_group):
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

            if is_device:
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

                with output.status(f"Uploading {local_file.name} to {target_name}..."):
                    with device_session(target_name, config) as session:
                        success = session.upload_file(
                            local_path=local_file,
                            remote_filename=remote_filename,
                            verify_upload=verify,
                            verify_checksum=checksum_verify,
                        )

                if success:
                    ctx.print_success("Upload successful")
                    ctx.print_success(
                        f"File '{local_file.name}' uploaded to {target_name} as '{remote_name}'"
                    )
                else:
                    ctx.print_error("Upload failed")
                    raise typer.Exit(1)
                return

            # Group path
            members: list[str] = []
            try:
                members = config.get_group_members(target_name)
            except Exception:
                # Fallback manual resolution (shouldn't happen)
                group_obj = groups.get(target_name)
                if group_obj and getattr(group_obj, "members", None):
                    members = group_obj.members or []

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
            ctx.print_info(f"  Checksum verify: {'Yes' if checksum_verify else 'No'}")
            output.print_blank_line()

            with output.status(
                f"Uploading {local_file.name} to {len(members)} devices...",
            ):
                results = device_session.upload_file_to_devices(
                    device_names=members,
                    config=config,
                    local_path=local_file,
                    remote_filename=remote_filename,
                    verify_upload=verify,
                    verify_checksum=checksum_verify,
                    max_concurrent=max_concurrent,
                )

            successful = sum(results.values())
            total = len(members)

            ctx.print_info("Group Upload Results:")
            ctx.print_success(f"  Successful: {successful}/{total}")
            if total - successful > 0:
                ctx.print_error(f"  Failed: {total - successful}/{total}")
            output.print_blank_line()

            ctx.print_info("Per-Device Results:")
            for dev in members:
                ok = results.get(dev, False)
                if ok:
                    ctx.print_success(f"  {dev}")
                else:
                    ctx.print_error(f"  {dev}")

            if successful < total:
                ctx.print_warning("Warning:")
                ctx.print_warning(f"{total - successful} device(s) failed")
                raise typer.Exit(1)
            else:
                ctx.print_success("All uploads completed successfully!")

        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except FileNotFoundError as e:  # pragma: no cover
            ctx.print_error(f"File not found: {e}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
