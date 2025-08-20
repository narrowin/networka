# SPDX-License-Identifier: MIT
"""Platform abstraction layer for vendor-specific network device operations."""

from network_toolkit.platforms.base import PlatformOperations, UnsupportedOperationError
from network_toolkit.platforms.factory import (
    check_operation_support,
    get_platform_file_extensions,
    get_platform_operations,
    get_supported_platforms,
    is_platform_supported,
)

__all__ = [
    "PlatformOperations",
    "UnsupportedOperationError",
    "check_operation_support",
    "get_platform_file_extensions",
    "get_platform_operations",
    "get_supported_platforms",
    "is_platform_supported",
]
