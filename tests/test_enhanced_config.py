"""Tests for enhanced configuration system with CSV support and subdirectory discovery."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from network_toolkit.config import (
    NetworkConfig,
    _discover_config_files,
    _load_csv_devices,
    _load_csv_groups,
    _load_csv_sequences,
    _merge_configs,
    load_modular_config,
)


class TestCSVLoading:
    """Test CSV file loading functionality."""

    def test_load_csv_devices_valid(self, tmp_path):
        """Test loading valid devices CSV file."""
        csv_content = """name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Switch 1,mipsbe,CRS326,Lab,switch;access;lab
rtr-01,192.168.1.254,mikrotik_routeros,Router 1,arm,RB4011,Office,router;edge"""

        csv_file = tmp_path / "devices.csv"
        csv_file.write_text(csv_content)

        devices = _load_csv_devices(csv_file)

        assert len(devices) == 2
        assert "sw-01" in devices
        assert "rtr-01" in devices

        sw01 = devices["sw-01"]
        assert sw01.host == "192.168.1.1"
        assert sw01.device_type == "mikrotik_routeros"
        assert sw01.description == "Switch 1"
        assert sw01.platform == "mipsbe"
        assert sw01.model == "CRS326"
        assert sw01.location == "Lab"
        assert sw01.tags == ["switch", "access", "lab"]

    def test_load_csv_devices_empty_tags(self, tmp_path):
        """Test loading devices CSV with empty tags."""
        csv_content = """name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Switch 1,mipsbe,CRS326,Lab,"""

        csv_file = tmp_path / "devices.csv"
        csv_file.write_text(csv_content)

        devices = _load_csv_devices(csv_file)

        assert len(devices) == 1
        assert devices["sw-01"].tags is None

    def test_load_csv_devices_missing_name(self, tmp_path):
        """Test loading devices CSV with missing name field."""
        csv_content = """name,host,device_type,description,platform,model,location,tags
,192.168.1.1,mikrotik_routeros,Switch 1,mipsbe,CRS326,Lab,switch
sw-02,192.168.1.2,mikrotik_routeros,Switch 2,mipsbe,CRS326,Lab,switch"""

        csv_file = tmp_path / "devices.csv"
        csv_file.write_text(csv_content)

        devices = _load_csv_devices(csv_file)

        # Should skip row with empty name
        assert len(devices) == 1
        assert "sw-02" in devices

    def test_load_csv_groups_valid(self, tmp_path):
        """Test loading valid groups CSV file."""
        csv_content = """name,description,members,match_tags
lab_switches,Lab environment switches,sw-01;sw-02,lab;switch
production_routers,Production routers,,router;production"""

        csv_file = tmp_path / "groups.csv"
        csv_file.write_text(csv_content)

        groups = _load_csv_groups(csv_file)

        assert len(groups) == 2
        assert "lab_switches" in groups
        assert "production_routers" in groups

        lab_group = groups["lab_switches"]
        assert lab_group.description == "Lab environment switches"
        assert lab_group.members == ["sw-01", "sw-02"]
        assert lab_group.match_tags == ["lab", "switch"]

        prod_group = groups["production_routers"]
        assert prod_group.members is None
        assert prod_group.match_tags == ["router", "production"]

    def test_load_csv_sequences_valid(self, tmp_path):
        """Test loading valid sequences CSV file."""
        csv_content = """name,description,commands,tags
system_info,Get system info,/system/identity/print;/system/clock/print,system;info
backup,Create backup,/export file=backup,backup;maintenance"""

        csv_file = tmp_path / "sequences.csv"
        csv_file.write_text(csv_content)

        sequences = _load_csv_sequences(csv_file)

        assert len(sequences) == 2
        assert "system_info" in sequences
        assert "backup" in sequences

        sys_seq = sequences["system_info"]
        assert sys_seq.description == "Get system info"
        assert sys_seq.commands == ["/system/identity/print", "/system/clock/print"]
        assert sys_seq.tags == ["system", "info"]

    def test_load_csv_sequences_no_commands(self, tmp_path):
        """Test loading sequences CSV with missing commands."""
        csv_content = """name,description,commands,tags
