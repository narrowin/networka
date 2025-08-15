from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.tui.data import TuiData
from network_toolkit.tui.models import (
    ExecutionPlan,
    RunCallbacks,
    RunResult,
    SelectionState,
    iter_commands,
)
from network_toolkit.tui.services import ExecutionService


def test_selection_state_validates_sets_and_defaults() -> None:
    s = SelectionState(
        devices={"a", "b"},
        groups={"g1", "g2"},
        sequences=set(),
        command_text=" ",
    )
    assert s.devices == {"a", "b"}
    assert s.groups == {"g1", "g2"}
    assert s.sequences == set()
    assert s.command_text == " "


def test_run_result_human_summary() -> None:
    r = RunResult(total=3, successes=2, failures=1)
    assert "2 succeeded" in r.human_summary()
    assert "1 failed" in r.human_summary()
    assert "total: 3" in r.human_summary()


def test_iter_commands_splits_and_trims() -> None:
    text = "\n show ver \n\n  /system/identity/print  \n"
    assert list(iter_commands(text)) == ["show ver", "/system/identity/print"]


@pytest.mark.asyncio
async def test_execution_service_build_and_run_plan_smoke(monkeypatch: Any) -> None:
    data = TuiData("config")
    svc = ExecutionService(data, concurrency=2)

    devices = data.targets().devices[:2]
    if not devices:
        pytest.skip("No devices available in repository test config")

    plan: ExecutionPlan = svc.build_plan(devices, sequences=[], command_text="/system/identity/print")
    assert set(plan.keys()) == set(devices)
    assert all(plan[d] for d in plan)

    calls: list[str] = []

    def fake_run(device: str, commands: list[str], cb: RunCallbacks) -> bool:
        calls.append(device)
        cb.on_meta(f"{device}: connected")
        for cmd in commands:
            cb.on_meta(f"{device}$ {cmd}")
            cb.on_output(f"{device}: output for {cmd}")
        return True

    monkeypatch.setattr(svc, "_run_device_blocking", fake_run)

    outputs: list[str] = []
    errors: list[str] = []
    metas: list[str] = []

    result = await svc.run_plan(
        plan,
        RunCallbacks(
            on_output=lambda m: outputs.append(m),
            on_error=lambda m: errors.append(m),
            on_meta=lambda m: metas.append(m),
        ),
    )

    assert isinstance(result, RunResult)
    assert result.total == len(devices)
    assert result.failures == 0
    assert result.successes == len(devices)
    assert not errors
    assert any("connected" in m for m in metas)
    assert outputs
