"""Unified backup command for network_toolkit."""

from __future__ import annotations

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

MAX_LIST_PREVIEW = 10

# Create a sub-app for backup commands
backup_app = typer.Typer(
    name="backup",
    help="Backup operations for network devices",
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
    setup_logging("DEBUG" if verbose else "INFO")
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
            """Resolve the backup sequence for a device."""
            seq_name = "backup_config"
            devices = config.devices or {}
            device_config = devices.get(device_name)

            # Try device-specific sequences first
            if (
                device_config
                and device_config.command_sequences
                and seq_name in device_config.command_sequences
            ):
                return device_config.command_sequences[seq_name]

            return []

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
                    backup_success = platform_ops.create_backup(
                        backup_sequence=seq_cmds,
                        download_files=None,  # Will handle downloads separately
                    )

                    if not backup_success:
                        ctx.print_error(f"Backup creation failed on {dev}")
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
            except Exception as e:  # pragma: no cover
                ctx.print_error(f"Unexpected error on {dev}: {e}")
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            ctx.print_operation_complete("Backup", success=True)
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
    setup_logging("DEBUG" if verbose else "INFO")
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

                    backup_success = platform_ops.create_backup(
                        backup_sequence=seq_cmds,
                        download_files=None,  # Will handle downloads separately
                    )

                    if not backup_success:
                        ctx.print_error(
                            f"Comprehensive backup creation failed on {dev}"
                        )
                        return False

                    if download:
                        downloads: list[dict[str, Any]] = [
                            {
                                "remote_file": "nw-backup.backup",
                                "local_path": str(config.general.backup_dir),
                                "local_filename": "{device}_{date}_nw.backup",
                                "delete_remote": delete_remote,
                            },
                            {
                                "remote_file": "nw-export.rsc",
                                "local_path": str(config.general.backup_dir),
                                "local_filename": "{device}_{date}_nw-export.rsc",
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
            except Exception as e:  # pragma: no cover
                ctx.print_error(f"Unexpected error on {dev}: {e}")
                return False

        if is_device:
            ok = process_device(target_name)
            if not ok:
                raise typer.Exit(1)
            ctx.print_operation_complete("Comprehensive Backup", success=True)
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
