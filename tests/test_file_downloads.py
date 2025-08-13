#!/usr/bin/env python3
"""
Test script for file download functionality.

This script validates the _handle_file_downloads function from cli.py
without requiring actual devices. It tests all edge cases, parameter
validation, placeholder replacement, and error conditions.
"""

import datetime
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, call, patch

from network_toolkit.cli import _handle_file_downloads
from network_toolkit.config import NetworkConfig
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import DeviceExecutionError


class TestHandleFileDownloads(unittest.TestCase):
    """Test cases for _handle_file_downloads function."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        # Mock config with backup directory
        self.mock_config = MagicMock(spec=NetworkConfig)
        self.mock_config.general = MagicMock()
        self.mock_config.general.backup_dir = "/srv/backups"

        # Mock device session
        self.mock_session = MagicMock(spec=DeviceSession)
        self.device_name = "test-device"

    def test_empty_download_files(self) -> None:
        """Test handling empty download_files list."""
        result = _handle_file_downloads(
            session=self.mock_session,
            device_name=self.device_name,
            download_files=[],
            config=self.mock_config,
        )

        self.assertEqual(result, {})
        self.mock_session.download_file.assert_not_called()

    def test_successful_download(self) -> None:
        """Test successful file download."""
        # Setup successful download
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "backup.rsc",
                "local_path": tempfile.gettempdir(),
                "local_filename": "device_backup.rsc",
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path(tempfile.gettempdir()) / "device_backup.rsc"
        self.assertEqual(result["backup.rsc"], f"Downloaded to {expected_path}")

        # Verify download_file was called with correct parameters
        self.mock_session.download_file.assert_called_once_with(
            remote_filename="backup.rsc",
            local_path=expected_path,
            delete_remote=False,
        )

    def test_download_failure(self) -> None:
        """Test handling of download failure."""
        # Setup failed download
        self.mock_session.download_file.return_value = False

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "missing.rsc",
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        self.assertEqual(result["missing.rsc"], "Download failed")

    def test_download_exception(self) -> None:
        """Test handling of download exception."""
        # Setup exception during download
        error_msg = "Connection lost during download"
        self.mock_session.download_file.side_effect = DeviceExecutionError(error_msg)

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "problematic.rsc",
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        self.assertTrue(result["problematic.rsc"].startswith("Download error:"))
        self.assertIn("Connection lost during download", result["problematic.rsc"])

    def test_placeholder_replacement_date(self) -> None:
        """Test {date} placeholder replacement in paths and filenames."""
        self.mock_session.download_file.return_value = True

        # Mock current date
        mock_date = datetime.date(2025, 8, 5)
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = mock_date
            mock_datetime.UTC = datetime.UTC

            download_files: list[dict[str, str | bool]] = [
                {
                    "remote_file": "config.rsc",
                    "local_path": "/backups/{date}",
                    "local_filename": "config-{date}.rsc",
                }
            ]

            with patch("network_toolkit.cli.console"):
                result = _handle_file_downloads(
                    session=self.mock_session,
                    device_name=self.device_name,
                    download_files=download_files,
                    config=self.mock_config,
                )

        expected_path = Path("/backups/2025-08-05") / "config-2025-08-05.rsc"
        self.assertEqual(result["config.rsc"], f"Downloaded to {expected_path}")

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="config.rsc",
            local_path=expected_path,
            delete_remote=False,
        )

    def test_placeholder_replacement_device(self) -> None:
        """Test {device} placeholder replacement in paths and filenames."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "logs.txt",
                "local_path": "/logs/{device}",
                "local_filename": "{device}-logs.txt",
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/logs/test-device") / "test-device-logs.txt"
        self.assertEqual(result["logs.txt"], f"Downloaded to {expected_path}")

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="logs.txt",
            local_path=expected_path,
            delete_remote=False,
        )

    def test_placeholder_replacement_both(self) -> None:
        """Test both {date} and {device} placeholder replacement."""
        self.mock_session.download_file.return_value = True

        # Mock current date
        mock_date = datetime.date(2025, 8, 5)
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = mock_date
            mock_datetime.UTC = datetime.UTC

            download_files: list[dict[str, str | bool]] = [
                {
                    "remote_file": "system-info.txt",
                    "local_path": "/archive/{device}/{date}",
                    "local_filename": "{device}-system-{date}.txt",
                }
            ]

            with patch("network_toolkit.cli.console"):
                result = _handle_file_downloads(
                    session=self.mock_session,
                    device_name=self.device_name,
                    download_files=download_files,
                    config=self.mock_config,
                )

        expected_path = (
            Path("/archive/test-device/2025-08-05")
            / "test-device-system-2025-08-05.txt"
        )
        self.assertEqual(result["system-info.txt"], f"Downloaded to {expected_path}")

    def test_default_local_path_from_config(self) -> None:
        """Test using default backup_dir from config when local_path not specified."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "auto-backup.rsc",
                # No local_path specified, should use config.general.backup_dir
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/srv/backups") / "auto-backup.rsc"
        self.assertEqual(result["auto-backup.rsc"], f"Downloaded to {expected_path}")

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="auto-backup.rsc",
            local_path=expected_path,
            delete_remote=False,
        )

    def test_default_local_filename_from_remote(self) -> None:
        """Test using remote filename as local filename when not specified."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "original-name.rsc",
                "local_path": "/custom/path",
                # No local_filename specified, should use remote_file name
            }
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/custom/path") / "original-name.rsc"
        self.assertEqual(result["original-name.rsc"], f"Downloaded to {expected_path}")

    def test_delete_remote_flag(self) -> None:
        """Test delete_remote flag is passed correctly."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "temp-file.rsc",
                "delete_remote": True,
            }
        ]

        with patch("network_toolkit.cli.console"):
            _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/srv/backups") / "temp-file.rsc"

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="temp-file.rsc",
            local_path=expected_path,
            delete_remote=True,
        )

    def test_multiple_downloads(self) -> None:
        """Test handling multiple file downloads."""

        # Setup: first succeeds, second fails, third throws exception
        def download_side_effect(remote_filename: str, **kwargs: Any) -> bool:
            if remote_filename == "success.rsc":
                return True
            elif remote_filename == "failure.rsc":
                return False
            else:  # error.rsc
                error_msg = "Network error"
                raise DeviceExecutionError(error_msg)

        self.mock_session.download_file.side_effect = download_side_effect

        download_files: list[dict[str, str | bool]] = [
            {"remote_file": "success.rsc"},
            {"remote_file": "failure.rsc"},
            {"remote_file": "error.rsc"},
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        # Check all three results
        self.assertTrue(result["success.rsc"].startswith("Downloaded to"))
        self.assertEqual(result["failure.rsc"], "Download failed")
        self.assertTrue(result["error.rsc"].startswith("Download error:"))
        self.assertIn("Network error", result["error.rsc"])

        # Verify all downloads were attempted
        self.assertEqual(self.mock_session.download_file.call_count, 3)

    def test_empty_remote_file_name(self) -> None:
        """Test handling of empty remote_file name."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [
            {
                "remote_file": "",  # Empty string
                "local_filename": "test.rsc",
            }
        ]

        with patch("network_toolkit.cli.console"):
            _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/srv/backups") / "test.rsc"

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="",
            local_path=expected_path,
            delete_remote=False,
        )

    def test_missing_keys_use_defaults(self) -> None:
        """Test that missing dictionary keys use appropriate defaults."""
        self.mock_session.download_file.return_value = True

        # Test with minimal dictionary - only remote_file
        download_files: list[dict[str, str | bool]] = [{"remote_file": "minimal.rsc"}]

        with patch("network_toolkit.cli.console"):
            _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/srv/backups") / "minimal.rsc"

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="minimal.rsc",
            local_path=expected_path,
            delete_remote=False,  # Default value
        )

    def test_type_coercion(self) -> None:
        """Test that values are properly coerced to expected types."""
        self.mock_session.download_file.return_value = True

        # Test with non-string values that should be coerced
        # Using Any to allow mixed types for testing type coercion
        download_files: list[dict[str, Any]] = [
            {
                "remote_file": 123,  # Will be converted to str
                "local_path": Path("/test"),  # Will be converted to str
                "local_filename": None,  # Will be converted to str
                "delete_remote": "true",  # Will be converted to bool
            }
        ]

        with patch("network_toolkit.cli.console"):
            _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        expected_path = Path("/test") / "None"  # str(None) = "None"

        self.mock_session.download_file.assert_called_once_with(
            remote_filename="123",  # str(123)
            local_path=expected_path,
            delete_remote=True,  # bool("true") = True
        )

    @patch("network_toolkit.cli.console")
    def test_console_output_success(self, mock_console: MagicMock) -> None:
        """Test console output for successful download."""
        self.mock_session.download_file.return_value = True

        download_files: list[dict[str, str | bool]] = [{"remote_file": "test.rsc"}]

        _handle_file_downloads(
            session=self.mock_session,
            device_name=self.device_name,
            download_files=download_files,
            config=self.mock_config,
        )

        # Verify console.print was called with correct messages
        expected_calls = [
            call("[cyan]Downloading test.rsc from test-device...[/cyan]"),
            call("[green]✓ Downloaded test.rsc to /srv/backups/test.rsc[/green]"),
        ]
        mock_console.print.assert_has_calls(expected_calls)

    @patch("network_toolkit.cli.console")
    def test_console_output_failure(self, mock_console: MagicMock) -> None:
        """Test console output for failed download."""
        self.mock_session.download_file.return_value = False

        download_files: list[dict[str, str | bool]] = [{"remote_file": "missing.rsc"}]

        _handle_file_downloads(
            session=self.mock_session,
            device_name=self.device_name,
            download_files=download_files,
            config=self.mock_config,
        )

        # Verify console.print was called with correct messages
        expected_calls = [
            call("[cyan]Downloading missing.rsc from test-device...[/cyan]"),
            call("[red]✗ Failed to download missing.rsc[/red]"),
        ]
        mock_console.print.assert_has_calls(expected_calls)

    @patch("network_toolkit.cli.console")
    def test_console_output_exception(self, mock_console: MagicMock) -> None:
        """Test console output for download exception."""
        self.mock_session.download_file.side_effect = Exception("Network timeout")

        download_files: list[dict[str, str | bool]] = [{"remote_file": "error.rsc"}]

        _handle_file_downloads(
            session=self.mock_session,
            device_name=self.device_name,
            download_files=download_files,
            config=self.mock_config,
        )

        # Verify console.print was called with correct messages
        expected_calls = [
            call("[cyan]Downloading error.rsc from test-device...[/cyan]"),
            call("[red]✗ Error downloading error.rsc: Network timeout[/red]"),
        ]
        mock_console.print.assert_has_calls(expected_calls)


