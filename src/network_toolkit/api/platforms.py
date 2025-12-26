"""Programmatic API for platform operations."""

from __future__ import annotations

from dataclasses import dataclass

from network_toolkit.platforms.registry import (
    PLATFORM_REGISTRY,
    PlatformCapabilities,
    PlatformInfo,
    PlatformStatus,
    get_platforms_by_status,
    get_platforms_by_vendor,
    get_platforms_with_capability,
)


@dataclass
class PlatformListOptions:
    """Options for listing platforms."""

    status: str | None = None
    vendor: str | None = None
    capability: str | None = None


@dataclass
class PlatformSummary:
    """Summary information about a platform for list display."""

    device_type: str
    display_name: str
    vendor: str
    status: PlatformStatus
    config_backup: bool
    firmware_upgrade: bool
    comprehensive_backup: bool


@dataclass
class PlatformListResult:
    """Result of listing platforms."""

    platforms: list[PlatformSummary]
    total_count: int


@dataclass
class PlatformDetails:
    """Detailed information about a specific platform."""

    device_type: str
    display_name: str
    vendor: str
    description: str
    status: PlatformStatus
    operations_class: str | None
    firmware_extensions: list[str]
    capabilities: PlatformCapabilities
    docs_path: str | None


class PlatformFilterError(Exception):
    """Error when filtering platforms with invalid parameters."""

    def __init__(self, message: str, valid_values: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.valid_values = valid_values


def list_platforms(options: PlatformListOptions | None = None) -> PlatformListResult:
    """List platforms with optional filtering.

    Args:
        options: Filtering options for status, vendor, or capability

    Returns:
        PlatformListResult with matching platforms

    Raises:
        PlatformFilterError: If filter value is invalid
    """
    if options is None:
        options = PlatformListOptions()

    platform_dict: dict[str, PlatformInfo]

    if options.status:
        status_lower = options.status.lower()
        try:
            status_enum = PlatformStatus(status_lower)
        except ValueError:
            msg = f"Invalid status: {options.status}"
            raise PlatformFilterError(
                msg,
                valid_values=[
                    "implemented",
                    "planned",
                    "sequences_only",
                    "experimental",
                ],
            ) from None
        platform_dict = get_platforms_by_status(status_enum)

    elif options.vendor:
        platforms = get_platforms_by_vendor(options.vendor.lower())
        if not platforms:
            msg = f"No platforms found for vendor: {options.vendor}"
            raise PlatformFilterError(msg)
        platform_dict = {p.device_type: p for p in platforms}

    elif options.capability:
        valid_capabilities = [
            "config_backup",
            "firmware_upgrade",
            "comprehensive_backup",
        ]
        if options.capability not in valid_capabilities:
            msg = f"Invalid capability: {options.capability}"
            raise PlatformFilterError(msg, valid_values=valid_capabilities)
        platforms = get_platforms_with_capability(options.capability)
        platform_dict = {p.device_type: p for p in platforms}

    else:
        platform_dict = PLATFORM_REGISTRY

    # Convert to summary objects, sorted by vendor then name
    summaries = []
    for device_type in sorted(
        platform_dict.keys(),
        key=lambda p: (platform_dict[p].vendor, p),
    ):
        info = platform_dict[device_type]
        summaries.append(
            PlatformSummary(
                device_type=device_type,
                display_name=info.display_name,
                vendor=info.vendor,
                status=info.status,
                config_backup=info.capabilities.config_backup,
                firmware_upgrade=info.capabilities.firmware_upgrade,
                comprehensive_backup=info.capabilities.comprehensive_backup,
            )
        )

    return PlatformListResult(platforms=summaries, total_count=len(summaries))


def get_platform_details(device_type: str) -> PlatformDetails | None:
    """Get detailed information about a specific platform.

    Args:
        device_type: The platform device type identifier

    Returns:
        PlatformDetails if found, None otherwise
    """
    if device_type not in PLATFORM_REGISTRY:
        return None

    info = PLATFORM_REGISTRY[device_type]

    return PlatformDetails(
        device_type=device_type,
        display_name=info.display_name,
        vendor=info.vendor,
        description=info.description,
        status=info.status,
        operations_class=info.operations_class,
        firmware_extensions=info.firmware_extensions,
        capabilities=info.capabilities,
        docs_path=info.docs_path,
    )
