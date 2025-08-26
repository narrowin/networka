# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Interactive configuration initialization for Networka.

Creates a complete starter configuration with:
- .env file with credential templates
- config.yml with core settings
- devices/ with MikroTik and Cisco examples
- groups/ with tag-based and explicit groups
- sequences/ with global and vendor-specific sequences

Additionally offers to install predefined sequences (bundled or from git)
and install shell completions in an idempotent manner.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.paths import default_config_root
from network_toolkit.exceptions import (
    ConfigurationError,
    FileTransferError,
    NetworkToolkitError,
)

logger = logging.getLogger(__name__)


def create_env_file(target_dir: Path) -> None:
    """Create a minimal .env file with credential templates and options.

    Args:
        target_dir: Directory where .env file will be created

    Raises:
        FileTransferError: If file creation fails
    """
    try:
        env_content = (
            "# Network Toolkit Environment Variables\n"
            "# Default credentials (used when device-specific vars not set)\n"
            "NW_USER_DEFAULT=admin\n"
            "NW_PASSWORD_DEFAULT=changeme123\n\n"  # pragma: allowlist secret
            "# Device-specific credential examples (optional)\n"
            "# NW_SW_OFFICE_01_USER=admin\n"
            "# NW_SW_OFFICE_01_PASSWORD=device_specific_password\n"
        )
        (target_dir / ".env").write_text(env_content, encoding="utf-8")
        logger.debug(f"Created .env file in {target_dir}")
    except OSError as e:
        msg = f"Failed to create .env file: {e}"
        raise FileTransferError(msg) from e


def create_config_yml(config_dir: Path) -> None:
    """Create a minimal config.yml with sane defaults.

    Args:
        config_dir: Directory where config.yml will be created

    Raises:
        FileTransferError: If file creation fails
    """
    try:
        content = 'general:\n  transport: "ssh"\n  timeout: 30\n  backup_dir: backups\n'
        (config_dir / "config.yml").write_text(content, encoding="utf-8")
        logger.debug(f"Created config.yml in {config_dir}")
    except OSError as e:
        msg = f"Failed to create config.yml: {e}"
        raise FileTransferError(msg) from e


def create_example_devices(devices_dir: Path) -> None:
    """Create example device files for MikroTik and Cisco.

    Args:
        devices_dir: Directory where device files will be created

    Raises:
        FileTransferError: If file or directory creation fails
    """
    try:
        devices_dir.mkdir(parents=True, exist_ok=True)
        mikrotik = (
            "sw-office-01:\n"
            "  host: 192.0.2.10\n"
            "  port: 22\n"
            "  platform: mikrotik_routeros\n"
            "  tags: [office, switch]\n"
        )
        cisco = (
            "rtr-core-01:\n"
            "  host: 192.0.2.1\n"
            "  port: 22\n"
            "  platform: cisco_ios\n"
            "  tags: [core, router]\n"
        )
        (devices_dir / "mikrotik.yml").write_text(mikrotik, encoding="utf-8")
        (devices_dir / "cisco.yml").write_text(cisco, encoding="utf-8")
        logger.debug(f"Created example device files in {devices_dir}")
    except OSError as e:
        msg = f"Failed to create device examples: {e}"
        raise FileTransferError(msg) from e


def create_example_groups(groups_dir: Path) -> None:
    """Create example groups with tag-based matching.

    Args:
        groups_dir: Directory where group files will be created

    Raises:
        FileTransferError: If file or directory creation fails
    """
    try:
        groups_dir.mkdir(parents=True, exist_ok=True)
        content = "office_switches:\n  match_tags: [office, switch]\n"
        (groups_dir / "main.yml").write_text(content, encoding="utf-8")
        logger.debug(f"Created example group files in {groups_dir}")
    except OSError as e:
        msg = f"Failed to create group examples: {e}"
        raise FileTransferError(msg) from e


