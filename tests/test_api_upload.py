"""Tests for the library-first upload API."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from network_toolkit.api.upload import UploadOptions, upload_file
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

    def upload_file(
        self,
        local_path: Path,
        remote_filename: str | None = None,
        *,
        verify_upload: bool = True,
        verify_checksum: bool = False
    ) -> bool:
        return True


@pytest.fixture
def patch_device_session(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("network_toolkit.api.upload.DeviceSession", DummyDeviceSession)


def test_upload_single_device(
    sample_config: NetworkConfig,
    patch_device_session: None,
    tmp_path: Path,
) -> None:
    local_file = tmp_path / "upload.txt"
    local_file.write_text("content")

    options = UploadOptions(
        target="test_device1",
        local_file=local_file,
        config=sample_config,
    )

    result = upload_file(options)

    assert result.totals.succeeded == 1
    assert result.device_results[0].success
    assert result.device_results[0].device == "test_device1"
    assert result.device_results[0].remote_path == "upload.txt"


def test_upload_group(
    sample_config: NetworkConfig,
    patch_device_session: None,
    tmp_path: Path,
) -> None:
    local_file = tmp_path / "upload.txt"
    local_file.write_text("content")

    options = UploadOptions(
        target="test_device1,test_device2",
        local_file=local_file,
        config=sample_config,
    )

    result = upload_file(options)

    assert result.is_group
    assert result.totals.succeeded == 2
    assert len(result.device_results) == 2
