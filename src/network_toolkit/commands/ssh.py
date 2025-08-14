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

import datetime
import shlex
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer

from network_toolkit.commands.ssh_fallback import open_sequential_ssh_sessions
from network_toolkit.commands.ssh_platform import get_platform_capabilities
from network_toolkit.common.logging import console, setup_logging
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
    "Open tmux with SSH panes for a device or group.\n\n"
    "Quick tmux keys (defaults):\n"
    "- Prefix: Ctrl-b\n"
    "- Pane navigation: Prefix + Arrow keys\n"
    '- Split pane: Prefix + % (vertical), Prefix + " (horizontal)\n'
    "- Cycle layouts: Prefix + Space\n"
    "- Synchronize panes: Prefix + : then 'set synchronize-panes on|off'\n"
    "- Detach: Ctrl-b then d\n\n"
    "Tip: Use --sync/--no-sync to control synchronized typing from nw."
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


def _resolve_targets(config: NetworkConfig, targets: str) -> Target:
    """Resolve comma-separated targets to a list of devices."""
    resolver = DeviceResolver(config)
    devices, unknowns = resolver.resolve_targets(targets)

    if unknowns:
        # Be tolerant and warn about unknowns but continue
        unknowns_str = ", ".join(unknowns)
        console.print(f"[yellow]Warning: Unknown targets: {unknowns_str}[/yellow]")

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


def _build_ssh_cmd(
    *,
    host: str,
    user: str,
    port: int = 22,
    auth: AuthMode = AuthMode.KEY_FIRST,
    password: str | None = None,
) -> str:
    base = [
        "ssh",
        "-p",
        str(port),
        "-o",
        "StrictHostKeyChecking=accept-new",
        # Add options to try key auth first, then password
        "-o",
        "PreferredAuthentications=publickey,password",
        "-o",
        "PasswordAuthentication=yes",
        f"{user}@{host}",
    ]

    if auth == AuthMode.PASSWORD:
        if not password:
            msg = (
                "No password available for password auth. Set --password or "
                "use env/config credentials."
            )
            raise NetworkToolkitError(msg)
        # Use SSHPASS environment variable to avoid password in command line/history
        # This requires setting the environment variable before executing the command
        sshpass_cmd = f"SSHPASS={shlex.quote(str(password))} sshpass -e "
        return sshpass_cmd + " ".join(shlex.quote(p) for p in base)

    if auth == AuthMode.KEY_FIRST and password:
        # For key-first mode with password available, we still try keys first
        # but SSH will naturally fall back to password if keys fail
        return " ".join(shlex.quote(p) for p in base)

    return " ".join(shlex.quote(p) for p in base)


def _session_name(default_base: str) -> str:
    ts = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")
    base = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in default_base)
    return f"nw_{base}_{ts}"


def _sanitize_session_name(name: str) -> str:
    """Allow only safe characters in session name used for tmux attach."""
    return "".join(c if (c.isalnum() or c in ("-", "_", ".")) else "_" for c in name)


