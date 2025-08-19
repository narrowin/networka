"""Command execution service for the TUI."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Sequence
from contextlib import asynccontextmanager
from typing import Any, Protocol

from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.tui.data import TuiData, TuiDataService
from network_toolkit.tui.models import ExecutionPlan, RunResult


class DataProtocol(Protocol):
    """Protocol for data service interface."""

    @property
    def config(self) -> Any:
        ...

    def sequence_commands(
        self, name: str, device_name: str | None = None
    ) -> list[str] | None:
        ...


class DataServiceAdapter:
    """Adapter to make TuiDataService compatible with legacy TuiData interface."""

    def __init__(self, data_service: TuiDataService) -> None:
        self._service = data_service

    @property
    def config(self) -> Any:
        return self._service.config

    def sequence_commands(
        self, name: str, device_name: str | None = None
    ) -> list[str] | None:
        """Get sequence commands using sync interface."""
        return asyncio.run(self._service.resolve_sequence_commands(name, device_name))


class ExecutionCallbacks:
    """Callbacks for execution events."""

    def __init__(
        self,
        on_output: Callable[[str], None] | None = None,
        on_error: Callable[[str], None] | None = None,
        on_progress: Callable[[str], None] | None = None,
    ) -> None:
        self.on_output = on_output or (lambda _: None)
        self.on_error = on_error or (lambda _: None)
        self.on_progress = on_progress or (lambda _: None)


class ExecutionManager:
    """Manages command execution with proper async patterns."""

    def __init__(
        self, data_service: TuiData | TuiDataService, concurrency: int = 5
    ) -> None:
        """Initialize with either TuiData or TuiDataService."""
        # Handle both legacy and modern data services
        if hasattr(data_service, "sequence_commands"):
            # It's a TuiData (legacy)
            self._data: DataProtocol = data_service  # type: ignore[assignment]
            self._config = data_service.config
        else:
            # It's a TuiDataService (modern), create adapter
            self._data = DataServiceAdapter(data_service)  # type: ignore[arg-type]
            self._config = data_service.config

        self._semaphore = asyncio.Semaphore(concurrency)
        self._resolver = DeviceResolver(self._config)

    def resolve_devices(
        self, devices: Sequence[str], groups: Sequence[str]
    ) -> list[str]:
        """Resolve device names from selections."""
        selected_devices: set[str] = set(devices)

        # Expand groups
        for group in groups:
            try:
                members = self._config.get_group_members(group)
                selected_devices.update(members)
            except Exception:
                logging.debug(f"Failed to expand group: {group}")

        # Filter to valid devices only
        return [
            device
            for device in sorted(selected_devices)
            if self._resolver.is_device(device)
        ]

    def build_execution_plan(
        self,
        devices: Sequence[str],
        sequences: Sequence[str],
        command_text: str,
    ) -> ExecutionPlan:
        """Build execution plan from selections."""
        plan: ExecutionPlan = {}

        if sequences:
            # Use sequences
            for device in devices:
                commands: list[str] = []
                for sequence in sequences:
                    resolved = self._data.sequence_commands(sequence, device)
                    if resolved:
                        commands.extend(resolved)
                if commands:
                    plan[device] = commands
        elif command_text.strip():
            # Use free-form commands
            commands = [cmd.strip() for cmd in command_text.splitlines() if cmd.strip()]
            if commands:
                for device in devices:
                    plan[device] = commands

        return plan

    async def execute_plan(
        self, plan: ExecutionPlan, callbacks: ExecutionCallbacks
    ) -> RunResult:
        """Execute the plan with proper concurrency control."""
        total_devices = len(plan)
        if total_devices == 0:
            return RunResult(total=0, successes=0, failures=0)

        callbacks.on_progress(f"Starting execution on {total_devices} devices...")

        # Execute all devices concurrently
        tasks = [
            self._execute_device(device, commands, callbacks)
            for device, commands in plan.items()
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Count results
        successes = sum(1 for result in results if result is True)
        failures = total_devices - successes

        return RunResult(total=total_devices, successes=successes, failures=failures)

    async def _execute_device(
        self,
        device: str,
        commands: list[str],
        callbacks: ExecutionCallbacks,
    ) -> bool:
        """Execute commands on a single device."""
        async with self._semaphore:
            return await asyncio.to_thread(
                self._execute_device_sync, device, commands, callbacks
            )

    def _execute_device_sync(
        self,
        device: str,
        commands: list[str],
        callbacks: ExecutionCallbacks,
    ) -> bool:
        """Synchronous device execution (runs in thread)."""
        try:
            # Import here to avoid circular dependencies
            from network_toolkit.cli import DeviceSession

            callbacks.on_progress(f"{device}: Connecting...")

            with DeviceSession(device, self._config) as session:
                callbacks.on_progress(f"{device}: Connected")

                for command in commands:
                    callbacks.on_progress(f"{device}: {command}")

                    try:
                        result = session.execute_command(command)
                        output = str(result).strip()

                        if output:
                            for line in output.splitlines():
                                callbacks.on_output(f"{device}: {line}")

                    except Exception as e:
                        error_msg = f"{device}: Command failed: {command} - {e}"
                        callbacks.on_error(error_msg)
                        return False

                callbacks.on_progress(f"{device}: Completed successfully")
                return True

        except Exception as e:
            error_msg = f"{device}: Connection failed: {e}"
            callbacks.on_error(error_msg)
            return False


@asynccontextmanager
async def execution_context(
    data: TuiData, concurrency: int = 5
) -> Any:  # Using Any to avoid complex AsyncGenerator typing
    """Context manager for execution operations."""
    manager = ExecutionManager(data, concurrency)
    try:
        yield manager
    finally:
        # Cleanup if needed
        pass
