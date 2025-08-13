"""Tests for enhanced results storage functionality."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.config import GeneralConfig, NetworkConfig
from network_toolkit.results_enhanced import ResultsManager


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock NetworkConfig for testing."""
    general_config = GeneralConfig(
        results_dir="test_results",
        store_results=True,
        results_format="txt",
        results_include_timestamp=True,
        results_include_command=True,
    )
    config = MagicMock(spec=NetworkConfig)
    config.general = general_config
    return config


class TestResultsManager:
    """Test ResultsManager functionality."""

    def test_init_with_defaults(self, mock_config: MagicMock) -> None:
        """Test ResultsManager initialization with default values."""
        manager = ResultsManager(mock_config)

        assert manager.config == mock_config
        assert manager.store_results is True
        assert manager.results_dir == Path("test_results")
        assert manager.results_format == "txt"
        assert manager.include_timestamp is True
        assert manager.include_command is True
        assert manager.command_context is None
        assert manager.session_dir is not None

    def test_init_with_overrides(self, mock_config: MagicMock, tmp_path: Path) -> None:
        """Test ResultsManager initialization with override values."""
        manager = ResultsManager(
            mock_config,
            store_results=False,
            results_dir=tmp_path,
            command_context="test_command",
        )

        assert manager.store_results is False
        assert manager.results_dir == tmp_path
        assert manager.command_context == "test_command"
        assert manager.session_dir is None

    def test_sanitize_filename_basic(self, mock_config: MagicMock) -> None:
        """Test basic filename sanitization."""
        manager = ResultsManager(mock_config, store_results=False)

        # Test RouterOS path separators
        result = manager._sanitize_filename("/system/identity/print")
        assert result == "system_identity_print"

        # Test special characters
        result = manager._sanitize_filename('test:*?"<>|file')
        assert result == "test_file"

        # Test spaces and multiple underscores
        result = manager._sanitize_filename("test   file___name")
        assert result == "test_file_name"

    def test_sanitize_filename_edge_cases(self, mock_config: MagicMock) -> None:
        """Test edge cases in filename sanitization."""
        manager = ResultsManager(mock_config, store_results=False)

        # Test leading/trailing dots and underscores
        result = manager._sanitize_filename("._test_file_.")
        assert result == "test_file"

        # Test empty string
        result = manager._sanitize_filename("")
        assert result == ""

        # Test long filename truncation
        long_name = "a" * 150
        result = manager._sanitize_filename(long_name)
        assert len(result) == 100

    @patch("network_toolkit.results_enhanced.datetime")
    def test_create_session_directory_basic(
        self, mock_datetime: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test session directory creation without command context."""
        mock_datetime.now.return_value.strftime.return_value = "20250811_143000"

        manager = ResultsManager(mock_config, store_results=False, results_dir=tmp_path)

        with patch.object(Path, "mkdir") as mock_mkdir:
            session_dir = manager._create_session_directory()

            expected_path = tmp_path / "20250811_143000"
            assert session_dir == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("network_toolkit.results_enhanced.datetime")
    def test_create_session_directory_with_context(
        self, mock_datetime: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test session directory creation with command context."""
        mock_datetime.now.return_value.strftime.return_value = "20250811_143000"

        manager = ResultsManager(
            mock_config,
            store_results=False,
            results_dir=tmp_path,
            command_context="run sw-acc1 /system/identity/print",
        )

        with patch.object(Path, "mkdir") as mock_mkdir:
            session_dir = manager._create_session_directory()

            expected_name = "20250811_143000_run_sw-acc1_system_identity_print"
            expected_path = tmp_path / expected_name
            assert session_dir == expected_path
            mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_store_command_result_disabled(self, mock_config: MagicMock) -> None:
        """Test command result storage when disabled."""
        manager = ResultsManager(mock_config, store_results=False)

        result = manager.store_command_result(
            "test_device", "/system/identity/print", "identity: test-router"
        )

        assert result is None

    @patch("network_toolkit.results_enhanced.datetime")
    def test_store_command_result_success(
        self, mock_datetime: MagicMock, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful command result storage."""
        mock_datetime.now.return_value.strftime.return_value = "20250811_143000"

        manager = ResultsManager(
            mock_config,
            results_dir=tmp_path,
            command_context="run_command",  # Provide a real string context
        )

        with patch.object(manager, "_write_result_file") as mock_write:
            result_path = manager.store_command_result(
                "sw-acc1",
                "/system/identity/print",
                "identity: test-router",
                metadata={"test": "value"},
            )

            assert result_path is not None
            assert "sw-acc1" in str(result_path)
            assert "cmd_system_identity_print.txt" in str(result_path)

            mock_write.assert_called_once()
            call_args = mock_write.call_args
            result_data = call_args[0][1]

            assert result_data["device_name"] == "sw-acc1"
            assert result_data["command"] == "/system/identity/print"
            assert result_data["output"] == "identity: test-router"
            assert result_data["metadata"] == {"test": "value"}

    def test_store_command_result_exception_handling(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test exception handling in command result storage."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        error_msg = "Write error"
        with patch.object(
            manager, "_write_result_file", side_effect=Exception(error_msg)
        ):
            with patch("network_toolkit.results_enhanced.logger") as mock_logger:
                result = manager.store_command_result(
                    "test_device", "test_command", "test_output"
                )

                assert result is None
                mock_logger.error.assert_called_once()

    def test_store_sequence_results_disabled(self, mock_config: MagicMock) -> None:
        """Test sequence results storage when disabled."""
        manager = ResultsManager(mock_config, store_results=False)

        results = manager.store_sequence_results(
            "test_device", "test_sequence", {"cmd1": "output1", "cmd2": "output2"}
        )

        assert results == []

    def test_store_sequence_results_success(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful sequence results storage."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        test_results = {
            "/system/identity/print": "identity: router1",
            "/system/clock/print": "time: 14:30:00",
        }

        with patch.object(manager, "_write_result_file"):
            stored_files = manager.store_sequence_results(
                "sw-acc1",
                "system_info",
                test_results,
                metadata={"sequence": "system_info"},
            )

            assert len(stored_files) == 3  # 2 command files + 1 summary file
            assert all("sw-acc1" in str(path) for path in stored_files)

            # Check that files are properly numbered
            filenames = [path.name for path in stored_files]
            assert any("01_system_identity_print.txt" in name for name in filenames)
            assert any("02_system_clock_print.txt" in name for name in filenames)
            assert any(
                "00_sequence_summary_system_info.txt" in name for name in filenames
            )

    def test_store_group_results_disabled(self, mock_config: MagicMock) -> None:
        """Test group results storage when disabled."""
        manager = ResultsManager(mock_config, store_results=False)

        group_results = [("device1", "output1", None), ("device2", "output2", "error")]

        result = manager.store_group_results(
            "test_group", "test_command", group_results
        )

        assert result == []

    def test_store_group_results_success(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test successful group results storage."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        group_results = [
            ("device1", "success_output", None),
            ("device2", "error_output", "Connection failed"),
        ]

        with patch.object(manager, "_write_result_file") as mock_write:
            with patch.object(manager, "store_command_result") as mock_store_cmd:
                mock_store_cmd.return_value = Path("test/file.txt")

                stored_files = manager.store_group_results(
                    "office_switches", "test_command", group_results
                )

                assert len(stored_files) >= 1
                mock_write.assert_called()
                mock_store_cmd.assert_called()

    def test_integration_with_real_filesystem(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Integration test with real filesystem operations."""
        results_dir = tmp_path / "integration_results"
        manager = ResultsManager(mock_config, results_dir=results_dir)

        result_path = manager.store_command_result(
            "sw-acc1", "/system/identity/print", "identity: test-router"
        )

        assert result_path is not None
        assert result_path.exists()
        assert result_path.is_file()

        content = result_path.read_text(encoding="utf-8")
        assert "identity: test-router" in content

    def test_session_directory_reuse(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test that the same session directory is reused for multiple operations."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        with patch.object(manager, "_write_result_file"):
            path1 = manager.store_command_result("device1", "cmd1", "output1")
            path2 = manager.store_command_result("device2", "cmd2", "output2")

            assert path1 is not None and path2 is not None
            assert path1.parent.parent == path2.parent.parent
            assert path1.parent.parent == manager.session_dir

    def test_logging_integration(self, mock_config: MagicMock, tmp_path: Path) -> None:
        """Test logging integration in ResultsManager."""
        with patch("network_toolkit.results_enhanced.logger") as mock_logger:
            manager = ResultsManager(mock_config, results_dir=tmp_path)

            mock_logger.info.assert_called_with(
                f"Results will be stored in: {tmp_path}"
            )

            with patch.object(manager, "_write_result_file"):
                manager.store_command_result("test_device", "test_cmd", "test_output")
                mock_logger.debug.assert_called()

    def test_error_handling_in_group_results(
        self, mock_config: MagicMock, tmp_path: Path
    ) -> None:
        """Test error handling in group results storage."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        group_results = [
            ("device1", "success_output", None),
            ("device2", None, "Connection timeout"),
        ]

        with patch.object(manager, "_write_result_file"):
            stored_files = manager.store_group_results(
                "test_group", "test_command", group_results
            )

            assert len(stored_files) >= 1

    def test_sequence_numbering(self, mock_config: MagicMock, tmp_path: Path) -> None:
        """Test that sequence results are properly numbered."""
        manager = ResultsManager(mock_config, results_dir=tmp_path)

        test_results = {
            "/system/identity/print": "identity: router1",
            "/system/clock/print": "time: 14:30:00",
            "/system/resource/print": "cpu: 10%",
        }

        with patch.object(manager, "_write_result_file"):
            stored_files = manager.store_sequence_results(
                "sw-acc1", "system_info", test_results
            )

            assert len(stored_files) == 4  # 3 command files + 1 summary file
            # Check that numbering is correct
            filenames = [path.name for path in stored_files]
            assert any("01_" in name for name in filenames)
            assert any("02_" in name for name in filenames)
            assert any("03_" in name for name in filenames)
            assert any("00_sequence_summary" in name for name in filenames)
