"""OS-specific application paths for Networka.

Provides best-practice user directories using platform-native locations:
- Linux: ~/.config/networka
- macOS: ~/Library/Application Support/networka
- Windows: %APPDATA%/networka (roaming)

We rely on `platformdirs` for correct behavior across platforms,
with sensible fallbacks for environments where it's not available.

The networka configuration follows these conventions:
- App root: OS-specific user config directory + '/networka'
- Config files: App root + '/config/' (contains config.yml, devices/, groups/, sequences/)
- Environment file: App root + '/.env'
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # Prefer platformdirs if available
    from platformdirs import PlatformDirs as _PlatformDirs  # type: ignore

    _has_platformdirs = True
except Exception:  # pragma: no cover - fallback only
    _PlatformDirs = None  # type: ignore[misc,assignment]
    _has_platformdirs = False


APP_NAME = "networka"
APP_AUTHOR = "narrowin"


def default_config_root() -> Path:
    """Return the user-level configuration root directory for the app.

    Uses platform-appropriate directories (XDG on Linux, AppData on Windows,
    Application Support on macOS). Ensures the base app directory name is
    'networka'. The directory is not created implicitly.

    Returns the app root directory where both config/ and .env will be stored.
    """
    if _has_platformdirs:  # pragma: no branch
        dirs: Any = _PlatformDirs(appname=APP_NAME, appauthor=APP_AUTHOR, roaming=True)  # type: ignore[misc]
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


def default_app_root() -> Path:
    """Return the user-level app root directory for networka.

    This is the same as default_config_root() but provided for clarity.
    Contains both config/ subdirectory and .env file.
    """
    return default_config_root()


def default_modular_config_dir() -> Path:
    """Return the directory that contains the modular config files.

    This returns the app root directory where config.yml, devices/, groups/,
    and sequences/ are stored directly (not in a nested config/ subdirectory).
    """
    return default_config_root()


def user_sequences_dir() -> Path:
    """Return the directory to look for user-defined vendor sequences.

    This is the sequences/ directory within the app root.
    """
    return default_modular_config_dir() / "sequences"
