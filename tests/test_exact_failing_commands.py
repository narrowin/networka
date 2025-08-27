"""
Test exact CLI commands that were failing in production.

This reproduces the specific commands and paths the user reported as broken.
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestExactFailingCommands:
    """Test the exact commands that were reported as broken."""

    def test_nw_list_devices_with_config_yml_path(self):
        """Test: nw list devices -c ./config/config.yml"""
        if not Path("config/config.yml").exists():
            pytest.skip("Config file not found")

        runner = CliRunner()
        result = runner.invoke(app, ["list", "devices", "-c", "./config/config.yml"])

        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")

        # Should not fail
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Check if devices exist in config
        device_files = (
            list(Path("config/devices").glob("*.yml"))
            if Path("config/devices").exists()
            else []
        )

        if device_files:
            # If device files exist, CLI should NOT show "No devices configured"
            assert "No devices configured" not in result.output, (
                f"Found {len(device_files)} device files but CLI shows no devices. Output: {result.output}"
            )
        else:
            # If no device files, showing "No devices configured" is correct
            assert "No devices configured" in result.output

    def test_nw_list_sequences_default(self):
        """Test: nw list sequences (with no config specified)"""
        runner = CliRunner()
        result = runner.invoke(app, ["list", "sequences"])

        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output}")

        # Should not fail
        assert result.exit_code == 0, f"Command failed: {result.output}"

        # Check if sequences exist in config
        sequences_exist = Path("config/sequences").exists() and any(
            d.is_dir()
            for d in Path("config/sequences").iterdir()
            if not d.name.startswith(".")
        )

        if sequences_exist:
            # If sequence dirs exist, CLI should NOT show "No data available"
            assert "No data available" not in result.output, (
                f"Found sequence directories but CLI shows no data. Output: {result.output}"
            )
        else:
            # If no sequences, showing "No data available" is correct
            assert "No data available" in result.output

    def test_config_loading_matches_cli_behavior(self):
        """Test that config loading behavior matches what CLI actually does."""
        from network_toolkit.config import load_config

        # Test the exact paths the CLI would use
        test_paths = [
            Path("config"),  # Default CLI path
            Path("./config/config.yml"),  # User-reported failing path
        ]

        for config_path in test_paths:
            if not config_path.exists():
                continue

            print(f"Testing config path: {config_path}")

            try:
                config = load_config(config_path)

                device_count = len(config.devices) if config.devices else 0
                sequence_count = (
                    len(config.vendor_sequences) if config.vendor_sequences else 0
                )

                print(f"  Devices loaded: {device_count}")
                print(f"  Vendor sequences loaded: {sequence_count}")

                # Both paths should load the same modular config
                if Path("config/devices").exists() and any(
                    Path("config/devices").glob("*.yml")
                ):
                    assert device_count > 0, f"Should load devices from {config_path}"

                if Path("config/sequences").exists() and any(
                    d.is_dir()
                    for d in Path("config/sequences").iterdir()
                    if not d.name.startswith(".")
                ):
                    assert sequence_count > 0, (
                        f"Should load sequences from {config_path}"
                    )

            except Exception as e:
                pytest.fail(f"Config loading failed for {config_path}: {e}")

    def test_cli_output_inspection(self):
        """Inspect CLI output to understand what's happening."""
        if not Path("config").exists():
            pytest.skip("Config directory not found")

        runner = CliRunner()

        # Test devices command
        devices_result = runner.invoke(
            app, ["list", "devices", "-c", "./config/config.yml"]
        )
        print(f"Devices command output:\n{devices_result.output}")
        print(f"Devices exit code: {devices_result.exit_code}")

        # Test sequences command
        sequences_result = runner.invoke(
            app, ["list", "sequences", "-c", "./config/config.yml"]
        )
        print(f"Sequences command output:\n{sequences_result.output}")
        print(f"Sequences exit code: {sequences_result.exit_code}")

        # Both should succeed
        assert devices_result.exit_code == 0, "Devices command should not fail"
        assert sequences_result.exit_code == 0, "Sequences command should not fail"
