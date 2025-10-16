"""Unified config commands for the network toolkit CLI."""

from __future__ import annotations

import logging
import os
import shutil
from pathlib import Path
from typing import Annotated, cast

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
from network_toolkit.common.paths import default_config_root, default_modular_config_dir
from network_toolkit.config import load_config
from network_toolkit.exceptions import (
    ConfigurationError,
    FileTransferError,
    NetworkToolkitError,
)

logger = logging.getLogger(__name__)


def _discover_config_metadata(original: Path) -> dict[str, object]:
    """Discover where config was loaded from and which files are involved.

    Mirrors the resolution logic in `load_config` to report:
    - mode: "modular"
    - root: Path of the modular root directory
    - files: list[Path] of relevant files that were validated
    - display_name: user-facing name for the target (keep "config" when used)
    """
    # Keep the provided token for display (we want to show just "config" when used)
    display_name = str(original)
    path = Path(original)

    # Helper: collect existing files under a directory with a stable, readable order
    def collect_modular_files(root: Path) -> list[Path]:
        files: list[Path] = []
        for name in ("config.yml", "devices.yml", "groups.yml", "sequences.yml"):
            p = root / name
            if p.exists():
                files.append(p)
        # Include nested directories if present
        for sub in ("devices", "groups", "sequences"):
            d = root / sub
            if d.exists() and d.is_dir():
                # Collect YAML & CSV fragments, sorted for stable output
                for ext in ("*.yml", "*.yaml", "*.csv"):
                    files.extend(sorted(d.rglob(ext)))
        return files

    # Resolution logic (aligned with config.load_config)
    # 1) Directory input with direct modular files
    if path.exists() and path.is_dir():
        direct_cfg = path / "config.yml"
        if direct_cfg.exists():
            root = path
            return {
                "mode": "modular",
                "root": root.resolve(),
                "files": collect_modular_files(root),
                "display_name": display_name,
            }

    # 2) Direct config.yml file path
    if (
        path.exists()
        and path.is_file()
        and path.name.lower() in {"config.yml", "config.yaml"}
    ):
        root = path.parent
        return {
            "mode": "modular",
            "root": root.resolve(),
            "files": collect_modular_files(root),
            "display_name": display_name,
        }

    # 3) Fallback to platform default modular directory for default token
    if str(path) in ["config"]:
        platform_default = default_modular_config_dir()
        cfg_yaml = platform_default / "config.yml"
        if cfg_yaml.exists():
            root = platform_default
            return {
                "mode": "modular",
                "root": root.resolve(),
                "files": collect_modular_files(root),
                "display_name": display_name,
            }
        # No cwd based fallbacks anymore

    # 5) Final attempt similar to load_config last check
    platform_default = default_modular_config_dir()
    if (platform_default / "config.yml").exists():
        root = platform_default
        return {
            "mode": "modular",
            "root": root.resolve(),
            "files": collect_modular_files(root),
            "display_name": display_name,
        }

    # Unknown — return best-effort with the original path
    return {
        "mode": "unknown",
        "root": path.resolve(),
        "files": [],
        "display_name": display_name,
    }


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

  # Default transport for all devices (can be overridden per device)
  transport: system     # Options: system, paramiko, ssh

# Device configurations are loaded from devices/ directory
# Group configurations are loaded from groups/ directory
# Sequence configurations are loaded from sequences/ directory
"""
    config_file = config_dir / "config.yml"
    config_file.write_text(config_content)


def create_example_devices(devices_dir: Path) -> None:
    """Create example device configurations."""
    devices_dir.mkdir(parents=True, exist_ok=True)

    devices_content = """# Example Device Configurations
devices:
  router1:
    host: 192.168.1.1
    device_type: mikrotik_routeros
    platform: tile
    description: "Main office router"
    tags:
      - office
      - critical

  switch1:
    host: 192.168.1.2
    device_type: cisco_iosxe
    platform: x86
    description: "Access switch"
    tags:
      - switch
      - access
"""

    (devices_dir / "devices.yml").write_text(devices_content)


def create_example_groups(groups_dir: Path) -> None:
    """Create example group configurations."""
    groups_dir.mkdir(parents=True, exist_ok=True)

    groups_content = """# Example Group Configurations
groups:
  office:
    description: "All office network devices"
    match_tags:
      - office

  critical:
    description: "Critical network infrastructure"
    match_tags:
      - critical
