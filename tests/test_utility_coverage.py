# SPDX-License-Identifier: MIT
"""Configuration and device session boundary cases."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from scrapli.exceptions import ScrapliException

from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import DeviceConnectionError


def test_device_session_context_manager_error(sample_config: NetworkConfig) -> None:
    """Each partially opened transport is closed before the next retry."""
    sample_config.general.retry_delay = 0
    with patch("network_toolkit.transport.scrapli_sync.Cli") as mock_scrapli:
        mock_scrapli.return_value.open.side_effect = ScrapliException(
            "Connection failed"
        )
        with pytest.raises(
            DeviceConnectionError, match="Connection failed for test_device1"
        ):
            with DeviceSession("test_device1", sample_config):
                pytest.fail("Connection failure entered the caller's block")
        assert mock_scrapli.return_value.open.call_count == 3
        assert mock_scrapli.return_value.close.call_count == 3
        mock_scrapli.return_value.close.assert_called_with(force=True)


def test_load_config_with_no_devices(tmp_path: Path) -> None:
    """An explicit empty inventory is available as an empty device mapping."""
    config_path = tmp_path / "config.yml"
    config_path.write_text("general:\n  timeout: 30\ndevices: {}\n", encoding="utf-8")

    config = load_config(config_path)

    assert config.general.timeout == 30
    assert config.devices == {}
