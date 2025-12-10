"""Tests for the library-first backup API."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from network_toolkit.api.backup import BackupOptions, run_backup
from network_toolkit.config import NetworkConfig


class DummyDeviceSession:
    """In-memory DeviceSession replacement for tests."""

    def __init__(self, device_name: str, config: NetworkConfig) -> None:
        self.device_name = device_name
        self.config = config

    def __enter__(self) -> DummyDeviceSession:
        return self

    def __exit__(self, *_args: Any) -> None:
        return None

    def download_file(
        self, remote_filename: str, local_path: Path, delete_remote: bool
    ) -> bool:
        return True


@pytest.fixture
def mock_platform_ops(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    mock_ops = MagicMock()
    mock_ops.get_platform_name.return_value = "dummy_platform"

    # Default successful result
    result = MagicMock()
    result.success = True
    result.text_outputs = {"config.rsc": "dummy config"}
    result.files_to_download = [
        {"source": "backup.backup", "destination": "backup.backup"}
    ]
    result.errors = []

    mock_ops.create_backup.return_value = result

    def _get_ops(session: Any) -> MagicMock:
        return mock_ops

    monkeypatch.setattr("network_toolkit.api.backup.get_platform_operations", _get_ops)
    return mock_ops


@pytest.fixture
def patch_device_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("network_toolkit.api.backup.DeviceSession", DummyDeviceSession)


def test_run_backup_single_device(
    sample_config: NetworkConfig,
    patch_device_session: None,
    mock_platform_ops: MagicMock,
    tmp_path: Path,
) -> None:
    # Setup config backup dir to tmp_path
    sample_config.general.backup_dir = str(tmp_path)

    options = BackupOptions(
        target="test_device1",
        config=sample_config,
        download=True,
    )

    result = run_backup(options)

    assert result.totals.succeeded == 1
    assert result.device_results[0].success
    assert result.device_results[0].platform == "dummy_platform"
    assert "config.rsc" in result.device_results[0].text_outputs
    assert "backup.backup" in result.device_results[0].downloaded_files

    # Verify files were written
    backup_dir = result.device_results[0].backup_dir
    assert backup_dir is not None
    assert (backup_dir / "config.rsc").exists()
    assert (backup_dir / "manifest.json").exists()


def test_run_backup_failure(
    sample_config: NetworkConfig,
    patch_device_session: None,
    mock_platform_ops: MagicMock,
    tmp_path: Path,
) -> None:
    # Setup failure
    fail_result = MagicMock()
    fail_result.success = False
    fail_result.errors = ["Backup failed"]
    fail_result.text_outputs = {}
    fail_result.files_to_download = []

    mock_platform_ops.create_backup.return_value = fail_result

    sample_config.general.backup_dir = str(tmp_path)

    options = BackupOptions(
        target="test_device1",
        config=sample_config,
    )

    result = run_backup(options)

    assert result.totals.failed == 1
    assert not result.device_results[0].success
    assert "Backup failed" in str(result.device_results[0].error)
