from __future__ import annotations

import asyncio
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
        # Controller runtime fields
        self._run_active = False
        self._cancel_token = None
        self._bg_tasks: set[asyncio.Task[Any]] = set()
        self._meta: list[str] = []
        self._errors: list[str] = []
        self._output_lines: list[str] = []
        # Reset tracking
        self.reset_calls = 0

        # Widgets used by the controller
        self._w_output_log = _DummyWidget()
        self._w_summary = _DummyWidget()
        self._w_status = _DummyWidget()
        self._w_output_panel = _DummyWidget()
        self._w_summary_panel = _DummyWidget()
        self._w_help_panel = _DummyWidget()
        self._w_bottom = _DummyWidget()

    # public accessor for tests
    @property
    def is_running(self) -> bool:
        return bool(self._run_active)

    def _reset_output_tabs(self) -> None:
        self.reset_calls += 1

    def _collect_state(self) -> None:
        pass

    def _dispatch_ui(self, fn: Any, *args: Any, **kwargs: Any) -> None:
        fn(*args, **kwargs)

    def _set_inputs_enabled(self, enabled: bool) -> None:
        pass

    def _set_run_enabled(self, enabled: bool) -> None:
        pass

    def _render_summary(self, base_summary: str | None = None) -> None:
        self._w_summary.update(base_summary or "")

    def _show_bottom_panel(self) -> None:
        self._w_bottom.remove_class("hidden")

    def _hide_summary_panel(self) -> None:
        self._w_summary_panel.add_class("hidden")

    def _hide_output_panel(self) -> None:
        self._w_output_panel.add_class("hidden")

    def _show_summary_panel(self) -> None:
        self._w_summary_panel.remove_class("hidden")

    def _show_output_panel(self) -> None:
        self._w_output_panel.remove_class("hidden")

    def _refresh_bottom_visibility(self) -> None:
        pass

    def _add_meta(self, msg: str) -> None:
        self._meta.append(str(msg))

    def _add_error(self, msg: str) -> None:
        self._errors.append(str(msg))

    def _output_append(self, msg: str) -> None:
        self._output_lines.append(str(msg))

    def _output_append_device(self, _device: str, msg: str) -> None:
        self._output_lines.append(str(msg))

    def _clear_all_selections(self) -> None:
        pass

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
    def resolve_devices(self, _devices: Any, _groups: Any) -> list[str]:
        return ["d1"]

    def build_plan(self, devices: list[str], _s: Any, _c: str) -> dict[str, list[str]]:
        return {devices[0]: ["cmd"]}

    async def run_plan(self, _plan: dict[str, list[str]], _cb: Any, **_: Any) -> Any:
        class R:
            total = 1
            successes = 1
            failures = 0

            def human_summary(self) -> str:
                return "done"

        return R()


@pytest.mark.asyncio
async def test_controller_calls_reset_tabs_on_each_run() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices={"d1"}, groups=set(), sequences=set(), command_text="show"
    )
    ctl = TuiController(
        app, compat=object(), data=object(), service=_FakeService(), state=state
    )

    await ctl.action_confirm()
    # Wait for the first run to finish
    for _ in range(100):
        if not app.is_running:
            break
        await asyncio.sleep(0.01)
    assert app.reset_calls == 1

    # Trigger a second run; should reset again
    await ctl.action_confirm()
    for _ in range(100):
        if not app.is_running:
            break
        await asyncio.sleep(0.01)
    assert app.reset_calls == 2
