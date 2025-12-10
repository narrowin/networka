"""
Example: Automated Compliance & Health Report

This script demonstrates how to use the Networka library to build a custom
automation workflow. Unlike the CLI, this script defines its own business
logic, runs multiple checks, parses the output programmatically, and
generates a consolidated report.

Usage:
    uv run scripts/compliance_report.py
"""

import sys
from dataclasses import dataclass
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from network_toolkit.api.run import RunOptions, run_commands
from network_toolkit.config import load_config
from network_toolkit.common.credentials import InteractiveCredentials

# --- Configuration / Business Logic ---

# In a real app, these might come from a database, API, or YAML file
TARGET_DEVICE = "192.168.139.192"
TARGET_PLATFORM = "linux"
SSH_USER = "md"

@dataclass
class ComplianceCheck:
    name: str
    command: str
    # A simple validator function that takes the output string and returns bool
    validator: callable

CHECKS = [
    ComplianceCheck(
        name="Kernel Version Check",
        command="uname -r",
        validator=lambda out: "6." in out or "5." in out  # Example: Require kernel 5.x or 6.x
    ),
    ComplianceCheck(
        name="Root Filesystem",
        command="df -h /",
        validator=lambda out: "100%" not in out  # Fail if root is 100% full
    ),
    ComplianceCheck(
        name="System Uptime",
        command="uptime",
        validator=lambda out: "load average" in out
    ),
    ComplianceCheck(
        name="Critical Service (SSH)",
        command="systemctl is-active ssh",
        validator=lambda out: "active" in out
    )
]

# --------------------------------------

def main():
    console = Console()
    console.print(Panel.fit(
        "[bold blue]Networka Library Demo[/bold blue]\n"
        "Automated Compliance Reporting Tool",
        border_style="blue"
    ))

    # 1. Load Networka Configuration
    try:
        config = load_config("config")
    except Exception as e:
        console.print(f"[red]Failed to load config: {e}[/red]")
        return

    # 2. Setup Credentials (programmatic, not interactive CLI prompts)
    # Here we hardcode for the demo, but you could fetch from Vault/Env
    creds = InteractiveCredentials(username=SSH_USER, password="")

    results_table = Table(title="Compliance Report", show_lines=True)
    results_table.add_column("Check Name", style="cyan")
    results_table.add_column("Command", style="dim")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Details")

    success_count = 0

    # 3. Execute the Workflow
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task_id = progress.add_task("Running compliance checks...", total=len(CHECKS))

        for check in CHECKS:
            progress.update(task_id, description=f"Checking: {check.name}")
            
            # --- THE LIBRARY CALL ---
            # Notice how we construct options programmatically for each check
            options = RunOptions(
                target=TARGET_DEVICE,
                command_or_sequence=check.command,
                config=config,
                device_type=TARGET_PLATFORM,
                interactive_creds=creds,
                no_strict_host_key_checking=True, # For lab demo
            )

            try:
                # Execute synchronously (library handles internal concurrency if target was a group)
                run_result = run_commands(options)
                
                # Process the result
                # Since we targeted a single IP, we expect one command result
                if not run_result.command_results:
                    status_str = "[red]NO RESPONSE[/red]"
                    details = "No results returned"
                else:
                    cmd_res = run_result.command_results[0]
                    
                    if cmd_res.error:
                        status_str = "[red]ERROR[/red]"
                        details = f"Connection/Command Error: {cmd_res.error}"
                    else:
                        # --- PROGRAMMATIC VALIDATION ---
                        # This is where using a library shines: we can inspect the output object
                        output_text = cmd_res.output or ""
                        is_compliant = check.validator(output_text)
                        
                        if is_compliant:
                            status_str = "[green]PASS[/green]"
                            details = output_text.strip().split('\n')[0] # Show first line
                            success_count += 1
                        else:
                            status_str = "[bold red]FAIL[/bold red]"
                            details = f"Validation failed. Output:\n{output_text.strip()}"

            except Exception as e:
                status_str = "[red]EXCEPTION[/red]"
                details = str(e)

            results_table.add_row(check.name, check.command, status_str, details)
            progress.advance(task_id)

    # 4. Final Report
    console.print()
    console.print(results_table)
    
    score = (success_count / len(CHECKS)) * 100
    color = "green" if score == 100 else "yellow" if score > 50 else "red"
    console.print(f"Compliance Score: [bold {color}]{score:.1f}%[/bold {color}]")

if __name__ == "__main__":
    sys.exit(main())
