# SPDX-License-Identifier: MIT
"""Centralized styling and theming system for Network Toolkit."""

from __future__ import annotations

from enum import Enum

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from network_toolkit.common.output import OutputMode


class StyleName(str, Enum):
    """Semantic style names used throughout the application."""

    # Core semantic styles
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

    # Entity styles
    DEVICE = "device"
    HOST = "host"
    PORT = "port"
    PLATFORM = "platform"
    GROUP = "group"
    SEQUENCE = "sequence"
    COMMAND = "command"
    OUTPUT = "output"

    # UI styles
    SUMMARY = "summary"
    DIM = "dim"
    BOLD = "bold"
    TRANSPORT = "transport"
    RUNNING = "running"
    CONNECTED = "connected"
    FAILED = "failed"
    DOWNLOADING = "downloading"
    CREDENTIAL = "credential"
    UNKNOWN = "unknown"


class StyleManager:
    """Centralized style and theme management."""

    def __init__(self, mode: OutputMode):
        """Initialize style manager with output mode."""
        self.mode = mode

        # Theme definitions - must be defined before _create_console
        self.themes = {
            OutputMode.LIGHT: {
                StyleName.INFO.value: "blue",
                StyleName.WARNING.value: "dark_orange",
                StyleName.ERROR.value: "red",
                StyleName.SUCCESS.value: "green",
                StyleName.DEVICE.value: "cyan",
                StyleName.HOST.value: "blue",
                StyleName.PORT.value: "blue",
                StyleName.PLATFORM.value: "green",
                StyleName.GROUP.value: "cyan",
                StyleName.SEQUENCE.value: "magenta",
                StyleName.COMMAND.value: "magenta",
                StyleName.OUTPUT.value: "black",  # Dark text for light background
                StyleName.SUMMARY.value: "blue",
                StyleName.DIM.value: "dim",
                StyleName.BOLD.value: "bold blue",
                StyleName.TRANSPORT.value: "purple",
                StyleName.RUNNING.value: "blue",
                StyleName.CONNECTED.value: "green",
                StyleName.FAILED.value: "red",
                StyleName.DOWNLOADING.value: "cyan",
                StyleName.CREDENTIAL.value: "cyan",
                StyleName.UNKNOWN.value: "yellow",
            },
            OutputMode.DARK: {
                StyleName.INFO.value: "bright_blue",
                StyleName.WARNING.value: "yellow",
                StyleName.ERROR.value: "bright_red",
                StyleName.SUCCESS.value: "bright_green",
                StyleName.DEVICE.value: "bright_cyan",
                StyleName.HOST.value: "cyan",
                StyleName.PORT.value: "blue",
                StyleName.PLATFORM.value: "green",
                StyleName.GROUP.value: "bright_cyan",
                StyleName.SEQUENCE.value: "bright_magenta",
                StyleName.COMMAND.value: "bright_magenta",
                StyleName.OUTPUT.value: "white",  # Light text for dark background
                StyleName.SUMMARY.value: "bright_blue",
                StyleName.DIM.value: "dim",
                StyleName.BOLD.value: "bold bright_white",
                StyleName.TRANSPORT.value: "bright_magenta",
                StyleName.RUNNING.value: "bright_blue",
                StyleName.CONNECTED.value: "bright_green",
                StyleName.FAILED.value: "bright_red",
                StyleName.DOWNLOADING.value: "bright_cyan",
                StyleName.CREDENTIAL.value: "bright_cyan",
                StyleName.UNKNOWN.value: "bright_yellow",
            },
            OutputMode.DEFAULT: {
                StyleName.INFO.value: "blue",
                StyleName.WARNING.value: "yellow",
                StyleName.ERROR.value: "red",
                StyleName.SUCCESS.value: "green",
                StyleName.DEVICE.value: "cyan",
                StyleName.HOST.value: "cyan",
                StyleName.PORT.value: "blue",
                StyleName.PLATFORM.value: "green",
                StyleName.GROUP.value: "cyan",
                StyleName.SEQUENCE.value: "magenta",
                StyleName.COMMAND.value: "magenta",
                StyleName.OUTPUT.value: "default",
                StyleName.SUMMARY.value: "blue",
                StyleName.DIM.value: "dim",
                StyleName.BOLD.value: "bold",
                StyleName.TRANSPORT.value: "magenta",
                StyleName.RUNNING.value: "blue",
                StyleName.CONNECTED.value: "green",
                StyleName.FAILED.value: "red",
                StyleName.DOWNLOADING.value: "cyan",
                StyleName.CREDENTIAL.value: "cyan",
                StyleName.UNKNOWN.value: "yellow",
            },
        }

        self._console = self._create_console()

    def _create_console(self) -> Console:
        """Create a console instance based on the current mode."""
        if self.mode == OutputMode.RAW:
            # Raw mode uses no styling at all
            return Console(
                color_system=None,
                force_terminal=False,
                stderr=False,
                width=None,
                height=None,
            )
        elif self.mode == OutputMode.NO_COLOR:
            # No color mode disables colors but keeps other formatting
            return Console(color_system=None, force_terminal=True, stderr=False)
        else:
            # Themed modes
            theme_styles = self.themes.get(self.mode, self.themes[OutputMode.DEFAULT])
            theme = Theme(theme_styles)
            return Console(
                theme=theme,
                stderr=False,
                force_terminal=True,
                color_system="standard",
            )

    @property
    def console(self) -> Console:
        """Get the console instance."""
        return self._console

    def get_style(self, style_name: StyleName) -> str | None:
        """Get the actual style string for a semantic style name.

        Returns None for NO_COLOR and RAW modes to disable styling.
        """
        if self.mode in [OutputMode.NO_COLOR, OutputMode.RAW]:
            return None

        theme_styles = self.themes.get(self.mode, self.themes[OutputMode.DEFAULT])
        return theme_styles.get(style_name.value)

    def create_table(self, title: str = "") -> Table:
        """Create a Rich Table with appropriate styling for the current mode."""
        if self.mode in [OutputMode.NO_COLOR, OutputMode.RAW]:
            # For no-color modes, create table without styling
            return Table(title=title, show_header=True, show_lines=False)
        else:
            # For colored modes, use themed table
            return Table(title=title)

    def add_column(
        self, table: Table, header: str, style_name: StyleName | None = None
    ) -> None:
        """Add a column to a table with appropriate styling."""
        style = self.get_style(style_name) if style_name else None
        table.add_column(header, style=style)

    def format_message(self, message: str, style_name: StyleName) -> str:
        """Format a message with semantic styling."""
        if self.mode in [OutputMode.NO_COLOR, OutputMode.RAW]:
            return message
        else:
            return f"[{style_name.value}]{message}[/{style_name.value}]"


def create_style_manager(mode: OutputMode) -> StyleManager:
    """Create a style manager for the given output mode."""
    return StyleManager(mode)