def create_example_sequences(sequences_dir: Path) -> None:
    """Create basic example sequences shared across vendors.

    Args:
        sequences_dir: Directory where sequence files will be created

    Raises:
        FileTransferError: If file or directory creation fails
    """
    try:
        sequences_dir.mkdir(parents=True, exist_ok=True)
        content = (
            "system_info:\n"
            "  vendor: mikrotik_routeros\n"
            "  steps:\n"
            "    - cmd: /system/identity/print\n"
        )
        (sequences_dir / "basic.yml").write_text(content, encoding="utf-8")
        logger.debug(f"Created example sequence files in {sequences_dir}")
    except OSError as e:
        msg = f"Failed to create sequence examples: {e}"
        raise FileTransferError(msg) from e


def _detect_repo_root() -> Path | None:
    """Detect the repository root directory.

    Returns:
        Path to repository root, or None if not found
    """
    here = Path(__file__).resolve()
    parts = list(here.parents)
    if len(parts) >= 4:
        candidate = parts[3]
        if (candidate / "config" / "sequences").exists():
            return candidate
    return None


def _validate_git_url(url: str) -> None:
    """Validate Git URL for security.

    Args:
        url: Git URL to validate

    Raises:
        ConfigurationError: If URL is invalid or insecure
    """
    if not url:
        msg = "Git URL cannot be empty"
        raise ConfigurationError(msg)

    if not url.startswith(("https://", "git@")):
        msg = "Git URL must use HTTPS or SSH protocol"
        raise ConfigurationError(msg)

    # Block localhost and private IPs for security
    if any(
        pattern in url.lower()
        for pattern in ["localhost", "127.", "192.168.", "10.", "172."]
    ):
        msg = "Private IP addresses not allowed in Git URLs"
        raise ConfigurationError(msg)


def _find_git_executable() -> str:
    """Find git executable with full path for security.

    Returns:
        Full path to git executable

    Raises:
        ConfigurationError: If git is not found
    """
    import shutil as sh

    git_path = sh.which("git")
    if not git_path:
        msg = "Git executable not found in PATH"
        raise ConfigurationError(msg)
    return git_path


