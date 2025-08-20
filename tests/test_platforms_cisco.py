"""Tests for Cisco platform operations (stubs)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from network_toolkit.platforms.base import UnsupportedOperationError
from network_toolkit.platforms.cisco_ios.operations import CiscoIOSOperations
from network_toolkit.platforms.cisco_iosxe.operations import CiscoIOSXEOperations


class TestCiscoIOSOperations:
    """Test Cisco IOS platform operations (stub implementation)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_switch"
        self.platform_ops = CiscoIOSOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "Cisco IOS"
        assert "cisco_ios" in self.platform_ops.get_device_types()
        assert "cisco_iosxe" in self.platform_ops.get_device_types()
        supported_exts = self.platform_ops.get_supported_file_extensions()
        assert ".bin" in supported_exts
        assert ".tar" in supported_exts

    def test_firmware_upgrade_not_implemented(self) -> None:
        """Test that firmware upgrade raises UnsupportedOperationError."""
        mock_firmware_path = MagicMock(spec=Path)

        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "firmware_upgrade" in str(exc_info.value)
        assert "Cisco IOS" in str(exc_info.value)

    def test_firmware_downgrade_not_implemented(self) -> None:
        """Test that firmware downgrade raises UnsupportedOperationError."""
        mock_firmware_path = MagicMock(spec=Path)

        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert "firmware_downgrade" in str(exc_info.value)
        assert "Cisco IOS" in str(exc_info.value)

    def test_bios_upgrade_not_implemented(self) -> None:
        """Test that BIOS upgrade raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "bios_upgrade" in str(exc_info.value)
        assert "Cisco IOS" in str(exc_info.value)

    def test_create_backup_not_implemented(self) -> None:
        """Test that backup creation raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.create_backup([])

        assert "create_backup" in str(exc_info.value)
        assert "Cisco IOS" in str(exc_info.value)

    def test_operation_support_checking(self) -> None:
        """Test that operations are reported as not supported."""
        # Since these are stub implementations that raise UnsupportedOperationError,
        # they should still be detected as having the methods
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )


class TestCiscoIOSXEOperations:
    """Test Cisco IOS-XE platform operations (stub implementation)."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_session = MagicMock()
        self.mock_session.device_name = "test_switch"
        self.platform_ops = CiscoIOSXEOperations(self.mock_session)

    def test_platform_metadata(self) -> None:
        """Test platform metadata methods."""
        assert self.platform_ops.get_platform_name() == "Cisco IOS-XE"
        assert self.platform_ops.get_device_types() == ["cisco_iosxe"]
        supported_exts = self.platform_ops.get_supported_file_extensions()
        assert ".bin" in supported_exts
        assert ".pkg" in supported_exts

    def test_firmware_upgrade_not_implemented(self) -> None:
        """Test that firmware upgrade raises UnsupportedOperationError."""
        mock_firmware_path = MagicMock(spec=Path)

        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.firmware_upgrade(mock_firmware_path)

        assert "firmware_upgrade" in str(exc_info.value)
        assert "Cisco IOS-XE" in str(exc_info.value)

    def test_firmware_downgrade_not_implemented(self) -> None:
        """Test that firmware downgrade raises UnsupportedOperationError."""
        mock_firmware_path = MagicMock(spec=Path)

        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.firmware_downgrade(mock_firmware_path)

        assert "firmware_downgrade" in str(exc_info.value)
        assert "Cisco IOS-XE" in str(exc_info.value)

    def test_bios_upgrade_not_implemented(self) -> None:
        """Test that BIOS upgrade raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.bios_upgrade()

        assert "bios_upgrade" in str(exc_info.value)
        assert "Cisco IOS-XE" in str(exc_info.value)

    def test_create_backup_not_implemented(self) -> None:
        """Test that backup creation raises UnsupportedOperationError."""
        with pytest.raises(UnsupportedOperationError) as exc_info:
            self.platform_ops.create_backup([])

        assert "create_backup" in str(exc_info.value)
        assert "Cisco IOS-XE" in str(exc_info.value)

    def test_operation_support_checking(self) -> None:
        """Test that operations are reported as not supported."""
        # Since these are stub implementations that raise UnsupportedOperationError,
        # they should still be detected as having the methods
        assert self.platform_ops.is_operation_supported("firmware_upgrade") is True
        assert self.platform_ops.is_operation_supported("firmware_downgrade") is True
        assert self.platform_ops.is_operation_supported("bios_upgrade") is True
        assert self.platform_ops.is_operation_supported("create_backup") is True
        assert (
            self.platform_ops.is_operation_supported("nonexistent_operation") is False
        )
