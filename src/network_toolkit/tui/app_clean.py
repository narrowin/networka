"""Modern TUI Application.

A clean, maintainable implementation of the Textual-based user interface
following modern patterns and best practices.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.widgets import Footer, Header

from network_toolkit.tui.data import TuiDataService
from network_toolkit.tui.state import AppState
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

    # Inline CSS instead of external file
    CSS = """
    /* Main layout */
    #main-container {
        height: 100%;
    }

    #panels-container {
        height: 1fr;
        min-height: 20;
    }

    /* Panel styling */
    .panel {
        border: round $surface;
        padding: 1;
        margin: 1;
    }

    .panel-title {
        text-style: bold;
        text-align: center;
        color: $accent;
        height: 3;
        content-align: center middle;
    }

    /* Target and Actions panels */
    #targets-panel, #actions-panel {
        width: 1fr;
        height: 100%;
    }

    /* Execution panel */
    #execution-panel {
        height: 2fr;
        width: 100%;
    }

    /* Status bar */
    #status-bar {
        dock: bottom;
        height: 3;
        background: $primary;
        color: $text;
        text-align: center;
        content-align: center middle;
    }

    /* Input styling */
    .filter-input {
        border: round $primary;
        margin: 1;
    }

    /* Selection lists */
    .scrollable {
        overflow-y: auto;
    }

    /* Output log */
    .output-log {
        background: $background;
        color: $text;
        padding: 1;
    }

    /* Buttons */
    .run-button {
        dock: bottom;
        width: 100%;
        margin: 1;
        background: $success;
        color: $text;
    }

    .run-button:hover {
        background: $success-darken-1;
    }
    """

    def __init__(self, config_path: str | Path = "config") -> None:
        super().__init__()
        self.config_path = Path(config_path)

        # Core services
        self.state = AppState()
        self.data_service = TuiDataService(self.config_path)

        # Component references
        self.targets_panel: TargetsPanel | None = None
        self.actions_panel: ActionsPanel | None = None
        self.execution_panel: ExecutionPanel | None = None
        self.status_bar: StatusBar | None = None

    def compose(self) -> ComposeResult:
        """Create the main UI layout."""
        yield Header()

        with Vertical(id="main-container"):
            with Horizontal(id="panels-container"):
                # Left side: Targets panel
                self.targets_panel = TargetsPanel(
                    data_service=self.data_service,
                    state=self.state,
                    id="targets-panel",
                    classes="panel",
                )
                yield self.targets_panel

                # Right side: Actions panel
                self.actions_panel = ActionsPanel(
                    data_service=self.data_service,
                    state=self.state,
                    id="actions-panel",
                    classes="panel",
                )
                yield self.actions_panel

            # Bottom: Execution panel
            self.execution_panel = ExecutionPanel(
                data_service=self.data_service,
                state=self.state,
                id="execution-panel",
                classes="panel",
            )
            yield self.execution_panel

            # Status bar
            self.status_bar = StatusBar(
                state=self.state,
                id="status-bar",
            )
            yield self.status_bar

        yield Footer()

    async def on_mount(self) -> None:
        """Initialize the application after mounting."""
        try:
            await self.data_service.initialize()
            await self.state.initialize()

            # Initialize panels
            if self.targets_panel:
                await self.targets_panel.refresh_data()
            if self.actions_panel:
                await self.actions_panel.refresh_data()
            if self.status_bar:
                await self.status_bar.refresh_status()

        except Exception as e:
            self.notify(f"Initialization error: {e}", severity="error")

    def action_run(self) -> None:
        """Handle run action."""
        if self.execution_panel:
            self.call_from_thread(self._run_async)

    async def _run_async(self) -> None:
        """Execute the run action asynchronously."""
        if self.execution_panel:
            await self.execution_panel.execute_selected()

    def action_toggle_summary(self) -> None:
        """Toggle summary view."""
        if self.execution_panel:
            self.execution_panel.toggle_summary()

    def action_toggle_output(self) -> None:
        """Toggle output view."""
        if self.execution_panel:
            self.execution_panel.toggle_output()

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.dark = not self.dark

    def action_clear_focus(self) -> None:
        """Clear focus from current widget."""
        if self.focused:
            self.set_focus(None)

    def on_key(self, event: Key) -> None:
        """Handle key events for navigation."""
        key = event.key

        # Handle special navigation
        if key in ("up", "down", "left", "right"):
            self._handle_navigation(key)
        elif key == "tab":
            self._cycle_focus_forward()
        elif key == "shift+tab":
            self._cycle_focus_backward()

    def _handle_navigation(self, direction: str) -> None:
        """Handle directional navigation between panels."""
        if not self.focused:
            return

        current = self.focused

        if direction == "left":
            # Move to targets panel if in actions
            if current and "actions-panel" in str(current.css_identifier_styled):
                if self.targets_panel:
                    self.set_focus(self.targets_panel)
        elif direction == "right":
            # Move to actions panel if in targets
            if current and "targets-panel" in str(current.css_identifier_styled):
                if self.actions_panel:
                    self.set_focus(self.actions_panel)
        elif direction == "down":
            # Move to execution panel
            if self.execution_panel:
                self.set_focus(self.execution_panel)

    def _cycle_focus_forward(self) -> None:
        """Cycle focus forward through panels."""
        panels = [self.targets_panel, self.actions_panel, self.execution_panel]
        panels = [p for p in panels if p is not None]

        if not panels:
            return

        current_index = -1
        if self.focused:
            for i, panel in enumerate(panels):
                if panel and self.focused.has_ancestor(panel):
                    current_index = i
                    break

        next_index = (current_index + 1) % len(panels)
        self.set_focus(panels[next_index])

    def _cycle_focus_backward(self) -> None:
        """Cycle focus backward through panels."""
        panels = [self.targets_panel, self.actions_panel, self.execution_panel]
        panels = [p for p in panels if p is not None]

        if not panels:
            return

        current_index = -1
        if self.focused:
            for i, panel in enumerate(panels):
                if panel and self.focused.has_ancestor(panel):
                    current_index = i
                    break

        prev_index = (current_index - 1) % len(panels)
        self.set_focus(panels[prev_index])

    async def action_quit(self) -> None:
        """Clean quit action."""
        try:
            # Clean up resources
            if hasattr(self.data_service, "cleanup"):
                await self.data_service.cleanup()
        except Exception as e:
            self.log.error(f"Error during cleanup: {e}")
        finally:
            self.exit()

    def on_unmount(self) -> None:
        """Handle unmount cleanup."""
        # Schedule cleanup task
        task = asyncio.create_task(self._cleanup())
        # Store reference to prevent GC
        self._cleanup_task = task

    async def _cleanup(self) -> None:
        """Clean up resources on unmount."""
        try:
            if hasattr(self.data_service, "cleanup"):
                await self.data_service.cleanup()
        except Exception as e:
            self.log.error(f"Cleanup error: {e}")
