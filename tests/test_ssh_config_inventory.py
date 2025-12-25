"""Tests for SSH config inventory sync."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from network_toolkit.inventory.ssh_config import (
    SSHConfigOptions,
    enumerate_ssh_hosts,
    parse_ssh_config,
)


@pytest.fixture
def sample_ssh_config(tmp_path: Path) -> Path:
    """Create a sample SSH config file.

    Note: SSH config uses first-match-wins for each directive,
    so specific hosts must come before wildcards.
    """
    config = tmp_path / "config"
    config.write_text(
        """\
Host router-core-01
    HostName 10.1.0.1
    User admin
    Port 22

Host router-edge-01
    HostName 10.1.0.10

Host switch-acc-01
    HostName 10.2.0.1

Host switch-*
    User netadmin

Host *.example.com
    User webadmin

Host *
    User default_user
""",
        encoding="utf-8",
    )
    return config


def test_enumerate_concrete_hosts(sample_ssh_config: Path) -> None:
    """Only concrete hosts, no wildcards."""
    hosts = enumerate_ssh_hosts(sample_ssh_config)
    assert "router-core-01" in hosts
    assert "router-edge-01" in hosts
    assert "switch-acc-01" in hosts
    assert "*" not in hosts
    assert "*.example.com" not in hosts
    assert "switch-*" not in hosts


def test_skip_wildcards(sample_ssh_config: Path) -> None:
    """Wildcards like *.example.com are skipped."""
    hosts = enumerate_ssh_hosts(sample_ssh_config)
    for host in hosts:
        assert "*" not in host
        assert "?" not in host


def test_parse_ssh_config(sample_ssh_config: Path) -> None:
    """Parse SSH config into SSHHost objects."""
    options = SSHConfigOptions(path=sample_ssh_config)
    hosts = parse_ssh_config(options)

    assert "router-core-01" in hosts
    assert hosts["router-core-01"].hostname == "10.1.0.1"
    assert hosts["router-core-01"].user == "admin"
    assert hosts["router-core-01"].port == 22


def test_include_patterns(sample_ssh_config: Path) -> None:
    """Only include matching hosts."""
    options = SSHConfigOptions(
        path=sample_ssh_config,
        include_patterns=["router-*"],
    )
    hosts = parse_ssh_config(options)

    assert "router-core-01" in hosts
    assert "router-edge-01" in hosts
    assert "switch-acc-01" not in hosts


def test_exclude_patterns(sample_ssh_config: Path) -> None:
    """Exclude matching hosts."""
    options = SSHConfigOptions(
        path=sample_ssh_config,
        exclude_patterns=["*-edge-*"],
    )
    hosts = parse_ssh_config(options)

    assert "router-core-01" in hosts
    assert "router-edge-01" not in hosts
    assert "switch-acc-01" in hosts


def test_hostname_resolution(sample_ssh_config: Path) -> None:
    """Hostname is resolved from SSH config."""
    options = SSHConfigOptions(path=sample_ssh_config)
    hosts = parse_ssh_config(options)

    # router-edge-01 has explicit HostName
    assert hosts["router-edge-01"].hostname == "10.1.0.10"


def test_user_inheritance(sample_ssh_config: Path) -> None:
    """User is inherited from wildcards."""
    options = SSHConfigOptions(path=sample_ssh_config)
    hosts = parse_ssh_config(options)

    # switch-acc-01 should inherit user from switch-* pattern
    assert hosts["switch-acc-01"].user == "netadmin"


def test_default_user_inheritance(sample_ssh_config: Path) -> None:
    """Default user from Host * is inherited."""
    options = SSHConfigOptions(path=sample_ssh_config)
    hosts = parse_ssh_config(options)

    # router-edge-01 has no explicit user but should get default_user from Host *
    assert hosts["router-edge-01"].user == "default_user"


def test_include_and_exclude_combined(sample_ssh_config: Path) -> None:
    """Include and exclude patterns work together."""
    options = SSHConfigOptions(
        path=sample_ssh_config,
        include_patterns=["router-*", "switch-*"],
        exclude_patterns=["*-core-*"],
    )
    hosts = parse_ssh_config(options)

    assert "router-edge-01" in hosts
    assert "switch-acc-01" in hosts
    assert "router-core-01" not in hosts


class TestSyncCommand:
    """Tests for the sync ssh-config command."""

    @pytest.fixture
    def ssh_config_file(self, tmp_path: Path) -> Path:
        """Create a sample SSH config file for sync tests."""
        config = tmp_path / "ssh_config"
        config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    User admin
    Port 22

Host switch-01
    HostName 10.2.0.1
    User netadmin
""",
            encoding="utf-8",
        )
        return config

    @pytest.fixture
    def output_file(self, tmp_path: Path) -> Path:
        """Path for output YAML file."""
        return tmp_path / "devices" / "ssh-hosts.yml"

    def test_sync_creates_new_inventory(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """First sync creates inventory file."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
            ],
        )

        assert result.exit_code == 0, result.output
        assert output_file.exists()
        assert "Added 2 hosts" in result.output

        # Verify content
        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert data["router-01"]["host"] == "10.1.0.1"
        assert data["router-01"]["user"] == "admin"
        assert data["router-01"]["port"] == 22
        assert data["router-01"]["device_type"] == "generic"
        assert data["router-01"]["_ssh_config_source"] == "router-01"

    def test_sync_preserves_manual_edits(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """Re-sync preserves manual edits like device_type and tags."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # First sync
        runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config_file), "--output", str(output_file)],
        )

        # Manually edit the inventory
        data = yaml.safe_load(output_file.read_text())
        data["router-01"]["device_type"] = "mikrotik_routeros"
        data["router-01"]["tags"] = ["core", "production"]
        output_file.write_text(yaml.dump(data))

        # Re-sync
        result = runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config_file), "--output", str(output_file)],
        )

        assert result.exit_code == 0, result.output
        assert "No changes" in result.output

        # Verify manual edits preserved
        data = yaml.safe_load(output_file.read_text())
        assert data["router-01"]["device_type"] == "mikrotik_routeros"
        assert data["router-01"]["tags"] == ["core", "production"]

    def test_sync_updates_ssh_fields(self, tmp_path: Path, output_file: Path) -> None:
        """Re-sync updates host/user/port if changed in SSH config."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Initial SSH config
        ssh_config = tmp_path / "ssh_config"
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    User admin
""",
            encoding="utf-8",
        )

        # First sync
        runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        # Update SSH config
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.99
    User newadmin
    Port 2222
