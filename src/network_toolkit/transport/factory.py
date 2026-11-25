"""Transport factory for creating different connection types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from network_toolkit.config import NetworkConfig
    from network_toolkit.transport.interfaces import Transport


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
