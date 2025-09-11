from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from network_toolkit.tui.controller import TuiController
from network_toolkit.tui.models import SelectionState


class _DummyWidget:
    def __init__(self) -> None:
        self._text: str = ""
        self.classes: list[str] = []

        class _Styles:
            display: str = "block"

        self.styles = _Styles()

    def clear(self) -> None:  # For output-log
        self._text = ""

    def update(self, text: Any) -> None:  # For summary/status
        self._text = str(text)

    def add_class(self, name: str) -> None:
        if name not in self.classes:
            self.classes.append(name)

    def remove_class(self, name: str) -> None:
        try:
            self.classes.remove(name)
        except ValueError:
            pass


class _FakeApp:
    def __init__(self) -> None:
        # Runtime state flags the controller expects
        self._run_active = False
        self._cancel_token = None
        self._bg_tasks: set[asyncio.Task[Any]] = set()
        self._meta: list[str] = []
        self._errors: list[str] = []
        self._output_lines: list[str] = []

        # Widgets used by the controller
        self._w_output_log = _DummyWidget()
        self._w_summary = _DummyWidget()
        self._w_status = _DummyWidget()
        self._w_output_panel = _DummyWidget()
        self._w_summary_panel = _DummyWidget()
        self._w_help_panel = _DummyWidget()
        self._w_bottom = _DummyWidget()

    # UI selection state collection (no-op for these tests)
    def _collect_state(self) -> None:  # pragma: no cover - simple noop
        return

    def _dispatch_ui(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        fn(*args, **kwargs)

    def _set_inputs_enabled(self, enabled: bool) -> None:  # pragma: no cover
        pass

    def _set_run_enabled(self, enabled: bool) -> None:  # pragma: no cover
        pass

    # Minimal render summary: write into summary widget
    def _render_summary(
        self, base_summary: str | None = None
    ) -> None:  # pragma: no cover
        text = base_summary or ""
        self._w_summary.update(text)

    def _show_bottom_panel(self) -> None:  # pragma: no cover
        self._w_bottom.remove_class("hidden")

    def _hide_summary_panel(self) -> None:  # pragma: no cover
        self._w_summary_panel.add_class("hidden")

    def _hide_output_panel(self) -> None:  # pragma: no cover
        self._w_output_panel.add_class("hidden")

    def _refresh_bottom_visibility(self) -> None:  # pragma: no cover
        pass

    def _add_meta(self, msg: str) -> None:
        self._meta.append(str(msg))

    def query_one(self, selector: str) -> _DummyWidget:
        mapping = {
            "#output-log": self._w_output_log,
            "#run-summary": self._w_summary,
            "#run-status": self._w_status,
            "#output-panel": self._w_output_panel,
            "#summary-panel": self._w_summary_panel,
            "#help-panel": self._w_help_panel,
            "#bottom": self._w_bottom,
        }
        return mapping[selector]


class _FakeService:
    def __init__(self, delay_s: float = 0.2) -> None:
        self.delay_s = delay_s

    def resolve_devices(self, devices: Any, groups: Any) -> list[str]:
        # Simulate slow work to keep run active long enough to trigger guard
        time.sleep(self.delay_s)
        return ["dev1"] if devices or groups is not None else []

    def build_plan(
        self, devices: list[str], sequences: Any, command_text: str
    ) -> dict[str, list[str]]:
        # Return empty plan to end run quickly after the delay
        return {}


@pytest.mark.asyncio
async def test_controller_prevents_concurrent_runs() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    svc = _FakeService(delay_s=0.2)
    ctl = TuiController(app, compat=object(), data=object(), service=svc, state=state)

    # Start first run; should set active and schedule background work
    await ctl.action_confirm()
    assert app._run_active is True

    # Second confirm while active should be rejected and add a meta note
    await ctl.action_confirm()
    assert any("already in progress" in m for m in app._meta)

    # Wait for background task to complete cleanly
    if app._run_task is not None:
        await asyncio.wait_for(app._run_task, timeout=2.0)
    assert app._run_active is False


@pytest.mark.asyncio
async def test_controller_cancel_sets_token_and_status() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    svc = _FakeService(delay_s=0.2)
    ctl = TuiController(app, compat=object(), data=object(), service=svc, state=state)

    # Start a run
    await ctl.action_confirm()
    assert app._run_active is True and app._cancel_token is not None

    # Request cancellation
    await ctl.action_cancel()
    assert app._cancel_token is not None and app._cancel_token.is_set()
    assert "cancelling" in app._w_status._text.lower()
    assert any("Cancellation requested" in m for m in app._meta)

    # Allow runner to finish
    if app._run_task is not None:
        await asyncio.wait_for(app._run_task, timeout=2.0)
    assert app._run_active is False
