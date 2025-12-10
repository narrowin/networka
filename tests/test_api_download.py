"""Tests for the library-first download API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from network_toolkit.api.download import DownloadOptions, download_file
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

    def connect(self) -> None:
        pass

    def download_file(
        self,
        remote_file: str,
        local_path: Path,
        *,
        verify: bool = True,
        delete_remote: bool = False
    ) -> bool:
        # Simulate file creation
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_text("dummy content")
        return True


@pytest.fixture
def patch_device_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("network_toolkit.api.download.DeviceSession", DummyDeviceSession)


def test_download_single_device(
    sample_config: NetworkConfig,
    patch_device_session: None,
    tmp_path: Path,
) -> None:
    local_file = tmp_path / "downloaded.txt"

    options = DownloadOptions(
        target="test_device1",
        remote_file="remote.txt",
        local_path=local_file,
        config=sample_config,
    )

    result = download_file(options)

    assert result.totals.succeeded == 1
    assert result.device_results[0].success
    assert result.device_results[0].device == "test_device1"
    assert result.device_results[0].local_path == local_file
    assert local_file.exists()
    assert local_file.read_text() == "dummy content"


def test_download_group(
    sample_config: NetworkConfig,
    patch_device_session: None,
    tmp_path: Path,
) -> None:
    # Target multiple devices by comma list
    options = DownloadOptions(
        target="test_device1,test_device2",
        remote_file="remote.txt",
        local_path=tmp_path,
        config=sample_config,
    )

    result = download_file(options)

    assert result.is_group
    assert result.totals.succeeded == 2

    # Check files
    dev1_file = tmp_path / "test_device1" / "remote.txt"
    dev2_file = tmp_path / "test_device2" / "remote.txt"

    assert dev1_file.exists()
    assert dev2_file.exists()
