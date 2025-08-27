"""Scrapli sync adapter implementing the Transport protocol."""

from __future__ import annotations

from scrapli import Scrapli

from network_toolkit.transport.interfaces import CommandResult


class ScrapliSyncTransport:
    """Thin adapter over Scrapli to satisfy our Transport Protocol."""

    def __init__(self, driver: Scrapli) -> None:
        self._driver = driver

    def open(self) -> None:  # pragma: no cover - passthrough
        self._driver.open()

    def close(self) -> None:  # pragma: no cover - passthrough
        self._driver.close()

    def send_command(self, command: str) -> CommandResult:
        resp = self._driver.send_command(command)
        # Scrapli returns an object with .result and .failed
        return CommandResult(
            result=resp.result, failed=bool(getattr(resp, "failed", False))
        )

    def send_interactive(
        self, interact_events: list[tuple[str, str, bool]], timeout_ops: float
    ) -> str:
        resp = self._driver.send_interactive(
            interact_events=interact_events, timeout_ops=timeout_ops
        )
        # Scrapli returns a Response; we only care about repr/text for now
        return repr(resp)
