"""Test that config_source_dir is properly set and used by SequenceManager."""

from pathlib import Path

from network_toolkit.config import (
    create_minimal_config,
    load_config,
    load_modular_config,
)
from network_toolkit.sequence_manager import SequenceManager


def test_config_source_dir_set_by_load_modular_config(tmp_path: Path) -> None:
    """Test that load_modular_config sets _config_source_dir."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal config.yml
    config_file = config_dir / "config.yml"
    config_file.write_text("general: {}\n", encoding="utf-8")

    # Load config
    config = load_modular_config(config_dir)

    # Verify _config_source_dir is set
    assert hasattr(config, "_config_source_dir")
    assert config._config_source_dir == config_dir


def test_config_source_dir_set_by_load_config_directory(tmp_path: Path) -> None:
    """Test that load_config sets _config_source_dir when given a directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal config.yml
    config_file = config_dir / "config.yml"
    config_file.write_text("general: {}\n", encoding="utf-8")

    # Load config via load_config (which calls load_modular_config)
    config = load_config(config_dir)

    # Verify _config_source_dir is set
    assert hasattr(config, "_config_source_dir")
    assert config._config_source_dir == config_dir


def test_config_source_dir_set_by_load_config_file(tmp_path: Path) -> None:
    """Test that load_config sets _config_source_dir when given a file path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create minimal config.yml
    config_file = config_dir / "config.yml"
    config_file.write_text("general: {}\n", encoding="utf-8")

    # Load config via file path
    config = load_config(config_file)

    # Verify _config_source_dir is set to parent directory
    assert hasattr(config, "_config_source_dir")
    assert config._config_source_dir == config_dir


def test_config_source_dir_none_for_minimal_config() -> None:
    """Test that create_minimal_config leaves _config_source_dir as None."""
    config = create_minimal_config()

    # Verify _config_source_dir exists but is None
    assert hasattr(config, "_config_source_dir")
    assert config._config_source_dir is None


def test_sequence_manager_uses_config_source_dir(tmp_path: Path) -> None:
    """Test that SequenceManager uses _config_source_dir for repo sequences."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create sequences directory with a vendor subdirectory
    sequences_dir = config_dir / "sequences"
    sequences_dir.mkdir()
    vendor_dir = sequences_dir / "mikrotik_routeros"
    vendor_dir.mkdir()

    # Create a test sequence file
    sequence_file = vendor_dir / "common.yml"
    sequence_file.write_text(
        """sequences:
  test_seq:
    description: "Test sequence from config"
    commands:
      - "/system/identity/print"
""",
        encoding="utf-8",
    )

    # Create minimal config.yml with vendor_platforms
    config_file = config_dir / "config.yml"
    config_file.write_text(
        """general: {}
""",
        encoding="utf-8",
    )

    # Create sequences.yml with vendor_platforms
    sequences_yml = config_dir / "sequences.yml"
    sequences_yml.write_text(
        """vendor_platforms:
  mikrotik_routeros:
    description: "MikroTik RouterOS"
    sequence_path: "sequences/mikrotik_routeros"
    default_files: ["common.yml"]
""",
        encoding="utf-8",
    )

    # Load config
    config = load_modular_config(config_dir)

    # Create SequenceManager
    sm = SequenceManager(config)

    # Verify repo sequences are loaded
    mikrotik_seqs = sm.list_vendor_sequences("mikrotik_routeros")
    assert "test_seq" in mikrotik_seqs
    assert mikrotik_seqs["test_seq"].description == "Test sequence from config"


def test_sequence_manager_fallback_when_no_config_source_dir() -> None:
    """Test that SequenceManager gracefully handles None _config_source_dir."""
    config = create_minimal_config()

    # Create SequenceManager - should not crash
    sm = SequenceManager(config)

    # Should still load builtin sequences
    mikrotik_seqs = sm.list_vendor_sequences("mikrotik_routeros")

    # Should have builtin sequences (even if no repo sequences)
    # At minimum, builtin sequences should exist
    assert isinstance(mikrotik_seqs, dict)