class TestHandleFileDownloadsIntegration(unittest.TestCase):
    """Integration tests for _handle_file_downloads function."""

    def setUp(self) -> None:
        """Set up integration test fixtures."""
        self.mock_config = MagicMock(spec=NetworkConfig)
        self.mock_config.general = MagicMock()
        self.mock_config.general.backup_dir = "/srv/backups"
        self.mock_session = MagicMock(spec=DeviceSession)
        self.device_name = "integration-test-device"

    def test_realistic_backup_scenario(self) -> None:
        """Test a realistic backup scenario with date/device placeholders."""
        self.mock_session.download_file.return_value = True

        # Mock current date for consistent testing
        mock_date = datetime.date(2025, 8, 5)
        with patch("datetime.datetime") as mock_datetime:
            mock_datetime.now.return_value.date.return_value = mock_date
            mock_datetime.UTC = datetime.UTC

            download_files: list[dict[str, str | bool]] = [
                {
                    "remote_file": "backup.backup",
                    "local_path": "/srv/backups/{device}/{date}",
                    "local_filename": "{device}-backup-{date}.backup",
                    "delete_remote": False,
                },
                {
                    "remote_file": "export.rsc",
                    "local_path": "/srv/backups/{device}/{date}",
                    "local_filename": "{device}-config-{date}.rsc",
                    "delete_remote": True,
                },
            ]

            with patch("network_toolkit.cli.console"):
                result = _handle_file_downloads(
                    session=self.mock_session,
                    device_name=self.device_name,
                    download_files=download_files,
                    config=self.mock_config,
                )

        # Check results
        self.assertEqual(len(result), 2)

        backup_path = (
            Path("/srv/backups/integration-test-device/2025-08-05")
            / "integration-test-device-backup-2025-08-05.backup"
        )
        config_path = (
            Path("/srv/backups/integration-test-device/2025-08-05")
            / "integration-test-device-config-2025-08-05.rsc"
        )

        self.assertEqual(result["backup.backup"], f"Downloaded to {backup_path}")
        self.assertEqual(result["export.rsc"], f"Downloaded to {config_path}")

        # Verify calls
        expected_calls = [
            call(
                remote_filename="backup.backup",
                local_path=backup_path,
                delete_remote=False,
            ),
            call(
                remote_filename="export.rsc",
                local_path=config_path,
                delete_remote=True,
            ),
        ]
        self.mock_session.download_file.assert_has_calls(expected_calls)

    def test_mixed_success_failure_scenario(self) -> None:
        """Test scenario with mixed success and failure outcomes."""

        # Setup mixed results
        def download_side_effect(remote_filename: str, **_kwargs: Any) -> bool:
            if remote_filename == "config.rsc":
                return True
            elif remote_filename == "missing.rsc":
                return False
            elif remote_filename == "corrupted.rsc":
                msg = "File corrupted during transfer"
                raise DeviceExecutionError(msg)
            else:
                msg = "Unexpected file"
                raise Exception(msg)

        self.mock_session.download_file.side_effect = download_side_effect

        download_files: list[dict[str, str | bool]] = [
            {"remote_file": "config.rsc", "local_filename": "good-config.rsc"},
            {"remote_file": "missing.rsc", "local_filename": "missing-file.rsc"},
            {"remote_file": "corrupted.rsc", "local_filename": "bad-file.rsc"},
        ]

        with patch("network_toolkit.cli.console"):
            result = _handle_file_downloads(
                session=self.mock_session,
                device_name=self.device_name,
                download_files=download_files,
                config=self.mock_config,
            )

        # Verify results reflect the different outcomes
        self.assertTrue(result["config.rsc"].startswith("Downloaded to"))
        self.assertEqual(result["missing.rsc"], "Download failed")
        self.assertTrue(result["corrupted.rsc"].startswith("Download error:"))
        self.assertIn("File corrupted during transfer", result["corrupted.rsc"])

        # All downloads should have been attempted
        self.assertEqual(self.mock_session.download_file.call_count, 3)


if __name__ == "__main__":
    # Run the tests
    unittest.main(verbosity=2)
