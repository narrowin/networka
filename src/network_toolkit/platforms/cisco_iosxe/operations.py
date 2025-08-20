# SPDX-License-Identifier: MIT
"""Cisco IOS-XE platform operations implementation (stub)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError
from network_toolkit.platforms.cisco_iosxe.constants import (
    DEVICE_TYPES,
    PLATFORM_NAME,
    SUPPORTED_FIRMWARE_EXTENSIONS,
)

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession

logger = logging.getLogger(__name__)


class CiscoIOSXEOperations(PlatformOperations):
    """Cisco IOS-XE specific operations implementation (stub).

    These operations are not yet implemented for Cisco IOS-XE devices.
    This class serves as a placeholder and will raise UnsupportedOperationError
    for all operations until they are implemented.
    """

    def firmware_upgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Firmware upgrade is not yet implemented for Cisco IOS-XE devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "firmware_upgrade")

    def firmware_downgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Firmware downgrade is not yet implemented for Cisco IOS-XE devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "firmware_downgrade")

    def bios_upgrade(
        self,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
        verify_before: bool = True,
    ) -> bool:
        """BIOS upgrade is not yet implemented for Cisco IOS-XE devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "bios_upgrade")

    def create_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Backup creation is not yet implemented for Cisco IOS-XE devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "create_backup")

    @classmethod
    def get_supported_file_extensions(cls) -> list[str]:
        """Get list of supported firmware file extensions for Cisco IOS-XE."""
        return SUPPORTED_FIRMWARE_EXTENSIONS.copy()

    @classmethod
    def get_platform_name(cls) -> str:
        """Get human-readable platform name."""
        return PLATFORM_NAME

    @classmethod
    def get_device_types(cls) -> list[str]:
        """Get list of device types supported by this platform."""
        return DEVICE_TYPES.copy()
