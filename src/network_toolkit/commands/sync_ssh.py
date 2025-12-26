"""Sync SSH config to YAML inventory."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
import yaml

from network_toolkit.common.logging import setup_logging
from network_toolkit.common.paths import default_modular_config_dir
from network_toolkit.exceptions import ConfigurationError
from network_toolkit.inventory.ssh_config import SSHConfigOptions, parse_ssh_config

# Marker to identify hosts that were synced from SSH config
SSH_CONFIG_SOURCE_MARKER = "_ssh_config_source"
# Additional provenance marker for field-level tracking
SSH_CONFIG_PROVENANCE_MARKER = "_ssh_config_provenance"

# Default paths
DEFAULT_SSH_CONFIG = Path("~/.ssh/config")
DEFAULT_OUTPUT_FILE = "devices/ssh-hosts.yml"

# Create a sub-app for sync commands
sync_app = typer.Typer(
    name="sync",
    help="Sync inventory from external sources",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)


def _load_existing_inventory(path: Path) -> dict[str, dict[str, Any]]:
    """Load existing YAML inventory file if it exists.

    Raises:
        ConfigurationError: If the file cannot be read or contains invalid YAML.
    """
    if not path.exists():
        return {}

    try:
        content = path.read_text(encoding="utf-8")
    except PermissionError as e:
        msg = f"Permission denied reading inventory file: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path)},
        ) from e
    except OSError as e:
        msg = f"Failed to read inventory file: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path), "error": str(e)},
        ) from e

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        msg = f"Invalid YAML in inventory file: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path), "error": str(e)},
        ) from e

    if data is None:
        return {}
    if not isinstance(data, dict):
        msg = f"Inventory file must contain a YAML mapping, got {type(data).__name__}"
        raise ConfigurationError(
            msg,
            details={"path": str(path)},
        )
    return data


def _write_inventory(path: Path, inventory: dict[str, dict[str, Any]]) -> None:
    """Write inventory to YAML file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml_output = yaml.dump(inventory, default_flow_style=False, sort_keys=False)
    path.write_text(yaml_output, encoding="utf-8")


def _get_default_output_path() -> Path:
    """Get the default output path for SSH config sync."""
    return default_modular_config_dir() / DEFAULT_OUTPUT_FILE


