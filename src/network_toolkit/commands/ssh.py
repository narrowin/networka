"""tmux-powered SSH fanout command.

This command opens a tmux session/window with panes for one or more devices and
starts interactive SSH clients in each pane. It aims to be lean and simple,
relying on the user's SSH setup (keys/agent). Optionally it can enable
"synchronize-panes" so a single keyboard input is sent to all panes.

Design goals:
- No persistence beyond tmux session; no extra daemons.
- Avoid handling passwords; prefer SSH keys. Optionally use sshpass.
- Minimal, readable code using libtmux.
"""

from __future__ import annotations

# Standard library imports
import datetime
import os
import shlex
import shutil
import tempfile
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

# Third-party imports
import typer

# Local application imports
from network_toolkit.commands.ssh_fallback import open_sequential_ssh_sessions
from network_toolkit.commands.ssh_platform import get_platform_capabilities
from network_toolkit.common.command_helpers import CommandContext
from network_toolkit.common.defaults import DEFAULT_CONFIG_PATH
from network_toolkit.common.logging import setup_logging
from network_toolkit.common.output import OutputMode
from network_toolkit.common.resolver import DeviceResolver
from network_toolkit.config import NetworkConfig, load_config
from network_toolkit.exceptions import NetworkToolkitError
from network_toolkit.ip_device import (
    create_ip_based_config,
    extract_ips_from_target,
    get_supported_platforms,
    is_ip_list,
)

app_help = (
    "Open tmux with CLI panes for a device or group.\n\n"
    "Requires tmux installed and available on PATH; without tmux the command "
    "falls back to sequential SSH sessions.\n\n"
    "Synchronized typing is ENABLED by default - keystrokes go to all panes.\n"
    "Use --no-sync to disable at startup.\n\n"
    "Quick controls:\n"
    "- Ctrl+b, z: Zoom/unzoom focused pane (exits/enters sync mode)\n"
    "- Ctrl+b + Arrow keys: Navigate panes\n"
    "- Click any pane to focus it\n"
    "- Ctrl+b, d: Detach session\n\n"
    "When sync is on, all panes show red borders."
)


LAYOUT_CHOICES = (
    "tiled",
    "even-horizontal",
    "even-vertical",
    "main-horizontal",
    "main-vertical",
)


@dataclass
class Target:
    name: str
    devices: list[str]


def _ensure_libtmux() -> Any:
    """Ensure libtmux is available and can connect to tmux server."""
    try:
        import libtmux
    except Exception as e:  # pragma: no cover - simple import guard
        msg = (
            "libtmux is required for this command. Install with 'uv add libtmux' or "
            "'pip install libtmux'."
        )
        raise RuntimeError(msg) from e

    # Test if we can connect to tmux server (will start one if needed)
    try:
        server = libtmux.Server()
        # This will fail if tmux is not installed or cannot start
        _ = server.sessions
    except Exception as e:
        msg = (
            "Cannot connect to tmux server. Please ensure tmux is installed.\n"
            "Install with: apt install tmux (Linux), brew install tmux (macOS), "
            "or use WSL on Windows."
        )
        raise RuntimeError(msg) from e

    return libtmux


def _resolve_targets(
    config: NetworkConfig,
    targets: str,
    ctx: CommandContext,
    platform: str | None = None,
    port: int | None = None,
    transport_type: str | None = None,
) -> Target:
    """Resolve comma-separated targets to a list of devices."""
    resolver = DeviceResolver(
        config, platform=platform, port=port, transport_type=transport_type
    )
    devices, unknowns = resolver.resolve_targets(targets)

    if unknowns:
        # Be tolerant and warn about unknowns but continue
        unknowns_str = ", ".join(unknowns)
        ctx.print_warning(f"Unknown targets: {unknowns_str}")

    if not devices:
        msg = f"No valid devices found in targets: {targets}"
        raise NetworkToolkitError(
            msg,
            details={"targets": targets, "unknowns": unknowns},
        )

    return Target(name=targets, devices=devices)


class AuthMode(str, Enum):
    KEY_FIRST = "key-first"  # try keys first, fallback to password
    KEY = "key"  # prefer keys/agent only
    PASSWORD = "password"  # use sshpass only
    INTERACTIVE = "interactive"  # let ssh prompt per-pane


