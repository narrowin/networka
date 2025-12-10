# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Network Toolkit - Network automation made simple for MikroTik (and beyond)."""

from network_toolkit.__about__ import __version__
from network_toolkit.client import NetworkaClient

__all__ = ["NetworkaClient", "__version__"]
