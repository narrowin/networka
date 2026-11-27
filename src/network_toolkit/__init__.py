# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Networka - Network automation made simple for MikroTik (and beyond)."""

import logging

from network_toolkit.__about__ import __version__
from network_toolkit.client import NetworkaClient
from network_toolkit.common.credentials import InteractiveCredentials
from network_toolkit.device import DeviceSession
from network_toolkit.exceptions import (
    DeviceConnectionError,
    DeviceExecutionError,
    FileTransferError,
    NetworkToolkitError,
)
from network_toolkit.ip_device import create_ip_based_config

# A library leaves log output to the application. Without a handler, Python's
# last-resort handler prints Networka and Scrapli warnings to stderr.
for _logger_name in ("network_toolkit", "scrapli"):
    logging.getLogger(_logger_name).addHandler(logging.NullHandler())

__all__ = [
    "DeviceConnectionError",
    "DeviceExecutionError",
    "DeviceSession",
    "FileTransferError",
    "InteractiveCredentials",
    "NetworkToolkitError",
    "NetworkaClient",
    "__version__",
    "create_ip_based_config",
]
