"""
Professional output testing utilities.

This module provides a cleaner, more maintainable approach to testing CLI output
that handles terminal coloring properly without brittle string matching.
"""

import os
import re
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any
from unittest.mock import patch

import pytest
from rich.console import Console
from typer.testing import CliRunner

from src.network_toolkit.output_clean import OutputMode


@contextmanager
def output_mode(mode: OutputMode) -> Generator[None, None, None]:
    """Context manager to force a specific output mode for testing.

    Args:
        mode: The OutputMode to use during the test

    Example:
        with output_mode(OutputMode.NO_COLOR):
            result = runner.invoke(app, ["run", "device1", "show version"])
            assert "Error:" in result.stdout  # No ANSI codes
    """
    env_vars = {}

    if mode == OutputMode.NO_COLOR:
        env_vars.update({"NO_COLOR": "1", "CI": "true", "TERM": "dumb"})
    elif mode == OutputMode.RICH:
        env_vars.update({"NO_COLOR": "", "CI": "", "TERM": "xterm-256color"})

    with patch.dict(os.environ, env_vars, clear=False):
        yield


@contextmanager
def test_console(
    *, force_terminal: bool = False, width: int = 80
) -> Generator[Console, None, None]:
    """Create a test console with predictable behavior.

    Args:
        force_terminal: Whether to force terminal mode
        width: Console width

    Yields:
        A Console instance configured for testing
    """
    console = Console(
        force_terminal=force_terminal,
        width=width,
        height=24,
        legacy_windows=False,
        color_system="truecolor" if force_terminal else None,
        _environ={},
    )
    yield console


class OutputTester:
    """Professional output testing utility.

    Provides methods to test CLI output in different modes without brittle assertions.
    """

    def __init__(self):
        self.runner = CliRunner()

    def run_with_mode(self, app: Any, args: list[str], mode: OutputMode) -> Any:
        """Run CLI command with specific output mode.

        Args:
            app: The Typer app to test
            args: Command line arguments
            mode: Output mode to use

        Returns:
            Click test result
        """
        with output_mode(mode):
            return self.runner.invoke(app, args)

    def assert_clean_output(self, result: Any, expected_content: str) -> None:
        """Assert output contains expected content without ANSI codes.

        Args:
            result: Click test result
            expected_content: Expected content (without ANSI codes)
        """
        # Strip ANSI codes for comparison
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        clean_output = ansi_escape.sub("", result.stdout)

        assert expected_content in clean_output

    def assert_has_color(self, result: Any) -> None:
        """Assert that output contains ANSI color codes.

        Args:
            result: Click test result
        """
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        has_ansi = bool(ansi_escape.search(result.stdout))
        assert has_ansi, "Expected colored output but found none"

    def assert_no_color(self, result: Any) -> None:
        """Assert that output contains no ANSI color codes.

        Args:
            result: Click test result
        """
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        has_ansi = bool(ansi_escape.search(result.stdout))
        assert not has_ansi, f"Found unexpected ANSI codes in output: {result.stdout!r}"


# Test decorators for common scenarios
def with_no_color(test_func):
    """Decorator to run test with NO_COLOR mode."""

    def wrapper(*args, **kwargs):
        with output_mode(OutputMode.NO_COLOR):
            return test_func(*args, **kwargs)

    return wrapper


def with_rich_output(test_func):
    """Decorator to run test with RICH mode."""

    def wrapper(*args, **kwargs):
        with output_mode(OutputMode.RICH):
            return test_func(*args, **kwargs)

    return wrapper


# Pytest fixtures
@pytest.fixture
def output_tester():
    """Pytest fixture providing OutputTester instance."""
    return OutputTester()


@pytest.fixture
def no_color_env():
    """Pytest fixture that sets NO_COLOR environment."""
    with output_mode(OutputMode.NO_COLOR):
        yield


@pytest.fixture
def rich_env():
    """Pytest fixture that sets RICH environment."""
    with output_mode(OutputMode.RICH):
        yield
