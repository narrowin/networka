from __future__ import annotations

from pathlib import Path

import yaml
from typer.testing import CliRunner

from network_toolkit.cli import app


def _write_yaml(path: Path, content: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(content, f)


def test_cli_inventory_option_is_additive_and_sources_are_shown() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        cwd = Path.cwd()
        config_path = cwd / "config.yml"
        _write_yaml(
            config_path,
            {
                "inventory": {"discover_local": False},
                "devices": {"cfgdev": {"host": "1.1.1.1", "device_type": "linux"}},
            },
        )

        inv_dir = cwd / "inv1"
        _write_yaml(
            inv_dir / "hosts.yml",
            {"invdev": {"hostname": "2.2.2.2", "platform": "linux"}},
        )

        result = runner.invoke(
            app,
            [
                "--inventory",
                str(inv_dir),
                "list",
                "devices",
                "--config",
                str(config_path),
                "--output-mode",
                "raw",
            ],
        )

        assert result.exit_code == 0
        assert "device=cfgdev source=config" in result.output
        assert "device=invdev source=cli:inv1" in result.output
