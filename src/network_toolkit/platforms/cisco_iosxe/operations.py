# SPDX-License-Identifier: MIT
"""Cisco IOS-XE platform operations implementation."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
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
    """Cisco IOS-XE specific operations implementation.

    Implements firmware operations for Cisco IOS-XE using INSTALL mode
    with package management for proper rollback support.
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
        """Upload Cisco IOS-XE firmware and apply it using INSTALL mode workflow.

        Implements the Cisco IOS-XE INSTALL mode firmware upgrade workflow:
        1. Enable file verification
        2. Check if device is in INSTALL mode
        3. Transfer firmware using SCP
        4. Verify integrity if requested
        5. Use install add/activate/commit commands
        6. Keep inactive packages for rollback

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local firmware file (.bin or .pkg)
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
            msg = f"Invalid firmware file for Cisco IOS-XE. Expected {expected_exts}, got {local_firmware_path.suffix}"
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
            f"🚨 CISCO IOS-XE FIRMWARE UPGRADE INITIATED on {self.session.device_name}!"
        )
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning("   Using INSTALL mode with package management")
        logger.warning("   This will RELOAD the device!")

        try:
            # Step 1: Enable file verification
            logger.info("Step 1/6: Enabling file verification")
            try:
                self.session.execute_command("file verify auto")
                logger.info("OK File verification enabled")
            except DeviceExecutionError as e:
                logger.warning(f"Could not enable file verification: {e}")

            # Step 2: Check device mode and state
            logger.info("Step 2/6: Checking device mode and state")
            is_install_mode = False
            try:
                version_output = self.session.execute_command("show version")
                logger.debug(f"Current version: {version_output}")

                # Check if device supports and is in INSTALL mode
                try:
                    install_output = self.session.execute_command(
                        "show install summary"
                    )
                    logger.debug(f"Install summary: {install_output}")
                    is_install_mode = True
                    logger.info("OK Device is in INSTALL mode")
                except DeviceExecutionError:
                    logger.warning(
                        "Device is in BUNDLE mode or install commands not available"
                    )
                    is_install_mode = False

                boot_output = self.session.execute_command("show boot")
                logger.debug(f"Current boot config: {boot_output}")

                flash_output = self.session.execute_command("dir flash:")
                logger.debug(f"Flash contents: {flash_output}")

            except DeviceExecutionError as e:
                logger.warning(f"Could not check device state: {e}")

            # Step 3: Upload the firmware file
            logger.info(f"Step 3/6: Uploading firmware file {local_firmware_path.name}")
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

            # Step 4: Apply firmware based on device mode
            if is_install_mode:
                # Use INSTALL mode commands (preferred for IOS-XE)
                logger.info("Step 4/6: Using IOS-XE INSTALL mode workflow")

                # Step 4a: Add the image
                logger.info("Step 4a/6: Adding firmware package")
                try:
                    add_cmd = f"install add file flash:{remote_name}"
                    logger.info(f"Executing: {add_cmd}")
                    add_result = self.session.execute_command(add_cmd)
                    logger.info(f"Add command result: {add_result}")

                except DeviceExecutionError as e:
                    msg = f"Failed to add firmware package: {e}"
                    raise DeviceExecutionError(msg) from e

                # Step 4b: Activate and commit (this will reload)
                logger.warning(
                    "Step 4b/6: Activating and committing firmware (device will reload)"
                )
                logger.warning(f"Waiting {pre_reboot_delay}s before activation...")
                time.sleep(pre_reboot_delay)

                try:
                    activate_cmd = f"install activate file flash:{remote_name}"
                    logger.warning(f"Executing: {activate_cmd}")
                    logger.warning("This will reload the device immediately!")

                    activate_result = self.session.execute_command(activate_cmd)
                    logger.info(f"Activate command result: {activate_result}")

                    # Device should reload automatically after activation
                    self.session._connected = False
                    logger.warning(
                        "🚨 CISCO IOS-XE DEVICE RELOADING WITH NEW FIRMWARE!"
                    )
                    logger.info(
                        "Note: Use 'install commit' after verifying the upgrade"
                    )
                    logger.info("Note: Use 'install rollback' to revert if needed")
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
                        logger.info(
                            f"Device disconnected during activation (expected): {e}"
                        )
                        logger.warning(
                            "🚨 CISCO IOS-XE DEVICE RELOADING WITH NEW FIRMWARE!"
                        )
                        self.session._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during activation: {e}")
                        msg = f"Install activate command failed: {e}"
                        raise DeviceExecutionError(msg) from e

            else:
                # Fall back to traditional boot system method for BUNDLE mode
                logger.warning(
                    "Step 4/6: Device in BUNDLE mode, using traditional boot system"
                )
                try:
                    config_commands = [
                        "configure terminal",
                        "no boot system",
                        f"boot system flash:{remote_name}",
                        "end",
                        "write memory",
                    ]

                    for cmd in config_commands:
                        logger.debug(f"Executing: {cmd}")
                        result = self.session.execute_command(cmd)
                        logger.debug(f"Result: {result}")

                    logger.info("OK Boot system configured")

                except DeviceExecutionError as e:
                    msg = f"Failed to configure boot system: {e}"
                    raise DeviceExecutionError(msg) from e

                # Step 5: Reload the device (only for BUNDLE mode)
                logger.warning(f"Step 5/6: Reloading device in {pre_reboot_delay}s...")
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
                    logger.warning(
                        "🚨 CISCO IOS-XE DEVICE RELOADING WITH NEW FIRMWARE!"
                    )

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
                        logger.info(
                            f"Device disconnected during reload (expected): {e}"
                        )
                        logger.warning(
                            "🚨 CISCO IOS-XE DEVICE RELOADING WITH NEW FIRMWARE!"
                        )
                        self.session._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during reload: {e}")
                        msg = f"Reload command failed: {e}"
                        raise DeviceConnectionError(msg) from e

        except Exception as e:
            logger.error(f"Cisco IOS-XE firmware upgrade failed: {e}")
            raise

    def firmware_downgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Downgrade Cisco IOS-XE firmware using INSTALL mode rollback or upgrade workflow.

        For IOS-XE INSTALL mode, will attempt to use install rollback if previous
        version is available, otherwise falls back to standard upgrade workflow.

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
        logger.info("Initiating Cisco IOS-XE firmware downgrade")

        # Check if we can use install rollback
        try:
            if self.session._connected:
                install_output = self.session.execute_command("show install summary")
                logger.debug(f"Install summary: {install_output}")

                # Check if there's a previous version to rollback to
                if "Inactive" in install_output or "Rollback" in install_output:
                    logger.info(
                        "Previous version available, attempting install rollback"
                    )
                    try:
                        rollback_cmd = "install rollback to previous"
                        logger.warning(f"Executing: {rollback_cmd}")
                        logger.warning("This will reload the device!")

                        rollback_result = self.session.execute_command(rollback_cmd)
                        logger.info(f"Rollback command result: {rollback_result}")

                        self.session._connected = False
                        logger.warning(
                            "🚨 CISCO IOS-XE DEVICE ROLLING BACK TO PREVIOUS VERSION!"
                        )
                        return True

                    except Exception as e:
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
                            logger.info(
                                f"Device disconnected during rollback (expected): {e}"
                            )
                            logger.warning(
                                "🚨 CISCO IOS-XE DEVICE ROLLING BACK TO PREVIOUS VERSION!"
                            )
                            self.session._connected = False
                            return True
                        else:
                            logger.warning(f"Install rollback failed: {e}")
                            logger.info("Falling back to standard upgrade workflow")

        except DeviceExecutionError:
            logger.info(
                "Install commands not available, using standard upgrade workflow"
            )

        # Fall back to standard upgrade workflow with older firmware
        logger.info("Using standard upgrade workflow for downgrade")
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
        """BIOS upgrade is not applicable for Cisco IOS-XE devices."""
        raise UnsupportedOperationError(PLATFORM_NAME, "bios_upgrade")

    def create_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create backup is not yet implemented for Cisco IOS-XE devices."""
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
