"""
Test CLI commands with real config files to catch production issues.

This test suite uses the actual CLI commands exactly as users would run them,
catching issues that unit tests with mocks might miss.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app

# Get the repository root directory (parent of tests directory)
REPO_ROOT = Path(__file__).parent.parent
CONFIG_DIR = REPO_ROOT / "config"


class TestCLIWithRealConfig:
    """Test CLI commands work with actual config files."""

    def test_list_devices_with_config_yml_path(self):
        """Test that 'nw list devices -c config/config.yml' works."""
        config_file = CONFIG_DIR / "config.yml"
        if not config_file.exists():
            pytest.skip("Real config file not found")

        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "-c", str(config_file)])

        # Should not exit with error
        assert result.exit_code == 0, f"CLI failed with: {result.output}"

        # Should not show "No devices configured" if devices exist
        if (CONFIG_DIR / "devices").exists() and any(
            (CONFIG_DIR / "devices").glob("*.yml")
        ):
            assert "No devices configured" not in result.output, (
                "Should find devices from config/devices/"
            )
            # Should show actual devices
            assert "Device" in result.output or "host" in result.output, (
                "Should show device information"
            )

    def test_list_sequences_with_config_yml_path(self):
        """Test that 'nw list sequences -c config/config.yml' works."""
        config_file = Path("config/config.yml")
        if not config_file.exists():
            pytest.skip("Real config file not found")

        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences", "-c", str(config_file)])

        # Should not exit with error
        assert result.exit_code == 0, f"CLI failed with: {result.output}"

        # Should not show "No data available" if sequences exist
        if Path("config/sequences").exists() and any(
            Path("config/sequences").iterdir()
        ):
            assert "No data available" not in result.output, (
                "Should find sequences from config/sequences/"
            )
            assert "Vendor Sequences" in result.output, "Should show vendor sequences"

    def test_list_devices_with_config_directory(self):
        """Test that 'nw list devices -c config' works."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Real config directory not found")

        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "-c", str(config_dir)])

        # Should not exit with error
        assert result.exit_code == 0, f"CLI failed with: {result.output}"

        # Should find devices if they exist
        if (config_dir / "devices").exists() and any(
            (config_dir / "devices").glob("*.yml")
        ):
            assert "No devices configured" not in result.output, "Should find devices"

    def test_list_sequences_with_config_directory(self):
        """Test that 'nw list sequences -c config' works."""
        config_dir = Path("config")
        if not config_dir.exists():
            pytest.skip("Real config directory not found")

        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences", "-c", str(config_dir)])

        # Should not exit with error
        assert result.exit_code == 0, f"CLI failed with: {result.output}"

        # Should find sequences if they exist
        if (config_dir / "sequences").exists() and any(
            (config_dir / "sequences").iterdir()
        ):
            assert "No data available" not in result.output, "Should find sequences"
            assert "Vendor Sequences" in result.output, "Should show vendor sequences"

    def test_original_failing_command(self):
        """Test the exact command that was originally failing."""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences"])

        # Should work with default config discovery
        assert result.exit_code == 0, f"Default config loading failed: {result.output}"

    def test_config_loading_debug(self, mock_repo_config: Path):
        """Debug test to understand what's happening with config loading."""
        from network_toolkit.config import load_config

        # Test different config loading scenarios
        test_cases = [
            mock_repo_config,
            mock_repo_config / "config.yml",
        ]

        for config_path in test_cases:
            if config_path.exists():
                try:
                    config = load_config(config_path)
                    device_count = len(config.devices) if config.devices else 0

                    # Check for sequences in vendor_sequences OR global_command_sequences
                    vendor_sequence_count = 0
                    if config.vendor_sequences:
                        vendor_sequence_count = sum(
                            len(platform_sequences)
                            for platform_sequences in config.vendor_sequences.values()
                        )

                    global_sequence_count = (
                        len(config.global_command_sequences)
                        if config.global_command_sequences
                        else 0
                    )
                    total_sequence_count = vendor_sequence_count + global_sequence_count

                    # Both should load the same data since they point to the same modular config
                    assert device_count > 0, f"No devices loaded from {config_path}"
                    assert total_sequence_count > 0, (
                        f"No sequences loaded from {config_path} (vendor: {vendor_sequence_count}, global: {global_sequence_count})"
                    )

                except Exception as e:
                    pytest.fail(f"Config loading failed for {config_path}: {e}")

    def test_cli_matches_config_loading(self):
        """Ensure CLI results match direct config loading."""
        from network_toolkit.config import load_config

        config_file = Path("config/config.yml")
        if not config_file.exists():
            pytest.skip("Config file not found")

        # Load config directly
        config = load_config(config_file)
        device_count = len(config.devices) if config.devices else 0
        sequence_count = len(config.vendor_sequences) if config.vendor_sequences else 0

        # Test CLI commands
        runner = CliRunner()

        # Test devices
        devices_result = runner.invoke(app, ["list", "devices", "-c", str(config_file)])
        assert devices_result.exit_code == 0, (
            f"Devices CLI failed: {devices_result.output}"
        )

        if device_count > 0:
            assert "No devices configured" not in devices_result.output, (
                "CLI should match config loading"
            )

        # Test sequences
        sequences_result = runner.invoke(
            app, ["list", "sequences", "-c", str(config_file)]
        )
        assert sequences_result.exit_code == 0, (
            f"Sequences CLI failed: {sequences_result.output}"
        )

        if sequence_count > 0:
            assert "No data available" not in sequences_result.output, (
                "CLI should match config loading"
            )