"""

    (groups_dir / "groups.yml").write_text(groups_content)


def create_example_sequences(sequences_dir: Path) -> None:
    """Create example sequence configurations."""
    sequences_dir.mkdir(parents=True, exist_ok=True)

    sequences_content = """# Example Command Sequences
sequences:
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

    (sequences_dir / "sequences.yml").write_text(sequences_content)

    # Create vendor-specific directories
    (sequences_dir / "mikrotik").mkdir(exist_ok=True)
    (sequences_dir / "cisco").mkdir(exist_ok=True)

    # Create vendor-specific sequences
    mikrotik_content = """# MikroTik RouterOS Sequences
system_info:
  description: "System information and status"
  commands:
    - "/system resource print"
    - "/system identity print"
    - "/system clock print"

interface_status:
  description: "Interface status and configuration"
  commands:
    - "/interface print brief"
    - "/ip address print"
"""

    cisco_content = """# Cisco IOS Sequences
system_info:
  description: "System information and status"
  commands:
    - "show version"
    - "show running-config | include hostname"
    - "show clock"

interface_status:
  description: "Interface status and configuration"
  commands:
    - "show ip interface brief"
    - "show interface status"
"""

    (sequences_dir / "mikrotik" / "system.yml").write_text(mikrotik_content)
    (sequences_dir / "cisco" / "system.yml").write_text(cisco_content)


def _validate_git_url(url: str) -> None:
    """Validate Git URL for security."""
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
    """Find git executable with full path for security."""
    import shutil as sh

    git_path = sh.which("git")
    if not git_path:
        msg = "Git executable not found in PATH"
        raise ConfigurationError(msg)
    return git_path


def _detect_repo_root() -> Path | None:
    """Detect the repository root directory (development mode only)."""
    # Look for a .git folder upwards as a strong signal
    here = Path(__file__).resolve()
    for parent in [here, *here.parents]:
        if (parent / ".git").exists() and (parent / "shell_completion").exists():
            return parent
    # Fallback to pyproject presence
    for parent in [here, *here.parents]:
        if (parent / "pyproject.toml").exists() and (
            parent / "shell_completion"
        ).exists():
            return parent
    return None


def detect_shell(shell: str | None = None) -> str | None:
    """Detect the user's shell for completion installation."""
    if shell in {"bash", "zsh"}:
        return shell
    env_shell = os.environ.get("SHELL", "")
    for name in ("bash", "zsh"):
        if name in env_shell:
            return name
    return None


def install_shell_completions(selected: str) -> tuple[Path | None, Path | None]:
    """Install shell completion scripts.

    Tries packaged resources first, then falls back to repo-root files in dev.
    """
    if selected not in {"bash", "zsh"}:
        msg = "Only bash and zsh shells are supported for completion installation"
        raise ConfigurationError(msg)

    # Try packaged resources under network_toolkit.shell_completion first
    pkg_src: Path | None = None
    try:
        import importlib.resources as ir

        if selected == "bash":
            with ir.path(
                "network_toolkit.shell_completion", "bash_completion_nw.sh"
            ) as p:
                pkg_src = p if p.exists() else None
        else:
            with ir.path(
                "network_toolkit.shell_completion", "zsh_completion_nw.zsh"
            ) as p:
                pkg_src = p if p.exists() else None
    except Exception:  # pragma: no cover - safety
        pkg_src = None

    # Fallback to repo-root scripts in development mode
    repo_src: Path | None = None
    repo_root = _detect_repo_root()
    if repo_root:
        sc_dir = repo_root / "shell_completion"
        if selected == "bash":
            cand = sc_dir / "bash_completion_nw.sh"
        else:
            cand = sc_dir / "zsh_completion_netkit.zsh"
        if cand.exists():
            repo_src = cand

    if not pkg_src and not repo_src:
        logger.warning("Completion scripts not found; skipping")
        return (None, None)

    try:
        home = Path.home()
        # Pick packaged source first, otherwise repo source
        src = pkg_src or repo_src
        assert src is not None  # for type checkers
        if selected == "bash":
            dest = home / ".local" / "share" / "bash-completion" / "completions" / "nw"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return (dest, home / ".bashrc")
        else:  # zsh
            dest = home / ".zsh" / "completions" / "_nw"
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return (dest, home / ".zshrc")

    except OSError as e:
        msg = f"Failed to install {selected} completion: {e}"
        raise FileTransferError(msg) from e


