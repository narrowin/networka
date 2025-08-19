"""Modern Network Worker TUI Application.

A clean, maintainable Textual application for network device automation.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, ClassVar

from textual import on
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header

from network_toolkit.tui.data import TuiData
from network_toolkit.tui.execution import ExecutionCallbacks, ExecutionManager
from network_toolkit.tui.state import ReactiveState
from network_toolkit.tui.styles import APP_CSS
from network_toolkit.tui.widgets import MainLayout


class NetworkWorkerApp(App):
    """Modern Network Worker TUI Application."""

    CSS = APP_CSS

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit", priority=True),
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("r", "run_execution", "Run", priority=True),
        Binding("o", "toggle_output", "Toggle Output", priority=True),
        Binding("s", "toggle_summary", "Toggle Summary", priority=True),
        Binding("t", "toggle_theme", "Toggle Theme", priority=True),
        Binding("f", "focus_filter", "Focus Filter", priority=True),
    ]

    def __init__(self, config_path: str | Path = "config") -> None:
        super().__init__()
        self._config_path = config_path
        self._data: TuiData | None = None
        self._state = ReactiveState()
        self._execution_manager: ExecutionManager | None = None
        self._main_layout: MainLayout | None = None

    def compose(self) -> ComposeResult:
        """Create the application layout."""
        yield Header(show_clock=True)

        # Load data and create layout
        self._data = TuiData(self._config_path)
        self._execution_manager = ExecutionManager(self._data)

        targets = self._data.targets()
        actions = self._data.actions()

        self._main_layout = MainLayout(
            devices=targets.devices,
            groups=targets.groups,
            sequences=actions.sequences,
        )

        yield self._main_layout
        yield Footer()

    async def action_run_execution(self) -> None:
        """Execute the current plan."""
        if not self._main_layout or not self._execution_manager:
            return

        # Collect current selections
        try:
            targets_panel = self._main_layout.query_one("#targets-panel")
            actions_panel = self._main_layout.query_one("#actions-panel")
            status_bar = self._main_layout.query_one("#status-bar")
            output_panel = self._main_layout.query_one("#output-panel")
        except Exception:
            return

        selected_devices = targets_panel.selected_devices
        selected_groups = targets_panel.selected_groups
        selected_sequences = actions_panel.selected_sequences
        command_text = actions_panel.command_text

        # Resolve devices
        devices = self._execution_manager.resolve_devices(
            selected_devices, selected_groups
        )

        if not devices:
            status_bar.set_status("No devices selected")
            return

        # Build execution plan
        plan = self._execution_manager.build_execution_plan(
            devices, selected_sequences, command_text
        )

        if not plan:
            status_bar.set_status("No commands to execute")
            return

        # Show output panel and clear logs
        output_panel.show()
        output_panel.clear_output()
        output_panel.clear_summary()

        # Set up callbacks
        callbacks = ExecutionCallbacks(
            on_output=output_panel.add_output,
            on_error=lambda msg: output_panel.add_summary(f"ERROR: {msg}"),
            on_progress=status_bar.set_status,
        )

        # Execute plan
        try:
            status_bar.set_status("Executing...")
            status_bar.add_class("-running")

            result = await self._execution_manager.execute_plan(plan, callbacks)

            # Update status based on results
            if result.failures == 0:
                status_bar.set_status(f"Success: {result.successes} devices completed")
                status_bar.remove_class("-running")
                status_bar.add_class("-success")
            else:
                status_bar.set_status(
                    f"Completed: {result.successes} success, {result.failures} failed"
                )
                status_bar.remove_class("-running")
                status_bar.add_class("-error")

            # Add summary
            output_panel.add_summary(result.human_summary())

        except Exception as e:
            status_bar.set_status(f"Execution failed: {e}")
            status_bar.remove_class("-running")
            status_bar.add_class("-error")
            output_panel.add_summary(f"FATAL ERROR: {e}")

    def action_toggle_output(self) -> None:
        """Toggle output panel visibility."""
        if self._main_layout:
            try:
                output_panel = self._main_layout.query_one("#output-panel")
                output_panel.toggle()
            except Exception:
                pass

    def action_toggle_summary(self) -> None:
        """Toggle summary tab in output panel."""
        if self._main_layout:
            try:
                output_panel = self._main_layout.query_one("#output-panel")
                if output_panel.has_class("hidden"):
                    output_panel.show()
                # Switch to summary tab
                tabs = output_panel.query_one("#output-tabs")
                tabs.active = "summary-tab"
            except Exception:
                pass

    def action_toggle_theme(self) -> None:
        """Toggle between light and dark themes."""
        self.dark = not self.dark

    def action_focus_filter(self) -> None:
        """Focus the most relevant filter input."""
        if not self._main_layout:
            return

        # Try to focus device filter by default
        try:
            targets_panel = self._main_layout.query_one("#targets-panel")
            device_filter = targets_panel.query_one("#devices-selection-filter")
            device_filter.focus()
        except Exception:
            pass
