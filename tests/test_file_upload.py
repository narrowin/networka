#!/usr/bin/env python3
"""
Test script for file upload functionality.

This script validates the file upload methods without requiring actual devices.
It tests error conditions, parameter validation, and basic functionality.
"""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import paramiko

from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import DeviceExecutionError


class TestFileUpload(unittest.TestCase):
    """Test cases for file upload functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.mock_config = MagicMock()
        self.mock_config.get_device_connection_params.return_value = {
            "host": "192.168.1.1",
            "port": 22,
            "auth_username": "admin",
            "auth_password": "password",
        }

        self.device_session = DeviceSession("test_device", self.mock_config)
        self.device_session._connected = True
        self.device_session._driver = MagicMock()

    def test_upload_file_not_connected(self):
        """Test upload_file raises error when not connected."""
        session = DeviceSession("test_device", self.mock_config)
        session._connected = False

        with self.assertRaises(DeviceExecutionError):
            session.upload_file("test_file.txt")

    def test_upload_file_not_found(self):
        """Test upload_file raises error for non-existent file."""
        with self.assertRaises(FileNotFoundError):
            self.device_session.upload_file("non_existent_file.txt")

    def test_upload_file_directory_path(self):
        """Test upload_file raises error for directory path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ValueError):
                self.device_session.upload_file(temp_dir)

    @patch("paramiko.Transport")
    @patch("paramiko.SFTPClient.from_transport")
    def test_upload_file_success(self, mock_sftp_class, mock_transport_class):
        """Test successful file upload."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write("Test file content")
            temp_file_path = temp_file.name

        try:
            # Mock the transport and SFTP client
            mock_transport = MagicMock()
            mock_sftp = MagicMock()
            mock_transport_class.return_value = mock_transport
            mock_sftp_class.return_value = mock_sftp

            # Mock the verify method to return True
            self.device_session._verify_file_upload = MagicMock(return_value=True)

            # Test upload
            result = self.device_session.upload_file(temp_file_path)

            # Verify the upload was successful
            self.assertTrue(result)
            mock_transport.connect.assert_called_once()
            mock_sftp.put.assert_called_once()
            mock_sftp.close.assert_called_once()
            mock_transport.close.assert_called_once()

        finally:
            # Clean up the temporary file
            Path(temp_file_path).unlink()

    @patch("paramiko.Transport")
    def test_upload_file_authentication_error(self, mock_transport_class):
        """Test upload_file handles authentication errors."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write("Test file content")
            temp_file_path = temp_file.name

        try:
            # Mock authentication failure
            mock_transport = MagicMock()
            mock_transport.connect.side_effect = paramiko.AuthenticationException(
                "Auth failed"
            )
            mock_transport_class.return_value = mock_transport

            # Test upload
            with self.assertRaises(DeviceExecutionError):
                self.device_session.upload_file(temp_file_path)

        finally:
            # Clean up the temporary file
            Path(temp_file_path).unlink()

    @patch("network_toolkit.device.DeviceSession")
    def test_upload_file_to_devices_success(self, mock_device_session_class):
        """Test successful batch upload to multiple devices."""
        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write("Test file content")
            temp_file_path = temp_file.name

        try:
            # Mock successful device sessions
            mock_session = MagicMock()
            mock_session.upload_file.return_value = True
            mock_device_session_class.return_value.__enter__.return_value = mock_session

            # Test batch upload
            device_names = ["device1", "device2", "device3"]
            results = DeviceSession.upload_file_to_devices(
                device_names=device_names,
                config=self.mock_config,
                local_path=temp_file_path,
            )

            # Verify results
            self.assertEqual(len(results), 3)
            for device_name in device_names:
                self.assertTrue(results[device_name])

        finally:
            # Clean up the temporary file
            Path(temp_file_path).unlink()

    def test_upload_file_to_devices_file_not_found(self):
        """Test batch upload with non-existent file."""
        with self.assertRaises(FileNotFoundError):
            DeviceSession.upload_file_to_devices(
                device_names=["device1"],
                config=self.mock_config,
                local_path="non_existent_file.txt",
            )

    @patch("network_toolkit.device_transfers.tempfile.NamedTemporaryFile")
    @patch("network_toolkit.device_transfers.calculate_file_checksum")
    @patch.object(DeviceSession, "download_file")
    def test_verify_file_upload_success(
        self, mock_download, mock_checksum, mock_tempfile
    ):
        """Test file verification success using download method."""
        # Mock temporary file creation
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_verify_file"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file

        # Mock Path operations
        with patch("network_toolkit.device_transfers.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = True
            mock_path.stat.return_value.st_size = 12  # Expected size
            mock_path.unlink.return_value = None
            mock_path_class.return_value = mock_path

            # Mock the download_file method to simulate successful download
            mock_download.return_value = True

            # Mock calculate_file_checksum to return expected checksum
            mock_checksum.return_value = "expected_checksum"

            # Test with checksum verification
            result = self.device_session._verify_file_upload(
                "test_file.rsc", expected_size=12, expected_checksum="expected_checksum"
            )
            self.assertTrue(result)

            # Verify download_file was called correctly
            mock_download.assert_called_once()

    @patch("network_toolkit.device_transfers.tempfile.NamedTemporaryFile")
    @patch.object(DeviceSession, "download_file")
    def test_verify_file_upload_not_found(self, mock_download, mock_tempfile):
        """Test file verification when download fails."""
        # Mock temporary file creation
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_verify_file"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file

        # Mock Path operations
        with patch("network_toolkit.device_transfers.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False  # File doesn't exist after cleanup
            mock_path.unlink.return_value = None
            mock_path_class.return_value = mock_path

            # Mock the download_file method to simulate download failure
            mock_download.return_value = False

            result = self.device_session._verify_file_upload("missing_file.rsc")
            self.assertFalse(result)

    @patch("network_toolkit.device_transfers.tempfile.NamedTemporaryFile")
    @patch.object(DeviceSession, "download_file")
    def test_verify_file_upload_command_error(self, mock_download, mock_tempfile):
        """Test file verification when download raises an exception."""
        # Mock temporary file creation
        mock_temp_file = MagicMock()
        mock_temp_file.name = "/tmp/test_verify_file"
        mock_tempfile.return_value.__enter__.return_value = mock_temp_file

        # Mock Path operations
        with patch("network_toolkit.device_transfers.Path") as mock_path_class:
            mock_path = MagicMock()
            mock_path.exists.return_value = False  # File doesn't exist after cleanup
            mock_path.unlink.return_value = None
            mock_path_class.return_value = mock_path

            # Mock the download_file method to raise an error
            mock_download.side_effect = DeviceExecutionError("Download failed")

            result = self.device_session._verify_file_upload("test_file.rsc")
            self.assertFalse(result)


class TestFileUploadIntegration(unittest.TestCase):
    """Integration tests for file upload functionality."""

    @patch("paramiko.Transport")
    @patch("paramiko.SFTPClient.from_transport")
    def test_upload_with_custom_filename(self, mock_sftp_class, mock_transport_class):
        """Test upload with custom remote filename."""
        mock_config = MagicMock()
        mock_config.get_device_connection_params.return_value = {
            "host": "192.168.1.1",
            "port": 22,
            "auth_username": "admin",
            "auth_password": "password",
        }

        session = DeviceSession("test_device", mock_config)
        session._connected = True
        session._driver = MagicMock()

        # Create a temporary file
        with tempfile.NamedTemporaryFile(
            mode="w", delete=False, suffix=".txt"
        ) as temp_file:
            temp_file.write("Test file content")
            temp_file_path = temp_file.name

        try:
            # Mock the transport and SFTP client
            mock_transport = MagicMock()
            mock_sftp = MagicMock()
            mock_transport_class.return_value = mock_transport
            mock_sftp_class.return_value = mock_sftp

            # Mock the verify method to return True
            session._verify_file_upload = MagicMock(return_value=True)

            # Test upload with custom filename
            custom_name = "custom_config.rsc"
            result = session.upload_file(temp_file_path, remote_filename=custom_name)

            # Verify the upload used the custom filename
            self.assertTrue(result)
            mock_sftp.put.assert_called_with(temp_file_path, f"/{custom_name}")

        finally:
            # Clean up the temporary file
            Path(temp_file_path).unlink()


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