@sync_app.command("ssh-config")
def sync_ssh_config(
    ssh_config_path: Annotated[
        Path | None,
        typer.Argument(
            help="Path to SSH config file (default: ~/.ssh/config)",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output YAML inventory file (default: <config>/devices/ssh-hosts.yml)",
        ),
    ] = None,
    default_device_type: Annotated[
        str,
        typer.Option(
            "--default-device-type",
            help="Default device_type for new hosts",
        ),
    ] = "generic",
    include: Annotated[
        list[str] | None,
        typer.Option(
            "--include",
            help="Include hosts matching pattern (can repeat)",
        ),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option(
            "--exclude",
            help="Exclude hosts matching pattern (can repeat)",
        ),
    ] = None,
    prune: Annotated[
        bool,
        typer.Option(
            "--prune",
            help="Remove hosts no longer in SSH config",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show changes without writing",
        ),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option(
            "--verbose",
            "-v",
            help="Enable verbose output",
        ),
    ] = False,
) -> None:
    """Sync devices from SSH config to YAML inventory.

    First run creates the file. Subsequent runs:

    - Add new hosts from SSH config

    - Update host/user/port if changed in SSH config

    - Preserve manual edits (device_type, tags, description, etc.)

    - Optionally prune hosts removed from SSH config (--prune)

    Examples:

        nw sync ssh-config                    # Use defaults

        nw sync ssh-config --dry-run          # Preview changes

        nw sync ssh-config ~/.ssh/config.d/routers -o routers.yml
    """
    setup_logging("DEBUG" if verbose else "WARNING")

    # Apply defaults
    resolved_ssh_config = (
        ssh_config_path.expanduser()
        if ssh_config_path
        else DEFAULT_SSH_CONFIG.expanduser()
    )
    resolved_output = output.expanduser() if output else _get_default_output_path()

    # Validate SSH config exists
    if not resolved_ssh_config.exists():
        msg = f"SSH config file not found: {resolved_ssh_config}"
        raise typer.BadParameter(msg)

    options = SSHConfigOptions(
        path=resolved_ssh_config,
        default_device_type=default_device_type,
        include_patterns=include,
        exclude_patterns=exclude,
    )

    # Parse SSH config
    ssh_hosts = parse_ssh_config(options)

    # Load existing output file if it exists
    existing = _load_existing_inventory(resolved_output)

    # Track changes
    added: list[str] = []
    updated: list[tuple[str, list[str]]] = []
    removed: list[str] = []
    unchanged: list[str] = []

    # Process SSH hosts
    for name, ssh_host in ssh_hosts.items():
        if name not in existing:
            # New host - add with SSH config values
            # Track which fields came from SSH config for introspection
            provenance_fields = ["host"]
            new_entry: dict[str, Any] = {
                "host": ssh_host.hostname,
                "device_type": default_device_type,
                SSH_CONFIG_SOURCE_MARKER: name,
            }
            if ssh_host.user:
                new_entry["user"] = ssh_host.user
                provenance_fields.append("user")
            if ssh_host.port:
                new_entry["port"] = ssh_host.port
                provenance_fields.append("port")
            # Store field-level provenance
            new_entry[SSH_CONFIG_PROVENANCE_MARKER] = {
                "source_file": str(resolved_ssh_config),
                "ssh_host_alias": name,
                "fields": provenance_fields,
            }
            existing[name] = new_entry
            added.append(name)
        else:
            # Existing host - only update if it has the marker
            current = existing[name]
            if SSH_CONFIG_SOURCE_MARKER not in current:
                # Not from SSH config, don't touch it
                unchanged.append(name)
                continue

            changes: list[str] = []

            # Update hostname from SSH config
            if current.get("host") != ssh_host.hostname:
                current["host"] = ssh_host.hostname
                changes.append("host")

            # Update user: handle both changes and removals
            old_user = current.get("user")
            if old_user != ssh_host.user:
                if ssh_host.user is None:
                    if "user" in current:
                        del current["user"]
                        changes.append("user (removed)")
                else:
                    current["user"] = ssh_host.user
                    changes.append("user")

            # Update port: handle both changes and removals
            old_port = current.get("port")
            if old_port != ssh_host.port:
                if ssh_host.port is None:
                    if "port" in current:
                        del current["port"]
                        changes.append("port (removed)")
                else:
                    current["port"] = ssh_host.port
                    changes.append("port")

            # Preserve: device_type, tags, description, platform, etc.

            # Update provenance tracking for changed fields
            if changes:
                provenance = current.get(SSH_CONFIG_PROVENANCE_MARKER, {})
                if not provenance:
                    provenance = {
                        "source_file": str(resolved_ssh_config),
                        "ssh_host_alias": name,
                        "fields": [],
                    }
                # Update tracked fields
                tracked_fields = set(provenance.get("fields", []))
                for change in changes:
                    field_name = change.split()[0]  # Handle "user (removed)"
                    if "(removed)" in change:
                        tracked_fields.discard(field_name)
                    else:
                        tracked_fields.add(field_name)
                provenance["fields"] = list(tracked_fields)
                current[SSH_CONFIG_PROVENANCE_MARKER] = provenance
                updated.append((name, changes))
            else:
                unchanged.append(name)

    # Handle removed hosts (only those with marker)
    if prune:
        for name in list(existing.keys()):
            if name not in ssh_hosts and SSH_CONFIG_SOURCE_MARKER in existing[name]:
                del existing[name]
                removed.append(name)

    # Report changes
    prefix = "[DRY RUN] " if dry_run else ""
    if added:
        suffix = "..." if len(added) > 5 else ""
        typer.echo(f"{prefix}Added {len(added)} hosts: {', '.join(added[:5])}{suffix}")
    if updated:
        names = [n for n, _ in updated[:5]]
        typer.echo(f"{prefix}Updated {len(updated)} hosts: {', '.join(names)}")
    if removed:
        suffix = "..." if len(removed) > 5 else ""
        typer.echo(
            f"{prefix}Removed {len(removed)} hosts: {', '.join(removed[:5])}{suffix}"
        )
    if not added and not updated and not removed:
        typer.echo(f"{prefix}No changes ({len(unchanged)} hosts unchanged)")

    # Write output
    if not dry_run:
        _write_inventory(resolved_output, existing)
        typer.echo(f"Wrote {len(existing)} devices to {resolved_output}")
    else:
        typer.echo("[DRY RUN] No changes written")


# Register function to be called by cli.py
def register(app: typer.Typer) -> None:
    app.add_typer(sync_app)
