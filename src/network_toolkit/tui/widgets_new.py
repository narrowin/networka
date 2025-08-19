"""Modern TUI widgets for Network Worker.

This module contains all the individual UI components used in the TUI application,
following modern Textual patterns with proper separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from textual import on, work
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.widgets import (
    Button,
    Input,
    ProgressBar,
    RichLog,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

if TYPE_CHECKING:
    from textual.app import ComposeResult

    from network_toolkit.tui.data import TuiDataService
    from network_toolkit.tui.state import AppState


class FilterableSelectionList(Container):
    """A selection list with built-in filtering capability."""

    selected_items: reactive[set[str]] = reactive(set())

    def __init__(
        self,
        items: list[str] | None = None,
        placeholder: str = "Filter...",
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes)
        self._all_items = items or []
        self._placeholder = placeholder
        self._filtered_items = self._all_items[:]

    def compose(self) -> ComposeResult:
        """Build the widget layout."""
        with Vertical():
            yield Input(
                placeholder=self._placeholder,
                id=f"{self.id}-filter",
                classes="filter-input",
            )
            yield SelectionList[str](
                *self._all_items,
                id=f"{self.id}-list",
                classes="scrollable",
            )

    def on_mount(self) -> None:
        """Initialize after mounting."""
        self._update_selection_tracking()

    @on(Input.Changed, "#*-filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        filter_text = event.value.lower().strip()
        self._apply_filter(filter_text)

    @on(SelectionList.SelectedChanged)
    def on_selection_changed(self, event: SelectionList.SelectedChanged) -> None:
        """Handle selection changes."""
        selection_list = self.query_one(SelectionList)
        self.selected_items = set(selection_list.selected)

    def _apply_filter(self, filter_text: str) -> None:
        """Apply filter to the selection list."""
        selection_list = self.query_one(SelectionList)

        # Store current selections
        current_selected = set(selection_list.selected)

        # Filter items
        if filter_text:
            self._filtered_items = [
                item for item in self._all_items if filter_text in item.lower()
            ]
        else:
            self._filtered_items = self._all_items[:]

        # Update list
        selection_list.clear_options()
        for item in self._filtered_items:
            selection_list.add_option(item)

        # Restore selections for items still in filtered list
        for item in current_selected:
            if item in self._filtered_items:
                selection_list.select(item)

    def update_items(self, items: list[str]) -> None:
        """Update the list of available items."""
        self._all_items = items[:]
        current_filter = self.query_one(Input).value.lower().strip()
        self._apply_filter(current_filter)

    def focus_filter(self) -> None:
        """Focus the filter input."""
        filter_input = self.query_one(Input)
        filter_input.focus()

    def _update_selection_tracking(self) -> None:
        """Initialize selection tracking."""
        selection_list = self.query_one(SelectionList)
        self.selected_items = set(selection_list.selected)


class TargetsPanel(Container):
    """Panel for selecting target devices and groups."""

    def __init__(
        self,
        data_service: TuiDataService,
        state: AppState,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes or "panel")
        self.data_service = data_service
        self.state = state

    def compose(self) -> ComposeResult:
        """Build the targets panel layout."""
        yield Static("Targets", classes="panel-title")
        with TabbedContent():
            with TabPane("Devices", id="tab-devices"):
                yield FilterableSelectionList(
                    placeholder="Filter devices...",
                    widget_id="devices-list",
                )
            with TabPane("Groups", id="tab-groups"):
                yield FilterableSelectionList(
                    placeholder="Filter groups...",
                    widget_id="groups-list",
                )

    async def initialize(self) -> None:
        """Initialize the panel with data."""
        try:
            targets = await self.data_service.get_targets()

            devices_list = self.query_one("#devices-list", FilterableSelectionList)
            devices_list.update_items(targets.devices)

            groups_list = self.query_one("#groups-list", FilterableSelectionList)
            groups_list.update_items(targets.groups)

            # Subscribe to selection changes
            devices_list.watch("selected_items", self._on_devices_changed)
            groups_list.watch("selected_items", self._on_groups_changed)

        except Exception as e:
            self.app.notify(f"Failed to load targets: {e}", severity="error")

    def _on_devices_changed(self, selected: set[str]) -> None:
        """Handle device selection changes."""
        self.state.update_selection(devices=selected)

    def _on_groups_changed(self, selected: set[str]) -> None:
        """Handle group selection changes."""
        self.state.update_selection(groups=selected)

    def focus_filter(self) -> None:
        """Focus the filter input of the active tab."""
        tabs = self.query_one(TabbedContent)
        active_tab = tabs.active

        if active_tab == "tab-devices":
            devices_list = self.query_one("#devices-list", FilterableSelectionList)
            devices_list.focus_filter()
        elif active_tab == "tab-groups":
            groups_list = self.query_one("#groups-list", FilterableSelectionList)
            groups_list.focus_filter()


class ActionsPanel(Container):
    """Panel for selecting sequences and entering commands."""

    def __init__(
        self,
        data_service: TuiDataService,
        state: AppState,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes or "panel")
        self.data_service = data_service
        self.state = state

    def compose(self) -> ComposeResult:
        """Build the actions panel layout."""
        yield Static("Actions", classes="panel-title")
        with TabbedContent():
            with TabPane("Sequences", id="tab-sequences"):
                yield FilterableSelectionList(
                    placeholder="Filter sequences...",
                    widget_id="sequences-list",
                )
            with TabPane("Commands", id="tab-commands"):
                yield TextArea(
                    placeholder="Enter commands (one per line)...",
                    id="commands-input",
                    classes="command-input",
                )

    async def initialize(self) -> None:
        """Initialize the panel with data."""
        try:
            actions = await self.data_service.get_actions()

            sequences_list = self.query_one("#sequences-list", FilterableSelectionList)
            sequences_list.update_items(actions.sequences)

            # Subscribe to selection changes
            sequences_list.watch("selected_items", self._on_sequences_changed)

        except Exception as e:
            self.app.notify(f"Failed to load actions: {e}", severity="error")

    @on(TextArea.Changed, "#commands-input")
    def on_commands_changed(self, event: TextArea.Changed) -> None:
        """Handle command text changes."""
        self.state.update_selection(command_text=event.text_area.text)

    def _on_sequences_changed(self, selected: set[str]) -> None:
        """Handle sequence selection changes."""
        self.state.update_selection(sequences=selected)

    def focus_filter(self) -> None:
        """Focus the filter input of the active tab."""
        tabs = self.query_one(TabbedContent)
        active_tab = tabs.active

        if active_tab == "tab-sequences":
            sequences_list = self.query_one("#sequences-list", FilterableSelectionList)
            sequences_list.focus_filter()
        elif active_tab == "tab-commands":
            commands_input = self.query_one("#commands-input", TextArea)
            commands_input.focus()


class ExecutionPanel(Container):
    """Panel for execution controls and output display."""

    def __init__(
        self,
        data_service: TuiDataService,
        state: AppState,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes or "panel")
        self.data_service = data_service
        self.state = state

    def compose(self) -> ComposeResult:
        """Build the execution panel layout."""
        with Vertical():
            # Controls section
            with Horizontal(classes="execution-controls"):
                yield Button(
                    "Run Selected",
                    variant="primary",
                    id="run-button",
                    classes="run-button",
                )
                yield ProgressBar(
                    total=100,
                    show_eta=False,
                    id="progress-bar",
                    classes="hidden",
                )

            # Output section with tabs
            with TabbedContent(id="output-tabs"):
                with TabPane("Summary", id="tab-summary"):
                    yield RichLog(
                        id="summary-log",
                        classes="output-log",
                        auto_scroll=True,
                    )
                    yield Input(
                        placeholder="Filter summary...",
                        id="summary-filter",
                        classes="filter-input hidden",
                    )
                with TabPane("Output", id="tab-output"):
                    yield RichLog(
                        id="output-log",
                        classes="output-log",
                        auto_scroll=True,
                    )
                    yield Input(
                        placeholder="Filter output...",
                        id="output-filter",
                        classes="filter-input hidden",
                    )

    async def initialize(self) -> None:
        """Initialize the execution panel."""
        # Subscribe to state changes
        self.state.subscribe("execution_changed", self._update_execution_display)
        self.state.subscribe("selection_changed", self._update_run_button)

        # Initial state
        self._update_run_button()

    @on(Button.Pressed, "#run-button")
    def on_run_pressed(self, event: Button.Pressed) -> None:
        """Handle run button press."""
        self.start_execution()

    @work
    async def start_execution(self) -> None:
        """Start command execution."""
        if not self.state.has_selections():
            self.app.notify(
                "Please select targets and actions first", severity="warning"
            )
            return

        if self.state.execution.is_running:
            self.app.notify("Execution already in progress", severity="warning")
            return

        try:
            # Import execution service here to avoid circular imports
            from network_toolkit.tui.execution import ExecutionService

            service = ExecutionService(self.data_service, self.state)
            await service.execute()

        except Exception as e:
            self.app.notify(f"Execution failed: {e}", severity="error")
            self.state.clear_execution()

    def _update_run_button(self) -> None:
        """Update run button state based on selections."""
        run_button = self.query_one("#run-button", Button)
        has_selections = self.state.has_selections()
        is_running = self.state.execution.is_running

        run_button.disabled = not has_selections or is_running

        if is_running:
            run_button.label = "Running..."
        elif has_selections:
            run_button.label = "Run Selected"
        else:
            run_button.label = "Select Targets & Actions"

    def _update_execution_display(self) -> None:
        """Update execution display based on current state."""
        progress_bar = self.query_one("#progress-bar", ProgressBar)

        if self.state.execution.is_running:
            progress_bar.remove_class("hidden")
            if self.state.execution.total_devices > 0:
                progress = (
                    self.state.execution.completed_devices
                    / self.state.execution.total_devices
                ) * 100
                progress_bar.update(progress=progress)
        else:
            progress_bar.add_class("hidden")

    def toggle_summary(self) -> None:
        """Toggle summary panel visibility."""
        summary_filter = self.query_one("#summary-filter", Input)
        if summary_filter.has_class("hidden"):
            summary_filter.remove_class("hidden")
            self.state.update_ui(show_summary=True)
        else:
            summary_filter.add_class("hidden")
            self.state.update_ui(show_summary=False)

    def toggle_output(self) -> None:
        """Toggle output panel visibility."""
        output_filter = self.query_one("#output-filter", Input)
        if output_filter.has_class("hidden"):
            output_filter.remove_class("hidden")
            self.state.update_ui(show_output=True)
        else:
            output_filter.add_class("hidden")
            self.state.update_ui(show_output=False)


class StatusBar(Static):
    """Status bar showing current application state."""

    def __init__(
        self,
        state: AppState,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes)
        self.state = state

    async def initialize(self) -> None:
        """Initialize the status bar."""
        self.state.subscribe("execution_changed", self._update_status)
        self.state.subscribe("selection_changed", self._update_status)
        self._update_status()

    def _update_status(self) -> None:
        """Update status display."""
        message = self.state.get_status_message()

        # Apply appropriate styling based on state
        if self.state.execution.is_running:
            self.update(f"[bold yellow]{message}[/bold yellow]")
            self.remove_class("status-idle status-success status-error")
            self.add_class("status-running")
        elif self.state.execution.total_devices > 0:
            if self.state.execution.failed_devices > 0:
                self.update(f"[bold red]{message}[/bold red]")
                self.remove_class("status-idle status-running status-success")
                self.add_class("status-error")
            else:
                self.update(f"[bold green]{message}[/bold green]")
                self.remove_class("status-idle status-running status-error")
                self.add_class("status-success")
        else:
            self.update(f"[dim]{message}[/dim]")
            self.remove_class("status-running status-success status-error")
            self.add_class("status-idle")
