# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Custom exceptions for the network toolkit."""

from typing import Any


class NetworkToolkitError(Exception):
    """Base exception for all network toolkit errors."""

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ConfigurationError(NetworkToolkitError):
    """Raised when there's an issue with configuration parsing or validation."""


class DeviceConnectionError(NetworkToolkitError):
    """Raised when unable to connect to a network device."""

    def __init__(
        self,
        message: str,
        host: str | None = None,
        port: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.host = host
        self.port = port


class DeviceExecutionError(NetworkToolkitError):
    """Raised when command execution on device fails."""

    def __init__(
        self,
        message: str,
        command: str | None = None,
        exit_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.command = command
        self.exit_code = exit_code


class FileTransferError(NetworkToolkitError):
    """Raised when file transfer operations fail."""

    def __init__(
        self,
        message: str,
        local_path: str | None = None,
        remote_path: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, details)
        self.local_path = local_path
        self.remote_path = remote_path


class DeviceAuthError(DeviceConnectionError):
    """Raised when authentication fails."""


class DeviceTimeoutError(NetworkToolkitError):
    """Raised when device operations timeout."""


# Legacy aliases for backward compatibility (to be removed)
CommandExecutionError = DeviceExecutionError
TransferError = FileTransferError
AuthenticationError = DeviceAuthError
