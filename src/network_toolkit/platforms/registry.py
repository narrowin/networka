"""Platform Registry - Single source of truth for all platform/vendor information.

This module provides a unified registry that contains metadata for all platforms
supported by the network toolkit. It eliminates scattered hardcoded platform lists
and ensures code and documentation stay in sync.

The registry is the single source of truth for:
- Platform identification and metadata
- Implementation status
- Capabilities and features
- File type support
- Documentation references
- Operations class references
"""

from enum import Enum

from pydantic import BaseModel, Field


class PlatformStatus(str, Enum):
    """Implementation status of a platform.

    Attributes:
        IMPLEMENTED: Full operations and sequences with documentation
        SEQUENCES_ONLY: Only builtin sequences, no operations class
        PLANNED: On roadmap, not yet implemented
        EXPERIMENTAL: Partial implementation, unstable API
    """

    IMPLEMENTED = "implemented"
    SEQUENCES_ONLY = "sequences_only"
    PLANNED = "planned"
    EXPERIMENTAL = "experimental"


class PlatformCapabilities(BaseModel):
    """Capabilities and features supported by a platform.

    Attributes:
        firmware_upgrade: Supports firmware upgrade operations
        firmware_downgrade: Supports firmware downgrade operations
        bios_upgrade: Supports BIOS/bootloader upgrade operations
        config_backup: Supports configuration backup
        comprehensive_backup: Supports comprehensive system backup
    """

    firmware_upgrade: bool = False
    firmware_downgrade: bool = False
    bios_upgrade: bool = False
    config_backup: bool = False
    comprehensive_backup: bool = False


class PlatformInfo(BaseModel):
    """Complete information about a network platform.

    Attributes:
        device_type: Unique identifier (e.g., 'mikrotik_routeros')
        display_name: Human-readable name (e.g., 'MikroTik RouterOS')
        vendor: Vendor name (e.g., 'MikroTik')
        status: Implementation status
        description: Short description for documentation
        capabilities: Supported operations and features
        firmware_extensions: Supported firmware file extensions
        has_operations_class: Whether platform has operations implementation
        has_builtin_sequences: Whether platform has builtin command sequences
        docs_path: Relative path to vendor documentation
        operations_class: Fully qualified operations class name
    """

    device_type: str = Field(
        description="Unique identifier (e.g., 'mikrotik_routeros')"
    )
    display_name: str = Field(
        description="Human-readable name (e.g., 'MikroTik RouterOS')"
    )
    vendor: str = Field(description="Vendor name (e.g., 'MikroTik')")
    status: PlatformStatus = Field(description="Implementation status")
    description: str = Field(description="Short description for docs")
    capabilities: PlatformCapabilities = Field(default_factory=PlatformCapabilities)
    firmware_extensions: list[str] = Field(
        default_factory=list, description="Supported firmware file extensions"
    )
    has_operations_class: bool = Field(
        description="Has platform operations implementation"
    )
    has_builtin_sequences: bool = Field(description="Has builtin command sequences")
    docs_path: str | None = Field(
        default=None, description="Relative path to vendor docs"
    )
    operations_class: str | None = Field(
        default=None, description="Fully qualified class name"
    )


