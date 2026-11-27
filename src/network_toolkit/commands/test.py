# SPDX-License-Identifier: MIT
"""Run lab tests in a containerlab lab, or replay their saved evidence."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from network_toolkit import lab_summary, labtest
from network_toolkit.client import NetworkaClient
from network_toolkit.commands.intent import EXIT_CODES, _error
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH


def _print_result(ctx: CommandContext, result: dict[str, Any]) -> None:
    ctx.console.print(f"Test: {result['name']}", markup=False)
    ctx.console.print(f"Purpose: {result['purpose']}", markup=False)
    for when in ("before", "after"):
        state = result["state"].get(when)
        if state is None:
            continue
        table = Table(title=f"State {when}", show_header=True, header_style="bold")
        table.add_column("State check", overflow="fold")
        table.add_column("Verdict", overflow="fold")
        for state_check in state["state_checks"]:
            notes = [
                f"{c['device']} {c['check']}: {c['verdict']}"
                + (f" ({c['reason']})" if c["reason"] else "")
                for c in state_check["checks"]
                if c["verdict"] != "pass"
            ]
            table.add_row(
                state_check["name"], "\n".join([state_check["verdict"], *notes])
            )
        ctx.console.print(table)
    for reboot in result.get("reboots", {}).values():
        ctx.console.print(
            f"Reboot of {reboot['switch']}: {reboot['verdict']}", markup=False
        )
        if "after_uptime_s" in reboot:
            ctx.console.print(
                f"Uptime {reboot['before_uptime_s']:g} s before, {reboot['after_uptime_s']:g} s after "
                f"{reboot['elapsed_s']:g} s elapsed.",
                markup=False,
            )
        if "recovered_s" in reboot:
            ctx.console.print(
                f"Lab state {reboot['state']} at {reboot['recovered_s']:g} s (limit {reboot['limit_s']:g} s).",
                markup=False,
            )
    if result["steps"]:
        for step in result["steps"]:
            ctx.console.print(
                f"Expected in step {step['name']}: {step['expected']}", markup=False
            )
        table = Table(title="Steps", show_header=True, header_style="bold")
        for column in ("Step", "Stream or log rule", "Measured", "Limit", "Verdict"):
            table.add_column(column, overflow="fold")
        for step in result["steps"]:
            for name, stream in step["streams"].items():
                table.add_row(
                    step["name"],
                    name,
                    stream["summary"],
                    f"{stream['limit_s']:g} s",
                    stream["verdict"]
                    if stream["verdict"] == "pass"
                    else f"{stream['verdict']}: {stream['reason']}",
                )
            for rule in step["log"]:
                table.add_row(
                    step["name"],
                    f"{rule['switch']} {rule['kind']} {rule['text']!r}",
                    rule["reason"],
                    "",
                    rule["verdict"],
                )
        ctx.console.print(table)
    for rule in result["log"]:
        ctx.console.print(
            f"Whole test: {rule['switch']} {rule['kind']} {rule['text']!r}: "
            f"{rule['verdict']} ({rule['reason']})",
            markup=False,
        )
    if closing := result.get("closing"):
        for name, stream in closing["streams"].items():
            ctx.console.print(
                f"After the steps, {name}: {stream['summary']}, {stream['duplicates']} duplicates.",
                markup=False,
            )
    if result["switch_log"] and result["switch_log"].get("lines") is not None:
        counts = ", ".join(f"{s} {n}" for s, n in result["switch_log"]["lines"].items())
        ctx.console.print(f"Switch log lines: {counts or 'none'}", markup=False)
    for reason in result["reasons"]:
        ctx.console.print(reason, markup=False)
    ctx.console.print(f"Test verdict: {result['verdict']}", markup=False)


def register(app: typer.Typer) -> None:
    """Register the test command and its subcommands."""
    test_app = typer.Typer(
        name="test",
        help="Run lab tests in a containerlab lab and replay their saved evidence",
        no_args_is_help=True,
    )

    @test_app.command("run")
    def run_cmd(
        files: Annotated[list[Path], typer.Argument(help="Test files (YAML)")],
        *,
        lab_dir: Annotated[
            Path,
            typer.Option(
                "--lab", help="Lab directory that containerlab wrote (clab-<name>)"
            ),
        ],
        save: Annotated[
            Path,
            typer.Option(
                "--save", "-s", help="Directory for one evidence folder per test"
            ),
        ],
        config_file: Annotated[
            Path,
            typer.Option("--config", "-c", help="Configuration directory or file path"),
        ] = DEFAULT_CONFIG_PATH,
        interactive_auth: Annotated[
            bool,
            typer.Option(
                "--interactive-auth",
                "-i",
                help="Prompt for username and password interactively",
            ),
        ] = False,
    ) -> None:
        """Run each test in the lab, save its evidence, and print the verdicts.

        Needs root on the lab host. Exit status: 0 pass, 1 fail, 2 error (not
        verified, or an unusable file).
        """
        verdicts = []
        try:
            ctx = CommandContext(config_file=config_file)
            tests = [labtest.load_test(file) for file in files]
            run_options: dict[str, Any] = {}
            if interactive_auth:
                run_options["interactive_creds"] = prompt_for_credentials(
                    "Enter username for devices", "Enter password for devices", "admin"
                )
            with NetworkaClient(config_file) as client:
                for test in tests:
                    result = labtest.run_test(
                        client, test, lab_dir, save, **run_options
                    )
                    _print_result(ctx, result)
                    ctx.print_info(f"Evidence saved in {save / test.path.stem}")
                    verdicts.append(result["verdict"])
        except Exception as error:  # no traceback for the operator: exit 2
            raise _error(error) from None
        raise typer.Exit(EXIT_CODES[labtest.rollup(verdicts)])

    @test_app.command("replay")
    def replay_cmd(
        directory: Annotated[
            Path, typer.Argument(help="Evidence folder written by 'nw test run'")
        ],
    ) -> None:
        """Rebuild the report and compare the result bytes from saved lab evidence.

        Exit status: 0 pass, 1 fail, 2 error (not verified, unusable evidence,
        or a result that differs from the saved result.json).
        """
        try:
            ctx = CommandContext()
            result, same = labtest.replay(directory)
            _print_result(ctx, result)
        except Exception as error:  # no traceback for the operator: exit 2
            raise _error(error) from None
        if not same:
            typer.echo(
                f"error: the replayed result differs from {directory / labtest.RESULT_FILE}",
                err=True,
            )
            raise typer.Exit(2)
        raise typer.Exit(EXIT_CODES[result["verdict"]])

    @test_app.command("summary")
    def summary_cmd(
        spec: Annotated[
            Path, typer.Argument(help="Summary file (YAML) naming the saved runs")
        ],
    ) -> None:
        """Write the results table and worst-outage chart from saved test runs.

        Rewrites the lines between the results markers in the Markdown file
        and writes the SVG chart that the summary file names. Exit status: 0
        written, 2 unusable summary file or a missing run or result.
        """
        try:
            ctx = CommandContext()
            for path in lab_summary.summarize(spec):
                ctx.print_info(f"Wrote {path}")
        except Exception as error:  # no traceback for the operator: exit 2
            raise _error(error) from None

    app.add_typer(test_app, rich_help_panel="Remote Operations")


__all__ = ["register"]
