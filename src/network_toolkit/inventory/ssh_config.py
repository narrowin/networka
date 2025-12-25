"""SSH config inventory parser.

Parse ~/.ssh/config to extract host definitions for inventory sync.
Uses Paramiko for SSH config parsing with custom host enumeration.
"""

from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from paramiko import SSHConfig

from network_toolkit.exceptions import ConfigurationError

if TYPE_CHECKING:
    from collections.abc import Sequence

# Pattern validation constants
MAX_PATTERN_LENGTH = 200
MAX_PATTERN_WILDCARDS = 20

# Valid hostname pattern (letters, numbers, dots, hyphens, underscores)
VALID_HOSTNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


@dataclass
class SSHConfigOptions:
    """Configuration for SSH config parsing."""

    path: Path = field(default_factory=lambda: Path("~/.ssh/config"))
    default_device_type: str = "generic"
    include_patterns: Sequence[str] | None = None
    exclude_patterns: Sequence[str] | None = None


@dataclass
class SSHHost:
    """Parsed SSH host entry."""

    name: str
    hostname: str
    user: str | None
    port: int | None


def enumerate_ssh_hosts(config_path: Path) -> list[str]:
    """Extract concrete Host entries (no wildcards).

    Paramiko doesn't expose the host list directly, so we parse the file
    to find Host directives and filter out wildcard patterns.

    Args:
        config_path: Path to SSH config file.

    Returns:
        List of concrete host names (no wildcards).

    Raises:
        ConfigurationError: If the file cannot be read or contains unsupported
            directives.
    """
    hosts: list[str] = []
    expanded_path = config_path.expanduser()

    try:
        with open(expanded_path, encoding="utf-8") as f:
            for line in f:
                # Detect Include directives (not currently supported)
                if re.match(r"^\s*Include\s+", line, re.IGNORECASE):
                    msg = (
                        "SSH config files with 'Include' directives are not "
                        "currently supported. Please flatten your SSH config or "
                        "specify the included file directly."
                    )
                    raise ConfigurationError(
                        msg,
                        details={"path": str(config_path), "line": line.strip()},
                    )

                if match := re.match(r"^\s*Host\s+(.+)", line, re.IGNORECASE):
                    for pattern in match.group(1).split():
                        # Skip wildcard patterns
                        if "*" not in pattern and "?" not in pattern:
                            # Validate hostname characters
                            if VALID_HOSTNAME_PATTERN.match(pattern):
                                hosts.append(pattern)
    except FileNotFoundError as e:
        msg = f"SSH config file not found: {config_path}"
        raise ConfigurationError(
            msg,
            details={"path": str(config_path)},
        ) from e
    except PermissionError as e:
        msg = f"Permission denied reading SSH config: {config_path}"
        raise ConfigurationError(
            msg,
            details={"path": str(config_path)},
        ) from e
    except UnicodeDecodeError as e:
        msg = f"SSH config file contains invalid encoding: {config_path}"
        raise ConfigurationError(
            msg,
            details={"path": str(config_path), "error": str(e)},
        ) from e

    return hosts


def _validate_pattern(pattern: str) -> None:
    """Validate user-provided fnmatch pattern to prevent ReDoS.

    Args:
        pattern: The fnmatch pattern to validate.

    Raises:
        ConfigurationError: If the pattern is too long or too complex.
    """
    if len(pattern) > MAX_PATTERN_LENGTH:
        msg = f"Pattern too long (max {MAX_PATTERN_LENGTH} characters): {pattern}"
        raise ConfigurationError(
            msg,
            details={"pattern": pattern, "length": len(pattern)},
        )

    wildcard_count = pattern.count("*") + pattern.count("?") + pattern.count("[")
    if wildcard_count > MAX_PATTERN_WILDCARDS:
        msg = f"Pattern too complex (max {MAX_PATTERN_WILDCARDS} wildcards): {pattern}"
        raise ConfigurationError(
            msg,
            details={"pattern": pattern, "wildcard_count": wildcard_count},
        )


def _safe_port(port_value: Any, host_name: str) -> int | None:
    """Safely parse and validate a port value.

    Args:
        port_value: The port value to parse (may be string, int, or None).
        host_name: The host name for error messages.

    Returns:
        The validated port as an integer, or None if no port was specified.

    Raises:
        ConfigurationError: If the port value is invalid or out of range.
    """
    if port_value is None:
        return None
    try:
        port = int(port_value)
        if not (1 <= port <= 65535):
            msg = f"Port out of range for host '{host_name}': {port} (must be 1-65535)"
            raise ConfigurationError(
                msg,
                details={"host": host_name, "port": port},
            )
        return port
    except (ValueError, TypeError) as e:
        msg = f"Invalid port value for host '{host_name}': {port_value}"
        raise ConfigurationError(
            msg,
            details={"host": host_name, "port": port_value},
        ) from e


def parse_ssh_config(options: SSHConfigOptions) -> dict[str, SSHHost]:
    """Parse SSH config into SSHHost objects.

    Args:
        options: Parsing configuration options.

    Returns:
        Dictionary mapping host names to SSHHost objects.

    Raises:
        ConfigurationError: If the file cannot be read, contains invalid data,
            or if include/exclude patterns are invalid.
    """
    # Validate patterns before using them
    if options.include_patterns:
        for pattern in options.include_patterns:
            _validate_pattern(pattern)
    if options.exclude_patterns:
        for pattern in options.exclude_patterns:
            _validate_pattern(pattern)

    config = SSHConfig()
    path = options.path.expanduser()

    try:
        with open(path, encoding="utf-8") as f:
            config.parse(f)
    except FileNotFoundError as e:
        msg = f"SSH config file not found: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path)},
        ) from e
    except PermissionError as e:
        msg = f"Permission denied reading SSH config: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path)},
        ) from e
    except UnicodeDecodeError as e:
        msg = f"SSH config file contains invalid encoding: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path), "error": str(e)},
        ) from e
    except Exception as e:
        msg = f"Failed to parse SSH config: {path}"
        raise ConfigurationError(
            msg,
            details={"path": str(path), "error": str(e)},
        ) from e

    hosts: dict[str, SSHHost] = {}

    for host_name in enumerate_ssh_hosts(path):
        # Apply include patterns
        if options.include_patterns:
            if not any(fnmatch.fnmatch(host_name, p) for p in options.include_patterns):
                continue

        # Apply exclude patterns
        if options.exclude_patterns:
            if any(fnmatch.fnmatch(host_name, p) for p in options.exclude_patterns):
                continue

        # Lookup resolved values from Paramiko
        host_config = config.lookup(host_name)

        hosts[host_name] = SSHHost(
            name=host_name,
            hostname=host_config.get("hostname", host_name),
            user=host_config.get("user"),
            port=_safe_port(host_config.get("port"), host_name),
        )

    return hosts
