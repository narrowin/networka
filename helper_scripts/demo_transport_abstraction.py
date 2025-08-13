#!/usr/bin/env python3
"""Quick test script for transport abstraction functionality."""

import os
import tempfile
from pathlib import Path

from src.network_toolkit.config import load_config
from src.network_toolkit.transport.factory import get_transport_factory


def create_test_config():
    """Create a minimal test configuration."""
    config_content = """
general:
  default_transport_type: scrapli
  transport_defaults:
    scrapli:
      timeout_socket: 30
      timeout_transport: 30
      auth_strict_key: false
    nornir_netmiko:
      timeout: 30
      global_delay_factor: 1

devices:
  test_device:
    host: 192.168.1.1
    device_type: mikrotik_routeros
    transport_type: scrapli
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yml", delete=False) as f:
        f.write(config_content)
        return Path(f.name)


def test_transport_factory():
    """Test basic transport factory functionality."""

    # Test factory creation for both transport types
    try:
        get_transport_factory("scrapli")
    except Exception:
        return False

    try:
        get_transport_factory("nornir_netmiko")
    except Exception:
        return False

    return True


def test_configuration():
    """Test configuration with transport settings."""

    config_file = create_test_config()

    try:
        # Test config loading
        config = load_config(config_file)

        # Test transport type resolution
        config.get_transport_type("test_device")

        # Set mock environment variables for testing
        os.environ["NT_DEFAULT_PASSWORD"] = "test_password"

        # Test connection parameters
        config.get_device_connection_params("test_device")

        return True

    except Exception:
        return False
    finally:
        # Cleanup
        config_file.unlink(missing_ok=True)
        os.environ.pop("NT_DEFAULT_PASSWORD", None)


def test_transport_creation():
    """Test transport creation without actual connection."""

    config_file = create_test_config()
    os.environ["NT_DEFAULT_PASSWORD"] = "test_password"

    try:
        config = load_config(config_file)

        # Test Scrapli transport creation
        scrapli_factory = get_transport_factory("scrapli")
        scrapli_transport = scrapli_factory.create_transport(
            device_name="test_device",
            config=config,
            connection_params=config.get_device_connection_params("test_device"),
        )

        # Test connection state interface
        scrapli_transport.get_connection_state()

        return True

    except Exception:
        return False
    finally:
        # Cleanup
        config_file.unlink(missing_ok=True)
        os.environ.pop("NT_DEFAULT_PASSWORD", None)


def main():
    """Run all transport abstraction tests."""

    tests = [
        test_transport_factory,
        test_configuration,
        test_transport_creation,
    ]

    passed = 0
    for test in tests:
        if test():
            passed += 1

    if passed == len(tests):
        return True
    else:
        return False


if __name__ == "__main__":
    main()
