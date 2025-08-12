"""Deprecated: The 'sequence' command has been removed. Use 'run' instead.

This module remains only as a stub placeholder to avoid import errors in older
environments. It doesn't register any commands. All sequence functionality is
handled by `netkit run <device|group> <sequence>`.
"""

from __future__ import annotations

import typer


def register(app: typer.Typer) -> None:  # pragma: no cover - compatibility stub
    _ = app
    # Intentionally no-op: 'sequence' subcommand was removed in favor of 'run'.
    # Keeping this stub avoids crashes if older integrations import it.
    pass