empty_seq,Empty sequence,,system
valid_seq,Valid sequence,/system/identity/print,system"""

        csv_file = tmp_path / "sequences.csv"
        csv_file.write_text(csv_content)

        sequences = _load_csv_sequences(csv_file)

        # Should skip sequence with no commands
        assert len(sequences) == 1
        assert "valid_seq" in sequences

    def test_load_csv_invalid_file(self, tmp_path):
        """Test loading invalid CSV file."""
        csv_file = tmp_path / "invalid.csv"
        csv_file.write_text("invalid,csv,content\nwith,missing,headers")

        devices = _load_csv_devices(csv_file)
        groups = _load_csv_groups(csv_file)
        sequences = _load_csv_sequences(csv_file)

        # Should return empty dicts for invalid files
        assert devices == {}
        assert groups == {}
        assert sequences == {}


class TestConfigDiscovery:
    """Test configuration file discovery functionality."""

    def test_discover_config_files_yaml_only(self, tmp_path):
        """Test discovering YAML config files."""
        # Create main config files
        (tmp_path / "devices.yml").touch()
        (tmp_path / "groups.yaml").touch()

        # Create subdirectory with additional files
        devices_dir = tmp_path / "devices"
        devices_dir.mkdir()
        (devices_dir / "prod.yml").touch()
        (devices_dir / "test.yaml").touch()

        files = _discover_config_files(tmp_path, "devices")

        # Should find main file and subdirectory files
        file_names = [f.name for f in files]
        assert "devices.yml" in file_names
        assert "prod.yml" in file_names
        assert "test.yaml" in file_names

    def test_discover_config_files_csv_only(self, tmp_path):
        """Test discovering CSV config files."""
        # Create main CSV file
        (tmp_path / "devices.csv").touch()

        # Create subdirectory with additional CSV files
        devices_dir = tmp_path / "devices"
        devices_dir.mkdir()
        (devices_dir / "devices.csv").touch()
        (devices_dir / "additional.csv").touch()

        files = _discover_config_files(tmp_path, "devices")

        file_names = [f.name for f in files]
        assert "devices.csv" in file_names
        assert "additional.csv" in file_names

    def test_discover_config_files_mixed(self, tmp_path):
        """Test discovering mixed YAML and CSV files."""
        # Create main files
        (tmp_path / "devices.yml").touch()
        (tmp_path / "devices.csv").touch()

        # Create subdirectory with mixed files
        devices_dir = tmp_path / "devices"
        devices_dir.mkdir()
        (devices_dir / "prod.yml").touch()
        (devices_dir / "bulk.csv").touch()

        files = _discover_config_files(tmp_path, "devices")

        file_names = [f.name for f in files]
        assert "devices.yml" in file_names
        assert "devices.csv" in file_names
        assert "prod.yml" in file_names
        assert "bulk.csv" in file_names

    def test_discover_config_files_no_files(self, tmp_path):
        """Test discovering when no config files exist."""
        files = _discover_config_files(tmp_path, "devices")
        assert files == []

    def test_discover_config_files_removes_duplicates(self, tmp_path):
        """Test that duplicate file discovery is handled."""
        # This tests the deduplication logic in the function
        (tmp_path / "devices.yml").touch()

        files = _discover_config_files(tmp_path, "devices")

        # Should only appear once even though discovery might find it multiple ways
        yml_files = [f for f in files if f.name == "devices.yml"]
        assert len(yml_files) == 1


class TestConfigMerging:
    """Test configuration merging functionality."""

    def test_merge_configs_simple(self):
        """Test simple config merging."""
        base = {"key1": "value1", "key2": "value2"}
        override = {"key2": "override2", "key3": "value3"}

        merged = _merge_configs(base, override)

        assert merged["key1"] == "value1"
        assert merged["key2"] == "override2"  # Override wins
        assert merged["key3"] == "value3"

    def test_merge_configs_nested(self):
        """Test nested config merging."""
        base = {"section1": {"key1": "value1", "key2": "value2"}, "section2": {"key3": "value3"}}
        override = {"section1": {"key2": "override2", "key4": "value4"}, "section3": {"key5": "value5"}}

        merged = _merge_configs(base, override)

        assert merged["section1"]["key1"] == "value1"
        assert merged["section1"]["key2"] == "override2"
        assert merged["section1"]["key4"] == "value4"
        assert merged["section2"]["key3"] == "value3"
        assert merged["section3"]["key5"] == "value5"

    def test_merge_configs_override_with_none(self):
        """Test merging when override has different types."""
        base = {"section": {"key": "value"}}
        override = {"section": None}

        merged = _merge_configs(base, override)

        assert merged["section"] is None


class TestModularConfigLoading:
    """Test the enhanced modular config loading."""

    def test_load_modular_config_yaml_only(self, tmp_path):
        """Test loading modular config with YAML files only."""
        # Create main config
        config_content = {"general": {"timeout": 30}}
        with (tmp_path / "config.yml").open("w") as f:
            yaml.dump(config_content, f)

        # Create devices config
        devices_content = {"devices": {"sw-01": {"host": "192.168.1.1", "device_type": "mikrotik_routeros"}}}
        with (tmp_path / "devices.yml").open("w") as f:
            yaml.dump(devices_content, f)

        config = load_modular_config(tmp_path)

        assert isinstance(config, NetworkConfig)
        assert config.general.timeout == 30
        assert "sw-01" in config.devices
        assert config.devices["sw-01"].host == "192.168.1.1"

    def test_load_modular_config_csv_only(self, tmp_path):
        """Test loading modular config with CSV files only."""
        # Create main config
        config_content = {"general": {"timeout": 30}}
        with (tmp_path / "config.yml").open("w") as f:
            yaml.dump(config_content, f)

        # Create devices CSV
        csv_content = """name,host,device_type,description,platform,model,location,tags
