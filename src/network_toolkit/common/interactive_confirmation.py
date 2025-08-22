"""Interactive confirmation patterns and utilities for network devices.

This module provides a centralized approach to handling yes/no confirmations
across different network device platforms, reducing code duplication and
ensuring consistent behavior.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from network_toolkit.exceptions import DeviceExecutionError

if TYPE_CHECKING:
    from network_toolkit.transport.interfaces import Transport

logger = logging.getLogger(__name__)


class ConfirmationPattern:
    """A confirmation pattern for interactive device commands."""

    def __init__(
        self, prompt: str, response: str, is_reboot_operation: bool = False
    ) -> None:
        """Initialize confirmation pattern.

        Parameters
        ----------
        prompt : str
            The exact prompt text to expect from the device
        response : str
            The response to send (empty string means press Enter)
        is_reboot_operation : bool
            Whether this pattern is for a reboot/restart operation
        """
        self.prompt = prompt
        self.response = response
        self.is_reboot_operation = is_reboot_operation


class InteractiveConfirmationHandler:
    """Handles interactive confirmations with standardized patterns and error handling."""

    def __init__(self, transport: Transport) -> None:
        """Initialize the confirmation handler.

        Parameters
        ----------
        transport : Transport
            The transport layer to use for sending interactive commands
        """
        self._transport = transport

    def execute_with_confirmation(
        self,
        command: str,
        pattern: ConfirmationPattern,
        timeout_ops: float = 10.0,
        description: str = "",
    ) -> str:
        """Execute a command that requires interactive confirmation.

        Parameters
        ----------
        command : str
            The command to execute
        pattern : ConfirmationPattern
            The confirmation pattern to use
        timeout_ops : float
            Timeout for the interactive operation in seconds
        description : str
            Description of the operation for logging

        Returns
        -------
        str
            The response from the device

        Raises
        ------
        DeviceExecutionError
            If the command fails
        """
        operation_desc = description or f"command '{command}'"
        logger.debug(f"Executing {operation_desc} with confirmation")
        logger.debug(f"Command: {command}")
        logger.debug(f"Expected prompt: {pattern.prompt!r}")
        logger.debug(f"Response: {pattern.response!r}")

        try:
            response = self._transport.send_interactive(
                interact_events=[
                    (command, pattern.prompt, True),
                    (pattern.response, "", False),
                ],
                timeout_ops=timeout_ops,
            )

            logger.info(f"Interactive {operation_desc} completed successfully")
            logger.debug(f"Device response: {response!r}")
            return response

        except Exception as e:
            # For reboot operations, disconnection is expected
            if pattern.is_reboot_operation and self._is_expected_disconnect(e):
                logger.info(
                    f"Device disconnected during {operation_desc} (expected for reboot)"
                )
                return "Device rebooted (connection lost as expected)"

            logger.error(f"Interactive {operation_desc} failed: {e}")
            msg = f"Interactive {operation_desc} failed: {e}"
            raise DeviceExecutionError(msg) from e

    def _is_expected_disconnect(self, exception: Exception) -> bool:
        """Check if the exception indicates an expected disconnection during reboot."""
        error_str = str(exception).lower()
        expected_patterns = [
            "connection",
            "disconnect",
            "timeout",
            "closed",
            "eof",
            "timed out sending interactive input",
        ]
        return any(pattern in error_str for pattern in expected_patterns)


def create_confirmation_handler(transport: Transport) -> InteractiveConfirmationHandler:
    """Factory function to create a confirmation handler.

    Parameters
    ----------
    transport : Transport
        The transport layer to use

    Returns
    -------
    InteractiveConfirmationHandler
        A new confirmation handler instance
    """
    return InteractiveConfirmationHandler(transport)
