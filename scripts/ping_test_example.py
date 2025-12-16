"""
Example: Ping Test Script

This script demonstrates how to use the Networka library to perform ping tests
from a specific remote device. It shows how to handle both successful and
failed ping attempts programmatically.

Usage:
    uv run scripts/ping_test_example.py [--level {quiet,info,debug}]
"""

import argparse
import logging
import os
import sys
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from rich.console import Console
from rich.logging import RichHandler
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskID, TextColumn
from rich.table import Table

from network_toolkit import InteractiveCredentials, NetworkaClient
from network_toolkit.api.execution import execute_parallel

# --- Configuration ---
LINUX_DEVICE = os.getenv("NETWORKA_TEST_LINUX_DEVICE", "wago-plc2a-vlan10")
MIKROTIK_DEVICE = os.getenv(
    "NETWORKA_TEST_MIKROTIK_DEVICE", "clab-ot-sec-segmented-gw-firewall"
)
PING_TARGET_SUCCESS = "1.1.1.1"
PING_TARGET_FAIL = "192.0.2.1"  # TEST-NET-1, reserved and typically unreachable
PING_COUNT = 2

# Setup Logger
logger = logging.getLogger("ping_test")


class LogLevel(str, Enum):
    QUIET = "quiet"
    INFO = "info"
    DEBUG = "debug"


@dataclass
class TestCase:
    vendor: str
    device: str
    target: str
    func: Callable
    description: str


@dataclass
class PingResult:
    device: str
    target: str
    method: str
    success: bool
    details: str
    command: str
    raw_output: str | None = None


def run_ping_linux(client, device_name, target_ip, count, creds) -> PingResult:
    """
    Run ping on a Linux device using standard tools.
    """
    command = f"ping -c {count} -W 1 {target_ip}"
    logger.debug(f"Running command on {device_name}: {command}")

    result = client.run(device_name, command, interactive_creds=creds)

    if not result.command_results:
        return PingResult(
            device_name,
            target_ip,
            "Linux Standard",
            False,
            "No results returned",
            command,
        )

    cmd_result = result.command_results[0]
    output = cmd_result.output or ""

    if cmd_result.error:
        logger.debug(f"Command failed with error: {cmd_result.error}")
        logger.debug(f"Output: {output}")

        details = f"Exit Code: {cmd_result.error}"
        if "Connection failed" in str(cmd_result.error):
            details = "Connection Failed"

        return PingResult(
            device_name,
            target_ip,
            "Linux Standard",
            False,
            details,
            command,
            output,
        )

    if ", 0% packet loss" in output:
        return PingResult(
            device_name,
            target_ip,
            "Linux Standard",
            True,
            "0% Packet Loss",
            command,
            output,
        )
    else:
        logger.debug(f"Packet loss detected in output: {output}")
        return PingResult(
            device_name,
            target_ip,
            "Linux Standard",
            False,
            "Packet Loss Detected",
            command,
            output,
        )


def run_ping_mikrotik(client, device_name, target_ip, count, creds) -> PingResult:
    """
    Run ping on a Mikrotik RouterOS device.
    """
    command = f"ping {target_ip} count={count}"
    logger.debug(f"Running command on {device_name}: {command}")

    result = client.run(device_name, command, interactive_creds=creds)

    if not result.command_results:
        return PingResult(
            device_name,
            target_ip,
            "Mikrotik API",
            False,
            "No results returned",
            command,
        )

    cmd_result = result.command_results[0]
    output = cmd_result.output or ""

    if cmd_result.error:
        details = f"Error: {cmd_result.error}"
        if "Connection failed" in str(cmd_result.error):
            details = "Connection Failed"
        return PingResult(
            device_name,
            target_ip,
            "Mikrotik API",
            False,
            details,
            command,
            output,
        )

    if "packet-loss=0%" in output:
        return PingResult(
            device_name,
            target_ip,
            "Mikrotik API",
            True,
            "0% Packet Loss",
            command,
            output,
        )
    elif "packet-loss=100%" in output or "timeout" in output:
        logger.debug(f"100% packet loss or timeout: {output}")
        return PingResult(
            device_name,
            target_ip,
            "Mikrotik API",
            False,
            "100% Packet Loss",
            command,
            output,
        )
    else:
        logger.debug(f"Partial or unknown loss: {output}")
        return PingResult(
            device_name,
            target_ip,
            "Mikrotik API",
            False,
            "Partial/Unknown Loss",
            command,
            output,
        )


