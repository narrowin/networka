# SPDX-License-Identifier: MIT
"""Base utilities for standardized command implementation."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar, cast

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import OutputMode
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
    - Standard CLI parameters (--config, --verbose, --output-mode)
    - Automatic CommandContext creation
    - Proper styled error handling
    - Context injection into command function

    Args:
        has_config: Whether to add --config parameter
        has_verbose: Whether to add --verbose parameter
        has_output_mode: Whether to add --output-mode parameter
    """

    def decorator(func: F) -> F:
        def wrapper(
            config_file: Annotated[
                Path, typer.Option("--config", "-c", help="Configuration file path")
            ] = DEFAULT_CONFIG_PATH,
            verbose: Annotated[
                bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
            ] = False,
            output_mode: Annotated[
                OutputMode | None,
                typer.Option(
                    "--output-mode",
                    "-o",
                    help="Output decoration mode: default, light, dark, no-color, raw",
                    show_default=False,
                ),
            ] = None,
        ) -> Any:
            # Create CommandContext with automatic setup
            ctx = CommandContext(
                config_file=config_file,
                verbose=verbose,
                output_mode=output_mode,
            )

            try:
                # Call the original function with context
                return func(ctx)
            except NetworkToolkitError as e:
                ctx.print_error(f"Error: {e.message}")
                if verbose and e.details:
                    ctx.print_error(f"Details: {e.details}")
                raise typer.Exit(1) from None
            except typer.Exit:
                # Allow clean exits (e.g., user cancellation) to pass through
                raise
            except Exception as e:  # pragma: no cover - unexpected
                ctx.print_error(f"Unexpected error: {e}")
                raise typer.Exit(1) from None

        # Copy over function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        wrapper.__module__ = func.__module__
        wrapper.__qualname__ = getattr(func, "__qualname__", func.__name__)
        wrapper.__annotations__ = {
            "config_file": Annotated[
                Path, typer.Option("--config", "-c", help="Configuration file path")
            ],
            "verbose": Annotated[
                bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
            ],
            "output_mode": Annotated[
                OutputMode | None,
                typer.Option(
                    "--output-mode",
                    "-o",
                    help="Output decoration mode: default, light, dark, no-color, raw",
                    show_default=False,
                ),
            ],
            "return": None,
        }

        return cast(F, wrapper)

    return decorator
