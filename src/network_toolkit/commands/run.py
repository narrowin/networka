# SPDX-License-Identifier: MIT
"""`nw run` command implementation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Annotated, Any

import typer

# Tables and printing routed via OutputManager helpers
from network_toolkit.common.command import CommandContext
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_mode_from_config,
    set_output_mode,
)
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.ip_device import (
    create_ip_based_config,
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_list,
    validate_platform,
)
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.sequence_manager import SequenceManager


class RawFormat(str, Enum):
    """Supported raw output formats."""

    TXT = "txt"
    JSON = "json"


PREVIEW_LEN = 200


def register(app: typer.Typer) -> None:
    @app.command(rich_help_panel="Executing Operations")
    def run(
        target: Annotated[
            str,
            typer.Argument(
                help=(
                    "Device/group name, comma-separated list, or IP addresses. "
                    "For IPs use --platform to specify device type"
                )
            ),
        ],
        command_or_sequence: Annotated[
            str,
            typer.Argument(
                help=("RouterOS command to execute or name of a configured sequence"),
            ),
        ],
        *,
        config_file: Annotated[
            Path,
            typer.Option("--config", "-c", help="Configuration directory or file path"),
        ] = DEFAULT_CONFIG_PATH,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
        store_results: Annotated[
            bool,
            typer.Option(
                "--store-results", "-s", help="Store command results to files"
            ),
        ] = False,
        results_dir: Annotated[
            str | None, typer.Option("--results-dir", help="Override results directory")
        ] = None,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        raw: Annotated[
            RawFormat | None,
            typer.Option(
                "--raw",
                help="Legacy raw output mode - use --output-mode raw instead",
                show_default=False,
                hidden=True,
            ),
        ] = None,
        interactive_auth: Annotated[
            bool,
            typer.Option(
                "--interactive-auth",
                "-i",
                help="Prompt for username and password interactively",
            ),
        ] = False,
        device_type: Annotated[
            str | None,
            typer.Option(
                "--platform",
                "-p",
                help="Device type when using IP addresses (e.g., mikrotik_routeros). Note: This specifies the network driver type, not hardware platform.",
            ),
        ] = None,
        port: Annotated[
            int | None,
            typer.Option(
                "--port",
                help="SSH port when using IP addresses (default: 22)",
            ),
        ] = None,
        transport_type: Annotated[
            str | None,
            typer.Option(
                "--transport",
                "-t",
                help="Transport type to use for connections (currently only scrapli is supported). Defaults to configuration or scrapli.",
            ),
        ] = None,
    ) -> None:
        """Execute a single command or a sequence on a device or a group."""
        # Validate transport type if provided
        if transport_type is not None:
            from network_toolkit.transport.factory import get_transport_factory

            try:
                # This will raise ValueError if transport_type is invalid
                get_transport_factory(transport_type)
            except ValueError as e:
                # Use typer echo for early errors before CommandContext is available
                typer.echo(f"Error: {e}", err=True)
                raise typer.Exit(1)

        # Handle legacy raw mode mapping
        if raw is not None:
            output_mode = OutputMode.RAW

        # Create command context with proper styling/logging
        ctx = CommandContext(
            output_mode=output_mode,
            verbose=verbose,
            config_file=config_file,
        )

        # Handle interactive authentication if requested
        interactive_creds = None
        if interactive_auth:
            if ctx.output.mode != OutputMode.RAW:
                ctx.print_info("Interactive authentication mode enabled")
            interactive_creds = prompt_for_credentials(
                "Enter username for devices",
                "Enter password for devices",
                "admin",  # Default username suggestion
            )
            if ctx.output.mode != OutputMode.RAW:
                ctx.print_success(f"Will use username: {interactive_creds.username}")

        # Track run timing & reporting state
        started_at = perf_counter()
        printed_results_dir = False
        output_mgr = (
            ctx.output
        )  # Use context's output manager (may update after config)

        def _print_results_dir_once(results_mgr: ResultsManager) -> None:
            """Print the results directory once if storing is enabled."""
            nonlocal printed_results_dir
            if (
                results_mgr.store_results
                and results_mgr.session_dir
                and not printed_results_dir
            ):
                output_mgr.print_results_directory(str(results_mgr.session_dir))
                printed_results_dir = True

        def _print_run_summary(
            *,
            target_label: str,
            op_type: str,  # "Command" | "Sequence"
            name: str,
            duration: float,
            results_mgr: ResultsManager,
            is_group: bool = False,
            totals: tuple[int, int, int] | None = None,
            raw_mode: bool = False,
        ) -> None:
            """
            Render an end-of-run summary.

            Skips printing for device command in raw output mode.
            """
            results_dir = (
                str(results_mgr.session_dir)
                if results_mgr.store_results and results_mgr.session_dir
                else None
            )

            output_mgr.print_summary(
                target=target_label,
                operation_type=op_type,
                name=name,
                duration=duration,
                is_group=is_group,
                totals=totals,
                results_dir=results_dir,
            )

        def _run_command_on_device(
            device_name: str,
            config: Any,
            cmd: str,
            username_override: str | None = None,
            password_override: str | None = None,
            transport_override: str | None = None,
        ) -> tuple[str, str | None, str | None]:
            # Late import to allow tests to patch `network_toolkit.cli.DeviceSession`
            from network_toolkit.cli import DeviceSession

            try:
                with DeviceSession(
                    device_name,
                    config,
                    username_override,
                    password_override,
                    transport_override,
                ) as session:
                    result = session.execute_command(cmd)
                    return (device_name, result, None)
            except NetworkToolkitError as e:  # pragma: no cover - error path
                error_msg = f"Error on {device_name}: {e.message}"
                if verbose and e.details:
                    error_msg += f" | Details: {e.details}"
                if output_mode != OutputMode.RAW:
                    output_mgr.print_error(error_msg, device_name)
                return (device_name, None, e.message)
            except Exception as e:  # pragma: no cover - unexpected
                error_msg = f"Unexpected error on {device_name}: {e}"
                if output_mode != OutputMode.RAW:
                    output_mgr.print_error(error_msg, device_name)
                return (device_name, None, str(e))

        def _run_sequence_on_device(
            device_name: str,
            config: Any,
            seq_name: str,
            username_override: str | None = None,
            password_override: str | None = None,
            transport_override: str | None = None,
        ) -> tuple[str, dict[str, str] | None, str | None]:
            # Import DeviceSession from cli to preserve tests' patch path
            from network_toolkit.cli import DeviceSession

            try:
                with DeviceSession(
                    device_name,
                    config,
                    username_override,
                    password_override,
                    transport_override,
                ) as session:
                    # Use vendor-aware sequence resolution
                    sm = SequenceManager(config)
                    sequence_commands = sm.resolve(seq_name, device_name)
                    if not sequence_commands:
                        msg = f"Sequence '{seq_name}' not found for device type"
                        return (device_name, None, msg)

                    results_map: dict[str, str] = {}
                    for cmd in sequence_commands:
                        output = session.execute_command(cmd)
                        results_map[cmd] = output

                    return (device_name, results_map, None)
            except NetworkToolkitError as e:  # pragma: no cover - error path
                error_msg = f"Error on {device_name}: {e.message}"
                if verbose and e.details:
                    error_msg += f" | Details: {e.details}"
                return (device_name, None, e.message)
            except Exception as e:  # pragma: no cover - unexpected
                return (device_name, None, str(e))

        try:
            config = load_config(config_file)

            # If no CLI output mode given, honor config/general output mode
            # Keep OutputManager as the single source of truth for theming
            if output_mode is None:
                chosen_mode = get_output_mode_from_config(
                    getattr(getattr(config, "general", None), "output_mode", None)
                )
                output_mgr = set_output_mode(chosen_mode)

            # Use output manager for all prints

            # Check if target is IP addresses and handle accordingly
            if is_ip_list(target):
                if device_type is None:
                    supported_platforms = get_supported_platforms()
                    platform_list = "\n".join(
                        [f"  {k}: {v}" for k, v in supported_platforms.items()]
                    )
                    if raw is None:
                        ctx.print_error(
                            "When using IP addresses, --platform is required"
                        )
                        ctx.print_info(f"Supported platforms:\n{platform_list}")
                    raise typer.Exit(1)

                if not validate_platform(device_type):
                    supported_platforms = get_supported_platforms()
                    platform_list = "\n".join(
                        [f"  {k}: {v}" for k, v in supported_platforms.items()]
                    )
                    if raw is None:
                        ctx.print_error(f"Invalid device type '{device_type}'")
                        ctx.print_info(f"Supported platforms:\n{platform_list}")
                    raise typer.Exit(1)

                # Extract IP addresses and create dynamic config
                ips = extract_ips_from_target(target)
                config = create_ip_based_config(
                    ips, device_type, config, port=port, transport_type=transport_type
                )

                if raw is None:
                    ctx.print_info(
                        f"Using IP addresses with device type '{device_type}': {', '.join(ips)}"
                    )

            sm = SequenceManager(config)
            # Provide command context for better results folder naming
            cmd_ctx = f"run_{target}_{command_or_sequence}"
            results_mgr = ResultsManager(
                config,
                store_results=store_results,
                results_dir=results_dir,
                command_context=cmd_ctx,
            )

            # --- Resolve targets (support comma-separated names and IPs) ---
            def resolve_targets(target_expr: str) -> tuple[list[str], list[str]]:
                """Resolve a target expression to concrete device names.

                Returns a tuple (devices, unknowns).
                """
                # If target is IP addresses, the devices were already created
                # with generated names, so we need to get those device names
                if is_ip_list(target_expr):
                    ips = extract_ips_from_target(target_expr)
                    ip_device_names = [f"ip_{ip.replace('.', '_')}" for ip in ips]
                    # All IP devices should exist in config now
                    return ip_device_names, []

                requested = [t.strip() for t in target_expr.split(",") if t.strip()]
                devices: list[str] = []
                unknowns: list[str] = []

                # helpers
                def _add_device(name: str) -> None:
                    if name not in devices:
                        devices.append(name)

                for name in requested:
                    if config.devices and name in config.devices:
                        _add_device(name)
                        continue
                    if config.device_groups and name in config.device_groups:
                        for m in config.get_group_members(name):
                            _add_device(m)
                        continue
                    unknowns.append(name)

                return devices, unknowns

            resolved_devices, unknown_targets = resolve_targets(target)

            if unknown_targets and not resolved_devices:
                if raw is None:
                    output_mgr.print_error(
                        f"target(s) not found: {', '.join(unknown_targets)}"
                    )
                raise typer.Exit(1)
            elif unknown_targets and raw is None:
                ctx.print_warning(
                    f"Warning: ignoring unknown target(s): {', '.join(unknown_targets)}"
                )

            # Determine target mode
            is_single_device = len(resolved_devices) == 1

            # Determine if the provided second argument is a known sequence name
            is_sequence = bool(sm.exists(command_or_sequence))

            # Legacy single-target flags removed; use booleans above directly

            json_mode = raw == RawFormat.JSON

            if is_sequence:
                if is_single_device:
                    if raw is None:
                        ctx.print_info(
                            f"Executing sequence '{command_or_sequence}' on device {target}"
                        )
                        output_mgr.print_blank_line()

                    # Single concrete device
                    device_target = resolved_devices[0]
                    # Get credential overrides if in interactive mode
                    username_override = (
                        interactive_creds.username if interactive_creds else None
                    )
                    password_override = (
                        interactive_creds.password if interactive_creds else None
                    )

                    device_name, results_map, error = _run_sequence_on_device(
                        device_target,
                        config,
                        command_or_sequence,
                        username_override,
                        password_override,
                        transport_type,
                    )

                    if error:
                        if raw is None:
                            ctx.print_error(f"Error: {error}")
                        raise typer.Exit(1)

                    if results_map:
                        if raw is not None:
                            # Print raw outputs with context per command
                            for cmd, output in results_map.items():
                                if json_mode:
                                    output_mgr.print_json(
                                        {
                                            "event": "result",
                                            "device": device_target,
                                            "cmd": cmd,
                                            "output": output,
                                        }
                                    )
                                else:
                                    output_mgr.print_command_output(
                                        device_target, cmd, output
                                    )
                        else:
                            ctx.print_success(
                                f"Sequence Results ({len(results_map)} commands):"
                            )
                            output_mgr.print_blank_line()
                            for i, (cmd, output) in enumerate(results_map.items(), 1):
                                output_mgr.print_info(f"Command {i}: {cmd}")
                                output_mgr.print_output(output)
                                output_mgr.print_separator()

                            if results_mgr.store_results:
                                stored_paths = results_mgr.store_sequence_results(
                                    device_target, command_or_sequence, results_map
                                )
                                if stored_paths:
                                    output_mgr.print_blank_line()
                                    output_mgr.print_info(
                                        f"Results stored: {stored_paths[-1]}"
                                    )
                                    _print_results_dir_once(results_mgr)

                        duration = perf_counter() - started_at
                        _print_run_summary(
                            target_label=device_target,
                            op_type="Sequence",
                            name=command_or_sequence,
                            duration=duration,
                            results_mgr=results_mgr,
                            is_group=False,
                            raw_mode=raw is not None,
                        )
                        if json_mode:
                            output_mgr.print_json(
                                {
                                    "event": "summary",
                                    "target": device_target,
                                    "type": "Sequence",
                                    "name": command_or_sequence,
                                    "duration": duration,
                                    "succeeded": True,
                                }
                            )
                else:
                    group_members = resolved_devices
                    if not group_members:
                        if raw is None:
                            ctx.print_warning(f"No devices resolved for '{target}'.")
                        return

                    if raw is None:
                        ctx.print_info(
                            f"Executing sequence '{command_or_sequence}' on targets '{target}' "
                            f"({len(group_members)} devices)"
                        )
                        ctx.print_info(f"Members: {', '.join(group_members)}")
                        output_mgr.print_blank_line()

                    with ThreadPoolExecutor(max_workers=len(group_members)) as executor:
                        # Get credential overrides if in interactive mode
                        username_override = (
                            interactive_creds.username if interactive_creds else None
                        )
                        password_override = (
                            interactive_creds.password if interactive_creds else None
                        )

                        seq_future_to_device = {
                            executor.submit(
                                _run_sequence_on_device,
                                device,
                                config,
                                command_or_sequence,
                                username_override,
                                password_override,
                                transport_type,
                            ): device
                            for device in group_members
                        }

                        all_results: list[
                            tuple[str, dict[str, str] | None, str | None]
                        ] = []
                        for seq_future in as_completed(seq_future_to_device):
                            all_results.append(seq_future.result())

                    if raw is not None:
                        # Preserve device order from group for deterministic output
                        order_index = {d: i for i, d in enumerate(group_members)}
                        for _device_name, device_results, error in sorted(
                            all_results, key=lambda x: order_index.get(x[0], 0)
                        ):
                            if error or not device_results:
                                # In raw mode, skip errors/no output
                                continue
                            for cmd, output in device_results.items():
                                if json_mode:
                                    output_mgr.print_json(
                                        {
                                            "event": "result",
                                            "device": _device_name,
                                            "cmd": cmd,
                                            "output": output,
                                        }
                                    )
                                else:
                                    output_mgr.print_command_output(
                                        _device_name, cmd, output
                                    )
                    else:
                        ctx.print_success("Group Sequence Results")
                        for device_name, device_results, error in all_results:
                            # Print a simple device header and status lines (no tables)
                            output_mgr.print_separator()
                            output_mgr.print_info(f"Device: {device_name}")
                            if error:
                                output_mgr.print_error("Failed", device_name)
                                output_mgr.print_error(str(error), device_name)
                            else:
                                output_mgr.print_success("Success", device_name)
                                if device_results:
                                    output_mgr.print_info(
                                        f"Commands executed: {len(device_results)}",
                                        device_name,
                                    )
                            output_mgr.print_blank_line()

                    if results_mgr.store_results:
                        # Store per-device results and a group summary file
                        for device_name, device_results, error in all_results:
                            if device_results and not error:
                                results_mgr.store_sequence_results(
                                    device_name, command_or_sequence, device_results
                                )
                        stored = results_mgr.store_group_results(
                            group_name=target,
                            command_or_sequence=command_or_sequence,
                            group_results=all_results,
                            is_sequence=True,
                        )
                        if stored:
                            _print_results_dir_once(results_mgr)

                    # End-of-run summary for group + sequence
                    duration = perf_counter() - started_at
                    succeeded = sum(1 for _, r, e in all_results if r and not e)
                    failed = sum(1 for _, _, e in all_results if e)
                    _print_run_summary(
                        target_label=target,
                        op_type="Sequence",
                        name=command_or_sequence,
                        duration=duration,
                        results_mgr=results_mgr,
                        is_group=True,
                        totals=(len(group_members), succeeded, failed),
                        raw_mode=raw is not None,
                    )
                    if json_mode:
                        output_mgr.print_json(
                            {
                                "event": "summary",
                                "target": target,
                                "type": "Sequence",
                                "name": command_or_sequence,
                                "duration": duration,
                                "total": len(group_members),
                                "succeeded": succeeded,
                                "failed": failed,
                            }
                        )

                return  # Done handling sequence

            # Otherwise, handle as a single command
            if is_single_device:
                if raw is None:
                    device_target = resolved_devices[0]
                    ctx.print_info(f"Executing command on device {device_target}")
                    ctx.print_info(f"Command: {command_or_sequence}")
                    output_mgr.print_blank_line()

                device_target = resolved_devices[0]
                # Get credential overrides if in interactive mode
                username_override = (
                    interactive_creds.username if interactive_creds else None
                )
                password_override = (
                    interactive_creds.password if interactive_creds else None
                )

                device_name, result, error = _run_command_on_device(
                    device_target,
                    config,
                    command_or_sequence,
                    username_override,
                    password_override,
                    transport_type,
                )
                if error:
                    raise typer.Exit(1)

                if raw is not None:
                    if json_mode:
                        output_mgr.print_json(
                            {
                                "event": "result",
                                "device": device_target,
                                "cmd": command_or_sequence,
                                "output": result,
                            }
                        )
                    else:
                        output_mgr.print_command_output(
                            device_target, command_or_sequence, result or ""
                        )
                else:
                    output_mgr.print_command_output(
                        device_target, command_or_sequence, result or ""
                    )

                if results_mgr.store_results and raw is None and result:
                    stored_path = results_mgr.store_command_result(
                        device_target, command_or_sequence, result
                    )
                    if stored_path:
                        output_mgr.print_blank_line()
                        output_mgr.print_info(f"Results stored: {stored_path}")
                        _print_results_dir_once(results_mgr)

                duration = perf_counter() - started_at
                _print_run_summary(
                    target_label=device_target,
                    op_type="Command",
                    name=command_or_sequence,
                    duration=duration,
                    results_mgr=results_mgr,
                    is_group=False,
                    raw_mode=raw is not None,
                )
                if json_mode:
                    output_mgr.print_json(
                        {
                            "event": "summary",
                            "target": device_target,
                            "type": "Command",
                            "name": command_or_sequence,
                            "duration": duration,
                            "succeeded": True,
                        }
                    )

            else:
                members = resolved_devices
                if not members:
                    if raw is None:
                        ctx.print_warning(f"No devices resolved for '{target}'.")
                    return

                if raw is None:
                    ctx.print_info(
                        f"Executing command on targets '{target}' "
                        f"({len(members)} devices)"
                    )
                    ctx.print_info(f"Command: {command_or_sequence}")
                    ctx.print_info(f"Members: {', '.join(members)}")
                    output_mgr.print_blank_line()

                with ThreadPoolExecutor(max_workers=len(members)) as executor:
                    # Get credential overrides if in interactive mode
                    username_override = (
                        interactive_creds.username if interactive_creds else None
                    )
                    password_override = (
                        interactive_creds.password if interactive_creds else None
                    )

                    future_to_device_cmd = {
                        executor.submit(
                            _run_command_on_device,
                            device,
                            config,
                            command_or_sequence,
                            username_override,
                            password_override,
                            transport_type,
                        ): device
                        for device in members
                    }

                    group_results: list[tuple[str, str | None, str | None]] = []
                    for future in as_completed(future_to_device_cmd):
                        group_results.append(future.result())

                if raw is not None:
                    # Emit raw results per device (skip errors in raw mode)
                    for device_name, out_text, error in group_results:
                        if error or out_text is None:
                            continue
                        if json_mode:
                            output_mgr.print_json(
                                {
                                    "event": "result",
                                    "device": device_name,
                                    "cmd": command_or_sequence,
                                    "output": out_text,
                                }
                            )
                        else:
                            output_mgr.print_command_output(
                                device_name, command_or_sequence, out_text
                            )
                else:
                    ctx.print_success("Group Command Results:")
                    for device_name, out_text, error in group_results:
                        # Print a simple device header and status lines (no tables)
                        output_mgr.print_separator()
                        output_mgr.print_info(f"Device: {device_name}")
                        if error:
                            output_mgr.print_error("Failed", device_name)
                            output_mgr.print_error(str(error), device_name)
                        else:
                            output_mgr.print_success("Success", device_name)
                            if out_text:
                                output_mgr.print_blank_line()
                                output_mgr.print_output(out_text)
                        output_mgr.print_blank_line()

                if results_mgr.store_results:
                    # Store per-device results and a group summary file
                    for device_name, out_text, error in group_results:
                        if out_text and not error:
                            results_mgr.store_command_result(
                                device_name, command_or_sequence, out_text
                            )
                    stored = results_mgr.store_group_results(
                        group_name=target,
                        command_or_sequence=command_or_sequence,
                        group_results=group_results,
                        is_sequence=False,
                    )
                    if stored:
                        _print_results_dir_once(results_mgr)

                # End-of-run summary for group + single command
                duration = perf_counter() - started_at
                succeeded = sum(1 for _, o, e in group_results if o and not e)
                failed = sum(1 for _, _, e in group_results if e)
                _print_run_summary(
                    target_label=target,
                    op_type="Command",
                    name=command_or_sequence,
                    duration=duration,
                    results_mgr=results_mgr,
                    is_group=True,
                    totals=(len(members), succeeded, failed),
                    raw_mode=raw is not None,
                )
                if json_mode:
                    output_mgr.print_json(
                        {
                            "event": "summary",
                            "target": target,
                            "type": "Command",
                            "name": command_or_sequence,
                            "duration": duration,
                            "total": len(members),
                            "succeeded": succeeded,
                            "failed": failed,
                        }
                    )

        except NetworkToolkitError as e:
            if raw is None:
                output_mgr.print_error(f"Error: {e.message}")
                if verbose and e.details:
                    output_mgr.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except typer.Exit:
            # Re-raise typer.Exit without catching it as an unexpected error
            raise
        except Exception as e:  # pragma: no cover - unexpected
            if raw is None:
                output_mgr.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None
