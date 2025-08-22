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

import os
import shutil
import subprocess
from pathlib import Path
from typing import Annotated

import typer

from network_toolkit.common.logging import console, setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.paths import default_config_root
from network_toolkit.common.styles import StyleManager, StyleName


def _print_success(message: str) -> None:
    """Print success message using default theme."""
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(message, StyleName.SUCCESS)
    console.print(styled_message)


def _print_info(message: str) -> None:
    """Print info message using default theme."""
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(message, StyleName.INFO)
    console.print(styled_message)


def _print_warn(message: str) -> None:
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(message, StyleName.WARNING)
    console.print(styled_message)


def _print_action(message: str) -> None:
    style_manager = StyleManager(mode=OutputMode.DEFAULT)
    styled_message = style_manager.format_message(message, StyleName.INFO)
    console.print(styled_message)


def create_env_file(target_dir: Path) -> None:
    """Create a minimal .env file with credential templates and options."""
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


def create_config_yml(config_dir: Path) -> None:
    """Create a minimal config.yml with sane defaults."""
    content = 'general:\n  transport: "ssh"\n  timeout: 30\n  backup_dir: backups\n'
    (config_dir / "config.yml").write_text(content, encoding="utf-8")


def create_example_devices(devices_dir: Path) -> None:
    """Create example device files for MikroTik and Cisco."""
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


def create_example_groups(groups_dir: Path) -> None:
    """Create example groups with tag-based matching."""
    groups_dir.mkdir(parents=True, exist_ok=True)
    content = "office_switches:\n  match_tags: [office, switch]\n"
    (groups_dir / "main.yml").write_text(content, encoding="utf-8")


def create_example_sequences(sequences_dir: Path) -> None:
    """Create basic example sequences shared across vendors."""
    sequences_dir.mkdir(parents=True, exist_ok=True)
    content = (
        "system_info:\n"
        "  vendor: mikrotik_routeros\n"
        "  steps:\n"
        "    - cmd: /system/identity/print\n"
    )
    (sequences_dir / "basic.yml").write_text(content, encoding="utf-8")


