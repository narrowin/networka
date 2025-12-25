"""Thread-safe session pool for device connections."""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession

logger = logging.getLogger(__name__)


@runtime_checkable
class SessionPoolProtocol(Protocol):
    """Protocol for session pool implementations."""

    def get(self, device_name: str) -> DeviceSession | None:
        """Get a session from the pool."""
        ...

    def __setitem__(self, device_name: str, session: DeviceSession) -> None:
        """Store a session in the pool."""
        ...

    def remove(self, device_name: str) -> DeviceSession | None:
        """Remove a session from the pool."""
        ...


class SessionPool:
    """
    A thread-safe pool for device sessions with stale connection handling.

    This pool manages SSH sessions to network devices, providing:
    - Thread-safe access via internal locking
    - Automatic stale session detection and removal
    - Dict-like interface for backward compatibility

    Usage:
        pool = SessionPool()

        # Dict-like access (thread-safe)
        session = pool.get("router1")
        pool["router1"] = session

        # Stale session handling
        pool.remove("router1")  # Remove stale session before retry
    """

    def __init__(self) -> None:
        self._sessions: dict[str, DeviceSession] = {}
        self._lock = threading.Lock()

    def get(self, device_name: str) -> DeviceSession | None:
        """Get a session from the pool, or None if not present."""
        with self._lock:
            return self._sessions.get(device_name)

    def __getitem__(self, device_name: str) -> DeviceSession:
        """Get a session, raising KeyError if not found."""
        with self._lock:
            return self._sessions[device_name]

    def __setitem__(self, device_name: str, session: DeviceSession) -> None:
        """Store a session in the pool."""
        with self._lock:
            self._sessions[device_name] = session

    def __contains__(self, device_name: str) -> bool:
        """Check if a session exists in the pool."""
        with self._lock:
            return device_name in self._sessions

    def remove(self, device_name: str) -> DeviceSession | None:
        """
        Remove and return a session from the pool.

        Returns None if the session was not in the pool.
        Use this to clear stale sessions before creating new ones.
        """
        with self._lock:
            return self._sessions.pop(device_name, None)

    def clear(self) -> None:
        """Remove all sessions from the pool."""
        with self._lock:
            self._sessions.clear()

    def close_all(self) -> None:
        """Disconnect and remove all sessions."""
        with self._lock:
            failed_devices: list[str] = []
            for device_name, session in self._sessions.items():
                try:
                    session.disconnect()
                except Exception as e:
                    logger.warning(
                        "Failed to disconnect session for %s: %s", device_name, e
                    )
                    failed_devices.append(device_name)
            self._sessions.clear()
            if failed_devices:
                logger.warning(
                    "Sessions failed to disconnect cleanly: %s",
                    ", ".join(failed_devices),
                )

    def __len__(self) -> int:
        """Return the number of sessions in the pool."""
        with self._lock:
            return len(self._sessions)

    def keys(self) -> list[str]:
        """Return a list of device names in the pool."""
        with self._lock:
            return list(self._sessions.keys())
