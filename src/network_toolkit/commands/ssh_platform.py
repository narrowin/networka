"""Cross-platform SSH command support."""

from __future__ import annotations

import platform
import shutil
from typing import Any

from network_toolkit.common.command_helpers import CommandContext


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
            # First check if tmux binary exists
            if not shutil.which("tmux"):
                self._tmux_available = False
                return self._tmux_available

            # Then check if we can import and use libtmux
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

    def suggest_alternatives(self, ctx: CommandContext | None = None) -> None:
        """Print platform-specific installation suggestions."""
        if ctx is None:
            # Temporary fallback for non-converted code
            ctx = CommandContext()

        if not self.supports_tmux:
            if self.system == "Windows":
                ctx.print_warning("tmux not available on Windows. Consider:")
                ctx.output_manager.print_text("• Install WSL2 and use: wsl -d Ubuntu")
                ctx.output_manager.print_text(
                    "• Use Windows Terminal with multiple tabs"
                )
                ctx.output_manager.print_text(
                    "• Use ConEmu or similar terminal multiplexer"
                )
            else:
                ctx.print_warning("tmux not found. Install with:")
                if self.system == "Darwin":
                    ctx.output_manager.print_text("• brew install tmux")
                else:
                    ctx.output_manager.print_text("• apt install tmux (Ubuntu/Debian)")
                    ctx.output_manager.print_text("• yum install tmux (RHEL/CentOS)")

        if self.ssh_client_type == "none":
            if self.system == "Windows":
                ctx.print_warning("No SSH client found. Install:")
                ctx.output_manager.print_text(
                    "• Windows OpenSSH: Settings > Apps > Optional Features"
                )
                ctx.output_manager.print_text("• PuTTY: https://www.putty.org/")
                ctx.output_manager.print_text("• Git Bash (includes OpenSSH)")
            else:
                ctx.print_warning("SSH client not found. Install openssh-client")


# Global instance
_platform_capabilities: PlatformCapabilities | None = None


def get_platform_capabilities() -> PlatformCapabilities:
    """Get platform capabilities singleton."""
    # Use module-level variable instead of global statement
    if _platform_capabilities is None:
        globals()["_platform_capabilities"] = PlatformCapabilities()
    # At this point, we know _platform_capabilities is not None
    assert _platform_capabilities is not None
    return _platform_capabilities
