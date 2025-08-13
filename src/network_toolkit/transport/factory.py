"""Transport factory for creating different connection types."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from nornir import Nornir

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
        from scrapli import Scrapli

        from network_toolkit.transport.scrapli_sync import ScrapliSyncTransport

        # Create Scrapli driver with existing logic
        driver = Scrapli(**connection_params)

        return ScrapliSyncTransport(driver)


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
        try:
            from network_toolkit.transport.nornir_inventory import (
                build_nornir_inventory,
            )
            from network_toolkit.transport.nornir_netmiko import NornirNetmikoTransport
        except ImportError as e:
            error_msg = (
                "Nornir and related packages required for nornir_netmiko transport. "
                "Install with: pip install nornir nornir-netmiko"
            )
            raise ImportError(error_msg) from e

        # Initialize Nornir runner if needed
        if self._nornir_runner is None:
            self._nornir_runner = self._setup_nornir(config)

        # Get device info
        device_config = config.devices[device_name] if config.devices else None
        host = device_config.host if device_config else connection_params.get("host", "unknown")
        port = device_config.port if device_config else connection_params.get("port", 22)
        # Ensure port is an int
        port = int(port) if port is not None else 22

        return NornirNetmikoTransport(self._nornir_runner, device_name, host, port)

    def _setup_nornir(self, config: NetworkConfig) -> Nornir:
        """Setup Nornir runner with inventory from config."""
        try:
            # Import nornir-netmiko to register its plugins
            import nornir_netmiko
            from nornir.core import Nornir
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
    if transport_type == "nornir_netmiko":
        return NornirNetmikoTransportFactory()
    elif transport_type == "scrapli":
        return ScrapliTransportFactory()
    else:
        error_msg = f"Unknown transport type: {transport_type}"
        raise ValueError(error_msg)
