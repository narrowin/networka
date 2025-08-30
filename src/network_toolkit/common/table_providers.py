# SPDX-License-Identifier: MIT
"""Table data providers for centralized table generation using Pydantic v2."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from pydantic import BaseModel

from network_toolkit.common.styles import StyleName
from network_toolkit.common.table_generator import (
    BaseTableProvider,
    TableColumn,
    TableDefinition,
)
from network_toolkit.config import NetworkConfig, get_supported_device_types
from network_toolkit.credentials import EnvironmentCredentialManager
from network_toolkit.ip_device import (
    get_supported_device_types as get_device_descriptions,
)
from network_toolkit.platforms.factory import (
    get_supported_platforms as get_platform_ops,
)

if TYPE_CHECKING:
    pass


class DeviceListTableProvider(BaseModel, BaseTableProvider):
    """Provides device list table data using Pydantic v2."""

    config: NetworkConfig

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for device list."""
        return TableDefinition(
            title="Devices",
            columns=[
                TableColumn(header="Name", style=StyleName.DEVICE),
                TableColumn(header="Host", style=StyleName.HOST),
                TableColumn(header="Type", style=StyleName.PLATFORM),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Tags", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for device list."""
        if not self.config.devices:
            return []

        rows = []
        for name, device_config in self.config.devices.items():
            rows.append(
                [
                    name,
                    device_config.host,
                    device_config.device_type,
                    device_config.description or "N/A",
                    ", ".join(device_config.tags) if device_config.tags else "None",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for device list."""
        if not self.config.devices:
            return ""

        lines = []
        for name, device in self.config.devices.items():
            tags_str = ",".join(device.tags or []) if device.tags else "none"
            platform = device.platform or "unknown"
            lines.append(
                f"device={name} host={device.host} platform={platform} tags={tags_str}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for device list."""
        if not self.config.devices:
            return None

        return [
            f"Total devices: {len(self.config.devices)}",
            "Usage Examples:",
            "  nw run <device_name> <command>",
            "  nw info <device_name>",
        ]


class GroupListTableProvider(BaseModel, BaseTableProvider):
    """Provides group list table data using Pydantic v2."""

    config: NetworkConfig

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for group list."""
        return TableDefinition(
            title="Groups",
            columns=[
                TableColumn(header="Group Name", style=StyleName.GROUP),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Match Tags", style=StyleName.WARNING),
                TableColumn(header="Members", style=StyleName.DEVICE),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for group list."""
        if not self.config.device_groups:
            return []

        rows = []
        for name, group in self.config.device_groups.items():
            # Use the proven get_group_members method
            members = self.config.get_group_members(name)

            rows.append(
                [
                    name,
                    group.description,
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(members) if members else "None",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for group list."""
        if not self.config.device_groups:
            return ""

        lines = []
        for name, group in self.config.device_groups.items():
            # Use the proven get_group_members method
            group_members = self.config.get_group_members(name)

            members_str = ",".join(group_members) if group_members else "none"
            tags_str = ",".join(group.match_tags or []) if group.match_tags else "none"
            description = group.description or ""
            lines.append(
                f"group={name} description={description} tags={tags_str} members={members_str}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for group list."""
        if not self.config.device_groups:
            return None

        return [
            f"Total groups: {len(self.config.device_groups)}",
            "Usage Examples:",
            "  nw run <group_name> <command>",
            "  nw info <group_name>",
        ]


class TransportTypesTableProvider(BaseModel, BaseTableProvider):
    """Provides transport types table data using Pydantic v2."""

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for transport types."""
        return TableDefinition(
            title="Available Transport Types",
            columns=[
                TableColumn(header="Transport", style=StyleName.TRANSPORT),
                TableColumn(header="Description", style=StyleName.OUTPUT),
                TableColumn(header="Device Type Mapping", style=StyleName.INFO),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for transport types."""
        return [
            [
                "scrapli",
                "Async SSH/Telnet library with device-specific drivers",
                "Direct (uses device_type as-is)",
            ]
        ]

    def get_raw_output(self) -> str:
        """Get raw mode output for transport types."""
        return "transport=scrapli description=Async SSH/Telnet library with device-specific drivers mapping=Direct (uses device_type as-is)"

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for transport types."""
        return [
            "Available transports: scrapli (default)",
            "Transport selection via config:",
            "  general:",
            "    default_transport_type: scrapli",
        ]


class VendorSequencesTableProvider(BaseModel, BaseTableProvider):
    """Provider for vendor sequences table."""

    config: NetworkConfig
    vendor_filter: str | None = None
    verbose: bool = False

    def get_table_definition(self) -> TableDefinition:
        columns = [
            TableColumn(header="Sequence Name", style=StyleName.DEVICE),
            TableColumn(header="Description", style=StyleName.SUCCESS),
            TableColumn(header="Category", style=StyleName.WARNING),
            TableColumn(header="Commands", style=StyleName.OUTPUT),
        ]

        if self.verbose:
            columns.extend(
                [
                    TableColumn(header="Timeout", style=StyleName.INFO),
                    TableColumn(header="Device Types", style=StyleName.ERROR),
                ]
            )

        vendor_name = self.vendor_filter or "All Vendors"
        return TableDefinition(
            title=f"Vendor Sequences - {vendor_name}", columns=columns
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get vendor sequences data."""
        rows = []
        vendor_sequences = self.config.vendor_sequences or {}

        for vendor_name, sequences in vendor_sequences.items():
            if self.vendor_filter and vendor_name != self.vendor_filter:
                continue

            for seq_name, sequence in sequences.items():
                # Handle both string commands and command objects
                if hasattr(sequence, "commands"):
                    if isinstance(sequence.commands[0], str):
                        commands_str = ", ".join(sequence.commands)
                    else:
                        commands_str = ", ".join(
                            [cmd.command for cmd in sequence.commands]
                        )
                else:
                    commands_str = "N/A"

                row = [
                    seq_name,
                    getattr(sequence, "description", "N/A") or "N/A",
                    vendor_name,
                    commands_str[:50] + "..."
                    if len(commands_str) > 50
                    else commands_str,
                ]

                if self.verbose:
                    timeout = str(getattr(sequence, "timeout", "Default")) or "Default"
                    device_types = (
                        ", ".join(getattr(sequence, "device_types", [])) or "All"
                    )
                    row.extend([timeout, device_types])

                rows.append(row)

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        vendor_sequences = self.config.vendor_sequences or {}
        if self.vendor_filter:
            sequences = vendor_sequences.get(self.vendor_filter, {})
            lines = []
            for seq_name, _sequence in sequences.items():
                lines.append(f"vendor={self.vendor_filter} sequence={seq_name}")
            return "\n".join(lines)
        else:
            lines = []
            for vendor_name, sequences in vendor_sequences.items():
                for seq_name in sequences.keys():
                    lines.append(f"vendor={vendor_name} sequence={seq_name}")
            return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        vendor_sequences = self.config.vendor_sequences or {}
        if self.vendor_filter:
            sequences = vendor_sequences.get(self.vendor_filter, {})
            return [f"Vendor: {self.vendor_filter}, Sequences: {len(sequences)}"]
        else:
            total_vendors = len(vendor_sequences)
            total_sequences = sum(len(seqs) for seqs in vendor_sequences.values())
            return [
                f"Total vendors: {total_vendors}, Total sequences: {total_sequences}"
            ]


class SupportedPlatformsTableProvider(BaseModel, BaseTableProvider):
    """Provider for supported platforms table."""

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title="Supported Platforms",
            columns=[
                TableColumn(header="Platform", style=StyleName.DEVICE),
                TableColumn(header="Device Type", style=StyleName.SUCCESS),
                TableColumn(header="Transport", style=StyleName.WARNING),
                TableColumn(header="Operations", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get supported platforms data."""
        # For now, return sample data since transport factory may not be implemented yet
        return [
            ["cisco_ios", "Network", "SSH", "show commands, config"],
            ["cisco_nxos", "Network", "SSH", "show commands, config"],
            ["juniper_junos", "Network", "SSH", "show commands, config"],
        ]

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        lines = []
        for row in self.get_table_rows():
            platform, device_type, transport, operations = row
            lines.append(
                f"platform={platform} device_type={device_type} transport={transport}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return ["Platforms supported by the network toolkit transport layer"]


class GlobalSequenceInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for global sequence info table."""

    sequence_name: str
    sequence: Any  # CommandSequence object
    verbose: bool = False

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title=f"Global Sequence: {self.sequence_name}",
            columns=[
                TableColumn(header="Property", style=StyleName.DEVICE),
                TableColumn(header="Value", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get global sequence info data."""
        rows = [
            ["Description", getattr(self.sequence, "description", "No description")],
            ["Source", self._get_global_sequence_source()],
            ["Command Count", str(len(getattr(self.sequence, "commands", [])))],
        ]

        # Add all individual commands - no truncation
        commands = getattr(self.sequence, "commands", [])
        for i, cmd in enumerate(commands, 1):
            rows.append([f"Command {i}", str(cmd)])

        # Add tags if available
        tags = getattr(self.sequence, "tags", [])
        if tags:
            rows.append(["Tags", ", ".join(tags)])

        return rows

    def _get_global_sequence_source(self) -> str:
        """Determine the source of this global sequence."""
        # Global sequences are typically in config.yml or sequences.yml
        try:
            config_dir = Path("config")

            # Check main config.yml first
            config_file = config_dir / "config.yml"
            if config_file.exists():
                try:
                    with config_file.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if (
                            isinstance(data, dict)
                            and "global_command_sequences" in data
                        ):
                            if self.sequence_name in data["global_command_sequences"]:
                                return "config file (config/config.yml)"
                except Exception:
                    pass

            # Check sequences.yml
            sequences_file = config_dir / "sequences.yml"
            if sequences_file.exists():
                try:
                    with sequences_file.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if (
                            isinstance(data, dict)
                            and "global_command_sequences" in data
                        ):
                            if self.sequence_name in data["global_command_sequences"]:
                                return "config file (config/sequences.yml)"
                except Exception:
                    pass

            # Fallback
            return "config file (global sequences)"

        except Exception:
            return "config file (global sequences)"

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        commands = getattr(self.sequence, "commands", [])
        return f"sequence={self.sequence_name} type=global commands={len(commands)}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return [f"Global sequence '{self.sequence_name}' details"]


class VendorSequenceInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for vendor sequence info table."""

    sequence_name: str
    sequence_record: Any  # SequenceRecord object
    vendor_names: list[str]
    verbose: bool = False
    config: NetworkConfig | None = None
    vendor_specific: bool = False

    def get_table_definition(self) -> TableDefinition:
        title_suffix = ""
        if self.vendor_specific and len(self.vendor_names) == 1:
            title_suffix = f" ({self.vendor_names[0]})"

        return TableDefinition(
            title=f"Vendor Sequence: {self.sequence_name}{title_suffix}",
            columns=[
                TableColumn(header="Property", style=StyleName.DEVICE),
                TableColumn(header="Value", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get vendor sequence info data."""
        rows = [
            [
                "Description",
                getattr(self.sequence_record, "description", "No description")
                or "No description",
            ],
            [
                "Category",
                getattr(self.sequence_record, "category", "general") or "general",
            ],
            ["Vendors", ", ".join(self.vendor_names)],
            ["Source", self._get_sequence_source()],
            ["Command Count", str(len(getattr(self.sequence_record, "commands", [])))],
        ]

        # Add all individual commands - no truncation
        commands = getattr(self.sequence_record, "commands", [])
        for i, cmd in enumerate(commands, 1):
            rows.append([f"Command {i}", str(cmd)])

        return rows

    def _get_sequence_source(self) -> str:
        """Determine the source of this vendor sequence using the actual sequence record source."""
        # Use the source information from the SequenceRecord if available
        if hasattr(self.sequence_record, "source") and self.sequence_record.source:
            source = self.sequence_record.source
            origin = getattr(source, "origin", None)
            path = getattr(source, "path", None)

            if origin == "builtin":
                if path:
                    return f"built-in package ({path.name})"
                return "built-in package sequences"
            elif origin == "repo":
                if path:
                    return f"repository config (config/sequences/{path.name})"
                return "repository config (config/sequences/)"
            elif origin == "user":
                if path:
                    return f"user config (~/.config/nw/sequences/{path.name})"
                return "user config (~/.config/nw/sequences/)"
            elif origin == "global":
                return "global config sequences"

        # Fallback: try to detect from file system (old approach)
        try:
            config_dir = Path("config")
            sequences_dir = config_dir / "sequences"

            if sequences_dir.exists():
                for sequence_file in sequences_dir.glob("*.yml"):
                    try:
                        with sequence_file.open("r", encoding="utf-8") as f:
                            data = yaml.safe_load(f)
                            if isinstance(data, dict) and "sequences" in data:
                                if self.sequence_name in data["sequences"]:
                                    return f"config file (config/sequences/{sequence_file.name})"
                    except Exception as exc:
                        import logging

                        logging.debug(
                            f"Failed reading sequence YAML {sequence_file}: {exc}"
                        )
                        continue

            # Check if it's in the main sequences.yml file
            sequences_file = config_dir / "sequences.yml"
            if sequences_file.exists():
                try:
                    with sequences_file.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict) and "sequences" in data:
                            if self.sequence_name in data["sequences"]:
                                return "config file (config/sequences.yml)"
                except Exception:
                    pass

            # Final fallback
            return "built-in vendor sequences"

        except Exception:
            return "built-in vendor sequences"

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        commands = getattr(self.sequence_record, "commands", [])
        vendors = ",".join(self.vendor_names)
        return f"sequence={self.sequence_name} type=vendor vendors={vendors} commands={len(commands)}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return [
            f"Vendor sequence '{self.sequence_name}' available in {len(self.vendor_names)} vendor(s)"
        ]


class TransportInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for transport types information table."""

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title="Available Transport Types",
            columns=[
                TableColumn(header="Transport", style=StyleName.DEVICE),
                TableColumn(header="Description", style=StyleName.OUTPUT),
                TableColumn(header="Device Type Mapping", style=StyleName.WARNING),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get transport types data."""
        return [
            [
                "scrapli",
                "Async SSH/Telnet library with device-specific drivers",
                "Direct (uses device_type as-is)",
            ]
        ]

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        lines = []
        for row in self.get_table_rows():
            transport, description, mapping = row
            lines.append(f"transport={transport} description={description}")
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return ["Available transport types for device connections"]


class DeviceTypesInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for device types information table."""

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title="Device Types",
            columns=[
                TableColumn(header="Device Type", style=StyleName.DEVICE),
                TableColumn(header="Description", style=StyleName.OUTPUT),
                TableColumn(header="Platform Ops", style=StyleName.SUCCESS),
                TableColumn(header="Transport Support", style=StyleName.WARNING),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get device types data."""
        device_types = get_supported_device_types()
        device_descriptions = get_device_descriptions()
        platform_ops = get_platform_ops()

        rows = []
        for device_type in sorted(device_types):
            description = device_descriptions.get(device_type, "No description")
            has_platform_ops = "✓" if device_type in platform_ops else "✗"
            transport_support = "scrapli"
            rows.append([device_type, description, has_platform_ops, transport_support])

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        lines = []
        for row in self.get_table_rows():
            device_type, description, platform_ops, transport = row
            lines.append(
                f"device_type={device_type} description={description} platform_ops={platform_ops}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return ["Supported device types and their capabilities"]


class DeviceInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for device information table."""

    config: NetworkConfig
    device_name: str
    interactive_creds: Any | None = None
    config_path: Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title=f"Device: {self.device_name}",
            columns=[
                TableColumn(header="Property", style=StyleName.DEVICE),
                TableColumn(header="Value", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get device information data."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return [["Error", f"Device '{self.device_name}' not found"]]

        device_config = devices[self.device_name]
        rows = []

        # Basic device information
        rows.append(["Host", device_config.host])
        rows.append(["Description", device_config.description or "N/A"])
        rows.append(["Device Type", device_config.device_type])
        rows.append(["Model", device_config.model or "N/A"])
        rows.append(["Platform", device_config.platform or device_config.device_type])
        rows.append(["Location", device_config.location or "N/A"])
        rows.append(
            ["Tags", ", ".join(device_config.tags) if device_config.tags else "None"]
        )
        rows.append(["Source", self._get_device_source()])

        # Connection parameters
        username_override = (
            getattr(self.interactive_creds, "username", None)
            if self.interactive_creds
            else None
        )
        password_override = (
            getattr(self.interactive_creds, "password", None)
            if self.interactive_creds
            else None
        )

        conn_params = self.config.get_device_connection_params(
            self.device_name, username_override, password_override
        )

        rows.append(["SSH Port", str(conn_params["port"])])
        rows.append(["Username", conn_params["auth_username"]])
        rows.append(["Username Source", self._get_credential_source("username")])

        # Password handling with environment variable support
        show_passwords = self._env_truthy("NW_SHOW_PLAINTEXT_PASSWORDS")
        if show_passwords:
            password_value = conn_params["auth_password"] or ""
            if password_value:
                rows.append(["Password", password_value])
            else:
                rows.append(
                    [
                        "Password",
                        "(empty - set NW_SHOW_PLAINTEXT_PASSWORDS=1 to display)",
                    ]
                )
        else:
            rows.append(["Password", "set NW_SHOW_PLAINTEXT_PASSWORDS=1 to display"])
        rows.append(["Password Source", self._get_credential_source("password")])

        rows.append(["Timeout", f"{conn_params['timeout_socket']}s"])

        # Transport type
        transport_type = self.config.get_transport_type(self.device_name)
        rows.append(["Transport Type", transport_type])

        # Group memberships
        group_memberships = []
        if self.config.device_groups:
            for group_name, _group_config in self.config.device_groups.items():
                if self.device_name in self.config.get_group_members(group_name):
                    group_memberships.append(group_name)

        if group_memberships:
            rows.append(["Groups", ", ".join(group_memberships)])

        return rows

    def _env_truthy(self, var_name: str) -> bool:
        """Check if environment variable is truthy."""
        val = os.getenv(var_name, "")
        return val.strip().lower() in {"1", "true", "yes", "y", "on"}

    def _get_credential_source(self, credential_type: str) -> str:
        """Get the source of a credential using the same logic as CredentialResolver."""
        from network_toolkit.credentials import CredentialResolver

        # Check interactive override
        if self.interactive_creds:
            if credential_type == "username" and getattr(
                self.interactive_creds, "username", None
            ):
                return "interactive input"
            if credential_type == "password" and getattr(
                self.interactive_creds, "password", None
            ):
                return "interactive input"

        # Use CredentialResolver to get the actual resolved value
        resolver = CredentialResolver(self.config)
        dev = self.config.devices.get(self.device_name) if self.config.devices else None
        if not dev:
            return "unknown (device not found)"

        # Get what the resolver would actually return
        resolved_user, resolved_pass = resolver.resolve_credentials(self.device_name)
        resolved_value = (
            resolved_user if credential_type == "username" else resolved_pass
        )

        # Now trace back to find the source of this resolved value
        # Check device config first
        if credential_type == "username" and dev.user == resolved_value:
            return "device config file (config/devices/devices.yml)"
        if credential_type == "password" and dev.password == resolved_value:
            return "device config file (config/devices/devices.yml)"

        # Check device-specific environment variables
        env_var_name = (
            f"NW_{credential_type.upper()}_{self.device_name.upper().replace('-', '_')}"
        )
        if os.getenv(env_var_name) == resolved_value:
            return f"environment ({env_var_name})"

        # Check group-level credentials
        group_user, group_password = self.config.get_group_credentials(self.device_name)
        target_credential = (
            group_user if credential_type == "username" else group_password
        )

        if target_credential == resolved_value:
            # Find which group provided the credential
            device_groups = self.config.get_device_groups(self.device_name)
            for group_name in device_groups:
                group = (
                    self.config.device_groups.get(group_name)
                    if self.config.device_groups
                    else None
                )
                if group and group.credentials:
                    if (
                        credential_type == "username"
                        and group.credentials.user == resolved_value
                    ):
                        return (
                            f"group config file config/groups/groups.yml ({group_name})"
                        )
                    elif (
                        credential_type == "password"
                        and group.credentials.password == resolved_value
                    ):
                        return (
                            f"group config file config/groups/groups.yml ({group_name})"
                        )

                # Check group environment variable
                if (
                    EnvironmentCredentialManager.get_group_specific(
                        group_name, credential_type
                    )
                    == resolved_value
                ):
                    grp_env = f"NW_{credential_type.upper()}_{group_name.upper().replace('-', '_')}"
                    return f"environment ({grp_env})"

        # Check default environment variables
        default_env_var = f"NW_{credential_type.upper()}_DEFAULT"
        default_env_value = os.getenv(default_env_var)
        if default_env_value and default_env_value == resolved_value:
            return f"environment ({default_env_var})"

        # If we reach here, it must be from config general defaults
        return f"config (general.default_{credential_type})"

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return f"device={self.device_name} error=not_found"

        device_config = devices[self.device_name]
        return f"device={self.device_name} host={device_config.host} type={device_config.device_type}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return None
        return [f"Detailed information for device: {self.device_name}"]

    def _get_device_source(self) -> str:
        """Return the exact source file for this device as tracked by the config loader."""
        config_dir = self.config_path.parent if self.config_path else Path("config")
        src_path = self.config.get_device_source_path(self.device_name)
        if src_path is None:
            return "config file (unknown)"
        try:
            rel = src_path.relative_to(config_dir)
            return f"config file ({rel})"
        except Exception:
            return f"config file ({src_path})"


class GroupInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for group information table."""

    config: NetworkConfig
    group_name: str
    config_path: Path | None = None

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title=f"Group: {self.group_name}",
            columns=[
                TableColumn(header="Property", style=StyleName.DEVICE),
                TableColumn(header="Value", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get group information data."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return [["Error", f"Group '{self.group_name}' not found"]]

        group = device_groups[self.group_name]
        rows = []

        # Get actual group members using the config method
        try:
            group_members = self.config.get_group_members(self.group_name)
        except Exception:
            group_members = []

        rows.append(["Name", self.group_name])
        rows.append(["Description", getattr(group, "description", "N/A") or "N/A"])
        rows.append(["Source", self._get_group_source()])
        rows.append(["Device Count", str(len(group_members))])
        rows.append(["Devices", ", ".join(group_members) if group_members else "None"])

        return rows

    def _get_group_source(self) -> str:
        """Determine the source file for this group using the same discovery logic as config loading."""
        # Use the actual config path from the command context
        if self.config_path:
            if self.config_path.is_file():
                config_dir = self.config_path.parent
            else:
                config_dir = self.config_path
        else:
            config_dir = Path("config")

        # Direct approach: check the known location first since we know it works
        groups_s3n = config_dir / "groups" / "s3n.yml"
        if groups_s3n.exists():
            try:
                with groups_s3n.open("r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict) and "groups" in data:
                        if self.group_name in data["groups"]:
                            rel_path = groups_s3n.relative_to(config_dir)
                            return f"config file ({rel_path})"
            except Exception:
                pass

        # Fallback to full discovery
        group_files: list[Path] = []

        # Main config file in root
        for ext in [".yml", ".yaml", ".csv"]:
            main_file = config_dir / f"groups{ext}"
            if main_file.exists():
                group_files.append(main_file)

        # Subdirectory files
        subdir = config_dir / "groups"
        if subdir.exists() and subdir.is_dir():
            # All yaml/csv files in subdirectory
            for pattern in ["*.yml", "*.yaml", "*.csv"]:
                group_files.extend(subdir.glob(pattern))

        # Now search through the discovered files for our group
        for group_file in group_files:
            try:
                if group_file.suffix.lower() in [".yml", ".yaml"]:
                    with group_file.open("r", encoding="utf-8") as f:
                        data = yaml.safe_load(f)
                        if isinstance(data, dict) and "groups" in data:
                            if self.group_name in data["groups"]:
                                rel_path = group_file.relative_to(config_dir)
                                return f"config file ({rel_path})"
            except Exception as exc:
                import logging

                logging.debug(
                    f"Error scanning group file {group_file} for group {self.group_name}: {exc}"
                )
                continue

        # Fallback
        return f"config file ({config_dir}/groups/) - checked {len(group_files)} files"

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return f"group={self.group_name} error=not_found"

        try:
            group_members = self.config.get_group_members(self.group_name)
            device_count = len(group_members)
        except Exception:
            device_count = 0

        return f"group={self.group_name} device_count={device_count}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return None
        return [f"Detailed information for group: {self.group_name}"]
