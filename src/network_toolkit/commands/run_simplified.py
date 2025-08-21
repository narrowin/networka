# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Simplified and clean run command implementation."""

from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import typer

from network_toolkit.common.command import CommandContext
from network_toolkit.common.errors import print_error, print_success
from network_toolkit.common.logging import console, setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.sequence_manager import SequenceManager


def _print_info(text: str) -> None:
    """Print info message using default theme."""
    from network_toolkit.common.styles import StyleManager, StyleName

    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    style = style_manager.get_style(StyleName.INFO)
    console.print(f"[{style}]{text}[/{style}]")


def _print_success(text: str) -> None:
    """Print success message using default theme."""
    from network_toolkit.common.styles import StyleManager, StyleName

    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    style = style_manager.get_style(StyleName.SUCCESS)
    console.print(f"[{style}]{text}[/{style}]")


class OutputFormat(str, Enum):
    """Output format options."""

    NORMAL = "normal"
    JSON = "json"
    RAW = "raw"


class RunExecutor:
    """Centralized execution logic for run command."""

    def __init__(
        self,
        config: Any,
        resolver: DeviceResolver,
        sequence_manager: SequenceManager,
        results_manager: ResultsManager,
        output_format: OutputFormat = OutputFormat.NORMAL,
        verbose: bool = False,
    ) -> None:
        """Initialize executor with dependencies."""
        self.config = config
        self.resolver = resolver
        self.sequence_manager = sequence_manager
        self.results_manager = results_manager
        self.output_format = output_format
        self.verbose = verbose

    def execute_command_on_device(
        self, device_name: str, command: str
    ) -> tuple[str, str | None]:
        """Execute a single command on a device.

        Returns
        -------
        tuple[str, str | None]
            Tuple of (result, error_message)
        """
        try:
            # Late import to allow tests to patch `network_toolkit.cli.DeviceSession`
            from network_toolkit.cli import DeviceSession

            with DeviceSession(device_name, self.config) as session:
                result = session.execute_command(command)
                return result, None
        except NetworkToolkitError as e:
            error_msg = f"Error on {device_name}: {e.message}"
            if self.verbose and e.details:
                error_msg += f" | Details: {e.details}"
            return "", error_msg
        except Exception as e:
            return "", f"Unexpected error on {device_name}: {e}"

    def execute_sequence_on_device(
        self, device_name: str, sequence_name: str
    ) -> tuple[dict[str, str] | None, str | None]:
        """Execute a sequence on a device.

        Returns
        -------
        tuple[dict[str, str] | None, str | None]
            Tuple of (results_map, error_message)
        """
        try:
            # Late import to allow tests to patch `network_toolkit.cli.DeviceSession`
            from network_toolkit.cli import DeviceSession

            with DeviceSession(device_name, self.config) as session:
                sequence_commands = self.sequence_manager.resolve(
                    sequence_name, device_name
                )
                if not sequence_commands:
                    return None, f"Sequence '{sequence_name}' not found for device type"

                results_map: dict[str, str] = {}
                for cmd in sequence_commands:
                    output = session.execute_command(cmd)
                    results_map[cmd] = output

                return results_map, None
        except NetworkToolkitError as e:
            error_msg = f"Error on {device_name}: {e.message}"
            if self.verbose and e.details:
                error_msg += f" | Details: {e.details}"
            return None, error_msg
        except Exception as e:
            return None, f"Unexpected error on {device_name}: {e}"

    def print_result(self, device_name: str, command: str, result: str) -> None:
        """Print command result based on output format."""
        if self.output_format == OutputFormat.JSON:
            event = {
                "event": "result",
                "device": device_name,
                "command": command,
                "output": result,
            }
            sys.stdout.write(json.dumps(event) + "\n")
        elif self.output_format == OutputFormat.RAW:
            sys.stdout.write(f"device={device_name} cmd={command}\n")
            sys.stdout.write(f"{result}\n")
        else:
            console.print("[bold green]Command Output:[/bold green]")
            console.print(f"[white]{result}[/white]")

    def print_sequence_results(
        self, device_name: str, sequence_name: str, results_map: dict[str, str]
    ) -> None:
        """Print sequence results based on output format."""
        if self.output_format == OutputFormat.JSON:
            for cmd, output in results_map.items():
                event = {
                    "event": "result",
                    "device": device_name,
                    "command": cmd,
                    "output": output,
                }
                sys.stdout.write(json.dumps(event) + "\n")
        elif self.output_format == OutputFormat.RAW:
            for cmd, output in results_map.items():
                sys.stdout.write(f"device={device_name} cmd={cmd}\n")
                sys.stdout.write(f"{output}\n")
        else:
            console.print(
                f"[bold green]Sequence Results ({len(results_map)} commands):[/bold green]"
            )
            console.print()
            for i, (cmd, output) in enumerate(results_map.items(), 1):
                console.print(f"[bold cyan]Command {i}:[/bold cyan] {cmd}")
                console.print(f"[white]{output}[/white]")
                console.print("-" * 80)


