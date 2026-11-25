"""Test the transport abstraction implementation."""

import os
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
from network_toolkit.transport.factory import get_transport_factory
from network_toolkit.transport.interfaces import Transport
from network_toolkit.transport.scrapli_sync import ScrapliSyncTransport


class TestTransportAbstraction:
    """Test suite for transport abstraction."""

    def test_get_transport_factory_scrapli(self):
        """Test getting Scrapli transport factory."""
        factory = get_transport_factory("scrapli")
        assert factory is not None
        assert hasattr(factory, "create_transport")

    def test_get_transport_factory_nornir_not_available(self):
        """Test that Nornir transport factory is not available yet."""
        with pytest.raises(ValueError, match="Unknown transport type"):
            get_transport_factory("nornir_netmiko")

    def test_get_transport_factory_invalid(self):
        """Test invalid transport type raises error."""
        with pytest.raises(ValueError, match="Unknown transport type"):
            get_transport_factory("invalid_transport")

    @patch.dict(
        os.environ, {"NW_USER_DEFAULT": "admin", "NW_PASSWORD_DEFAULT": "test_password"}
    )
    def test_scrapli_transport_creation(self):
        """Test creating a Scrapli transport instance."""
        # Set up environment variables for credential resolution
        os.environ["NW_USER_DEFAULT"] = "test_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "test_pass"

        try:
            config = NetworkConfig(
                general=GeneralConfig(),
                devices={
                    "test_device": DeviceConfig(
                        host="192.168.1.1", transport_type="scrapli"
                    )
                },
            )

            factory = get_transport_factory("scrapli")
            connection_params = config.get_device_connection_params("test_device")

            # Mock Scrapli to avoid actual connection
            with patch("network_toolkit.transport.scrapli_sync.Cli") as mock_scrapli:
                mock_driver = MagicMock()
                mock_scrapli.return_value = mock_driver

                transport = factory.create_transport(
                    device_name="test_device",
                    config=config,
                    connection_params=connection_params,
                )

                assert transport is not None
                assert isinstance(transport, Transport)
        finally:
            # Clean up environment variables
            for key in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if key in os.environ:
                    del os.environ[key]

    def test_config_transport_type_resolution(self):
        """Test transport type resolution from config."""
        config = NetworkConfig(
            general=GeneralConfig(default_transport_type="scrapli"),
            devices={
                "device1": DeviceConfig(host="192.168.1.1"),  # No transport_type
                "device2": DeviceConfig(host="192.168.1.2", transport_type="scrapli"),
            },
        )

        # Device1 should use default
        assert config.get_transport_type("device1") == "scrapli"

        # Device2 should use device-specific
        assert config.get_transport_type("device2") == "scrapli"

    @patch.dict(
        os.environ, {"NW_USER_DEFAULT": "admin", "NW_PASSWORD_DEFAULT": "test_password"}
    )
    def test_config_connection_params(self):
        """Test connection parameter generation."""
        # Set up environment variables for credential resolution
        os.environ["NW_USER_DEFAULT"] = "test_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "test_pass"

        try:
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
            # Note: transport_type is not included in connection params
            assert params["timeout_socket"] == 30  # From transport defaults
            # Note: custom transport options may not be included in connection params
        finally:
            # Clean up environment variables
            for key in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if key in os.environ:
                    del os.environ[key]


class TestScrapliSyncTransport:
    """Reply handling and SSH options of the native Scrapli session."""

    @staticmethod
    def _transport(reply: str, *, routeros: bool = True) -> ScrapliSyncTransport:
        driver = MagicMock()
        driver.send_input.return_value = MagicMock(result=reply, failed=False)
        return ScrapliSyncTransport(driver, 1, routeros=routeros)

    @pytest.mark.parametrize(
        "reply",
        [
            "/foo\nbad command name foo (line 1 column 2)",
            "/ip/address/print x\nsyntax error (line 1 column 19)",
            "/interface/set ether9 disabled=yes\nno such item",
            "/x\r\n  failure: already have such address",
        ],
    )
    def test_routeros_error_reply_is_failed(self, reply: str) -> None:
        command = reply.partition("\n")[0].strip()
        result = self._transport(reply).send_command(command)
        assert result.failed is True

    def test_routeros_normal_reply_is_not_failed(self) -> None:
        reply = "/ip/address/print\n 0 10.0.0.1/24  10.0.0.0  ether1"
        result = self._transport(reply).send_command("/ip/address/print")
        assert result.failed is False
        assert result.result == " 0 10.0.0.1/24  10.0.0.0  ether1"

    def test_routeros_error_text_later_in_reply_is_not_failed(self) -> None:
        reply = "/log/print\n12:00:00 system,error no such item"
        assert self._transport(reply).send_command("/log/print").failed is False

    def test_error_prefix_ignored_for_other_platforms(self) -> None:
        result = self._transport("syntax error", routeros=False).send_command("x")
        assert result.failed is False