sw-01,192.168.1.1,mikrotik_routeros,Switch 1,mipsbe,CRS326,Lab,switch"""
        (tmp_path / "devices.csv").write_text(csv_content)

        config = load_modular_config(tmp_path)

        assert isinstance(config, NetworkConfig)
        assert "sw-01" in config.devices
        assert config.devices["sw-01"].host == "192.168.1.1"
        assert config.devices["sw-01"].tags == ["switch"]

    def test_load_modular_config_mixed_formats(self, tmp_path):
        """Test loading modular config with mixed YAML and CSV files."""
        # Create main config
        config_content = {"general": {"timeout": 30}}
        with (tmp_path / "config.yml").open("w") as f:
            yaml.dump(config_content, f)

        # Create devices YAML
        devices_yaml_content = {"devices": {"sw-yaml": {"host": "192.168.1.1", "device_type": "mikrotik_routeros"}}}
        with (tmp_path / "devices.yml").open("w") as f:
            yaml.dump(devices_yaml_content, f)

        # Create devices CSV
        csv_content = """name,host,device_type,description,platform,model,location,tags
sw-csv,192.168.1.2,mikrotik_routeros,Switch CSV,mipsbe,CRS326,Lab,switch"""
        (tmp_path / "devices.csv").write_text(csv_content)

        config = load_modular_config(tmp_path)

        assert isinstance(config, NetworkConfig)
        assert "sw-yaml" in config.devices
        assert "sw-csv" in config.devices
        assert config.devices["sw-yaml"].host == "192.168.1.1"
        assert config.devices["sw-csv"].host == "192.168.1.2"

    def test_load_modular_config_subdirectories(self, tmp_path):
        """Test loading modular config with subdirectories."""
        # Create main config
        config_content = {"general": {"timeout": 30}}
        with (tmp_path / "config.yml").open("w") as f:
            yaml.dump(config_content, f)

        # Create main devices file
        main_devices = {"devices": {"sw-main": {"host": "192.168.1.1", "device_type": "mikrotik_routeros"}}}
        with (tmp_path / "devices.yml").open("w") as f:
            yaml.dump(main_devices, f)

        # Create devices subdirectory with additional files
        devices_dir = tmp_path / "devices"
        devices_dir.mkdir()

        # Additional YAML file
        sub_devices = {"devices": {"sw-sub": {"host": "192.168.1.2", "device_type": "mikrotik_routeros"}}}
        with (devices_dir / "additional.yml").open("w") as f:
            yaml.dump(sub_devices, f)

        # Additional CSV file
        csv_content = """name,host,device_type,description,platform,model,location,tags
