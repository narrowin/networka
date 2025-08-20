# SPDX-License-Identifier: MIT
"""Base platform abstraction classes for network device operations."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession


class PlatformOperations(ABC):
    """Abstract base class for platform-specific operations.

    Each platform must implement these methods to provide vendor-specific
    implementations of common network operations.
    """

    def __init__(self, session: DeviceSession) -> None:
        """Initialize platform operations with device session.

        Parameters
        ----------
        session : DeviceSession
            Active device session for executing commands
        """
        self.session = session

    @abstractmethod
    def firmware_upgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Upload firmware package and reboot device to apply it.

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local firmware file
        remote_filename : str | None
            Remote filename (default: same as local file)
        verify_upload : bool
            Verify file was uploaded successfully
        verify_checksum : bool
            Verify file integrity using checksums
        pre_reboot_delay : float
            Delay in seconds before rebooting
        confirmation_timeout : float
            Timeout for confirmation prompts

        Returns
        -------
        bool
            True if upgrade was initiated successfully
        """
        ...

    @abstractmethod
    def firmware_downgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Upload older firmware package and schedule downgrade.

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local firmware file
        remote_filename : str | None
            Remote filename (default: same as local file)
        verify_upload : bool
            Verify file was uploaded successfully
        verify_checksum : bool
            Verify file integrity using checksums
        confirmation_timeout : float
            Timeout for confirmation prompts

        Returns
        -------
        bool
            True if downgrade was initiated successfully
        """
        ...

    @abstractmethod
    def bios_upgrade(
        self,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
        verify_before: bool = True,
    ) -> bool:
        """Upgrade device BIOS/RouterBOOT and reboot to apply.

        Parameters
        ----------
        pre_reboot_delay : float
            Delay in seconds before rebooting
        confirmation_timeout : float
            Timeout for confirmation prompts
        verify_before : bool
            Verify current status before upgrade

        Returns
        -------
        bool
            True if BIOS upgrade was initiated successfully
        """
        ...

    @abstractmethod
    def create_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create device backup using platform-specific commands.

        Parameters
        ----------
        backup_sequence : list[str]
            List of commands to execute for backup
        download_files : list[dict[str, str]] | None
            Optional list of files to download after backup

        Returns
        -------
        bool
            True if backup was created successfully
        """
        ...

    @classmethod
    @abstractmethod
    def get_supported_file_extensions(cls) -> list[str]:
        """Get list of supported firmware file extensions for this platform.

        Returns
        -------
        list[str]
            List of supported file extensions (e.g., ['.npk', '.pkg'])
        """
        ...

    @classmethod
    @abstractmethod
    def get_platform_name(cls) -> str:
        """Get human-readable platform name.

        Returns
        -------
        str
            Platform name (e.g., 'MikroTik RouterOS')
        """
        ...

    @classmethod
    @abstractmethod
    def get_device_types(cls) -> list[str]:
        """Get list of device types supported by this platform.

        Returns
        -------
        list[str]
            List of supported device types
        """
        ...

    def is_operation_supported(self, operation: str) -> bool:
        """Check if an operation is supported by this platform.

        Parameters
        ----------
        operation : str
            Operation name ('firmware_upgrade', 'bios_upgrade', etc.)

        Returns
        -------
        bool
            True if operation is supported
        """
        # Default implementation checks if method exists and is not abstract
        if not hasattr(self, operation):
            return False

        method = getattr(self, operation)
        return callable(method) and not getattr(method, "__isabstractmethod__", False)


class UnsupportedOperationError(Exception):
    """Raised when an operation is not supported by a platform."""

    def __init__(self, platform: str, operation: str) -> None:
        """Initialize with platform and operation details.

        Parameters
        ----------
        platform : str
            Platform name
        operation : str
            Operation that is not supported
        """
        self.platform = platform
        self.operation = operation
        super().__init__(
            f"Operation '{operation}' is not supported on platform '{platform}'"
        )
