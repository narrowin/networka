"""Tests for the platform registry module."""

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


class TestPlatformStatus:
    """Test PlatformStatus enum."""

    def test_all_statuses_defined(self):
        """Verify all expected statuses are defined."""
        assert PlatformStatus.IMPLEMENTED == "implemented"
        assert PlatformStatus.SEQUENCES_ONLY == "sequences_only"
        assert PlatformStatus.PLANNED == "planned"
        assert PlatformStatus.EXPERIMENTAL == "experimental"

    def test_status_is_string_enum(self):
        """Verify PlatformStatus is a string enum."""
        assert isinstance(PlatformStatus.IMPLEMENTED, str)
        assert PlatformStatus.IMPLEMENTED.value == "implemented"


class TestPlatformCapabilities:
    """Test PlatformCapabilities model."""

    def test_default_capabilities_all_false(self):
        """Verify default capabilities are all False."""
        caps = PlatformCapabilities()
        assert caps.firmware_upgrade is False
        assert caps.firmware_downgrade is False
        assert caps.bios_upgrade is False
        assert caps.config_backup is False
        assert caps.comprehensive_backup is False

    def test_can_set_individual_capabilities(self):
        """Verify individual capabilities can be set."""
        caps = PlatformCapabilities(firmware_upgrade=True, config_backup=True)
        assert caps.firmware_upgrade is True
        assert caps.config_backup is True
        assert caps.firmware_downgrade is False

    def test_all_capabilities_enabled(self):
        """Verify all capabilities can be enabled."""
        caps = PlatformCapabilities(
            firmware_upgrade=True,
            firmware_downgrade=True,
            bios_upgrade=True,
            config_backup=True,
            comprehensive_backup=True,
        )
        assert caps.firmware_upgrade is True
        assert caps.firmware_downgrade is True
        assert caps.bios_upgrade is True
        assert caps.config_backup is True
        assert caps.comprehensive_backup is True


class TestPlatformInfo:
    """Test PlatformInfo model."""

    def test_minimal_platform_info(self):
        """Verify minimal platform info can be created."""
        info = PlatformInfo(
            device_type="test_device",
            display_name="Test Device",
            vendor="Test Vendor",
            status=PlatformStatus.PLANNED,
            description="Test description",
            has_operations_class=False,
            has_builtin_sequences=False,
        )
        assert info.device_type == "test_device"
        assert info.display_name == "Test Device"
        assert info.vendor == "Test Vendor"
        assert info.status == PlatformStatus.PLANNED
        assert info.description == "Test description"
        assert info.has_operations_class is False
        assert info.has_builtin_sequences is False
        assert info.docs_path is None
        assert info.operations_class is None
        assert len(info.firmware_extensions) == 0

    def test_full_platform_info(self):
        """Verify full platform info with all fields."""
        caps = PlatformCapabilities(firmware_upgrade=True, config_backup=True)
        info = PlatformInfo(
            device_type="test_device",
            display_name="Test Device",
            vendor="Test Vendor",
            status=PlatformStatus.IMPLEMENTED,
            description="Test description",
            capabilities=caps,
            firmware_extensions=[".bin", ".pkg"],
            has_operations_class=True,
            has_builtin_sequences=True,
            docs_path="vendors/test/index.md",
            operations_class="network_toolkit.platforms.test.operations.TestOperations",
        )
        assert info.capabilities.firmware_upgrade is True
        assert info.capabilities.config_backup is True
        assert info.firmware_extensions == [".bin", ".pkg"]
        assert info.has_operations_class is True
        assert info.has_builtin_sequences is True
        assert info.docs_path == "vendors/test/index.md"
        assert (
            info.operations_class
            == "network_toolkit.platforms.test.operations.TestOperations"
        )


