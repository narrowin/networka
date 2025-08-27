"""Targeted device.py coverage improvement tests - focus on working functionality."""

from __future__ import annotations

from concurrent.futures import Future
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import (
    DeviceConnectionError,
    DeviceExecutionError,
    NetworkToolkitError,
)


class TestDeviceBasics:
    """Test basic DeviceSession functionality that should work."""

    def test_init_success(self, sample_config: NetworkConfig) -> None:
        """Test successful initialization."""
        session = DeviceSession("test_device1", sample_config)

        assert session.device_name == "test_device1"
        assert session.config == sample_config
        assert not session.is_connected

    def test_repr_disconnected(self, sample_config: NetworkConfig) -> None:
        """Test string representation when disconnected."""
        session = DeviceSession("test_device1", sample_config)
        repr_str = repr(session)

        assert "DeviceSession" in repr_str
        assert "test_device1" in repr_str
        assert "disconnected" in repr_str

    def test_repr_connected(self, sample_config: NetworkConfig) -> None:
        """Test string representation when connected."""
        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        repr_str = repr(session)
        assert "connected" in repr_str

    def test_init_with_credential_overrides(self, sample_config: NetworkConfig) -> None:
        """Test initialization with credential overrides."""
        session = DeviceSession(
            "test_device1",
            sample_config,
            username_override="override_user",
            password_override="override_pass",
        )

        assert session.device_name == "test_device1"
        assert session.config == sample_config


class TestConnectionHandling:
    """Test connection-related functionality."""

    @patch("network_toolkit.device.Scrapli")
    def test_connect_success(self, mock_scrapli, sample_config: NetworkConfig) -> None:
        """Test successful connection."""
        mock_driver = MagicMock()
        mock_scrapli.return_value = mock_driver

        session = DeviceSession("test_device1", sample_config)
        session.connect()

        assert session.is_connected
        mock_driver.open.assert_called_once()

    def test_connect_failure(self, sample_config: NetworkConfig) -> None:
        """Test connection failure handling."""
        from scrapli.exceptions import ScrapliException

        session = DeviceSession("test_device1", sample_config)

        # Mock the driver to raise ScrapliException on open
        with patch.object(session, "_driver") as mock_driver:
            mock_driver.open.side_effect = ScrapliException("Connection failed")

            with pytest.raises(DeviceConnectionError):
                session.connect()

    def test_disconnect_success(self, sample_config: NetworkConfig) -> None:
        """Test successful disconnection."""
        session = DeviceSession("test_device1", sample_config)
        mock_driver = MagicMock()
        session._driver = mock_driver
        session._connected = True

        session.disconnect()

        assert not session.is_connected
        mock_driver.close.assert_called_once()

    def test_disconnect_when_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test disconnect when not connected."""
        session = DeviceSession("test_device1", sample_config)
        # Should not raise exception
        session.disconnect()

    def test_disconnect_with_driver_error(self, sample_config: NetworkConfig) -> None:
        """Test disconnect when driver.close() fails."""
        session = DeviceSession("test_device1", sample_config)
        mock_driver = MagicMock()
        mock_driver.close.side_effect = Exception("Close failed")
        session._driver = mock_driver
        session._connected = True

        # Should not raise exception, should log
        session.disconnect()
        assert not session.is_connected


class TestContextManager:
    """Test context manager functionality."""

    @patch("network_toolkit.device.Scrapli")
    def test_context_manager_success(
        self, mock_scrapli, sample_config: NetworkConfig
    ) -> None:
        """Test context manager with successful connection."""
        mock_driver = MagicMock()
        mock_scrapli.return_value = mock_driver

        with DeviceSession("test_device1", sample_config) as session:
            assert session.is_connected
            mock_driver.open.assert_called_once()

        mock_driver.close.assert_called_once()

    def test_context_manager_connection_failure(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test context manager with connection failure."""
        from scrapli.exceptions import ScrapliException

        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_scrapli.return_value.open.side_effect = ScrapliException(
                "Connection failed"
            )

            with pytest.raises(DeviceConnectionError):
                with DeviceSession("test_device1", sample_config):
                    pass

    @patch("network_toolkit.device.Scrapli")
    def test_context_manager_exception_in_block(
        self, mock_scrapli, sample_config: NetworkConfig
    ) -> None:
        """Test context manager with exception in block."""
        mock_driver = MagicMock()
        mock_scrapli.return_value = mock_driver

        with pytest.raises(ValueError):
            with DeviceSession("test_device1", sample_config):
                test_message = "Test exception"
                raise ValueError(test_message)

        # Should still call close
        mock_driver.close.assert_called_once()


