# SPDX-License-Identifier: MIT
"""Tests for the library-first run API."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from network_toolkit.api.run import (
    DeviceSequenceResult,
    RunOptions,
    RunResult,
    TargetResolutionError,
    run_commands,
)
from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import DeviceExecutionError, OperationUnconfirmedError
from network_toolkit.session_pool import SessionPool


class DummyDeviceSession:
    """In-memory DeviceSession replacement for tests."""

    def __init__(
        self,
        device_name: str,
        config: NetworkConfig,
        username_override: str | None = None,
        password_override: str | None = None,
        transport_override: str | None = None,
    ) -> None:
        self.device_name = device_name
        self.config = config
        self.username_override = username_override
        self.password_override = password_override
        self.transport_override = transport_override
        self.commands: list[str] = []

    def __enter__(self) -> DummyDeviceSession:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def execute_command(self, command: str) -> str:
        self.commands.append(command)
        return f"{self.device_name}:{command}"


@pytest.fixture
def patch_device_session(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[DummyDeviceSession], None]:
    """Monkeypatch the DeviceSession used by the API with a dummy implementation."""

    def _apply(session_cls: type[DummyDeviceSession]) -> None:
        monkeypatch.setattr("network_toolkit.device.DeviceSession", session_cls)

    return _apply


def test_run_commands_single_device_command(
    sample_config: NetworkConfig,
    tmp_path: Path,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(DummyDeviceSession)

    options = RunOptions(
        target="test_device1",
        command_or_sequence="/system/clock/print",
        config=sample_config,
        store_results=True,
        results_dir=str(tmp_path),
    )

    result = run_commands(options)

    assert result.is_sequence is False
    assert result.totals.total == 1
    assert result.totals.succeeded == 1
    assert not result.command_results[0].error
    assert result.command_results[0].output == "test_device1:/system/clock/print"
    assert result.results_dir is not None
    assert result.results_dir.exists()


def test_run_commands_group_sequence(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_device_session(DummyDeviceSession)

    # Force sequence resolution regardless of actual config contents
    monkeypatch.setattr(
        "network_toolkit.api.run.SequenceManager.exists", lambda _self, _name: True
    )
    monkeypatch.setattr(
        "network_toolkit.api.run.SequenceManager.resolve",
        lambda _self, _name, _device: ["cmd_a", "cmd_b"],
    )

    options = RunOptions(
        target="lab_devices",
        command_or_sequence="health_check",
        config=sample_config,
        store_results=False,
    )

    result = run_commands(options)

    assert result.is_sequence is True
    assert result.is_group is True
    assert result.totals.total == 2
    assert result.totals.failed == 0
    assert all(
        isinstance(device_result, DeviceSequenceResult)
        for device_result in result.sequence_results
    )
    # Ensure deterministic ordering follows group resolution
    assert [r.device for r in result.sequence_results] == result.resolution.resolved
    assert all(
        r.outputs == {"cmd_a": f"{r.device}:cmd_a", "cmd_b": f"{r.device}:cmd_b"}
        for r in result.sequence_results
    )


def test_run_commands_unknown_target_raises(sample_config: NetworkConfig) -> None:
    options = RunOptions(
        target="does_not_exist",
        command_or_sequence="/system/clock/print",
        config=sample_config,
    )

    with pytest.raises(TargetResolutionError) as excinfo:
        run_commands(options)

    assert "No devices resolved" in excinfo.value.message


class FailingDeviceSession(DummyDeviceSession):
    """Dummy session that rejects one command and loses the transport on another."""

    disconnects = 0

    def connect(self) -> None:
        return None

    def disconnect(self) -> None:
        FailingDeviceSession.disconnects += 1

    def execute_command(self, command: str) -> str:
        if command == "rejected":
            msg = f"Command failed on {self.device_name}: {command}"
            raise DeviceExecutionError(msg)
        if command == "lost":
            msg = "Device did not acknowledge the command"
            raise OperationUnconfirmedError(msg, command=command)
        return super().execute_command(command)


def _force_sequence(monkeypatch: pytest.MonkeyPatch, commands: list[str]) -> None:
    monkeypatch.setattr(
        "network_toolkit.api.run.SequenceManager.exists", lambda _self, _name: True
    )
    monkeypatch.setattr(
        "network_toolkit.api.run.SequenceManager.resolve",
        lambda _self, _name, _device: commands,
    )


@pytest.mark.parametrize("use_pool", [False, True])
def test_sequence_failure_keeps_earlier_outputs(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
    monkeypatch: pytest.MonkeyPatch,
    use_pool: bool,
) -> None:
    patch_device_session(FailingDeviceSession)
    _force_sequence(monkeypatch, ["cmd_a", "rejected", "cmd_c"])

    result = run_commands(
        RunOptions(
            target="test_device1",
            command_or_sequence="health_check",
            config=sample_config,
            session_pool=SessionPool() if use_pool else None,
        )
    )

    device_result = result.sequence_results[0]
    assert result.totals.failed == 1
    assert device_result.error == "Command failed on test_device1: rejected"
    assert device_result.outputs == {"cmd_a": "test_device1:cmd_a"}


def test_sequence_success_has_no_error(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_device_session(FailingDeviceSession)
    _force_sequence(monkeypatch, ["cmd_a", "cmd_b"])

    result = run_commands(
        RunOptions(
            target="test_device1",
            command_or_sequence="health_check",
            config=sample_config,
            session_pool=SessionPool(),
        )
    )

    assert result.sequence_results[0].error is None
    assert result.totals.failed == 0


def test_lost_transport_drops_pooled_session_without_repeating(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(FailingDeviceSession)
    FailingDeviceSession.disconnects = 0
    pool = SessionPool()

    def run(command: str) -> RunResult:
        return run_commands(
            RunOptions(
                target="test_device1",
                command_or_sequence=command,
                config=sample_config,
                session_pool=pool,
            )
        )

    run("cmd_a")
    first = pool.get("test_device1")
    assert first is not None

    lost = run("lost")
    assert lost.command_results[0].error == "Device did not acknowledge the command"
    assert pool.get("test_device1") is None
    assert FailingDeviceSession.disconnects == 1

    again = run("cmd_b")
    second = pool.get("test_device1")
    assert again.command_results[0].output == "test_device1:cmd_b"
    assert second is not None and second is not first
    assert second.commands == ["cmd_b"]


def test_rejected_command_keeps_pooled_session(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(FailingDeviceSession)
    pool = SessionPool()
    options = RunOptions(
        target="test_device1",
        command_or_sequence="rejected",
        config=sample_config,
        session_pool=pool,
    )

    result = run_commands(options)

    assert result.command_results[0].error is not None
    assert pool.get("test_device1") is not None
