"""Modern TUI Application.

A clean, maintainable implementation of the Textual-based user interface
following modern patterns and best practices.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header

from network_toolkit.tui.data import TuiDataService
from network_toolkit.tui.state import AppState
from network_toolkit.tui.styles import APP_CSS
from network_toolkit.tui.widgets import (
    ActionsPanel,
    ExecutionPanel,
    StatusBar,
    TargetsPanel,
)

if TYPE_CHECKING:
    from textual.css.query import NoMatches


class NetworkWorkerApp(App[None]):
    """Modern Network Worker TUI application."""

    TITLE = "Network Worker TUI"
    SUB_TITLE = "Network Device Automation"

    BINDINGS: ClassVar[list[Binding]] = [
        Binding("q", "quit", "Quit"),
        Binding("ctrl+c", "quit", "Quit"),
        Binding("r", "run", "Run", priority=True),
        Binding("enter", "run", "Run", show=False),
        Binding("s", "toggle_summary", "Summary", show=True),
        Binding("o", "toggle_output", "Output", show=True),
        Binding("t", "toggle_theme", "Theme", show=True),
        Binding("escape", "clear_focus", "Clear Focus", show=False),
    ]

    CSS = APP_CSS

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the TUI application."""
        super().__init__()
        self._config_path = config_path
        self._data_service: TuiDataService | None = None
        self._state = AppState()

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)

        # Initialize data service
        self._data_service = TuiDataService(self._config_path or Path("devices.yml"))

        # Main layout
        with Vertical(id="main-container"):
            with Horizontal(id="panels-container"):
                yield TargetsPanel(id="targets-panel", classes="panel")
                yield ActionsPanel(id="actions-panel", classes="panel")
            yield ExecutionPanel(id="execution-panel", classes="panel")

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Initialize the app after mounting."""
        if self._data_service:
            self._data_service.load_data()
            self._update_status("Ready")

    def action_run(self) -> None:
        """Handle run action."""
        self._update_status("Running execution...")
        # Implementation would go here

    def action_toggle_summary(self) -> None:
        """Toggle execution summary view."""
        execution_panel = self.query_one("#execution-panel", ExecutionPanel)
        execution_panel.toggle_summary_view()

    def action_toggle_output(self) -> None:
        """Toggle execution output view."""
        execution_panel = self.query_one("#execution-panel", ExecutionPanel)
        execution_panel.toggle_output_view()

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.dark = not self.dark
        theme = "dark" if self.dark else "light"
        self._update_status(f"Switched to {theme} theme")

    def action_clear_focus(self) -> None:
        """Clear focus from current widget."""
        if self.focused:
            self.focused.blur()

    def _update_status(self, message: str) -> None:
        """Update the status bar message."""
        try:
            status_bar = self.query_one("#status-bar", StatusBar)
            status_bar.update_status(message)
        except Exception:
            # Ignore if status bar not found
            pass
