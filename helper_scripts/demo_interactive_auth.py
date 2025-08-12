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
    print("=== Network Toolkit Interactive Credentials Demo ===\n")

    print("This demonstrates the new --interactive-auth feature that allows")
    print("you to securely enter credentials at runtime.\n")

    # Simulate what happens when --interactive-auth is used
    print("1. When you use --interactive-auth, the tool will prompt for credentials:")
    print(
        "   Example: netkit run sw-acc1 '/system/identity/print' --interactive-auth\n"
    )

    try:
        # Demo the credential prompting
        print(
            "Demo: Prompting for credentials (try entering 'testuser' and 'testpass'):"
        )
        creds = prompt_for_credentials(
            "Enter username for devices",
            "Enter password for devices",
            "admin",  # Default suggestion
        )

        print("\n2. Credentials captured:")
        print(f"   Username: {creds.username}")
        print(f"   Password: {'*' * len(creds.password)} (hidden)")

        # Demo credential confirmation
        print("\n3. Confirming credentials...")
        if confirm_credentials(creds):
            print("   ✓ Credentials confirmed!")
        else:
            print("   ✗ Credentials rejected")

        print("\n4. These credentials would override any environment variables")
        print("   or config file settings for this session only.")

    except KeyboardInterrupt:
        print("\n\nDemo cancelled by user.")
    except Exception as e:
        print(f"\nError during demo: {e}")


def show_usage_examples():
    """Show usage examples for the new feature."""
    print("\n=== Usage Examples ===\n")

    examples = [
        {
            "description": "Get device info with interactive auth",
            "command": "netkit info sw-acc1 --interactive-auth",
        },
        {
            "description": "Run command with interactive auth",
            "command": "netkit run sw-acc1 '/system/identity/print' --interactive-auth",
        },
        {
            "description": "Run on multiple devices with interactive auth",
            "command": "netkit run sw-acc1,sw-acc2 '/system/clock/print' -i",
        },
        {
            "description": "Run sequence with interactive auth",
            "command": "netkit run access_switches system_info --interactive-auth",
        },
    ]

    for i, example in enumerate(examples, 1):
        print(f"{i}. {example['description']}:")
        print(f"   {example['command']}")
        print()


def show_security_benefits():
    """Explain the security benefits of this approach."""
    print("=== Security Benefits ===\n")

    benefits = [
        "No credentials stored in environment variables",
        "No credentials in config files or version control",
        "Credentials only exist in memory during execution",
        "Password input is hidden (not echoed to terminal)",
        "Works with any command that connects to devices",
        "Overrides all other credential sources (env vars, config)",
    ]

    for i, benefit in enumerate(benefits, 1):
        print(f"{i}. {benefit}")

    print("\nThis is ideal for:")
    print("• Shared systems where you don't want to leave credentials")
    print("• One-off operations with temporary access")
    print("• High-security environments")
    print("• Demonstrations and testing")


if __name__ == "__main__":
    demo_interactive_credentials()
    show_usage_examples()
    show_security_benefits()

    print("\n=== Next Steps ===")
    print("Try the feature with a real device using:")
    print("netkit info <device-name> --interactive-auth")