sw-csv-sub,192.168.1.3,mikrotik_routeros,Subdirectory CSV,mipsbe,CRS326,Lab,switch"""
        (devices_dir / "bulk.csv").write_text(csv_content)

        config = load_modular_config(tmp_path)

        assert isinstance(config, NetworkConfig)
        assert len(config.devices) == 3
        assert "sw-main" in config.devices
        assert "sw-sub" in config.devices
        assert "sw-csv-sub" in config.devices

    def test_load_modular_config_missing_main_config(self, tmp_path):
        """Test loading modular config without main config file."""
        with pytest.raises(FileNotFoundError, match="Main config file not found"):
            load_modular_config(tmp_path)

    def test_load_modular_config_invalid_yaml(self, tmp_path):
        """Test loading modular config with invalid YAML."""
        # Create main config
        (tmp_path / "config.yml").write_text("general:\n  timeout: 30")

        # Create invalid YAML devices file
        (tmp_path / "devices.yml").write_text("invalid: yaml: content:")

        # The enhanced system should handle this gracefully by logging warnings
        # and continue loading other valid configurations
        config = load_modular_config(tmp_path)

        # Should still create a valid config object with general settings
        assert isinstance(config, NetworkConfig)
        assert config.general.timeout == 30
        # Devices should be empty due to invalid YAML being skipped
        assert len(config.devices) == 0


class TestIntegration:
    """Integration tests for the enhanced configuration system."""

    def test_full_integration_example(self, tmp_path):
        """Test a complete integration example with all features."""
        # Create main config
        config_content = {"general": {"timeout": 30, "results_dir": "/tmp/results"}}
        with (tmp_path / "config.yml").open("w") as f:
            yaml.dump(config_content, f)

        # Create main devices file
        main_devices = {
            "devices": {
                "main-device": {
                    "host": "192.168.1.1",
                    "device_type": "mikrotik_routeros",
                    "description": "Main device from YAML",
                }
            }
        }
        with (tmp_path / "devices.yml").open("w") as f:
            yaml.dump(main_devices, f)

        # Create devices subdirectory
        devices_dir = tmp_path / "devices"
        devices_dir.mkdir()

        # Add CSV devices
        csv_devices = """name,host,device_type,description,platform,model,location,tags
csv-device-1,192.168.1.10,mikrotik_routeros,CSV Device 1,mipsbe,CRS326,Lab,switch;access
csv-device-2,192.168.1.11,mikrotik_routeros,CSV Device 2,mipsbe,CRS326,Lab,switch;access"""
        (devices_dir / "csv-devices.csv").write_text(csv_devices)

        # Add YAML devices in subdirectory
        sub_devices = {
            "devices": {
                "yaml-sub-device": {
                    "host": "192.168.1.20",
                    "device_type": "mikrotik_routeros",
                    "description": "YAML subdirectory device",
                    "tags": ["router", "edge"],
                }
            }
        }
        with (devices_dir / "yaml-devices.yml").open("w") as f:
            yaml.dump(sub_devices, f)

        # Create groups
        groups_content = {"groups": {"yaml-group": {"description": "YAML defined group", "match_tags": ["switch"]}}}
        with (tmp_path / "groups.yml").open("w") as f:
            yaml.dump(groups_content, f)

        # Create groups subdirectory with CSV
        groups_dir = tmp_path / "groups"
        groups_dir.mkdir()

        csv_groups = """name,description,members,match_tags
csv-group,CSV defined group,,router;edge"""
        (groups_dir / "groups.csv").write_text(csv_groups)

        # Create sequences
        sequences_content = {
            "sequences": {
                "yaml-sequence": {
                    "description": "YAML defined sequence",
                    "commands": ["/system/identity/print", "/system/clock/print"],
                    "tags": ["system"],
                }
            }
        }
        with (tmp_path / "sequences.yml").open("w") as f:
            yaml.dump(sequences_content, f)

        # Load the complete configuration
        config = load_modular_config(tmp_path)

        # Verify all devices are loaded
        assert len(config.devices) == 4
        assert "main-device" in config.devices
        assert "csv-device-1" in config.devices
        assert "csv-device-2" in config.devices
        assert "yaml-sub-device" in config.devices

        # Verify device properties
        assert config.devices["main-device"].description == "Main device from YAML"
        assert config.devices["csv-device-1"].tags == ["switch", "access"]
        assert config.devices["yaml-sub-device"].tags == ["router", "edge"]

        # Verify groups
        assert len(config.device_groups) == 2
        assert "yaml-group" in config.device_groups
        assert "csv-group" in config.device_groups

        # Verify group functionality
        yaml_group_members = config.get_group_members("yaml-group")
        csv_group_members = config.get_group_members("csv-group")

        # yaml-group should match devices with "switch" tag
        assert "csv-device-1" in yaml_group_members
        assert "csv-device-2" in yaml_group_members

        # csv-group should match devices with "router" and "edge" tags
        assert "yaml-sub-device" in csv_group_members

        # Verify sequences
        assert len(config.global_command_sequences) == 1
        assert "yaml-sequence" in config.global_command_sequences

        # Verify general config
        assert config.general.timeout == 30
        assert config.general.results_dir == "/tmp/results"
