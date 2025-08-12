"""Test the transport abstraction implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from src.network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
from src.network_toolkit.transport.factory import get_transport_factory
from src.network_toolkit.transport.interfaces import Transport


class TestTransportAbstraction:
    """Test suite for transport abstraction."""

    def test_get_transport_factory_scrapli(self):
        """Test getting Scrapli transport factory."""
        factory = get_transport_factory("scrapli")
        assert factory is not None
        assert hasattr(factory, "create_transport")

    def test_get_transport_factory_nornir(self):
        """Test getting Nornir transport factory."""
        factory = get_transport_factory("nornir_netmiko")
        assert factory is not None
        assert hasattr(factory, "create_transport")

    def test_get_transport_factory_invalid(self):
        """Test invalid transport type raises error."""
        with pytest.raises(ValueError, match="Unknown transport type"):
            get_transport_factory("invalid_transport")

    @patch.dict(os.environ, {"NT_DEFAULT_PASSWORD": "test_password"})
    def test_scrapli_transport_creation(self):
        """Test creating Scrapli transport without actual connection."""
        # Create minimal config
        config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1", transport_type="scrapli"
                )
            },
        )

        factory = get_transport_factory("scrapli")
        connection_params = config.get_device_connection_params("test_device")

        # Mock Scrapli to avoid actual connection
        with patch("scrapli.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_scrapli.return_value = mock_driver

            transport = factory.create_transport(
                device_name="test_device",
                config=config,
                connection_params=connection_params,
            )

            assert transport is not None
            assert hasattr(transport, "send_command")
            assert hasattr(transport, "get_connection_state")

    def test_config_transport_type_resolution(self):
        """Test transport type resolution from config."""
        config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(host="192.168.1.1"),  # No transport_type
                "device2": DeviceConfig(
                    host="192.168.1.2", transport_type="nornir_netmiko"
                ),
            },
        )

        # Device1 should use default
        assert config.get_transport_type("device1") == "scrapli"

        # Device2 should use device-specific
        assert config.get_transport_type("device2") == "nornir_netmiko"

    @patch.dict(os.environ, {"NT_DEFAULT_PASSWORD": "test_password"})
    def test_config_connection_params(self):
        """Test connection parameter generation."""
        config = NetworkConfig(
            general=GeneralConfig(
                default_transport_type="scrapli",
                transport_defaults={
                    "scrapli": {"timeout_socket": 30, "auth_strict_key": False}
                },
            ),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    port=2222,
                    transport_options={"custom_param": "value"},
                )
            },
        )

        params = config.get_device_connection_params("test_device")

        assert params["host"] == "192.168.1.1"
        assert params["port"] == 2222
        assert params["transport_type"] == "scrapli"
        assert params["timeout_socket"] == 30  # From transport defaults
        assert params["custom_param"] == "value"  # From device options
