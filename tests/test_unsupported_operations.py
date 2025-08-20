"""Tests for unsupported platform operations detection."""

from unittest.mock import MagicMock, patch

import pytest

from network_toolkit.platforms import (
    check_operation_support,
    get_platform_file_extensions,
)


class TestUnsupportedOperations:
    """Test detection of unsupported operations before device connection."""

    def test_check_operation_support_cisco_firmware_upgrade(self) -> None:
        """Test that Cisco platforms don't support firmware upgrade."""
        is_supported, error_msg = check_operation_support(
            "cisco_ios", "firmware_upgrade"
        )

        assert not is_supported
        assert (
            "Operation 'firmware_upgrade' is not supported on platform 'Cisco IOS'"
            in error_msg
        )

    def test_check_operation_support_cisco_iosxe_firmware_upgrade(self) -> None:
        """Test that Cisco IOS-XE platforms don't support firmware upgrade."""
        is_supported, error_msg = check_operation_support(
            "cisco_iosxe", "firmware_upgrade"
        )

        assert not is_supported
        assert (
            "Operation 'firmware_upgrade' is not supported on platform 'Cisco IOS-XE'"
            in error_msg
        )

    def test_check_operation_support_cisco_bios_upgrade(self) -> None:
        """Test that Cisco platforms don't support BIOS upgrade."""
        is_supported, error_msg = check_operation_support("cisco_ios", "bios_upgrade")

        assert not is_supported
        assert (
            "Operation 'bios_upgrade' is not supported on platform 'Cisco IOS'"
            in error_msg
        )

    def test_check_operation_support_cisco_config_backup(self) -> None:
        """Test that Cisco platforms don't support config backup."""
        is_supported, error_msg = check_operation_support("cisco_ios", "create_backup")

        assert not is_supported
        assert (
            "Operation 'create_backup' is not supported on platform 'Cisco IOS'"
            in error_msg
        )

    def test_check_operation_support_mikrotik_supported(self) -> None:
        """Test that MikroTik RouterOS supports all operations."""
        is_supported, error_msg = check_operation_support(
            "mikrotik_routeros", "firmware_upgrade"
        )

        assert is_supported
        assert error_msg == ""

    def test_check_operation_support_unknown_platform(self) -> None:
        """Test handling of unknown platforms."""
        is_supported, error_msg = check_operation_support(
            "unknown_platform", "firmware_upgrade"
        )

        assert not is_supported
        assert "Platform 'unknown_platform' is not supported" in error_msg

    def test_get_platform_file_extensions_cisco(self) -> None:
        """Test file extension detection for Cisco platforms."""
        extensions = get_platform_file_extensions("cisco_ios")
        assert ".bin" in extensions

        extensions = get_platform_file_extensions("cisco_iosxe")
        assert ".bin" in extensions

    def test_get_platform_file_extensions_mikrotik(self) -> None:
        """Test file extension detection for MikroTik platforms."""
        extensions = get_platform_file_extensions("mikrotik_routeros")
        assert ".npk" in extensions

    def test_get_platform_file_extensions_unknown(self) -> None:
        """Test file extension detection for unknown platforms."""
        extensions = get_platform_file_extensions("unknown_platform")
        assert extensions == []