def register(app: typer.Typer) -> None:
    @app.command("ssh", help=app_help)
    def ssh_fanout(
        target: Annotated[
            str,
            typer.Argument(help="Comma-separated device/group names or IP addresses"),
        ],
        *,
        config_file: Annotated[
            Path, typer.Option("--config", "-c", help="Path to config dir or YAML")
        ] = Path("config"),
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
        reuse: Annotated[
            bool, typer.Option("--reuse", help="Reuse existing session if it exists")
        ] = False,
        sync: Annotated[
            bool,
            typer.Option("--sync/--no-sync", help="Enable tmux synchronize-panes"),
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
        platform: Annotated[
            str | None,
            typer.Option(
                "--platform",
                "-p",
                help="Platform type when using IP addresses (e.g., mikrotik_routeros)",
            ),
        ] = None,
        port: Annotated[
            int | None,
            typer.Option(
                "--port",
                help="SSH port when using IP addresses (default: 22)",
            ),
        ] = None,
    ) -> None:
        """
        Open a tmux window with SSH panes for devices in targets.

        Supports comma-separated device and group names.

        Examples:
        - nw ssh sw-acc1
        - nw ssh sw-acc1,sw-acc2
        - nw ssh access_switches
        - nw ssh sw-acc1,access_switches
        """

        setup_logging("DEBUG" if verbose else "INFO")

        try:
            libtmux = _ensure_libtmux()
        except Exception as e:  # pragma: no cover - trivial failures
            console.print(f"[red]{e}[/red]")
            raise typer.Exit(1) from None

        try:
            config = load_config(config_file)

            # Handle IP addresses if platform is provided
            if is_ip_list(target):
                if platform is None:
                    supported_platforms = get_supported_platforms()
                    platform_list = "\n".join(
                        [f"  {k}: {v}" for k, v in supported_platforms.items()]
                    )
                    console.print(
                        "[red]Error: When using IP addresses, "
                        "--platform is required[/red]\n"
                        f"[yellow]Supported platforms:[/yellow]\n{platform_list}"
                    )
                    raise typer.Exit(1)

                ips = extract_ips_from_target(target)
                config = create_ip_based_config(ips, platform, config, port=port)
                console.print(
                    f"[cyan]Using IP addresses with platform '{platform}': "
                    f"{', '.join(ips)}[/cyan]"
                )

            resolver = DeviceResolver(config, platform, port)
            tgt = Target(name=target, devices=resolver.resolve_targets(target)[0])

            # Check platform capabilities after we have config and targets
            platform_caps = get_platform_capabilities()
            capabilities = platform_caps.get_fallback_options()

            if not capabilities["can_do_tmux_fanout"]:
                console.print(
                    "[yellow]tmux-based SSH fanout not available on this platform.[/yellow]"
                )

                if not capabilities["tmux_available"]:
                    console.print("[yellow]Reason: tmux not available[/yellow]")
                    platform_caps.suggest_alternatives()

                if capabilities["can_do_sequential_ssh"]:
                    console.print(
                        "[cyan]Falling back to sequential SSH connections...[/cyan]"
                    )
                    # Use fallback implementation
                    open_sequential_ssh_sessions(tgt.devices, config)
                    return
                else:
                    console.print("[red]No SSH client available[/red]")
                    platform_caps.suggest_alternatives()
                    raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Failed to load config or resolve target: {e}[/red]")
            raise typer.Exit(1) from None

        # Resolve effective auth mode with legacy flag support
        effective_auth = auth

        # Prepare connection params and SSH commands per device
        device_cmds: list[tuple[str, str]] = []  # (device_name, ssh_cmd)
        sshpass_required = False
        for dev in tgt.devices:
            params = config.get_device_connection_params(dev)
            try:
                # Determine credentials
                user = user_override or str(params.get("auth_username"))
                host = str(params.get("host"))
                port = int(params.get("port", 22))
                pw = password_override or params.get("auth_password")

                # Decide auth mode if KEY_FIRST or legacy flag set
                mode = effective_auth
                if mode == AuthMode.KEY_FIRST:
                    # For KEY_FIRST, we use SSH native fallback behavior
                    # SSH will try keys first, then prompt for password if available
                    mode = AuthMode.KEY_FIRST
                if use_sshpass:
                    mode = AuthMode.PASSWORD
                if mode == AuthMode.PASSWORD:
                    sshpass_required = True

                ssh_cmd = _build_ssh_cmd(
                    host=host,
                    user=user,
                    port=port,
                    auth=mode,
                    password=str(pw) if pw is not None else None,
                )
            except Exception as e:
                console.print(f"[red]Skipping {dev}: {e}[/red]")
                continue
            device_cmds.append((dev, ssh_cmd))

        if not device_cmds:
            console.print("[red]No valid devices to connect to.[/red]")
            raise typer.Exit(1)

        # If any pane needs password mode, ensure sshpass exists
        if sshpass_required and not shutil.which("sshpass"):
            console.print(
                "[red]sshpass is required for password authentication "
                "but was not found.\n"
                "Install it (e.g., apt install sshpass) or use --auth key "
                "/ --auth interactive, or provide SSH keys.[/red]"
            )
            raise typer.Exit(1)

        # Create or reuse tmux session
        server = libtmux.Server()
        sname = session_name or _session_name(tgt.name)
        sname = _sanitize_session_name(sname)

        session = server.find_where({"session_name": sname})
        if session is None:
            session = server.new_session(session_name=sname, attach=False)
        elif not reuse:
            # Create a new unique session to avoid clobber
            sname = _sanitize_session_name(_session_name(tgt.name))
            session = server.new_session(session_name=sname, attach=False)

        wname = window_name or tgt.name
        window = getattr(session, "attached_window", None)
        if window is None:
            window = session.new_window(attach=True, window_name=wname)
        else:
            try:
                window.rename_window(wname)
            except Exception as exc:  # pragma: no cover - rename failure is non-fatal
                console.log(f"Could not rename tmux window: {exc}")

        # Ensure we start with a single pane
        # Create panes for each device
        panes: list[Any] = []
        if not window.panes:
            pane0 = window.split_window(attach=False)
            panes.append(pane0)
        else:
            panes.append(window.attached_pane)

        for idx in range(1, len(device_cmds)):
            vertical = idx % 2 == 1
            panes.append(window.split_window(attach=False, vertical=vertical))

        # Apply layout
        if layout in LAYOUT_CHOICES:
            window.select_layout(layout)

        # Send ssh commands
        for (dev_name, cmd), pane in zip(device_cmds, window.panes, strict=True):
            _ = dev_name  # name not used but kept for future labels
            pane.send_keys(cmd, enter=True)

        # Synchronize panes if requested
        try:
            window.set_option("synchronize-panes", bool(sync))
        except Exception as exc:  # pragma: no cover - non-critical
            console.log(f"Could not set synchronize-panes: {exc}")

        console.print(
            "[green]Created tmux session[/green] "
            f"[bold]{sname}[/bold] with {len(device_cmds)} pane(s)."
        )
        console.print("Use tmux to navigate. Press Ctrl-b d to detach.")

        if attach:
            # Use libtmux to attach directly instead of subprocess
            try:
                # Attach using libtmux server
                session.attach_session()
            except Exception:
                console.print(
                    "[yellow]Failed to attach automatically. "
                    f"Run: tmux attach -t {sname}[/yellow]"
                )
