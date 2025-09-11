"""JSON schemas for configuration validation."""

from pathlib import Path

# Schema files are generated during build and shipped with the package
SCHEMA_DIR = Path(__file__).parent
NETWORK_CONFIG_SCHEMA = SCHEMA_DIR / "network-config.schema.json"
DEVICE_CONFIG_SCHEMA = SCHEMA_DIR / "device-config.schema.json"