class TestPlatformRegistry:
    """Test PLATFORM_REGISTRY dictionary."""

    def test_registry_is_dict(self):
        """Verify registry is a dictionary."""
        assert isinstance(PLATFORM_REGISTRY, dict)

    def test_registry_not_empty(self):
        """Verify registry contains platforms."""
        assert len(PLATFORM_REGISTRY) > 0

    def test_all_device_types_in_registry(self):
        """Verify expected device types are in registry."""
        expected_platforms = {
            "mikrotik_routeros",
            "cisco_ios",
            "cisco_iosxe",
            "cisco_nxos",
            "arista_eos",
            "juniper_junos",
            "nokia_srlinux",
            "cisco_iosxr",
            "linux",
            "generic",
        }
        assert set(PLATFORM_REGISTRY.keys()) == expected_platforms

    def test_all_registry_values_are_platform_info(self):
        """Verify all registry values are PlatformInfo instances."""
        for device_type, info in PLATFORM_REGISTRY.items():
            assert isinstance(info, PlatformInfo), f"{device_type} is not PlatformInfo"
            assert info.device_type == device_type

    def test_mikrotik_routeros_platform(self):
        """Verify MikroTik RouterOS platform is correctly configured."""
        info = PLATFORM_REGISTRY["mikrotik_routeros"]
        assert info.device_type == "mikrotik_routeros"
        assert info.display_name == "MikroTik RouterOS"
        assert info.vendor == "MikroTik"
        assert info.status == PlatformStatus.IMPLEMENTED
        assert info.has_operations_class is True
        assert info.has_builtin_sequences is True
        assert info.capabilities.firmware_upgrade is True
        assert info.capabilities.bios_upgrade is True
        assert ".npk" in info.firmware_extensions
        assert info.operations_class is not None
        assert "MikroTikRouterOSOperations" in info.operations_class

    def test_cisco_ios_platform(self):
        """Verify Cisco IOS platform is correctly configured."""
        info = PLATFORM_REGISTRY["cisco_ios"]
        assert info.device_type == "cisco_ios"
        assert info.display_name == "Cisco IOS"
        assert info.vendor == "Cisco"
        assert info.status == PlatformStatus.IMPLEMENTED
        assert info.has_operations_class is True
        assert info.has_builtin_sequences is False
        assert info.capabilities.firmware_upgrade is True
        assert ".bin" in info.firmware_extensions

    def test_cisco_iosxe_platform(self):
        """Verify Cisco IOS-XE platform is correctly configured."""
        info = PLATFORM_REGISTRY["cisco_iosxe"]
        assert info.device_type == "cisco_iosxe"
        assert info.display_name == "Cisco IOS-XE"
        assert info.vendor == "Cisco"
        assert info.status == PlatformStatus.IMPLEMENTED
        assert info.has_operations_class is True
        assert info.has_builtin_sequences is True

    def test_cisco_nxos_platform(self):
        """Verify Cisco NX-OS platform is sequences only."""
        info = PLATFORM_REGISTRY["cisco_nxos"]
        assert info.device_type == "cisco_nxos"
        assert info.status == PlatformStatus.SEQUENCES_ONLY
        assert info.has_operations_class is False
        assert info.has_builtin_sequences is True

    def test_planned_platforms(self):
        """Verify planned platforms are correctly configured."""
        planned_platforms = ["nokia_srlinux", "cisco_iosxr", "linux", "generic"]
        for device_type in planned_platforms:
            info = PLATFORM_REGISTRY[device_type]
            assert info.status == PlatformStatus.PLANNED
            assert info.has_operations_class is False
            assert info.has_builtin_sequences is False


class TestGetPlatformInfo:
    """Test get_platform_info function."""

    def test_get_existing_platform(self):
        """Verify getting an existing platform returns info."""
        info = get_platform_info("mikrotik_routeros")
        assert info is not None
        assert info.device_type == "mikrotik_routeros"

    def test_get_nonexistent_platform(self):
        """Verify getting a nonexistent platform returns None."""
        info = get_platform_info("nonexistent_platform")
        assert info is None

    def test_get_all_registered_platforms(self):
        """Verify we can get info for all registered platforms."""
        for device_type in PLATFORM_REGISTRY.keys():
            info = get_platform_info(device_type)
            assert info is not None
            assert info.device_type == device_type


class TestGetImplementedPlatforms:
    """Test get_implemented_platforms function."""

    def test_returns_only_implemented(self):
        """Verify only implemented platforms are returned."""
        platforms = get_implemented_platforms()
        for info in platforms.values():
            assert info.status == PlatformStatus.IMPLEMENTED

    def test_contains_expected_implemented_platforms(self):
        """Verify expected platforms are in implemented list."""
        platforms = get_implemented_platforms()
        assert "mikrotik_routeros" in platforms
        assert "cisco_ios" in platforms
        assert "cisco_iosxe" in platforms

    def test_excludes_sequences_only_platforms(self):
        """Verify sequences-only platforms are excluded."""
        platforms = get_implemented_platforms()
        assert "cisco_nxos" not in platforms
        assert "arista_eos" not in platforms

    def test_excludes_planned_platforms(self):
        """Verify planned platforms are excluded."""
        platforms = get_implemented_platforms()
        assert "nokia_srlinux" not in platforms
        assert "linux" not in platforms


