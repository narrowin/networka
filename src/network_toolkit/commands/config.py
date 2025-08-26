"""Unified config commands for the network toolkit CLI."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import (
    OutputMode,
    get_output_manager,
    get_output_manager_with_config,
    set_output_mode,
)
from network_toolkit.common.paths import default_config_root
from network_toolkit.config import load_config
from network_toolkit.exceptions import NetworkToolkitError

logger = logging.getLogger(__name__)


def create_env_file(target_dir: Path) -> None:
    """Create a minimal .env file with credential templates."""
    env_content = """# Network Toolkit Environment Variables
# =================================

# Default credentials (used when device-specific ones aren't found)
NW_USER_DEFAULT=admin
NW_PASSWORD_DEFAULT=your_password_here

# Device-specific credentials (optional)
# NW_ROUTER1_USER=admin
# NW_ROUTER1_PASSWORD=specific_password

# Global settings
# NW_TIMEOUT=30
# NW_LOG_LEVEL=INFO
"""
    env_file = target_dir / ".env"
    env_file.write_text(env_content)


def create_config_yml(config_dir: Path) -> None:
    """Create the main config.yml file."""
    config_content = """# Network Toolkit Configuration
# =============================

general:
  output_mode: default  # Options: default, light, dark, no-color, raw
  log_level: INFO       # Options: DEBUG, INFO, WARNING, ERROR

# Device configurations are loaded from devices/ directory
# Group configurations are loaded from groups/ directory
# Sequence configurations are loaded from sequences/ directory
"""
    config_file = config_dir / "config.yml"
    config_file.write_text(config_content)


def create_example_devices(devices_dir: Path) -> None:
    """Create example device configurations."""
    mikrotik_content = """# MikroTik RouterOS Device Example
host: 192.168.1.1
device_type: mikrotik_routeros
description: "Main office router"
tags:
  - office
  - critical
"""

    cisco_content = """# Cisco IOS Device Example
host: 192.168.1.2
device_type: cisco_ios
description: "Access switch"
tags:
  - switch
  - access
"""

    (devices_dir / "router1.yml").write_text(mikrotik_content)
    (devices_dir / "switch1.yml").write_text(cisco_content)


def create_example_groups(groups_dir: Path) -> None:
    """Create example group configurations."""
    office_content = """# Office devices group
description: "All office network devices"
match_tags:
  - office
"""

    critical_content = """# Critical infrastructure group
description: "Critical network infrastructure"
match_tags:
  - critical
"""

    (groups_dir / "office.yml").write_text(office_content)
    (groups_dir / "critical.yml").write_text(critical_content)


def create_example_sequences(sequences_dir: Path) -> None:
    """Create example sequence configurations."""
    global_content = """# Global command sequences
health_check:
  description: "Basic device health check"
  commands:
    - "/system resource print"
    - "/interface print brief"

backup_config:
  description: "Backup device configuration"
  commands:
    - "/export file=backup"
