#!/usr/bin/env python3
"""Generate JSON schema files for YAML editor validation."""

import json
from pathlib import Path
from typing import Any

from src.network_toolkit.config import generate_json_schema


def main() -> None:
    """Generate schema files for different use cases."""

    # Generate the main schema
    schema = generate_json_schema()

    # Create schema directory
    schema_dir = Path("schemas")
    schema_dir.mkdir(exist_ok=True)

    # Full NetworkConfig schema
    full_schema_path = schema_dir / "network-config.schema.json"
    with full_schema_path.open("w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"✅ Generated full schema: {full_schema_path}")

    # Extract DeviceConfig schema for standalone device files
    # Device files contain a "devices" object with multiple DeviceConfig entries
    device_collection_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Device Collection Configuration",
        "description": "Schema for device collection files (config/devices/*.yml)",
        "type": "object",
        "properties": {
            "devices": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/DeviceConfig"},
                "description": "Dictionary of device configurations keyed by device name",
            }
        },
        "required": ["devices"],
        "$defs": schema["$defs"],  # Include all definitions for references
    }

    device_schema_path = schema_dir / "device-config.schema.json"
    with device_schema_path.open("w", encoding="utf-8") as f:
        json.dump(device_collection_schema, f, indent=2)
    print(f"✅ Generated device schema: {device_schema_path}")

    # Create groups collection schema for standalone group files
    # Group files contain a "groups" object with multiple DeviceGroup entries
    groups_collection_schema: dict[str, Any] = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "Groups Collection Configuration",
        "description": "Schema for group collection files (config/groups/*.yml)",
        "type": "object",
        "properties": {
            "groups": {
                "type": "object",
                "additionalProperties": {"$ref": "#/$defs/DeviceGroup"},
                "description": "Dictionary of device group configurations keyed by group name",
            }
        },
        "required": ["groups"],
        "$defs": schema["$defs"],  # Include all definitions for references
    }

    groups_schema_path = schema_dir / "groups-config.schema.json"
    with groups_schema_path.open("w", encoding="utf-8") as f:
        json.dump(groups_collection_schema, f, indent=2)
    print(f"✅ Generated groups schema: {groups_schema_path}")

    # Create VS Code settings for YAML validation
    vscode_dir = Path(".vscode")
    vscode_dir.mkdir(exist_ok=True)

    settings_path = vscode_dir / "settings.json"
    vscode_settings = {
        "yaml.schemas": {
            "./schemas/network-config.schema.json": [
                "config/config.yml",
                "devices.yml",
            ],
            "./schemas/device-config.schema.json": [
                "config/devices/*.yml",
                "config/devices.yml",
            ],
            "./schemas/groups-config.schema.json": [
                "config/groups/*.yml",
                "config/groups.yml",
            ],
        }
    }

    # Merge with existing settings if they exist
    if settings_path.exists():
        with settings_path.open("r", encoding="utf-8") as f:
            existing = json.load(f)
        existing.update(vscode_settings)
        vscode_settings = existing

    with settings_path.open("w", encoding="utf-8") as f:
        json.dump(vscode_settings, f, indent=2)
    print(f"✅ Updated VS Code settings: {settings_path}")

    print("\n🎯 Schema validation is now active!")
    print("   - Open any YAML config file in VS Code")
    print("   - Try typing an invalid device_type")
    print("   - VS Code will show validation errors and auto-completion")


if __name__ == "__main__":
    main()