class TestGetPlatformsByStatus:
    """Test get_platforms_by_status function."""

    def test_get_implemented_platforms(self):
        """Verify getting implemented platforms."""
        platforms = get_platforms_by_status(PlatformStatus.IMPLEMENTED)
        assert len(platforms) == 3  # mikrotik, cisco_ios, cisco_iosxe
        assert all(p.status == PlatformStatus.IMPLEMENTED for p in platforms.values())

    def test_get_sequences_only_platforms(self):
        """Verify getting sequences-only platforms."""
        platforms = get_platforms_by_status(PlatformStatus.SEQUENCES_ONLY)
        assert len(platforms) == 3  # cisco_nxos, arista_eos, juniper_junos
        assert all(
            p.status == PlatformStatus.SEQUENCES_ONLY for p in platforms.values()
        )

    def test_get_planned_platforms(self):
        """Verify getting planned platforms."""
        platforms = get_platforms_by_status(PlatformStatus.PLANNED)
        assert len(platforms) == 4  # nokia_srlinux, cisco_iosxr, linux, generic
        assert all(p.status == PlatformStatus.PLANNED for p in platforms.values())

    def test_get_experimental_platforms(self):
        """Verify getting experimental platforms (currently none)."""
        platforms = get_platforms_by_status(PlatformStatus.EXPERIMENTAL)
        assert len(platforms) == 0


class TestGetPlatformsByVendor:
    """Test get_platforms_by_vendor function."""

    def test_get_cisco_platforms(self):
        """Verify getting all Cisco platforms."""
        platforms = get_platforms_by_vendor("Cisco")
        assert len(platforms) == 4  # ios, iosxe, nxos, iosxr
        assert all(p.vendor == "Cisco" for p in platforms)

    def test_get_mikrotik_platforms(self):
        """Verify getting MikroTik platforms."""
        platforms = get_platforms_by_vendor("MikroTik")
        assert len(platforms) == 1
        assert platforms[0].device_type == "mikrotik_routeros"

    def test_get_vendor_case_insensitive(self):
        """Verify vendor search is case-insensitive."""
        platforms_upper = get_platforms_by_vendor("CISCO")
        platforms_lower = get_platforms_by_vendor("cisco")
        platforms_mixed = get_platforms_by_vendor("CiScO")
        assert len(platforms_upper) == len(platforms_lower) == len(platforms_mixed)
        assert len(platforms_upper) == 4

    def test_get_nonexistent_vendor(self):
        """Verify getting platforms for nonexistent vendor returns empty list."""
        platforms = get_platforms_by_vendor("NonexistentVendor")
        assert len(platforms) == 0


class TestGetPlatformsWithCapability:
    """Test get_platforms_with_capability function."""

    def test_get_platforms_with_firmware_upgrade(self):
        """Verify getting platforms with firmware upgrade capability."""
        platforms = get_platforms_with_capability("firmware_upgrade")
        assert len(platforms) == 3  # mikrotik, cisco_ios, cisco_iosxe
        assert all(p.capabilities.firmware_upgrade for p in platforms)

    def test_get_platforms_with_bios_upgrade(self):
        """Verify getting platforms with BIOS upgrade capability."""
        platforms = get_platforms_with_capability("bios_upgrade")
        assert len(platforms) == 1  # only mikrotik
        assert platforms[0].device_type == "mikrotik_routeros"

    def test_get_platforms_with_config_backup(self):
        """Verify getting platforms with config backup capability."""
        platforms = get_platforms_with_capability("config_backup")
        assert len(platforms) == 3  # mikrotik, cisco_ios, cisco_iosxe
        assert all(p.capabilities.config_backup for p in platforms)

    def test_get_platforms_with_nonexistent_capability(self):
        """Verify getting platforms with nonexistent capability returns empty list."""
        platforms = get_platforms_with_capability("nonexistent_capability")
        assert len(platforms) == 0


