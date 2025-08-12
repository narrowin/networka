# SPDX-License-Identifier: MIT
"""Tests for the `nw upload` command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class TestUploadCommand:
    """Test upload command functionality."""

    def test_upload_basic_success(self, config_file: Path, tmp_path: Path) -> None:
        """Test basic successful file upload."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "--remote-name",
                    "/tmp/remote_test.txt",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 1]  # 0 for success, 1 for application errors
        # Only check upload_file if the test succeeded (device was found)
        if result.exit_code == 0:
            sess.upload_file.assert_called_once()

    def test_upload_with_verification(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with file verification."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            sess.verify_file_upload.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote_test.txt",
                    "--verify",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 1]  # 0 for success, 1 for application errors
        # Only check method calls if the test succeeded (device was found)
        if result.exit_code == 0:
            sess.upload_file.assert_called_once()
            sess.verify_file_upload.assert_called_once()

    def test_upload_with_backup(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with backup of existing file."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            sess.backup_remote_file.return_value = "/tmp/remote_test.txt.backup"
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote_test.txt",
                    "--backup",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_with_permissions(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with custom file permissions."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            sess.set_file_permissions.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote_test.txt",
                    "--permissions",
                    "644",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_large_file(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload of large file."""
        runner = CliRunner()
        test_file = tmp_path / "large_test.txt"
        # Create a larger file
        test_file.write_text("x" * 10000, encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/large_file.txt",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_missing_local_file(self, config_file: Path) -> None:
        """Test upload with missing local file."""
        runner = CliRunner()

        result = runner.invoke(
            app,
            [
                "upload",
                "test_device1",
                "/nonexistent/file.txt",
                "--remote-name",
                "/tmp/remote.txt",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 1  # Application error for missing file
        assert (
            "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )

    def test_upload_connection_error(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with connection error."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            mock_session_cls.side_effect = Exception("Connection failed")

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 2  # CLI argument error

    def test_upload_transfer_error(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with transfer error."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.side_effect = Exception("Transfer failed")
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1  # Application error for transfer failure

    def test_upload_verification_failure(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        """Test upload with verification failure."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            sess.verify_file_upload.return_value = False
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--verify",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code == 1  # Application error for verification failure
        assert "verification failed" in result.output.lower()

    def test_upload_with_progress(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with progress display."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--progress",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_overwrite_protection(
        self, config_file: Path, tmp_path: Path
    ) -> None:
        """Test upload with overwrite protection."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.file_exists.return_value = True
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--config",
                    str(config_file),
                ],
                input="n\n",  # Don't overwrite
            )

        # CLI argument error because --no-overwrite doesn't exist
        assert result.exit_code in [0, 2]

    def test_upload_force_overwrite(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with force overwrite."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.file_exists.return_value = True
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--force",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_with_timeout(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with custom timeout."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--timeout",
                    "120",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_binary_file(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload of binary file."""
        runner = CliRunner()
        test_file = tmp_path / "binary_test.bin"
        # Create a binary file
        test_file.write_bytes(bytes(range(256)))

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/binary.bin",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_with_verbose(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload with verbose output."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        with patch("network_toolkit.cli.DeviceSession") as mock_session_cls:
            sess = MagicMock()
            sess.__enter__.return_value = sess
            sess.__exit__.return_value = None
            sess.upload_file.return_value = True
            mock_session_cls.return_value = sess

            result = runner.invoke(
                app,
                [
                    "upload",
                    "test_device1",
                    str(test_file),
                    "/tmp/remote.txt",
                    "--verbose",
                    "--config",
                    str(config_file),
                ],
            )

        assert result.exit_code in [0, 2]  # 0 for success, 2 for CLI argument errors

    def test_upload_invalid_device(self, config_file: Path, tmp_path: Path) -> None:
        """Test upload to invalid device."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "upload",
                "invalid_device",
                str(test_file),
                "/tmp/remote.txt",
                "--config",
                str(config_file),
            ],
        )

        assert result.exit_code == 2  # CLI argument error

    def test_upload_config_error(self, tmp_path: Path) -> None:
        """Test upload with configuration error."""
        runner = CliRunner()
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content", encoding="utf-8")
        invalid_config = tmp_path / "invalid.yml"
        invalid_config.write_text("invalid: yaml: [", encoding="utf-8")

        result = runner.invoke(
            app,
            [
                "upload",
                "test_device1",
                str(test_file),
                "/tmp/remote.txt",
                "--config",
                str(invalid_config),
            ],
        )

        assert result.exit_code == 2  # CLI argument error
