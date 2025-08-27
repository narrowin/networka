from __future__ import annotations

# pyright: reportPrivateUsage=false, reportAttributeAccessIssue=false
import asyncio
from typing import Any

import pytest

from network_toolkit.tui.controller import TuiController
from network_toolkit.tui.models import CancellationToken, SelectionState


class _DummyWidget:
    def __init__(self) -> None:
        self._text: str = ""
        self.classes: list[str] = []

        class _Styles:
            display: str = "block"

        self.styles = _Styles()

    def clear(self) -> None:
        self._text = ""

    def update(self, text: Any) -> None:
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
        self._run_active = False
        self._cancel_token: CancellationToken | None = None
        self._bg_tasks: set[asyncio.Task[Any]] = set()
        self._meta: list[str] = []
        self._errors: list[str] = []
        self._output_lines: list[str] = []

        self._w_output_log = _DummyWidget()
        self._w_summary = _DummyWidget()
        self._w_status = _DummyWidget()
        self._w_output_panel = _DummyWidget()
        self._w_summary_panel = _DummyWidget()
        self._w_help_panel = _DummyWidget()
        self._w_bottom = _DummyWidget()

        # Flags toggled by controller prompts
        self._cancel_prompt_active = False
        self._cancel_mode_prompt_active = False

    def _dispatch_ui(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        fn(*args, **kwargs)

    def _show_bottom_panel(self) -> None:
        self._w_bottom.remove_class("hidden")

    def _refresh_bottom_visibility(self) -> None:
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

    # No-ops required by controller but irrelevant in these paths
    def _collect_state(self) -> None:  # pragma: no cover
        return

    def _set_inputs_enabled(self, enabled: bool) -> None:  # pragma: no cover
        pass

    def _set_run_enabled(self, enabled: bool) -> None:  # pragma: no cover
        pass


class _Event:
    def __init__(self, key: str) -> None:
        self.key = key
        self._stopped = False

    def stop(self) -> None:
        self._stopped = True


class _FakeService:
    def __init__(self) -> None:
        self.hard_cancel_called = False

    def request_hard_cancel(self, _token: Any) -> None:
        self.hard_cancel_called = True


@pytest.mark.asyncio
async def test_cancel_prompt_no_keeps_running() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    svc = _FakeService()
    ctl = TuiController(app, compat=object(), data=object(), service=svc, state=state)

    # Simulate active run
    app._run_active = True
    await ctl.action_confirm()
    assert app._cancel_prompt_active is True
    assert any("Run already in progress" in m for m in app._meta)

    # Press '1' -> continue running
    evt = _Event("1")
    ctl.on_key(evt)
    assert app._cancel_prompt_active is False
    assert "Continuing current run" in app._w_status._text


@pytest.mark.asyncio
async def test_cancel_prompt_soft_cancel() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    svc = _FakeService()
    ctl = TuiController(app, compat=object(), data=object(), service=svc, state=state)

    # Simulate active run with token
    app._run_active = True
    app._cancel_token = CancellationToken()
    await ctl.action_confirm()
    assert app._cancel_prompt_active is True

    # Single-step: press '2' to soft-cancel
    ctl.on_key(_Event("2"))

    # Allow bg task to run
    await asyncio.sleep(0)
    assert app._cancel_token.is_set()
    assert "cancelling" in app._w_status._text.lower()


@pytest.mark.asyncio
async def test_cancel_prompt_hard_cancel() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices=set(), groups=set(), sequences=set(), command_text=""
    )
    svc = _FakeService()
    ctl = TuiController(app, compat=object(), data=object(), service=svc, state=state)

    app._run_active = True
    app._cancel_token = CancellationToken()
    await ctl.action_confirm()
    assert app._cancel_prompt_active is True

    # Single-step: press '3' to hard-cancel
    ctl.on_key(_Event("3"))
    await asyncio.sleep(0)
    assert app._cancel_token.is_set()
    assert svc.hard_cancel_called is True
    assert "cancelling (hard)" in app._w_status._text.lower()
