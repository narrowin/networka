"""Core state management for the TUI application.

This module provides reactive state management using Pydantic models and Textual's
reactive system for clean, type-safe state handling throughout the application.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, Field


class SelectionState(BaseModel):
    """User selections for devices, groups, sequences, and commands."""

    model_config = {"frozen": False}

    devices: set[str] = Field(default_factory=set)
    groups: set[str] = Field(default_factory=set)
    sequences: set[str] = Field(default_factory=set)
    command_text: str = ""


class ExecutionState(BaseModel):
    """Current execution status and progress."""

    model_config = {"frozen": False}

    is_running: bool = False
    progress: str = ""
    total_devices: int = 0
    completed_devices: int = 0
    successful_devices: int = 0
    failed_devices: int = 0
    current_device: str = ""


class UIState(BaseModel):
    """UI-specific state for panels, filters, and visibility."""

    model_config = {"frozen": False}

    # Panel visibility
    show_summary: bool = False
    show_output: bool = False
    summary_user_hidden: bool = False
    output_user_hidden: bool = False

    # Filter states
    filter_devices: str = ""
    filter_groups: str = ""
    filter_sequences: str = ""
    filter_output: str = ""
    filter_summary: str = ""

    # Active tabs
    active_targets_tab: str = "devices"
    active_actions_tab: str = "sequences"


class AppState:
    """Central application state manager.

    Provides reactive state management with change callbacks and validation.
    """

    def __init__(self) -> None:
        self.selection = SelectionState()
        self.execution = ExecutionState()
        self.ui = UIState()

        # Change callbacks
        self._callbacks: dict[str, list[Callable[[], None]]] = {}

    def subscribe(self, event: str, callback: Callable[[], None]) -> None:
        """Subscribe to state changes.

        Args:
            event: The state change event to listen for
            callback: Function to call when the event occurs
        """
        if event not in self._callbacks:
            self._callbacks[event] = []
        self._callbacks[event].append(callback)

    def emit(self, event: str) -> None:
        """Emit a state change event.

        Args:
            event: The event to emit
        """
        for callback in self._callbacks.get(event, []):
            try:
                callback()
            except Exception:
                # Don't let callback errors break the app
                pass

    async def initialize(self) -> None:
        """Initialize the state system."""
        self.emit("initialized")

    def update_selection(self, **kwargs: Any) -> None:
        """Update selection state and emit change event."""
        for key, value in kwargs.items():
            if hasattr(self.selection, key):
                setattr(self.selection, key, value)
        self.emit("selection_changed")

    def update_execution(self, **kwargs: Any) -> None:
        """Update execution state and emit change event."""
        for key, value in kwargs.items():
            if hasattr(self.execution, key):
                setattr(self.execution, key, value)
        self.emit("execution_changed")

    def update_ui(self, **kwargs: Any) -> None:
        """Update UI state and emit change event."""
        for key, value in kwargs.items():
            if hasattr(self.ui, key):
                setattr(self.ui, key, value)
        self.emit("ui_changed")

    def get_selected_targets(self) -> set[str]:
        """Get all selected targets (devices + expanded groups)."""
        targets = set(self.selection.devices)
        # Groups will be expanded by the execution service
        targets.update(self.selection.groups)
        return targets

    def has_selections(self) -> bool:
        """Check if any targets and actions are selected."""
        has_targets = bool(self.selection.devices or self.selection.groups)
        has_actions = bool(
            self.selection.sequences or self.selection.command_text.strip()
        )
        return has_targets and has_actions

    def clear_execution(self) -> None:
        """Reset execution state to idle."""
        self.execution = ExecutionState()
        self.emit("execution_changed")

    def get_status_message(self) -> str:
        """Get current status message for display."""
        if self.execution.is_running:
            if self.execution.current_device:
                return f"Running on {self.execution.current_device}... ({self.execution.completed_devices}/{self.execution.total_devices})"
            return f"Starting execution... ({self.execution.completed_devices}/{self.execution.total_devices})"

        if self.execution.total_devices > 0:
            return f"Completed: {self.execution.successful_devices} succeeded, {self.execution.failed_devices} failed"

        return "Ready"
