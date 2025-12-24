"""Hidden completion command.

This command is used internally by shell completion scripts to dynamically retrieve
newline-separated values for use by completion scripts (bash/zsh).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.inventory.resolve import (
    list_unique_device_names,
    list_unique_group_names,
    resolve_named_targets,
    select_named_target,
)
from network_toolkit.sequence_manager import SequenceManager


def _list_commands() -> list[str]:
    """Return top-level command names exposed by the CLI.

    Keep this in sync with registrations in cli.py. We avoid importing the app
    object to prevent circular imports.
    """
    return [
        "info",
        "run",
        "upload",
        "download",
        "backup",
        "firmware",
        "cli",
        "diff",
        "list",
        "config",
        "schema",
        "complete",
    ]


def _list_devices(config: NetworkConfig) -> list[str]:
    return list_unique_device_names(config)


def _list_groups(config: NetworkConfig) -> list[str]:
    return list_unique_group_names(config)


def _list_sequence_groups(config: NetworkConfig) -> list[str]:
    return (
        list(config.command_sequence_groups.keys())
        if config.command_sequence_groups
        else []
    )


def _list_tags(config: NetworkConfig) -> list[str]:
    tags: set[str] = set()
    if config.devices:
        for device in config.devices.values():
            if device.tags:
                tags.update(device.tags)
    return sorted(tags)


def _list_vendors(config: NetworkConfig) -> list[str]:
    """Return all vendor platforms available in sequences."""
    vendors: set[str] = set()

    # Get vendors from SequenceManager
    sm = SequenceManager(config)
    all_sequences = sm.list_all_sequences()
    vendors.update(all_sequences.keys())

    return sorted(vendors)


def _list_sequences(config: NetworkConfig, *, target: str | None) -> list[str]:
    names: set[str] = set()
    target_kind: str | None = None
    if target:
        target_kind = select_named_target(config, target)

    # Global command sequences (vendor-agnostic)
    if config.global_command_sequences:
        names.update(config.global_command_sequences.keys())

    # Device-specific sequences (either for a specific device/group or across all)
    if config.devices:
        if target_kind == "device" and target and target in config.devices:
            dev = config.devices[target]
            if dev.command_sequences:
                names.update(dev.command_sequences.keys())
        elif target_kind == "group" and target:
            members = resolve_named_targets(config, target).resolved_devices
            for dev_name in members:
                dev2 = (config.devices or {}).get(dev_name)
                if dev2 and dev2.command_sequences:
                    names.update(dev2.command_sequences.keys())
        else:
            for dev in config.devices.values():
                if dev.command_sequences:
                    names.update(dev.command_sequences.keys())

    # Vendor/user sequences via SequenceManager if we have a target context
    sm = SequenceManager(config)
    if target and config.devices:
        if target_kind == "device" and target in config.devices:
            # Single device: include its vendor sequences
            platform = config.devices[target].device_type
            vendor = sm.list_vendor_sequences(platform)
            names.update(vendor.keys())
        elif target_kind == "group":
            members = resolve_named_targets(config, target).resolved_devices
            platforms: set[str] = set()
            for dev_name in members:
                dev3 = (config.devices or {}).get(dev_name)
                if dev3 and dev3.device_type:
                    platforms.add(dev3.device_type)
            for plat in platforms:
                vendor_map = sm.list_vendor_sequences(plat)
                names.update(vendor_map.keys())

    return sorted(names)


def register(app: typer.Typer) -> None:
    @app.command("__complete", hidden=True)
    def __complete(
        for_: Annotated[
            str,
            typer.Option(
                "--for",
                "-f",
                help=(
                    "Completion target: commands|devices|groups|sequences|"
                    "sequence-groups|tags|vendors"
                ),
            ),
        ],
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        device: Annotated[
            str | None,
            typer.Option(
                "--device",
                "-d",
                help=(
                    "Optional target context (device or group) to improve sequence "
                    "suggestions by including vendor and device-defined sequences"
                ),
            ),
        ] = None,
    ) -> None:
        """Print completion candidates for the requested category."""
        try:
            # Only load config when not completing top-level commands
            if for_ == "commands":
                items = _list_commands()
            else:
                cfg = load_config(config_file)
                if for_ == "devices":
                    items = _list_devices(cfg)
                elif for_ == "groups":
                    items = _list_groups(cfg)
                elif for_ == "sequences":
                    items = _list_sequences(cfg, target=device)
                elif for_ == "sequence-groups":
                    items = _list_sequence_groups(cfg)
                elif for_ == "tags":
                    items = _list_tags(cfg)
                elif for_ == "vendors":
                    items = _list_vendors(cfg)
                else:
                    items = []

            for item in items:
                # Plain newline-delimited output; no styles
                typer.echo(item)
        except Exception as _exc:
            # On error, return no suggestions to avoid noisy completion
            raise typer.Exit(0) from None