def activate_shell_completion(
    shell: str, installed: Path, rc_file: Path | None
) -> None:
    """Activate shell completion by updating RC file."""
    if rc_file is None:
        return

    try:
        begin = "# >>> NW COMPLETION >>>"
        end = "# <<< NW COMPLETION <<<"
        if shell == "bash":
            snippet = f'\n{begin}\n# Networka bash completion\nif [ -f "{installed}" ]; then\n  source "{installed}"\nfi\n{end}\n'
        else:
            compdir = installed.parent
            snippet = f"\n{begin}\n# Networka zsh completion\nfpath=({compdir} $fpath)\nautoload -Uz compinit && compinit\n{end}\n"

        if not rc_file.exists():
            rc_file.write_text(snippet, encoding="utf-8")
            logger.debug(f"Created rc file with completion: {rc_file}")
            return

        content = rc_file.read_text(encoding="utf-8")
        if begin in content and end in content:
            logger.debug("Completion activation already present in rc; skipping")
            return

        with rc_file.open("a", encoding="utf-8") as fh:
            fh.write(snippet)
        logger.debug(f"Activated shell completion in: {rc_file}")

    except OSError as e:
        msg = f"Failed to activate shell completion: {e}"
        raise FileTransferError(msg) from e


def install_sequences_from_repo(url: str, ref: str, dest: Path) -> int:
    """Install sequences from a Git repository.

    Returns:
        Number of files installed
    """
    import shutil
    import subprocess
    import tempfile

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
                logger.debug("No sequences found in repo under config/sequences")
                return 0

            # Copy sequences to destination
            files_copied = 0
            for item in src.iterdir():
                if item.name.startswith(".git"):
                    continue
                target = dest / item.name
                if item.is_dir():
                    shutil.copytree(item, target, dirs_exist_ok=True)
                    files_copied += 1
                else:
                    shutil.copy2(item, target)
                    files_copied += 1

            logger.debug(
                f"Copied {files_copied} sequence files from {url}@{ref} to {dest}"
            )
            return files_copied

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else str(e)
            msg = f"Git clone failed: {error_msg}"
            raise FileTransferError(msg) from e
        except OSError as e:
            msg = f"Failed to copy sequences: {e}"
            raise FileTransferError(msg) from e