""",
            encoding="utf-8",
        )

        # Re-sync
        result = runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        assert result.exit_code == 0, result.output
        assert "Updated 1 hosts" in result.output

        # Verify updates
        data = yaml.safe_load(output_file.read_text())
        assert data["router-01"]["host"] == "10.1.0.99"
        assert data["router-01"]["user"] == "newadmin"
        assert data["router-01"]["port"] == 2222

    def test_sync_prune_removes_old_hosts(
        self, tmp_path: Path, output_file: Path
    ) -> None:
        """--prune removes hosts no longer in SSH config."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Initial SSH config with two hosts
        ssh_config = tmp_path / "ssh_config"
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1

Host router-02
    HostName 10.1.0.2
""",
            encoding="utf-8",
        )

        # First sync
        runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        # Remove router-02 from SSH config
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
""",
            encoding="utf-8",
        )

        # Re-sync with prune
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config),
                "--output",
                str(output_file),
                "--prune",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Removed 1 hosts" in result.output

        # Verify router-02 removed
        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert "router-02" not in data

    def test_sync_dry_run(self, ssh_config_file: Path, output_file: Path) -> None:
        """--dry-run shows changes without writing."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert not output_file.exists()

    def test_sync_with_include_filter(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """--include filters hosts by pattern."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
                "--include",
                "router-*",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Added 1 hosts" in result.output

        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert "switch-01" not in data

    def test_sync_with_exclude_filter(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """--exclude filters out hosts by pattern."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
                "--exclude",
                "switch-*",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "Added 1 hosts" in result.output

        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert "switch-01" not in data

    def test_sync_with_default_device_type(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """--default-device-type sets device type for new hosts."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
                "--default-device-type",
                "mikrotik_routeros",
            ],
        )

        assert result.exit_code == 0, result.output

        data = yaml.safe_load(output_file.read_text())
        assert data["router-01"]["device_type"] == "mikrotik_routeros"

    def test_sync_does_not_touch_non_ssh_hosts(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """Hosts without _ssh_config_source marker are not modified."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Create output with a manually added host
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            yaml.dump(
                {
                    "manual-host": {
                        "host": "192.168.1.1",
                        "device_type": "cisco_iosxe",
                    }
                }
            )
        )

        # Sync
        result = runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config_file), "--output", str(output_file)],
        )

        assert result.exit_code == 0, result.output

        # Verify manual host is preserved
        data = yaml.safe_load(output_file.read_text())
        assert "manual-host" in data
        assert data["manual-host"]["host"] == "192.168.1.1"
        assert "_ssh_config_source" not in data["manual-host"]

    def test_sync_prune_does_not_remove_non_ssh_hosts(
        self, tmp_path: Path, output_file: Path
    ) -> None:
        """--prune only removes hosts with _ssh_config_source marker."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Empty SSH config
        ssh_config = tmp_path / "ssh_config"
        ssh_config.write_text("", encoding="utf-8")

        # Create output with a manually added host
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(
            yaml.dump(
                {
                    "manual-host": {
                        "host": "192.168.1.1",
                        "device_type": "cisco_iosxe",
                    }
                }
            )
        )

        # Sync with prune
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config),
                "--output",
                str(output_file),
                "--prune",
            ],
        )

        assert result.exit_code == 0, result.output

        # Verify manual host is preserved (no _ssh_config_source marker)
        data = yaml.safe_load(output_file.read_text())
        assert "manual-host" in data

    def test_sync_removes_user_when_removed_from_ssh_config(
        self, tmp_path: Path, output_file: Path
    ) -> None:
        """Should remove user from inventory when removed from SSH config."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Initial SSH config with user
        ssh_config = tmp_path / "ssh_config"
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    User admin
    Port 22
""",
            encoding="utf-8",
        )

        # First sync
        runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        # Update SSH config - remove user
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    Port 22
""",
            encoding="utf-8",
        )

        # Re-sync
        result = runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        assert result.exit_code == 0, result.output
        assert "Updated 1 hosts" in result.output

        # Verify user was removed
        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert "user" not in data["router-01"]
        assert data["router-01"]["port"] == 22

    def test_sync_removes_port_when_removed_from_ssh_config(
        self, tmp_path: Path, output_file: Path
    ) -> None:
        """Should remove port from inventory when removed from SSH config."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()

        # Initial SSH config with port
        ssh_config = tmp_path / "ssh_config"
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    User admin
    Port 2222
