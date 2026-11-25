"""Tests for banner functionality."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from network_toolkit.banner import BANNER_PLAIN, show_banner
from network_toolkit.common.output import OutputManager, OutputMode


def test_banner_content() -> None:
    """The banner contains the Networka block art."""
    assert "█" in BANNER_PLAIN
    assert len(BANNER_PLAIN.strip()) > 100


def test_show_banner(capsys: pytest.CaptureFixture[str]) -> None:
    """The banner shows the block art and next commands in plain output."""
    with patch("network_toolkit.banner.CommandContext") as context:
        context.return_value.output_manager = OutputManager(OutputMode.NO_COLOR)
        show_banner()

    output = capsys.readouterr().out
    assert "█" in output
    assert "Welcome to Networka" in output
    assert "nw --help" in output
    assert "nw config init" in output
    assert "\x1b[" not in output
