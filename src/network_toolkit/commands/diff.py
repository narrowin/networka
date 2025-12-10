"""`nw diff` command implementation.

Provides smart diffing of device configuration and operational state:
 - Config diff: compares current RouterOS export (compact) with a baseline file
 - Command diff: compares a single command output with a baseline file
 - Sequence diff: compares a sequence's per-command outputs with files in a baseline directory

Subject-based UX:
    nw diff <targets> <subject>
Where subject is one of:
    - "config" (special keyword for /export compact)
    - "/..." (a RouterOS command)
    - a sequence name (resolved per-device)

Device-to-device: if exactly two devices are provided and no --baseline is supplied,
the command compares outputs directly between the devices.

Exit codes:
 - 0: No differences
 - 1: Differences found or baseline missing/mismatched
 - 2: Usage / configuration error (bad inputs)
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.markup import escape
from rich.syntax import Syntax

from network_toolkit.api.diff import DiffItemResult, DiffOptions, diff_targets
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import OutputMode
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    @app.command(
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def diff(
        target: Annotated[
            str,
            typer.Argument(
                help=(
                    "Device/group name or comma-separated list (e.g. 'sw-1,lab_devices')"
                ),
            ),
        ],
        subject: Annotated[
            str,
            typer.Argument(
                help=(
                    "Subject to diff: 'config' for /export compact, a RouterOS command "
                    "starting with '/', or the name of a configured sequence."
                ),
            ),
        ],
        *,
        baseline: Annotated[
            Path | None,
            typer.Option(
                "--baseline",
                "-b",
                help=(
                    "Baseline file (for config/command) or directory (for sequence)."
                ),
            ),
        ] = None,
        ignore: Annotated[
            list[str] | None,
            typer.Option(
                "--ignore",
                help=("Regex to ignore lines; repeat for multiple patterns."),
            ),
        ] = None,
        save_current: Annotated[
            Path | None,
            typer.Option(
                "--save-current",
                help=(
                    "Optional path to save the current fetched state "
                    "(file or directory)."
                ),
            ),
        ] = None,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
        store_results: Annotated[
            bool,
            typer.Option(
                "--store-results",
                "-s",
                help="Store diff outputs to files",
            ),
        ] = False,
        results_dir: Annotated[
            str | None,
            typer.Option("--results-dir", help="Override results directory"),
        ] = None,
    ) -> None:
        """Diff config, a command, or a sequence.

        Examples:
          - nw diff sw-acc1 config -b baseline/export_compact.txt
          - nw diff sw-acc1 "/system/resource/print" -b baseline/resource.txt
          - nw diff lab_devices system_info -b baseline_dir/
          - nw diff sw-acc1,sw-acc2 "/system/resource/print"   # device-to-device
          - nw diff sw-acc1,sw-acc2 config                      # device-to-device
        """
        # Create command context with proper styling
        ctx = CommandContext(
            output_mode=output_mode,
            verbose=verbose,
            config_file=config_file,
        )

        try:
            config = load_config(config_file)
        except Exception as e:  # pragma: no cover - load errors covered elsewhere
            ctx.print_error(f"Failed to load config: {e}")
            raise typer.Exit(2) from None

        options = DiffOptions(
            targets=target,
            subject=subject,
            config=config,
            baseline=baseline,
            ignore_patterns=ignore,
            save_current=save_current,
            store_results=store_results,
            results_dir=results_dir,
            verbose=verbose,
        )

        try:
            result = diff_targets(options)
        except NetworkToolkitError as e:
            # Map specific errors to exit code 2 for backward compatibility
            if "Baseline path is required" in str(e) or "Target(s) not found" in str(e):
                ctx.print_error(f"Error: {e}")
                raise typer.Exit(2) from None
            ctx.print_error(f"Error: {e}")
            raise typer.Exit(1) from None

        # Display results
        if not result.results:
            ctx.print_warning("No results produced.")
            # If we expected results but got none (e.g. sequence empty), maybe exit 0 or 1?
            # Original code didn't handle this explicitly as "no results" usually meant error.
            return

        # Group results by device (or pair)
        grouped_results: dict[str, list[DiffItemResult]] = {}
        for item in result.results:
            if item.device not in grouped_results:
                grouped_results[item.device] = []
            grouped_results[item.device].append(item)

        has_errors = False
        for device, items in grouped_results.items():
            ctx.print_operation_header("Diff Report", device)

            for item in items:
                if item.error:
                    # Escape brackets to prevent Rich from interpreting them as tags
                    # especially since /command looks like a closing tag [/command]
                    safe_subject = escape(item.subject)
                    ctx.print_error(f"\\[{safe_subject}] Error: {item.error}")
                    has_errors = True
                    continue

                if not item.outcome:
                    continue

                status = (
                    "[red]CHANGED[/red]"
                    if item.outcome.changed
                    else "[green]MATCH[/green]"
                )
                ctx.console.print(
                    f"  Subject: [bold]{escape(item.subject)}[/bold] -> {status}"
                )

                if item.outcome.changed:
                    # Print diff output
                    # Use Syntax highlighting for diff
                    syntax = Syntax(
                        item.outcome.output, "diff", theme="monokai", line_numbers=False
                    )
                    ctx.console.print(syntax)
                    ctx.print_blank_line()

        if result.total_changed > 0 or result.total_missing > 0 or has_errors:
            msg = []
            if result.total_changed > 0:
                msg.append(f"{result.total_changed} differences found")
            if result.total_missing > 0:
                msg.append(f"{result.total_missing} baselines missing")
            if has_errors:
                msg.append("errors occurred")

            if msg:
                ctx.print_warning(", ".join(msg))
            raise typer.Exit(1)
        else:
            ctx.print_success("No differences found.")
