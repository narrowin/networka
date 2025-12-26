# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Tests for the platforms API module."""

from __future__ import annotations

import pytest

from network_toolkit.api.platforms import (
    PlatformDetails,
    PlatformFilterError,
    PlatformListOptions,
    PlatformListResult,
    PlatformSummary,
    get_platform_details,
    list_platforms,
)
from network_toolkit.platforms.registry import PlatformStatus


class TestListPlatforms:
    """Tests for the list_platforms function."""

    def test_list_all_platforms(self) -> None:
        """Test listing all platforms without filters."""
        result = list_platforms()
        assert isinstance(result, PlatformListResult)
        assert result.total_count > 0
        assert len(result.platforms) == result.total_count
        # Check all items are PlatformSummary
        for platform in result.platforms:
            assert isinstance(platform, PlatformSummary)

    def test_list_platforms_with_none_options(self) -> None:
        """Test listing platforms with None options."""
        result = list_platforms(None)
        assert isinstance(result, PlatformListResult)
        assert result.total_count > 0

    def test_list_platforms_empty_options(self) -> None:
        """Test listing platforms with empty options."""
        result = list_platforms(PlatformListOptions())
        assert isinstance(result, PlatformListResult)
        assert result.total_count > 0

    def test_filter_by_implemented_status(self) -> None:
        """Test filtering by implemented status."""
        options = PlatformListOptions(status="implemented")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.status == PlatformStatus.IMPLEMENTED

    def test_filter_by_planned_status(self) -> None:
        """Test filtering by planned status."""
        options = PlatformListOptions(status="planned")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.status == PlatformStatus.PLANNED

    def test_filter_by_sequences_only_status(self) -> None:
        """Test filtering by sequences_only status."""
        options = PlatformListOptions(status="sequences_only")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.status == PlatformStatus.SEQUENCES_ONLY

    def test_filter_by_status_case_insensitive(self) -> None:
        """Test that status filtering is case insensitive."""
        options = PlatformListOptions(status="IMPLEMENTED")
        result = list_platforms(options)
        assert result.total_count > 0

    def test_filter_by_invalid_status_raises_error(self) -> None:
        """Test that invalid status raises PlatformFilterError."""
        options = PlatformListOptions(status="invalid")
        with pytest.raises(PlatformFilterError) as exc_info:
            list_platforms(options)
        assert "Invalid status" in exc_info.value.message
        assert exc_info.value.valid_values is not None
        assert "implemented" in exc_info.value.valid_values

    def test_filter_by_cisco_vendor(self) -> None:
        """Test filtering by cisco vendor."""
        options = PlatformListOptions(vendor="cisco")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.vendor.lower() == "cisco"

    def test_filter_by_mikrotik_vendor(self) -> None:
        """Test filtering by mikrotik vendor."""
        options = PlatformListOptions(vendor="mikrotik")
        result = list_platforms(options)
        assert result.total_count == 1
        assert result.platforms[0].device_type == "mikrotik_routeros"

    def test_filter_by_vendor_case_insensitive(self) -> None:
        """Test that vendor filtering is case insensitive."""
        options = PlatformListOptions(vendor="CISCO")
        result = list_platforms(options)
        assert result.total_count > 0

    def test_filter_by_nonexistent_vendor_raises_error(self) -> None:
        """Test that nonexistent vendor raises PlatformFilterError."""
        options = PlatformListOptions(vendor="nonexistent")
        with pytest.raises(PlatformFilterError) as exc_info:
            list_platforms(options)
        assert "No platforms found for vendor" in exc_info.value.message

    def test_filter_by_config_backup_capability(self) -> None:
        """Test filtering by config_backup capability."""
        options = PlatformListOptions(capability="config_backup")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.config_backup is True

    def test_filter_by_firmware_upgrade_capability(self) -> None:
        """Test filtering by firmware_upgrade capability."""
        options = PlatformListOptions(capability="firmware_upgrade")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.firmware_upgrade is True

    def test_filter_by_comprehensive_backup_capability(self) -> None:
        """Test filtering by comprehensive_backup capability."""
        options = PlatformListOptions(capability="comprehensive_backup")
        result = list_platforms(options)
        assert result.total_count > 0
        for platform in result.platforms:
            assert platform.comprehensive_backup is True

    def test_filter_by_invalid_capability_raises_error(self) -> None:
        """Test that invalid capability raises PlatformFilterError."""
        options = PlatformListOptions(capability="invalid_capability")
        with pytest.raises(PlatformFilterError) as exc_info:
            list_platforms(options)
        assert "Invalid capability" in exc_info.value.message
        assert exc_info.value.valid_values is not None
        assert "config_backup" in exc_info.value.valid_values

    def test_platforms_sorted_by_vendor_then_name(self) -> None:
        """Test that platforms are sorted by vendor, then by device type."""
        result = list_platforms()
        vendors = [p.vendor for p in result.platforms]
        # Check vendor ordering is non-decreasing
        for i in range(1, len(vendors)):
            if vendors[i - 1] == vendors[i]:
                # Same vendor, check device_type ordering
                assert (
                    result.platforms[i - 1].device_type
                    <= result.platforms[i].device_type
                )
            else:
                assert vendors[i - 1] <= vendors[i]

    def test_platform_summary_has_all_fields(self) -> None:
        """Test that PlatformSummary has all required fields."""
        result = list_platforms()
        assert result.total_count > 0
        platform = result.platforms[0]
        assert hasattr(platform, "device_type")
        assert hasattr(platform, "display_name")
        assert hasattr(platform, "vendor")
        assert hasattr(platform, "status")
        assert hasattr(platform, "config_backup")
        assert hasattr(platform, "firmware_upgrade")
        assert hasattr(platform, "comprehensive_backup")


