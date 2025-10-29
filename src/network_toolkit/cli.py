# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Command-line interface for the network toolkit (modularized)."""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperGroup
from typer.main import get_command as _get_click_command

from network_toolkit import __version__

# Command registration: import command factories that attach to `app`
# Each module defines a `register(app)` function that adds its commands.
from network_toolkit.commands.backup import register as register_backup
from network_toolkit.commands.complete import register as register_complete
from network_toolkit.commands.config import register as register_config
from network_toolkit.commands.diff import register as register_diff
from network_toolkit.commands.download import register as register_download
from network_toolkit.commands.firmware import register as register_firmware
from network_toolkit.commands.info import register as register_info
from network_toolkit.commands.list import register as register_list
from network_toolkit.commands.run import register as register_run
from network_toolkit.commands.schema import register as register_schema
from network_toolkit.commands.ssh import register as register_ssh
from network_toolkit.commands.upload import register as register_upload
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import get_output_manager
from network_toolkit.config import NetworkConfig


class _DynamicConsoleProxy:
    """Proxy that forwards attribute access to the current OutputManager console.

    This avoids capturing a stale Console at import time so that changes to the
    output mode (e.g., via --output-mode or config) are reflected everywhere.
    """

    def __getattr__(self, name: str) -> Any:
        return getattr(get_output_manager().console, name)


# Dynamic console that always reflects the active OutputManager
console = _DynamicConsoleProxy()

# Keep this import here to preserve tests that patch `network_toolkit.cli.DeviceSession`
from network_toolkit.device import DeviceSession as _DeviceSession  # noqa: E402


# Preserve insertion order and group commands under a single Commands section
class CategorizedHelpGroup(TyperGroup):
    def list_commands(self, ctx: Any) -> list[str]:
        _ = ctx  # unused
        return list(self.commands)

    def format_commands(self, ctx: Any, formatter: Any) -> None:
        # Desired categories
        exec_names = [
            "run",
            "cli",
            "diff",
            "upload",
            "download",
        ]
        vendor_names: list[str] = [
            "backup",
            "firmware",
        ]
        info_names = [
            "info",
            "list",
            "config",
            "schema",
        ]

        def rows(names: list[str]) -> list[tuple[str, str]]:
            items: list[tuple[str, str]] = []
            for name in names:
                cmd = self.get_command(ctx, name)
                if not cmd:
                    continue
                # Prefer short help if available
                short_getter = getattr(cmd, "get_short_help_str", None)
                short_text = (
                    short_getter() if callable(short_getter) else (cmd.help or "")
                )
                items.append((name, str(short_text)))
            return items

        exec_rows = rows(exec_names)
        vendor_rows = rows(vendor_names)
        info_rows = rows(info_names)

        if exec_rows:
            formatter.write_text("\nRemote Operations")
            formatter.write_dl(exec_rows)
        if vendor_rows:
            formatter.write_text("\nVendor-Specific Remote Operations")
            formatter.write_dl(vendor_rows)
        if info_rows:
            formatter.write_text("\nInfo & Configuration")
            formatter.write_dl(info_rows)


# Typer application instance
help_text = (
    "\n    Networka (nw)\n\n"
    "    A powerful multi-vendor CLI tool for automating network devices based "
    "on ssh protocol.\n"
    "    Built with async/await support and type safety in mind.\n\n"
    "    QUICK START:\n"
    "      nw run sw-acc1 '/system/clock/print'  # Execute command\n"
    "      nw run office_switches system_info    # Run sequence on group\n\n"
    "    For detailed help on any command: nw <command> --help\n"
    "    Default config directory: system app config (use --config to override)\n    "
)
app = typer.Typer(
    name="nw",
    help=help_text,
    no_args_is_help=False,
    rich_markup_mode="rich",
    add_completion=False,
    cls=CategorizedHelpGroup,
    context_settings={"help_option_names": []},  # Disable default help
    invoke_without_command=True,
)

# Click-compatible command is created after all subcommands are registered below


