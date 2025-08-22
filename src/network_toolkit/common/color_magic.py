# SPDX-License-Identifier: MIT
"""Magical command decorator for automatic color system integration."""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.output import OutputMode
from network_toolkit.exceptions import NetworkToolkitError

F = TypeVar("F", bound=Callable[..., Any])


def with_color_support(func: F) -> F:
    """Magical decorator that adds --output-mode support to any command.

    This decorator:
    1. Automatically adds --output-mode parameter if missing
    2. Injects 'ctx' (CommandContext) into the function
    3. Handles all error styling consistently
    4. Zero code changes needed in existing commands!

    Usage:
        @with_color_support
        def my_command(target: str, ctx: CommandContext, ...):
            ctx.print_info("Starting operation...")
            # Use ctx.console for Rich output
            # Use ctx.print_error(), ctx.print_success(), etc.
    """
    sig = inspect.signature(func)

    # Check if function already has output_mode parameter
    has_output_mode = any(
        param.annotation and "OutputMode" in str(param.annotation)
        for param in sig.parameters.values()
    )

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Extract standard parameters
        output_mode = kwargs.pop("output_mode", None)
        verbose = kwargs.get("verbose", False)
        config_file = kwargs.get("config_file", DEFAULT_CONFIG_PATH)

        # Create command context
        ctx = CommandContext(
            output_mode=output_mode,
            verbose=verbose,
            config_file=config_file,
        )

        # Inject context into function call
        kwargs["ctx"] = ctx

        try:
            return func(*args, **kwargs)
        except typer.Exit:
            # Re-raise typer.Exit without modification
            raise
        except NetworkToolkitError as e:
            ctx.print_error(f"Error: {e.message}")
            if verbose and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    # Dynamically add output_mode parameter if missing
    if not has_output_mode:
        wrapper = add_output_mode_parameter(wrapper)

    return wrapper


def add_output_mode_parameter(func: Callable) -> Callable:
    """Dynamically add --output-mode parameter to a function."""
    # Get existing signature
    sig = inspect.signature(func)

    # Create new parameter
    output_mode_param = inspect.Parameter(
        "output_mode",
        inspect.Parameter.KEYWORD_ONLY,
        default=None,
        annotation=Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ],
    )

    # Insert before last parameter (usually verbose)
    params = list(sig.parameters.values())
    if params and params[-1].name == "verbose":
        # Insert before verbose
        params.insert(-1, output_mode_param)
    else:
        # Append at end
        params.append(output_mode_param)

    # Create new signature
    new_sig = sig.replace(parameters=params)
    func.__signature__ = new_sig

    return func


def styled_print(ctx: CommandContext, message: str, style: str = "info") -> None:
    """Helper for styled printing based on context mode."""
    if style == "error":
        ctx.print_error(message)
    elif style == "warning":
        ctx.print_warning(message)
    elif style == "success":
        ctx.print_success(message)
    else:
        ctx.print_info(message)


# Legacy console replacement for gradual migration
class LegacyConsoleWrapper:
    """Wrapper to gradually replace console.print() calls."""

    def __init__(self, ctx: CommandContext):
        self.ctx = ctx
        self._console = ctx.console

    def print(self, *args, **kwargs):
        """Smart print that detects and converts hardcoded colors."""
        if args:
            text = str(args[0])
            # Convert common hardcoded patterns
            if "[red]" in text and "[/red]" in text:
                # Extract error message
                import re

                match = re.search(r"\[red\](.*?)\[/red\]", text)
                if match:
                    self.ctx.print_error(match.group(1))
                    return
            elif "[yellow]" in text and "[/yellow]" in text:
                # Extract warning message
                import re

                match = re.search(r"\[yellow\](.*?)\[/yellow\]", text)
                if match:
                    self.ctx.print_warning(match.group(1))
                    return
            elif "[green]" in text and "[/green]" in text:
                # Extract success message
                import re

                match = re.search(r"\[green\](.*?)\[/green\]", text)
                if match:
                    self.ctx.print_success(match.group(1))
                    return

        # Fall back to regular console
        self._console.print(*args, **kwargs)


def get_legacy_console(ctx: CommandContext) -> LegacyConsoleWrapper:
    """Get a console wrapper that automatically converts hardcoded colors."""
    return LegacyConsoleWrapper(ctx)