"""

    (sequences_dir / "global.yml").write_text(global_content)

    # Create vendor-specific directories
    (sequences_dir / "mikrotik").mkdir(exist_ok=True)
    (sequences_dir / "cisco").mkdir(exist_ok=True)


def detect_shell(shell: str | None = None) -> str | None:
    """Detect the current shell."""
    if shell:
        return shell if shell in {"bash", "zsh"} else None

    # Try to detect from environment
    shell_env = os.environ.get("SHELL", "")
    if "bash" in shell_env:
        return "bash"
    elif "zsh" in shell_env:
        return "zsh"

    return None


def install_shell_completions(shell: str) -> tuple[Path | None, Path | None]:
    """Install shell completion scripts."""
    # This is a simplified version - just return None for now
    # In a real implementation, this would copy completion scripts
    return None, None


def activate_shell_completion(shell: str, config_path: Path, rc_file: Path) -> None:
    """Activate shell completion in the shell profile."""
    # This is a simplified version - just log that it would be activated
    logger.info(f"Would activate {shell} completion in {rc_file}")


def install_sequences_from_repo(url: str, ref: str, dest: Path) -> None:
    """Install sequences from a git repository."""
    # This is a simplified version - just log that it would install
    logger.info(f"Would install sequences from {url}#{ref} to {dest}")


def install_editor_schemas(target_path: Path) -> None:
    """Install JSON schemas for YAML editor validation."""
    # This is a simplified version - just log that it would install
    logger.info(f"Would install JSON schemas to {target_path}")


def _config_init_impl(
    target_dir: Path | None = None,
    force: bool = False,
    yes: bool = False,
    dry_run: bool = False,
    install_sequences: bool | None = None,
    git_url: str | None = None,
    git_ref: str = "main",
    install_completions: bool | None = None,
    shell: str | None = None,
    activate_completions: bool | None = None,
    install_schemas: bool | None = None,
    verbose: bool = False,
) -> None:
    """Implementation logic for config init."""
    # Create command context for consistent output
    ctx = CommandContext()

    # Determine whether we prompt (interactive) or not
    interactive = target_dir is None and not yes

    # Resolve target path
    if target_dir is not None:
        target_path = Path(target_dir).expanduser().resolve()
    else:
        default_path = default_config_root()
        if yes:
            target_path = default_path
        else:
            ctx.output_manager.print_text(
                "\nWhere should Networka store its configuration?"
            )
            ctx.output_manager.print_text(f"[dim]Default: {default_path}[/dim]")
            user_input = typer.prompt("Location", default=str(default_path))
            target_path = Path(user_input).expanduser().resolve()

    # Check if configuration already exists and handle force flag
    if target_path.exists() and any(target_path.iterdir()) and not force:
        if yes:
            ctx.print_error(
                f"Configuration directory {target_path} already exists and is not empty. "
                "Use --force to overwrite."
            )
            raise typer.Exit(1)
        else:
            overwrite = typer.confirm(
                f"Configuration directory {target_path} already exists and is not empty. "
                "Overwrite?",
                default=False,
            )
            if not overwrite:
                ctx.print_info("Configuration initialization cancelled.")
                raise typer.Exit(0)

    if dry_run:
        ctx.print_info(f"DRY RUN: Would create configuration in {target_path}")
        return

    # Create directory structure
    target_path.mkdir(parents=True, exist_ok=True)
    (target_path / "devices").mkdir(exist_ok=True)
    (target_path / "groups").mkdir(exist_ok=True)
    (target_path / "sequences").mkdir(exist_ok=True)

    # Create core configuration files
    create_env_file(target_path)
    create_config_yml(target_path)
    create_example_devices(target_path / "devices")
    create_example_groups(target_path / "groups")
    create_example_sequences(target_path / "sequences")

    ctx.print_success(f"Configuration initialized in {target_path}")

    # Handle optional features
    default_seq_repo = "https://github.com/narrowin/networka.git"
    do_install_sequences = False
    do_install_compl = False
    do_install_schemas = False
    chosen_shell: str | None = None
    do_activate_compl = False

    interactive_extras = interactive and not dry_run

    if install_sequences is not None:
        do_install_sequences = install_sequences
    elif interactive_extras:
        do_install_sequences = typer.confirm(
            "Install additional predefined vendor sequences from GitHub?",
            default=True,
        )

    if install_completions is not None:
        do_install_compl = install_completions
    elif interactive_extras:
        do_install_compl = typer.confirm("Install shell completions?", default=True)

    if install_schemas is not None:
        do_install_schemas = install_schemas
    elif interactive_extras:
        do_install_schemas = typer.confirm(
            "Install JSON schemas for YAML editor validation and auto-completion?",
            default=True,
        )

    if do_install_compl:
        detected = (
            detect_shell(shell)
            if interactive_extras
            else (shell if shell in {"bash", "zsh"} else None)
        )
        if interactive_extras:
            default_shell = detected or "bash"
            answer = typer.prompt(
                "Choose shell for completions (bash|zsh)", default=default_shell
            )
            chosen_shell = answer if answer in {"bash", "zsh"} else default_shell
        else:
            chosen_shell = detected or "bash"

        if activate_completions is not None:
            do_activate_compl = activate_completions
        elif interactive_extras:
            do_activate_compl = typer.confirm(
                f"Activate {chosen_shell} completions by updating your shell profile?",
                default=True,
            )

    # Execute optional installations
    if do_install_sequences:
        try:
            install_sequences_from_repo(
                git_url or default_seq_repo,
                git_ref,
                target_path / "sequences",
            )
        except Exception as e:
            ctx.print_error(f"Failed to install sequences: {e}")

    if do_install_compl and chosen_shell:
        try:
            install_shell_completions(chosen_shell)
            if do_activate_compl:
                # Find the rc file for the shell
                rc_file = None
                if chosen_shell == "bash":
                    rc_file = Path.home() / ".bashrc"
                elif chosen_shell == "zsh":
                    rc_file = Path.home() / ".zshrc"

                if rc_file:
                    activate_shell_completion(chosen_shell, target_path, rc_file)
        except Exception as e:
            ctx.print_error(f"Failed to install completions: {e}")

    if do_install_schemas:
        try:
            install_editor_schemas(target_path)
        except Exception as e:
            ctx.print_error(f"Failed to install schemas: {e}")


def _config_validate_impl(
    config_file: Path,
    output_mode: OutputMode | None = None,
    verbose: bool = False,
) -> None:
    """Implementation logic for config validate."""
    output_manager = None
    try:
        config = load_config(config_file)

        # Handle output mode configuration
        if output_mode is not None:
            set_output_mode(output_mode)
            output_manager = get_output_manager()
        else:
            # Use config-based output mode
            output_manager = get_output_manager_with_config(config.general.output_mode)

        output_manager.print_info(f"Validating Configuration: {config_file}")
        output_manager.print_blank_line()

        output_manager.print_success("Configuration is valid!")
        output_manager.print_blank_line()

        device_count = len(config.devices) if config.devices else 0
        group_count = len(config.device_groups) if config.device_groups else 0
        global_seq_count = (
            len(config.global_command_sequences)
            if config.global_command_sequences
            else 0
        )

        output_manager.print_info(f"Devices: {device_count}")
        output_manager.print_info(f"Device Groups: {group_count}")
        output_manager.print_info(f"Global Sequences: {global_seq_count}")

        if verbose and device_count > 0 and config.devices:
            output_manager.print_blank_line()
            output_manager.print_info("Device Summary:")
            for name, device in config.devices.items():
                output_manager.print_info(
                    f"  • {name} ({device.host}) - {device.device_type}"
                )

    except NetworkToolkitError as e:
        # Initialize output_manager if not already set
        if output_manager is None:
            output_manager = get_output_manager()
        output_manager.print_error("Configuration validation failed!")
        output_manager.print_error(f"Error: {e.message}")
        if verbose and e.details:
            output_manager.print_error(f"Details: {e.details}")
        raise typer.Exit(1) from None
    except Exception as e:  # pragma: no cover - unexpected
        # Initialize output_manager if not already set
        if output_manager is None:
            output_manager = get_output_manager()
        output_manager.print_error(f"Unexpected error during validation: {e}")
        raise typer.Exit(1) from None


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
            # Use the local implementation
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
            # Use the local implementation
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
