"""Configuration manifest for tracking installed framework files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class FrameworkFileInfo:
    """Information about a framework-managed file."""

    checksum: str
    installed_version: str
    installed_at: str = field(default_factory=lambda: datetime.now(tz=UTC).isoformat())


@dataclass
class ConfigManifest:
    """Manifest tracking framework files installed in user config.

    This tracks only framework-managed files to detect modifications
    and enable safe updates.
    """

    version: str
    installed_at: str
    framework_files: dict[str, FrameworkFileInfo] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "version": self.version,
            "installed_at": self.installed_at,
            "framework_files": {
                path: {
                    "checksum": info.checksum,
                    "installed_version": info.installed_version,
                    "installed_at": info.installed_at,
                }
                for path, info in self.framework_files.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> ConfigManifest:
        """Load from dictionary."""
        framework_files = {}
        for path, info in data.get("framework_files", {}).items():
            framework_files[path] = FrameworkFileInfo(
                checksum=info["checksum"],
                installed_version=info["installed_version"],
                installed_at=info.get("installed_at", ""),
            )

        return cls(
            version=data["version"],
            installed_at=data["installed_at"],
            framework_files=framework_files,
        )

    def save(self, path: Path) -> None:
        """Save manifest to file."""
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> ConfigManifest:
        """Load manifest from file."""
        data = json.loads(path.read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def create_new(cls, version: str) -> ConfigManifest:
        """Create new manifest for fresh installation."""
        return cls(
            version=version,
            installed_at=datetime.now(tz=UTC).isoformat(),
            framework_files={},
        )

    def add_file(self, rel_path: str, checksum: str, version: str) -> None:
        """Add or update a framework file in the manifest."""
        self.framework_files[rel_path] = FrameworkFileInfo(
            checksum=checksum,
            installed_version=version,
        )

    def get_file_info(self, rel_path: str) -> FrameworkFileInfo | None:
        """Get info for a specific file."""
        return self.framework_files.get(rel_path)

    def is_file_tracked(self, rel_path: str) -> bool:
        """Check if file is tracked as framework file."""
        return rel_path in self.framework_files

    def remove_file(self, rel_path: str) -> None:
        """Remove file from tracking."""
        self.framework_files.pop(rel_path, None)
