# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the exceptions module."""

from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.exceptions import (
    AuthenticationError,
    CommandExecutionError,
    ConfigurationError,
    DeviceConnectionError,
    DeviceExecutionError,
    NetworkToolkitError,
    TransferError,
)


class TestNetworkToolkitError:
    """Test the base NetworkToolkitError class."""

    def test_basic_creation(self) -> None:
        """Test basic error creation."""
        error = NetworkToolkitError("Test error")
        assert str(error) == "Test error"
        assert error.message == "Test error"
        assert error.details == {}

    def test_with_details(self) -> None:
        """Test error creation with details."""
        details: dict[str, Any] = {"key": "value", "number": 42}
        error = NetworkToolkitError("Test error", details=details)
        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["number"] == 42

    def test_inheritance(self) -> None:
        """Test that NetworkToolkitError inherits from Exception."""
        error = NetworkToolkitError("Test error")
        assert isinstance(error, Exception)

    def test_empty_details(self) -> None:
        """Test that details defaults to empty dict."""
        error = NetworkToolkitError("Test error", details=None)
        assert error.details == {}


class TestConfigurationError:
    """Test the ConfigurationError class."""

    def test_basic_creation(self) -> None:
        """Test basic configuration error creation."""
        error = ConfigurationError("Invalid config")
        assert str(error) == "Invalid config"
        assert isinstance(error, NetworkToolkitError)

    def test_with_details(self) -> None:
        """Test configuration error with details."""
        details: dict[str, Any] = {"file": "devices.yml", "line": 42}
        error = ConfigurationError("YAML syntax error", details=details)
        assert error.details == details
        assert error.details["file"] == "devices.yml"


class TestDeviceConnectionError:
    """Test the DeviceConnectionError class."""

    def test_basic_creation(self) -> None:
        """Test basic device connection error creation."""
        error = DeviceConnectionError("Connection failed")
        assert str(error) == "Connection failed"
        assert isinstance(error, NetworkToolkitError)
        assert error.host is None
        assert error.port is None

    def test_with_host_and_port(self) -> None:
        """Test device connection error with host and port."""
        error = DeviceConnectionError("Connection failed", host="test.local", port=22)
        assert error.host == "test.local"
        assert error.port == 22

    def test_with_details(self) -> None:
        """Test device connection error with details."""
        details: dict[str, Any] = {"timeout": 30, "retries": 3}
        error = DeviceConnectionError("Connection failed", details=details)
        assert error.details == details


class TestCommandExecutionError:
    """Test the CommandExecutionError class."""

    def test_basic_creation(self) -> None:
        """Test basic command execution error creation."""
        error = CommandExecutionError("Command failed")
        assert str(error) == "Command failed"
        assert isinstance(error, NetworkToolkitError)
        assert error.command is None
        assert error.exit_code is None

    def test_with_command_and_exit_code(self) -> None:
        """Test command execution error with command and exit code."""
        error = CommandExecutionError("Command failed", command="test_cmd", exit_code=1)
        assert error.command == "test_cmd"
        assert error.exit_code == 1

    def test_with_details(self) -> None:
        """Test command execution error with details."""
        details: dict[str, Any] = {"stderr": "Permission denied", "stdout": ""}
        error = CommandExecutionError("Command failed", details=details)
        assert error.details == details


class TestTransferError:
    """Test the TransferError class."""

    def test_basic_creation(self) -> None:
        """Test basic transfer error creation."""
        error = TransferError("Transfer failed")
        assert str(error) == "Transfer failed"
        assert isinstance(error, NetworkToolkitError)
        assert error.local_path is None
        assert error.remote_path is None

    def test_with_paths(self) -> None:
        """Test transfer error with local and remote paths."""
        error = TransferError(
            "Transfer failed",
            local_path="/tmp/file.txt",
            remote_path="/home/user/file.txt",
        )
        assert error.local_path == "/tmp/file.txt"
        assert error.remote_path == "/home/user/file.txt"

    def test_with_details(self) -> None:
        """Test transfer error with details."""
        details: dict[str, Any] = {"size": 1024, "mode": "binary"}
        error = TransferError("Transfer failed", details=details)
        assert error.details == details


