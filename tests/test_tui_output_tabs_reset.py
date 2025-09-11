from __future__ import annotations

import asyncio
from typing import Any

import pytest

from network_toolkit.tui.controller import TuiController
from network_toolkit.tui.models import SelectionState


class _DummyLog:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def clear(self) -> None:
        self.lines.clear()

    def write(self, msg: str) -> None:
        self.lines.append(msg)


class _DummyTabs:
    def __init__(self) -> None:
        self._panes: dict[str, Any] = {"output-tab-all": object()}
        self.active: Any = "output-tab-all"

    # Compatibility surface used by app._ensure_device_tab/_reset_output_tabs
    def add_pane(self, pane: Any) -> None:
        pane_id = getattr(pane, "id", None)
        if pane_id:
            self._panes[pane_id] = pane

    def add(self, pane: Any) -> None:
        self.add_pane(pane)

    def remove(self, pane: Any) -> None:
        pid = getattr(pane, "id", None)
        if pid in self._panes:
            del self._panes[pid]

    @property
    def children(self) -> list[Any]:
        return [type("C", (), {"id": k})() for k in self._panes]

    def clear_device_panes(self) -> None:
        self._panes = {"output-tab-all": object()}


class _FakeApp:
    def __init__(self) -> None:
        self._output_lines: list[str] = []
        self._output_device_logs: dict[str, _DummyLog] = {}
        self._output_device_lines: dict[str, list[str]] = {}
        self._tabs = _DummyTabs()
        self._all = _DummyLog()
        self._meta: list[str] = []

    def _set_inputs_enabled(self, enabled: bool) -> None:
        """Mock implementation for input state management."""
        pass

    def _set_run_enabled(self, enabled: bool) -> None:
        """Mock implementation for run button state management."""
        pass

    def query_one(self, selector: str) -> Any:
        if selector == "#output-log":
            return self._all
        if selector == "#output-tabs":
            return self._tabs

        # Fallback: construct an object with matching id
        class W:
            def __init__(self, _id: str) -> None:
                self.id = _id

            def remove(self) -> None:
                pass

            def unmount(self) -> None:
                pass

        if selector.startswith("#output-tab-"):
            return W(selector[1:])
        # Provide dummies for other selectors used in controller
        return W(selector.strip("#"))

    def _sanitize_id(self, name: str) -> str:
        return name

    def _maybe_show_output_panel(self) -> None:
        pass

    def _apply_output_filter(self, value: str) -> None:
        pass

    def _add_meta(self, msg: str) -> None:
        self._meta.append(str(msg))

    # Minimal behaviors used by controller callbacks
    def _ensure_device_tab(self, device: str) -> Any:
        pane_id = f"output-tab-{device}"
        # Create a lightweight pane object with an id attribute
        pane = type("Pane", (), {"id": pane_id})()
        self._tabs.add_pane(pane)
        # Return a dummy log; not used in this test
        log = _DummyLog()
        self._output_device_logs[device] = log
        self._output_device_lines.setdefault(device, [])
        return log

    def _output_append_device(self, device: str, msg: str) -> None:
        # Ensure tab exists, then record the lines
        self._ensure_device_tab(device)
        lines = [str(x) for x in str(msg).splitlines()]
        self._output_lines.extend(lines)
        self._output_device_lines.setdefault(device, []).extend(lines)

    def _reset_output_tabs(self) -> None:
        # Clear device panes, keep All
        self._tabs.clear_device_panes()
        self._output_device_logs.clear()
        self._output_device_lines.clear()


class _FakeService:
    def resolve_devices(self, _d: Any, _g: Any) -> list[str]:
        return ["dev1", "dev2"]

    def build_plan(self, devices: list[str], _s: Any, _c: str) -> dict[str, list[str]]:
        return {d: ["cmd1"] for d in devices}

    async def run_plan(self, plan: dict[str, list[str]], cb: Any, **_: Any) -> Any:
        # Simulate streaming output that triggers tab creation
        for dev, cmds in plan.items():
            for cmd in cmds:
                cb.on_device_output(
                    dev, f"-- {dev}: {cmd} --\nline\n-- finish {dev}: {cmd} --"
                )

        class R:
            def __init__(self) -> None:
                self.total = len(plan)
                self.successes = len(plan)
                self.failures = 0

            def human_summary(self) -> str:
                return "ok"

        return R()


@pytest.mark.skip("Complex TUI integration test needs refactoring")
@pytest.mark.asyncio
async def test_output_tabs_cleared_on_new_run() -> None:
    app = _FakeApp()
    state = SelectionState(
        devices={"devX"}, groups=set(), sequences=set(), command_text="echo"
    )
    ctl = TuiController(
        app, compat=object(), data=object(), service=_FakeService(), state=state
    )

    # First run creates tabs for dev1/dev2
    await ctl.action_confirm()
    await asyncio.sleep(0)
    tabs = app.query_one("#output-tabs")
    assert any(
        c.id.startswith("output-tab-") and c.id != "output-tab-all"
        for c in tabs.children
    )

    # Second run should clear tabs before creating new ones
    await ctl.action_confirm()
    await asyncio.sleep(0)
    tabs2 = app.query_one("#output-tabs")
    device_tabs = [c.id for c in tabs2.children if c.id != "output-tab-all"]
    # After reset, new run repopulated them, but no duplicates should linger
    assert len(device_tabs) == len(set(device_tabs))
    assert all(t.startswith("output-tab-") for t in device_tabs)
