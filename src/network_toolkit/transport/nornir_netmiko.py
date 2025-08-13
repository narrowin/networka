"""Nornir + Netmiko transport implementation."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from nornir import Nornir
    from nornir.core.task import MultiResult, Result

from network_toolkit.transport.interfaces import CommandResult, ConnectionState


class NornirNetmikoTransport:
    """Nornir + Netmiko transport implementation."""

    def __init__(
        self,
        nornir_runner: Nornir,
        device_name: str,
        host: str,
        port: int,
    ) -> None:
        """Initialize the Nornir+Netmiko transport.

        Parameters
        ----------
        nornir_runner : Nornir
            The Nornir runner instance
        device_name : str
            Name of the device in Nornir inventory
        host : str
            Device hostname/IP
        port : int
            Connection port
        """
        self.nr = nornir_runner
        self.device_name = device_name
        self.host = host
        self.port = port
        self._last_activity: float | None = None
        self._connected = False

    def open(self) -> None:
        """Open the connection to the device."""
        # Nornir connections are managed automatically
        # We'll just mark as connected and test connectivity
        try:
            # Import here to avoid dependency issues if nornir not installed
            from nornir_netmiko.tasks import netmiko_send_command

            # Test connection with a simple command
            filtered_nr = self.nr.filter(name=self.device_name)
            result = filtered_nr.run(
                task=netmiko_send_command,
                command_string="",  # Empty command for connection test
                read_timeout=5,
            )

            if result.failed:
                error_msg = f"Failed to connect to {self.device_name}"
                raise ConnectionError(error_msg)

            self._connected = True
            self._last_activity = time.time()
        except ImportError as e:
            error_msg = (
                "Nornir and nornir-netmiko packages required. "
                "Install with: pip install nornir nornir-netmiko"
            )
            raise ImportError(error_msg) from e

    def close(self) -> None:
        """Close the connection to the device."""
        # Nornir manages connections automatically
        self._connected = False
        self._last_activity = None

    def send_command(self, command: str) -> CommandResult:
        """Send a command to the device and return the result."""
        start_time = time.time()

        try:
            # Use Netmiko directly instead of Nornir
            from netmiko import ConnectHandler

            # Get device config from Nornir inventory
            host = self.nr.inventory.hosts[self.device_name]

            # Create Netmiko connection directly
            device_params = {
                "device_type": host.platform,
                "host": host.hostname,
                "username": host.username,
                "password": host.password,
                "port": host.port,
                "timeout": 30,
                "global_delay_factor": 1,
            }

            # Connect and execute command
            with ConnectHandler(**device_params) as connection:
                output = connection.send_command(command)

            execution_time = time.time() - start_time
            self._last_activity = time.time()

            return CommandResult(
                result=str(output),  # Ensure it's a string
                failed=False,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Failed to execute command '{command}': {e}"

            return CommandResult(
                result="",
                failed=True,
            )
        """Send a single command and return the result."""
        try:
            from nornir_netmiko.tasks import netmiko_send_command
        except ImportError as e:
            error_msg = "nornir-netmiko package required. Install with: pip install nornir-netmiko"
            raise ImportError(error_msg) from e

        start_time = time.time()

        # Filter to single device and run command
        filtered_nr = self.nr.filter(name=self.device_name)
        result = filtered_nr.run(
            task=netmiko_send_command,
            command_string=command,
        )

        execution_time = time.time() - start_time
        self._last_activity = time.time()

        # Extract result from Nornir MultiResult
        device_result = result[self.device_name]

        return CommandResult(
            result=str(device_result.result) if device_result.result else "",
            failed=device_result.failed,
            execution_time=execution_time,
            error_context=(
                {
                    "exception": str(device_result.exception) if device_result.exception else None,
                    "host": device_result.host.name if device_result.host else None,
                }
                if device_result.failed
                else None
            ),
        )

    def send_commands(self, commands: list[str]) -> list[CommandResult]:
        """Send multiple commands efficiently using Nornir's batch capabilities."""
        try:
            from nornir_netmiko.tasks import netmiko_send_commands
        except ImportError:
            # Fallback to individual commands
            return [self.send_command(cmd) for cmd in commands]

        filtered_nr = self.nr.filter(name=self.device_name)
        result = filtered_nr.run(
            task=netmiko_send_commands,
            command_string=commands,
        )

        self._last_activity = time.time()

        device_result = result[self.device_name]

        if device_result.failed:
            # Return failed result for all commands
            failed_result = CommandResult(
                result="",
                failed=True,
            )
            return [failed_result for _ in commands]

        # Convert results to CommandResult list
        results = []
        if isinstance(device_result.result, list):
            for _i, cmd_result in enumerate(device_result.result):
                results.append(
                    CommandResult(
                        result=str(cmd_result),
                        failed=False,
                    )
                )
        else:
            # Single result, split by commands
            result_text = str(device_result.result)
            for _ in commands:
                results.append(
                    CommandResult(
                        result=result_text,
                        failed=False,
                    )
                )

        return results

    def send_interactive(self, interact_events: list[tuple[str, str, bool]], timeout_ops: float) -> str:
        """Send interactive command with prompts and responses."""
        # This is more complex with Netmiko, would need custom implementation
        # For now, raise NotImplementedError
        error_msg = (
            "Interactive commands not yet implemented for Nornir+Netmiko transport. "
            "Use Scrapli transport for interactive commands."
        )
        raise NotImplementedError(error_msg)

    def get_connection_state(self) -> ConnectionState:
        """Get current connection state information."""
        return ConnectionState(
            connected=self._connected,
            transport_type="nornir_netmiko",
            device_name=self.device_name,
            host=self.host,
            port=self.port,
            last_activity=self._last_activity,
        )

    def is_alive(self) -> bool:
        """Check if the connection is still active."""
        return self._connected

    def execute_on_group(self, device_names: list[str], command: str) -> dict[str, CommandResult]:
        """Execute command on multiple devices efficiently using Nornir's parallel execution."""
        try:
            from nornir_netmiko.tasks import netmiko_send_command
        except ImportError as e:
            error_msg = "nornir-netmiko package required. Install with: pip install nornir-netmiko"
            raise ImportError(error_msg) from e

        # Filter to target devices and run command in parallel
        filtered_nr = self.nr.filter(name__in=device_names)
        results = filtered_nr.run(
            task=netmiko_send_command,
            command_string=command,
        )

        # Convert Nornir results to CommandResult dict
        command_results = {}
        for device_name in device_names:
            if device_name in results:
                device_result = results[device_name]
                command_results[device_name] = CommandResult(
                    result=str(device_result.result) if device_result.result else "",
                    failed=device_result.failed,
                )
            else:
                # Device not found in results
                command_results[device_name] = CommandResult(
                    result="",
                    failed=True,
                )

        return command_results
