"""Output formatting utilities for the network toolkit."""

from __future__ import annotations

import re
from enum import Enum
from typing import Any

from rich.console import Console
from rich.table import Table


class OutputMode(Enum):
    """Output formatting modes."""

    RICH = "rich"
    JSON = "json"
    CSV = "csv"
    NO_COLOR = "no-color"


class SmartConsole:
    """A console that automatically handles color/no-color modes."""

    def __init__(self, mode: OutputMode = OutputMode.RICH):
        """Initialize with output mode."""
        self.mode = mode
        self._rich_console = Console()

    def print(self, content: Any, style: str | None = None) -> None:  # noqa: A003
        """Print content with automatic mode handling."""
        if self.mode == OutputMode.NO_COLOR:
            # Strip any Rich markup and use plain print
            if isinstance(content, str) and "[" in str(content):
                # Remove any existing Rich markup
                clean_content = re.sub(r"\[[^\]]*\]", "", str(content))
                print(clean_content)
            else:
                print(content)
        elif style and isinstance(content, str):
            self._rich_console.print(f"[{style}]{content}[/{style}]")
        else:
            self._rich_console.print(content)

    def print_success(self, message: str) -> None:
        """Print success message."""
        self.print(message, "green")

    def print_warning(self, message: str) -> None:
        """Print warning message."""
        self.print(message, "yellow")

    def print_error(self, message: str) -> None:
        """Print error message."""
        self.print(f"FAIL {message}", "red")


def format_output(
    data: list[dict[str, Any]],
    headers: list[str],
    title: str,
    output_mode: OutputMode,
    styles: dict[str, str] | None = None,
) -> str | Table:
    """Format data for output based on the specified mode."""
    if output_mode == OutputMode.JSON:
        import json

        return json.dumps(data, indent=2)

    elif output_mode == OutputMode.CSV:
        import csv
        import io

        output = io.StringIO()
        if data:
            writer = csv.DictWriter(output, fieldnames=headers)
            writer.writeheader()
            for row in data:
                writer.writerow(row)
        return output.getvalue()

    elif output_mode == OutputMode.NO_COLOR:
        # Plain text table format
        if not data:
            return f"{title}\n\nNo data available"

        # Calculate column widths
        col_widths = {}
        for i, header in enumerate(headers):
            col_widths[i] = len(header)
            for row in data:
                value = str(row.get(list(row.keys())[i], ""))
                col_widths[i] = max(col_widths[i], len(value))

        # Build table
        lines = [title, ""]

        # Header row
        header_line = " | ".join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
        lines.append(header_line)
        lines.append("-" * len(header_line))

        # Data rows
        for row in data:
            values = [
                str(row.get(list(row.keys())[i], "")) for i in range(len(headers))
            ]
            data_line = " | ".join(v.ljust(col_widths[i]) for i, v in enumerate(values))
            lines.append(data_line)

        return "\n".join(lines)

    else:  # OutputMode.RICH (default)
        table = Table(title=title)

        # Style mapping for safety
        style_map = {
            "device": "bright_blue",
            "host": "cyan",
            "port": "blue",
            "platform": "green",
            "groups": "yellow",
            "group": "bright_blue",
            "devices": "cyan",
            "count": "blue",
        }

        valid_colors = {
            "red",
            "green",
            "blue",
            "yellow",
            "cyan",
            "magenta",
            "white",
            "black",
            "bright_red",
            "bright_green",
            "bright_blue",
            "bright_yellow",
            "bright_cyan",
            "bright_magenta",
            "bright_white",
        }

        for i, header in enumerate(headers):
            style = None
            if styles and i < len(list(styles.keys())):
                style_key = list(styles.keys())[i]
                raw_style = styles[style_key]
                # Use mapped style or validate raw style
                style = style_map.get(
                    raw_style, raw_style if raw_style in valid_colors else None
                )
            table.add_column(header, style=style)

        # Add rows
        for row in data:
            values = [
                str(row.get(list(row.keys())[i], "")) for i in range(len(headers))
            ]
            table.add_row(*values)

        return table


def create_smart_console(output_mode: OutputMode) -> SmartConsole:
    """Create a smart console instance for the given output mode."""
    return SmartConsole(output_mode)


# Legacy compatibility functions
def get_output_mode_from_env() -> OutputMode:
    """Determine output mode from environment variables."""
    import os

    if os.getenv("NO_COLOR"):
        return OutputMode.NO_COLOR
    if os.getenv("FORCE_COLOR"):
        return OutputMode.RICH
    ci_envs = ["CI", "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"]
    if any(os.getenv(env) for env in ci_envs):
        return OutputMode.NO_COLOR
    return OutputMode.RICH


def get_output_mode_from_config(config_output_mode: str | None = None) -> OutputMode:
    """Get output mode from configuration or environment."""
    if config_output_mode:
        try:
            return OutputMode(config_output_mode)
        except ValueError:
            pass
    return get_output_mode_from_env()


class OutputManager:
    """Manages output formatting and display."""

    def __init__(self, mode: OutputMode = OutputMode.RICH):
        """Initialize the output manager."""
        self.mode = mode
        self.smart_console = SmartConsole(mode)

    def format_table(
        self,
        data: list[dict[str, Any]],
        headers: list[str],
        title: str = "",
        styles: dict[str, str] | None = None,
    ) -> str | Table:
        """Format data as a table."""
        return format_output(data, headers, title, self.mode, styles)

    def print_table(
        self,
        data: list[dict[str, Any]],
        headers: list[str],
        title: str = "",
        styles: dict[str, str] | None = None,
    ) -> None:
        """Print a formatted table."""
        output = self.format_table(data, headers, title, styles)
        self.smart_console.print(output)


def get_output_manager() -> OutputManager:
    """Get the output manager instance."""
    return OutputManager()


def get_output_manager_with_config(config: Any = None) -> OutputManager:
    """Get the output manager with configuration."""
    return OutputManager()


def set_output_mode(mode: OutputMode) -> None:
    """Set the global output mode."""
    pass


# Create console instance for backward compatibility
console = Console()