""",
            encoding="utf-8",
        )

        # First sync
        runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        # Update SSH config - remove port
        ssh_config.write_text(
            """\
Host router-01
    HostName 10.1.0.1
    User admin
""",
            encoding="utf-8",
        )

        # Re-sync
        result = runner.invoke(
            app,
            ["sync", "ssh-config", str(ssh_config), "--output", str(output_file)],
        )

        assert result.exit_code == 0, result.output
        assert "Updated 1 hosts" in result.output

        # Verify port was removed
        data = yaml.safe_load(output_file.read_text())
        assert "router-01" in data
        assert "port" not in data["router-01"]
        assert data["router-01"]["user"] == "admin"

    def test_sync_dry_run_prefix(
        self, ssh_config_file: Path, output_file: Path
    ) -> None:
        """--dry-run shows [DRY RUN] prefix in output."""
        from typer.testing import CliRunner

        from network_toolkit.cli import app

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "sync",
                "ssh-config",
                str(ssh_config_file),
                "--output",
                str(output_file),
                "--dry-run",
            ],
        )

        assert result.exit_code == 0, result.output
        assert "[DRY RUN]" in result.output
        assert not output_file.exists()


class TestSSHConfigErrors:
    """Tests for SSH config error handling."""

    def test_parse_ssh_config_file_not_found(self, tmp_path: Path) -> None:
        """Should raise ConfigurationError with helpful message."""
        from network_toolkit.exceptions import ConfigurationError

        nonexistent = tmp_path / "nonexistent_ssh_config"
        options = SSHConfigOptions(path=nonexistent)

        with pytest.raises(ConfigurationError) as exc_info:
            parse_ssh_config(options)

        assert "not found" in str(exc_info.value).lower()

    def test_parse_ssh_config_permission_denied(self, tmp_path: Path) -> None:
        """Should raise ConfigurationError when file is unreadable."""
        import os

        from network_toolkit.exceptions import ConfigurationError

        # Create file and make it unreadable
        config = tmp_path / "ssh_config"
        config.write_text("Host test\n    HostName 10.0.0.1\n", encoding="utf-8")
        os.chmod(config, 0o000)

        try:
            options = SSHConfigOptions(path=config)
            with pytest.raises(ConfigurationError) as exc_info:
                parse_ssh_config(options)

            assert "permission" in str(exc_info.value).lower()
        finally:
            # Restore permissions for cleanup
            os.chmod(config, 0o644)

    def test_sync_invalid_yaml_existing_inventory(self, tmp_path: Path) -> None:
        """Should fail with clear error if existing inventory is corrupted."""
        from network_toolkit.commands.sync_ssh import _load_existing_inventory
        from network_toolkit.exceptions import ConfigurationError

        # Create corrupted inventory file
        output_file = tmp_path / "devices" / "inventory.yml"
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("invalid: yaml: content: [", encoding="utf-8")

        with pytest.raises(ConfigurationError) as exc_info:
            _load_existing_inventory(output_file)

        assert "yaml" in str(exc_info.value).lower()

    def test_parse_empty_ssh_config(self, tmp_path: Path) -> None:
        """Should handle empty SSH config gracefully."""
        config = tmp_path / "ssh_config"
        config.write_text("", encoding="utf-8")

        options = SSHConfigOptions(path=config)
        hosts = parse_ssh_config(options)

        assert hosts == {}

    def test_parse_ssh_config_with_include_directive(self, tmp_path: Path) -> None:
        """Should error when Include directive is present."""
        from network_toolkit.exceptions import ConfigurationError

        config = tmp_path / "ssh_config"
        config.write_text(
            """\