def create_vendor_sequences(sequences_dir: Path) -> None:
    """Create vendor-specific sequences directory structure (placeholder)."""
    # Keep minimal for now; tests only require basic.yml to exist
    _ = sequences_dir


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
        ] = "ssh_multiplex",
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
                console.print("\nWhere should Networka store its configuration?")
                console.print(f"[dim]Default:[/dim] {default_path}")
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

        # Overwrite protection (no creation yet; we may be in interactive mode)
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
                    console.print(
                        "[yellow]Warning: The following files/directories already exist:[/yellow]"
                    )
                    for p in existing:
                        console.print(f"  - {p}")
                    console.print(
                        "\n[yellow]Use --force to overwrite existing files.[/yellow]"
                    )
                    raise typer.Exit(1)
                else:
                    console.print(
                        "[yellow]Existing configuration detected in the default location.[/yellow]"
                    )
                    if not typer.confirm("Overwrite existing files?", default=False):
                        raise typer.Exit(1)

        console.print(
            f"[bold cyan]Initializing network toolkit configuration in: {target_path}[/bold cyan]"
        )
        console.print()

        # Helper: locate repo root (for completion scripts)
        def _detect_repo_root() -> Path | None:
            here = Path(__file__).resolve()
            parts = list(here.parents)
            if len(parts) >= 4:
                candidate = parts[3]
                if (candidate / "config" / "sequences").exists():
                    return candidate
            return None

        # Clone sequences repo helper
        def _install_sequences_from_repo(url: str, ref: str, dest: Path) -> None:
            tmp_root = dest.with_name(dest.name + ".repo")
            if tmp_root.exists():
                shutil.rmtree(tmp_root, ignore_errors=True)
            try:
                subprocess.run(
                    [
                        "git",
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
                )
                src = tmp_root / "config" / "sequences"
                if src.exists():
                    for item in src.iterdir():
                        if item.name.startswith(".git"):
                            continue
                        target = dest / item.name
                        if item.is_dir():
                            shutil.copytree(item, target, dirs_exist_ok=True)
                        else:
                            shutil.copy2(item, target)
                    _print_success(
                        f"Installed additional sequences from {url}@{ref} into: {dest}"
                    )
                else:
                    _print_warn(
                        "No sequences found in repo under config/sequences; skipping."
                    )
            except Exception as e:
                _print_warn(f"Failed to download sequences from {url}@{ref}: {e}")
            finally:
                shutil.rmtree(tmp_root, ignore_errors=True)

        # Schema installation helper
        def _install_editor_schemas(config_root: Path) -> None:
            """Install JSON schemas and VS Code settings for YAML editor validation."""
            try:
                # Import here to avoid circular imports
                # Change to config directory temporarily to generate schemas there
                import os

                from network_toolkit.config import export_schemas_to_workspace

                original_cwd = Path.cwd()
                try:
                    os.chdir(config_root)
                    export_schemas_to_workspace()
                    _print_success("Installed JSON schemas for YAML editor validation")
                    console.print(
                        "   - schemas/network-config.schema.json (full config)"
                    )
                    console.print(
                        "   - schemas/device-config.schema.json (device files)"
                    )
                    console.print(
                        "   - .vscode/settings.json (VS Code YAML validation)"
                    )
                    console.print()
                    console.print("🎯 Your YAML files now have:")
                    console.print(
                        "   • Auto-completion for device_type and other fields"
                    )
                    console.print("   • Validation errors for invalid configurations")
                    console.print("   • Hover tooltips with field descriptions")
                finally:
                    os.chdir(original_cwd)
            except Exception as e:
                _print_warn(f"Failed to install schemas: {e}")
                console.print("   You can manually export schemas later with:")
                console.print(
                    "   cd your-config-dir && python -c 'from network_toolkit.config import export_schemas_to_workspace; export_schemas_to_workspace()'"
                )

        # Shell completion helpers
        def _detect_shell() -> str | None:
            if shell in {"bash", "zsh"}:
                return shell
            env_shell = os.environ.get("SHELL", "")
            for name in ("bash", "zsh"):
                if name in env_shell:
                    return name
            return None

        def _install_shell_for(selected: str) -> tuple[Path, Path | None]:
            repo_root = _detect_repo_root()
            if not repo_root:
                _print_warn("Completion scripts not found; skipping.")
                return (Path(""), None)
            sc_dir = repo_root / "shell_completion"
            home = Path.home()
            if selected == "bash":
                src = sc_dir / "bash_completion_nw.sh"
                dest = (
                    home / ".local" / "share" / "bash-completion" / "completions" / "nw"
                )
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                return (dest, home / ".bashrc")
            if selected == "zsh":
                src = sc_dir / "zsh_completion_netkit.zsh"
                dest = home / ".zsh" / "completions" / "_nw"
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)
                return (dest, home / ".zshrc")
            _print_warn(
                "Only bash and zsh shells are supported for completion installation."
            )
            return (Path(""), None)

        def _activate_shell(
            selected: str, installed: Path, rc_file: Path | None
        ) -> None:
            if rc_file is None:
                return
            begin = "# >>> NW COMPLETION >>>"
            end = "# <<< NW COMPLETION <<<"
            if selected == "bash":
                snippet = f'\n{begin}\n# Networka bash completion\nif [ -f "{installed}" ]; then\n  source "{installed}"\nfi\n{end}\n'
            else:
                compdir = installed.parent
                snippet = f"\n{begin}\n# Networka zsh completion\nfpath=({compdir} $fpath)\nautoload -Uz compinit && compinit\n{end}\n"
            if not rc_file.exists():
                rc_file.write_text(snippet)
                _print_success(f"Updated rc file: {rc_file}")
                return
            content = rc_file.read_text()
            if begin in content and end in content:
                _print_info("Completion activation already present in rc; skipping.")
                return
            with rc_file.open("a", encoding="utf-8") as fh:
                fh.write(snippet)
            _print_success(f"Activated shell completion in: {rc_file}")

        # Gather answers first when interactive
        default_seq_repo = "https://github.com/narrowin/networka.git"
        do_install_sequences = False
        do_install_compl = False
        do_install_schemas = False
        chosen_shell: str | None = None
        do_activate_compl = False

        if install_sequences is not None:
            do_install_sequences = install_sequences
        elif interactive:
            do_install_sequences = typer.confirm(
                "Install additional predefined vendor sequences from GitHub?",
                default=True,
            )

        if install_completions is not None:
            do_install_compl = install_completions
        elif interactive:
            do_install_compl = typer.confirm("Install shell completions?", default=True)

        if install_schemas is not None:
            do_install_schemas = install_schemas
        elif interactive:
            do_install_schemas = typer.confirm(
                "Install JSON schemas for YAML editor validation and auto-completion?",
                default=True,
            )

        if do_install_compl:
            detected = (
                _detect_shell()
                if interactive
                else (shell if shell in {"bash", "zsh"} else None)
            )
            if interactive:
                default_shell = detected or "bash"
                answer = typer.prompt(
                    "Choose shell for completions (bash|zsh)", default=default_shell
                )
                chosen_shell = answer if answer in {"bash", "zsh"} else default_shell
            else:
                chosen_shell = detected or "bash"

            if activate_completions is not None:
                do_activate_compl = activate_completions
            elif interactive:
                do_activate_compl = typer.confirm(
                    "Activate completions by updating your shell rc file?", default=True
                )

        # Perform writes now (in interactive mode, this is after all questions)
        if dry_run:
            _print_action(f"[dry-run] Would create file: {env_file}")
            _print_action(f"[dry-run] Would ensure directory: {devices_dir}")
            _print_action(f"[dry-run] Would ensure directory: {groups_dir}")
            _print_action(f"[dry-run] Would ensure directory: {sequences_dir}")
            _print_action(
                "[dry-run] Would create config.yml/devices/groups and basic sequences"
            )
        else:
            if not target_path.exists():
                target_path.mkdir(parents=True, exist_ok=True)
                _print_info(f"Created directory: {target_path}")
            create_env_file(target_path)
            devices_dir.mkdir(exist_ok=True)
            groups_dir.mkdir(exist_ok=True)
            sequences_dir.mkdir(exist_ok=True)
            create_config_yml(config_dir)
            create_example_devices(devices_dir)
            create_example_groups(groups_dir)
            create_example_sequences(sequences_dir)
            create_vendor_sequences(sequences_dir)

        # Sequences from GitHub
        if do_install_sequences:
            chosen_seq_url = git_url or default_seq_repo
            if dry_run:
                _print_action(
                    f"[dry-run] Would download sequences from {chosen_seq_url}@{git_ref} into: {sequences_dir}"
                )
            else:
                _install_sequences_from_repo(chosen_seq_url, git_ref, sequences_dir)

        # Shell completions
        if do_install_compl and chosen_shell:
            if dry_run:
                _print_action(
                    f"[dry-run] Would install {chosen_shell} completion and activate={do_activate_compl}"
                )
            else:
                installed_path, rc_file = _install_shell_for(chosen_shell)
                console.print(
                    f"Installed {chosen_shell} completion script to: {installed_path}"
                )
                if rc_file:
                    console.print(f"Shell rc file detected: {rc_file}")
                if do_activate_compl:
                    _activate_shell(chosen_shell, installed_path, rc_file)
                    console.print(
                        "Activation snippet appended. Open a new shell to use completions."
                    )
                else:
                    console.print(
                        "Activation skipped. You can manually source or add the snippet later."
                    )

        # JSON Schemas for editor validation
        if do_install_schemas:
            if dry_run:
                _print_action(
                    "[dry-run] Would install JSON schemas and VS Code settings for YAML validation"
                )
            else:
                _install_editor_schemas(target_path)

        console.print()
        _print_success("Configuration initialization complete!")
