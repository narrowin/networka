"""Unified config commands for the network toolkit CLI."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.exceptions import NetworkToolkitError


def register(app: typer.Typer) -> None:
    """Register the unified config command group with the main CLI app."""
    config_app = typer.Typer(
        name="config",
        help="Configuration management commands",
        no_args_is_help=True,
    )

    @config_app.command("init")
    def init(
        target_dir: Annotated[
            Path | None,
            typer.Argument(
                help=(
                    "Directory to initialize (default: system config location for your OS)"
                ),
            ),
        ] = None,
        force: Annotated[
            bool, typer.Option("--force", "-f", help="Overwrite existing files")
        ] = False,
        yes: Annotated[
            bool, typer.Option("--yes", "-y", help="Non-interactive: accept defaults")
        ] = False,
        dry_run: Annotated[
            bool, typer.Option("--dry-run", help="Show actions without writing changes")
        ] = False,
        install_sequences: Annotated[
            bool | None,
            typer.Option(
                "--install-sequences/--no-install-sequences",
                help="Install additional predefined vendor sequences from GitHub",
            ),
        ] = None,
        git_url: Annotated[
            str | None,
            typer.Option(
                "--git-url",
                help="Git URL for sequences when using --sequences-source git",
            ),
        ] = None,
        git_ref: Annotated[
            str,
            typer.Option(
                "--git-ref", help="Git branch/tag/ref for sequences", show_default=True
            ),
        ] = "main",
        install_completions: Annotated[
            bool | None,
            typer.Option(
                "--install-completions/--no-install-completions",
                help="Install shell completion scripts",
            ),
        ] = None,
        shell: Annotated[
            str | None,
            typer.Option("--shell", help="Shell for completions (bash or zsh)"),
        ] = None,
        activate_completions: Annotated[
            bool | None,
            typer.Option(
                "--activate-completions/--no-activate-completions",
                help="Activate completions by updating shell rc file",
            ),
        ] = None,
        install_schemas: Annotated[
            bool | None,
            typer.Option(
                "--install-schemas/--no-install-schemas",
                help="Install JSON schemas for YAML editor validation and auto-completion",
            ),
        ] = None,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable verbose logging")
        ] = False,
    ) -> None:
        """Initialize a network toolkit configuration in OS-appropriate location.

        Creates a complete starter configuration with:
        - .env file with credential templates
        - config.yml with core settings
        - devices/ with MikroTik and Cisco examples
        - groups/ with tag-based and explicit groups
        - sequences/ with global and vendor-specific sequences
        - JSON schemas for YAML editor validation (optional)
        - Shell completions (optional)
        - Additional predefined sequences from GitHub (optional)

        Default locations by OS:
        - Linux: ~/.config/networka/
        - macOS: ~/Library/Application Support/networka/
        - Windows: %APPDATA%/networka/

        The 'nw' command will automatically find configurations in these locations.
        """
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            from network_toolkit.commands.config_init import _config_init_impl

            _config_init_impl(
                target_dir=target_dir,
                force=force,
                yes=yes,
                dry_run=dry_run,
                install_sequences=install_sequences,
                git_url=git_url,
                git_ref=git_ref,
                install_completions=install_completions,
                shell=shell,
                activate_completions=activate_completions,
                install_schemas=install_schemas,
                verbose=verbose,
            )

        except NetworkToolkitError as e:
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    @config_app.command("validate")
    def validate(
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Configuration file path")
        ] = DEFAULT_CONFIG_PATH,
        output_mode: Annotated[
            OutputMode | None,
            typer.Option(
                "--output-mode",
                "-o",
                help="Output decoration mode: default, light, dark, no-color, raw",
                show_default=False,
            ),
        ] = None,
        verbose: Annotated[
            bool,
            typer.Option(
                "--verbose", "-v", help="Show detailed validation information"
            ),
        ] = False,
    ) -> None:
        """Validate the configuration file and show any issues."""
        setup_logging("DEBUG" if verbose else "INFO")

        try:
            from network_toolkit.commands.config_validate import _config_validate_impl

            _config_validate_impl(
                config_file=config_file,
                output_mode=output_mode,
                verbose=verbose,
            )

        except NetworkToolkitError as e:
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(str(e))
            if verbose and hasattr(e, "details") and e.details:
                ctx.print_error(f"Details: {e.details}")
            raise typer.Exit(1) from None
        except Exception as e:  # pragma: no cover - unexpected
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    app.add_typer(config_app, name="config")
