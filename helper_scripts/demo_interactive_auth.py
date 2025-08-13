#!/usr/bin/env python3
"""
Demo script showing the new interactive credentials functionality.

This script demonstrates how to use the --interactive-auth/-i option
to securely enter credentials at runtime instead of relying on
environment variables or config files.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path for testing
sys.path.insert(0, str(Path(__file__).parent / "src"))

from network_toolkit.common.credentials import (
    confirm_credentials,
    prompt_for_credentials,
)


def demo_interactive_credentials():
    """Demonstrate the interactive credentials functionality."""

    # Simulate what happens when --interactive-auth is used

    try:
        # Demo the credential prompting
        creds = prompt_for_credentials(
            "Enter username for devices",
            "Enter password for devices",
            "admin",  # Default suggestion
        )

        # Demo credential confirmation
        if confirm_credentials(creds):
            pass
        else:
            pass

    except KeyboardInterrupt:
        pass
    except Exception:
        pass


def show_usage_examples():
    """Show usage examples for the new feature."""

    examples = [
        {
            "description": "Get device info with interactive auth",
            "command": "nw info sw-acc1 --interactive-auth",
        },
        {
            "description": "Run command with interactive auth",
            "command": "nw run sw-acc1 '/system/identity/print' --interactive-auth",
        },
        {
            "description": "Run on multiple devices with interactive auth",
            "command": "nw run sw-acc1,sw-acc2 '/system/clock/print' -i",
        },
        {
            "description": "Run sequence with interactive auth",
            "command": "nw run access_switches system_info --interactive-auth",
        },
    ]

    for _i, _example in enumerate(examples, 1):
        pass


def show_security_benefits():
    """Explain the security benefits of this approach."""

    benefits = [
        "No credentials stored in environment variables",
        "No credentials in config files or version control",
        "Credentials only exist in memory during execution",
        "Password input is hidden (not echoed to terminal)",
        "Works with any command that connects to devices",
        "Overrides all other credential sources (env vars, config)",
    ]

    for _i, _benefit in enumerate(benefits, 1):
        pass


if __name__ == "__main__":
    demo_interactive_credentials()
    show_usage_examples()
    show_security_benefits()