class TestGetPlatformDetails:
    """Tests for the get_platform_details function."""

    def test_get_mikrotik_routeros_details(self) -> None:
        """Test getting details for mikrotik_routeros."""
        details = get_platform_details("mikrotik_routeros")
        assert details is not None
        assert isinstance(details, PlatformDetails)
        assert details.device_type == "mikrotik_routeros"
        assert details.display_name == "MikroTik RouterOS"
        assert details.vendor == "MikroTik"
        assert details.status == PlatformStatus.IMPLEMENTED
        assert details.operations_class is not None
        assert ".npk" in details.firmware_extensions
        assert details.capabilities.firmware_upgrade is True
        assert details.capabilities.config_backup is True

    def test_get_cisco_ios_details(self) -> None:
        """Test getting details for cisco_ios."""
        details = get_platform_details("cisco_ios")
        assert details is not None
        assert details.device_type == "cisco_ios"
        assert details.vendor == "Cisco"
        assert details.status == PlatformStatus.IMPLEMENTED
        assert ".bin" in details.firmware_extensions

    def test_get_cisco_nxos_details(self) -> None:
        """Test getting details for sequences_only platform."""
        details = get_platform_details("cisco_nxos")
        assert details is not None
        assert details.status == PlatformStatus.SEQUENCES_ONLY
        assert details.operations_class is None

    def test_get_planned_platform_details(self) -> None:
        """Test getting details for planned platform."""
        details = get_platform_details("cisco_iosxr")
        assert details is not None
        assert details.status == PlatformStatus.PLANNED
        assert details.operations_class is None

    def test_get_nonexistent_platform_returns_none(self) -> None:
        """Test that nonexistent platform returns None."""
        details = get_platform_details("nonexistent")
        assert details is None

    def test_platform_details_has_all_fields(self) -> None:
        """Test that PlatformDetails has all required fields."""
        details = get_platform_details("mikrotik_routeros")
        assert details is not None
        assert hasattr(details, "device_type")
        assert hasattr(details, "display_name")
        assert hasattr(details, "vendor")
        assert hasattr(details, "description")
        assert hasattr(details, "status")
        assert hasattr(details, "operations_class")
        assert hasattr(details, "firmware_extensions")
        assert hasattr(details, "capabilities")
        assert hasattr(details, "docs_path")


class TestPlatformFilterError:
    """Tests for PlatformFilterError exception."""

    def test_error_with_message_only(self) -> None:
        """Test creating error with message only."""
        error = PlatformFilterError("Test error")
        assert error.message == "Test error"
        assert error.valid_values is None

    def test_error_with_valid_values(self) -> None:
        """Test creating error with valid values."""
        error = PlatformFilterError("Test error", valid_values=["a", "b", "c"])
        assert error.message == "Test error"
        assert error.valid_values == ["a", "b", "c"]

    def test_error_is_exception(self) -> None:
        """Test that error is an exception."""
        error = PlatformFilterError("Test error")
        assert isinstance(error, Exception)


class TestPublicAPIExports:
    """Tests for public API exports from network_toolkit.api."""

    def test_list_platforms_exported(self) -> None:
        """Test that list_platforms is exported from api."""
        from network_toolkit.api import list_platforms as api_list_platforms

        assert api_list_platforms is list_platforms

    def test_get_platform_details_exported(self) -> None:
        """Test that get_platform_details is exported from api."""
        from network_toolkit.api import get_platform_details as api_get_details

        assert api_get_details is get_platform_details

    def test_dataclasses_exported(self) -> None:
        """Test that dataclasses are exported from api."""
        from network_toolkit.api import (
            PlatformDetails,
            PlatformFilterError,
            PlatformListOptions,
            PlatformListResult,
            PlatformSummary,
        )

        assert PlatformDetails is not None
        assert PlatformFilterError is not None
        assert PlatformListOptions is not None
        assert PlatformListResult is not None
        assert PlatformSummary is not None


__all__ = [
    "TestGetPlatformDetails",
    "TestListPlatforms",
    "TestPlatformFilterError",
    "TestPublicAPIExports",
]
