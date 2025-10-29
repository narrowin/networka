"""Tests for results_enhanced module."""

from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from network_toolkit.results_enhanced import ResultsManager


class TestResultsManager:
    """Test ResultsManager class."""

    def test_init_with_defaults(self) -> None:
        """Test ResultsManager initialization with default values."""
        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config)

        assert manager.config is config
        assert manager.store_results is True
        assert manager.results_dir == Path("results")
        assert manager.results_format == "txt"
        assert manager.include_timestamp is True
        assert manager.include_command is True
        assert manager.command_context is None

    def test_init_with_overrides(self) -> None:
        """Test ResultsManager initialization with override values."""
        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(
            config,
            store_results=False,
            results_dir="/tmp/custom",
            command_context="run device1 command",
        )

        assert manager.store_results is False
        assert manager.results_dir == Path("/tmp/custom")
        assert manager.command_context == "run device1 command"

    @patch("network_toolkit.results_enhanced.Path.mkdir")
    @patch("network_toolkit.results_enhanced.logger")
    def test_init_creates_results_dir(
        self, mock_logger: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test that initialization creates results directory."""
        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        ResultsManager(config)

        mock_mkdir.assert_called_with(parents=True, exist_ok=True)
        mock_logger.info.assert_called()

    def test_sanitize_filename_basic(self) -> None:
        """Test basic filename sanitization."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        result = manager._sanitize_filename("/system/identity/print")
        assert result == "system_identity_print"

    def test_sanitize_filename_special_chars(self) -> None:
        """Test filename sanitization with special characters."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        result = manager._sanitize_filename('test:file<name>with*chars?"')
        assert result == "test_file_name_with_chars"

    def test_sanitize_filename_multiple_spaces(self) -> None:
        """Test filename sanitization with multiple spaces."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        result = manager._sanitize_filename("test   multiple    spaces")
        assert result == "test_multiple_spaces"

    def test_sanitize_filename_long_text(self) -> None:
        """Test filename sanitization with long text."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        long_text = "a" * 150  # Longer than MAX_FILENAME_LEN (100)
        result = manager._sanitize_filename(long_text)
        assert len(result) == 100

    @patch("network_toolkit.results_enhanced.datetime")
    @patch("network_toolkit.results_enhanced.Path.mkdir")
    def test_create_session_directory(
        self, mock_mkdir: MagicMock, mock_datetime: MagicMock
    ) -> None:
        """Test session directory creation."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.return_value = "20250811_143000"
        mock_datetime.now.return_value = mock_now

        config = MagicMock()
        config.general.store_results = False
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(
            config, store_results=False, command_context="run device1"
        )

        result = manager._create_session_directory()

        assert "20250811_143000_run_device1" in str(result)
        mock_mkdir.assert_called_with(parents=True, exist_ok=True)

    def test_store_command_result_disabled(self) -> None:
        """Test store_command_result when storage is disabled."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        result = manager.store_command_result(
            "device1", "/system/identity/print", "output"
        )

        assert result is None

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("network_toolkit.results_enhanced.datetime")
    def test_store_command_result_enabled(
        self, mock_datetime: MagicMock, mock_file: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test store_command_result when storage is enabled."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2025-08-11T14:30:00Z"
        mock_now.strftime.return_value = "20250811_143000"
        mock_datetime.now.return_value = mock_now

        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=True, results_dir="/tmp/test")
        manager.session_dir = Path("/tmp/test/session")

        result = manager.store_command_result(
            "device1", "/system/identity/print", "test output"
        )

        assert result is not None
        assert "device1" in str(result)
        assert "system_identity_print" in str(result)
        mock_mkdir.assert_called()
        mock_file.assert_called_with("w", encoding="utf-8")

    def test_store_sequence_results_disabled(self) -> None:
        """Test store_sequence_results when storage is disabled."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        results = {"cmd1": "output1", "cmd2": "output2"}
        result = manager.store_sequence_results("device1", "test_sequence", results)

        assert result == []

    @patch("pathlib.Path.mkdir")
    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("network_toolkit.results_enhanced.datetime")
    def test_store_sequence_results_enabled(
        self, mock_datetime: MagicMock, mock_file: MagicMock, mock_mkdir: MagicMock
    ) -> None:
        """Test store_sequence_results when storage is enabled."""
        # Mock datetime
        mock_now = MagicMock()
        mock_now.isoformat.return_value = "2025-08-11T14:30:00Z"
        mock_now.strftime.return_value = "20250811_143000"
        mock_datetime.now.return_value = mock_now

        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=True, results_dir="/tmp/test")
        manager.session_dir = Path("/tmp/test/session")

        results = {"cmd1": "output1", "cmd2": "output2"}
        result = manager.store_sequence_results("device1", "test_sequence", results)

        assert len(result) == 3  # 2 commands + 1 sequence summary
        mock_mkdir.assert_called()
        # File operations should have been called for both commands + summary
        assert mock_file.call_count >= 3

    @patch("pathlib.Path.open", new_callable=mock_open)
    def test_write_result_file_txt_format(self, mock_file: MagicMock) -> None:
        """Test writing result file in txt format."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        data = {
            "timestamp": "2025-08-11T14:30:00Z",
            "device_name": "device1",
            "command": "test command",
            "output": "test output",
            "nw_command": "run",
        }
        manager._write_result_file(Path("/tmp/test.txt"), data, is_single_command=True)

        mock_file.assert_called_with("w", encoding="utf-8")
        # Check that write was called with the output
        written_content = "".join(
            call[0][0] for call in mock_file().write.call_args_list
        )
        assert "test output" in written_content

    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("yaml.dump")
    def test_write_result_file_yaml_format(
        self, mock_yaml_dump: MagicMock, mock_file: MagicMock
    ) -> None:
        """Test writing result file in yaml format."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "yaml"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        data = {
            "timestamp": "2025-08-11T14:30:00Z",
            "device_name": "device1",
            "command": "test command",
            "output": "test output",
            "nw_command": "run",
        }
        manager._write_result_file(
            Path("/tmp/test.yaml"), data, is_single_command=False
        )

        mock_file.assert_called_with("w", encoding="utf-8")
        mock_yaml_dump.assert_called_once()

    @patch("pathlib.Path.open", new_callable=mock_open)
    @patch("json.dump")
    def test_write_result_file_json_format(
        self, mock_json_dump: MagicMock, mock_file: MagicMock
    ) -> None:
        """Test writing result file in json format."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "json"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        data = {
            "timestamp": "2025-08-11T14:30:00Z",
            "device_name": "device1",
            "command": "test command",
            "output": "test output",
            "nw_command": "run",
        }
        manager._write_result_file(
            Path("/tmp/test.json"), data, is_single_command=False
        )

        mock_file.assert_called_with("w", encoding="utf-8")
        mock_json_dump.assert_called_once()

    def test_write_result_file_unknown_format(self) -> None:
        """Test writing result file with unknown format defaults to txt."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "unknown"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        with patch("pathlib.Path.open", mock_open()) as mock_file:
            data = {
                "timestamp": "2025-08-11T14:30:00Z",
                "device_name": "device1",
                "command": "test command",
                "output": "test output",
                "nw_command": "run",
            }
            manager._write_result_file(
                Path("/tmp/test.txt"), data, is_single_command=True
            )

            mock_file.assert_called_with("w", encoding="utf-8")

    def test_sanitize_filename_edge_cases(self) -> None:
        """Test filename sanitization edge cases."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        manager = ResultsManager(config, store_results=False)

        # Empty string should return "output" (fallback for valid filename)
        assert manager._sanitize_filename("") == "output"

        # Only special characters should return "output" (fallback)
        assert manager._sanitize_filename("///") == "output"

        # Leading/trailing dots and underscores
        assert manager._sanitize_filename("_.test._") == "test"

        # Multiple consecutive underscores
        assert manager._sanitize_filename("test___file") == "test_file"

    @patch("network_toolkit.results_enhanced.Path.mkdir")
    def test_session_dir_creation_only_once(self, mock_mkdir: MagicMock) -> None:
        """Test that session directory is only created once."""
        config = MagicMock()
        config.general.store_results = True
        config.general.results_dir = "results"
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        with patch("network_toolkit.results_enhanced.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.strftime.return_value = "20250811_143000"
            mock_datetime.now.return_value = mock_now

            manager = ResultsManager(config)

            # First call should create directory
            dir1 = manager._create_session_directory()

            # Second call should return same directory
            dir2 = manager._create_session_directory()

            assert dir1 == dir2

    def test_init_without_store_results_doesnt_create_dir(self) -> None:
        """Test that initialization without store_results doesn't create directories."""
        config = MagicMock()
        config.general.store_results = False
        config.general.results_format = "txt"
        config.general.results_include_timestamp = True
        config.general.results_include_command = True

        with patch("network_toolkit.results_enhanced.Path.mkdir") as mock_mkdir:
            ResultsManager(config, store_results=False)

            # mkdir should not be called when store_results is False
            mock_mkdir.assert_not_called()
