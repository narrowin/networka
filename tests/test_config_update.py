"""Tests for config update command functionality."""

from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app
from network_toolkit.common.config_manifest import ConfigManifest
from network_toolkit.common.file_utils import calculate_checksum


@pytest.fixture
def mock_config_dir(tmp_path: Path) -> Path:
    """Create a mock config directory with structure."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create sequences structure
    sequences_dir = config_dir / "sequences"
    sequences_dir.mkdir()

    # Create custom directory
    custom_dir = sequences_dir / "custom"
    custom_dir.mkdir()
    (custom_dir / "README.md").write_text("Put your custom sequences here")

    # Create vendor directories with framework files
    for vendor in ["cisco_iosxe", "arista_eos"]:
        vendor_dir = sequences_dir / vendor
        vendor_dir.mkdir()
        common_file = vendor_dir / "common.yml"
        common_file.write_text(
            f"# Framework file for {vendor}\nsequences:\n  test: show version\n"
        )

    # Create sequences.yml
    (sequences_dir / "sequences.yml").write_text("# Framework sequences config\n")

    # Create manifest
    manifest = ConfigManifest.create_new("1.0.0")
    for vendor in ["cisco_iosxe", "arista_eos"]:
        rel_path = f"sequences/{vendor}/common.yml"
        file_path = config_dir / rel_path
        manifest.add_file(rel_path, calculate_checksum(file_path), "1.0.0")
    manifest.add_file(
        "sequences/sequences.yml",
        calculate_checksum(config_dir / "sequences/sequences.yml"),
        "1.0.0",
    )
    manifest.save(config_dir / ".nw-installed")

    return config_dir


@pytest.fixture
def mock_repo_dir(tmp_path: Path) -> Path:
    """Create a mock repository directory with updated files."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    config_dir = repo_dir / "config"
    config_dir.mkdir()

    sequences_dir = config_dir / "sequences"
    sequences_dir.mkdir()

    # Create updated framework files
    for vendor in ["cisco_iosxe", "arista_eos"]:
        vendor_dir = sequences_dir / vendor
        vendor_dir.mkdir()
        common_file = vendor_dir / "common.yml"
        common_file.write_text(
            f"# UPDATED Framework file for {vendor}\nsequences:\n  test: show version\n  new: show interfaces\n"
        )

    (sequences_dir / "sequences.yml").write_text(
        "# UPDATED Framework sequences config\n"
    )

    return repo_dir


