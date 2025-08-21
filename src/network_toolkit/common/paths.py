"""OS-specific application paths for Networka.

Provides best-practice user directories using platform-native locations:
- Linux: ~/.config/networka
- macOS: ~/Library/Application Support/networka
- Windows: %APPDATA%/networka (roaming) or %LOCALAPPDATA%/networka

We rely on `platformdirs` for correct behavior across platforms,
fallbacking to simple heuristics if not available.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # Prefer platformdirs if available
    from platformdirs import PlatformDirs as _PlatformDirs  # type: ignore
except Exception:  # pragma: no cover - fallback only
    _PlatformDirs = None


APP_NAME = "networka"
APP_AUTHOR = "narrowin"


def default_config_root() -> Path:
    """Return the user-level configuration root directory for the app.

    Uses platform-appropriate directories (XDG on Linux, AppData on Windows,
    Application Support on macOS). Ensures the base app directory name is
    'networka'. The directory is not created implicitly.
    """
    if _PlatformDirs is not None:  # pragma: no branch
        dirs: Any = _PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)
        user_cfg = getattr(dirs, "user_config_dir", None)
        if user_cfg:
            return Path(str(user_cfg))

    # Fallbacks without platformdirs
    home = Path.home()
    if (home / "Library" / "Application Support").exists():  # macOS heuristic
        return home / "Library" / "Application Support" / APP_NAME
    if (home / ".config").exists():  # Linux heuristic (XDG)
        return home / ".config" / APP_NAME
    # Windows or other: prefer AppData/Roaming if present
    appdata = Path.home() / "AppData" / "Roaming"
    if appdata.exists():
        return appdata / APP_NAME
    return home / f".{APP_NAME}"


def default_modular_config_dir() -> Path:
    """Return the directory that contains the modular config files.

    By convention we use `<config_root>/config` for YAML files and subfolders.
    """
    return default_config_root() / "config"


def user_sequences_dir() -> Path:
    """Return the directory to look for user-defined vendor sequences.

    By convention we use `<config_root>/config/sequences`.
    """
    return default_modular_config_dir() / "sequences"
