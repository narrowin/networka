"""Unified backup command for network_toolkit."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from importlib import import_module
from pathlib import Path
from typing import Annotated, Any, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.platforms import (
    UnsupportedOperationError,
    check_operation_support,
    get_platform_operations,
)
from network_toolkit.sequence_manager import SequenceManager

MAX_LIST_PREVIEW = 10

# Create a sub-app for backup commands
backup_app = typer.Typer(
    name="backup",
    help="Backup operations for network devices",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


@backup_app.command("config")
def config_backup(
    target_name: Annotated[str, typer.Argument(help="Device or group name")],
    download: Annotated[
        bool,
        typer.Option(
            "--download/--no-download",
            help="Download created backup/export files after running the sequence",
        ),
    ] = True,
    delete_remote: Annotated[
        bool,
        typer.Option(
            "--delete-remote/--keep-remote",
            help="Delete remote backup/export files after successful download",
        ),
    ] = False,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Configuration file path")
    ] = DEFAULT_CONFIG_PATH,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Backup device configuration.

    Performs a configuration backup for the specified device or group.
    """
    setup_logging("DEBUG" if verbose else "WARNING")
    ctx = CommandContext(
        output_mode=None,  # Use global config theme
        verbose=verbose,
        config_file=config_file,
    )

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
            ctx.output_manager.print_error(
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

        def resolve_backup_sequence(
            config: NetworkConfig, device_name: str
        ) -> list[str]:
            """Resolve the backup sequence for a device using SequenceManager."""
            seq_name = "backup_config"
            sm = SequenceManager(config)
            sequence_commands = sm.resolve(seq_name, device_name)
            return sequence_commands or []

        # Create single timestamp for entire backup run
        run_timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        backup_dirs: list[Path] = []  # Track all backup directories

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
                    seq_cmds = resolve_backup_sequence(config, dev)
                    if not seq_cmds:
                        ctx.print_error(
                            f"backup sequence 'backup_config' not defined for {dev}"
                        )
                        return False

                    ctx.print_operation_header("Configuration Backup", dev, "device")
                    transport_type = config.get_transport_type(dev)
                    platform_name = platform_ops.get_platform_name()
                    ctx.print_info(f"Platform: {platform_name}")
                    ctx.print_info(f"Transport: {transport_type}")

                    # Use platform-specific backup creation
                    backup_result = platform_ops.create_backup(
                        backup_sequence=seq_cmds,
                        download_files=None,
                    )

                    if not backup_result.success:
                        ctx.print_error(f"Backup creation failed on {dev}")
                        for error in backup_result.errors:
                            ctx.print_error(f"  {error}")
                        return False

                    # Create backup directory using shared timestamp
                    backup_dir = (
                        Path(config.general.backup_dir) / f"{dev}_{run_timestamp}"
                    )
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_dirs.append(backup_dir)
                    ctx.print_info(f"Saving backup to: {backup_dir}")

                    # Save text outputs
                    for filename, content in backup_result.text_outputs.items():
                        output_file = backup_dir / filename
                        output_file.write_text(content, encoding="utf-8")
                        ctx.print_info(f"  Saved: {filename}")

                    # Download platform-specified files if requested
                    if download and backup_result.files_to_download:
                        for file_spec in backup_result.files_to_download:
                            download_spec = {
                                "remote_file": file_spec["source"],
                                "local_path": str(backup_dir),
                                "local_filename": file_spec["destination"],
                                "delete_remote": delete_remote,
                            }
                            handle_downloads(
                                session=session,
                                device_name=dev,
                                download_files=[download_spec],
                                config=config,
                            )

                    # Generate manifest
                    manifest = {
                        "device": dev,
                        "timestamp": run_timestamp,
                        "platform": platform_name,
                        "transport": transport_type,
                        "text_outputs": list(backup_result.text_outputs.keys()),
                        "downloaded_files": (
                            [f["destination"] for f in backup_result.files_to_download]
                            if download
                            else []
                        ),
                    }
                    manifest_file = backup_dir / "manifest.json"
                    manifest_file.write_text(
                        json.dumps(manifest, indent=2), encoding="utf-8"
                    )
                    ctx.print_info("  Saved: manifest.json")

                    return True
            except NetworkToolkitError as e:
                ctx.print_error(f"Error on {dev}: {e.message}")
                if verbose and e.details:
                    ctx.print_error(f"Details: {e.details}")
                return False
            except Exception as e:  # pragma: no cover
                ctx.print_error(f"Unexpected error on {dev}: {e}")
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            ctx.print_operation_complete("Backup", success=True)

            # Print backup summary
            if backup_dirs:
                ctx.output_manager.print_text("")  # Blank line
                ctx.print_success("Backup Summary:")
                ctx.print_info(f"  Timestamp: {run_timestamp}")
                ctx.print_info(f"  Location: {backup_dirs[0]}")
                file_count = len(list(backup_dirs[0].glob("*")))
                ctx.print_info(f"  Files: {file_count} files saved")
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
            ctx.print_error(f"No devices found in group '{target_name}'")
            raise typer.Exit(1)

        ctx.print_operation_header("Backup", target_name, "group")
        failures = 0
        for dev in members:
            ok = process_device(dev)
            failures += 0 if ok else 1

        total = len(members)
        ctx.print_info(f"Completed: {total - failures}/{total} successful backups")

        # Print backup summary for group
        if backup_dirs:
            ctx.output_manager.print_text("")  # Blank line
            ctx.print_success("Backup Summary:")
            ctx.print_info(f"  Timestamp: {run_timestamp}")
            ctx.print_info(f"  Devices backed up: {len(backup_dirs)}")
            for backup_dir in backup_dirs:
                file_count = len(list(backup_dir.glob("*")))
                ctx.print_info(f"    {backup_dir.name}: {file_count} files")
            ctx.print_info(f"  Base directory: {backup_dirs[0].parent}")

        if failures:
            raise typer.Exit(1)

    except NetworkToolkitError as e:
        ctx.handle_error(e)
    except Exception as e:  # pragma: no cover
        ctx.handle_error(e)


@backup_app.command("comprehensive")
def comprehensive_backup(
    target_name: Annotated[str, typer.Argument(help="Device or group name")],
    download: Annotated[
        bool,
        typer.Option(
            "--download/--no-download",
            help="Download created backup/export files after running the sequence",
        ),
    ] = True,
    delete_remote: Annotated[
        bool,
        typer.Option(
            "--delete-remote/--keep-remote",
            help="Delete remote backup/export files after successful download",
        ),
    ] = False,
    config_file: Annotated[
        Path, typer.Option("--config", "-c", help="Configuration file path")
    ] = DEFAULT_CONFIG_PATH,
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
) -> None:
    """Perform comprehensive backup including vendor-specific data.

    Performs a comprehensive backup for the specified device or group,
    including vendor-specific configuration and operational data.
    """
    setup_logging("DEBUG" if verbose else "WARNING")
    ctx = CommandContext(
        config_file=config_file,
        verbose=verbose,
        output_mode=None,  # Use global config theme
    )

    try:
        config = load_config(config_file)

        module = import_module("network_toolkit.cli")
        device_session = cast(Any, module).DeviceSession
        handle_downloads = cast(Any, module)._handle_file_downloads

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

        def resolve_comprehensive_backup_sequence(
            config: NetworkConfig, device_name: str
        ) -> list[str]:
            """Resolve the comprehensive backup command sequence for a device."""
            devices = config.devices or {}
            dev_cfg = devices.get(device_name)

            # Device-specific override
            if dev_cfg and dev_cfg.command_sequences:
                seq = dev_cfg.command_sequences.get("backup")
                if seq:
                    return list(seq)

            return []

        # Create single timestamp for entire backup run
        run_timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        backup_dirs: list[Path] = []  # Track all backup directories

        def process_device(dev: str) -> bool:
            try:
                with device_session(dev, config) as session:
                    try:
                        platform_ops = get_platform_operations(session)
                    except UnsupportedOperationError as e:
                        ctx.print_error(f"Error on {dev}: {e}")
                        return False

                    seq_cmds = resolve_comprehensive_backup_sequence(config, dev)
                    if not seq_cmds:
                        ctx.print_error(
                            f"backup sequence 'backup' not defined for {dev}"
                        )
                        return False

                    ctx.print_operation_header("Comprehensive Backup", dev, "device")
                    transport_type = config.get_transport_type(dev)
                    platform_name = platform_ops.get_platform_name()
                    ctx.print_info(f"Platform: {platform_name}")
                    ctx.print_info(f"Transport: {transport_type}")

                    backup_result = platform_ops.backup(
                        backup_sequence=seq_cmds,
                        download_files=None,
                    )

                    if not backup_result.success:
                        ctx.print_error(
                            f"Comprehensive backup creation failed on {dev}"
                        )
                        for error in backup_result.errors:
                            ctx.print_error(f"  {error}")
                        return False

                    # Create backup directory using shared timestamp
                    backup_dir = (
                        Path(config.general.backup_dir) / f"{dev}_{run_timestamp}"
                    )
                    backup_dir.mkdir(parents=True, exist_ok=True)
                    backup_dirs.append(backup_dir)
                    ctx.print_info(f"Saving comprehensive backup to: {backup_dir}")

                    # Save text outputs
                    for filename, content in backup_result.text_outputs.items():
                        output_file = backup_dir / filename
                        output_file.write_text(content, encoding="utf-8")
                        ctx.print_info(f"  Saved: {filename}")

                    # Download platform-specified files if requested
                    if download and backup_result.files_to_download:
                        for file_spec in backup_result.files_to_download:
                            download_spec = {
                                "remote_file": file_spec["source"],
                                "local_path": str(backup_dir),
                                "local_filename": file_spec["destination"],
                                "delete_remote": delete_remote,
                            }
                            handle_downloads(
                                session=session,
                                device_name=dev,
                                download_files=[download_spec],
                                config=config,
                            )

                    # Generate manifest
                    manifest = {
                        "device": dev,
                        "timestamp": run_timestamp,
                        "platform": platform_name,
                        "transport": transport_type,
                        "backup_type": "comprehensive",
                        "text_outputs": list(backup_result.text_outputs.keys()),
                        "downloaded_files": (
                            [f["destination"] for f in backup_result.files_to_download]
                            if download
                            else []
                        ),
                    }
                    manifest_file = backup_dir / "manifest.json"
                    manifest_file.write_text(
                        json.dumps(manifest, indent=2), encoding="utf-8"
                    )
                    ctx.print_info("  Saved: manifest.json")

                    return True
            except NetworkToolkitError as e:
                ctx.print_error(f"Error on {dev}: {e.message}")
                if verbose and e.details:
                    ctx.print_error(f"Details: {e.details}")
                return False
            except Exception as e:  # pragma: no cover
                ctx.print_error(f"Unexpected error on {dev}: {e}")
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            ctx.print_operation_complete("Comprehensive Backup", success=True)

            # Print backup summary
            if backup_dirs:
                ctx.output_manager.print_text("")  # Blank line
                ctx.print_success("Backup Summary:")
                ctx.print_info(f"  Timestamp: {run_timestamp}")
                ctx.print_info(f"  Location: {backup_dirs[0]}")
                file_count = len(list(backup_dirs[0].glob("*")))
                ctx.print_info(f"  Files: {file_count} files saved")
            return

        # Group processing
        members: list[str] = []
        try:
            members = config.get_group_members(target_name)
        except Exception:
            grp = groups.get(target_name)
            if grp and getattr(grp, "members", None):
                members = grp.members or []

        if not members:
            ctx.print_error(f"No devices found in group '{target_name}'")
            raise typer.Exit(1)

        ctx.print_operation_header("Comprehensive Backup", target_name, "group")
        failures = 0
        for dev in members:
            ok = process_device(dev)
            failures += 0 if ok else 1

        total = len(members)
        ctx.print_info(f"Completed: {total - failures}/{total} successful backups")

        # Print backup summary for group
        if backup_dirs:
            ctx.output_manager.print_text("")  # Blank line
            ctx.print_success("Backup Summary:")
            ctx.print_info(f"  Timestamp: {run_timestamp}")
            ctx.print_info(f"  Devices backed up: {len(backup_dirs)}")
            for backup_dir in backup_dirs:
                file_count = len(list(backup_dir.glob("*")))
                ctx.print_info(f"    {backup_dir.name}: {file_count} files")
            ctx.print_info(f"  Base directory: {backup_dirs[0].parent}")
        if failures:
            raise typer.Exit(1)

    except NetworkToolkitError as e:
        ctx.handle_error(e)
    except Exception as e:  # pragma: no cover
        ctx.handle_error(e)


@backup_app.command("vendors")
def show_vendors() -> None:
    """Show which vendors support backup operations.

    Lists all supported vendors and their backup operation capabilities.
    """
    from network_toolkit.platforms.factory import get_supported_platforms

    platforms = get_supported_platforms()

    ctx = CommandContext()
    ctx.print_info("Vendor backup operation support:")

    operations = [
        ("config_backup", "Configuration Backup"),
        ("create_backup", "Comprehensive Backup"),
    ]

    for device_type, vendor_name in platforms.items():
        ctx.print_info(f"\n{vendor_name} ({device_type}):")

        for op_name, op_display in operations:
            supported, _ = check_operation_support(device_type, op_name)
            status = "✓ Supported" if supported else "✗ Not supported"
            ctx.print_info(f"  {op_display}: {status}")


def register(app: typer.Typer) -> None:
    """Register the unified backup command with the main CLI app."""
    # Register vendor config backup as a subcommand
    from network_toolkit.commands.vendor_config_backup import register_with_backup_app

    register_with_backup_app(backup_app)

    app.add_typer(backup_app, rich_help_panel="Vendor-Specific Remote Operations")
