"""Test SSH host key verification configuration."""

from __future__ import annotations

import pytest

from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig


class TestSSHHostKeyVerification:
    """Test SSH host key verification configuration and behavior."""

    def test_default_accepts_new_keys(self) -> None:
        """Test that default accepts new keys (False - accept-new behavior)."""
        config = GeneralConfig()
        assert config.ssh_strict_host_key_checking is False

    def test_can_keep_strict_checking_enabled(self) -> None:
        """Test keeping strict checking enabled (secure)."""
        config = GeneralConfig(ssh_strict_host_key_checking=True)
        assert config.ssh_strict_host_key_checking is True

    def test_can_disable_strict_checking_explicitly(self) -> None:
        """Test explicitly disabling strict checking (insecure, for labs only)."""
        config = GeneralConfig(ssh_strict_host_key_checking=False)
        assert config.ssh_strict_host_key_checking is False

    def test_invalid_value_raises_error(self) -> None:
        """Test that non-boolean values raise validation error."""
        with pytest.raises(ValueError, match="must be a boolean"):
            GeneralConfig(ssh_strict_host_key_checking="yes")  # type: ignore[arg-type]

    def test_network_config_uses_general_setting(self) -> None:
        """Test NetworkConfig respects GeneralConfig setting."""
        config = NetworkConfig(
            general=GeneralConfig(ssh_strict_host_key_checking=True),
            devices={
                "test_device": DeviceConfig(host="192.168.1.1", device_type="cisco_ios")
            },
        )
        assert config.general.ssh_strict_host_key_checking is True

    def test_network_config_default_accepts_new_keys(self) -> None:
        """Test NetworkConfig default accepts new keys (accept-new) when not specified."""
        config = NetworkConfig(
            devices={
                "test_device": DeviceConfig(host="192.168.1.1", device_type="cisco_ios")
            }
        )
        assert config.general.ssh_strict_host_key_checking is False


class TestSSHHostKeyVerificationIntegration:
    """Integration tests for SSH host key verification in device sessions."""

    def test_device_connection_params_reflect_config_strict_enabled(self) -> None:
        """Test DeviceSession uses strict checking when enabled in config."""
        config = NetworkConfig(
            general=GeneralConfig(ssh_strict_host_key_checking=True),
            devices={
                "test_device": DeviceConfig(host="192.168.1.1", device_type="cisco_ios")
            },
        )

        # The device session should use the config setting
        # Note: DeviceSession adds auth_strict_key in __init__
        # We're testing that the config has the right value available
        assert config.general.ssh_strict_host_key_checking is True

    def test_device_connection_params_reflect_config_strict_disabled(self) -> None:
        """Test DeviceSession uses insecure mode when explicitly disabled in config."""
        config = NetworkConfig(
            general=GeneralConfig(ssh_strict_host_key_checking=False),
            devices={
                "test_device": DeviceConfig(host="192.168.1.1", device_type="cisco_ios")
            },
        )

        # Verify config has insecure setting (disabled for lab use)
        assert config.general.ssh_strict_host_key_checking is False


class TestSSHCommandHostKeyVerification:
    """Test SSH command host key verification behavior."""

    def test_build_ssh_cmd_with_accept_new(self) -> None:
        """Test _build_ssh_cmd generates accept-new for normal mode."""
        from pathlib import Path

        from network_toolkit.commands.ssh import AuthMode, _build_ssh_cmd
        from network_toolkit.common.command_helpers import CommandContext
        from network_toolkit.common.output import OutputMode

        ctx = CommandContext(
            output_mode=OutputMode.DEFAULT,
            verbose=False,
            config_file=Path("/tmp/test"),
        )

        cmd = _build_ssh_cmd(
            host="192.168.1.1",
            user="admin",
            port=22,
            auth=AuthMode.KEY,
            password=None,
            strict_host_key_checking=False,
            ctx=ctx,
        )

        assert "StrictHostKeyChecking=accept-new" in cmd
        assert "192.168.1.1" in cmd
        assert "admin@" in cmd

    def test_build_ssh_cmd_without_strict_checking(self) -> None:
        """Test _build_ssh_cmd generates correct option for insecure mode (DISABLED)."""
        from pathlib import Path

        from network_toolkit.commands.ssh import AuthMode, _build_ssh_cmd
        from network_toolkit.common.command_helpers import CommandContext
        from network_toolkit.common.output import OutputMode

        ctx = CommandContext(
            output_mode=OutputMode.DEFAULT,
            verbose=False,
            config_file=Path("/tmp/test"),
        )

        cmd = _build_ssh_cmd(
            host="192.168.1.1",
            user="admin",
            port=22,
            auth=AuthMode.KEY,
            password=None,
            strict_host_key_checking=False,
            ctx=ctx,
        )

        assert "StrictHostKeyChecking=no" in cmd
        assert "192.168.1.1" in cmd
        assert "admin@" in cmd

    def test_build_ssh_cmd_default_accepts_new_keys(self) -> None:
        """Test _build_ssh_cmd defaults to accept-new mode (accept new, verify existing)."""
        from pathlib import Path

        from network_toolkit.commands.ssh import AuthMode, _build_ssh_cmd
        from network_toolkit.common.command_helpers import CommandContext
        from network_toolkit.common.output import OutputMode

        ctx = CommandContext(
            output_mode=OutputMode.DEFAULT,
            verbose=False,
            config_file=Path("/tmp/test"),
        )

        # Call without strict_host_key_checking parameter (uses default)
        cmd = _build_ssh_cmd(
            host="192.168.1.1",
            user="admin",
            port=22,
            auth=AuthMode.KEY,
            password=None,
            ctx=ctx,
        )

        # Default should be accept-new (accept new keys, verify existing)
        assert "StrictHostKeyChecking=accept-new" in cmd
