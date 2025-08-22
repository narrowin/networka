# SPDX-License-Identifier: MIT
"""Tests for the tmux-based SSH command."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from network_toolkit.cli import app


class FakePane:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send_keys(self, cmd: str, *, enter: bool = False) -> None:
        self.sent.append(cmd)


class FakeWindow:
    def __init__(self) -> None:
        self._panes: list[FakePane] = [FakePane()]
        self.name = "nw"

    @property
    def panes(self) -> list[FakePane]:
        return self._panes

    @property
    def attached_pane(self) -> FakePane:
        return self._panes[0]

    @property
    def active_pane(self) -> FakePane:
        return self._panes[0]

    def split_window(
        self, *, attach: bool = False, vertical: bool | None = None
    ) -> FakePane:
        _ = (attach, vertical)
        p = FakePane()
        self._panes.append(p)
        return p

    def select_layout(self, layout: str) -> None:
        return None

    def set_option(self, name: str, value: Any) -> None:
        return None

    def rename_window(self, name: str) -> None:
        self.name = name


class FakeSession:
    def __init__(self, name: str) -> None:
        self.name = name
        self._window = FakeWindow()

    @property
    def attached_window(self) -> FakeWindow:
        return self._window

    @property
    def active_window(self) -> FakeWindow:
        return self._window

    def new_window(
        self, *, _attach: bool = True, _window_name: str | None = None
    ) -> FakeWindow:
        self._window = FakeWindow()
        return self._window

    def attach_session(self) -> None:
        """Mock session attach - does nothing in tests."""
        pass


class FakeServer:
    def __init__(self) -> None:
        self.sessions: dict[str, FakeSession] = {}
        # expose last server instance for assertions
        FakeLibtmux.last_server = self

    def find_where(self, query: dict[str, str]) -> FakeSession | None:
        name = query.get("session_name", "")
        return self.sessions.get(name)

    def new_session(self, session_name: str, attach: bool = False) -> FakeSession:  # noqa: FBT001, FBT002
        _ = attach
        s = FakeSession(session_name)
        self.sessions[session_name] = s
        return s


class FakeLibtmux:
    Server = FakeServer
    last_server: FakeServer | None = None


class FakePlatformCapabilities:
    """Mock platform capabilities that always supports tmux."""

    def get_fallback_options(self) -> dict[str, Any]:
        return {
            "tmux_available": True,
            "ssh_client": "openssh_unix",
            "sshpass_available": True,
            "platform": "Linux",
            "can_do_sequential_ssh": True,
            "can_do_tmux_fanout": True,
        }

    def suggest_alternatives(self) -> None:
        pass


class FakePlatformCapabilitiesNoSshpass:
    """Mock platform capabilities that supports tmux but no sshpass."""

    def get_fallback_options(self) -> dict[str, Any]:
        return {
            "tmux_available": True,
            "ssh_client": "openssh_unix",
            "sshpass_available": False,  # No sshpass
            "platform": "Linux",
            "can_do_sequential_ssh": True,
            "can_do_tmux_fanout": True,
        }

    def suggest_alternatives(self) -> None:
        pass


def _patch_tmux_env() -> tuple[Any, Any, Any]:
    return (
        patch(
            "network_toolkit.commands.ssh.shutil.which",
            return_value="/usr/bin/tmux",
        ),
        patch(
            "network_toolkit.commands.ssh._ensure_libtmux",
            return_value=FakeLibtmux,
        ),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilities(),
        ),
    )


def test_ssh_device_opens_session(config_file: Path) -> None:
    runner = CliRunner()
    with (
        _patch_tmux_env()[0] as p1,
        _patch_tmux_env()[1] as p2,
        _patch_tmux_env()[2] as p3,
    ):
        _ = (p1, p2, p3)
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--no-attach",
                "--no-sync",
            ],
        )
    assert result.exit_code == 0
    assert "Created tmux session" in result.output
    assert "1 pane(s)" in result.output


def test_ssh_group_two_panes(config_file: Path) -> None:
    runner = CliRunner()
    with _patch_tmux_env()[0], _patch_tmux_env()[1], _patch_tmux_env()[2]:
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "lab_devices",
                "--layout",
                "even-vertical",
                "--no-attach",
            ],
        )
    assert result.exit_code == 0
    assert "2 pane(s)" in result.output


def test_ssh_missing_tmux_server(config_file: Path) -> None:
    """Test when libtmux cannot connect to tmux server."""
    runner = CliRunner()

    def mock_ensure_libtmux() -> None:
        msg = "Cannot connect to tmux server. Please ensure tmux is installed."
        raise RuntimeError(msg)

    with patch(
        "network_toolkit.commands.ssh._ensure_libtmux", side_effect=mock_ensure_libtmux
    ):
        result = runner.invoke(
            app, ["ssh", "--config", str(config_file), "test_device1", "--no-attach"]
        )
    assert result.exit_code == 1
    assert "Cannot connect to tmux server" in result.output


def _which_side_effect(prog: str) -> str | None:
    if prog == "tmux":
        return "/usr/bin/tmux"
    if prog == "sshpass":
        return "/usr/bin/sshpass"
    return None


def test_auth_key_first_uses_ssh_with_password_fallback(config_file: Path) -> None:
    runner = CliRunner()
    with (
        patch(
            "network_toolkit.commands.ssh.shutil.which", side_effect=_which_side_effect
        ),
        patch("network_toolkit.commands.ssh._ensure_libtmux", return_value=FakeLibtmux),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilities(),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--no-attach",
            ],
        )
    assert result.exit_code == 0
    server = FakeLibtmux.last_server
    assert server is not None
    # Only one session created
    assert len(server.sessions) == 1
    sess = next(iter(server.sessions.values()))
    panes = sess.attached_window.panes
    assert len(panes) >= 1
    sent = panes[0].sent[0]
    # With password present and sshpass available, key-first uses sshpass to allow auto password
    assert sent.startswith("sshpass -f ")
    assert "admin@192.168.1.10" in sent
    assert "PreferredAuthentications=publickey,password" in sent
    assert "PasswordAuthentication=yes" in sent


def test_auth_key_forced_ignores_sshpass(config_file: Path) -> None:
    runner = CliRunner()

    # sshpass missing should not error when --auth key
    def _which_no_sshpass(prog: str) -> str | None:
        return "/usr/bin/tmux" if prog == "tmux" else None

    with (
        patch(
            "network_toolkit.commands.ssh.shutil.which",
            side_effect=_which_no_sshpass,
        ),
        patch(
            "network_toolkit.commands.ssh._ensure_libtmux",
            return_value=FakeLibtmux,
        ),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilities(),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--auth",
                "key",
                "--no-attach",
            ],
        )
    assert result.exit_code == 0
    assert FakeLibtmux.last_server is not None
    key = next(iter(FakeLibtmux.last_server.sessions))
    sent = FakeLibtmux.last_server.sessions[key].attached_window.panes[0].sent[0]
    assert sent.startswith("ssh ")
    assert "sshpass" not in sent


def test_auth_password_requires_sshpass_missing_errors(config_file: Path) -> None:
    runner = CliRunner()

    def _which_tmux_only(prog: str) -> str | None:
        return "/usr/bin/tmux" if prog == "tmux" else None

    with (
        patch(
            "network_toolkit.commands.ssh.shutil.which",
            side_effect=_which_tmux_only,
        ),
        patch(
            "network_toolkit.commands.ssh._ensure_libtmux",
            return_value=FakeLibtmux,
        ),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilitiesNoSshpass(),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--auth",
                "password",
                "--no-attach",
            ],
        )
    assert result.exit_code == 1
    assert "sshpass is required" in result.output


def test_user_password_overrides_use_ssh_with_key_first(config_file: Path) -> None:
    runner = CliRunner()
    with (
        patch(
            "network_toolkit.commands.ssh.shutil.which",
            side_effect=_which_side_effect,
        ),
        patch(
            "network_toolkit.commands.ssh._ensure_libtmux",
            return_value=FakeLibtmux,
        ),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilities(),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--user",
                "other",
                "--password",
                "p123",
                "--no-attach",
            ],
        )
    assert result.exit_code == 0
    assert FakeLibtmux.last_server is not None
    key = next(iter(FakeLibtmux.last_server.sessions))
    sent = FakeLibtmux.last_server.sessions[key].attached_window.panes[0].sent[0]
    # Should use sshpass (-f FIFO) with key-first authentication preference when password is provided
    assert sent.startswith("sshpass -f ")
    assert " ssh " in sent
    assert "other@192.168.1.10" in sent
    assert "PreferredAuthentications=publickey,password" in sent
    assert "PasswordAuthentication=yes" in sent


def test_auth_interactive_no_sshpass(config_file: Path) -> None:
    runner = CliRunner()

    def _which_tmux_only2(prog: str) -> str | None:
        return "/usr/bin/tmux" if prog == "tmux" else None

    with (
        patch(
            "network_toolkit.commands.ssh.shutil.which",
            side_effect=_which_tmux_only2,
        ),
        patch(
            "network_toolkit.commands.ssh._ensure_libtmux",
            return_value=FakeLibtmux,
        ),
        patch(
            "network_toolkit.commands.ssh.get_platform_capabilities",
            return_value=FakePlatformCapabilities(),
        ),
    ):
        result = runner.invoke(
            app,
            [
                "ssh",
                "--config",
                str(config_file),
                "test_device1",
                "--auth",
                "interactive",
                "--no-attach",
            ],
        )
    assert result.exit_code == 0
    assert FakeLibtmux.last_server is not None
    key = next(iter(FakeLibtmux.last_server.sessions))
    sent = FakeLibtmux.last_server.sessions[key].attached_window.panes[0].sent[0]
    assert sent.startswith("ssh ")
    assert "sshpass" not in sent