def run_ping_optimized_linux(
    client, device_name, target_ip, count, creds
) -> PingResult:
    """
    Optimized approach for Linux: Offload success check to remote shell.
    """
    command = f"ping -c {count} -W 1 {target_ip} | grep -q ', 0% packet loss' && echo 'PING_SUCCESS' || echo 'PING_FAILURE'"
    logger.debug(f"Running command on {device_name}: {command}")

    result = client.run(device_name, command, interactive_creds=creds)

    if not result.command_results:
        return PingResult(
            device_name,
            target_ip,
            "Linux Optimized",
            False,
            "No results returned",
            command,
        )

    cmd_result = result.command_results[0]
    if cmd_result.error:
        details = f"Error: {cmd_result.error}"
        if "Connection failed" in str(cmd_result.error):
            details = "Connection Failed"
        return PingResult(
            device_name,
            target_ip,
            "Linux Optimized",
            False,
            details,
            command,
            (cmd_result.output or ""),
        )

    output = (result.command_results[0].output or "").strip()

    if output == "PING_SUCCESS":
        return PingResult(
            device_name,
            target_ip,
            "Linux Optimized",
            True,
            "Verified by Remote Shell",
            command,
            output,
        )
    else:
        logger.debug(f"Remote shell returned failure: {output}")
        return PingResult(
            device_name,
            target_ip,
            "Linux Optimized",
            False,
            f"Remote Shell: {output}",
            command,
            output,
        )


def run_device_tests(
    device_name: str,
    tests: list[TestCase],
    creds: InteractiveCredentials,
    progress: Progress | None,
    task_id: TaskID | None,
) -> list[PingResult]:
    """
    Execute a list of tests for a single device using a dedicated NetworkaClient.
    This runs in a separate thread.

    Concurrency Note:
    The Networka library supports parallel execution via client.run(target="group", ...)
    but only when running the SAME command/sequence across all devices.

    Since this script needs to run DIFFERENT commands (due to vendor syntax) and
    perform custom parsing logic per device, we cannot use the library's built-in
    group parallelism.

    Instead, we use Python's ThreadPoolExecutor to run independent test suites
    for each device in parallel. We create a separate NetworkaClient instance
    for each thread because the client is not thread-safe.
    """
    results = []
    try:
        # Create a thread-local client instance (NetworkaClient is not thread-safe)
        client = NetworkaClient()

        # Set faster timeouts for testing
        client.config.general.timeout = 2

        # Check if device exists in this client's config
        if not client.devices or device_name not in client.devices:
            logger.warning(f"Device '{device_name}' not found in inventory.")
            if progress and task_id:
                progress.update(task_id, visible=False)
            return []

        with client:
            for test in tests:
                if progress and task_id:
                    progress.update(
                        task_id,
                        description=f"[{test.vendor}] {test.description}: {device_name} -> {test.target}",
                    )

                # Run the test
                try:
                    results.append(
                        test.func(client, device_name, test.target, PING_COUNT, creds)
                    )
                except Exception as e:
                    logger.error(f"Error running test on {device_name}: {e}")
                    results.append(
                        PingResult(
                            device_name,
                            test.target,
                            "Error",
                            False,
                            f"Exception: {e}",
                            "N/A",
                        )
                    )

                if progress and task_id:
                    progress.advance(task_id)

    except Exception as e:
        logger.error(f"Failed to initialize client for {device_name}: {e}")

    return results


def setup_logging(level: LogLevel, console: Console):
    """Configure logging based on the selected level."""
    if level == LogLevel.QUIET:
        logger.setLevel(logging.CRITICAL + 1)  # Disable logging
    elif level == LogLevel.DEBUG:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    # Use RichHandler for pretty logs, attached to the same console
    handler = RichHandler(console=console, show_time=False, show_path=False)
    logger.addHandler(handler)
    # Disable propagation to avoid double logging if root logger is configured
    logger.propagate = False


