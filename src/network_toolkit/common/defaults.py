# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Default values and constants for the network toolkit."""

from __future__ import annotations

from network_toolkit.common.paths import default_modular_config_dir

# Default configuration path used by all commands
# New behavior: only use the platform-specific user config directory
# (e.g., ~/.config/networka) unless an explicit --config path is provided.
DEFAULT_CONFIG_PATH = default_modular_config_dir()

# Legacy single-file mode has been removed; no legacy path constant
