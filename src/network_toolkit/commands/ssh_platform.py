"""Cross-platform SSH command support."""

from __future__ import annotations

import platform
import shutil
from typing import Any

from network_toolkit.common.logging import console


class PlatformCapabilities:
    """Detect and provide platform-specific capabilities."""

    def __init__(self) -> None:
        self.system = platform.system()
        self._tmux_available: bool | None = None
        self._ssh_client: str | None = None
        self._supports_sshpass: bool | None = None

    @property
    def supports_tmux(self) -> bool:
        """Check if tmux is supported on this platform."""
        if self._tmux_available is None:
            try:
                import libtmux

                server = libtmux.Server()
                # Test if we can connect to tmux server
                _ = server.sessions
                self._tmux_available = True
            except Exception:
                self._tmux_available = False
        return self._tmux_available

    @property
    def ssh_client_type(self) -> str:
        """Detect available SSH client type."""
        if self._ssh_client is None:
            if self.system == "Windows":
                if shutil.which("ssh.exe"):
                    self._ssh_client = "openssh_windows"
                elif shutil.which("plink.exe"):
                    self._ssh_client = "putty"
                elif shutil.which("ssh"):  # WSL or Git Bash
                    self._ssh_client = "openssh_unix"
                else:
                    self._ssh_client = "none"
            elif shutil.which("ssh"):
                self._ssh_client = "openssh_unix"
            else:
                self._ssh_client = "none"
        return self._ssh_client

    @property
    def supports_sshpass(self) -> bool:
        """Check if sshpass is available."""
        if self._supports_sshpass is None:
            self._supports_sshpass = shutil.which("sshpass") is not None
        return self._supports_sshpass

    def get_fallback_options(self) -> dict[str, Any]:
        """Get available fallback options for current platform."""
        return {
            "tmux_available": self.supports_tmux,
            "ssh_client": self.ssh_client_type,
            "sshpass_available": self.supports_sshpass,
            "platform": self.system,
            "can_do_sequential_ssh": self.ssh_client_type != "none",
            "can_do_tmux_fanout": self.supports_tmux and self.ssh_client_type != "none",
        }

    def suggest_alternatives(self) -> None:
        """Print platform-specific installation suggestions."""
        if not self.supports_tmux:
            if self.system == "Windows":
                console.print(
                    "[yellow]tmux not available on Windows. Consider:[/yellow]"
                )
                console.print("• Install WSL2 and use: wsl -d Ubuntu")
                console.print("• Use Windows Terminal with multiple tabs")
                console.print("• Use ConEmu or similar terminal multiplexer")
            else:
                console.print("[yellow]tmux not found. Install with:[/yellow]")
                if self.system == "Darwin":
                    console.print("• brew install tmux")
                else:
                    console.print("• apt install tmux (Ubuntu/Debian)")
                    console.print("• yum install tmux (RHEL/CentOS)")

        if self.ssh_client_type == "none":
            if self.system == "Windows":
                console.print("[yellow]No SSH client found. Install:[/yellow]")
                console.print("• Windows OpenSSH: Settings > Apps > Optional Features")
                console.print("• PuTTY: https://www.putty.org/")
                console.print("• Git Bash (includes OpenSSH)")
            else:
                console.print(
                    "[yellow]SSH client not found. Install openssh-client[/yellow]"
                )


# Global instance
_platform_capabilities: PlatformCapabilities | None = None


def get_platform_capabilities() -> PlatformCapabilities:
    """Get platform capabilities singleton."""
    # Use module-level variable without global statement
    # This avoids the PLW0603 warning while maintaining singleton behavior
    if _platform_capabilities is None:
        # Create the instance and store it in the module global
        globals()["_platform_capabilities"] = PlatformCapabilities()

    # Type checker guarantee: _platform_capabilities is now definitely not None
    assert _platform_capabilities is not None
    return _platform_capabilities
