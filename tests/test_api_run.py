# SPDX-License-Identifier: MIT
"""Tests for the library-first run API."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, ClassVar
from unittest.mock import MagicMock

import pytest

from network_toolkit.api.run import (
    DeviceSequenceResult,
    RunOptions,
    RunResult,
    TargetResolutionError,
    run_commands,
)
from network_toolkit.config import NetworkConfig
from network_toolkit.exceptions import (
    DeviceConnectionError,
    DeviceExecutionError,
    OperationUnconfirmedError,
)
from network_toolkit.sequence_manager import SequenceManager
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
) -> None:
    patch_device_session(DummyDeviceSession)
    assert sample_config.devices is not None
    sample_config.devices["test_device1"].command_sequences = {
        "device_local_report": ["cmd_a", "cmd_b"]
    }

    options = RunOptions(
        target="lab_devices",
        command_or_sequence="device_local_report",
        config=sample_config,
        store_results=False,
    )

    result = run_commands(options)

    assert result.is_sequence is True
    assert result.is_group is True
    assert result.totals.total == 2
    assert result.totals.succeeded == 1
    assert result.totals.failed == 1
    assert not result.command_results
    assert all(
        isinstance(device_result, DeviceSequenceResult)
        for device_result in result.sequence_results
    )
    # Ensure deterministic ordering follows group resolution
    assert [r.device for r in result.sequence_results] == result.resolution.resolved
    owning_device, other_device = result.sequence_results
    assert owning_device.outputs == {
        "cmd_a": "test_device1:cmd_a",
        "cmd_b": "test_device1:cmd_b",
    }
    assert other_device.outputs is None
    assert other_device.error == (
        "Sequence 'device_local_report' not found for device 'test_device2'"
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


def test_run_uses_supplied_sequence_manager(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_device_session(DummyDeviceSession)
    manager = SequenceManager(sample_config)

    def fail_init(_self: SequenceManager, _config: NetworkConfig) -> None:
        msg = "run_commands built a new sequence manager"
        raise AssertionError(msg)

    monkeypatch.setattr(SequenceManager, "__init__", fail_init)

    result = run_commands(
        RunOptions(
            target="test_device1",
            command_or_sequence="/system/clock/print",
            config=sample_config,
            sequence_manager=manager,
        )
    )

    assert result.command_results[0].output == "test_device1:/system/clock/print"


def test_run_builds_sequence_manager_for_other_config(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_device_session(DummyDeviceSession)
    stale = SequenceManager(sample_config.model_copy())
    built: list[NetworkConfig] = []
    original_init = SequenceManager.__init__

    def record_init(self: SequenceManager, config: NetworkConfig) -> None:
        built.append(config)
        original_init(self, config)

    monkeypatch.setattr(SequenceManager, "__init__", record_init)

    run_commands(
        RunOptions(
            target="test_device1",
            command_or_sequence="/system/clock/print",
            config=sample_config,
            sequence_manager=stale,
        )
    )

    assert len(built) == 1
    assert built[0] is sample_config


def test_connection_failure_reason_reaches_result(
    sample_config: NetworkConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    from scrapli.exceptions import ScrapliException

    driver = MagicMock()
    driver.ptr = None
    driver.open.side_effect = ScrapliException("Permission denied (password)")
    monkeypatch.setattr(
        "network_toolkit.transport.scrapli_sync.Cli", MagicMock(return_value=driver)
    )
    monkeypatch.setattr("network_toolkit.device.time.sleep", lambda _s: None)

    result = run_commands(
        RunOptions(
            target="test_device1",
            command_or_sequence="/system/clock/print",
            config=sample_config,
        )
    )

    assert result.command_results[0].error == (
        "Authentication failed for test_device1: Permission denied (password)"
    )


class SlowConnectSession(DummyDeviceSession):
    """Dummy session whose connect can be held open by a test."""

    created: ClassVar[list[str]] = []
    release: ClassVar[dict[str, threading.Event]] = {}

    def __init__(self, device_name: str, *args: Any) -> None:
        super().__init__(device_name, *args)
        self.stale = False
        SlowConnectSession.created.append(device_name)

    def connect(self) -> None:
        if self.stale:
            msg = "Connection failed for stale session"
            raise DeviceConnectionError(msg)
        gate = SlowConnectSession.release.get(self.device_name)
        if gate is not None:
            assert gate.wait(5)

    def disconnect(self) -> None:
        return None


def _run_pooled(config: NetworkConfig, pool: SessionPool, device: str) -> RunResult:
    return run_commands(
        RunOptions(
            target=device,
            command_or_sequence="/system/clock/print",
            config=config,
            session_pool=pool,
        )
    )


def test_concurrent_runs_replace_stale_session_once(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(SlowConnectSession)
    stale = SlowConnectSession("test_device1", sample_config)
    stale.stale = True
    SlowConnectSession.created = []
    gate = threading.Event()
    SlowConnectSession.release = {"test_device1": gate}
    pool = SessionPool()
    pool["test_device1"] = stale  # type: ignore[assignment]

    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_run_pooled, sample_config, pool, "test_device1")
            for _ in range(4)
        ]
        # Give every thread time to reach session setup while connect is held.
        deadline = time.monotonic() + 0.5
        while len(SlowConnectSession.created) < 2 and time.monotonic() < deadline:
            time.sleep(0.01)
        gate.set()
        results = [f.result(timeout=5) for f in futures]

    # One replacement session; without the device lock each thread opens its own.
    assert SlowConnectSession.created == ["test_device1"]
    assert all(not r.command_results[0].error for r in results)
    assert pool.get("test_device1") is not stale


class RefusedConnectSession(DummyDeviceSession):
    """Dummy session whose connect always fails."""

    connects = 0

    def connect(self) -> None:
        RefusedConnectSession.connects += 1
        msg = "Connection failed for test_device1: timed out"
        raise DeviceConnectionError(msg)

    def disconnect(self) -> None:
        return None


def test_new_session_that_fails_to_connect_is_not_retried(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(RefusedConnectSession)
    RefusedConnectSession.connects = 0
    pool = SessionPool()

    result = _run_pooled(sample_config, pool, "test_device1")

    assert result.command_results[0].error == (
        "Connection failed for test_device1: timed out"
    )
    assert RefusedConnectSession.connects == 1
    assert pool.get("test_device1") is None


def test_rejected_command_reply_reaches_result(
    sample_config: NetworkConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = MagicMock()
    transport.send_command.return_value = MagicMock(
        result="bad command name bogus (line 1 column 12)", failed=True
    )
    factory = MagicMock()
    factory.create_transport.return_value = transport
    monkeypatch.setattr(
        "network_toolkit.device.get_transport_factory", lambda _name: factory
    )

    result = _run_pooled(sample_config, SessionPool(), "test_device1")

    assert result.command_results[0].error == (
        "Command failed on test_device1: /system/clock/print: "
        "bad command name bogus (line 1 column 12)"
    )


def test_connecting_device_does_not_block_other_devices(
    sample_config: NetworkConfig,
    patch_device_session: Callable[[DummyDeviceSession], None],
) -> None:
    patch_device_session(SlowConnectSession)
    SlowConnectSession.created = []
    gate = threading.Event()
    SlowConnectSession.release = {"test_device1": gate}
    pool = SessionPool()

    with ThreadPoolExecutor(max_workers=2) as executor:
        blocked = executor.submit(_run_pooled, sample_config, pool, "test_device1")
        other = executor.submit(_run_pooled, sample_config, pool, "test_device2")
        try:
            result = other.result(timeout=5)
            assert not blocked.done()
        finally:
            gate.set()
        blocked.result(timeout=5)

    assert result.command_results[0].output == "test_device2:/system/clock/print"