def create_simple_run_command() -> Any:
    """Create a simplified run command function."""

    def run(
        target: Annotated[
            str, typer.Argument(help="Device/group name or comma-separated list")
        ],
        command_or_sequence: Annotated[
            str, typer.Argument(help="Command or sequence name")
        ],
        *,
        config_file: Annotated[Path, typer.Option("--config", "-c")] = Path(
            "devices.yml"
        ),
        verbose: Annotated[bool, typer.Option("--verbose", "-v")] = False,
        store_results: Annotated[bool, typer.Option("--store-results", "-s")] = False,
        results_dir: Annotated[str | None, typer.Option("--results-dir")] = None,
        output_format: Annotated[
            OutputFormat, typer.Option("--format")
        ] = OutputFormat.NORMAL,
    ) -> None:
        """Execute a command or sequence on device(s) or group(s)."""
        if output_format == OutputFormat.NORMAL:
            setup_logging("DEBUG" if verbose else "INFO")

        start_time = perf_counter()

        try:
            # Load configuration and create dependencies
            config = load_config(config_file)
            resolver = DeviceResolver(config)
            sequence_manager = SequenceManager(config)

            cmd_ctx = f"run_{target}_{command_or_sequence}"
            results_manager = ResultsManager(
                config,
                store_results=store_results,
                results_dir=results_dir,
                command_context=cmd_ctx,
            )

            # Resolve targets
            resolved_devices, unknown_targets = resolver.resolve_targets(target)

            if unknown_targets and not resolved_devices:
                print_error(
                    console,
                    f"target(s) not found: {', '.join(unknown_targets)}",
                    exit_code=1,
                )

            if unknown_targets and output_format == OutputFormat.NORMAL:
                console.print(
                    f"[yellow]Warning: ignoring unknown target(s): "
                    f"{', '.join(unknown_targets)}[/yellow]"
                )

            # Create executor
            executor = RunExecutor(
                config=config,
                resolver=resolver,
                sequence_manager=sequence_manager,
                results_manager=results_manager,
                output_format=output_format,
                verbose=verbose,
            )

            # Determine operation type
            is_sequence = sequence_manager.exists(command_or_sequence)
            is_single_device = len(resolved_devices) == 1

            # Execute operation
            if is_sequence:
                if is_single_device:
                    _execute_sequence_single_device(
                        executor, resolved_devices[0], command_or_sequence, target
                    )
                else:
                    _execute_sequence_multiple_devices(
                        executor, resolved_devices, command_or_sequence, target
                    )
            elif is_single_device:
                _execute_command_single_device(
                    executor, resolved_devices[0], command_or_sequence, target
                )
            else:
                _execute_command_multiple_devices(
                    executor, resolved_devices, command_or_sequence, target
                )

            # Print summary
            if output_format == OutputFormat.NORMAL:
                duration = perf_counter() - start_time
                _print_execution_summary(
                    target,
                    command_or_sequence,
                    is_sequence,
                    len(resolved_devices),
                    duration,
                )

        except NetworkToolkitError as e:
            if output_format == OutputFormat.NORMAL:
                print_error(console, e.message, e.details if verbose else None)
            raise typer.Exit(1) from None
        except Exception as e:
            if output_format == OutputFormat.NORMAL:
                print_error(console, f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    return run


def _execute_sequence_single_device(
    executor: RunExecutor, device_name: str, sequence_name: str, target_label: str
) -> None:
    """Execute sequence on single device."""
    if executor.output_format == OutputFormat.NORMAL:
        transport_type = executor.config.get_transport_type(device_name)
        console.print(
            f"[bold blue]Executing sequence '{sequence_name}' on device {target_label}[/bold blue]"
        )
        _print_info(f"Transport: {transport_type}")
        console.print()

    results_map, error = executor.execute_sequence_on_device(device_name, sequence_name)

    if error:
        if executor.output_format == OutputFormat.NORMAL:
            print_error(
                executor.console if hasattr(executor, "console") else console, error
            )
        raise typer.Exit(1)

    if results_map:
        executor.print_sequence_results(device_name, sequence_name, results_map)

        # Store results if enabled
        if executor.results_manager.store_results:
            stored_paths = executor.results_manager.store_sequence_results(
                device_name, sequence_name, results_map
            )
            if stored_paths and executor.output_format == OutputFormat.NORMAL:
                console.print(f"\n[dim]Results stored: {stored_paths[-1]}[/dim]")


def _execute_sequence_multiple_devices(
    executor: RunExecutor, devices: list[str], sequence_name: str, target_label: str
) -> None:
    """Execute sequence on multiple devices."""
    if executor.output_format == OutputFormat.NORMAL:
        console.print(
            f"[bold blue]Executing sequence '{sequence_name}' on group {target_label} "
            f"({len(devices)} devices)[/bold blue]"
        )
        console.print()

    success_count = 0
    for device_name in devices:
        results_map, error = executor.execute_sequence_on_device(
            device_name, sequence_name
        )

        if error:
            if executor.output_format == OutputFormat.NORMAL:
                print_error(console, error, context=device_name)
        else:
            success_count += 1
            if results_map:
                executor.print_sequence_results(device_name, sequence_name, results_map)

    if executor.output_format == OutputFormat.NORMAL:
        console.print(
            f"\n[bold]Group Summary:[/bold] {success_count}/{len(devices)} devices succeeded"
        )

    if success_count < len(devices):
        raise typer.Exit(1)


def _execute_command_single_device(
    executor: RunExecutor, device_name: str, command: str, target_label: str
) -> None:
    """Execute command on single device."""
    if executor.output_format == OutputFormat.NORMAL:
        transport_type = executor.config.get_transport_type(device_name)
        console.print(
            f"[bold blue]Executing command on device {target_label}[/bold blue]"
        )
        _print_info(f"Command: {command}")
        _print_info(f"Transport: {transport_type}")
        console.print()

    result, error = executor.execute_command_on_device(device_name, command)

    if error:
        if executor.output_format == OutputFormat.NORMAL:
            print_error(console, error)
        raise typer.Exit(1)

    executor.print_result(device_name, command, result)

    # Store results if enabled
    if executor.results_manager.store_results and result:
        stored_path = executor.results_manager.store_command_result(
            device_name, command, result
        )
        if stored_path and executor.output_format == OutputFormat.NORMAL:
            console.print(f"\n[dim]Results stored: {stored_path}[/dim]")


def _execute_command_multiple_devices(
    executor: RunExecutor, devices: list[str], command: str, target_label: str
) -> None:
    """Execute command on multiple devices."""
    if executor.output_format == OutputFormat.NORMAL:
        console.print(
            f"[bold blue]Executing command on group {target_label} "
            f"({len(devices)} devices)[/bold blue]"
        )
        _print_info(f"Command: {command}")
        console.print()

    success_count = 0
    for device_name in devices:
        result, error = executor.execute_command_on_device(device_name, command)

        if error:
            if executor.output_format == OutputFormat.NORMAL:
                print_error(console, error, context=device_name)
        else:
            success_count += 1
            executor.print_result(device_name, command, result)

    if executor.output_format == OutputFormat.NORMAL:
        console.print(
            f"\n[bold]Group Summary:[/bold] {success_count}/{len(devices)} devices succeeded"
        )

    if success_count < len(devices):
        raise typer.Exit(1)


def _print_execution_summary(
    target: str,
    command_or_sequence: str,
    is_sequence: bool,
    device_count: int,
    duration: float,
) -> None:
    """Print execution summary."""
    operation_type = "Sequence" if is_sequence else "Command"
    console.print("\n[bold cyan]Execution Summary[/bold cyan]")
    console.print(f"  [bold]Target:[/bold] {target}")
    console.print(f"  [bold]Type:[/bold] {operation_type}")
    console.print(f"  [bold]Name:[/bold] {command_or_sequence}")
    console.print(f"  [bold]Devices:[/bold] {device_count}")
    console.print(f"  [bold]Duration:[/bold] {duration:.2f}s")
