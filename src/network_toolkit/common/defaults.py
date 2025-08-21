# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Default values and constants for the network toolkit."""

from __future__ import annotations

from pathlib import Path

# Default configuration path used by all commands
# When this path is used, the system will automatically search:
# 1. Current working directory for "./config/" or "./devices.yml"
# 2. Platform-specific user config directory (e.g., ~/.config/networka/)
DEFAULT_CONFIG_PATH = Path("config")

# Legacy fallback for backward compatibility
LEGACY_CONFIG_PATH = Path("devices.yml")
