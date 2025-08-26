"""Schema management commands."""

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import get_output_manager


def register(app: typer.Typer) -> None:
    """Register schema commands with the CLI app."""
    app.command(name="schema-update")(schema_update)
    app.command(name="schema-info")(schema_info)


def schema_update(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Update JSON schemas for YAML editor validation.

    Regenerates the JSON schema files used by VS Code and other YAML editors
    to provide validation and auto-completion for configuration files.

    Creates/updates:
    - schemas/network-config.schema.json (full config)
    - schemas/device-config.schema.json (device collections)
    - schemas/groups-config.schema.json (group collections)
    - .vscode/settings.json (VS Code YAML validation)
    """
    setup_logging("DEBUG" if verbose else "INFO")
    output_manager = get_output_manager()

    try:
        from network_toolkit.config import export_schemas_to_workspace

        export_schemas_to_workspace()

        output_manager.print_success("✅ JSON schemas updated successfully")
        output_manager.print_text(
            "   - schemas/network-config.schema.json (full config)"
        )
        output_manager.print_text(
            "   - schemas/device-config.schema.json (device collections)"
        )
        output_manager.print_text(
            "   - schemas/groups-config.schema.json (group collections)"
        )
        output_manager.print_text(
            "   - .vscode/settings.json (VS Code YAML validation)"
        )
        output_manager.print_blank_line()
        output_manager.print_text(
            "Your YAML files now have updated validation and auto-completion."
        )

    except Exception as e:
        output_manager.print_error(f"Failed to update schemas: {e}")
        if verbose:
            import traceback

            output_manager.print_text(traceback.format_exc())
        raise typer.Exit(1) from e


def schema_info(
    verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
) -> None:
    """Display information about JSON schema files."""
    setup_logging("DEBUG" if verbose else "INFO")
    output_manager = get_output_manager()

    schema_dir = Path("schemas")
    vscode_settings = Path(".vscode/settings.json")

    output_manager.print_text("📊 Schema Status:")
    output_manager.print_blank_line()

    # Check schema files
    network_schema = schema_dir / "network-config.schema.json"
    device_schema = schema_dir / "device-config.schema.json"

    if network_schema.exists():
        size = network_schema.stat().st_size
        output_manager.print_text(f"   ✅ {network_schema} ({size:,} bytes)")
    else:
        output_manager.print_text(f"   ❌ {network_schema} (missing)")

    if device_schema.exists():
        size = device_schema.stat().st_size
        output_manager.print_text(f"   ✅ {device_schema} ({size:,} bytes)")
    else:
        output_manager.print_text(f"   ❌ {device_schema} (missing)")

    if vscode_settings.exists():
        size = vscode_settings.stat().st_size
        output_manager.print_text(f"   ✅ {vscode_settings} ({size:,} bytes)")
    else:
        output_manager.print_text(f"   ❌ {vscode_settings} (missing)")

    output_manager.print_blank_line()

    # Check if schemas are working
    missing_count = sum(1 for f in [network_schema, device_schema] if not f.exists())

    if missing_count == 0:
        output_manager.print_success(
            "All schema files are present and ready for YAML validation."
        )
    else:
        output_manager.print_warning(f"{missing_count} schema file(s) missing.")
        output_manager.print_text("Run 'nw schema-update' to regenerate them.")


def _schema_update_impl(verbose: bool = False) -> None:
    """Implementation function for schema update that can be called from unified command.

    This delegates to the original schema_update function by creating a temporary Typer app
    and calling the registered command.
    """
    # Create a temporary app to get access to the registered command
    temp_app = typer.Typer()
    register(temp_app)

    # Find and call the registered command function
    for cmd_info in temp_app.registered_commands:
        if cmd_info.name == "schema-update" and cmd_info.callback:
            cmd_info.callback(verbose=verbose)
            return

    # This should never happen
    error_msg = "Could not find schema-update command in registered commands"
    raise RuntimeError(error_msg)


def _schema_info_impl(verbose: bool = False) -> None:
    """Implementation function for schema info that can be called from unified command.

    This delegates to the original schema_info function by creating a temporary Typer app
    and calling the registered command.
    """
    # Create a temporary app to get access to the registered command
    temp_app = typer.Typer()
    register(temp_app)

    # Find and call the registered command function
    for cmd_info in temp_app.registered_commands:
        if cmd_info.name == "schema-info" and cmd_info.callback:
            cmd_info.callback(verbose=verbose)
            return

    # This should never happen
    error_msg = "Could not find schema-info command in registered commands"
    raise RuntimeError(error_msg)
