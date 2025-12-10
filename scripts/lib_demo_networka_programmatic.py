"""
Example: Automated Compliance & Health Report

This script demonstrates how to use the Networka library to build a custom
automation workflow. Unlike the CLI, this script defines its own business
logic, runs multiple checks, parses the output programmatically, and
generates a consolidated report.

Usage:
    uv run scripts/lib_demo_networka_programmatic.py
"""

import sys
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from network_toolkit import NetworkaClient
from network_toolkit.common.credentials import InteractiveCredentials
from network_toolkit.device import DeviceSession
from network_toolkit.ip_device import create_ip_based_config

# --- Configuration / Business Logic ---

# Target Selection Strategy:
# 1. PREFERRED_DEVICE_NAME: If this name exists in the loaded config, use it.
#    (Allows using a friendly name with tags, platform, etc. defined in YAML)
# 2. TARGET_IP (in config): If the IP exists as a key in the config, use it.
# 3. TARGET_IP (ad-hoc): If neither above is found, connect directly to this IP.
#    (Requires providing device_type and credentials explicitly)

TARGET_IP = "192.168.139.192"
PREFERRED_DEVICE_NAME = "test_device_192"
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
        validator=lambda out: "6." in out
        or "5." in out,  # Example: Require kernel 5.x or 6.x
    ),
    ComplianceCheck(
        name="Root Filesystem",
        command="df -h /",
        validator=lambda out: "100%" not in out,  # Fail if root is 100% full
    ),
    ComplianceCheck(
        name="System Uptime",
        command="uptime",
        validator=lambda out: "load average" in out,
    ),
    ComplianceCheck(
        name="Critical Service (SSH)",
        command="systemctl is-active ssh",
        validator=lambda out: "active" in out,
    ),
]

# --------------------------------------


def main():
    console = Console()
    console.print(
        Panel.fit(
            "[bold blue]Networka Library Demo[/bold blue]\n"
            "Automated Compliance Reporting Tool",
            border_style="blue",
        )
    )

    # 1. Initialize Networka Client
    # This automatically loads configuration from default locations
    try:
        client = NetworkaClient()
    except Exception as e:
        console.print(f"[red]Failed to initialize client: {e}[/red]")
        return

    # 2. Setup Credentials (programmatic, not interactive CLI prompts)
    # Here we hardcode for the demo, but you could fetch from Vault/Env
    creds = InteractiveCredentials(username=SSH_USER, password="")

    # 3. Determine Target
    # See "Target Selection Strategy" above for details.
    target = TARGET_IP
    config = client.config

    if client.devices and PREFERRED_DEVICE_NAME in client.devices:
        target = PREFERRED_DEVICE_NAME
        console.print(
            f"[green]Found preferred device '{PREFERRED_DEVICE_NAME}' in config. Using it.[/green]"
        )
    elif client.devices and TARGET_IP in client.devices:
        target = TARGET_IP
        console.print(f"[green]Found IP '{TARGET_IP}' in config. Using it.[/green]")
    else:
        console.print(
            f"[yellow]Target '{TARGET_IP}' not found in config. Using as direct IP address.[/yellow]"
        )
        # Create a temporary config for the IP
        config = create_ip_based_config(
            ips=[TARGET_IP],
            device_type=TARGET_PLATFORM,
            base_config=client.config,
        )
        # When using ad-hoc IP config, the device name in the config is generated
        # by create_ip_based_config as "ip_<ip_with_underscores>"
        target = f"ip_{TARGET_IP.replace('.', '_').replace(':', '_')}"

    results_table = Table(title=f"Compliance Report: {target}", show_lines=True)
    results_table.add_column("Check Name", style="cyan")
    results_table.add_column("Command", style="dim")
    results_table.add_column("Status", justify="center")
    results_table.add_column("Details")

    success_count = 0

    # 4. Execute the Workflow (Persistent Session)
    # Disable strict host key checking for this script (lab demo)
    config.general.ssh_strict_host_key_checking = False

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task_id = progress.add_task("Connecting...", total=len(CHECKS))

        try:
            # Open a persistent session
            with DeviceSession(
                device_name=target,
                config=config,
                username_override=creds.username,
                password_override=creds.password,
            ) as session:
                progress.update(task_id, description="Connected! Running checks...")

                for check in CHECKS:
                    progress.update(task_id, description=f"Checking: {check.name}")

                    try:
                        # Execute command in the existing session
                        output_text = session.execute_command(check.command)

                        # Validate
                        is_compliant = check.validator(output_text)

                        if is_compliant:
                            status_str = "[green]PASS[/green]"
                            details = output_text.strip().split("\n")[0]
                            success_count += 1
                        else:
                            status_str = "[bold red]FAIL[/bold red]"
                            details = (
                                f"Validation failed. Output:\n{output_text.strip()}"
                            )

                    except Exception as e:
                        status_str = "[red]EXCEPTION[/red]"
                        details = str(e)

                    results_table.add_row(
                        check.name, check.command, status_str, details
                    )
                    progress.advance(task_id)

        except Exception as e:
            console.print(f"[bold red]Session Error:[/bold red] {e}")
            return

    # 4. Final Report
    console.print()
    console.print(results_table)

    score = (success_count / len(CHECKS)) * 100
    color = "green" if score == 100 else "yellow" if score > 50 else "red"
    console.print(f"Compliance Score: [bold {color}]{score:.1f}%[/bold {color}]")


if __name__ == "__main__":
    sys.exit(main())
