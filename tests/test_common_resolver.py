"""Tests for common.resolver module."""

from unittest.mock import MagicMock

from network_toolkit.common.resolver import DeviceResolver


class TestDeviceResolver:
    """Test DeviceResolver class."""

    def test_resolver_initialization(self) -> None:
        """Test DeviceResolver initialization."""
        config = MagicMock()
        resolver = DeviceResolver(config)

        assert resolver.config is config

    def test_is_device_true(self) -> None:
        """Test is_device returns True for valid device."""
        config = MagicMock()
        config.devices = {"device1": MagicMock()}
        resolver = DeviceResolver(config)

        result = resolver.is_device("device1")

        assert result is True

    def test_is_device_false(self) -> None:
        """Test is_device returns False for invalid device."""
        config = MagicMock()
        config.devices = {}
        resolver = DeviceResolver(config)

        result = resolver.is_device("nonexistent")

        assert result is False

    def test_is_device_none_devices(self) -> None:
        """Test is_device with None devices config."""
        config = MagicMock()
        config.devices = None
        resolver = DeviceResolver(config)

        result = resolver.is_device("device1")

        assert result is False

    def test_is_group_true(self) -> None:
        """Test is_group returns True for valid group."""
        config = MagicMock()
        config.device_groups = {"group1": ["device1", "device2"]}
        resolver = DeviceResolver(config)

        result = resolver.is_group("group1")

        assert result is True

    def test_is_group_false(self) -> None:
        """Test is_group returns False for invalid group."""
        config = MagicMock()
        config.device_groups = {}
        resolver = DeviceResolver(config)

        result = resolver.is_group("nonexistent")

        assert result is False

    def test_is_group_none_groups(self) -> None:
        """Test is_group with None groups config."""
        config = MagicMock()
        config.device_groups = None
        resolver = DeviceResolver(config)

        result = resolver.is_group("group1")

        assert result is False

    def test_validate_target_device(self) -> None:
        """Test validate_target for device."""
        config = MagicMock()
        config.devices = {"device1": MagicMock()}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        is_valid, target_type = resolver.validate_target("device1")

        assert is_valid is True
        assert target_type == "device"

    def test_validate_target_group(self) -> None:
        """Test validate_target for group."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {"group1": ["device1"]}
        resolver = DeviceResolver(config)

        is_valid, target_type = resolver.validate_target("group1")

        assert is_valid is True
        assert target_type == "group"

    def test_validate_target_unknown(self) -> None:
        """Test validate_target for unknown target."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        is_valid, target_type = resolver.validate_target("unknown")

        assert is_valid is False
        assert target_type == "unknown"

    def test_get_group_members_success(self) -> None:
        """Test get_group_members for valid group."""
        config = MagicMock()
        config.device_groups = {"group1": ["device1", "device2"]}
        config.get_group_members.return_value = ["device1", "device2"]
        resolver = DeviceResolver(config)

        result = resolver.get_group_members("group1")

        assert result == ["device1", "device2"]
        config.get_group_members.assert_called_once_with("group1")

    def test_get_group_members_nonexistent_group(self) -> None:
        """Test get_group_members for nonexistent group."""
        config = MagicMock()
        config.device_groups = {}
        resolver = DeviceResolver(config)

        try:
            resolver.get_group_members("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Group 'nonexistent' does not exist" in str(e)

    def test_get_group_members_config_error(self) -> None:
        """Test get_group_members with config error."""
        config = MagicMock()
        config.device_groups = {"group1": ["device1"]}
        config.get_group_members.side_effect = RuntimeError("Config error")
        resolver = DeviceResolver(config)

        try:
            resolver.get_group_members("group1")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Failed to get members for group 'group1'" in str(e)

    def test_resolve_targets_single_device(self) -> None:
        """Test resolve_targets with single device."""
        config = MagicMock()
        config.devices = {"device1": MagicMock()}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("device1")

        assert devices == ["device1"]
        assert unknowns == []

    def test_resolve_targets_single_group(self) -> None:
        """Test resolve_targets with single group."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {"group1": ["device1", "device2"]}
        config.get_group_members.return_value = ["device1", "device2"]
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("group1")

        assert devices == ["device1", "device2"]
        assert unknowns == []

    def test_resolve_targets_mixed(self) -> None:
        """Test resolve_targets with mixed devices and groups."""
        config = MagicMock()
        config.devices = {"device1": MagicMock()}
        config.device_groups = {"group1": ["device2", "device3"]}
        config.get_group_members.return_value = ["device2", "device3"]
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("device1,group1")

        assert "device1" in devices
        assert "device2" in devices
        assert "device3" in devices
        assert unknowns == []

    def test_resolve_targets_unknown(self) -> None:
        """Test resolve_targets with unknown targets."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("unknown1,unknown2")

        assert devices == []
        assert unknowns == ["unknown1", "unknown2"]

    def test_resolve_targets_duplicate_devices(self) -> None:
        """Test resolve_targets removes duplicates."""
        config = MagicMock()
        config.devices = {"device1": MagicMock()}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("device1,device1")

        assert devices == ["device1"]  # No duplicates
        assert unknowns == []

    def test_resolve_targets_empty_string(self) -> None:
        """Test resolve_targets with empty string."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("")

        assert devices == []
        assert unknowns == []

    def test_resolve_targets_whitespace_handling(self) -> None:
        """Test resolve_targets handles whitespace correctly."""
        config = MagicMock()
        config.devices = {"device1": MagicMock(), "device2": MagicMock()}
        config.device_groups = {}
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets(" device1 , device2 ")

        assert "device1" in devices
        assert "device2" in devices
        assert unknowns == []

    def test_resolve_targets_group_exception_handling(self) -> None:
        """Test resolve_targets handles group exceptions gracefully."""
        config = MagicMock()
        config.devices = {}
        config.device_groups = {"bad_group": ["device1"]}
        config.get_group_members.side_effect = RuntimeError("Group error")
        resolver = DeviceResolver(config)

        devices, unknowns = resolver.resolve_targets("bad_group")

        # Group with error should be skipped, not cause unknown
        assert devices == []
        assert unknowns == []