Host router-01
    HostName 10.1.0.1

Include ~/.ssh/config.d/*

Host switch-01
    HostName 10.2.0.1
""",
            encoding="utf-8",
        )

        options = SSHConfigOptions(path=config)
        with pytest.raises(ConfigurationError) as exc_info:
            parse_ssh_config(options)

        assert "include" in str(exc_info.value).lower()

    def test_pattern_too_long_rejected(self, tmp_path: Path) -> None:
        """Should reject patterns that are too long (ReDoS prevention)."""
        from network_toolkit.exceptions import ConfigurationError

        config = tmp_path / "ssh_config"
        config.write_text("Host router-01\n    HostName 10.1.0.1\n", encoding="utf-8")

        # Create a very long pattern
        long_pattern = "a" * 300
        options = SSHConfigOptions(
            path=config,
            include_patterns=[long_pattern],
        )

        with pytest.raises(ConfigurationError) as exc_info:
            parse_ssh_config(options)

        assert "too long" in str(exc_info.value).lower()

    def test_pattern_too_complex_rejected(self, tmp_path: Path) -> None:
        """Should reject patterns with too many wildcards (ReDoS prevention)."""
        from network_toolkit.exceptions import ConfigurationError

        config = tmp_path / "ssh_config"
        config.write_text("Host router-01\n    HostName 10.1.0.1\n", encoding="utf-8")

        # Create a pattern with many wildcards
        complex_pattern = "*" * 25
        options = SSHConfigOptions(
            path=config,
            include_patterns=[complex_pattern],
        )

        with pytest.raises(ConfigurationError) as exc_info:
            parse_ssh_config(options)

        assert "complex" in str(exc_info.value).lower()

    def test_invalid_hostname_skipped(self, tmp_path: Path) -> None:
        """Should skip hosts with invalid hostname characters."""
        config = tmp_path / "ssh_config"
        config.write_text(
            """\
Host router-01
    HostName 10.1.0.1

Host bad<host>name
    HostName 10.2.0.1

Host switch-01
    HostName 10.3.0.1
""",
            encoding="utf-8",
        )

        hosts = enumerate_ssh_hosts(config)

        assert "router-01" in hosts
        assert "switch-01" in hosts
        assert "bad<host>name" not in hosts