class TestAuthenticationError:
    """Test the AuthenticationError class."""

    def test_basic_creation(self) -> None:
        """Test basic authentication error creation."""
        error = AuthenticationError("Authentication failed")
        assert str(error) == "Authentication failed"
        assert isinstance(error, DeviceConnectionError)
        assert isinstance(error, NetworkToolkitError)

    def test_inheritance_chain(self) -> None:
        """Test that AuthenticationError inherits properly."""
        error = AuthenticationError("Auth failed")
        assert isinstance(error, AuthenticationError)
        assert isinstance(error, DeviceConnectionError)
        assert isinstance(error, NetworkToolkitError)
        assert isinstance(error, Exception)


class TestDeviceExecutionError:
    """Test the DeviceExecutionError class."""

    def test_basic_creation(self) -> None:
        """Test basic device execution error creation."""
        error = DeviceExecutionError("Execution failed")
        assert str(error) == "Execution failed"
        assert isinstance(error, NetworkToolkitError)

    def test_with_details(self) -> None:
        """Test device execution error with details."""
        details: dict[str, Any] = {"device": "router1", "command": "show version"}
        error = DeviceExecutionError("Execution failed", details=details)
        assert error.details == details


class TestExceptionHierarchy:
    """Test exception hierarchy and inheritance."""

    def test_exception_chaining(self) -> None:
        """Test that exceptions can be chained properly."""
        try:
            msg = "Original error"
            raise ValueError(msg)
        except ValueError as e:
            try:
                msg = "Connection failed due to config error"
                raise DeviceConnectionError(msg) from e
            except DeviceConnectionError as conn_err:
                assert conn_err.__cause__ is e
                assert isinstance(conn_err.__cause__, ValueError)

    def test_nested_exception_handling(self) -> None:
        """Test nested exception handling."""
        try:
            msg = "Inner error"
            raise NetworkToolkitError(msg)
        except NetworkToolkitError:
            try:
                msg = "Configuration problem"
                raise ConfigurationError(msg) from None
            except ConfigurationError as config_err:
                assert config_err.__cause__ is None


class TestExceptionTypes:
    """Test exception type checking and isinstance behavior."""

    def test_all_exceptions_are_network_toolkit_errors(self) -> None:
        """Test that all exceptions inherit from NetworkToolkitError."""
        exceptions: list[NetworkToolkitError] = [
            NetworkToolkitError("test"),
            ConfigurationError("test"),
            DeviceConnectionError("test"),
            CommandExecutionError("test"),
            DeviceExecutionError("test"),
            TransferError("test"),
            AuthenticationError("test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, NetworkToolkitError)
            assert isinstance(exc, Exception)

    def test_exception_type_specificity(self) -> None:
        """Test that exceptions maintain their specific types."""
        exceptions: list[NetworkToolkitError] = [
            NetworkToolkitError("base error"),
            ConfigurationError("config error"),
            DeviceConnectionError("connection error"),
            CommandExecutionError("command error"),
            DeviceExecutionError("execution error"),
            TransferError("transfer error"),
            AuthenticationError("auth error"),
        ]

        for exc in exceptions:
            try:
                raise exc
            except NetworkToolkitError as e:
                assert isinstance(e, type(exc))
                assert str(e) == str(exc)


class TestExceptionContext:
    """Test exception context and error details."""

    def test_device_connection_error_context(self) -> None:
        """Test DeviceConnectionError context information."""
        with pytest.raises(DeviceConnectionError) as exc_info:
            msg = "Connection failed"
            raise DeviceConnectionError(msg, host="test.local")

        error = exc_info.value
        assert error.host == "test.local"
        assert str(error) == "Connection failed"

    def test_command_execution_error_context(self) -> None:
        """Test CommandExecutionError context information."""
        with pytest.raises(CommandExecutionError) as exc_info:
            msg = "Command failed"
            raise CommandExecutionError(msg, command="test_command")

        error = exc_info.value
        assert error.command == "test_command"
        assert str(error) == "Command failed"
