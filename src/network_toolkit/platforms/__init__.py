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
from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformCapabilities,
    PlatformInfo,
    PlatformStatus,
    get_implemented_platforms,
    get_platform_info,
    get_platforms_by_status,
    get_platforms_by_vendor,
    get_platforms_with_capability,
    get_supported_device_types,
    validate_registry,
)

__all__ = [
    # Registry (NEW - Single source of truth)
    "PLATFORM_REGISTRY",
    "PlatformCapabilities",
    "PlatformInfo",
    # Base classes
    "PlatformOperations",
    "PlatformStatus",
    "UnsupportedOperationError",
    # Factory functions (will be updated to use registry)
    "check_operation_support",
    "get_implemented_platforms",
    "get_platform_file_extensions",
    "get_platform_info",
    "get_platform_operations",
    "get_platforms_by_status",
    "get_platforms_by_vendor",
    "get_platforms_with_capability",
    "get_supported_device_types",
    "get_supported_platforms",
    "is_platform_supported",
    "validate_registry",
]
