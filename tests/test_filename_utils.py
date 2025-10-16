# SPDX-License-Identifier: MIT
"""Tests for filename normalization utilities."""

from network_toolkit.common.filename_utils import (
    normalize_command_output_filename,
    normalize_filename,
)


class TestNormalizeFilename:
    """Tests for normalize_filename function."""

    def test_mikrotik_export_compact(self) -> None:
        """Test normalizing MikroTik export compact command."""
        result = normalize_filename("/export compact file=nw-export")
        assert result == "export_compact"
        assert "=" not in result
        assert "file" not in result

    def test_mikrotik_backup_save(self) -> None:
        """Test normalizing MikroTik backup save command."""
        result = normalize_filename("/system/backup/save name=nw-backup")
        assert result == "system_backup_save"
        assert "=" not in result
        assert "name" not in result

    def test_mikrotik_resource_print(self) -> None:
        """Test normalizing MikroTik resource print command."""
        result = normalize_filename("/system resource print")
        assert result == "system_resource_print"

    def test_cisco_show_running_config(self) -> None:
        """Test normalizing Cisco show running-config command."""
        result = normalize_filename("show running-config")
        assert result == "show_running-config"

    def test_removes_leading_slash(self) -> None:
        """Test that leading slashes are removed."""
        result = normalize_filename("/interface/print")
        assert not result.startswith("_")
        assert result == "interface_print"

    def test_replaces_special_chars(self) -> None:
        """Test that special characters are replaced."""
        result = normalize_filename("/path:name*test?file<out>put|data")
        assert result == "path_name_test_file_out_put_data"

    def test_collapses_whitespace(self) -> None:
        """Test that multiple spaces/underscores are collapsed."""
        result = normalize_filename("test    multiple   spaces")
        assert result == "test_multiple_spaces"

    def test_strips_trailing_chars(self) -> None:
        """Test that trailing underscores and dots are removed."""
        result = normalize_filename("test___")
        assert result == "test"

        result = normalize_filename("test...")
        assert result == "test"

    def test_length_limiting(self) -> None:
        """Test that overly long filenames are truncated."""
        long_text = "a" * 200
        result = normalize_filename(long_text, max_length=50)
        assert len(result) == 50

    def test_empty_string_fallback(self) -> None:
        """Test that empty strings get a default name."""
        result = normalize_filename("")
        assert result == "output"

    def test_only_special_chars(self) -> None:
        """Test handling of strings with only special characters."""
        result = normalize_filename("===///***")
        assert result == "output"  # Falls back to default

    def test_preserves_hyphens(self) -> None:
        """Test that hyphens are preserved in filenames."""
        result = normalize_filename("show running-config")
        assert "running-config" in result


class TestNormalizeCommandOutputFilename:
    """Tests for normalize_command_output_filename function."""

    def test_adds_txt_extension(self) -> None:
        """Test that .txt extension is added."""
        result = normalize_command_output_filename("/system resource print")
        assert result.endswith(".txt")
        assert result == "system_resource_print.txt"

    def test_mikrotik_export_compact_output(self) -> None:
        """Test MikroTik export command produces clean output filename."""
        result = normalize_command_output_filename("/export compact file=nw-export")
        assert result == "export_compact.txt"

    def test_cisco_command_output(self) -> None:
        """Test Cisco command produces clean output filename."""
        result = normalize_command_output_filename("show running-config")
        assert result == "show_running-config.txt"

    def test_complex_command_output(self) -> None:
        """Test complex command with parameters."""
        result = normalize_command_output_filename(
            '/log/print where topics~"error|critical"'
        )
        assert result.endswith(".txt")
        assert "=" not in result
        # Should stop before the 'where' clause parameters
        assert result == "log_print.txt"
