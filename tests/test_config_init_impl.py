"""Tests for config init implementation functions."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

from network_toolkit.commands.config import (
    _config_init_impl,
    activate_shell_completion,
    create_config_yml,
    create_env_file,
    create_example_devices,
    create_example_groups,
    create_example_sequences,
    detect_shell,
    install_editor_schemas,
    install_sequences_from_repo,
    install_shell_completions,
)
from network_toolkit.exceptions import ConfigurationError


class TestConfigInitCore:
    """Test core configuration initialization functions."""

    def test_create_env_file(self, tmp_path: Path) -> None:
        """Test .env file creation."""
        create_env_file(tmp_path)

        env_file = tmp_path / ".env"
        assert env_file.exists()

        content = env_file.read_text()
        assert "NW_USER_DEFAULT=admin" in content
        assert "NW_PASSWORD_DEFAULT=your_password_here" in content
        assert "Network Toolkit Environment Variables" in content

    def test_create_config_yml(self, tmp_path: Path) -> None:
        """Test config.yml creation."""
        create_config_yml(tmp_path)

        config_file = tmp_path / "config.yml"
        assert config_file.exists()

        content = config_file.read_text()
        assert "general:" in content
        assert "output_mode: default" in content
        assert "log_level: INFO" in content

    def test_create_example_devices(self, tmp_path: Path) -> None:
        """Test example device files creation."""
        devices_dir = tmp_path / "devices"
        create_example_devices(devices_dir)

        assert devices_dir.exists()
        router_file = devices_dir / "router1.yml"
        switch_file = devices_dir / "switch1.yml"

        assert router_file.exists()
        assert switch_file.exists()

        router_content = router_file.read_text()
        assert "host: 192.168.1.1" in router_content
        assert "device_type: mikrotik_routeros" in router_content

    def test_create_example_groups(self, tmp_path: Path) -> None:
        """Test example group files creation."""
        groups_dir = tmp_path / "groups"
        create_example_groups(groups_dir)

        assert groups_dir.exists()
        office_file = groups_dir / "office.yml"
        critical_file = groups_dir / "critical.yml"

        assert office_file.exists()
        assert critical_file.exists()

        office_content = office_file.read_text()
        assert 'description: "All office network devices"' in office_content
        assert "match_tags:" in office_content

    def test_create_example_sequences(self, tmp_path: Path) -> None:
        """Test example sequence files creation."""
        sequences_dir = tmp_path / "sequences"
        create_example_sequences(sequences_dir)

        assert sequences_dir.exists()
        global_file = sequences_dir / "global.yml"
        assert global_file.exists()

        content = global_file.read_text()
        assert "health_check:" in content
        assert "backup_config:" in content
        assert "commands:" in content


class TestShellDetection:
    """Test shell detection functionality."""

    def test_detect_shell_explicit(self) -> None:
        """Test explicit shell detection."""
        assert detect_shell("bash") == "bash"
        assert detect_shell("zsh") == "zsh"
        # detect_shell falls back to environment detection for unsupported shells
        # We need to mock the environment to test None return
        with patch.dict("os.environ", {"SHELL": "/bin/fish"}):
            assert detect_shell("fish") is None

    @patch.dict("os.environ", {"SHELL": "/bin/bash"})
    def test_detect_shell_from_env_bash(self) -> None:
        """Test shell detection from environment variable - bash."""
        assert detect_shell() == "bash"

    @patch.dict("os.environ", {"SHELL": "/usr/bin/zsh"})
    def test_detect_shell_from_env_zsh(self) -> None:
        """Test shell detection from environment variable - zsh."""
        assert detect_shell() == "zsh"

    @patch.dict("os.environ", {"SHELL": "/bin/fish"})
    def test_detect_shell_from_env_unsupported(self) -> None:
        """Test shell detection from environment variable - unsupported."""
        assert detect_shell() is None


class TestShellCompletions:
    """Test shell completion installation and activation."""

    @patch("network_toolkit.commands.config._detect_repo_root")
    def test_install_shell_completions_no_repo(self, mock_repo: Mock) -> None:
        """Test shell completion installation when repo not found."""
        mock_repo.return_value = None

        result = install_shell_completions("bash")
        assert result == (None, None)

    @patch("network_toolkit.commands.config._detect_repo_root")
    def test_install_shell_completions_invalid_shell(self, mock_repo: Mock) -> None:
        """Test shell completion installation with invalid shell."""
        mock_repo.return_value = Path("/fake/repo")

        with pytest.raises(
            ConfigurationError, match="Only bash and zsh shells are supported"
        ):
            install_shell_completions("fish")

    def test_activate_shell_completion_no_rc_file(self) -> None:
        """Test shell completion activation with None rc file."""
        # Should not raise an exception
        activate_shell_completion("bash", Path("/fake/path"), None)

    def test_activate_shell_completion_bash(self, tmp_path: Path) -> None:
        """Test bash completion activation."""
        rc_file = tmp_path / ".bashrc"
        completion_path = tmp_path / "completion.sh"
        completion_path.touch()

        activate_shell_completion("bash", completion_path, rc_file)

        assert rc_file.exists()
        content = rc_file.read_text()
        assert ">>> NW COMPLETION >>>" in content
        assert "<<< NW COMPLETION <<<" in content
        assert str(completion_path) in content

    def test_activate_shell_completion_already_exists(self, tmp_path: Path) -> None:
        """Test shell completion activation when already present."""
        rc_file = tmp_path / ".bashrc"
        completion_path = tmp_path / "completion.sh"

        # Pre-populate with existing completion
        rc_file.write_text(
            "# >>> NW COMPLETION >>>\nexisting\n# <<< NW COMPLETION <<<\n"
        )

        activate_shell_completion("bash", completion_path, rc_file)

        # Should not add duplicate entries
        content = rc_file.read_text()
        assert content.count(">>> NW COMPLETION >>>") == 1


class TestSequenceInstallation:
    """Test sequence installation from repositories."""

    @patch("network_toolkit.commands.config._find_git_executable")
    @patch("subprocess.run")
    def test_install_sequences_from_repo_success(
        self, mock_run: Mock, mock_git: Mock, tmp_path: Path
    ) -> None:
        """Test successful sequence installation from repository."""
        mock_git.return_value = "/usr/bin/git"
        mock_run.return_value = Mock(returncode=0)

        # Create fake repo structure
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir) / "repo"
            sequences_path = repo_path / "config" / "sequences"
            sequences_path.mkdir(parents=True)

            # Create a test sequence file
            test_seq = sequences_path / "test.yml"
            test_seq.write_text("test_sequence:\n  commands: [test]")

            # Mock the temporary directory to return our prepared structure
            with patch("tempfile.TemporaryDirectory") as mock_temp:
                mock_temp.return_value.__enter__.return_value = temp_dir

                dest = tmp_path / "sequences"
                dest.mkdir(parents=True, exist_ok=True)  # Ensure destination exists
                install_sequences_from_repo(
                    "https://github.com/test/repo.git", "main", dest
                )

                # Verify git clone was called
                mock_run.assert_called_once()
                args = mock_run.call_args[0][0]
                assert "/usr/bin/git" in args
                assert "clone" in args
                assert "https://github.com/test/repo.git" in args

    def test_install_sequences_invalid_url(self) -> None:
        """Test sequence installation with invalid URL."""
        with pytest.raises(
            ConfigurationError, match="Git URL must use HTTPS or SSH protocol"
        ):
            install_sequences_from_repo(
                "ftp://invalid.com/repo.git", "main", Path("/tmp")
            )

    def test_install_sequences_private_ip(self) -> None:
        """Test sequence installation blocks private IPs."""
        with pytest.raises(
            ConfigurationError, match="Private IP addresses not allowed"
        ):
            install_sequences_from_repo(
                "https://192.168.1.1/repo.git", "main", Path("/tmp")
            )

    @patch("shutil.which")
    def test_install_sequences_no_git(self, mock_which: Mock) -> None:
        """Test sequence installation when git is not available."""
        mock_which.return_value = None

        with pytest.raises(ConfigurationError, match="Git executable not found"):
            install_sequences_from_repo(
                "https://github.com/test/repo.git", "main", Path("/tmp")
            )


class TestSchemaInstallation:
    """Test JSON schema installation."""

    @patch("urllib.request.urlopen")
    def test_install_editor_schemas_success(
        self, mock_urlopen: Mock, tmp_path: Path
    ) -> None:
        """Test successful schema installation."""
        # Mock HTTP responses
        mock_response = Mock()
        mock_response.read.return_value = b'{"$schema": "test"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = None

        install_editor_schemas(tmp_path)

        # Check schemas directory was created
        schemas_dir = tmp_path / "schemas"
        assert schemas_dir.exists()

        # Check VS Code settings were created
        vscode_dir = tmp_path / ".vscode"
        settings_file = vscode_dir / "settings.json"
        assert settings_file.exists()

        # Verify settings content
        settings = json.loads(settings_file.read_text())
        assert "yaml.schemas" in settings
        assert "./schemas/device-config.schema.json" in settings["yaml.schemas"]

    @patch("urllib.request.urlopen")
    def test_install_editor_schemas_existing_settings(
        self, mock_urlopen: Mock, tmp_path: Path
    ) -> None:
        """Test schema installation with existing VS Code settings."""
        # Create existing settings
        vscode_dir = tmp_path / ".vscode"
        vscode_dir.mkdir()
        settings_file = vscode_dir / "settings.json"
        existing_settings = {"existing": "setting"}
        settings_file.write_text(json.dumps(existing_settings))

        # Mock HTTP responses
        mock_response = Mock()
        mock_response.read.return_value = b'{"$schema": "test"}'
        mock_urlopen.return_value.__enter__.return_value = mock_response
        mock_urlopen.return_value.__exit__.return_value = None

        install_editor_schemas(tmp_path)

        # Verify existing settings were preserved
        settings = json.loads(settings_file.read_text())
        assert settings["existing"] == "setting"
        assert "yaml.schemas" in settings


class TestConfigInitImpl:
    """Test the main config init implementation."""

    @patch("network_toolkit.commands.config.create_env_file")
    @patch("network_toolkit.commands.config.create_config_yml")
    @patch("network_toolkit.commands.config.create_example_devices")
    @patch("network_toolkit.commands.config.create_example_groups")
    @patch("network_toolkit.commands.config.create_example_sequences")
    def test_config_init_impl_dry_run(
        self,
        mock_seq: Mock,
        mock_groups: Mock,
        mock_devices: Mock,
        mock_config: Mock,
        mock_env: Mock,
        tmp_path: Path,
    ) -> None:
        """Test config init implementation in dry-run mode."""
        _config_init_impl(target_dir=tmp_path, dry_run=True, yes=True)

        # In dry-run mode, no files should be created
        mock_env.assert_not_called()
        mock_config.assert_not_called()
        mock_devices.assert_not_called()
        mock_groups.assert_not_called()
        mock_seq.assert_not_called()

    @patch("network_toolkit.commands.config.create_env_file")
    @patch("network_toolkit.commands.config.create_config_yml")
    @patch("network_toolkit.commands.config.create_example_devices")
    @patch("network_toolkit.commands.config.create_example_groups")
    @patch("network_toolkit.commands.config.create_example_sequences")
    def test_config_init_impl_real_run(
        self,
        mock_seq: Mock,
        mock_groups: Mock,
        mock_devices: Mock,
        mock_config: Mock,
        mock_env: Mock,
        tmp_path: Path,
    ) -> None:
        """Test config init implementation with actual file creation."""
        _config_init_impl(target_dir=tmp_path, yes=True)

        # All creation functions should be called
        mock_env.assert_called_once_with(tmp_path)
        mock_config.assert_called_once_with(tmp_path)
        mock_devices.assert_called_once_with(tmp_path / "devices")
        mock_groups.assert_called_once_with(tmp_path / "groups")
        mock_seq.assert_called_once_with(tmp_path / "sequences")

    @patch("network_toolkit.commands.config.install_sequences_from_repo")
    def test_config_init_impl_with_sequences(
        self, mock_install: Mock, tmp_path: Path
    ) -> None:
        """Test config init with sequence installation."""
        mock_install.return_value = 5  # Return number of files installed

        _config_init_impl(
            target_dir=tmp_path,
            yes=True,
            install_sequences=True,
            git_url="https://github.com/test/repo.git",
            git_ref="main",
        )

        mock_install.assert_called_once_with(
            "https://github.com/test/repo.git", "main", tmp_path / "sequences"
        )

    @patch("network_toolkit.commands.config.install_shell_completions")
    @patch("network_toolkit.commands.config.activate_shell_completion")
    def test_config_init_impl_with_completions(
        self, mock_activate: Mock, mock_install: Mock, tmp_path: Path
    ) -> None:
        """Test config init with shell completion installation."""
        mock_install.return_value = (Path("/fake/completion"), Path("/fake/.bashrc"))

        shell_type = "bash"  # Extract to variable to avoid false positive lint warning
        _config_init_impl(
            target_dir=tmp_path,
            yes=True,
            install_completions=True,
            shell=shell_type,
            activate_completions=True,
        )

        mock_install.assert_called_once_with(shell_type)
        mock_activate.assert_called_once_with(
            shell_type, Path("/fake/completion"), Path("/fake/.bashrc")
        )

    @patch("network_toolkit.commands.config.install_editor_schemas")
    def test_config_init_impl_with_schemas(
        self, mock_install: Mock, tmp_path: Path
    ) -> None:
        """Test config init with schema installation."""
        mock_install.return_value = 3  # Return number of schemas installed

        _config_init_impl(
            target_dir=tmp_path,
            yes=True,
            install_schemas=True,
            git_url="https://github.com/test/repo.git",
            git_ref="main",
        )

        mock_install.assert_called_once_with(
            tmp_path, "https://github.com/test/repo.git", "main"
        )


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_user_cancellation_clean_exit(self, temp_dir: Path) -> None:
        """Test that user cancellation results in clean exit without error logging."""
        # Create existing config to trigger overwrite prompt
        existing_file = temp_dir / "devices.yml"
        existing_file.write_text("existing: config")

        # Mock user declining overwrite (which raises typer.Exit(0))
        with patch("typer.confirm", return_value=False):
            with pytest.raises(typer.Exit) as exc_info:
                _config_init_impl(
                    target_dir=temp_dir,
                    force=False,
                    yes=False,
                    dry_run=False,
                    install_sequences=False,
                    install_completions=False,
                    install_schemas=False,
                    verbose=False,
                )

            # Should be exit code 0 (clean cancellation)
            assert exc_info.value.exit_code == 0
