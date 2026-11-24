"""Transport factory for creating different connection types."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from nornir import Nornir  # pragma: no cover

    from network_toolkit.config import NetworkConfig
    from network_toolkit.transport.interfaces import Transport

logger = logging.getLogger(__name__)


class TransportFactory(Protocol):
    """Factory for creating transport instances."""

    def create_transport(
        self,
        device_name: str,
        config: NetworkConfig,
        connection_params: dict[str, Any],
    ) -> Transport:
        """Create a transport instance for the given device."""
        ...


class ScrapliTransportFactory:
    """Factory for creating Scrapli-based transports."""

    def create_transport(
        self,
        device_name: str,
        config: NetworkConfig,
        connection_params: dict[str, Any],
    ) -> Transport:
        """Create a Scrapli transport instance."""
        from network_toolkit.transport.scrapli_sync import ScrapliSyncTransport

        return ScrapliSyncTransport.from_connection_params(connection_params)


class NornirNetmikoTransportFactory:
    """Factory for creating Nornir+Netmiko based transports."""

    def __init__(self) -> None:
        """Initialize the factory."""
        self._nornir_runner: Nornir | None = None

    def create_transport(
        self,
        device_name: str,
        config: NetworkConfig,
        connection_params: dict[str, Any],
    ) -> Transport:
        """Create a Nornir+Netmiko transport instance."""
        # nornir_netmiko transport coming soon - use scrapli for now
        msg = (
            "nornir_netmiko transport is not yet fully implemented. "
            "This feature is coming soon. Please use 'scrapli' transport for now."
        )
        raise NotImplementedError(msg)

    def _setup_nornir(self, config: NetworkConfig) -> Nornir:
        """Setup Nornir runner with inventory from config."""
        try:
            # Import nornir-netmiko to register its plugins
            import importlib.util

            if importlib.util.find_spec("nornir_netmiko"):
                import nornir_netmiko  # type: ignore # noqa: F401
            from nornir.core import Nornir  # type: ignore
        except ImportError as e:
            error_msg = "Nornir package required. Install with: pip install nornir"
            raise ImportError(error_msg) from e

        from network_toolkit.transport.nornir_inventory import build_nornir_inventory

        # Build inventory directly
        inventory = build_nornir_inventory(config)

        # Create Nornir instance directly with inventory - simplest approach
        nr = Nornir(inventory=inventory)
        return nr


def get_transport_factory(transport_type: str = "scrapli") -> TransportFactory:
    """Get the appropriate transport factory."""
    if transport_type == "scrapli":
        return ScrapliTransportFactory()
    else:
        supported_transports = ["scrapli"]
        error_msg = (
            f"Unknown transport type: '{transport_type}'. "
            f"Supported transports: {', '.join(supported_transports)}"
        )
        raise ValueError(error_msg)
