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
                *[(item, item) for item in self._all_items],
                id=f"{self.id}-list",
                classes="scrollable",
            )

    def on_mount(self) -> None:
        """Initialize after mounting."""
        self._update_selection_tracking()

    @on(Input.Changed)
    def on_filter_changed(self, event: Input.Changed) -> None:
        """Handle filter input changes."""
        # Only handle our own filter input
        if event.input.id == f"{self.id}-filter":
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

            devices_list = self.query_one("#devices-list-list", SelectionList)
            # Clear existing options and add new ones
            devices_list.clear_options()
            for device in targets.devices:
                devices_list.add_option((device, device))

            groups_list = self.query_one("#groups-list-list", SelectionList)
            groups_list.clear_options()
            for group in targets.groups:
                groups_list.add_option((group, group))

            # For now, we'll handle selection changes via event handlers instead of watch

        except Exception as e:
            self.app.notify(f"Failed to load targets: {e}", severity="error")

    async def on_mount(self) -> None:
        """Initialize the panel when mounted."""
        await self.initialize()

    @on(SelectionList.SelectedChanged)
    def on_devices_selection_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        """Handle device selection changes."""
        # Only handle events from our devices list
        if event.selection_list.id == "devices-list-list":
            try:
                selection_list = event.selection_list
                selected = {str(item) for item in selection_list.selected}
                self.state.update_selection(devices=selected)
            except Exception:
                # Handle event processing errors gracefully
                pass

    @on(SelectionList.SelectedChanged)
    def on_groups_selection_changed(self, event: SelectionList.SelectedChanged) -> None:
        """Handle group selection changes."""
        # Only handle events from our groups list
        if event.selection_list.id == "groups-list-list":
            try:
                selection_list = event.selection_list
                selected = {str(item) for item in selection_list.selected}
                self.state.update_selection(groups=selected)
            except Exception:
                # Handle event processing errors gracefully
                pass

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
                    id="commands-input",
                    classes="command-input",
                )

    async def initialize(self) -> None:
        """Initialize the panel with data."""
        try:
            actions = await self.data_service.get_actions()

            sequences_list = self.query_one("#sequences-list-list", SelectionList)
            sequences_list.clear_options()
            for sequence in actions.sequences:
                sequences_list.add_option((sequence, sequence))

            # For now, we'll handle selection changes via event handlers instead of watch

        except Exception as e:
            self.app.notify(f"Failed to load actions: {e}", severity="error")

    async def on_mount(self) -> None:
        """Initialize the panel when mounted."""
        await self.initialize()

    @on(SelectionList.SelectedChanged)
    def on_sequences_selection_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        """Handle sequence selection changes."""
        # Only handle events from our sequences list
        if event.selection_list.id == "sequences-list-list":
            try:
                selection_list = event.selection_list
                selected = {str(item) for item in selection_list.selected}
                self.state.update_selection(sequences=selected)
            except Exception:
                # Handle event processing errors gracefully
                pass

    @on(TextArea.Changed, "#commands-input")
    def on_commands_changed(self, event: TextArea.Changed) -> None:
        """Handle command text changes."""
        self.state.update_selection(command_text=event.text_area.text)

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
            # Progress section (hidden by default)
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

        # Initial state - no need to update button since it doesn't exist

    async def on_mount(self) -> None:
        """Initialize the panel when mounted."""
        await self.initialize()

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
            from network_toolkit.tui.execution import (
                ExecutionCallbacks,
                ExecutionManager,
            )

            # Mark execution as starting
            self.state.update_execution(
                is_running=True, total_devices=0, completed_devices=0, failed_devices=0
            )

            # Clear output logs
            summary_log = self.query_one("#summary-log", RichLog)
            output_log = self.query_one("#output-log", RichLog)
            summary_log.clear()
            output_log.clear()

            # Get execution details
            devices = list(self.state.selection.devices)
            groups = list(self.state.selection.groups)
            sequences = list(self.state.selection.sequences)
            command_text = self.state.selection.command_text.strip()

            # Create execution manager using the data service directly
            execution_manager = ExecutionManager(self.data_service, concurrency=5)
            resolved_devices = execution_manager.resolve_devices(devices, groups)

            if not resolved_devices:
                self.app.notify(
                    "No valid devices found in selection", severity="warning"
                )
                return

            # Build execution plan
            execution_plan = execution_manager.build_execution_plan(
                resolved_devices, sequences, command_text
            )

            if not execution_plan:
                self.app.notify("No commands to execute", severity="warning")
                return

            total_devices = len(execution_plan)

            # Show what we're executing
            summary_log.write("[bold blue]Starting execution...[/bold blue]")
            summary_log.write(f"Devices: {resolved_devices}")
            if sequences:
                summary_log.write(f"Sequences: {sequences}")
            if command_text:
                commands = [
                    cmd.strip() for cmd in command_text.splitlines() if cmd.strip()
                ]
                summary_log.write(f"Commands: {len(commands)} custom commands")

            # Update progress tracking
            self.state.update_execution(
                total_devices=total_devices, completed_devices=0, failed_devices=0
            )

            # Set up callbacks for real-time updates
            def write_output(msg: str) -> None:
                output_log.write(msg)

            def write_error(msg: str) -> None:
                output_log.write(f"[red]{msg}[/red]")

            def write_progress(msg: str) -> None:
                # For now, just write progress messages to summary
                summary_log.write(f"[dim]{msg}[/dim]")

            callbacks = ExecutionCallbacks(
                on_output=write_output,
                on_error=write_error,
                on_progress=write_progress,
            )

            # Execute the plan
            result = await execution_manager.execute_plan(execution_plan, callbacks)

            # Update final state
            self.state.update_execution(
                total_devices=result.total,
                completed_devices=result.successes,
                failed_devices=result.failures,
            )

            # Show completion summary
            if result.failures > 0:
                summary_log.write(
                    f"[yellow]⚠ Execution completed with errors: {result.human_summary()}[/yellow]"
                )
                self.app.notify(
                    f"Execution completed with {result.failures} failures",
                    severity="warning",
                )
            else:
                summary_log.write(
                    f"[bold green]✓ Execution completed successfully: {result.human_summary()}[/bold green]"
                )
                self.app.notify(
                    f"Execution completed successfully on {result.successes} devices",
                    severity="information",
                )

        except Exception as e:
            self.app.notify(f"Execution failed: {e}", severity="error")
            try:
                summary_log = self.query_one("#summary-log", RichLog)
                summary_log.write(f"[bold red]ERROR:[/bold red] {e}")
            except Exception:
                pass
        finally:
            self.state.update_execution(is_running=False)

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

    async def on_mount(self) -> None:
        """Initialize the status bar when mounted."""
        await self.initialize()

    def _update_status(self) -> None:
        """Update status display."""
        message = self.state.get_status_message()

        # Apply appropriate styling based on state
        if self.state.execution.is_running:
            self.update(f"[bold yellow]{message}[/bold yellow]")
            self.remove_class("status-idle", "status-success", "status-error")
            self.add_class("status-running")
        elif self.state.execution.total_devices > 0:
            if self.state.execution.failed_devices > 0:
                self.update(f"[bold red]{message}[/bold red]")
                self.remove_class("status-idle", "status-running", "status-success")
                self.add_class("status-error")
            else:
                self.update(f"[bold green]{message}[/bold green]")
                self.remove_class("status-idle", "status-running", "status-error")
                self.add_class("status-success")
        else:
            self.update(f"[dim]{message}[/dim]")
            self.remove_class("status-running", "status-success", "status-error")
            self.add_class("status-idle")