def _secure_tmpdir() -> Path:
    """Return a secure, user-only temp directory for transient secrets.

    Prefers XDG_RUNTIME_DIR (0700 tmpfs) else ~/.cache/networka/sshpass (0700),
    else a namespaced dir under system temp (0700).
    """
    xdg = os.environ.get("XDG_RUNTIME_DIR")
    if xdg:
        p = Path(xdg) / "networka"
    else:
        p = Path.home() / ".cache" / "networka" / "sshpass"
    try:
        p.mkdir(parents=True, exist_ok=True)
        p.chmod(0o700)
    except Exception:
        p = Path(tempfile.gettempdir()) / "networka_sshpass"
        p.mkdir(parents=True, exist_ok=True)
        try:
            p.chmod(0o700)
        except Exception:
            pass
    return p


def _prepare_sshpass_fifo(password: str) -> str:
    """Create a secure FIFO and start a writer thread to feed sshpass.

    No plaintext is stored at rest; the FIFO node is removed after writing.
    Returns the FIFO path.
    """
    dirpath = _secure_tmpdir()
    ts_ms = int(datetime.datetime.now(tz=datetime.UTC).timestamp() * 1000)
    fifo_path = dirpath / f"pw_{os.getpid()}_{ts_ms}.fifo"
    try:
        os.mkfifo(fifo_path, 0o600)
    except FileExistsError:
        ts_ms += 1
        fifo_path = dirpath / f"pw_{os.getpid()}_{ts_ms}.fifo"
        os.mkfifo(fifo_path, 0o600)

    def _writer() -> None:
        try:
            with open(fifo_path, "w", encoding="utf-8", buffering=1) as f:
                f.write(password)
        except Exception:
            pass
        finally:
            try:
                os.remove(fifo_path)
            except Exception:
                pass

    threading.Thread(target=_writer, daemon=True).start()
    return str(fifo_path)


def _build_ssh_cmd(
    *,
    host: str,
    user: str,
    port: int = 22,
    auth: AuthMode = AuthMode.KEY_FIRST,
    password: str | None = None,
    strict_host_key_checking: bool = False,
    ctx: CommandContext,
) -> str:
    # Determine StrictHostKeyChecking value and related options
    # Default: accept-new (accept new keys, verify existing ones)
    # With --no-strict-host-key-checking: completely disable all verification
    base = [
        "ssh",
        "-p",
        str(port),
        "-o",
        f"StrictHostKeyChecking={'accept-new' if strict_host_key_checking else 'no'}",
    ]

    # When fully disabling strict checking, also disable known_hosts to prevent any errors
    if not strict_host_key_checking:
        base.extend(
            [
                "-o",
                "UserKnownHostsFile=/dev/null",
                "-o",
                "GlobalKnownHostsFile=/dev/null",
            ]
        )

    # Add authentication options
    base.extend(
        [
            "-o",
            "PreferredAuthentications=publickey,password",
            "-o",
            "PasswordAuthentication=yes",
            f"{user}@{host}",
        ]
    )

    if auth == AuthMode.PASSWORD:
        if not password:
            msg = (
                "No password available for password auth. Set --password or "
                "use env/config credentials."
            )
            raise NetworkToolkitError(msg)
        # Use sshpass reading from a secure FIFO to avoid env/cmdline/plain files
        if not shutil.which("sshpass"):
            msg = (
                "sshpass is required for password authentication but was not found.\n"
                "Install it with: sudo apt install sshpass (Ubuntu/Debian) or "
                "brew install hudochenkov/sshpass/sshpass (macOS)"
            )
            raise NetworkToolkitError(msg)
        fifo = _prepare_sshpass_fifo(password)
        sshpass_cmd = f"sshpass -f {shlex.quote(fifo)} "
        return sshpass_cmd + " ".join(shlex.quote(p) for p in base)

    if auth == AuthMode.KEY_FIRST and password:
        # For key-first mode with password available, use sshpass if available
        if shutil.which("sshpass"):
            fifo = _prepare_sshpass_fifo(password)
            sshpass_cmd = f"sshpass -f {shlex.quote(fifo)} "
            return sshpass_cmd + " ".join(shlex.quote(p) for p in base)
        else:
            # If sshpass not available, provide helpful message
            ctx.print_warning(
                "sshpass not found. SSH will prompt for password interactively."
            )
            ctx.print_info(
                "To automate password entry, install sshpass: "
                "sudo apt install sshpass (Ubuntu/Debian) or "
                "brew install hudochenkov/sshpass/sshpass (macOS)"
            )

    return " ".join(shlex.quote(p) for p in base)


def _session_name(default_base: str) -> str:
    ts = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")
    base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in default_base)
    return f"nw_{base}_{ts}"


def _sanitize_session_name(name: str) -> str:
    """Allow only safe characters in session name used for tmux attach."""
    return "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name)


