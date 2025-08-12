"""Transport layer abstractions for netkit.

Option B: sync transport interface with Scrapli adapter.
"""

from __future__ import annotations

from network_toolkit.transport.interfaces import CommandResult, Transport
from network_toolkit.transport.scrapli_sync import ScrapliSyncTransport

__all__ = [
    "CommandResult",
    "ScrapliSyncTransport",
    "Transport",
]