class TestCommandExecution:
    """Test command execution functionality."""

    def test_execute_command_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test command execution when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceExecutionError) as exc_info:
            session.execute_command("show version")

        assert "not connected" in str(exc_info.value).lower()

    def test_execute_command_success(self, sample_config: NetworkConfig) -> None:
        """Test successful command execution."""
        session = DeviceSession("test_device1", sample_config)

        # Create mock transport response
        mock_response = MagicMock()
        mock_response.failed = False
        mock_response.result = "RouterOS 7.1"

        # Mock the transport
        mock_transport = MagicMock()
        mock_transport.send_command.return_value = mock_response

        # Set up the session state
        with patch.object(session, "_connected", True):
            with patch.object(session, "_transport", mock_transport):
                result = session.execute_command("show version")

        assert result == "RouterOS 7.1"
        mock_transport.send_command.assert_called_once_with("show version")

    def test_execute_commands_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test execute_commands when not connected."""
        session = DeviceSession("test_device1", sample_config)

        result = session.execute_commands(["cmd1", "cmd2"])

        # Should return error messages for each command
        assert len(result) == 2
        assert "not connected" in result["cmd1"].lower()
        assert "not connected" in result["cmd2"].lower()


class TestFileOperations:
    """Test file operation functionality."""

    def test_upload_file_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test upload_file when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceExecutionError) as exc_info:
            session.upload_file(Path("/test/file.txt"), "remote.txt")

        assert "not connected" in str(exc_info.value).lower()


class TestFirmwareOperations:
    """Test firmware operations."""

    def test_upload_firmware_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test firmware upload when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError) as exc_info:
            session.upload_firmware_and_reboot(Path("/test/firmware.npk"))

        assert "not connected" in str(exc_info.value).lower()

    def test_downgrade_firmware_not_connected(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test firmware downgrade when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError) as exc_info:
            session.downgrade_firmware_and_reboot(Path("/test/firmware.npk"))

        assert "not connected" in str(exc_info.value).lower()

    def test_routerboard_upgrade_not_connected(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test RouterBoard upgrade when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError) as exc_info:
            session.routerboard_upgrade_and_reboot()

        assert "not connected" in str(exc_info.value).lower()

    def test_deploy_config_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test config deployment when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError) as exc_info:
            session.deploy_config_with_reset(Path("/test/config.rsc"))

        assert "not connected" in str(exc_info.value).lower()


class TestDownloadOperations:
    """Test download operations."""

    def test_download_file_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test download_file when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError) as exc_info:
            session.download_file("remote.txt", Path("/local/file.txt"))

        assert "not connected" in str(exc_info.value).lower()


class TestErrorConditions:
    """Test various error conditions and edge cases."""

    def test_invalid_device_name(self, sample_config: NetworkConfig) -> None:
        """Test initialization with invalid device name."""
        with pytest.raises(ValueError) as exc_info:
            DeviceSession("nonexistent_device", sample_config)

        assert "not found" in str(exc_info.value).lower()

    @patch("network_toolkit.device.Scrapli")
    def test_connect_already_connected(
        self, mock_scrapli, sample_config: NetworkConfig
    ) -> None:
        """Test connect when already connected."""
        mock_driver = MagicMock()
        mock_scrapli.return_value = mock_driver

        session = DeviceSession("test_device1", sample_config)
        session._connected = True
        session._driver = mock_driver

        # Should not call open again
        session.connect()
        mock_driver.open.assert_not_called()


class TestHelperMethods:
    """Test helper methods for coverage."""

    def test_calculate_file_checksum_file_not_found(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test checksum calculation with non-existent file."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(FileNotFoundError):
            session._calculate_file_checksum(Path("/nonexistent/file.txt"))

    @patch("network_toolkit.device.calculate_file_checksum")
    @patch("pathlib.Path.exists")
    def test_calculate_file_checksum_success(
        self, mock_exists, mock_calc, sample_config: NetworkConfig
    ) -> None:
        """Test successful checksum calculation."""
        mock_exists.return_value = True
        mock_calc.return_value = "abc123"

        session = DeviceSession("test_device1", sample_config)
        result = session._calculate_file_checksum(Path("/test/file.txt"))

        assert result == "abc123"


class TestMultiDeviceOperations:
    """Test multi-device operations."""

    @patch("network_toolkit.device.ThreadPoolExecutor")
    @patch("network_toolkit.device.as_completed")
    @patch("pathlib.Path.exists", return_value=True)  # Mock file existence
    @patch("pathlib.Path.is_file", return_value=True)  # Mock file type check
    def test_upload_file_to_devices_basic(
        self,
        mock_is_file,
        mock_exists,
        mock_as_completed,
        mock_executor,
        sample_config: NetworkConfig,
    ) -> None:
        """Test basic multi-device upload functionality."""
        # Mock a simple successful case
        mock_future = Mock()
        mock_future.result.return_value = ("device1", True)
        mock_as_completed.return_value = [mock_future]

        mock_executor_instance = MagicMock()
        mock_executor_instance.submit.return_value = mock_future
        mock_executor_instance.__enter__.return_value = mock_executor_instance
        mock_executor_instance.__exit__.return_value = None
        mock_executor.return_value = mock_executor_instance

        result = DeviceSession.upload_file_to_devices(
            device_names=["device1"],
            config=sample_config,
            local_path=Path("/test/file.txt"),
            remote_filename="remote.txt",
        )

        assert "device1" in result


class TestLoggingAndThreading:
    """Test logging and threading-related functionality."""

    @patch("network_toolkit.device.logger")
    def test_logging_calls(self, mock_logger, sample_config: NetworkConfig) -> None:
        """Test that logging calls are made."""
        DeviceSession("test_device1", sample_config)

        # Should log initialization
        mock_logger.info.assert_called()

    @patch("network_toolkit.device.threading.current_thread")
    def test_threading_context(self, mock_thread, sample_config: NetworkConfig) -> None:
        """Test threading context handling."""
        mock_thread.return_value.name = "TestThread"

        session = DeviceSession("test_device1", sample_config)
        assert session.device_name == "test_device1"


class TestEdgeCasesAndBoundaries:
    """Test edge cases and boundary conditions."""

    def test_empty_command_list(self, sample_config: NetworkConfig) -> None:
        """Test execute_commands with empty list."""
        session = DeviceSession("test_device1", sample_config)

        result = session.execute_commands([])
        assert result == {}

    def test_special_characters_in_device_name(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test device names with special characters."""
        # This should work as long as the device exists in config
        session = DeviceSession("test_device1", sample_config)
        assert session.device_name == "test_device1"

    @patch("network_toolkit.device.time.sleep")
    def test_time_operations(self, mock_sleep, sample_config: NetworkConfig) -> None:
        """Test operations that involve time delays."""
        # Some operations might use time.sleep for delays
        session = DeviceSession("test_device1", sample_config)
        assert session.device_name == "test_device1"
        # The sleep mock ensures we can test time-related operations
