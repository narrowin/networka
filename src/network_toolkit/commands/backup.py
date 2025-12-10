"""Unified backup command for network_toolkit."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.api.backup import BackupOptions, BackupResult, run_backup
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.config import load_config

# Create a sub-app for backup commands
backup_app = typer.Typer(
    name="backup",
    help="Backup operations for network devices",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _print_results(ctx: CommandContext, result: BackupResult) -> None:
    """Print the results of the backup operation."""

    # Print unknown targets
    if result.resolution.unknown:
        ctx.output_manager.print_error(
            f"Unknown targets: {', '.join(result.resolution.unknown)}"
        )

    # Print device results
    for dev_result in result.device_results:
        ctx.print_operation_header("Configuration Backup", dev_result.device, "device")

        if dev_result.platform:
            ctx.print_info(f"Platform: {dev_result.platform}")
        if dev_result.transport:
            ctx.print_info(f"Transport: {dev_result.transport}")

        if dev_result.success:
            if dev_result.backup_dir:
                ctx.print_info(f"Saving backup to: {dev_result.backup_dir}")

            for filename in dev_result.text_outputs:
                ctx.print_info(f"  Saved: {filename}")

            for filename in dev_result.downloaded_files:
                ctx.print_info(f"  Downloaded: {filename}")

            ctx.print_info("  Saved: manifest.json")
            ctx.output_manager.print_success(
                f"Backup completed for {dev_result.device}"
            )
        else:
            ctx.print_error(f"Backup creation failed on {dev_result.device}")
            if dev_result.error:
                ctx.print_error(f"  {dev_result.error}")

    # Print summary
    ctx.output_manager.print_header("Backup Summary")
    ctx.output_manager.print_info(f"Total: {result.totals.total}")
    ctx.output_manager.print_success(f"Succeeded: {result.totals.succeeded}")
    if result.totals.failed > 0:
        ctx.output_manager.print_error(f"Failed: {result.totals.failed}")

    ctx.output_manager.print_info(f"Duration: {result.duration:.2f}s")


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

        options = BackupOptions(
            target=target_name,
            config=config,
            download=download,
            delete_remote=delete_remote,
            verbose=verbose,
        )

        result = run_backup(options)

        _print_results(ctx, result)

        if result.totals.failed > 0:
            raise typer.Exit(1)

    except Exception as e:
        if isinstance(e, typer.Exit):
            raise
        ctx.output_manager.print_error(str(e))
        raise typer.Exit(1) from e


# Register function to be called by cli.py
def register(app: typer.Typer) -> None:
    app.add_typer(backup_app)
