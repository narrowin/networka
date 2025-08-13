"""Transport interfaces for device command execution.

Keep it minimal: sync-only, small contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class CommandResult:
    """Result of a command execution."""

    result: str
    failed: bool = False


class Transport(Protocol):
    """Minimal sync transport contract."""

    def open(self) -> None:  # pragma: no cover - thin adapter
        ...

    def close(self) -> None:  # pragma: no cover - thin adapter
        ...

    def send_command(self, command: str) -> CommandResult: ...

    def send_interactive(
        self, interact_events: list[tuple[str, str, bool]], timeout_ops: float
    ) -> str: ...
