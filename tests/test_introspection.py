# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the introspection module."""

from __future__ import annotations

from pathlib import Path

import pytest

from network_toolkit.introspection import (
    ConfigHistory,
    FieldHistory,
    LoaderType,
)


class TestLoaderType:
    """Tests for LoaderType enum."""

    def test_loader_type_values(self) -> None:
        """Test that all expected loader types exist."""
        assert LoaderType.CONFIG_FILE.value == "config_file"
        assert LoaderType.ENV_VAR.value == "env_var"
        assert LoaderType.DOTENV.value == "dotenv"
        assert LoaderType.GROUP.value == "group"
        assert LoaderType.SSH_CONFIG.value == "ssh_config"
        assert LoaderType.PYDANTIC_DEFAULT.value == "default"
        assert LoaderType.CLI.value == "cli"
        assert LoaderType.INTERACTIVE.value == "interactive"

    def test_loader_type_is_string(self) -> None:
        """Test that LoaderType is a string enum."""
        assert isinstance(LoaderType.CONFIG_FILE, str)
        assert LoaderType.CONFIG_FILE == "config_file"


class TestFieldHistory:
    """Tests for FieldHistory dataclass."""

    def test_field_history_creation(self) -> None:
        """Test creating a FieldHistory instance."""
        history = FieldHistory(
            field_name="host",
            value="192.168.1.1",
            loader=LoaderType.CONFIG_FILE,
            identifier="config/devices/routers.yml",
            line_number=5,
        )
        assert history.field_name == "host"
        assert history.value == "192.168.1.1"
        assert history.loader == LoaderType.CONFIG_FILE
        assert history.identifier == "config/devices/routers.yml"
        assert history.line_number == 5

    def test_field_history_defaults(self) -> None:
        """Test FieldHistory default values."""
        history = FieldHistory(
            field_name="timeout",
            value=30,
            loader=LoaderType.PYDANTIC_DEFAULT,
        )
        assert history.identifier is None
        assert history.line_number is None

    def test_field_history_immutable(self) -> None:
        """Test that FieldHistory is frozen (immutable)."""
        history = FieldHistory(
            field_name="host",
            value="192.168.1.1",
            loader=LoaderType.CONFIG_FILE,
        )
        with pytest.raises(AttributeError):
            history.value = "10.0.0.1"  # type: ignore[misc]

    def test_format_source_env_var(self) -> None:
        """Test format_source for environment variables."""
        history = FieldHistory(
            field_name="user",
            value="admin",
            loader=LoaderType.ENV_VAR,
            identifier="NW_USER_DEFAULT",
        )
        assert history.format_source() == "env: NW_USER_DEFAULT"

    def test_format_source_env_var_no_identifier(self) -> None:
        """Test format_source for environment variables without identifier."""
        history = FieldHistory(
            field_name="user",
            value="admin",
            loader=LoaderType.ENV_VAR,
        )
        assert history.format_source() == "env"

    def test_format_source_config_file(self) -> None:
        """Test format_source for config file."""
        history = FieldHistory(
            field_name="host",
            value="192.168.1.1",
            loader=LoaderType.CONFIG_FILE,
            identifier="/path/to/devices.yml",
            line_number=10,
        )
        # Note: actual output depends on Path.cwd(), but should include path
        result = history.format_source()
        assert "devices.yml" in result

    def test_format_source_config_file_with_line(self) -> None:
        """Test format_source includes line number when available."""
        history = FieldHistory(
            field_name="host",
            value="192.168.1.1",
            loader=LoaderType.CONFIG_FILE,
            identifier="devices.yml",
            line_number=42,
        )
        result = history.format_source()
        assert ":42" in result

    def test_format_source_group(self) -> None:
        """Test format_source for group inheritance."""
        history = FieldHistory(
            field_name="user",
            value="netadmin",
            loader=LoaderType.GROUP,
            identifier="core-routers",
        )
        assert history.format_source() == "group: core-routers"

    def test_format_source_pydantic_default(self) -> None:
        """Test format_source for Pydantic defaults."""
        history = FieldHistory(
            field_name="timeout",
            value=30,
            loader=LoaderType.PYDANTIC_DEFAULT,
        )
        assert history.format_source() == "default"

    def test_format_source_interactive(self) -> None:
        """Test format_source for interactive input."""
        history = FieldHistory(
            field_name="password",
            value="secret",
            loader=LoaderType.INTERACTIVE,
        )
        assert history.format_source() == "interactive"

    def test_format_source_cli(self) -> None:
        """Test format_source for CLI override."""
        history = FieldHistory(
            field_name="user",
            value="admin",
            loader=LoaderType.CLI,
        )
        assert history.format_source() == "cli"


