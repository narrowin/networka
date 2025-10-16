# SPDX-License-Identifier: MIT
"""Additional device tests for coverage improvement."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.transport import ScrapliSyncTransport


class TestDeviceSessionAdditional:
    """Additional device tests for coverage."""

    def test_device_session_repr(self, sample_config: NetworkConfig) -> None:
        """Test device session representation."""
        session = DeviceSession("test_device1", sample_config)

        # Test repr
        repr_str = repr(session)
        assert "DeviceSession" in repr_str
        assert "test_device1" in repr_str

    def test_device_session_context_manager(self, sample_config: NetworkConfig) -> None:
        """Test device session context manager."""
        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_scrapli.return_value = mock_driver

            with DeviceSession("test_device1", sample_config) as session:
                assert session.is_connected is True
                mock_driver.open.assert_called_once()

            mock_driver.close.assert_called_once()

    def test_execute_command_success(self, sample_config: NetworkConfig) -> None:
        """Test successful command execution."""
        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_transport = MagicMock(spec=ScrapliSyncTransport)

            mock_result = MagicMock()
            mock_result.result = "test output"
            mock_result.failed = False
            mock_transport.send_command.return_value = mock_result

            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with patch.object(session, "_transport", mock_transport):
                session._connected = True
                result = session.execute_command("/system/identity/print")
                assert result == "test output"

    def test_execute_command_failure(self, sample_config: NetworkConfig) -> None:
        """Test command execution failure."""
        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_transport = MagicMock(spec=ScrapliSyncTransport)

            mock_result = MagicMock()
            mock_result.result = "error output"
            mock_result.failed = True
            mock_transport.send_command.return_value = mock_result

            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with patch.object(session, "_transport", mock_transport):
                session._connected = True
                with pytest.raises(DeviceExecutionError):
                    session.execute_command("/invalid/command")

    def test_execute_command_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test command execution when not connected."""
        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceExecutionError, match="not connected"):
            session.execute_command("/system/identity/print")

    def test_execute_commands_multiple(self, sample_config: NetworkConfig) -> None:
        """Test executing multiple commands."""
        commands = [
            "/system/identity/print",
            "/system/clock/print",
            "/system/resource/print",
        ]

        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_transport = MagicMock(spec=ScrapliSyncTransport)

            mock_result = MagicMock()
            mock_result.result = "output"
            mock_result.failed = False
            mock_transport.send_command.return_value = mock_result

            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with patch.object(session, "_transport", mock_transport):
                session._connected = True
                results = session.execute_commands(commands)

            assert len(results) == 3
            assert all(result == "output" for result in results.values())

    def test_execute_commands_with_error(self, sample_config: NetworkConfig) -> None:
        """Test executing commands with one failing."""
        commands = ["/system/identity/print", "/invalid/command"]

        def side_effect(command: str) -> str:
            if "invalid" in command:
                msg = "Command failed"
                raise DeviceExecutionError(msg)
            return "success output"

        session = DeviceSession("test_device1", sample_config)

        with patch.object(session, "execute_command", side_effect=side_effect):
            results = session.execute_commands(commands)

        assert len(results) == 2
        assert results["/system/identity/print"] == "success output"
        assert "ERROR" in results["/invalid/command"]

    def test_upload_file_basic(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test basic file upload."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        # Mock all the network components
        with patch("paramiko.Transport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            with patch(
                "paramiko.SFTPClient.from_transport"
            ) as mock_sftp_from_transport:
                mock_sftp = MagicMock()
                mock_sftp_from_transport.return_value = mock_sftp

                with patch.object(session, "_verify_file_upload", return_value=True):
                    result = session.upload_file(str(test_file), "test.txt")
                    assert result is True

    def test_upload_file_not_connected(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test file upload when not connected."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceExecutionError, match="not connected"):
            session.upload_file(str(test_file), "test.txt")

    def test_upload_file_not_found(self, sample_config: NetworkConfig) -> None:
        """Test file upload with non-existent file."""
        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        with pytest.raises(FileNotFoundError):
            session.upload_file("/nonexistent/file.txt", "test.txt")

    def test_download_file_basic(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test basic file download."""
        local_file = tmp_path / "downloaded.txt"

        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        # Create the local file to satisfy the verification
        test_content = "test content"
        local_file.write_text(test_content)

        with patch("paramiko.Transport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            with patch(
                "paramiko.SFTPClient.from_transport"
            ) as mock_sftp_from_transport:
                mock_sftp = MagicMock()
                mock_sftp_from_transport.return_value = mock_sftp
                # Mock file stat to match downloaded file size
                mock_sftp.stat.return_value.st_size = len(test_content.encode())

                result = session.download_file("remote.txt", str(local_file))
                assert result is True

    def test_download_file_not_connected(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test file download when not connected."""
        local_file = tmp_path / "downloaded.txt"

        session = DeviceSession("test_device1", sample_config)

        with pytest.raises(DeviceConnectionError, match="not connected"):
            session.download_file("remote.txt", str(local_file))

    def test_disconnect(self, sample_config: NetworkConfig) -> None:
        """Test disconnect method."""
        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)
            session._connected = True
            session._driver = mock_driver

            session.disconnect()

            mock_driver.close.assert_called_once()
            assert session.is_connected is False

    def test_is_connected_property(self, sample_config: NetworkConfig) -> None:
        """Test is_connected property."""
        session = DeviceSession("test_device1", sample_config)

        # Initially not connected
        assert session.is_connected is False

        # Simulate connection
        session._connected = True
        assert session.is_connected is True

    def test_connection_params_initialization(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test connection parameters initialization."""
        session = DeviceSession("test_device1", sample_config)

        # Verify connection params were set
        assert hasattr(session, "_connection_params")
        params = session._connection_params
        assert "auth_strict_key" in params
        # auth_strict_key should match the config setting (default is False)
        assert (
            params["auth_strict_key"]
            == sample_config.general.ssh_strict_host_key_checking
        )
        assert "ssh_config_file" in params
        assert params["ssh_config_file"] == sample_config.general.ssh_config_file

    def test_connect_already_connected(self, sample_config: NetworkConfig) -> None:
        """Test connect when already connected."""
        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        # Should return early without creating new connection
        session.connect()
        assert session.is_connected is True

    def test_disconnect_not_connected(self, sample_config: NetworkConfig) -> None:
        """Test disconnect when not connected."""
        session = DeviceSession("test_device1", sample_config)

        # Should not raise error
        session.disconnect()
        assert session.is_connected is False

    def test_upload_file_directory_error(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test upload file with directory instead of file."""
        test_dir = tmp_path / "test_dir"
        test_dir.mkdir()

        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        with pytest.raises(ValueError, match="not a file"):
            session.upload_file(str(test_dir), "test.txt")

    def test_connection_error_handling(self, sample_config: NetworkConfig) -> None:
        """Test connection error handling."""
        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            # Test configuration error
            mock_scrapli.side_effect = TypeError("Invalid config")

            session = DeviceSession("test_device1", sample_config)

            with pytest.raises(DeviceConnectionError):
                session.connect()

    def test_connection_retry_logic(self, sample_config: NetworkConfig) -> None:
        """Test connection retry logic."""
        from scrapli.exceptions import ScrapliException

        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_driver.open.side_effect = [
                ScrapliException("First attempt fails"),
                None,  # Second attempt succeeds
            ]
            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with patch(
                "network_toolkit.transport.ScrapliSyncTransport"
            ) as mock_transport:
                mock_transport.return_value = MagicMock()
                session.connect()

                # Should have retried
                assert mock_driver.open.call_count == 2
                assert session.is_connected is True

    def test_connection_retry_exhausted(self, sample_config: NetworkConfig) -> None:
        """Test connection when all retries are exhausted."""
        from scrapli.exceptions import ScrapliException

        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_driver.open.side_effect = ScrapliException("Connection failed")
            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with pytest.raises(DeviceConnectionError):
                session.connect()

    def test_command_execution_scrapli_error(
        self, sample_config: NetworkConfig
    ) -> None:
        """Test command execution with Scrapli error."""
        from scrapli.exceptions import ScrapliException

        with patch("network_toolkit.device.Scrapli") as mock_scrapli:
            mock_driver = MagicMock()
            mock_transport = MagicMock(spec=ScrapliSyncTransport)
            mock_transport.send_command.side_effect = ScrapliException(
                "Transport error"
            )

            mock_scrapli.return_value = mock_driver

            session = DeviceSession("test_device1", sample_config)

            with patch.object(session, "_transport", mock_transport):
                session._connected = True
                with pytest.raises(DeviceExecutionError):
                    session.execute_command("/system/identity/print")

    def test_upload_file_auto_filename(
        self, sample_config: NetworkConfig, tmp_path: Path
    ) -> None:
        """Test upload file with automatic filename."""
        test_file = tmp_path / "auto_name.txt"
        test_file.write_text("test content", encoding="utf-8")

        session = DeviceSession("test_device1", sample_config)
        session._connected = True

        # Mock all the network components
        with patch("paramiko.Transport") as mock_transport_class:
            mock_transport = MagicMock()
            mock_transport_class.return_value = mock_transport

            with patch(
                "paramiko.SFTPClient.from_transport"
            ) as mock_sftp_from_transport:
                mock_sftp = MagicMock()
                mock_sftp_from_transport.return_value = mock_sftp

                with patch.object(session, "_verify_file_upload", return_value=True):
                    # No remote filename specified - should use original name
                    result = session.upload_file(str(test_file))
                    assert result is True
                assert result is True