class TestCommandLineUnsupportedOperations:
    """Test unsupported operations through command line interface."""

    @patch("network_toolkit.commands.firmware_upgrade.check_operation_support")
    @patch("network_toolkit.commands.firmware_upgrade.load_config")
    @patch("network_toolkit.commands.firmware_upgrade.setup_logging")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.is_file")
    def test_firmware_upgrade_fails_fast_for_unsupported_platform(
        self,
        mock_is_file: MagicMock,
        mock_exists: MagicMock,
        mock_setup_logging: MagicMock,
        mock_load_config: MagicMock,
        mock_check_support: MagicMock,
    ) -> None:
        """Test that firmware upgrade fails fast for unsupported platforms."""
        # Mock file validation
        mock_exists.return_value = True
        mock_is_file.return_value = True

        # Mock platform check to return unsupported
        mock_check_support.return_value = (
            False,
            "Operation 'firmware_upgrade' is not supported on platform 'Test Platform'",
        )

        # Mock config
        mock_config = MagicMock()
        mock_device_config = MagicMock()
        mock_device_config.device_type = "test_platform"
        mock_config.devices = {"test_device": mock_device_config}
        mock_config.device_groups = {}
        mock_load_config.return_value = mock_config

        import typer
        from typer.testing import CliRunner

        from network_toolkit.commands.firmware_upgrade import register

        app = typer.Typer()
        register(app)
        runner = CliRunner()

        result = runner.invoke(app, ["test_device", "firmware.bin"])

        # Should fail without attempting connection
        assert result.exit_code == 1

        # Should have checked platform support
        mock_check_support.assert_called_once_with("test_platform", "firmware_upgrade")

        # Should NOT have attempted to import device session module
        # (this would happen only during actual device connection)

    def test_all_unsupported_cisco_operations(self) -> None:
        """Test that all firmware/BIOS operations are unsupported on Cisco."""
        cisco_platforms = ["cisco_ios", "cisco_iosxe"]
        unsupported_operations = [
            "firmware_upgrade",
            "firmware_downgrade",
            "bios_upgrade",
            "create_backup",
        ]

        for platform in cisco_platforms:
            for operation in unsupported_operations:
                is_supported, error_msg = check_operation_support(platform, operation)
                assert not is_supported, (
                    f"{operation} should not be supported on {platform}"
                )
                assert operation in error_msg

                # Check that the platform name appears correctly in the error message
                if platform == "cisco_ios":
                    assert "Cisco IOS" in error_msg
                elif platform == "cisco_iosxe":
                    assert "Cisco IOS-XE" in error_msg

    def test_mikrotik_operations_supported(self) -> None:
        """Test that MikroTik RouterOS supports all operations."""
        supported_operations = [
            "firmware_upgrade",
            "firmware_downgrade",
            "bios_upgrade",
            "create_backup",
        ]

        for operation in supported_operations:
            is_supported, error_msg = check_operation_support(
                "mikrotik_routeros", operation
            )
            assert is_supported, f"{operation} should be supported on MikroTik RouterOS"
            assert error_msg == ""


class TestPlatformFileExtensions:
    """Test platform-specific file extension validation."""

    def test_mikrotik_file_extensions(self) -> None:
        """Test MikroTik RouterOS file extensions."""
        extensions = get_platform_file_extensions("mikrotik_routeros")
        assert ".npk" in extensions
        # Should reject .bin files
        assert ".bin" not in extensions

    def test_cisco_file_extensions(self) -> None:
        """Test Cisco platform file extensions."""
        for platform in ["cisco_ios", "cisco_iosxe"]:
            extensions = get_platform_file_extensions(platform)
            assert ".bin" in extensions
            # Should reject .npk files
            assert ".npk" not in extensions

    def test_file_extension_validation_workflow(self) -> None:
        """Test the complete file extension validation workflow."""
        # MikroTik should accept .npk but reject .bin
        assert ".npk" in get_platform_file_extensions("mikrotik_routeros")
        assert ".bin" not in get_platform_file_extensions("mikrotik_routeros")

        # Cisco should accept .bin but reject .npk
        assert ".bin" in get_platform_file_extensions("cisco_ios")
        assert ".npk" not in get_platform_file_extensions("cisco_ios")

        # This simulates the validation that should happen in commands:
        # 1. Get platform from device config
        # 2. Check supported extensions
        # 3. Validate file extension matches
        # 4. Show appropriate error if mismatch

        # Test validation logic
        def validate_firmware_file(device_type: str, filename: str) -> tuple[bool, str]:
            """Simulate the validation logic used in commands."""
            supported_exts = get_platform_file_extensions(device_type)
            file_ext = "." + filename.split(".")[-1]

            if file_ext.lower() not in supported_exts:
                platform_names = {
                    "mikrotik_routeros": "MikroTik RouterOS",
                    "cisco_ios": "Cisco IOS",
                    "cisco_iosxe": "Cisco IOS-XE",
                }
                platform_name = platform_names.get(device_type, device_type)
                ext_list = ", ".join(supported_exts)
                return (
                    False,
                    f"Invalid firmware file for {platform_name}. Expected {ext_list}, got {file_ext}",
                )
            return True, ""

        # Test cases
        valid, msg = validate_firmware_file("mikrotik_routeros", "firmware.npk")
        assert valid

        valid, msg = validate_firmware_file("mikrotik_routeros", "firmware.bin")
        assert not valid
        assert "MikroTik RouterOS" in msg
        assert ".npk" in msg
        assert ".bin" in msg

        valid, msg = validate_firmware_file("cisco_ios", "firmware.bin")
        assert valid

        valid, msg = validate_firmware_file("cisco_ios", "firmware.npk")
        assert not valid
        assert "Cisco IOS" in msg
        assert ".bin" in msg
        assert ".npk" in msg