def install_editor_schemas(
    config_root: Path, git_url: str | None = None, git_ref: str = "main"
) -> int:
    """Install JSON schemas and VS Code settings for YAML editor validation.

    Returns:
        Number of schema files installed
    """
    import json
    import urllib.request

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
        files_downloaded = 0
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
                files_downloaded += 1
            except Exception as e:
                logger.debug(f"Failed to download {schema_file}: {e}")

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
                logger.debug(f"Failed to merge existing VS Code settings: {e}")

        settings_path.write_text(
            json.dumps(yaml_schema_config, indent=2), encoding="utf-8"
        )

        logger.debug("Configured JSON schemas and VS Code settings")
        return files_downloaded

    except OSError as e:
        msg = f"Failed to install schemas: {e}"
        raise FileTransferError(msg) from e


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
            ctx.print_detail_line("Default", str(default_path))
            user_input = typer.prompt("Location", default=str(default_path))
            target_path = Path(user_input).expanduser().resolve()

    # Check if configuration already exists and handle force flag
    skip_base_config = False
    if target_path.exists() and any(target_path.iterdir()) and not force:
        if yes:
            # In --yes mode, we proceed without prompting (same as if user said yes)
            pass
        else:
            overwrite = typer.confirm(
                f"Configuration directory {target_path} already exists and is not empty. "
                "Overwrite?",
                default=False,
            )
            if not overwrite:
                ctx.print_info("Skipping base configuration setup (directory exists).")
                skip_base_config = True

    if dry_run:
        ctx.print_info(f"DRY RUN: Would create configuration in {target_path}")
        if not skip_base_config:
            ctx.print_info("DRY RUN: Would also ask about optional features")
        return

    # Create directory structure and base config only if not skipping
    if not skip_base_config:
        target_path.mkdir(parents=True, exist_ok=True)
        (target_path / "devices").mkdir(exist_ok=True)
        (target_path / "groups").mkdir(exist_ok=True)
        (target_path / "sequences").mkdir(exist_ok=True)

        # Create core configuration files
        ctx.print_info("Creating configuration files...")
        create_env_file(target_path)
        ctx.print_success(f"Created credential template: {target_path / '.env'}")

        create_config_yml(target_path)
        ctx.print_success(f"Created main configuration: {target_path / 'config.yml'}")

        create_example_devices(target_path / "devices")
        ctx.print_success(f"Created example devices: {target_path / 'devices'}")

        create_example_groups(target_path / "groups")
        ctx.print_success(f"Created example groups: {target_path / 'groups'}")

        create_example_sequences(target_path / "sequences")
        ctx.print_success(f"Created example sequences: {target_path / 'sequences'}")

        ctx.print_success(f"Base configuration initialized in {target_path}")
    else:
        # Ensure the target path exists for optional features
        target_path.mkdir(parents=True, exist_ok=True)

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

    # Group all shell completion questions together
    chosen_shell = None
    do_activate_compl = False
    if install_completions is not None:
        do_install_compl = install_completions
    elif interactive_extras:
        do_install_compl = typer.confirm("Install shell completions?", default=True)

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

    if install_schemas is not None:
        do_install_schemas = install_schemas
    elif interactive_extras:
        do_install_schemas = typer.confirm(
            "Install JSON schemas for YAML editor validation and auto-completion?",
            default=True,
        )

    # Execute optional installations
    if do_install_sequences:
        try:
            ctx.print_info("Installing additional vendor sequences...")
            files_installed = install_sequences_from_repo(
                git_url or default_seq_repo,
                git_ref,
                target_path / "sequences",
            )
            if files_installed > 0:
                ctx.print_success(
                    f"Installed {files_installed} sequence files from {git_url or default_seq_repo}"
                )
            else:
                ctx.print_warning("No sequence files found in repository")
        except Exception as e:
            ctx.print_error(f"Failed to install sequences: {e}")

    if do_install_compl and chosen_shell:
        try:
            ctx.print_info(f"Installing {chosen_shell} shell completion...")
            installed_path, rc_file = install_shell_completions(chosen_shell)
            if installed_path is not None:
                ctx.print_success(f"Installed completion script: {installed_path}")
                if do_activate_compl and rc_file:
                    activate_shell_completion(chosen_shell, installed_path, rc_file)
                    ctx.print_success(f"Activated completion in: {rc_file}")
                    ctx.print_info(
                        "Restart your shell or run 'source ~/.bashrc' to enable completions"
                    )
                else:
                    ctx.print_info("Completion script installed but not activated")
            else:
                ctx.print_warning("Shell completion installation failed")
        except Exception as e:
            ctx.print_error(f"Failed to install completions: {e}")

    if do_install_schemas:
        try:
            ctx.print_info("Installing JSON schemas for YAML editor validation...")
            schema_count = install_editor_schemas(target_path, git_url, git_ref)
            if schema_count > 0:
                ctx.print_success(
                    f"Installed {schema_count} schema files in: {target_path / 'schemas'}"
                )
                ctx.print_success(
                    f"Configured VS Code settings: {target_path / '.vscode' / 'settings.json'}"
                )
            else:
                ctx.print_warning("No schema files could be downloaded")
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

        # Discover and display where the config was resolved from
        meta = _discover_config_metadata(config_file)
        display_name = str(meta.get("display_name", str(config_file)))
        resolved_root = meta.get("root")
        files = meta.get("files")
        mode = meta.get("mode")

        output_manager.print_info(f"Validating Configuration: {display_name}")
        if isinstance(resolved_root, Path):
            output_manager.print_info(f"Path: {resolved_root}")
        if isinstance(mode, str) and mode in {"modular"}:
            output_manager.print_info(f"Mode: {mode}")
        if isinstance(files, list) and files:
            output_manager.print_info("Files:")
            files_typed = cast(list[Path], files)
            for f in files_typed:
                output_manager.print_info(f"  - {f}")
        output_manager.print_blank_line()

        output_manager.print_success("Configuration is valid!")
        output_manager.print_blank_line()

        device_count = len(config.devices) if config.devices else 0
        group_count = len(config.device_groups) if config.device_groups else 0

        output_manager.print_info(f"Devices: {device_count}")
        output_manager.print_info(f"Device Groups: {group_count}")

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
        context_settings={"help_option_names": ["-h", "--help"]},
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

        # Show banner for config init
        from network_toolkit.banner import show_banner

        show_banner()
        print()  # Add spacing

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
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
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
        except typer.Exit:
            # Allow clean exits (e.g., user cancellation) to pass through
            raise
        except Exception as e:  # pragma: no cover - unexpected
            from network_toolkit.common.command_helpers import CommandContext

            ctx = CommandContext()
            ctx.print_error(f"Unexpected error: {e}")
            raise typer.Exit(1) from None

    app.add_typer(config_app, name="config", rich_help_panel="Info & Configuration")
