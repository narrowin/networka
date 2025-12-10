"""Sequential SSH fallback for platforms without tmux."""

from __future__ import annotations

import platform
import shutil
import subprocess
from typing import Any

from network_toolkit.common.output import get_output_manager
from network_toolkit.config import NetworkConfig


def open_sequential_ssh_sessions(
    devices: list[str], config: NetworkConfig, **kwargs: Any
) -> None:
    """Open SSH sessions sequentially when tmux is not available."""
    output_manager = get_output_manager()
    output_manager.print_info(f"Opening {len(devices)} SSH sessions sequentially...")

    system = platform.system()

    for i, device in enumerate(devices, 1):
        output_manager.print_info(f"({i}/{len(devices)}) Connecting to {device}...")

        try:
            params = config.get_device_connection_params(device)
            host = str(params.get("host"))
            user = str(params.get("auth_username", "admin"))
            port = int(params.get("port", 22))

            # Build SSH command based on platform
            ssh_cmd = _build_platform_ssh_command(host, user, port, system)

            if system == "Windows":
                # On Windows, open in new command prompt window
                cmd_args = ["start", "cmd", "/k", *ssh_cmd]
                subprocess.run(cmd_args, shell=False, check=False)
            else:
                # On Unix-like systems, try to open in new terminal window
                terminal_cmd = _get_terminal_command(ssh_cmd)
                if terminal_cmd:
                    subprocess.run(terminal_cmd, check=False)
                else:
                    # Fallback: run SSH directly (will take over current terminal)
                    output_manager.print_warning(
                        f"Opening SSH in current terminal for {device}"
                    )
                    subprocess.run(ssh_cmd, check=False)

        except Exception as e:
            output_manager.print_error(f"Failed to connect to {device}: {e}")


def _build_platform_ssh_command(
    host: str, user: str, port: int, system: str
) -> list[str]:
    """Build SSH command appropriate for the platform."""
    if system == "Windows":
        # Try Windows OpenSSH first, then PuTTY
        if shutil.which("ssh.exe"):
            cmd = ["ssh.exe"]
        elif shutil.which("ssh"):
            cmd = ["ssh"]
        elif shutil.which("plink.exe"):
            # PuTTY plink has different syntax
            return ["plink.exe", "-P", str(port), f"{user}@{host}"]
        else:
            msg = "No SSH client found"
            raise RuntimeError(msg)
    else:
        cmd = ["ssh"]

    # Standard OpenSSH syntax
    if port != 22:
        cmd.extend(["-p", str(port)])

    cmd.extend(["-l", user, host])
    return cmd


def _get_terminal_command(ssh_cmd: list[str]) -> list[str] | None:
    """Get command to open SSH in a new terminal window."""
    # Try common terminal emulators
    terminals = [
        (["gnome-terminal", "--"], "gnome-terminal"),
        (["konsole", "-e"], "konsole"),
        (["xterm", "-e"], "xterm"),
        (["alacritty", "-e"], "alacritty"),
        (["kitty", "-e"], "kitty"),
    ]

    for term_cmd, binary in terminals:
        if shutil.which(binary):
            return term_cmd + ssh_cmd

    return None