def install_sequences_from_repo(url: str, ref: str, dest: Path) -> None:
    """Install sequences from a Git repository.

    Args:
        url: Git repository URL
        ref: Git reference (branch/tag/commit)
        dest: Destination directory for sequences

    Raises:
        ConfigurationError: If Git URL is invalid
        FileTransferError: If download or extraction fails
    """
    _validate_git_url(url)
    git_exe = _find_git_executable()

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir) / "repo"
        try:
            subprocess.run(
                [
                    git_exe,
                    "clone",
                    "--depth",
                    "1",
                    "--branch",
                    ref,
                    url,
                    str(tmp_root),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            src = tmp_root / "config" / "sequences"
            if not src.exists():
                logger.warning("No sequences found in repo under config/sequences")
                return

            # Copy sequences to destination
            for item in src.iterdir():
                if item.name.startswith(".git"):
                    continue
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, target)

            logger.debug(f"Copied sequences from {url}@{ref} to {dest}")

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            msg = f"Git clone failed: {error_msg}"
            raise FileTransferError(msg) from e
        except OSError as e:
            msg = f"Failed to copy sequences: {e}"
            raise FileTransferError(msg) from e


def install_editor_schemas(
    config_root: Path, git_url: str | None = None, git_ref: str = "main"
) -> None:
    """Install JSON schemas and VS Code settings for YAML editor validation.

    Args:
        config_root: Root configuration directory
        git_url: Git URL for schema source
        git_ref: Git reference for schemas

    Raises:
        FileTransferError: If schema installation fails
    """
    try:
        # Create schemas directory
        schemas_dir = config_root / "schemas"
        schemas_dir.mkdir(exist_ok=True)

        # Schema files to download from GitHub
        schema_files = [
            "network-config.schema.json",
            "device-config.schema.json",
            "groups-config.schema.json",
        ]

        github_base_url = (
            f"{git_url or 'https://github.com/narrowin/networka.git'}".replace(
                ".git", ""
            )
            + f"/raw/{git_ref}/schemas"
        )

        # Download each schema file
        for schema_file in schema_files:
            try:
                schema_url = f"{github_base_url}/{schema_file}"
                schema_path = schemas_dir / schema_file

                # Validate URL scheme for security
                if not schema_url.startswith(("http:", "https:")):
                    msg = "URL must start with 'http:' or 'https:'"
                    raise ValueError(msg)

                with urllib.request.urlopen(schema_url) as response:  # noqa: S310
                    schema_content = response.read().decode("utf-8")
                    schema_path.write_text(schema_content, encoding="utf-8")

                logger.debug(f"Downloaded {schema_file}")
            except Exception as e:
                logger.warning(f"Failed to download {schema_file}: {e}")

        # Create VS Code settings for YAML validation
        vscode_dir = config_root / ".vscode"
        vscode_dir.mkdir(exist_ok=True)

        settings_path = vscode_dir / "settings.json"
        yaml_schema_config = {
            "yaml.schemas": {
                "./schemas/network-config.schema.json": [
                    "config/config.yml",
                    "devices.yml",
                ],
                "./schemas/device-config.schema.json": [
                    "config/devices/*.yml",
                    "config/devices.yml",
                ],
                "./schemas/groups-config.schema.json": [
                    "config/groups/*.yml",
                    "config/groups.yml",
                ],
            }
        }

        if settings_path.exists():
            try:
                with settings_path.open(encoding="utf-8") as f:
                    existing_settings = json.load(f)
                existing_settings.update(yaml_schema_config)
                yaml_schema_config = existing_settings
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Failed to merge existing VS Code settings: {e}")

        settings_path.write_text(
            json.dumps(yaml_schema_config, indent=2), encoding="utf-8"
        )

        logger.debug("Configured JSON schemas and VS Code settings")

    except OSError as e:
        msg = f"Failed to install schemas: {e}"
        raise FileTransferError(msg) from e


def detect_shell(shell: str | None = None) -> str | None:
    """Detect the user's shell for completion installation.

    Args:
        shell: Explicitly specified shell

    Returns:
        Detected shell name or None if unsupported
    """
    if shell in {"bash", "zsh"}:
        return shell
    env_shell = os.environ.get("SHELL", "")
    for name in ("bash", "zsh"):
        if name in env_shell:
            return name
    return None


def install_shell_completions(selected: str) -> tuple[Path | None, Path | None]:
    """Install shell completion scripts.

    Args:
        selected: Shell type (bash or zsh)

    Returns:
        Tuple of (installed_path, rc_file_path) or (None, None) on failure

    Raises:
        ConfigurationError: If shell is unsupported
        FileTransferError: If installation fails
    """
    if selected not in {"bash", "zsh"}:
        msg = "Only bash and zsh shells are supported for completion installation"
        raise ConfigurationError(msg)

    repo_root = _detect_repo_root()
    if not repo_root:
        logger.warning("Completion scripts not found; skipping")
        return (None, None)

    sc_dir = repo_root / "shell_completion"
    if not sc_dir.exists():
        logger.warning(f"Shell completion directory not found: {sc_dir}")
        return (None, None)

    try:
        home = Path.home()
        if selected == "bash":
            src = sc_dir / "bash_completion_nw.sh"
            if not src.exists():
                logger.warning(f"Bash completion script not found: {src}")
                return (None, None)
            dest = home / ".local" / "share" / "bash-completion" / "completions" / "nw"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return (dest, home / ".bashrc")
        else:  # zsh
            src = sc_dir / "zsh_completion_netkit.zsh"
            if not src.exists():
                logger.warning(f"Zsh completion script not found: {src}")
                return (None, None)
            dest = home / ".zsh" / "completions" / "_nw"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return (dest, home / ".zshrc")

    except OSError as e:
        msg = f"Failed to install {selected} completion: {e}"
        raise FileTransferError(msg) from e


def activate_shell_completion(
    selected: str, installed: Path, rc_file: Path | None
) -> None:
    """Activate shell completion by updating RC file.

    Args:
        selected: Shell type
        installed: Path to installed completion script
        rc_file: Path to shell RC file

    Raises:
        FileTransferError: If RC file update fails
    """
    if rc_file is None:
        return

    try:
        begin = "# >>> NW COMPLETION >>>"
        end = "# <<< NW COMPLETION <<<"
        if selected == "bash":
            snippet = f'\n{begin}\n# Networka bash completion\nif [ -f "{installed}" ]; then\n  source "{installed}"\nfi\n{end}\n'
        else:
            compdir = installed.parent
            snippet = f"\n{begin}\n# Networka zsh completion\nfpath=({compdir} $fpath)\nautoload -Uz compinit && compinit\n{end}\n"

        if not rc_file.exists():
            rc_file.write_text(snippet, encoding="utf-8")
            logger.info(f"Updated rc file: {rc_file}")
            return

        content = rc_file.read_text(encoding="utf-8")
        if begin in content and end in content:
            logger.info("Completion activation already present in rc; skipping")
            return

        with rc_file.open("a", encoding="utf-8") as fh:
            fh.write(snippet)
        logger.info(f"Activated shell completion in: {rc_file}")

    except OSError as e:
        msg = f"Failed to activate shell completion: {e}"
        raise FileTransferError(msg) from e


def register(app: typer.Typer) -> None:
    """Register the config-init command."""

    @app.command("config-init", rich_help_panel="Info & Configuration")
    def config_init(
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
                    if typer.confirm("Use default location?", default=True):
                        target_path = default_path
                    else:
                        entered = typer.prompt(
                            "Enter a directory path", default=str(default_path)
                        )
                        target_path = Path(entered).expanduser()
                target_path = target_path.resolve()

            # Important paths
            config_dir = target_path
            env_file = target_path / ".env"
            devices_dir = config_dir / "devices"
            groups_dir = config_dir / "groups"
            sequences_dir = config_dir / "sequences"

            # Overwrite protection
            if not force:
                existing: list[str] = []
                if env_file.exists():
                    existing.append(str(env_file))
                cfg = config_dir / "config.yml"
                if cfg.exists():
                    existing.append(str(cfg))
                if devices_dir.exists():
                    existing.append(str(devices_dir))
                if existing:
                    if not interactive:
                        ctx.print_warning(
                            "The following files/directories already exist:"
                        )
                        for p in existing:
                            ctx.output_manager.print_text(f"  - {p}")
                        ctx.print_warning("Use --force to overwrite existing files.")
                        raise typer.Exit(1)
                    else:
                        ctx.print_warning(
                            "Existing configuration detected in the default location."
                        )
                        if not typer.confirm(
                            "Overwrite existing files?", default=False
                        ):
                            raise typer.Exit(1)

            ctx.print_info(
                f"Initializing network toolkit configuration in: {target_path}"
            )

            # Gather answers first when interactive
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
                do_install_compl = typer.confirm(
                    "Install shell completions?", default=True
                )

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
                    chosen_shell = (
                        answer if answer in {"bash", "zsh"} else default_shell
                    )
                else:
                    chosen_shell = detected or "bash"

                if activate_completions is not None:
                    do_activate_compl = activate_completions
                elif interactive_extras:
                    do_activate_compl = typer.confirm(
                        "Activate completions by updating your shell rc file?",
                        default=True,
                    )

            # Perform writes now (in interactive mode, this is after all questions)
            if dry_run:
                ctx.print_info(f"[dry-run] Would create file: {env_file}")
                ctx.print_info(f"[dry-run] Would ensure directory: {devices_dir}")
                ctx.print_info(f"[dry-run] Would ensure directory: {groups_dir}")
                ctx.print_info(f"[dry-run] Would ensure directory: {sequences_dir}")
                ctx.print_info(
                    "[dry-run] Would create config.yml/devices/groups and basic sequences"
                )
            else:
                if not target_path.exists():
                    target_path.mkdir(parents=True, exist_ok=True)
                    ctx.print_info(f"Created directory: {target_path}")

                create_env_file(target_path)
                devices_dir.mkdir(exist_ok=True)
                groups_dir.mkdir(exist_ok=True)
                sequences_dir.mkdir(exist_ok=True)
                create_config_yml(config_dir)
                create_example_devices(devices_dir)
                create_example_groups(groups_dir)
                create_example_sequences(sequences_dir)

            # Sequences from GitHub
            if do_install_sequences:
                chosen_seq_url = git_url or default_seq_repo
                if dry_run:
                    ctx.print_info(
                        f"[dry-run] Would download sequences from {chosen_seq_url}@{git_ref} into: {sequences_dir}"
                    )
                else:
                    try:
                        install_sequences_from_repo(
                            chosen_seq_url, git_ref, sequences_dir
                        )
                        ctx.print_success(
                            f"Installed additional sequences from {chosen_seq_url}@{git_ref}"
                        )
                    except NetworkToolkitError as e:
                        ctx.print_warning(f"Failed to install sequences: {e}")

            # Shell completions
            if do_install_compl and chosen_shell:
                if dry_run:
                    ctx.print_info(
                        f"[dry-run] Would install {chosen_shell} completion and activate={do_activate_compl}"
                    )
                else:
                    try:
                        installed_path, rc_file = install_shell_completions(
                            chosen_shell
                        )
                        if installed_path is not None:
                            ctx.print_success(
                                f"Installed {chosen_shell} completion script to: {installed_path}"
                            )
                            if rc_file:
                                ctx.output_manager.print_text(
                                    f"Shell rc file detected: {rc_file}"
                                )
                            if do_activate_compl:
                                activate_shell_completion(
                                    chosen_shell, installed_path, rc_file
                                )
                                ctx.print_success(
                                    "Activation snippet appended. Open a new shell to use completions."
                                )
                            else:
                                ctx.output_manager.print_text(
                                    "Activation skipped. You can manually source or add the snippet later."
                                )
                        else:
                            ctx.print_warning("Shell completion installation failed.")
                    except NetworkToolkitError as e:
                        ctx.print_warning(f"Failed to install completions: {e}")

            # JSON Schemas for editor validation
            if do_install_schemas:
                if dry_run:
                    ctx.print_info(
                        "[dry-run] Would install JSON schemas and VS Code settings for YAML validation"
                    )
                else:
                    try:
                        install_editor_schemas(target_path, git_url, git_ref)
                        ctx.print_success(
                            "Installed JSON schemas for YAML editor validation"
                        )
                    except NetworkToolkitError as e:
                        ctx.print_warning(f"Failed to install schemas: {e}")

            ctx.print_success("Configuration initialization complete!")

        except NetworkToolkitError as e:
            ctx = CommandContext()
            ctx.print_error(str(e))
            raise typer.Exit(1) from e
        except typer.Exit:
            # Let typer.Exit pass through without logging as unexpected error
            raise
        except Exception as e:
            logger.exception("Unexpected error during configuration initialization")
            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from e


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
    """Implementation function for config init that can be called from unified command.

    This delegates to the original config_init function by creating a temporary Typer app
    and calling the registered command.
    """
    # Create a temporary app to get access to the registered command
    temp_app = typer.Typer()
    register(temp_app)

    # Find and call the registered command function
    for cmd_info in temp_app.registered_commands:
        if cmd_info.name == "config-init" and cmd_info.callback:
            cmd_info.callback(
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
            return

    # This should never happen
    error_msg = "Could not find config-init command in registered commands"
    raise RuntimeError(error_msg)
