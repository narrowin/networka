# SPDX-License-Identifier: MIT
"""Base utilities for standardized command implementation."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import get_output_manager, set_output_mode
from network_toolkit.common.styles import StyleManager
from network_toolkit.exceptions import NetworkToolkitError

F = TypeVar("F", bound=Callable[..., Any])


def standardized_command(
    *,
    has_config: bool = True,
    has_verbose: bool = True,
    has_output_mode: bool = True,
) -> Callable[[F], F]:
    """Decorator to add standard parameters and error handling to commands.

    This decorator ensures all commands have consistent:
    - --output-mode parameter
    - --verbose parameter
    - --config parameter
    - Proper styled error handling
    - StyleManager setup

    Args:
        has_config: Whether to add --config parameter
        has_verbose: Whether to add --verbose parameter
        has_output_mode: Whether to add --output-mode parameter
    """

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract standard parameters from kwargs if they exist
            output_mode = kwargs.pop("output_mode", None)
            verbose = kwargs.pop("verbose", False)
            config_file = kwargs.pop("config_file", DEFAULT_CONFIG_PATH)

            # Set up output mode
            if output_mode is not None:
                set_output_mode(output_mode)
                output_manager = get_output_manager()
            else:
                # Use default output mode
                output_manager = get_output_manager()

            # Set up logging
            if verbose:
                setup_logging("DEBUG")
            else:
                setup_logging("WARNING")

            # Create style manager for themed output
            style_manager = StyleManager(output_manager.mode)

            # Add these to kwargs for the function
            kwargs["style_manager"] = style_manager
            kwargs["output_manager"] = output_manager
            if has_config:
                kwargs["config_file"] = config_file
            if has_verbose:
                kwargs["verbose"] = verbose

            try:
                return func(*args, **kwargs)
            except NetworkToolkitError as e:
                output_manager.print_error(f"Error: {e.message}")
                if verbose and e.details:
                    output_manager.print_error(f"Details: {e.details}")
                raise typer.Exit(1) from None
            except Exception as e:  # pragma: no cover - unexpected
                output_manager.print_error(f"Unexpected error: {e}")
                raise typer.Exit(1) from None

        return cast(F, wrapper)

    return decorator


def add_standard_options(
    *,
    has_config: bool = True,
    has_verbose: bool = True,
    has_output_mode: bool = True,
) -> Callable[[F], F]:
    """Add standard CLI options to a command function.

    This should be applied BEFORE the @app.command() decorator.
    """

    def decorator(func: F) -> F:
        # Add parameters in reverse order (typer processes them backwards)

        if has_verbose:
            func = typer.Option(
                False, "--verbose", "-v", help="Enable verbose logging"
            )(func)

        if has_output_mode:
            func = typer.Option(
                None,
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            )(func)

        if has_config:
            func = typer.Option(
                DEFAULT_CONFIG_PATH, "--config", "-c", help="Configuration file path"
            )(func)

        return func

    return decorator


class StandardizedCommandError(NetworkToolkitError):
    """Error in standardized command execution."""

    pass
