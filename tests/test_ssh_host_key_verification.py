"""Test SSH host key verification configuration."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
from network_toolkit.device import DeviceSession


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

    @pytest.mark.parametrize("strict", [True, False])
    def test_device_session_passes_host_key_policy_to_transport(
        self, strict: bool
    ) -> None:
        """DeviceSession passes the configured OpenSSH policy to Scrapli."""
        config = NetworkConfig(
            general=GeneralConfig(ssh_strict_host_key_checking=strict),
            devices={
                "test_device": DeviceConfig(
                    host="192.168.1.1",
                    device_type="cisco_ios",
                    user="testuser",
                    password="testpass",
                )
            },
        )

        with patch("network_toolkit.transport.scrapli_sync.Cli") as driver:
            with DeviceSession("test_device", config):
                driver.return_value.open.assert_called_once_with()

        driver.assert_called_once()
        options = driver.call_args.kwargs["transport_options"]
        assert options.enable_strict_key is strict