class TestConfigUpdateCommand:
    """Test the nw config update command."""

    def test_update_command_in_help(self) -> None:
        """Test that update command appears in config help."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "--help"])

        assert result.exit_code == 0
        assert "update" in result.output
        assert "Update framework-provided configuration files" in result.output

    def test_update_help(self) -> None:
        """Test update command help output."""
        runner = CliRunner()
        result = runner.invoke(app, ["config", "update", "--help"])

        assert result.exit_code == 0
        assert "--check" in result.output
        assert "--list-backups" in result.output
        assert "--dry-run" in result.output
        assert "--force" in result.output
        assert "Manual rollback" in result.output
        assert "Protected files" in result.output
        assert "Framework files" in result.output

    def test_list_backups_empty(self, mock_config_dir: Path) -> None:
        """Test --list-backups when no backups exist."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "config",
                "update",
                "--list-backups",
                "--config-dir",
                str(mock_config_dir),
            ],
        )

        assert result.exit_code == 0
        assert "No backups found" in result.output

    def test_list_backups_with_backups(self, mock_config_dir: Path) -> None:
        """Test --list-backups when backups exist."""
        # Create some backup directories
        backup_root = mock_config_dir / ".backup"
        backup_root.mkdir()
        (backup_root / "20251015_100000").mkdir()
        (backup_root / "20251015_110000").mkdir()
        (backup_root / "20251016_090000").mkdir()

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "config",
                "update",
                "--list-backups",
                "--config-dir",
                str(mock_config_dir),
            ],
        )

        assert result.exit_code == 0
        assert "20251016_090000" in result.output
        assert "20251015_110000" in result.output
        assert "20251015_100000" in result.output
        assert "To restore a backup manually" in result.output

    def test_update_no_manifest_creates_baseline(self, mock_config_dir: Path) -> None:
        """Test update creates baseline manifest if none exists."""
        manifest_file = mock_config_dir / ".nw-installed"
        manifest_file.unlink()

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert "No installation manifest found" in result.output
        assert "Created baseline manifest" in result.output
        assert manifest_file.exists()

    @patch("subprocess.run")
    def test_update_check_with_changes(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test --check flag detects available updates."""

        # Mock git clone to copy our mock repo
        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                # Find the target directory (last arg)
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--check", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert "Found" in result.output and "updates" in result.output
        assert "Check complete" in result.output

    @patch("subprocess.run")
    def test_update_check_no_changes(
        self, mock_subprocess: Mock, mock_config_dir: Path
    ) -> None:
        """Test --check when no updates available."""
        # Create a proper repo structure (not just copy config dir)
        repo_dir = mock_config_dir.parent / "repo"
        repo_dir.mkdir()
        repo_config = repo_dir / "config"
        shutil.copytree(mock_config_dir, repo_config)

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--check", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert (
            "No updates available" in result.output
            or "all framework files are current" in result.output
        )

    @patch("subprocess.run")
    def test_update_dry_run(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test --dry-run shows changes without applying."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--dry-run", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert "DRY RUN" in result.output
        assert "No changes made" in result.output

        # Verify files weren't actually changed
        cisco_file = mock_config_dir / "sequences/cisco_iosxe/common.yml"
        assert "UPDATED" not in cisco_file.read_text()

    @patch("subprocess.run")
    def test_update_applies_changes_with_backup(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test update applies changes and creates backup."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        # Store original content
        cisco_file = mock_config_dir / "sequences/cisco_iosxe/common.yml"
        original_content = cisco_file.read_text()

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--yes", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert "Creating backup" in result.output
        assert "Updated" in result.output and "framework files" in result.output

        # Verify files were updated
        assert "UPDATED" in cisco_file.read_text()
        assert "new: show interfaces" in cisco_file.read_text()

        # Verify backup was created
        backup_root = mock_config_dir / ".backup"
        assert backup_root.exists()
        backups = list(backup_root.iterdir())
        assert len(backups) == 1

        # Verify backup contains original content
        backup_cisco = backups[0] / "sequences/cisco_iosxe/common.yml"
        assert backup_cisco.exists()
        assert backup_cisco.read_text() == original_content

    @patch("subprocess.run")
    def test_update_skips_user_modified_files(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test update skips files modified by user."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        # Modify a framework file (user edit)
        cisco_file = mock_config_dir / "sequences/cisco_iosxe/common.yml"
        cisco_file.write_text("# USER MODIFIED\nsequences:\n  custom: show run\n")

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--yes", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0
        assert "Skipping modified file" in result.output

        # Verify file was NOT updated
        assert "USER MODIFIED" in cisco_file.read_text()
        assert "UPDATED" not in cisco_file.read_text()

    @patch("subprocess.run")
    def test_update_force_updates_modified_files(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test --force updates even user-modified files."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        # Modify a framework file
        cisco_file = mock_config_dir / "sequences/cisco_iosxe/common.yml"
        cisco_file.write_text("# USER MODIFIED\nsequences:\n  custom: show run\n")

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "config",
                "update",
                "--force",
                "--yes",
                "--config-dir",
                str(mock_config_dir),
            ],
        )

        assert result.exit_code == 0
        assert "Force updating modified file" in result.output

        # Verify file WAS updated
        assert "UPDATED" in cisco_file.read_text()
        assert "USER MODIFIED" not in cisco_file.read_text()

    def test_update_protects_custom_directory(self, mock_config_dir: Path) -> None:
        """Test that custom/ directory is never touched by updates."""
        custom_file = mock_config_dir / "sequences/custom/my_custom.yml"
        custom_content = "# My custom sequences\nsequences:\n  custom: show custom\n"
        custom_file.write_text(custom_content)

        runner = CliRunner()
        # Even with force, custom files should be ignored
        runner.invoke(
            app,
            [
                "config",
                "update",
                "--force",
                "--yes",
                "--config-dir",
                str(mock_config_dir),
            ],
        )

        # Verify custom file unchanged
        assert custom_file.read_text() == custom_content

    @patch("subprocess.run")
    def test_update_manifest_tracking(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test that manifest is updated after successful update."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        manifest_file = mock_config_dir / ".nw-installed"
        manifest_before = ConfigManifest.load(manifest_file)

        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--yes", "--config-dir", str(mock_config_dir)],
        )

        assert result.exit_code == 0

        # Verify manifest was updated with new checksums
        manifest_after = ConfigManifest.load(manifest_file)
        cisco_info_before = manifest_before.get_file_info(
            "sequences/cisco_iosxe/common.yml"
        )
        cisco_info_after = manifest_after.get_file_info(
            "sequences/cisco_iosxe/common.yml"
        )

        assert cisco_info_before is not None
        assert cisco_info_after is not None
        assert cisco_info_after.checksum != cisco_info_before.checksum

    def test_update_nonexistent_config_dir(self) -> None:
        """Test update with nonexistent config directory."""
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["config", "update", "--config-dir", "/nonexistent/path"],
        )

        assert result.exit_code == 1
        assert "Config directory not found" in result.output

    @patch("subprocess.run")
    def test_update_confirmation_prompt(
        self, mock_subprocess: Mock, mock_config_dir: Path, mock_repo_dir: Path
    ) -> None:
        """Test update prompts for confirmation without --yes."""

        def git_clone_side_effect(cmd: list[str], **_kwargs: object) -> Mock:
            if "clone" in cmd:
                target_dir = Path(cmd[-1])
                target_dir.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(mock_repo_dir, target_dir)
            result = Mock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        mock_subprocess.side_effect = git_clone_side_effect

        runner = CliRunner()
        # Decline the confirmation
        result = runner.invoke(
            app,
            ["config", "update", "--config-dir", str(mock_config_dir)],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Update cancelled" in result.output

        # Verify files weren't updated
        cisco_file = mock_config_dir / "sequences/cisco_iosxe/common.yml"
        assert "UPDATED" not in cisco_file.read_text()
