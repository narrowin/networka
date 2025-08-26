from __future__ import annotations

from typing import Any

import pytest

from network_toolkit.tui.data import TuiData
from network_toolkit.tui.models import CancellationToken, RunCallbacks
from network_toolkit.tui.services import DeviceRunResult, ExecutionService


@pytest.mark.asyncio
async def test_service_respects_pre_start_cancellation(monkeypatch: Any) -> None:
    data = TuiData("config")
    svc = ExecutionService(data, concurrency=2)
    plan = {"d1": ["cmd1"], "d2": ["cmd2"]}
    cancel = CancellationToken()
    cancel.set()

    outputs: list[str] = []
    metas: list[str] = []
    errors: list[str] = []

    # Speed up: monkeypatch resolver path to skip device work
    async def fast_run(
        plan: dict[str, list[str]],
        cb: RunCallbacks,
        cancel: CancellationToken | None = None,
    ) -> Any:  # type: ignore[override]
        return await ExecutionService.run_plan(svc, plan, cb, cancel=cancel)  # noqa: PIE804

    # Use real implementation; cancellation is handled inside run_plan
    result = await svc.run_plan(
        plan,
        RunCallbacks(
            on_output=outputs.append,
            on_error=errors.append,
            on_meta=metas.append,
        ),
        cancel=cancel,
    )

    assert result.total == 2
    # With pre-start cancel, devices may be skipped and recorded as not ok
    assert result.failures >= 1
    assert any("cancelled" in m.lower() for m in metas)


@pytest.mark.asyncio
async def test_service_emits_outputs_grouped_and_ordered(monkeypatch: Any) -> None:
    data = TuiData("config")
    svc = ExecutionService(data, concurrency=2)
    plan = {"a": ["c1", "c2"], "b": ["c3"]}

    def fake_run(device: str, commands: list[str], cb: RunCallbacks) -> DeviceRunResult:
        # Emit meta markers and buffer outputs to be emitted in plan order
        cb.on_meta(f"{device}: connected")
        lines = [f"{device}: out {c}" for c in commands]
        cb.on_meta(f"{device}: done")
        return DeviceRunResult(device=device, ok=True, output_lines=lines)

    monkeypatch.setattr(svc, "_run_device_blocking", fake_run)

    outputs: list[str] = []
    metas: list[str] = []

    def _noop_error(_m: str) -> None:
        return None

    await svc.run_plan(
        plan,
        RunCallbacks(
            on_output=outputs.append,
            on_error=_noop_error,
            on_meta=metas.append,
        ),
    )

    # Outputs should be grouped per device and ordered by plan keys: a then b
    expected = [
        "a: out c1",
        "a: out c2",
        "b: out c3",
    ]
    assert outputs == expected
