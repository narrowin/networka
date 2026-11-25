"""Hidden completion command.

This command is used internally by shell completion scripts to dynamically retrieve
newline-separated values for use by completion scripts (bash/zsh).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.config import NetworkConfig, load_config, load_inspection_config
from network_toolkit.inventory.resolve import (
    list_unique_device_names,
    list_unique_group_names,
    resolve_named_targets,
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
    manager = SequenceManager(config)
    if not target:
        return sorted({record.name for record in manager.catalog_records()})

    devices = resolve_named_targets(config, target).resolved_devices
    return sorted(
        {name for device in devices for name in manager.list_device_sequences(device)}
    )


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
            Path | None, typer.Option("--config", "-c", help="Configuration file path")
        ] = None,
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
                cfg = (
                    load_inspection_config(config_file)
                    if for_ in {"sequences", "vendors"}
                    else load_config(config_file or DEFAULT_CONFIG_PATH)
                )
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
        except Exception as error:
            if for_ in {"sequences", "vendors"}:
                typer.echo(str(error), err=True)
                raise typer.Exit(1) from None
            raise typer.Exit(0) from None
