"""CLI discovery of generated modular configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from network_toolkit.cli import app


class TestCLIWithRealConfig:
    @pytest.mark.parametrize("path", ["./config", "./config/config.yml"])
    def test_list_devices_with_modular_config(
        self, path: str, mock_repo_config: Path
    ) -> None:
        """Directory and config.yml paths load the devices in the same inventory."""
        result = CliRunner().invoke(app, ["list", "devices", "-c", path])

        assert result.exit_code == 0, result.output
        assert "router1" in result.output
        assert "switch1" in result.output
        assert "192.168.1.1" in result.output
        assert "192.168.1.2" in result.output

    @pytest.mark.parametrize(
        "config_args", [[], ["-c", "./config"], ["-c", "./config/config.yml"]]
    )
    def test_list_sequences_with_modular_config(
        self,
        config_args: list[str],
        config_file: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Default discovery, directory and file paths expose local vendor sequences."""
        monkeypatch.delenv("NW_CONFIG_DIR", raising=False)
        monkeypatch.chdir(config_file.parent.parent)
        sequences = config_file.parent / "sequences" / "mikrotik_routeros"
        sequences.mkdir()
        (sequences / "local.yml").write_text(
            "sequences:\n  local_check:\n    description: Local sequence\n"
            "    commands:\n      - /system/identity/print\n",
            encoding="utf-8",
        )

        result = CliRunner().invoke(
            app, ["list", "sequences", "--vendor", "mikrotik_routeros", *config_args]
        )

        assert result.exit_code == 0, result.output
        assert "local_check" in result.output
        assert "Local sequence" in result.output
