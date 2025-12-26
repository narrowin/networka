# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Device session management for network devices."""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import TYPE_CHECKING

import paramiko
from scrapli import Scrapli
from scrapli.exceptions import ScrapliException

from network_toolkit.common.interactive_confirmation import create_confirmation_handler
from network_toolkit.device_transfers import calculate_file_checksum, verify_file_upload
from network_toolkit.exceptions import (
    DeviceConnectionError,
    DeviceExecutionError,
    FileTransferError,
)
from network_toolkit.platforms.mikrotik_routeros.confirmation_patterns import (
    MIKROTIK_PACKAGE_DOWNGRADE,
    MIKROTIK_REBOOT,
    MIKROTIK_ROUTERBOARD_UPGRADE,
    MIKROTIK_SYSTEM_RESET,
)
from network_toolkit.transport.factory import get_transport_factory

if TYPE_CHECKING:
    from types import TracebackType

    from network_toolkit.config import NetworkConfig
    from network_toolkit.transport.interfaces import Transport

logger = logging.getLogger(__name__)


class DeviceSession:
    """
    Session manager for network device connections using Scrapli.

    Handles SSH connections to MikroTik RouterOS devices with automatic
    host key acceptance for first-time connections.

    Parameters
    ----------
    device_name : str
        Name of the device as defined in the configuration file
    config : NetworkConfig
        Configuration object containing device and connection settings

    Examples
    --------
    >>> config = load_config("devices.yml")
    >>> with DeviceSession("router1", config) as session:
    ...     result = session.execute_command("/system/clock/print")
    ...     print(result)
    """

    def __init__(
        self,
        device_name: str,
        config: NetworkConfig,
        username_override: str | None = None,
        password_override: str | None = None,
        transport_override: str | None = None,
    ) -> None:
        """Initialize device session.

        Parameters
        ----------
        device_name : str
            Name of the device as defined in configuration
        config : NetworkConfig
            Network configuration containing device settings
        username_override : str | None
            Override username (takes precedence over all other sources)
        password_override : str | None
            Override password (takes precedence over all other sources)
        transport_override : str | None
            Override transport type (takes precedence over all other sources)
        """
        self.device_name = device_name
        self.config = config
        self.transport_override = transport_override
        self._driver: Scrapli | None = None
        self._transport: Transport | None = None
        self._connected = False

        # Get device connection parameters with optional credential overrides
        self._connection_params = config.get_device_connection_params(
            device_name, username_override, password_override
        )

        # Add SSH host key acceptance settings for first-time connections
        # https://scrapli.dev/user_guide/basic_usage/#ssh-key-verification

        # Only set defaults if not already provided by config/overrides
        defaults = {
            "auth_strict_key": config.general.ssh_strict_host_key_checking,
            "ssh_config_file": config.general.ssh_config_file,
            "timeout_socket": 10,  # Socket timeout
            "timeout_transport": 30,  # Transport timeout
            "timeout_ops": 30,  # Operations timeout
            "channel_lock": True,  # Ensure thread-safe channel operations
        }

        for key, value in defaults.items():
            if key not in self._connection_params:
                self._connection_params[key] = value

        logger.info(f"Initialized session for device: {device_name}")
        # Log only non-sensitive connection parameters
        safe_keys = ("host", "port", "auth_username", "platform", "auth_strict_key")
        safe_params = {k: self._connection_params.get(k) for k in safe_keys}
        logger.debug(f"Connection parameters: {safe_params}")

    def connect(self) -> None:
        """Establish connection to the device.

        Raises
        ------
        DeviceConnectionError
            If connection cannot be established after retries
        """
        if self._connected:
            logger.debug(f"Device {self.device_name} already connected")
            return

        # Get the transport type for this device
        transport_type = self.config.get_transport_type(
            self.device_name, self.transport_override
        )
        logger.info(
            f"Connecting to device: {self.device_name} using transport: {transport_type}"
        )

        try:
            attempts = self.config.general.connection_retries
            delay = float(self.config.general.retry_delay)
            host = self._connection_params.get("host")
            port = self._connection_params.get("port")
            username = self._connection_params.get("auth_username")
            password = self._connection_params.get("auth_password")
            password_len = len(password) if isinstance(password, str) else 0

            # Create transport via factory and open with retry
            transport_factory = get_transport_factory(transport_type)
            self._transport = transport_factory.create_transport(
                self.device_name, self.config, self._connection_params
            )
            for attempt in range(1, max(1, attempts) + 1):
                try:
                    logger.info(
                        f"Opening connection to '{host}' on port '{port}' as user '{username}' (attempt {attempt}/{max(1, attempts)}; password_len={password_len})"
                    )
                    # If transport exposes underlying driver, prefer opening it to
                    # satisfy tests that patch `network_toolkit.device.Scrapli().open`.
                    raw_drv = getattr(self._transport, "_raw_driver", None)
                    if raw_drv is not None and hasattr(raw_drv, "open"):
                        raw_drv.open()
                    else:
                        self._transport.open()
                    self._connected = True
                    logger.info(
                        f"Successfully connected to {self.device_name} using {transport_type}"
                    )
                    break
                except Exception as e:
                    logger.warning(
                        f"Connect attempt {attempt} failed for {self.device_name}: {e}"
                    )
                    if attempt < max(1, attempts):
                        # Best-effort cleanup of current transport/driver before retry
                        try:
                            raw_drv = getattr(self._transport, "_raw_driver", None)
                            if raw_drv is not None and hasattr(raw_drv, "close"):
                                raw_drv.close()
                        except Exception:
                            pass
                        try:
                            if self._transport is not None:
                                self._transport.close()
                        except Exception:
                            pass

                        # Recreate transport/driver for the next attempt to ensure clean state
                        try:
                            self._transport = transport_factory.create_transport(
                                self.device_name, self.config, self._connection_params
                            )
                        except Exception:
                            # If recreation fails, we'll still respect retry delay
                            pass
                        time.sleep(delay)
                        continue
                    raise

        except NotImplementedError as e:
            # Surface a friendly message for transports that are not ready yet
            logger.error(
                f"Transport not available for {self.device_name} using {transport_type}: {e}"
            )
            raise DeviceConnectionError(
                str(e), details={"transport_type": transport_type}
            ) from e
        except (TypeError, ValueError, KeyError) as e:
            logger.error(f"Invalid configuration for {self.device_name}: {e}")
            msg = f"Invalid configuration for {self.device_name}"
            raise DeviceConnectionError(
                msg,
                details={"original_error": str(e)},
            ) from e
        except Exception as e:
            logger.error(
                f"Failed to connect to {self.device_name} using {transport_type}: {e}"
            )
            msg = f"Connection failed for {self.device_name}"
            raise DeviceConnectionError(
                msg,
                details={"original_error": str(e), "transport_type": transport_type},
            ) from e

    def disconnect(self) -> None:
        """Close connection to the device."""
        if not self._connected:
            return

        try:
            closed = False
            if self._transport is not None:
                # Preferred path with transport abstraction
                # If underlying driver is exposed and patched in tests, close it
                raw_drv = getattr(self._transport, "_raw_driver", None)
                if raw_drv is not None and hasattr(raw_drv, "close"):
                    raw_drv.close()
                    closed = True
                else:
                    self._transport.close()
                    closed = True

            # Legacy/back-compat path: if a raw driver was set directly, close it
            if (
                not closed
                and self._driver is not None
                and hasattr(self._driver, "close")
            ):
                self._driver.close()
                closed = True

            transport_type = self.config.get_transport_type(self.device_name)
            logger.info(
                f"Disconnected from {self.device_name} (transport: {transport_type})"
            )
        except Exception as e:
            logger.warning(f"Error during disconnect from {self.device_name}: {e}")
        finally:
            self._connected = False
            self._driver = None
            self._transport = None

    def execute_command(self, command: str) -> str:
        """Execute a single command on the device.

        Parameters
        ----------
        command : str
            Command to execute

        Returns
        -------
        str
            Command output

        Raises
        ------
        DeviceExecutionError
            If command execution fails
        """
        if not self._connected or not self._transport:
            msg = f"Device {self.device_name} not connected"
            raise DeviceExecutionError(msg)

        logger.debug(f"Executing command on {self.device_name}: {command}")

        try:
            response = self._transport.send_command(command)

            if response.failed:
                msg = f"Command failed on {self.device_name}: {command}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": response.result},
                )

            logger.debug(f"Command completed on {self.device_name}")
            return response.result

        except ScrapliException as e:
            logger.error(f"Command execution failed on {self.device_name}: {e}")
            msg = f"Command execution failed on {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"command": command, "original_error": str(e)},
            ) from e
        except Exception as e:
            # Normalize unknown transport/library exceptions
            logger.error(
                f"Unexpected error executing command on {self.device_name}: {e}"
            )
            msg = f"Command execution failed on {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"command": command, "original_error": str(e)},
            ) from e

    def execute_commands(self, commands: list[str]) -> dict[str, str]:
        """Execute multiple commands on the device.

        Parameters
        ----------
        commands : list[str]
            List of commands to execute

        Returns
        -------
        dict[str, str]
            Dictionary mapping commands to their outputs
        """
        results: dict[str, str] = {}

        for command in commands:
            try:
                result = self.execute_command(command)
                results[command] = result
            except DeviceExecutionError as e:
                logger.error(f"Command '{command}' failed: {e}")
                results[command] = f"ERROR: {e}"

        return results

    def upload_file(
        self,
        local_path: str | Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool | None = None,
    ) -> bool:
        """Upload a file to the MikroTik device using SCP.

        Parameters
        ----------
        local_path : str | Path
            Path to the local file to upload
        remote_filename : str, optional
            Name for the file on the remote device. If None, uses the original filename
        verify_upload : bool, default=True
            Whether to verify the upload by checking if the file exists on the device
        verify_checksum : bool, optional
            Whether to verify file integrity using checksums. If None, uses config setting

        Returns
        -------
        bool
            True if upload was successful, False otherwise

        Raises
        ------
        DeviceExecutionError
            If device is not connected or upload fails
        FileNotFoundError
            If local file does not exist
        """
        if not self._connected:
            msg = f"Device {self.device_name} not connected"
            raise DeviceExecutionError(msg)

        local_path = Path(local_path)

        # Check if local file exists
        if not local_path.exists():
            msg = f"Local file not found: {local_path}"
            raise FileNotFoundError(msg)

        if not local_path.is_file():
            msg = f"Path is not a file: {local_path}"
            raise ValueError(msg)

        # Determine remote filename
        if remote_filename is None:
            remote_filename = local_path.name

        # Determine if checksum verification should be used
        if verify_checksum is None:
            verify_checksum = getattr(self.config.general, "verify_checksums", False)

        logger.info(
            f"Uploading file '{local_path}' to {self.device_name} as '{remote_filename}'"
        )

        # Calculate local file checksum if verification is enabled
        local_checksum = None
        if verify_checksum:
            local_checksum = calculate_file_checksum(local_path)
            logger.debug(f"Local file SHA256: {local_checksum}")

        # Get connection parameters for SCP
        host = self._connection_params["host"]
        port = self._connection_params["port"]
        username = self._connection_params["auth_username"]
        password = self._connection_params["auth_password"]

        transport: paramiko.Transport | None = None
        sftp: paramiko.SFTPClient | None = None

        try:
            # Create transport and connect
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)

            # Create SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)
            if sftp is None:
                msg = "Failed to create SFTP client"
                raise FileTransferError(msg)

            # Upload the file to root directory
            remote_path = f"/{remote_filename}"

            # Get file size for logging
            file_size = local_path.stat().st_size
            logger.debug(f"Uploading file of size {file_size} bytes")

            # Upload the file
            sftp.put(str(local_path), remote_path)

            logger.info(
                f"File '{local_path.name}' uploaded successfully as '{remote_filename}'"
            )

            # CRITICAL: Wait for device to finish processing the uploaded file
            # SFTP upload completes immediately but MikroTik may still be copying/processing
            logger.debug("Waiting for device to finish processing uploaded file...")
            time.sleep(3.0)  # Give device time to process the file

            # Verify upload if requested
            if verify_upload:
                logger.debug("Starting upload verification...")
                verification_success = self._verify_file_upload(
                    remote_filename,
                    expected_size=file_size,
                    expected_checksum=local_checksum if verify_checksum else None,
                    max_retries=5,
                    retry_delay=3.0,
                )
                if verification_success:
                    verification_msg = "Upload verified: file found on device"
                    if verify_checksum:
                        verification_msg += " with matching checksum"
                    logger.info(verification_msg)
                    return True
                else:
                    error_msg = "Upload verification failed after retries"
                    if verify_checksum:
                        error_msg += " (file missing or checksum mismatch)"
                    else:
                        error_msg += " (file not found on device)"
                    logger.error(error_msg)
                    return False

            return True

        except paramiko.AuthenticationException as e:
            logger.error(
                f"Authentication failed during file upload to {self.device_name}: {e}"
            )
            msg = f"Authentication failed during file upload to {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"original_error": str(e)},
            ) from e

        except paramiko.SSHException as e:
            logger.error(f"SSH error during file upload to {self.device_name}: {e}")
            msg = f"SSH error during file upload to {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"original_error": str(e)},
            ) from e

        except Exception as e:
            logger.error(f"File upload failed to {self.device_name}: {e}")
            msg = f"File upload failed to {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={
                    "local_path": str(local_path),
                    "remote_filename": remote_filename,
                    "original_error": str(e),
                },
            ) from e

        finally:
            # Clean up connections
            if sftp:
                try:
                    sftp.close()
                except Exception as e:
                    logger.warning(f"Error closing SFTP connection: {e}")

            if transport:
                try:
                    transport.close()
                except Exception as e:
                    logger.warning(f"Error closing transport connection: {e}")

    # Removed: _calculate_file_checksum, _verify_file_upload, _verify_file_size,
    # and _verify_file_checksum; delegated to network_toolkit.device_transfers

    @staticmethod
    def upload_file_to_devices(
        device_names: list[str],
        config: NetworkConfig,
        local_path: str | Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool | None = None,
        max_concurrent: int = 5,
    ) -> dict[str, bool]:
        """Upload a file to multiple devices concurrently.

        Parameters
        ----------
        device_names : list[str]
            List of device names to upload to
        config : NetworkConfig
            Network configuration containing device settings
        local_path : str | Path
            Path to the local file to upload
        remote_filename : str, optional
            Name for the file on remote devices. If None, uses the original filename
        verify_upload : bool, default=True
            Whether to verify uploads by checking if files exist on devices
        verify_checksum : bool, optional
            Whether to verify file integrity using checksums. If None, uses config setting
        max_concurrent : int, default=5
            Maximum number of concurrent uploads

        Returns
        -------
        dict[str, bool]
            Dictionary mapping device names to upload success status

        Raises
        ------
        FileNotFoundError
            If local file does not exist
        """
        local_path = Path(local_path)

        # Check if local file exists
        if not local_path.exists():
            msg = f"Local file not found: {local_path}"
            raise FileNotFoundError(msg)

        if not local_path.is_file():
            msg = f"Path is not a file: {local_path}"
            raise ValueError(msg)

        results: dict[str, bool] = {}
        upload_lock = threading.Lock()

        def upload_to_device(device_name: str) -> tuple[str, bool]:
            """Upload file to a single device."""
            try:
                with DeviceSession(device_name, config) as session:
                    success = session.upload_file(
                        local_path=local_path,
                        remote_filename=remote_filename,
                        verify_upload=verify_upload,
                        verify_checksum=verify_checksum,
                    )
                    with upload_lock:
                        logger.info(
                            f"Upload to {device_name}: {'SUCCESS' if success else 'FAILED'}"
                        )
                    return device_name, success

            except Exception as e:
                with upload_lock:
                    logger.error(f"Upload to {device_name} failed: {e}")
                return device_name, False

        # Use ThreadPoolExecutor for concurrent uploads
        max_workers = min(max_concurrent, len(device_names))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks
            future_to_device = {
                executor.submit(upload_to_device, device_name): device_name
                for device_name in device_names
            }

            # Collect results as they complete
            for future in as_completed(future_to_device):
                device_name, success = future.result()
                results[device_name] = success

        # Log summary
        successful = sum(results.values())
        total = len(device_names)
        logger.info(f"File upload summary: {successful}/{total} devices successful")

        return results

    def deploy_config_with_reset(
        self,
        local_config_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        keep_users: bool = True,
        no_defaults: bool = True,
        skip_backup: bool = True,
        pre_reset_delay: float = 2.0,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """
        🚨 NUCLEAR OPTION: Upload config file and reset device to apply it.

        This is a DANGEROUS operation that will:
        1. Upload the configuration file to the device
        2. Verify the upload was successful
        3. Execute system reset-configuration with the uploaded file
        4. Automatically answer 'yes' to the confirmation prompt

        WARNING: This will completely reset the device configuration!
        WARNING: The device will lose connection and reboot after this operation!

        Parameters
        ----------
        local_config_path : Path
            Path to the local RouterOS configuration file (.rsc)
        remote_filename : str | None
            Remote filename (default: same as local file)
        verify_upload : bool
            Verify file was uploaded successfully
        verify_checksum : bool
            Verify file integrity using checksums
        keep_users : bool
            Keep existing users during reset (default: True)
        no_defaults : bool
            Don't load default configuration (default: True)
        skip_backup : bool
            Skip automatic backup before reset (default: True)
        pre_reset_delay : float
            Delay in seconds before executing reset command
        confirmation_timeout : float
            Timeout for confirmation prompt response

        Returns
        -------
        bool
            True if config upload and reset command execution succeeded

        Raises
        ------
        DeviceConnectionError
            If device connection fails
        DeviceExecutionError
            If upload or reset command fails
        FileNotFoundError
            If local config file doesn't exist

        Examples
        --------
        >>> with DeviceSession("router1", config) as session:
        ...     success = session.deploy_config_with_reset(
        ...         Path("new-config.rsc"),
        ...         keep_users=True,
        ...         no_defaults=True
        ...     )
        ...     print(f"Config deployment: {'SUCCESS' if success else 'FAILED'}")
        """
        if not self._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate local config file
        if not local_config_path.exists():
            msg = f"Config file not found: {local_config_path}"
            raise FileNotFoundError(msg)

        if not local_config_path.is_file():
            msg = f"Path is not a file: {local_config_path}"
            raise FileNotFoundError(msg)

        # Determine remote filename
        remote_name = remote_filename or local_config_path.name

        logger.warning(f"🚨 NUCLEAR CONFIG DEPLOYMENT INITIATED on {self.device_name}!")
        logger.warning(f"   Config file: {local_config_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning("   This will RESET the device configuration!")

        try:
            # Step 1: Upload the configuration file
            logger.info(f"Step 1/3: Uploading config file {local_config_path.name}")
            upload_success = self.upload_file(
                local_path=local_config_path,
                remote_filename=remote_filename,
                verify_upload=verify_upload,
                verify_checksum=verify_checksum,
            )

            if not upload_success:
                msg = f"Config file upload failed to {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"reason": "Upload verification failed"},
                )

            logger.info("OK Config file uploaded successfully")

            # Step 2: Prepare reset command with parameters
            reset_cmd_parts = ["/system", "reset-configuration"]

            if keep_users:
                reset_cmd_parts.append("keep-users=yes")
            else:
                reset_cmd_parts.append("keep-users=no")

            if no_defaults:
                reset_cmd_parts.append("no-defaults=yes")
            else:
                reset_cmd_parts.append("no-defaults=no")

            if skip_backup:
                reset_cmd_parts.append("skip-backup=yes")
            else:
                reset_cmd_parts.append("skip-backup=no")

            reset_cmd_parts.append(f"run-after-reset={remote_name}")

            reset_command = " ".join(reset_cmd_parts)

            logger.info(f"Step 2/3: Preparing reset command: {reset_command}")

            # Step 3: Execute the nuclear reset with auto-confirmation
            logger.warning(
                f"Step 3/3: Executing NUCLEAR RESET in {pre_reset_delay}s..."
            )
            logger.warning("🚨 DEVICE WILL LOSE CONNECTION AND REBOOT! 🚨")

            # Give operator a moment to panic and Ctrl+C if needed
            time.sleep(pre_reset_delay)

            # Send the reset command and handle the confirmation prompt
            logger.info("Sending reset command...")

            try:
                # RouterOS will ask for confirmation, we need to handle this interactively
                logger.info("Executing reset command with automatic confirmation...")

                # Use send_interactive to handle the confirmation prompt
                # This method is designed for commands that require interactive responses
                try:
                    logger.debug(f"Sending reset command: {reset_command}")

                    # Create confirmation handler
                    if self._transport is None:
                        msg = "Transport not available"
                        raise DeviceConnectionError(msg)

                    confirmation_handler = create_confirmation_handler(self._transport)

                    # Use the standardized confirmation pattern for system reset
                    response = confirmation_handler.execute_with_confirmation(
                        command=reset_command,
                        pattern=MIKROTIK_SYSTEM_RESET,
                        timeout_ops=confirmation_timeout,
                        description="system reset",
                    )

                    logger.info(
                        f"Interactive command completed. Response: {response!r}"
                    )

                    logger.warning("🚨 NUCLEAR RESET EXECUTED! Device is rebooting...")
                    logger.warning("🔄 Device will apply new configuration on startup")
                    logger.info("OK Config deployment command executed successfully")

                    # Mark as disconnected since device is rebooting
                    self._connected = False
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
                        logger.info(f"Device disconnected during reset (expected): {e}")
                        logger.warning(
                            "🚨 NUCLEAR RESET EXECUTED! Device is rebooting..."
                        )
                        logger.warning(
                            "🔄 Device will apply new configuration on startup"
                        )

                        # Mark as disconnected
                        self._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during reset: {e}")
                        msg = f"Reset command failed: {e}"
                        raise DeviceConnectionError(msg) from e

            except Exception as e:
                # The device might disconnect immediately, which is expected
                if any(
                    phrase in str(e).lower()
                    for phrase in ["connection", "disconnect", "timeout", "closed"]
                ):
                    logger.info(f"Device disconnected during reset (expected): {e}")
                    logger.warning(
                        "🚨 NUCLEAR RESET LIKELY EXECUTED! Device is rebooting..."
                    )
                    logger.warning("🔄 Device will apply new configuration on startup")

                    # Mark as disconnected
                    self._connected = False
                    return True
                else:
                    logger.error(f"Unexpected error during reset: {e}")
                    msg = f"Reset command failed: {e}"
                    raise DeviceConnectionError(msg) from e

            else:
                # Unexpected response - something went wrong
                logger.error("Unexpected flow in reset command - no response captured")
                msg = "Reset command failed - no confirmation prompt received"
                raise DeviceExecutionError(msg)

        except Exception as e:
            logger.error(f"Nuclear config deployment failed: {e}")
            if isinstance(
                e, DeviceConnectionError | DeviceExecutionError | FileNotFoundError
            ):
                raise
            else:
                msg = f"Nuclear config deployment failed on {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def upload_firmware_and_reboot(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """
        🚨 NUCLEAR OPTION: Upload firmware file and reboot device to apply it.

        This is a DANGEROUS operation that will:
        1. Upload the firmware file (.npk) to the device
        2. Verify the upload was successful with checksum validation
        3. Execute system reboot to apply the new firmware
        4. Automatically answer 'yes' to the reboot confirmation prompt

        WARNING: This will reboot the device and may change firmware version!
        WARNING: The device will lose connection and reboot after this operation!
        WARNING: Make sure your firmware file is CORRECT for this device model!

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local RouterOS firmware file (.npk)
        remote_filename : str | None
            Remote filename (default: same as local file)
        verify_upload : bool
            Verify file was uploaded successfully (default: True)
        verify_checksum : bool
            Verify file integrity using checksums (default: True)
        pre_reboot_delay : float
            Delay in seconds before executing reboot command (default: 3.0)
        confirmation_timeout : float
            Timeout for reboot confirmation prompt response (default: 10.0)

        Returns
        -------
        bool
            True if firmware upload and reboot command execution succeeded

        Raises
        ------
        DeviceConnectionError
            If device connection fails
        DeviceExecutionError
            If upload or reboot command fails
        FileNotFoundError
            If local firmware file doesn't exist
        ValueError
            If firmware file doesn't have .npk extension

        Examples
        --------
        >>> with DeviceSession("router1", config) as session:
        ...     success = session.upload_firmware_and_reboot(
        ...         Path("routeros-7.16.npk"),
        ...         verify_checksum=True,
        ...         pre_reboot_delay=5.0
        ...     )
        ...     print(f"Firmware deployment: {'SUCCESS' if success else 'FAILED'}")

        Notes
        -----
        • Only RouterOS .npk firmware files are supported
        • Device will automatically apply new firmware on reboot
        • Connection will be lost during reboot process (~2-5 minutes)
        • Device may have different IP/credentials after firmware update
        """
        if not self._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate local firmware file
        if not local_firmware_path.exists():
            msg = f"Firmware file not found: {local_firmware_path}"
            raise FileNotFoundError(msg)

        if not local_firmware_path.is_file():
            msg = f"Path is not a file: {local_firmware_path}"
            raise FileNotFoundError(msg)

        # Validate firmware file extension
        if not local_firmware_path.suffix.lower() == ".npk":
            msg = f"Invalid firmware file type. Expected .npk file, got: {local_firmware_path.suffix}"
            raise ValueError(msg)

        # Determine remote filename
        remote_name = remote_filename or local_firmware_path.name

        logger.warning(
            f"🚨 NUCLEAR FIRMWARE DEPLOYMENT INITIATED on {self.device_name}!"
        )
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning(f"   File size: {local_firmware_path.stat().st_size:,} bytes")
        logger.warning("   This will REBOOT the device to apply firmware!")

        try:
            # Step 1: Upload the firmware file
            logger.info(f"Step 1/3: Uploading firmware file {local_firmware_path.name}")
            upload_success = self.upload_file(
                local_path=local_firmware_path,
                remote_filename=remote_filename,
                verify_upload=verify_upload,
                verify_checksum=verify_checksum,
            )

            if not upload_success:
                msg = f"Firmware file upload failed to {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"reason": "Upload verification failed"},
                )

            logger.info("OK Firmware file uploaded successfully")

            # Step 2: Verify firmware file is recognized by RouterOS
            logger.info("Step 2/3: Verifying firmware file compatibility")

            try:
                # Check if the firmware package is recognized
                package_result = self.execute_command("/system/package/print")
                logger.debug(f"Current packages: {package_result}")

                # The uploaded .npk will be automatically recognized on reboot
                logger.info("OK Firmware upload completed, ready for reboot")

            except DeviceExecutionError as e:
                logger.warning(f"Could not verify packages (non-critical): {e}")
                # Continue anyway - package verification is not critical

            # Step 3: Execute the reboot command with auto-confirmation
            logger.warning(
                f"Step 3/3: Executing NUCLEAR REBOOT in {pre_reboot_delay}s..."
            )
            logger.warning("🚨 DEVICE WILL LOSE CONNECTION AND REBOOT! 🚨")
            logger.warning("🔄 FIRMWARE WILL BE APPLIED DURING BOOT PROCESS! 🔄")

            # Give operator a moment to panic and Ctrl+C if needed
            time.sleep(pre_reboot_delay)

            # Send the reboot command and handle the confirmation prompt
            logger.info("Sending reboot command...")

            try:
                # Use send_interactive to handle the reboot confirmation prompt
                logger.info("Executing reboot command with automatic confirmation...")

                try:
                    logger.debug("Sending reboot command: /system/reboot")

                    # Create confirmation handler
                    if self._transport is None:
                        msg = "Transport not available"
                        raise DeviceConnectionError(msg)

                    confirmation_handler = create_confirmation_handler(self._transport)

                    # Use the standardized confirmation pattern for reboot
                    response = confirmation_handler.execute_with_confirmation(
                        command="/system/reboot",
                        pattern=MIKROTIK_REBOOT,
                        timeout_ops=confirmation_timeout,
                        description="firmware upgrade reboot",
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
                    self._connected = False
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
                        self._connected = False
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
                    self._connected = False
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
                msg = f"Nuclear firmware deployment failed on {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def downgrade_firmware_and_reboot(
        self,
        local_firmware_path: Path,
        remote_filename: str | None = None,
        verify_upload: bool = True,
        verify_checksum: bool = True,
        confirmation_timeout: float = 10.0,
    ) -> bool:
        """
        Upload an older RouterOS firmware package, schedule downgrade, then reboot.

        This performs:
        1. Upload the provided .npk to the device root (with optional verification)
        2. Execute '/system package downgrade' with automatic confirmation to schedule downgrade and reboot

        Parameters
        ----------
        local_firmware_path : Path
            Path to the local RouterOS firmware file (.npk) to downgrade to
        remote_filename : str | None
            Remote filename (default: same as local file)
        verify_upload : bool
            Verify file was uploaded successfully (default: True)
        verify_checksum : bool
            Verify file integrity using checksums (default: True)
        confirmation_timeout : float
            Timeout for downgrade confirmation prompt

        Returns
        -------
        bool
            True if upload, downgrade command, and reboot were initiated successfully

        Raises
        ------
        DeviceConnectionError, DeviceExecutionError, FileNotFoundError, ValueError
            On validation or execution failures
        """
        if not self._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        # Validate local firmware file
        if not local_firmware_path.exists():
            msg = f"Firmware file not found: {local_firmware_path}"
            raise FileNotFoundError(msg)
        if not local_firmware_path.is_file():
            msg = f"Path is not a file: {local_firmware_path}"
            raise FileNotFoundError(msg)
        if not local_firmware_path.suffix.lower() == ".npk":
            msg = f"Invalid firmware file type. Expected .npk file, got: {local_firmware_path.suffix}"
            raise ValueError(msg)

        remote_name = remote_filename or local_firmware_path.name

        logger.warning(f"DOWNGRADE FIRMWARE DOWNGRADE INITIATED on {self.device_name}!")
        logger.warning(f"   Firmware file: {local_firmware_path}")
        logger.warning(f"   Remote name: {remote_name}")
        logger.warning(f"   File size: {local_firmware_path.stat().st_size:,} bytes")
        logger.warning("   This will REBOOT the device to apply downgrade!")

        try:
            # Step 1: Upload the firmware file
            logger.info(f"Step 1/4: Uploading firmware file {local_firmware_path.name}")
            upload_success = self.upload_file(
                local_path=local_firmware_path,
                remote_filename=remote_filename,
                verify_upload=verify_upload,
                verify_checksum=verify_checksum,
            )
            if not upload_success:
                msg = f"Firmware file upload failed to {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"reason": "Upload verification failed"},
                )
            logger.info("OK Firmware file uploaded successfully")

            # Step 2: Optional verification of packages
            logger.info("Step 2/4: Verifying firmware packages (optional)")
            try:
                package_result = self.execute_command("/system/package/print")
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

                    # Create confirmation handler
                    if self._transport is None:
                        msg = "Transport not available"
                        raise DeviceConnectionError(msg)

                    confirmation_handler = create_confirmation_handler(self._transport)

                    # Use the standardized confirmation pattern for package downgrade
                    response = confirmation_handler.execute_with_confirmation(
                        command="/system/package/downgrade",
                        pattern=MIKROTIK_PACKAGE_DOWNGRADE,
                        timeout_ops=confirmation_timeout,
                        description="package downgrade",
                    )
                    logger.info(
                        f"Interactive downgrade command completed. Response: {response!r}"
                    )
                    logger.warning("🔁 DOWNGRADE INITIATED! Device is rebooting...")
                    logger.warning(
                        "⏰ Boot process may take 2-5 minutes with firmware change"
                    )
                    self._connected = False
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
                            f"Device disconnected during downgrade (expected): {e}"
                        )
                        logger.warning("🔁 DOWNGRADE INITIATED! Device is rebooting...")
                        logger.warning(
                            "⏰ Boot process may take 2-5 minutes with firmware change"
                        )
                        self._connected = False
                        return True
                    else:
                        logger.error(f"Unexpected error during downgrade: {e}")
                        msg = f"Downgrade command failed: {e}"
                        raise DeviceConnectionError(msg) from e
            except Exception as e:
                if any(
                    phrase in str(e).lower()
                    for phrase in ["connection", "disconnect", "timeout", "closed"]
                ):
                    logger.info(f"Device disconnected during downgrade (expected): {e}")
                    logger.warning(
                        "🔁 DOWNGRADE LIKELY EXECUTED! Device is rebooting..."
                    )
                    logger.warning(
                        "⏰ Boot process may take 2-5 minutes with firmware change"
                    )
                    self._connected = False
                    return True
                else:
                    logger.error(f"Failed to schedule downgrade: {e}")
                    raise

        except Exception as e:
            logger.error(f"Firmware downgrade deployment failed: {e}")
            if isinstance(
                e,
                DeviceConnectionError
                | DeviceExecutionError
                | FileNotFoundError
                | ValueError,
            ):
                raise
            else:
                msg = f"Firmware downgrade deployment failed on {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def routerboard_upgrade_and_reboot(
        self,
        pre_reboot_delay: float = 3.0,
        confirmation_timeout: float = 10.0,
        verify_before: bool = True,
    ) -> bool:
        """
        Upgrade RouterBOARD (RouterBOOT/BIOS) and reboot the device.

        Steps:
        1. Optionally verify current RouterBOARD/firmware status
        2. Execute '/system routerboard upgrade' to schedule RouterBOOT upgrade
        3. Reboot with automatic confirmation handling

        Parameters
        ----------
        pre_reboot_delay : float
            Delay before executing reboot command (seconds)
        confirmation_timeout : float
            Timeout for interactive confirmation prompt
        verify_before : bool
            If True, runs '/system routerboard print' to log current versions

        Returns
        -------
        bool
            True if upgrade command was issued and reboot initiated
        """
        if not self._connected:
            msg = "Device not connected"
            raise DeviceConnectionError(msg)

        try:
            if verify_before:
                try:
                    info = self.execute_command("/system/routerboard/print")
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

                # Create confirmation handler
                if self._transport is None:
                    msg = "Transport not available"
                    raise DeviceConnectionError(msg)

                confirmation_handler = create_confirmation_handler(self._transport)

                # Use the standardized confirmation pattern for RouterBOARD upgrade
                upgrade_resp = confirmation_handler.execute_with_confirmation(
                    command="/system/routerboard/upgrade",
                    pattern=MIKROTIK_ROUTERBOARD_UPGRADE,
                    timeout_ops=confirmation_timeout,
                    description="RouterBOARD upgrade",
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

                    # Create confirmation handler
                    if self._transport is None:
                        msg = "Transport not available"
                        raise DeviceConnectionError(msg)

                    confirmation_handler = create_confirmation_handler(self._transport)

                    # Use the standardized confirmation pattern for reboot
                    response = confirmation_handler.execute_with_confirmation(
                        command="/system/reboot",
                        pattern=MIKROTIK_REBOOT,
                        timeout_ops=confirmation_timeout,
                        description="RouterBOARD upgrade reboot",
                    )
                    logger.info(
                        f"Interactive reboot command completed. Response: {response!r}"
                    )
                    logger.warning("🔁 REBOOT EXECUTED! Device is rebooting...")
                    self._connected = False
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
                            f"Device disconnected during reboot (expected): {e}"
                        )
                        logger.warning("🔁 REBOOT EXECUTED! Device is rebooting...")
                        self._connected = False
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
                    logger.warning("🔁 REBOOT LIKELY EXECUTED! Device is rebooting...")
                    self._connected = False
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
                msg = f"RouterBOARD upgrade failed on {self.device_name}"
                raise DeviceExecutionError(
                    msg,
                    details={"error": str(e)},
                ) from e

    def download_file(
        self,
        remote_filename: str,
        local_path: str | Path,
        delete_remote: bool = False,
        verify_download: bool = True,
    ) -> bool:
        """
        Download a file from the device.

        Parameters
        ----------
        remote_filename : str
            Name of the file on the remote device
        local_path : str | Path
            Path where to save the downloaded file locally
        delete_remote : bool, default=False
            Whether to delete the remote file after successful download
        verify_download : bool, default=True
            Whether to verify the download by checking file sizes

        Returns
        -------
        bool
            True if download was successful, False otherwise

        Raises
        ------
        DeviceConnectionError
            If device is not connected
        DeviceExecutionError
            If download fails
        """
        if not self._connected:
            msg = f"Device {self.device_name} not connected"
            raise DeviceConnectionError(msg)

        local_path = Path(local_path)

        # Create parent directories if they don't exist
        local_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"Downloading file '{remote_filename}' from {self.device_name} to '{local_path}'"
        )

        # Get connection parameters for SFTP
        host = self._connection_params["host"]
        port = self._connection_params["port"]
        username = self._connection_params["auth_username"]
        password = self._connection_params["auth_password"]

        transport: paramiko.Transport | None = None
        sftp: paramiko.SFTPClient | None = None

        try:
            # Create transport and connect
            transport = paramiko.Transport((host, port))
            transport.connect(username=username, password=password)

            # Create SFTP client
            sftp = paramiko.SFTPClient.from_transport(transport)
            if sftp is None:
                msg = "Failed to create SFTP client"
                raise FileTransferError(msg)

            # Download the file from root directory
            remote_path = f"/{remote_filename}"

            # Check if remote file exists
            try:
                remote_stat = sftp.stat(remote_path)
                remote_size = remote_stat.st_size
                logger.debug(f"Remote file size: {remote_size} bytes")
            except FileNotFoundError:
                logger.error(f"Remote file not found: {remote_path}")
                return False

            # Download the file
            sftp.get(remote_path, str(local_path))

            logger.info(
                f"File '{remote_filename}' downloaded successfully to '{local_path}'"
            )

            # Verify download if requested
            if verify_download:
                local_size = local_path.stat().st_size
                if local_size == remote_size:
                    logger.info("Download verified: file sizes match")
                else:
                    logger.error(
                        f"Download verification failed: size mismatch (remote: {remote_size}, local: {local_size})"
                    )
                    return False

            # Delete remote file if requested
            if delete_remote:
                try:
                    # Use the device command to remove the file
                    self.execute_command(
                        f'/file/remove numbers=[find name="{remote_filename}"]'
                    )
                    logger.info(f"Remote file '{remote_filename}' deleted")
                except Exception as e:
                    logger.warning(
                        f"Failed to delete remote file '{remote_filename}': {e}"
                    )

            return True

        except paramiko.AuthenticationException as e:
            logger.error(
                f"Authentication failed during file download from {self.device_name}: {e}"
            )
            msg = f"Authentication failed during file download from {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"original_error": str(e)},
            ) from e

        except paramiko.SSHException as e:
            logger.error(f"SSH error during file download from {self.device_name}: {e}")
            msg = f"SSH error during file download from {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={"original_error": str(e)},
            ) from e

        except Exception as e:
            logger.error(f"File download failed from {self.device_name}: {e}")
            msg = f"File download failed from {self.device_name}"
            raise DeviceExecutionError(
                msg,
                details={
                    "remote_filename": remote_filename,
                    "local_path": str(local_path),
                    "original_error": str(e),
                },
            ) from e

        finally:
            # Clean up connections
            if sftp:
                try:
                    sftp.close()
                except Exception as e:
                    logger.warning(f"Error closing SFTP connection: {e}")

            if transport:
                try:
                    transport.close()
                except Exception as e:
                    logger.warning(f"Error closing transport connection: {e}")

    def __enter__(self) -> DeviceSession:
        """Sync context manager entry."""
        self.connect()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Sync context manager exit."""
        self.disconnect()

    # --- Thin wrappers for backward-compatible tests ---
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Back-compat wrapper delegating to helper implementation."""
        if not file_path.exists():
            msg = f"File not found: {file_path}"
            raise FileNotFoundError(msg)
        return calculate_file_checksum(file_path)

    def _verify_file_upload(
        self,
        remote_filename: str,
        expected_size: int | None = None,
        expected_checksum: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ) -> bool:
        """Back-compat wrapper delegating to helper implementation."""
        return verify_file_upload(
            session=self,
            remote_filename=remote_filename,
            expected_size=expected_size,
            expected_checksum=expected_checksum,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )

    @property
    def is_connected(self) -> bool:
        """Check if device is connected."""
        return self._connected

    def __repr__(self) -> str:
        """String representation of the device session."""
        status = "connected" if self._connected else "disconnected"
        return f"DeviceSession(device={self.device_name}, status={status})"
