# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the sequence module."""

from __future__ import annotations

import typer

from network_toolkit.commands import sequence


class TestSequence:
    """Test sequence module functionality."""

    def test_register_no_op(self) -> None:
        """Test that register is a no-op and doesn't crash."""
        app = typer.Typer()

        # Should not raise any exceptions
        sequence.register(app)

        # App should remain unchanged (no commands added)
        assert len(app.registered_commands) == 0
