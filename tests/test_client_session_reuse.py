from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.client import NetworkaClient
from network_toolkit.config import NetworkConfig


@pytest.fixture
def mock_config():
    config = MagicMock(spec=NetworkConfig)
    config.devices = {"router1": MagicMock()}
    config.device_groups = {}
    config.general = MagicMock()
    config.general.ssh_strict_host_key_checking = False
    config.get_device_connection_params.return_value = {}
    config.get_transport_type.return_value = "ssh"
    config.vendor_sequences = {}
    config.sequences = {}
    return config

@patch("network_toolkit.client.load_config")
@patch("network_toolkit.device.DeviceSession")
def test_client_reuses_session(mock_device_session_cls, mock_load_config, mock_config):
    mock_load_config.return_value = mock_config

    # Setup mock session
    mock_session = MagicMock()
    mock_session.execute_command.return_value = "output"
    mock_session._connected = False

    def connect_side_effect():
        mock_session._connected = True

    mock_session.connect.side_effect = connect_side_effect

    mock_device_session_cls.return_value = mock_session

    client = NetworkaClient()

    # First run
    client.run("router1", "cmd1")

    # Verify session created
    assert mock_device_session_cls.call_count == 1
    # connect called once
    assert mock_session.connect.call_count == 1

    # Second run
    client.run("router1", "cmd2")

    # Verify session reused (no new creation)
    assert mock_device_session_cls.call_count == 1

    # connect called again (it's idempotent)
    assert mock_session.connect.call_count == 2

    assert mock_session.execute_command.call_count == 2

    # Close client
    client.close()
    assert mock_session.disconnect.call_count == 1

@patch("network_toolkit.client.load_config")
@patch("network_toolkit.device.DeviceSession")
def test_client_context_manager(mock_device_session_cls, mock_load_config, mock_config):
    mock_load_config.return_value = mock_config
    mock_session = MagicMock()
    mock_device_session_cls.return_value = mock_session

    with NetworkaClient() as client:
        client.run("router1", "cmd1")
        assert mock_device_session_cls.call_count == 1

    assert mock_session.disconnect.call_count == 1