class TestConfigHistory:
    """Tests for ConfigHistory dataclass."""

    def test_config_history_creation(self) -> None:
        """Test creating an empty ConfigHistory."""
        history = ConfigHistory()
        assert history.get_all_fields() == []

    def test_record_single_field(self) -> None:
        """Test recording a single field."""
        history = ConfigHistory()
        entry = FieldHistory(
            field_name="host",
            value="192.168.1.1",
            loader=LoaderType.CONFIG_FILE,
        )
        history.record(entry)

        assert "host" in history.get_all_fields()
        assert len(history.get_history("host")) == 1
        assert history.get_current("host") == entry

    def test_record_multiple_entries_same_field(self) -> None:
        """Test recording multiple entries for the same field."""
        history = ConfigHistory()

        # First entry: default
        entry1 = FieldHistory(
            field_name="timeout",
            value=30,
            loader=LoaderType.PYDANTIC_DEFAULT,
        )
        history.record(entry1)

        # Second entry: config file override
        entry2 = FieldHistory(
            field_name="timeout",
            value=60,
            loader=LoaderType.CONFIG_FILE,
            identifier="config.yml",
        )
        history.record(entry2)

        entries = history.get_history("timeout")
        assert len(entries) == 2
        assert entries[0] == entry1
        assert entries[1] == entry2
        assert history.get_current("timeout") == entry2

    def test_record_field_convenience_method(self) -> None:
        """Test the record_field convenience method."""
        history = ConfigHistory()
        history.record_field(
            field_name="host",
            value="10.0.0.1",
            loader=LoaderType.CONFIG_FILE,
            identifier="devices.yml",
            line_number=5,
        )

        current = history.get_current("host")
        assert current is not None
        assert current.value == "10.0.0.1"
        assert current.loader == LoaderType.CONFIG_FILE
        assert current.identifier == "devices.yml"
        assert current.line_number == 5

    def test_get_history_nonexistent_field(self) -> None:
        """Test getting history for a field that doesn't exist."""
        history = ConfigHistory()
        assert history.get_history("nonexistent") == []

    def test_get_current_nonexistent_field(self) -> None:
        """Test getting current value for a field that doesn't exist."""
        history = ConfigHistory()
        assert history.get_current("nonexistent") is None

    def test_get_all_fields(self) -> None:
        """Test getting all tracked fields."""
        history = ConfigHistory()
        history.record_field("host", "192.168.1.1", LoaderType.CONFIG_FILE)
        history.record_field("user", "admin", LoaderType.ENV_VAR)
        history.record_field("timeout", 30, LoaderType.PYDANTIC_DEFAULT)

        fields = history.get_all_fields()
        assert len(fields) == 3
        assert "host" in fields
        assert "user" in fields
        assert "timeout" in fields

    def test_merge_from(self) -> None:
        """Test merging history from another ConfigHistory."""
        history1 = ConfigHistory()
        history1.record_field("host", "192.168.1.1", LoaderType.CONFIG_FILE)

        history2 = ConfigHistory()
        history2.record_field("user", "admin", LoaderType.ENV_VAR)

        history1.merge_from(history2)
        assert "host" in history1.get_all_fields()
        assert "user" in history1.get_all_fields()


class TestCredentialSourceTracking:
    """Tests for credential source tracking with CLI overrides."""

    def test_cli_override_uses_cli_loader_type(self, tmp_path: Path) -> None:
        """Test that CLI overrides use LoaderType.CLI in credential resolution."""
        import os

        from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
        from network_toolkit.credentials import CredentialResolver

        # Set up required environment variables
        os.environ["NW_USER_DEFAULT"] = "default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "default_pass"

        try:
            # Create a minimal config with one device
            config = NetworkConfig(
                general=GeneralConfig(),
                devices={
                    "test-device": DeviceConfig(
                        host="192.168.1.1",
                        device_type="mikrotik_routeros",
                    )
                },
            )

            resolver = CredentialResolver(config)

            # Test with CLI override
            creds, sources = resolver.resolve_credentials_with_source(
                device_name="test-device",
                username_override="cli_user",
                password_override="cli_pass",
            )

            # Verify credentials are from override
            assert creds[0] == "cli_user"
            assert creds[1] == "cli_pass"

            # Verify source is CLI type
            assert sources[0].loader == LoaderType.CLI
            assert sources[1].loader == LoaderType.CLI
            assert sources[0].format() == "cli"
            assert sources[1].format() == "cli"

        finally:
            # Clean up environment
            for var in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if var in os.environ:
                    del os.environ[var]

    def test_env_var_uses_env_var_loader_type(self, tmp_path: Path) -> None:
        """Test that environment variable credentials use LoaderType.ENV_VAR."""
        import os

        from network_toolkit.config import DeviceConfig, GeneralConfig, NetworkConfig
        from network_toolkit.credentials import CredentialResolver

        # Set up required environment variables
        os.environ["NW_USER_DEFAULT"] = "env_default_user"
        os.environ["NW_PASSWORD_DEFAULT"] = "env_default_pass"

        try:
            # Create a minimal config with one device (no device-specific creds)
            config = NetworkConfig(
                general=GeneralConfig(),
                devices={
                    "test-device": DeviceConfig(
                        host="192.168.1.1",
                        device_type="mikrotik_routeros",
                    )
                },
            )

            resolver = CredentialResolver(config)

            # Test without override - should use env vars
            creds, sources = resolver.resolve_credentials_with_source(
                device_name="test-device",
                username_override=None,
                password_override=None,
            )

            # Verify credentials are from environment
            assert creds[0] == "env_default_user"
            assert creds[1] == "env_default_pass"

            # Verify source is ENV_VAR type
            assert sources[0].loader == LoaderType.ENV_VAR
            assert sources[1].loader == LoaderType.ENV_VAR
            assert sources[0].identifier == "NW_USER_DEFAULT"
            assert sources[1].identifier == "NW_PASSWORD_DEFAULT"

        finally:
            # Clean up environment
            for var in ["NW_USER_DEFAULT", "NW_PASSWORD_DEFAULT"]:
                if var in os.environ:
                    del os.environ[var]