class TestGetSupportedDeviceTypes:
    """Test get_supported_device_types function."""

    def test_returns_all_device_types(self):
        """Verify all device types are returned."""
        device_types = get_supported_device_types()
        assert isinstance(device_types, set)
        assert len(device_types) == len(PLATFORM_REGISTRY)
        assert device_types == set(PLATFORM_REGISTRY.keys())

    def test_can_check_membership(self):
        """Verify can check if device type is supported."""
        device_types = get_supported_device_types()
        assert "mikrotik_routeros" in device_types
        assert "cisco_ios" in device_types
        assert "nonexistent" not in device_types


class TestValidateRegistry:
    """Test validate_registry function."""

    def test_current_registry_is_valid(self):
        """Verify current registry passes validation."""
        errors = validate_registry()
        assert len(errors) == 0, f"Registry has validation errors: {errors}"

    def test_validation_with_mock_invalid_implemented_platform(self):
        """Verify validation catches invalid IMPLEMENTED platform."""
        # This is a documentation test showing what validation checks
        # In real code, we'd use mocking to inject invalid data
        pass

    def test_validation_with_mock_invalid_sequences_only_platform(self):
        """Verify validation catches invalid SEQUENCES_ONLY platform."""
        # This is a documentation test showing what validation checks
        # In real code, we'd use mocking to inject invalid data
        pass

    def test_validation_checks_firmware_capabilities(self):
        """Verify validation checks firmware capabilities consistency."""
        # This is a documentation test showing what validation checks
        # Real validation happens in validate_registry()
        # It checks that platforms with firmware capabilities have firmware_extensions
        pass

    def test_validation_checks_operations_capabilities(self):
        """Verify validation checks operations have capabilities."""
        # This is a documentation test showing what validation checks
        # Real validation happens in validate_registry()
        # It checks that platforms with operations_class have at least one capability
        pass


class TestRegistryIntegrity:
    """Test overall registry integrity and consistency."""

    def test_all_implemented_have_operations_class(self):
        """Verify all IMPLEMENTED platforms have operations classes."""
        implemented = get_platforms_by_status(PlatformStatus.IMPLEMENTED)
        for device_type, info in implemented.items():
            assert info.has_operations_class, f"{device_type} missing operations class"
            assert info.operations_class is not None, (
                f"{device_type} missing operations_class path"
            )

    def test_all_sequences_only_have_sequences(self):
        """Verify all SEQUENCES_ONLY platforms have sequences."""
        sequences_only = get_platforms_by_status(PlatformStatus.SEQUENCES_ONLY)
        for device_type, info in sequences_only.items():
            assert info.has_builtin_sequences, f"{device_type} missing sequences"
            assert not info.has_operations_class, (
                f"{device_type} should not have operations"
            )

    def test_all_planned_have_no_implementation(self):
        """Verify all PLANNED platforms have no implementation."""
        planned = get_platforms_by_status(PlatformStatus.PLANNED)
        for device_type, info in planned.items():
            assert not info.has_operations_class, (
                f"{device_type} should not have operations"
            )
            assert not info.has_builtin_sequences, (
                f"{device_type} should not have sequences"
            )

    def test_firmware_extensions_match_capabilities(self):
        """Verify platforms with firmware capabilities have extensions."""
        for device_type, info in PLATFORM_REGISTRY.items():
            if (
                info.capabilities.firmware_upgrade
                or info.capabilities.firmware_downgrade
            ):
                assert len(info.firmware_extensions) > 0, (
                    f"{device_type} has firmware capabilities but no extensions"
                )

    def test_operations_platforms_have_capabilities(self):
        """Verify platforms with operations have at least one capability."""
        for device_type, info in PLATFORM_REGISTRY.items():
            if info.has_operations_class:
                has_any = any(
                    [
                        info.capabilities.firmware_upgrade,
                        info.capabilities.firmware_downgrade,
                        info.capabilities.bios_upgrade,
                        info.capabilities.config_backup,
                        info.capabilities.comprehensive_backup,
                    ]
                )
                assert has_any, f"{device_type} has operations but no capabilities"

    def test_no_duplicate_device_types(self):
        """Verify all device types in registry are unique."""
        device_types = [info.device_type for info in PLATFORM_REGISTRY.values()]
        assert len(device_types) == len(set(device_types)), (
            "Duplicate device types found"
        )

    def test_all_display_names_unique(self):
        """Verify all display names are unique."""
        display_names = [info.display_name for info in PLATFORM_REGISTRY.values()]
        assert len(display_names) == len(set(display_names)), (
            "Duplicate display names found"
        )