def main():
    parser = argparse.ArgumentParser(description="Networka Ping Test Demo")
    parser.add_argument(
        "--level",
        type=LogLevel,
        default=LogLevel.INFO,
        choices=list(LogLevel),
        help="Set the output verbosity level",
    )
    args = parser.parse_args()

    console = Console()
    setup_logging(args.level, console)

    if args.level != LogLevel.QUIET:
        console.print(
            Panel.fit(
                "[bold blue]Networka Ping Test Demo[/bold blue]\n"
                "Multi-Vendor Support (Parallel Execution)",
                border_style="blue",
            )
        )

    creds = InteractiveCredentials(username="", password="")
    results = []

    # Define the test plan
    all_tests = [
        TestCase(
            vendor="Linux",
            device=LINUX_DEVICE,
            target=PING_TARGET_SUCCESS,
            func=run_ping_linux,
            description="Expected Success",
        ),
        TestCase(
            vendor="Linux",
            device=LINUX_DEVICE,
            target=PING_TARGET_FAIL,
            func=run_ping_linux,
            description="Expected Failure",
        ),
        TestCase(
            vendor="Linux",
            device=LINUX_DEVICE,
            target=PING_TARGET_SUCCESS,
            func=run_ping_optimized_linux,
            description="Optimized Success",
        ),
        TestCase(
            vendor="Mikrotik",
            device=MIKROTIK_DEVICE,
            target=PING_TARGET_SUCCESS,
            func=run_ping_mikrotik,
            description="Expected Success",
        ),
        TestCase(
            vendor="Mikrotik",
            device=MIKROTIK_DEVICE,
            target=PING_TARGET_FAIL,
            func=run_ping_mikrotik,
            description="Expected Failure",
        ),
    ]

    # Group tests by device
    tests_by_device = defaultdict(list)
    for test in all_tests:
        tests_by_device[test.device].append(test)

    # Execute tests in parallel
    if args.level != LogLevel.QUIET:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            console=console,
            transient=True,
        ) as progress:
            # Prepare items for parallel execution
            execution_items = []
            for device, device_tests in tests_by_device.items():
                task_id = progress.add_task(
                    f"Waiting: {device}...", total=len(device_tests)
                )
                execution_items.append(
                    {
                        "device": device,
                        "tests": device_tests,
                        "creds": creds,
                        "progress": progress,
                        "task_id": task_id,
                    }
                )

            def run_wrapper(item):
                return run_device_tests(
                    item["device"],
                    item["tests"],
                    item["creds"],
                    item["progress"],
                    item["task_id"],
                )

            batch_results = execute_parallel(execution_items, run_wrapper)
            for batch in batch_results:
                results.extend(batch)
    else:
        # Quiet mode execution (no progress bar)
        execution_items = []
        for device, device_tests in tests_by_device.items():
            execution_items.append(
                {
                    "device": device,
                    "tests": device_tests,
                    "creds": creds,
                    "progress": None,
                    "task_id": None,
                }
            )

        def run_wrapper(item):
            return run_device_tests(
                item["device"], item["tests"], item["creds"], None, None
            )

        batch_results = execute_parallel(execution_items, run_wrapper)
        for batch in batch_results:
            results.extend(batch)

    # Display Results Table
    table = Table(title="Ping Test Results", show_lines=True)
    table.add_column("Device", style="cyan")
    table.add_column("Target", style="magenta")
    table.add_column("Method", style="dim")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    # Add command column only in DEBUG mode
    if args.level == LogLevel.DEBUG:
        table.add_column("Command", style="yellow")

    for res in results:
        status_str = (
            "[bold green]PASS[/bold green]"
            if res.success
            else "[bold red]FAIL[/bold red]"
        )
        if args.level == LogLevel.DEBUG:
            table.add_row(
                res.device, res.target, res.method, status_str, res.details, res.command
            )
        else:
            table.add_row(res.device, res.target, res.method, status_str, res.details)

    console.print(table)


if __name__ == "__main__":
    sys.exit(main())
