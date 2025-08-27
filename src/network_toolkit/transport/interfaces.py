"""Transport interfaces for device command execution.

Keep it minimal: sync-only, small contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class CommandResult:
    """Result of a command execution."""

    result: str
    failed: bool = False


@dataclass(frozen=True)
class ConnectionState:
    """Connection state information."""

    connected: bool
    transport_type: str
    device_name: str
    host: str
    port: int
    last_activity: float | None = None


@runtime_checkable
class Transport(Protocol):
    """Minimal sync transport contract."""

    def open(self) -> None:  # pragma: no cover - thin adapter
        ...

    def close(self) -> None:  # pragma: no cover - thin adapter
        ...

    def send_command(self, command: str) -> CommandResult:
        ...

    def send_interactive(
        self, interact_events: list[tuple[str, str, bool]], timeout_ops: float
    ) -> str:
        ...
