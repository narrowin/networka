# SPDX-License-Identifier: MIT
"""Run an intent file against devices, or replay saved intent evidence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.table import Table

from network_toolkit import intent
from network_toolkit.client import NetworkaClient
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.credentials import prompt_for_credentials
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.exceptions import NetworkToolkitError

# Exit status per roll-up verdict. An unusable file or evidence also exits 2.
EXIT_CODES = {"pass": 0, "fail": 1, "unverified": 2}


def _show(value: Any) -> str:
    return "-" if value is None else json.dumps(value, sort_keys=True)


def _print_report(ctx: CommandContext, report: intent.IntentReport) -> None:
    table = Table(show_header=True, header_style="bold")
    for column in ("Item", "Device", "Check", "Expected", "Observed", "Verdict"):
        table.add_column(column, overflow="fold")
    for number, (item, result) in enumerate(report.results, 1):
        verdict = result.verdict + (f": {result.reason}" if result.reason else "")
        table.add_row(
            item.name or str(number),
            item.device,
            item.check,
            _show(result.expected),
            _show(result.observed),
            verdict,
        )
    ctx.console.print(table)
    ctx.console.print(f"Intent verdict: {report.verdict}", markup=False)


def register(app: typer.Typer) -> None:
    """Register the intent command and its subcommands."""
    intent_app = typer.Typer(
        name="intent",
        help="Check device state against an intent file and replay saved evidence",
        no_args_is_help=True,
    )

    @intent_app.command("run")
    def run_cmd(
        file: Annotated[Path, typer.Argument(help="Intent file (YAML list of items)")],
        *,
        save: Annotated[
            Path | None,
            typer.Option(
                "--save", "-s", help="Directory for intent.yaml and evidence.json"
            ),
        ] = None,
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
        """Read every item from its device, check it, and print the verdicts.

        Exit status: 0 pass, 1 fail, 2 unverified or an unusable intent file.
        """
        ctx = CommandContext(config_file=config_file)
        run_options: dict[str, Any] = {}
        if interactive_auth:
            run_options["interactive_creds"] = prompt_for_credentials(
                "Enter username for devices", "Enter password for devices", "admin"
            )
        try:
            items = intent.load_intent(file)
            with NetworkaClient(config_file) as client:
                report = intent.run_intent(client, items, save, file, **run_options)
        except NetworkToolkitError as error:
            ctx.print_error(error.message)
            raise typer.Exit(2) from None
        _print_report(ctx, report)
        if save is not None:
            ctx.print_info(f"Evidence saved in {save}")
        raise typer.Exit(EXIT_CODES[report.verdict])

    @intent_app.command("replay")
    def replay_cmd(
        directory: Annotated[
            Path, typer.Argument(help="Directory written by 'nw intent run --save'")
        ],
    ) -> None:
        """Check saved evidence again without devices.

        Exit status: 0 pass, 1 fail, 2 unverified or unusable evidence.
        """
        ctx = CommandContext()
        try:
            report = intent.replay_directory(directory)
        except NetworkToolkitError as error:
            ctx.print_error(error.message)
            raise typer.Exit(2) from None
        _print_report(ctx, report)
        raise typer.Exit(EXIT_CODES[report.verdict])

    app.add_typer(intent_app, rich_help_panel="Remote Operations")


__all__ = ["register"]
