"""Tests for platform abstraction layer."""

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from network_toolkit.platforms import (
    UnsupportedOperationError,
    get_platform_operations,
    get_supported_platforms,
    is_platform_supported,
)
from network_toolkit.platforms.base import PlatformOperations


class TestPlatformFactory:
    """Test platform factory functions."""

    def test_get_supported_platforms(self) -> None:
        """Test getting supported platforms list."""
        platforms = get_supported_platforms()

        assert isinstance(platforms, dict)
        assert "mikrotik_routeros" in platforms
        assert "cisco_ios" in platforms
        assert "cisco_iosxe" in platforms
        assert platforms["mikrotik_routeros"] == "MikroTik RouterOS"

    def test_is_platform_supported(self) -> None:
        """Test platform support checking."""
        assert is_platform_supported("mikrotik_routeros") is True
        assert is_platform_supported("cisco_ios") is True
        assert is_platform_supported("cisco_iosxe") is True
        assert is_platform_supported("unsupported_platform") is False

    def test_get_platform_operations_mikrotik(self) -> None:
        """Test getting MikroTik platform operations."""
        # Mock session and config
        mock_session = MagicMock()
        mock_session.device_name = "test_device"
        mock_config = MagicMock()
        mock_device_config = MagicMock()
        mock_device_config.device_type = "mikrotik_routeros"
        mock_config.devices = {"test_device": mock_device_config}
        mock_session.config = mock_config

        # Get platform operations
        platform_ops = get_platform_operations(mock_session)

        # Verify it's the correct platform
        assert platform_ops.get_platform_name() == "MikroTik RouterOS"
        assert "mikrotik_routeros" in platform_ops.get_device_types()
        assert ".npk" in platform_ops.get_supported_file_extensions()

    def test_get_platform_operations_cisco_ios(self) -> None:
        """Test getting Cisco IOS platform operations."""
        # Mock session and config
        mock_session = MagicMock()
        mock_session.device_name = "test_device"
        mock_config = MagicMock()
        mock_device_config = MagicMock()
        mock_device_config.device_type = "cisco_ios"
        mock_config.devices = {"test_device": mock_device_config}
        mock_session.config = mock_config

        # Get platform operations
        platform_ops = get_platform_operations(mock_session)

        # Verify it's the correct platform
        assert platform_ops.get_platform_name() == "Cisco IOS"
        assert "cisco_ios" in platform_ops.get_device_types()

    def test_get_platform_operations_cisco_iosxe(self) -> None:
        """Test getting Cisco IOS-XE platform operations."""
        # Mock session and config
        mock_session = MagicMock()
        mock_session.device_name = "test_device"
        mock_config = MagicMock()
        mock_device_config = MagicMock()
        mock_device_config.device_type = "cisco_iosxe"
        mock_config.devices = {"test_device": mock_device_config}
        mock_session.config = mock_config

        # Get platform operations
        platform_ops = get_platform_operations(mock_session)

        # Verify it's the correct platform
        assert platform_ops.get_platform_name() == "Cisco IOS-XE"
        assert "cisco_iosxe" in platform_ops.get_device_types()

    def test_get_platform_operations_unsupported(self) -> None:
        """Test getting operations for unsupported platform."""
        # Mock session and config
        mock_session = MagicMock()
        mock_session.device_name = "test_device"
        mock_config = MagicMock()
        mock_device_config = MagicMock()
        mock_device_config.device_type = "unsupported_platform"
        mock_config.devices = {"test_device": mock_device_config}
        mock_session.config = mock_config

        # Should raise UnsupportedOperationError
        with pytest.raises(UnsupportedOperationError) as exc_info:
            get_platform_operations(mock_session)

        assert "unsupported_platform" in str(exc_info.value)
        assert "platform_operations" in str(exc_info.value)

    def test_get_platform_operations_device_not_found(self) -> None:
        """Test getting operations when device not in config."""
        # Mock session and config
        mock_session = MagicMock()
        mock_session.device_name = "nonexistent_device"
        mock_config = MagicMock()
        mock_config.devices = {}
        mock_session.config = mock_config

        # Should raise ValueError
        with pytest.raises(ValueError) as exc_info:
            get_platform_operations(mock_session)

        assert "Device 'nonexistent_device' not found" in str(exc_info.value)


class TestPlatformOperationsBase:
    """Test base platform operations interface."""

    def test_is_operation_supported(self) -> None:
        """Test operation support checking."""

        # Create a test implementation
        class TestPlatformOps(PlatformOperations):
            def firmware_upgrade(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def firmware_downgrade(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def bios_upgrade(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def create_backup(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def config_backup(self, *args: Any, **kwargs: Any) -> bool:
                return True

            def backup(self, *args: Any, **kwargs: Any) -> bool:
                return True

            @classmethod
            def get_supported_file_extensions(cls) -> list[str]:
                return [".test"]

            @classmethod
            def get_platform_name(cls) -> str:
                return "Test Platform"

            @classmethod
            def get_device_types(cls) -> list[str]:
                return ["test_platform"]

        mock_session = MagicMock()
        ops = TestPlatformOps(mock_session)

        # These operations should be supported
        assert ops.is_operation_supported("firmware_upgrade") is True
        assert ops.is_operation_supported("firmware_downgrade") is True
        assert ops.is_operation_supported("bios_upgrade") is True
        assert ops.is_operation_supported("create_backup") is True

        # Non-existent operation should not be supported
        assert ops.is_operation_supported("nonexistent_operation") is False


class TestUnsupportedOperationError:
    """Test UnsupportedOperationError exception."""

    def test_exception_creation(self) -> None:
        """Test creating UnsupportedOperationError."""
        platform = "test_platform"
        operation = "test_operation"

        error = UnsupportedOperationError(platform, operation)

        assert error.platform == platform
        assert error.operation == operation
        assert platform in str(error)
        assert operation in str(error)
        assert "not supported" in str(error)
