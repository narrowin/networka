# SPDX-License-Identifier: MIT
"""MikroTik RouterOS platform operations implementation."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

from network_toolkit.exceptions import DeviceConnectionError, DeviceExecutionError
from network_toolkit.platforms.base import PlatformOperations
from network_toolkit.platforms.mikrotik_routeros.constants import (
    DEFAULT_BACKUP_DOWNLOADS,
    DEFAULT_BACKUP_SEQUENCE,
    DEVICE_TYPES,
    PLATFORM_NAME,
    SUPPORTED_FIRMWARE_EXTENSIONS,
)

if TYPE_CHECKING:
    from network_toolkit.device import DeviceSession

logger = logging.getLogger(__name__)


class MikroTikRouterOSOperations(PlatformOperations):
    """MikroTik RouterOS specific operations implementation."""

    def firmware_upgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Upload RouterOS firmware package and reboot device to apply it.

        This is the existing implementation extracted from DeviceSession.upload_firmware_and_reboot
        """
        if not self.session._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate firmware file extension
        if local_firmware_path.suffix.lower() not in SUPPORTED_FIRMWARE_EXTENSIONS:
            expected_exts = ", ".join(SUPPORTED_FIRMWARE_EXTENSIONS)
            msg = f"Invalid firmware file for RouterOS. Expected {expected_exts}, got {local_firmware_path.suffix}"
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
            f"🚨 NUCLEAR FIRMWARE DEPLOYMENT INITIATED on {self.session.device_name}!"
        )
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning("   This will REBOOT the device!")

        try:
            # Step 1: Upload the firmware file
            logger.info(f"Step 1/3: Uploading firmware file {local_firmware_path.name}")
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

            # Step 2: Optional verification of packages
            logger.info("Step 2/3: Verifying firmware packages (optional)")
            try:
                package_result = self.session.execute_command("/system/package/print")
                logger.debug(f"Current packages: {package_result}")
            except DeviceExecutionError as e:
                logger.warning(f"Could not verify packages (non-critical): {e}")

            # Step 3: Nuclear reboot (firmware applied during boot)
            logger.warning(
                f"Step 3/3: Rebooting in {pre_reboot_delay}s to apply firmware..."
            )
            logger.warning("🚨 DEVICE WILL LOSE CONNECTION AND REBOOT! 🚨")

            # Give operator a moment to panic and Ctrl+C if needed
            time.sleep(pre_reboot_delay)

            # Send the reboot command and handle the confirmation prompt
            logger.info("Sending reboot command...")

            try:
                logger.info("Executing reboot command with automatic confirmation...")
                try:
                    logger.debug("Sending reboot command: /system/reboot")
                    response = self.session._transport.send_interactive(  # type: ignore[union-attr]
                        interact_events=[
                            (
                                "/system/reboot",
                                "Reboot? [y/N]:",
                                True,
                            ),
                            (
                                "y",
                                "",
                                False,
                            ),  # Send 'y' and don't expect a response (device reboots)
                        ],
                        timeout_ops=confirmation_timeout,
                    )

                    logger.info(
                        f"Interactive reboot command completed. Response: {response!r}"
                    )

                    logger.warning("🚨 NUCLEAR REBOOT EXECUTED! Device is rebooting...")
                    logger.warning("🔄 Firmware will be applied during boot process...")
                    logger.warning(
                        "⏰ Boot process may take 2-5 minutes with firmware update"
                    )
                    logger.info("OK Firmware deployment command executed successfully")

                    # Mark as disconnected since device is rebooting
                    self.session._connected = False
                    return True

                except Exception as e:
                    # The device might disconnect immediately after confirmation, which is expected
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
                            f"Device disconnected during reboot (expected): {e}"
                        )
                        logger.warning(
                            "🚨 NUCLEAR REBOOT EXECUTED! Device is rebooting..."
                        )
                        logger.warning(
                            "🔄 Firmware will be applied during boot process..."
                        )
                        logger.warning(
                            "⏰ Boot process may take 2-5 minutes with firmware update"
                        )

                        # Mark as disconnected
                        self.session._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during reboot: {e}")
                        msg = f"Reboot command failed: {e}"
                        raise DeviceConnectionError(msg) from e

            except Exception as e:
                # The device might disconnect immediately, which is expected for reboot
                if any(
                    phrase in str(e).lower()
                    for phrase in ["connection", "disconnect", "timeout", "closed"]
                ):
                    logger.info(f"Device disconnected during reboot (expected): {e}")
                    logger.warning(
                        "🚨 NUCLEAR REBOOT LIKELY EXECUTED! Device is rebooting..."
                    )
                    logger.warning("🔄 Firmware will be applied during boot process...")
                    logger.warning(
                        "⏰ Boot process may take 2-5 minutes with firmware update"
                    )

                    # Mark as disconnected
                    self.session._connected = False
                    return True
                else:
                    logger.error(f"Unexpected error during reboot: {e}")
                    msg = f"Reboot command failed: {e}"
                    raise DeviceConnectionError(msg) from e

        except Exception as e:
            logger.error(f"Nuclear firmware deployment failed: {e}")
            if isinstance(
                e,
                DeviceConnectionError
                | DeviceExecutionError
                | FileNotFoundError
                | ValueError,
            ):
                raise
            else:
                msg = (
                    f"Nuclear firmware deployment failed on {self.session.device_name}"
                )
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def firmware_downgrade(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """Upload older RouterOS firmware package and schedule downgrade.

        This is the existing implementation from DeviceSession.downgrade_firmware_and_reboot
        """
        if not self.session._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate firmware file extension
        if local_firmware_path.suffix.lower() not in SUPPORTED_FIRMWARE_EXTENSIONS:
            expected_exts = ", ".join(SUPPORTED_FIRMWARE_EXTENSIONS)
            msg = f"Invalid firmware file for RouterOS. Expected {expected_exts}, got {local_firmware_path.suffix}"
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
            f"🚨 FIRMWARE DOWNGRADE INITIATED on {self.session.device_name}!"
        )
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning("   This will REBOOT the device!")

        try:
            # Step 1: Upload the firmware file
            logger.info(f"Step 1/4: Uploading firmware file {local_firmware_path.name}")
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

            # Step 2: Optional verification of packages
            logger.info("Step 2/4: Verifying firmware packages (optional)")
            try:
                package_result = self.session.execute_command("/system/package/print")
                logger.debug(f"Current packages: {package_result}")
            except DeviceExecutionError as e:
                logger.warning(f"Could not verify packages (non-critical): {e}")

            # Step 3: Schedule downgrade with interactive confirmation
            logger.info(
                "Step 3/4: Scheduling downgrade via '/system package downgrade'"
            )
            try:
                logger.info(
                    "Executing downgrade command with automatic confirmation..."
                )
                try:
                    logger.debug("Sending downgrade command: /system/package/downgrade")
                    response = self.session._transport.send_interactive(  # type: ignore[union-attr]
                        interact_events=[
                            (
                                "/system/package/downgrade",
                                "Router will be rebooted. Continue? [y/N]:",
                                True,
                            ),
                            ("y", "", False),
                        ],
                        timeout_ops=confirmation_timeout,
                    )

                    logger.info(f"Downgrade command response: {response!r}")
                    logger.warning("🚨 DOWNGRADE SCHEDULED! Device is rebooting...")
                    logger.warning("🔄 Older firmware will be applied during boot...")
                    logger.warning("⏰ Boot process may take 2-5 minutes")
                    logger.info("OK Firmware downgrade command executed successfully")

                    # Mark as disconnected since device is rebooting
                    self.session._connected = False
                    return True

                except Exception as e:
                    # The device might disconnect immediately after confirmation, which is expected
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
                            f"Device disconnected during downgrade (expected): {e}"
                        )
                        logger.warning("🚨 DOWNGRADE SCHEDULED! Device is rebooting...")
                        logger.warning(
                            "🔄 Older firmware will be applied during boot..."
                        )

                        # Mark as disconnected
                        self.session._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during downgrade: {e}")
                        msg = f"Downgrade command failed: {e}"
                        raise DeviceExecutionError(msg) from e

            except Exception as e:
                logger.error(f"Firmware downgrade command failed: {e}")
                msg = f"Firmware downgrade failed on {self.session.device_name}"
                raise DeviceExecutionError(msg) from e

        except Exception as e:
            logger.error(f"Firmware downgrade failed: {e}")
            if isinstance(
                e,
                DeviceConnectionError
                | DeviceExecutionError
                | FileNotFoundError
                | ValueError,
            ):
                raise
            else:
                msg = f"Firmware downgrade failed on {self.session.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def bios_upgrade(
        self,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
        verify_before: bool = True,
    ) -> bool:
        """Upgrade RouterBOARD (RouterBOOT/BIOS) and reboot to apply.

        This is the existing implementation from DeviceSession.routerboard_upgrade_and_reboot
        """
        if not self.session._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        try:
            if verify_before:
                try:
                    info = self.session.execute_command("/system/routerboard/print")
                    logger.debug(f"RouterBOARD status before upgrade: {info}")
                except DeviceExecutionError as e:
                    logger.warning(
                        f"Could not fetch RouterBOARD status (non-critical): {e}"
                    )

            logger.info("Issuing RouterBOARD upgrade command...")
            # RouterOS accepts both '/system routerboard upgrade' and with slashes
            # This command requires interactive confirmation
            try:
                logger.debug("Sending upgrade command with automatic confirmation...")
                upgrade_resp = self.session._transport.send_interactive(  # type: ignore[union-attr]
                    interact_events=[
                        (
                            "/system/routerboard/upgrade",
                            "Do you really want to upgrade firmware? [y/n]",
                            True,
                        ),
                        ("y", "", False),
                    ],
                    timeout_ops=confirmation_timeout,
                )
                logger.debug(f"RouterBOARD upgrade response: {upgrade_resp}")
                logger.info("✅ RouterBOARD upgrade scheduled (requires reboot)")
            except Exception as e:
                logger.error(f"RouterBOARD upgrade command failed: {e}")
                error_msg = f"RouterBOARD upgrade failed: {e}"
                raise DeviceExecutionError(error_msg) from e

            logger.warning(
                f"Rebooting in {pre_reboot_delay}s to apply RouterBOARD upgrade..."
            )
            logger.warning("🚨 DEVICE WILL LOSE CONNECTION AND REBOOT! 🚨")
            time.sleep(pre_reboot_delay)

            logger.info("Sending reboot command...")
            try:
                logger.info("Executing reboot command with automatic confirmation...")
                try:
                    logger.debug("Sending reboot command: /system/reboot")
                    response = self.session._transport.send_interactive(  # type: ignore[union-attr]
                        interact_events=[
                            (
                                "/system/reboot",
                                "Reboot? [y/N]:",
                                True,
                            ),
                            ("y", "", False),
                        ],
                        timeout_ops=confirmation_timeout,
                    )

                    logger.info(f"Reboot response: {response!r}")
                    logger.warning("🚨 RouterBOARD UPGRADE REBOOT EXECUTED!")
                    logger.warning("🔄 RouterBOOT/BIOS will be upgraded during boot...")
                    logger.warning(
                        "⏰ Boot process may take 3-10 minutes for BIOS upgrade"
                    )
                    logger.info("OK RouterBOARD upgrade initiated successfully")

                    # Mark as disconnected since device is rebooting
                    self.session._connected = False
                    return True

                except Exception as e:
                    # The device might disconnect immediately after confirmation
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
                            f"Device disconnected during reboot (expected): {e}"
                        )
                        logger.warning("🚨 RouterBOARD UPGRADE REBOOT EXECUTED!")
                        logger.warning(
                            "🔄 RouterBOOT/BIOS will be upgraded during boot..."
                        )

                        # Mark as disconnected
                        self.session._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during reboot: {e}")
                        msg = f"Reboot command failed: {e}"
                        raise DeviceConnectionError(msg) from e

            except Exception as e:
                if any(
                    phrase in str(e).lower()
                    for phrase in ["connection", "disconnect", "timeout", "closed"]
                ):
                    logger.info(f"Device disconnected during reboot (expected): {e}")
                    logger.warning("🚨 RouterBOARD UPGRADE REBOOT LIKELY EXECUTED!")

                    # Mark as disconnected
                    self.session._connected = False
                    return True
                else:
                    logger.error(f"Unexpected error during reboot: {e}")
                    msg = f"Reboot command failed: {e}"
                    raise DeviceConnectionError(msg) from e

        except Exception as e:
            logger.error(f"RouterBOARD upgrade failed: {e}")
            if isinstance(e, DeviceConnectionError | DeviceExecutionError):
                raise
            else:
                msg = f"RouterBOARD upgrade failed on {self.session.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def create_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create RouterOS device backup using platform-specific commands.

        Parameters
        ----------
        backup_sequence : list[str]
            List of RouterOS commands to execute for backup
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

        # Use provided sequence or fall back to default RouterOS backup sequence
        if not backup_sequence:
            backup_sequence = DEFAULT_BACKUP_SEQUENCE

        logger.info(f"Creating RouterOS backup on {self.session.device_name}")

        try:
            # Execute backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info("OK RouterOS backup commands executed successfully")
            return True

        except DeviceExecutionError as e:
            logger.error(f"RouterOS backup failed: {e}")
            raise

    def config_backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create RouterOS configuration backup using platform-specific commands.

        This operation creates a text representation of the RouterOS configuration
        using export commands.

        Parameters
        ----------
        backup_sequence : list[str]
            List of RouterOS commands to execute for configuration backup
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

        # Use provided sequence or fall back to default config export
        if not backup_sequence:
            backup_sequence = ["/export file=nw-config-export"]

        logger.info(
            f"Creating RouterOS configuration backup on {self.session.device_name}"
        )

        try:
            # Execute configuration backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing config backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info(
                "OK RouterOS configuration backup commands executed successfully"
            )
            return True

        except DeviceExecutionError as e:
            logger.error(f"RouterOS configuration backup failed: {e}")
            raise

    def backup(
        self,
        backup_sequence: list[str],
        download_files: list[dict[str, str]] | None = None,
    ) -> bool:
        """Create comprehensive RouterOS backup using platform-specific commands.

        This operation creates both text and binary backups of the RouterOS device.
        Includes configuration export and system backup.

        Parameters
        ----------
        backup_sequence : list[str]
            List of RouterOS commands to execute for comprehensive backup
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
                "/export file=nw-config-export",
                "/system/backup/save name=nw-system-backup",
            ]

        logger.info(
            f"Creating comprehensive RouterOS backup on {self.session.device_name}"
        )

        try:
            # Execute comprehensive backup commands
            for cmd in backup_sequence:
                logger.debug(f"Executing backup command: {cmd}")
                self.session.execute_command(cmd)

            logger.info(
                "OK RouterOS comprehensive backup commands executed successfully"
            )
            return True

        except DeviceExecutionError as e:
            logger.error(f"RouterOS comprehensive backup failed: {e}")
            raise

    @classmethod
    def get_supported_file_extensions(cls) -> list[str]:
        """Get list of supported firmware file extensions for RouterOS."""
        return SUPPORTED_FIRMWARE_EXTENSIONS.copy()

    @classmethod
    def get_platform_name(cls) -> str:
        """Get human-readable platform name."""
        return PLATFORM_NAME

    @classmethod
    def get_device_types(cls) -> list[str]:
        """Get list of device types supported by this platform."""
        return DEVICE_TYPES.copy()