@app.callback()
def main(
    ctx: typer.Context,
    version: Annotated[
        bool, typer.Option("--version", help="Show version information")
    ] = False,
    help_flag: Annotated[
        bool, typer.Option("--help", "-h", help="Show this message and exit")
    ] = False,
) -> None:
    """Configure global settings for the network toolkit."""
    if version:
        from network_toolkit.common.command_helpers import CommandContext

        cmd_ctx = CommandContext()
        cmd_ctx.print_info(f"Networka (nw) version {__version__}")
        raise typer.Exit()

    # If help flag is used or no command is invoked, show banner and help
    if help_flag or ctx.invoked_subcommand is None:
        from network_toolkit.banner import show_banner
        from network_toolkit.common.command_helpers import CommandContext

        cmd_ctx = CommandContext()
        # Show banner first
        show_banner()
        print()  # Add spacing
        # Then show help
        cmd_ctx.output_manager.print_text(ctx.get_help())
        raise typer.Exit()


# Expose DeviceSession symbol for tests to patch (`network_toolkit.cli.DeviceSession`)
DeviceSession = _DeviceSession


def _handle_file_downloads(
    session: _DeviceSession,
    config: NetworkConfig,
    device_name: str,
    download_files: list[dict[str, Any]],
) -> dict[str, str]:
    """Handle file downloads from a device session using centralized output.

    Returns:
        Dict mapping remote_file names to download status messages.
    """
    from network_toolkit.common.command_helpers import CommandContext

    # Create a context for centralized output
    ctx = CommandContext()

    results: dict[str, str] = {}

    def replace_placeholders(text: str) -> str:
        now = datetime.datetime.now(datetime.UTC)
        return (
            text.replace("{date}", now.strftime("%Y%m%d"))
            .replace("{time}", now.strftime("%H%M%S"))
            .replace("{datetime}", now.strftime("%Y%m%d_%H%M%S"))
            .replace("{device}", device_name)
        )

    def to_bool(val: Any) -> bool:
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "yes", "1", "on")
        return bool(val)

    default_dir = getattr(getattr(config, "general", object()), "backup_dir", ".")

    for item in download_files:
        remote_raw = item.get("remote_file", "")  # could be empty per tests
        remote_file = str(remote_raw)

        local_path_val = item.get("local_path", default_dir)
        local_path_str = str(local_path_val)
        local_filename_val = item.get("local_filename", remote_file)
        local_filename_str = str(local_filename_val)
        delete_remote = to_bool(item.get("delete_remote", False))

        # Placeholder replacement
        local_dir = Path(replace_placeholders(local_path_str))
        filename = replace_placeholders(local_filename_str)
        destination = local_dir / filename

        # Use centralized output system
        ctx.output_manager.print_downloading(device_name, remote_file)

        try:
            success = session.download_file(  # type: ignore[attr-defined]
                remote_filename=remote_file,
                local_path=destination,
                delete_remote=delete_remote,
            )
            if success:
                ctx.output_manager.print_success(
                    f"Downloaded {remote_file} to {destination}"
                )
                results[remote_file] = f"Downloaded to {destination}"
            else:
                ctx.output_manager.print_error(f"Failed to download {remote_file}")
                results[remote_file] = "Download failed"
        except Exception as e:  # DeviceExecutionError or unexpected
            ctx.output_manager.print_error(f"Error downloading {remote_file}: {e}")
            results[remote_file] = f"Download error: {e}"

    return results


# Register all commands with the Typer app
register_info(app)
register_list(app)
register_run(app)
register_config(app)
register_backup(app)
register_upload(app)
register_download(app)
register_firmware(app)
register_complete(app)
register_diff(app)
register_schema(app)
register_ssh(app)

# Expose a Click-compatible command for documentation tools (e.g., mkdocs-click)
# Create this after all subcommands have been registered
cli = _get_click_command(app)


__all__ = [
    "DeviceSession",
    "_handle_file_downloads",
    "app",
    "cli",
    "console",
    "setup_logging",
]
