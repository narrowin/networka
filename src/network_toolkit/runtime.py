# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Process-wide runtime settings.

These settings are populated by the CLI callback and read by config loading
and target resolution logic. Programmatic callers that do not use the CLI
will see default (empty) settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class RuntimeSettings:
    """Runtime settings affecting config loading and inventory resolution."""

    inventory_paths: list[Path] = field(default_factory=list)
    inventory_prefer: str | None = None


_RUNTIME = RuntimeSettings()


def get_runtime_settings() -> RuntimeSettings:
    """Return current runtime settings."""
    return _RUNTIME


def set_runtime_settings(
    *,
    inventory_paths: list[Path] | None = None,
    inventory_prefer: str | None = None,
) -> None:
    """Set process-wide runtime settings.

    Parameters
    ----------
    inventory_paths : list[Path] | None
        Additional inventory roots/files (Nornir SimpleInventory) to load.
    inventory_prefer : str | None
        Preference token used to select a source when a device/group name is
        present in multiple inventories. Supported values include "config",
        a filesystem path, or a discovered source id (e.g., "clab-s3n").
    """
    if inventory_paths is not None:
        _RUNTIME.inventory_paths = list(inventory_paths)
    _RUNTIME.inventory_prefer = inventory_prefer.strip() if inventory_prefer else None


def reset_runtime_settings() -> None:
    """Reset runtime settings to defaults (useful in tests)."""
    _RUNTIME.inventory_paths = []
    _RUNTIME.inventory_prefer = None
