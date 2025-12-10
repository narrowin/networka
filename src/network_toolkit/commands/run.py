# SPDX-License-Identifier: MIT
"""`nw run` command implementation (thin CLI wrapper over library API)."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.api.run import (
    DeviceCommandResult,
    DeviceSequenceResult,
    RunOptions,
    TargetResolutionError,
    run_commands,
)
from network_toolkit.common.command import CommandContext
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import (
    OutputMode,
    get_output_mode_from_config,
    set_output_mode,
)
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.ip_device import is_ip_list
from network_toolkit.results_enhanced import ResultsManager
from network_toolkit.transport.factory import get_transport_factory


class RawFormat(str, Enum):
    """Supported raw output formats."""

    TXT = "txt"
    JSON = "json"


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
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
        no_strict_host_key_checking: Annotated[
            bool,
            typer.Option(
                "--no-strict-host-key-checking",
                help="Disable strict SSH host key checking (insecure, use only in lab environments)",
            ),
        ] = False,
    ) -> None:
        """Execute a single command or a sequence on a device or a group."""
        # Validate transport type early to preserve current CLI behavior
        if transport_type is not None:
            try:
                get_transport_factory(transport_type)
            except ValueError as exc:
                typer.echo(f"Error: {exc}", err=True)
                raise typer.Exit(1) from exc

        if raw is not None:
            output_mode = OutputMode.RAW

        config = None
        if is_ip_list(target) and interactive_auth and device_type:
            from network_toolkit.config import create_minimal_config

            config = create_minimal_config()

        ctx = CommandContext(
            output_mode=output_mode,
            verbose=verbose,
            config_file=config_file,
            config=config,
        )

        # Allow config-driven output mode when CLI flag not set
        output_mgr = ctx.output
        if output_mode is None:
            chosen_mode = get_output_mode_from_config(
                getattr(getattr(ctx.config, "general", None), "output_mode", None)
            )
            output_mgr = set_output_mode(chosen_mode)

        interactive_creds = None
        if interactive_auth:
            if output_mode != OutputMode.RAW:
                ctx.print_info("Interactive authentication mode enabled")
            interactive_creds = prompt_for_credentials(
                "Enter username for devices",
                "Enter password for devices",
                "admin",
            )
            if output_mode != OutputMode.RAW:
                ctx.print_success(f"Will use username: {interactive_creds.username}")

        def _print_results_dir_once(results_mgr: ResultsManager | None) -> None:
            if (
                results_mgr
                and results_mgr.store_results
                and results_mgr.session_dir
                and output_mode != OutputMode.RAW
            ):
                output_mgr.print_results_directory(str(results_mgr.session_dir))

        def _print_run_summary(
            *,
            target_label: str,
            op_type: str,
            name: str,
            duration: float,
            results_mgr: ResultsManager | None,
            is_group: bool = False,
            totals: tuple[int, int, int] | None = None,
        ) -> None:
            results_dir = (
                str(results_mgr.session_dir)
                if results_mgr and results_mgr.store_results and results_mgr.session_dir
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

        def _print_unknown_targets(unknown: list[str]) -> None:
            if unknown and output_mode != OutputMode.RAW:
                ctx.print_warning(
                    f"Warning: ignoring unknown target(s): {', '.join(unknown)}"
                )

        def _print_notices(notices: list[str]) -> None:
            if output_mode == OutputMode.RAW:
                return
            for message in notices:
                ctx.print_info(message)

        try:
            options = RunOptions(
                target=target,
                command_or_sequence=command_or_sequence,
                config=ctx.config,
                device_type=device_type,
                port=port,
                transport_type=transport_type,
                interactive_creds=interactive_creds,
                store_results=store_results,
                results_dir=results_dir,
                no_strict_host_key_checking=no_strict_host_key_checking,
            )
            run_result = run_commands(options)
        except TargetResolutionError as exc:
            if output_mode != OutputMode.RAW:
                ctx.print_error(exc.message)
                if exc.unknown_targets:
                    ctx.print_info(
                        f"Unresolved target(s): {', '.join(exc.unknown_targets)}"
                    )
            raise typer.Exit(1) from exc
        except NetworkToolkitError as exc:
            if output_mode != OutputMode.RAW:
                output_mgr.print_error(f"Error: {exc.message}")
            raise typer.Exit(1) from exc
        except Exception as exc:  # pragma: no cover - unexpected
            if output_mode != OutputMode.RAW:
                output_mgr.print_error(f"Unexpected error: {exc}")
            raise typer.Exit(1) from exc

        json_mode = raw == RawFormat.JSON

        # Warn about unknown targets but continue when at least one device resolved
        _print_unknown_targets(run_result.resolution.unknown)
        _print_notices(run_result.notices)

        def _results_manager_for_printing() -> ResultsManager | None:
            if not store_results:
                return None
            # Mirror results manager used by API for consistent directory handling
            return ResultsManager(
                ctx.config,
                store_results=store_results,
                results_dir=results_dir,
                command_context=f"run_{target}_{command_or_sequence}",
            )

        # Shared ResultsManager instance for summary printing
        printing_results_mgr = (
            _results_manager_for_printing() if run_result.results_dir else None
        )
        if printing_results_mgr and run_result.results_dir:
            printing_results_mgr.session_dir = Path(run_result.results_dir)

        def _print_sequence_result(device_result: DeviceSequenceResult) -> None:
            if output_mode == OutputMode.RAW:
                if not device_result.outputs:
                    return
                for cmd, output in device_result.outputs.items():
                    if json_mode:
                        output_mgr.print_json(
                            {
                                "event": "result",
                                "device": device_result.device,
                                "cmd": cmd,
                                "output": output,
                            }
                        )
                    else:
                        output_mgr.print_command_output(
                            device_result.device, cmd, output
                        )
                return

            output_mgr.print_info(f"Device: {device_result.device}")
            if device_result.error:
                output_mgr.print_error("Failed", device_result.device)
                output_mgr.print_error(device_result.error, device_result.device)
                output_mgr.print_blank_line()
                return

            output_mgr.print_success("Success", device_result.device)
            if device_result.outputs:
                output_mgr.print_info(
                    f"Commands executed: {len(device_result.outputs)}",
                    device_result.device,
                )
                output_mgr.print_blank_line()
                for i, (cmd, output) in enumerate(device_result.outputs.items(), 1):
                    output_mgr.print_info(f"Command {i}: {cmd}")
                    output_mgr.print_output(output)
                    if i < len(device_result.outputs):
                        output_mgr.print_separator()
            output_mgr.print_blank_line()

        def _print_command_result(device_result: DeviceCommandResult) -> None:
            if output_mode == OutputMode.RAW:
                if device_result.error or device_result.output is None:
                    return
                if json_mode:
                    output_mgr.print_json(
                        {
                            "event": "result",
                            "device": device_result.device,
                            "cmd": device_result.command,
                            "output": device_result.output,
                        }
                    )
                else:
                    output_mgr.print_command_output(
                        device_result.device,
                        device_result.command,
                        device_result.output,
                    )
                return

            output_mgr.print_info(f"Device: {device_result.device}")
            if device_result.error:
                output_mgr.print_error("Failed", device_result.device)
                output_mgr.print_error(device_result.error, device_result.device)
            else:
                output_mgr.print_success("Success", device_result.device)
                if device_result.output:
                    output_mgr.print_blank_line()
                    output_mgr.print_output(device_result.output)
            output_mgr.print_blank_line()

        if run_result.is_sequence:
            # Sequence execution
            if not run_result.is_group:
                device_result = run_result.sequence_results[0]
                if output_mode != OutputMode.RAW:
                    ctx.print_info(
                        f"Executing sequence '{command_or_sequence}' on device {run_result.resolution.resolved[0]}"
                    )
                    output_mgr.print_blank_line()

                if device_result.error:
                    if output_mode != OutputMode.RAW:
                        ctx.print_error(f"Error: {device_result.error}")
                    raise typer.Exit(1)

                _print_sequence_result(device_result)

                if (
                    store_results
                    and device_result.stored_paths
                    and output_mode != OutputMode.RAW
                ):
                    output_mgr.print_info(
                        f"Results stored: {device_result.stored_paths[-1]}"
                    )
                    _print_results_dir_once(printing_results_mgr)

                _print_run_summary(
                    target_label=device_result.device,
                    op_type="Sequence",
                    name=command_or_sequence,
                    duration=run_result.duration,
                    results_mgr=printing_results_mgr,
                    is_group=False,
                )

                if json_mode:
                    output_mgr.print_json(
                        {
                            "event": "summary",
                            "target": device_result.device,
                            "type": "Sequence",
                            "name": command_or_sequence,
                            "duration": run_result.duration,
                            "succeeded": not device_result.error,
                        }
                    )
                return

            # Group sequence
            members = run_result.resolution.resolved
            if output_mode != OutputMode.RAW:
                ctx.print_info(
                    f"Executing sequence '{command_or_sequence}' on targets '{target}' "
                    f"({len(members)} devices)"
                )
                ctx.print_info(f"Members: {', '.join(members)}")
                output_mgr.print_blank_line()

            for device_result in run_result.sequence_results:
                _print_sequence_result(device_result)

            if store_results and output_mode != OutputMode.RAW:
                _print_results_dir_once(printing_results_mgr)

            _print_run_summary(
                target_label=target,
                op_type="Sequence",
                name=command_or_sequence,
                duration=run_result.duration,
                results_mgr=printing_results_mgr,
                is_group=True,
                totals=(
                    run_result.totals.total,
                    run_result.totals.succeeded,
                    run_result.totals.failed,
                ),
            )

            if json_mode:
                output_mgr.print_json(
                    {
                        "event": "summary",
                        "target": target,
                        "type": "Sequence",
                        "name": command_or_sequence,
                        "duration": run_result.duration,
                        "total": run_result.totals.total,
                        "succeeded": run_result.totals.succeeded,
                        "failed": run_result.totals.failed,
                    }
                )
            return

        # Single command execution
        if not run_result.is_group:
            device_result = run_result.command_results[0]
            if output_mode != OutputMode.RAW:
                ctx.print_info(
                    f"Executing command on device {run_result.resolution.resolved[0]}"
                )
                ctx.print_info(f"Command: {command_or_sequence}")
                output_mgr.print_blank_line()

            if device_result.error:
                raise typer.Exit(1)

            _print_command_result(device_result)

            if (
                store_results
                and device_result.stored_path
                and output_mode != OutputMode.RAW
            ):
                output_mgr.print_blank_line()
                output_mgr.print_info(f"Results stored: {device_result.stored_path}")
                _print_results_dir_once(printing_results_mgr)

            _print_run_summary(
                target_label=device_result.device,
                op_type="Command",
                name=command_or_sequence,
                duration=run_result.duration,
                results_mgr=printing_results_mgr,
                is_group=False,
            )

            if json_mode:
                output_mgr.print_json(
                    {
                        "event": "summary",
                        "target": device_result.device,
                        "type": "Command",
                        "name": command_or_sequence,
                        "duration": run_result.duration,
                        "succeeded": not device_result.error,
                    }
                )
            return

        # Group single command
        members = run_result.resolution.resolved
        if output_mode != OutputMode.RAW:
            ctx.print_info(
                f"Executing command on targets '{target}' ({len(members)} devices)"
            )
            ctx.print_info(f"Command: {command_or_sequence}")
            ctx.print_info(f"Members: {', '.join(members)}")
            output_mgr.print_blank_line()

        for device_result in run_result.command_results:
            _print_command_result(device_result)

        if store_results and output_mode != OutputMode.RAW:
            _print_results_dir_once(printing_results_mgr)

        _print_run_summary(
            target_label=target,
            op_type="Command",
            name=command_or_sequence,
            duration=run_result.duration,
            results_mgr=printing_results_mgr,
            is_group=True,
            totals=(
                run_result.totals.total,
                run_result.totals.succeeded,
                run_result.totals.failed,
            ),
        )

        if json_mode:
            output_mgr.print_json(
                {
                    "event": "summary",
                    "target": target,
                    "type": "Command",
                    "name": command_or_sequence,
                    "duration": run_result.duration,
                    "total": run_result.totals.total,
                    "succeeded": run_result.totals.succeeded,
                    "failed": run_result.totals.failed,
                }
            )
