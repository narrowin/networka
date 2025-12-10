# SPDX-License-Identifier: MIT
"""Cisco IOS platform operations implementation."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError
from network_toolkit.platforms.cisco_ios.constants import (
    DEVICE_TYPES,
    PLATFORM_NAME,
    SUPPORTED_FIRMWARE_EXTENSIONS,
)

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession

logger = logging.getLogger(__name__)


class CiscoIOSOperations(PlatformOperations):
    """Cisco IOS specific operations implementation.

    Implements firmware operations for traditional Cisco IOS using
    monolithic images and boot system commands.
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
        """Upload Cisco IOS firmware and apply it using boot system workflow.

        Implements the Cisco IOS firmware upgrade workflow:
        1. Enable file verification
        2. Transfer firmware using SCP
        3. Verify integrity if requested
        4. Configure boot system with new image
        5. Save configuration and reload

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local firmware file (.bin or .tar)
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
        if not self.session._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate firmware file extension
        if local_firmware_path.suffix.lower() not in SUPPORTED_FIRMWARE_EXTENSIONS:
            expected_exts = ", ".join(SUPPORTED_FIRMWARE_EXTENSIONS)
            msg = f"Invalid firmware file for Cisco IOS. Expected {expected_exts}, got {local_firmware_path.suffix}"
            raise ValueError(msg)

        # Validate local firmware file
        if not local_firmware_path.exists():
            msg = f"Firmware file not found: {local_firmware_path}"
            raise FileNotFoundError(msg)

        if not local_firmware_path.is_file():
            msg = f"Path is not a file: {local_firmware_path}"
            raise FileNotFoundError(msg)

        # Determine remote filename
        remote_name = remote_filename or local_firmware_path.name

        logger.warning(
            f"🚨 CISCO IOS FIRMWARE UPGRADE INITIATED on {self.session.device_name}!"
        )
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning("   This will RELOAD the device!")

        try:
            # Step 1: Enable file verification
            logger.info("Step 1/5: Enabling file verification")
            try:
                self.session.execute_command("file verify auto")
                logger.info("OK File verification enabled")
            except DeviceExecutionError as e:
                logger.warning(f"Could not enable file verification: {e}")

            # Step 2: Check current state and flash space
            logger.info("Step 2/5: Checking device state and flash space")
            try:
                version_output = self.session.execute_command("show version")
                logger.debug(f"Current version: {version_output}")

                boot_output = self.session.execute_command("show boot")
                logger.debug(f"Current boot config: {boot_output}")

                flash_output = self.session.execute_command("dir flash:")
                logger.debug(f"Flash contents: {flash_output}")

            except DeviceExecutionError as e:
                logger.warning(f"Could not check device state: {e}")

            # Step 3: Upload the firmware file
            logger.info(f"Step 3/5: Uploading firmware file {local_firmware_path.name}")
            upload_success = self.session.upload_file(
                local_path=local_firmware_path,
                remote_filename=remote_filename,
                verify_upload=verify_upload,
                verify_checksum=verify_checksum,
            )

            if not upload_success:
                msg = f"Firmware file upload failed to {self.session.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"reason": "Upload verification failed"},
                )

            logger.info("OK Firmware file uploaded successfully")

            # Step 4: Configure boot system for new firmware
            logger.info("Step 4/5: Configuring boot system")
            try:
                # Configure boot system using monolithic image workflow
                config_commands = [
                    "configure terminal",
                    "no boot system",  # Clear existing boot commands
                    f"boot system flash:{remote_name}",  # Set new primary boot image
                    "end",
                    "write memory",  # Save configuration
                ]

                for cmd in config_commands:
                    logger.debug(f"Executing: {cmd}")
                    result = self.session.execute_command(cmd)
                    logger.debug(f"Result: {result}")

                logger.info("OK Boot system configured")

            except DeviceExecutionError as e:
                msg = f"Failed to configure boot system: {e}"
                raise DeviceExecutionError(msg) from e

            # Step 5: Reload the device
            logger.warning(f"Step 5/5: Reloading device in {pre_reboot_delay}s...")
            logger.warning("🚨 DEVICE WILL LOSE CONNECTION AND RELOAD! 🚨")

            time.sleep(pre_reboot_delay)

            try:
                logger.info("Sending reload command...")
                response = self.session._transport.send_interactive(  # type: ignore[union-attr]
                    interact_events=[
                        (
                            "reload",
                            "Proceed with reload? [confirm]",
                            True,
                        ),
                        (
                            "",  # Just press enter to confirm
                            "",
                            False,
                        ),
                    ],
                    timeout_ops=confirmation_timeout,
                )

                logger.info(f"Reload command executed: {response}")
                logger.warning("🚨 CISCO IOS DEVICE RELOADING WITH NEW FIRMWARE!")

                self.session._connected = False
                return True

            except Exception as e:
                # Device might disconnect immediately, which is expected
                error_str = str(e).lower()
                if any(
                    phrase in error_str
                    for phrase in [
                        "connection",
                        "disconnect",
                        "timeout",
                        "closed",
                        "eof",
                    ]
                ):
                    logger.info(f"Device disconnected during reload (expected): {e}")
                    logger.warning("🚨 CISCO IOS DEVICE RELOADING WITH NEW FIRMWARE!")
                    self.session._connected = False
                    return True
                else:
                    logger.error(f"Unexpected error during reload: {e}")
                    msg = f"Reload command failed: {e}"
                    raise DeviceConnectionError(msg) from e

        except Exception as e:
            logger.error(f"Cisco IOS firmware upgrade failed: {e}")
            raise

    def firmware_downgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Downgrade Cisco IOS firmware using same workflow as upgrade.

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local firmware file (older version)
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
        # Downgrade uses the same process as upgrade for IOS
        logger.info("Initiating Cisco IOS firmware downgrade (same process as upgrade)")
        return self.firmware_upgrade(
            local_firmware_path=local_firmware_path,
            remote_filename=remote_filename,
            verify_upload=verify_upload,
            verify_checksum=verify_checksum,
            pre_reboot_delay=3.0,
            confirmation_timeout=confirmation_timeout,
        )

    def bios_upgrade(
        self,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
        verify_before: bool = True,
    ) -> bool:
        """BIOS upgrade is not applicable for Cisco IOS devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "bios_upgrade")

    def create_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create Cisco IOS device backup using platform-specific commands.

        Parameters
        ----------
        backup_sequence : list[str]
            List of Cisco IOS commands to execute for backup
        download_files : list[dict[str, str]] | None
            Optional list of files to download after backup

        Returns
        -------
        bool
            True if backup was created successfully
        """
        if not self.session.is_connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Use provided sequence or fall back to default IOS backup sequence
        if not backup_sequence:
            backup_sequence = ["show running-config"]

        logger.info(f"Creating Cisco IOS backup on {self.session.device_name}")

        try:
            # Execute backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info("OK Cisco IOS backup commands executed successfully")
            return True

        except DeviceExecutionError as e:
            logger.error(f"Cisco IOS backup failed: {e}")
            raise

    def config_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create Cisco IOS configuration backup using platform-specific commands.

        This operation creates a text representation of the Cisco IOS configuration
        using show commands.

        Parameters
        ----------
        backup_sequence : list[str]
            List of Cisco IOS commands to execute for configuration backup
        download_files : list[dict[str, str]] | None
            Optional list of files to download after backup

        Returns
        -------
        bool
            True if configuration backup was created successfully
        """
        if not self.session.is_connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Use provided sequence or fall back to default config backup
        if not backup_sequence:
            backup_sequence = ["show running-config"]

        logger.info(
            f"Creating Cisco IOS configuration backup on {self.session.device_name}"
        )

        try:
            # Execute configuration backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing config backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info(
                "OK Cisco IOS configuration backup commands executed successfully"
            )
            return True

        except DeviceExecutionError as e:
            logger.error(f"Cisco IOS configuration backup failed: {e}")
            raise

    def backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create comprehensive Cisco IOS backup using platform-specific commands.

        This operation creates both configuration and system information backups
        of the Cisco IOS device.

        Parameters
        ----------
        backup_sequence : list[str]
            List of Cisco IOS commands to execute for comprehensive backup
        download_files : list[dict[str, str]] | None
            Optional list of files to download after backup

        Returns
        -------
        bool
            True if comprehensive backup was created successfully
        """
        if not self.session.is_connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Use provided sequence or fall back to comprehensive backup
        if not backup_sequence:
            backup_sequence = [
                "show running-config",
                "show startup-config",
                "show version",
                "show inventory",
            ]

        logger.info(
            f"Creating comprehensive Cisco IOS backup on {self.session.device_name}"
        )

        try:
            # Execute comprehensive backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info(
                "OK Cisco IOS comprehensive backup commands executed successfully"
            )
            return True

        except DeviceExecutionError as e:
            logger.error(f"Cisco IOS comprehensive backup failed: {e}")
            raise

    @classmethod
    def get_supported_file_extensions(cls) -> list[str]:
        """Get list of supported firmware file extensions for Cisco IOS."""
        return SUPPORTED_FIRMWARE_EXTENSIONS.copy()

    @classmethod
    def get_platform_name(cls) -> str:
        """Get human-readable platform name."""
        return PLATFORM_NAME

    @classmethod
    def get_device_types(cls) -> list[str]:
        """Get list of device types supported by this platform."""
        return DEVICE_TYPES.copy()