def register(app: typer.Typer) -> None:
    @app.command(
        "cli",
        help=app_help,
        rich_help_panel="Remote Operations",
        context_settings={"help_option_names": ["-h", "--help"]},
    )
    def cli(
        target: Annotated[
            str,
            typer.Argument(help="Comma-separated device/group names or IP addresses"),
        ],
        *,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Path to config dir or YAML")
        ] = DEFAULT_CONFIG_PATH,
        auth: Annotated[
            AuthMode,
            typer.Option(
                "--auth",
                help=(
                    "Authentication mode: key-first (default), key, "
                    "password, interactive"
                ),
                case_sensitive=False,
            ),
        ] = AuthMode.KEY_FIRST,
        user_override: Annotated[
            str | None, typer.Option("--user", help="Override username for SSH")
        ] = None,
        password_override: Annotated[
            str | None, typer.Option("--password", help="Override password for SSH")
        ] = None,
        layout: Annotated[
            str,
            typer.Option(
                "--layout",
                case_sensitive=False,
                help=f"tmux layout to use: {', '.join(LAYOUT_CHOICES)}",
            ),
        ] = "tiled",
        session_name: Annotated[
            str | None, typer.Option("--session-name", help="Custom session name")
        ] = None,
        window_name: Annotated[
            str | None, typer.Option("--window-name", help="Custom window name")
        ] = None,
        sync: Annotated[
            bool,
            typer.Option(
                "--sync/--no-sync", help="Enable synchronized typing (default: on)"
            ),
        ] = True,
        use_sshpass: Annotated[
            bool,
            typer.Option(
                "--use-sshpass",
                help="Use sshpass (same as --auth password)",
            ),
        ] = False,
        attach: Annotated[
            bool, typer.Option("--attach/--no-attach", help="Attach after creating")
        ] = True,
        verbose: Annotated[
            bool, typer.Option("--verbose", "-v", help="Enable debug logging")
        ] = False,
        device_type: Annotated[
            str | None,
            typer.Option(
                "--platform",
                "-p",
                help="Device type when using IP addresses (e.g., mikrotik_routeros). Note: This specifies the network driver type, not hardware platform.",
            ),
        ] = None,
        port: Annotated[
            int | None,
            typer.Option(
                "--port",
                help="SSH port when using IP addresses (default: 22)",
            ),
        ] = None,
        transport_type: Annotated[
            str | None,
            typer.Option(
                "--transport",
                "-t",
                help="Transport type for connections (currently only scrapli is supported). Defaults to configuration or scrapli.",
            ),
        ] = None,
        no_strict_host_key_checking: Annotated[
            bool,
            typer.Option(
                "--no-strict-host-key-checking",
                help="Disable strict SSH host key checking (insecure, use only in lab environments)",
            ),
        ] = False,
    ) -> None:
        """
        Open a tmux window with CLI panes for devices in targets.

        Supports comma-separated device and group names.

        Examples:
        - nw cli sw-acc1
        - nw cli sw-acc1,sw-acc2
        - nw cli access_switches
        - nw cli sw-acc1,access_switches
        """

        setup_logging("DEBUG" if verbose else "WARNING")

        # Create command context for centralized output management
        ctx = CommandContext(
            output_mode=OutputMode.DEFAULT, verbose=verbose, config_file=config_file
        )

        # Validate transport type if provided
        if transport_type is not None:
            from network_toolkit.transport.factory import get_transport_factory

            try:
                # This will raise ValueError if transport_type is invalid
                get_transport_factory(transport_type)
            except ValueError as e:
                ctx.print_error(str(e))
                raise typer.Exit(1) from e

        try:
            libtmux = _ensure_libtmux()
        except Exception as e:  # pragma: no cover - trivial failures
            ctx.print_error(str(e))
            raise typer.Exit(1) from None

        try:
            config = load_config(config_file)

            # Handle IP addresses if platform is provided
            if is_ip_list(target):
                if device_type is None:
                    supported_platforms = get_supported_platforms()
                    platform_list = "\n".join(
                        [f"  {k}: {v}" for k, v in supported_platforms.items()]
                    )
                    ctx.print_error("When using IP addresses, --platform is required")
                    ctx.print_warning(f"Supported platforms:\n{platform_list}")
                    raise typer.Exit(1)

                ips = extract_ips_from_target(target)
                config = create_ip_based_config(
                    ips, device_type, config, port=port, transport_type=transport_type
                )
                ctx.print_info(
                    f"Using IP addresses with platform '{device_type}': {', '.join(ips)}"
                )

            # Use the helper function that properly handles unknown targets
            tgt = _resolve_targets(
                config,
                target,
                ctx,
                platform=device_type,
                port=port,
                transport_type=transport_type,
            )

            # Check platform capabilities after we have config and targets
            platform_caps = get_platform_capabilities()
            capabilities = platform_caps.get_fallback_options()

            if not capabilities["can_do_tmux_fanout"]:
                ctx.print_warning(
                    "tmux-based SSH fanout not available on this platform."
                )

                if not capabilities["tmux_available"]:
                    ctx.print_warning("Reason: tmux not available")
                    platform_caps.suggest_alternatives()

                if capabilities["can_do_sequential_ssh"]:
                    ctx.print_info("Falling back to sequential SSH connections...")
                    # Use fallback implementation
                    open_sequential_ssh_sessions(tgt.devices, config)
                    return
                else:
                    ctx.print_error("No SSH client available")
                    platform_caps.suggest_alternatives()
                    raise typer.Exit(1)
        except Exception as e:
            ctx.print_error(f"Failed to load config or resolve target: {e}")
            raise typer.Exit(1) from None

        # Resolve effective auth mode with legacy flag support
        effective_auth = auth

        # Prepare connection params and SSH commands per device
        device_cmds: list[tuple[str, str]] = []  # (device_name, ssh_cmd)
        for dev in tgt.devices:
            params = config.get_device_connection_params(
                dev, user_override, password_override
            )
            try:
                # Determine credentials
                user = str(params.get("auth_username"))
                host = str(params.get("host"))
                port = int(params.get("port", 22))
                pw = params.get("auth_password")

                # Decide auth mode if KEY_FIRST or legacy flag set
                mode = effective_auth
                if mode == AuthMode.KEY_FIRST:
                    # For KEY_FIRST, we use SSH native fallback behavior
                    # SSH will try keys first, then prompt for password if available
                    mode = AuthMode.KEY_FIRST
                if use_sshpass:
                    mode = AuthMode.PASSWORD

                # Note: We no longer strictly require sshpass since we have pexpect fallback

                ssh_cmd = _build_ssh_cmd(
                    host=host,
                    user=user,
                    port=port,
                    auth=mode,
                    password=str(pw) if pw is not None else None,
                    strict_host_key_checking=not no_strict_host_key_checking,
                    ctx=ctx,
                )
            except Exception as e:
                ctx.print_error(f"Skipping {dev}: {e}")
                continue
            device_cmds.append((dev, ssh_cmd))

        if not device_cmds:
            ctx.print_error("No valid devices to connect to.")
            raise typer.Exit(1)

        # Always create a new tmux session for clean behavior
        server = libtmux.Server()
        sname = session_name or _session_name(tgt.name)
        sname = _sanitize_session_name(sname)

        # Always create a new unique session name to avoid conflicts
        sname = _sanitize_session_name(_session_name(tgt.name))
        session = server.new_session(session_name=sname, attach=False)

        wname = window_name or tgt.name
        window = session.active_window
        if wname != window.name:
            try:
                window.rename_window(wname)
            except Exception as exc:  # pragma: no cover - rename failure is non-fatal
                ctx.console.log(f"Could not rename tmux window: {exc}")

        # Ensure we start with a single pane
        # Create panes for each device
        panes: list[Any] = []
        if not window.panes:
            pane0 = window.split_window(attach=False)
            panes.append(pane0)
        else:
            panes.append(window.active_pane)

        for idx in range(1, len(device_cmds)):
            vertical = idx % 2 == 1
            panes.append(window.split_window(attach=False, vertical=vertical))

        # Apply layout
        if layout in LAYOUT_CHOICES:
            window.select_layout(layout)

        # Send ssh commands to all panes first
        for (dev_name, cmd), pane in zip(device_cmds, window.panes, strict=True):
            _ = dev_name  # name not used but kept for future labels
            pane.send_keys(cmd, enter=True)

        # Simple sync setup using direct tmux commands
        if sync:
            try:
                window.cmd("set-window-option", "synchronize-panes", "on")
            except Exception as exc:
                ctx.console.log(f"Could not enable sync: {exc}")

        # Enable mouse support using direct command
        try:
            session.cmd("set-option", "mouse", "on")
        except Exception as exc:
            ctx.console.log(f"Could not enable mouse: {exc}")

        ctx.print_success("Created tmux session")
        ctx.print_info(f"Session: {sname} with {len(device_cmds)} pane(s).")
        ctx.print_info("Use tmux to navigate. Press Ctrl-b d to detach.")

        if attach:
            # Use libtmux to attach directly instead of subprocess
            try:
                # Attach using libtmux server
                session.attach_session()
            except Exception:
                ctx.print_warning(
                    f"Failed to attach automatically. Run: tmux attach -t {sname}"
                )
