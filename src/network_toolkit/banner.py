"""ASCII banner for Networka."""

from __future__ import annotations

# ASCII Art Banner for NETWORKA
BANNER = """
███╗   ██╗███████╗████████╗██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗ █████╗
████╗  ██║██╔════╝╚══██╔══╝██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝██╔══██╗
██╔██╗ ██║█████╗     ██║   ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ ███████║
██║╚██╗██║██╔══╝     ██║   ██║███╗██║██║   ██║██╔══██╗██╔═██╗ ██╔══██║
██║ ╚████║███████╗   ██║   ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗██║  ██║
╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
"""


def show_banner() -> None:
    """Show the banner with welcome message."""
    from network_toolkit.common.command_helpers import CommandContext

    ctx = CommandContext()
    ctx.print_info(BANNER.rstrip())
    ctx.print_info("Welcome to Networka! Multi-vendor network automation CLI.")
    ctx.print_info(
        "Type 'nw --help' for available commands or 'nw config init' to get started."
    )
