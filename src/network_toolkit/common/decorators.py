"""
Decorators for common CLI command patterns.

This module provides decorators that standardize common patterns across CLI commands,
particularly configuration loading and error handling.
"""

import functools
from collections.abc import Callable
from pathlib import Path
from typing import ParamSpec, TypeVar

from network_toolkit.common.config_context import ConfigContext
from network_toolkit.exceptions import NetworkToolkitError

P = ParamSpec("P")
R = TypeVar("R")


def with_config(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that automatically provides ConfigContext to CLI commands.

    This decorator:
    1. Creates a ConfigContext from the config_file parameter
    2. Injects it via kwargs as 'config_ctx'
    3. Handles configuration loading errors gracefully

    The decorated function signature should be:
    def command(device: str, ..., config_file: Path = Path("config"), **kwargs) -> None:
        config_ctx = kwargs.get("config_ctx")
        # ... rest of command implementation

    Args:
        func: The CLI command function to decorate

    Returns:
        Decorated function with ConfigContext injection

    Example:
        @with_config
        def info_command(targets: str, config_file: Path = Path("config"), **kwargs) -> None:
            config_ctx = kwargs.get("config_ctx")
            config = config_ctx.config
            # ... rest of command implementation
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        # Extract config_file from kwargs, defaulting to "config"
        config_file = kwargs.get("config_file", Path("config"))
        if isinstance(config_file, str):
            config_file = Path(config_file)
        elif not isinstance(config_file, Path):
            config_file = Path("config")  # Fallback to default

        # Create ConfigContext with intelligent path resolution
        try:
            config_ctx = ConfigContext.from_path(config_file)
        except NetworkToolkitError as e:
            # Re-raise configuration errors for CLI to handle
            raise e
        except Exception as e:
            # Wrap unexpected errors in our exception hierarchy
            from network_toolkit.exceptions import ConfigurationError

            error_msg = f"Failed to load configuration: {e}"
            raise ConfigurationError(error_msg) from e

        # Inject ConfigContext via kwargs
        kwargs["config_ctx"] = config_ctx
        return func(*args, **kwargs)

    return wrapper


def handle_command_errors(func: Callable[P, R]) -> Callable[P, R]:
    """
    Decorator that provides standard error handling for CLI commands.

    This decorator catches NetworkToolkitError exceptions and ensures they
    are properly handled by the CLI framework (typer) without logging them
    as "unexpected" errors.

    Args:
        func: The CLI command function to decorate

    Returns:
        Decorated function with error handling
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return func(*args, **kwargs)
        except NetworkToolkitError:
            # Framework exceptions (typer.Exit) should pass through
            # NetworkToolkitError should be handled by CLI layer
            raise
        except Exception as e:
            # Wrap unexpected errors
            error_msg = f"Unexpected error: {e}"
            raise NetworkToolkitError(error_msg) from e

    return wrapper


def with_config_and_error_handling(func: Callable[P, R]) -> Callable[P, R]:
    """
    Composite decorator that combines config injection and error handling.

    This is equivalent to:
    @handle_command_errors
    @with_config
    def command(...): ...

    Args:
        func: The CLI command function to decorate

    Returns:
        Decorated function with both config injection and error handling
    """
    return handle_command_errors(with_config(func))