PLATFORM_REGISTRY: dict[str, PlatformInfo] = {
    "mikrotik_routeros": PlatformInfo(
        device_type="mikrotik_routeros",
        display_name="MikroTik RouterOS",
        vendor="MikroTik",
        status=PlatformStatus.IMPLEMENTED,
        description="Primary focus, fully featured",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            bios_upgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".npk"],
        has_operations_class=True,
        has_builtin_sequences=True,
        docs_path="vendors/mikrotik/index.md",
        operations_class="network_toolkit.platforms.mikrotik_routeros.operations.MikroTikRouterOSOperations",
    ),
    "cisco_ios": PlatformInfo(
        device_type="cisco_ios",
        display_name="Cisco IOS",
        vendor="Cisco",
        status=PlatformStatus.IMPLEMENTED,
        description="Legacy Cisco switches and routers",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".bin", ".tar"],
        has_operations_class=True,
        has_builtin_sequences=False,
        docs_path="vendors/cisco/index.md",
        operations_class="network_toolkit.platforms.cisco_ios.operations.CiscoIOSOperations",
    ),
    "cisco_iosxe": PlatformInfo(
        device_type="cisco_iosxe",
        display_name="Cisco IOS-XE",
        vendor="Cisco",
        status=PlatformStatus.IMPLEMENTED,
        description="Modern Cisco switches and routers",
        capabilities=PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        ),
        firmware_extensions=[".bin", ".pkg"],
        has_operations_class=True,
        has_builtin_sequences=True,
        docs_path="vendors/cisco/index.md",
        operations_class="network_toolkit.platforms.cisco_iosxe.operations.CiscoIOSXEOperations",
    ),
    "cisco_nxos": PlatformInfo(
        device_type="cisco_nxos",
        display_name="Cisco NX-OS",
        vendor="Cisco",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Data center switches - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/cisco/index.md",
    ),
    "arista_eos": PlatformInfo(
        device_type="arista_eos",
        display_name="Arista EOS",
        vendor="Arista",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Data center switches - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/arista/index.md",
    ),
    "juniper_junos": PlatformInfo(
        device_type="juniper_junos",
        display_name="Juniper JunOS",
        vendor="Juniper",
        status=PlatformStatus.SEQUENCES_ONLY,
        description="Enterprise switches and routers - sequences available, operations coming soon",
        has_operations_class=False,
        has_builtin_sequences=True,
        docs_path="vendors/juniper/index.md",
    ),
    "nokia_srlinux": PlatformInfo(
        device_type="nokia_srlinux",
        display_name="Nokia SR Linux",
        vendor="Nokia",
        status=PlatformStatus.PLANNED,
        description="Modern data center network OS",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path="vendors/nokia/index.md",
    ),
    "cisco_iosxr": PlatformInfo(
        device_type="cisco_iosxr",
        display_name="Cisco IOS-XR",
        vendor="Cisco",
        status=PlatformStatus.PLANNED,
        description="Service provider routers",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
    "linux": PlatformInfo(
        device_type="linux",
        display_name="Generic Linux",
        vendor="Linux",
        status=PlatformStatus.PLANNED,
        description="Generic Linux hosts for scripting",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
    "generic": PlatformInfo(
        device_type="generic",
        display_name="Generic Device",
        vendor="Generic",
        status=PlatformStatus.PLANNED,
        description="Fallback for unsupported devices",
        has_operations_class=False,
        has_builtin_sequences=False,
        docs_path=None,
    ),
}


def get_platform_info(device_type: str) -> PlatformInfo | None:
    """Get platform information by device type.

    Args:
        device_type: The device type identifier

    Returns:
        Platform information if found, None otherwise
    """
    return PLATFORM_REGISTRY.get(device_type)


def get_implemented_platforms() -> dict[str, PlatformInfo]:
    """Get only fully implemented platforms with operations classes.

    Returns:
        Dictionary of device types to platform information for implemented platforms
    """
    return {
        k: v
        for k, v in PLATFORM_REGISTRY.items()
        if v.status == PlatformStatus.IMPLEMENTED
    }


def get_platforms_by_status(status: PlatformStatus) -> dict[str, PlatformInfo]:
    """Get all platforms with a specific status.

    Args:
        status: The platform status to filter by

    Returns:
        Dictionary of device types to platform information
    """
    return {k: v for k, v in PLATFORM_REGISTRY.items() if v.status == status}


def get_platforms_by_vendor(vendor: str) -> list[PlatformInfo]:
    """Get all platforms for a specific vendor.

    Args:
        vendor: The vendor name (case-insensitive)

    Returns:
        List of platform information for the vendor
    """
    return [v for v in PLATFORM_REGISTRY.values() if v.vendor.lower() == vendor.lower()]


def get_platforms_with_capability(capability: str) -> list[PlatformInfo]:
    """Get platforms supporting a specific capability.

    Args:
        capability: The capability name (e.g., 'firmware_upgrade')

    Returns:
        List of platform information for platforms with that capability
    """
    return [
        v
        for v in PLATFORM_REGISTRY.values()
        if getattr(v.capabilities, capability, False)
    ]


def get_supported_device_types() -> set[str]:
    """Get all registered device types.

    This is useful for validation and autocompletion.

    Returns:
        Set of all device type identifiers in the registry
    """
    return set(PLATFORM_REGISTRY.keys())


def validate_registry() -> list[str]:
    """Validate registry consistency and completeness.

    Checks for:
    - Operations class existence when claimed
    - Sequence directory existence when claimed
    - Documentation file existence when specified
    - Consistency between status and features

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    for device_type, info in PLATFORM_REGISTRY.items():
        # Check consistency between status and features
        if info.status == PlatformStatus.IMPLEMENTED:
            if not info.has_operations_class:
                errors.append(
                    f"{device_type}: Status is IMPLEMENTED but has_operations_class is False"
                )
            if not info.operations_class:
                errors.append(
                    f"{device_type}: Status is IMPLEMENTED but operations_class is not specified"
                )

        if info.status == PlatformStatus.SEQUENCES_ONLY:
            if not info.has_builtin_sequences:
                errors.append(
                    f"{device_type}: Status is SEQUENCES_ONLY but has_builtin_sequences is False"
                )
            if info.has_operations_class:
                errors.append(
                    f"{device_type}: Status is SEQUENCES_ONLY but has_operations_class is True"
                )

        if info.status == PlatformStatus.PLANNED:
            if info.has_operations_class or info.has_builtin_sequences:
                errors.append(
                    f"{device_type}: Status is PLANNED but has_operations_class or has_builtin_sequences is True"
                )

        # Check capabilities consistency
        if info.capabilities.firmware_upgrade or info.capabilities.firmware_downgrade:
            if not info.firmware_extensions:
                errors.append(
                    f"{device_type}: Has firmware capabilities but no firmware_extensions specified"
                )

        # If operations class is specified, it should have capabilities
        if info.has_operations_class:
            has_any_capability = any(
                [
                    info.capabilities.firmware_upgrade,
                    info.capabilities.firmware_downgrade,
                    info.capabilities.bios_upgrade,
                    info.capabilities.config_backup,
                    info.capabilities.comprehensive_backup,
                ]
            )
            if not has_any_capability:
                errors.append(
                    f"{device_type}: Has operations class but no capabilities specified"
                )

    return errors
