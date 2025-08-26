"""Hidden completion helper for dynamic shell completions.

This command is intentionally undocumented in user help and prints plain
newline-separated values for use by completion scripts (bash/zsh/fish).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.config import NetworkConfig, load_config
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
        "ssh",
        "diff",
        "list",
        "config",
        "schema",
        "complete",
    ]


def _list_devices(config: NetworkConfig) -> list[str]:
    return list(config.devices.keys()) if config.devices else []


def _list_groups(config: NetworkConfig) -> list[str]:
    return list(config.device_groups.keys()) if config.device_groups else []


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


def _list_sequences(config: NetworkConfig, *, target: str | None) -> list[str]:
    names: set[str] = set()

    # Global sequences
    if config.global_command_sequences:
        names.update(config.global_command_sequences.keys())

    # Device-specific sequences (either for a specific device/group or across all)
    if config.devices:
        if target and target in config.devices:
            dev = config.devices[target]
            if dev.command_sequences:
                names.update(dev.command_sequences.keys())
        elif (
            target
            and getattr(config, "device_groups", None)
            and (config.device_groups is not None and target in config.device_groups)
        ):
            # Include device-defined sequences from all devices in the group
            for dev_name in config.get_group_members(target):
                dev2 = config.devices.get(dev_name)
                if dev2 and dev2.command_sequences:
                    names.update(dev2.command_sequences.keys())
        else:
            for dev in config.devices.values():
                if dev.command_sequences:
                    names.update(dev.command_sequences.keys())

    # Vendor/user sequences via SequenceManager if we have a target context
    sm = SequenceManager(config)
    if target and config.devices:
        if target in config.devices:
            # Single device: include its vendor sequences
            platform = config.devices[target].device_type
            vendor = sm.list_vendor_sequences(platform)
            names.update(vendor.keys())
        elif getattr(config, "device_groups", None) and (
            config.device_groups is not None and target in config.device_groups
        ):
            # Group: union sequences across all vendors in the group
            platforms: set[str] = set()
            for dev_name in config.get_group_members(target):
                dev3 = config.devices.get(dev_name)
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
                    "sequence-groups|tags"
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
                else:
                    items = []

            for item in items:
                # Plain newline-delimited output; no styles
                typer.echo(item)
        except Exception as _exc:
            # On error, return no suggestions to avoid noisy completion
            raise typer.Exit(0) from None
