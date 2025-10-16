"""ASCII banner for Networka."""

from __future__ import annotations

from rich.console import Console
from rich.text import Text

# ASCII Art Banner for NETWORKA (plain text for fallback)
BANNER_PLAIN = """
███╗   ██╗███████╗████████╗██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗ █████╗
████╗  ██║██╔════╝╚══██╔══╝██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔══██╗
██╔██╗ ██║█████╗     ██║   ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ ███████║
██║╚██╗██║██╔══╝     ██║   ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══██║
██║ ╚████║███████╗   ██║   ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██║  ██║
╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
"""

# Keep BANNER for backward compatibility
BANNER = BANNER_PLAIN


def show_banner() -> None:
    """Show the banner with welcome message and cyan-to-blue gradient colors."""
    from network_toolkit.common.command_helpers import CommandContext

    ctx = CommandContext()

    # Check if we should suppress colors
    if ctx.should_suppress_colors():
        # Raw mode - just print plain banner
        ctx.print_info(BANNER_PLAIN.rstrip())
        ctx.print_info("Welcome to Networka! Multi-vendor network automation CLI.")
        ctx.print_info(
            "Type 'nw --help' for available commands or 'nw config init' to get started."
        )
        return

    # Use Rich to render banner with colors matching the logo image
    # Create smooth gradient from Sky blue (top) to softer pink (bottom)
    console = Console()
    banner_lines = BANNER_PLAIN.strip().split("\n")

    # Gradient from sky blue (45,121,210) to soft muted pink
    colors = [
        "rgb(45,121,210)",  # Line 1 - Sky blue top #2D79D2
        "rgb(68,113,196)",  # Line 2 - Transition
        "rgb(91,105,181)",  # Line 3 - Mid purple-blue
        "rgb(136,110,158)",  # Line 4 - Mid purple-pink
        "rgb(180,120,145)",  # Line 5 - Transition (softer)
        "rgb(210,140,160)",  # Line 6 - Soft muted pink bottom (desaturated)
    ]

    for i, line in enumerate(banner_lines):
        color = colors[i] if i < len(colors) else colors[0]
        text = Text(line, style=color)
        console.print(text)

    # Print welcome messages
    ctx.print_info("Welcome to Networka! Multi-vendor network automation CLI.")
    ctx.print_info(
        "Type 'nw --help' for available commands or 'nw config init' to get started."
    )
