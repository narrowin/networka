# SPDX-License-Identifier: MIT
"""Table data providers for centralized table generation using Pydantic v2."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from network_toolkit.api.list import DeviceInfo, GroupInfo, SequenceInfo
from network_toolkit.common.styles import StyleName
from network_toolkit.common.table_generator import (
    BaseTableProvider,
    TableColumn,
    TableDefinition,
)
from network_toolkit.config import NetworkConfig, get_supported_device_types
from network_toolkit.credentials import CredentialResolver
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

    devices: list[DeviceInfo]

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for device list."""
        return TableDefinition(
            title="Devices",
            columns=[
                TableColumn(header="Name", style=StyleName.DEVICE),
                TableColumn(header="Source", style=StyleName.WARNING),
                TableColumn(header="Host", style=StyleName.HOST),
                TableColumn(header="Type", style=StyleName.PLATFORM),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Tags", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for device list."""
        if not self.devices:
            return []

        rows = []
        for device in self.devices:
            rows.append(
                [
                    device.name,
                    device.source or "config",
                    device.hostname,
                    device.device_type,
                    device.description or "N/A",
                    ", ".join(device.tags) if device.tags else "None",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for device list."""
        if not self.devices:
            return ""

        lines = []
        for device in self.devices:
            tags_str = ",".join(device.tags or []) if device.tags else "none"
            platform = device.device_type
            source = device.source or "config"
            lines.append(
                f"device={device.name} source={source} host={device.hostname} platform={platform} tags={tags_str}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for device list."""
        if not self.devices:
            return None

        return [
            f"Total devices: {len(self.devices)}",
            "Usage Examples:",
            "  nw run <device_name> <command>",
            "  nw info <device_name>",
        ]


class GroupListTableProvider(BaseModel, BaseTableProvider):
    """Provides group list table data using Pydantic v2."""

    groups: list[GroupInfo]

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for group list."""
        return TableDefinition(
            title="Groups",
            columns=[
                TableColumn(header="Group Name", style=StyleName.GROUP),
                TableColumn(header="Source", style=StyleName.WARNING),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Match Tags", style=StyleName.WARNING),
                TableColumn(header="Members", style=StyleName.DEVICE),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for group list."""
        if not self.groups:
            return []

        rows = []
        for group in self.groups:
            rows.append(
                [
                    group.name,
                    group.source or "config",
                    group.description or "",
                    ", ".join(group.match_tags) if group.match_tags else "N/A",
                    ", ".join(group.members) if group.members else "None",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for group list."""
        if not self.groups:
            return ""

        lines = []
        for group in self.groups:
            members_str = ",".join(group.members) if group.members else "none"
            tags_str = ",".join(group.match_tags or []) if group.match_tags else "none"
            description = group.description or ""
            source = group.source or "config"
            lines.append(
                f"group={group.name} source={source} description={description} tags={tags_str} members={members_str}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for group list."""
        if not self.groups:
            return None

        return [
            f"Total groups: {len(self.groups)}",
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

    sequences: list[SequenceInfo]
    vendor_filter: str | None = None
    verbose: bool = False

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        columns = [
            TableColumn(header="Sequence Name", style=StyleName.DEVICE),
            TableColumn(header="Description", style=StyleName.SUCCESS),
            TableColumn(header="Vendor", style=StyleName.WARNING),
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

        for seq in self.sequences:
            commands_str = ", ".join(seq.commands) if seq.commands else "N/A"

            row = [
                seq.name,
                seq.description or "N/A",
                seq.vendor or "N/A",
                seq.category,
                (commands_str[:50] + "..." if len(commands_str) > 50 else commands_str),
            ]

            if self.verbose:
                timeout = str(seq.timeout) if seq.timeout is not None else "Default"
                device_types = (
                    ", ".join(seq.device_types) if seq.device_types else "All"
                )
                row.extend([timeout, device_types])

            rows.append(row)

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        lines = []
        for seq in self.sequences:
            lines.append(f"vendor={seq.vendor} sequence={seq.name}")
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        if self.vendor_filter:
            return [f"Vendor: {self.vendor_filter}, Sequences: {len(self.sequences)}"]
        else:
            # Count unique vendors
            vendors = {seq.vendor for seq in self.sequences if seq.vendor}
            return [
                f"Total Vendors: {len(vendors)}",
                f"Total Sequences: {len(self.sequences)}",
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
        device_types = get_supported_device_types()
        rows = []
        for device_type in sorted(device_types):
            rows.append([device_type, "Network", "SSH", "show commands, config"])
        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        lines = []
        for row in self.get_table_rows():
            platform, device_type, transport, _operations = row
            lines.append(
                f"platform={platform} device_type={device_type} transport={transport}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return ["Platforms supported by the network toolkit transport layer"]


class GlobalSequenceInfoTableProvider(BaseModel, BaseTableProvider):
    """Provider for global sequence info table."""

    # Config is optional for tests that instantiate the provider directly
    config: NetworkConfig | None = None
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
        rows: list[list[str]] = [
            ["Description", getattr(self.sequence, "description", "No description")],
            ["Source", self._get_sequence_source()],
            ["Command Count", str(len(getattr(self.sequence, "commands", [])))],
        ]

        # Add individual commands with truncation for long lists
        commands = getattr(self.sequence, "commands", [])
        max_preview = 3
        for i, cmd in enumerate(commands[:max_preview], 1):
            rows.append([f"Command {i}", str(cmd)])

        remaining = max(0, len(commands) - max_preview)
        if remaining > 0:
            rows.append(["Note", f"({remaining} more commands)"])

        # Add tags if available
        tags = getattr(self.sequence, "tags", [])
        if tags:
            rows.append(["Tags", ", ".join(tags)])

        return rows

    def _get_sequence_source(self) -> str:
        """
        Determine the source of this global sequence.

        Prefer the exact config file path recorded by the loader. When running
        with mocked configs (tests that don't provide loader metadata), fall back
        to a stable label.
        """
        # Try to use loader metadata if available
        try:
            if self.config is not None and hasattr(
                self.config, "get_global_sequence_source_path"
            ):
                src = self.config.get_global_sequence_source_path(self.sequence_name)
                if isinstance(src, Path):
                    try:
                        return str(src.resolve())
                    except Exception:
                        return str(src)
        except Exception:
            # Ignore and fall back to stable label
            pass

        # Fallback for mocked/global sequences without tracked source
        return "Global (config)"

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
                    return f"Built-in vendor sequences ({path.name})"
                return "Built-in vendor sequences"
            elif origin in {"repo", "user"}:
                # Prefer explicit path if provided
                if path:
                    return f"config file ({path.resolve()})"
                # Try loader metadata to get exact filename
                try:
                    if self.config and getattr(self.config, "vendor_sequences", None):
                        for _vendor_key, seqs in (
                            self.config.vendor_sequences or {}
                        ).items():
                            seq_obj = seqs.get(self.sequence_name)
                            if seq_obj is not None:
                                src = getattr(seq_obj, "_source_path", None)
                                if src:
                                    return f"config file ({Path(src).resolve()})"
                except Exception:
                    pass
                # Fall back to generic label by origin
                return (
                    "repository config sequences"
                    if origin == "repo"
                    else "user config sequences"
                )
            elif origin == "global":
                return "global config sequences"

        # Fallback: try loader metadata if config is provided
        try:
            if self.config and getattr(self, "vendor_names", None):
                vendor_sequences = getattr(self.config, "vendor_sequences", {}) or {}
                for vendor in self.vendor_names:
                    seqs = vendor_sequences.get(vendor.replace(" ", "_"), {})
                    seq_obj = seqs.get(self.sequence_name)
                    if seq_obj is not None:
                        src = getattr(seq_obj, "_source_path", None)
                        if src:
                            return f"config file ({Path(src).resolve()})"
        except Exception:
            # Ignore and continue to final fallback
            pass

        # Final fallback
        return "Built-in vendor sequences"

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
            transport, description, _mapping = row
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
            device_type, description, platform_ops, _transport = row
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
    show_provenance: bool = True  # Always show source column
    verbose_provenance: bool = False  # Full paths vs compact display (--trace)

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        columns = [
            TableColumn(header="Property", style=StyleName.DEVICE),
            TableColumn(header="Value", style=StyleName.OUTPUT),
        ]
        if self.show_provenance:
            columns.append(TableColumn(header="Source", style=StyleName.WARNING))
        return TableDefinition(
            title=f"Device: {self.device_name}",
            columns=columns,
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get device information data."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            row = ["Error", f"Device '{self.device_name}' not found"]
            return [[*row, "-"] if self.show_provenance else row]

        device_config = devices[self.device_name]
        rows: list[list[str]] = []

        def add_row(prop: str, value: str, source: str = "-") -> None:
            if self.show_provenance:
                rows.append([prop, value, source])
            else:
                rows.append([prop, value])

        # Get field history for provenance display
        def get_source(field_name: str) -> str:
            history = device_config.get_field_source(field_name)
            if history:
                return history.format_source(verbose=self.verbose_provenance)
            return "-"

        # Basic device information with sources
        add_row("Host", device_config.host, get_source("host"))
        add_row(
            "Description", device_config.description or "N/A", get_source("description")
        )
        add_row("Device Type", device_config.device_type, get_source("device_type"))
        add_row("Model", device_config.model or "N/A", get_source("model"))
        add_row(
            "Platform",
            device_config.platform or device_config.device_type,
            get_source("platform"),
        )
        add_row("Location", device_config.location or "N/A", get_source("location"))
        add_row(
            "Tags",
            ", ".join(device_config.tags) if device_config.tags else "None",
            get_source("tags"),
        )
        add_row("Source File", self._get_device_source(), "-")
        add_row("Inventory Source", self._get_device_inventory_source(), "-")

        # Connection parameters with credential sources
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

        # Get credential sources using the enhanced resolver
        user_source_str = self._get_credential_source("username")
        pass_source_str = self._get_credential_source("password")

        add_row("SSH Port", str(conn_params["port"]), get_source("port"))
        add_row("Username", conn_params["auth_username"], user_source_str)

        # Password handling with environment variable support
        show_passwords = self._env_truthy("NW_SHOW_PLAINTEXT_PASSWORDS")
        if show_passwords:
            password_value = conn_params["auth_password"] or ""
            if password_value:
                add_row("Password", password_value, pass_source_str)
            else:
                add_row(
                    "Password",
                    "(empty - set NW_SHOW_PLAINTEXT_PASSWORDS=1 to display)",
                    pass_source_str,
                )
        else:
            add_row(
                "Password",
                "set NW_SHOW_PLAINTEXT_PASSWORDS=1 to display",
                pass_source_str,
            )

        add_row("Timeout", f"{conn_params['timeout_socket']}s", "default")

        # Transport type
        transport_type = self.config.get_transport_type(self.device_name)
        add_row("Transport Type", transport_type, "default")

        # Group memberships
        group_memberships = []
        if self.config.device_groups:
            for group_name, _group_config in self.config.device_groups.items():
                if self.device_name in self.config.get_group_members(group_name):
                    group_memberships.append(group_name)

        if group_memberships:
            add_row("Groups", ", ".join(group_memberships), "computed")

        return rows

    def _env_truthy(self, var_name: str) -> bool:
        """Check if environment variable is truthy."""
        val = os.getenv(var_name, "")
        return val.strip().lower() in {"1", "true", "yes", "y", "on"}

    def _get_credential_source(self, credential_type: str) -> str:
        """Get the source of a credential using CredentialResolver.

        Uses the resolver's with_source methods to avoid duplicating resolution logic.
        """
        # Check interactive override first
        if self.interactive_creds:
            if credential_type == "username" and getattr(
                self.interactive_creds, "username", None
            ):
                return "interactive input"
            if credential_type == "password" and getattr(
                self.interactive_creds, "password", None
            ):
                return "interactive input"

        # Use CredentialResolver with source tracking
        resolver = CredentialResolver(self.config)
        try:
            _, (user_source, pass_source) = resolver.resolve_credentials_with_source(
                self.device_name
            )
            source = user_source if credential_type == "username" else pass_source
            return source.format()
        except ValueError:
            return "unknown"

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return f"device={self.device_name} error=not_found"

        device_config = devices[self.device_name]
        source = self._get_device_inventory_source()
        return (
            f"device={self.device_name} source={source} host={device_config.host} "
            f"type={device_config.device_type}"
        )

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return None
        return [f"Detailed information for device: {self.device_name}"]

    def _get_device_source(self) -> str:
        """Return the exact source file for this device as tracked by the config loader."""
        # Always present absolute path
        src_path = self.config.get_device_source_path(self.device_name)
        if src_path is None:
            return "unknown"
        try:
            return str(src_path.resolve())
        except Exception:
            return str(src_path)

    def _get_device_inventory_source(self) -> str:
        try:
            source_id = self.config.get_device_inventory_source_id(self.device_name)
        except Exception:
            source_id = None
        return source_id or "config"


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
        rows.append(["Inventory Source", self._get_group_inventory_source()])
        rows.append(["Device Count", str(len(group_members))])
        rows.append(["Devices", ", ".join(group_members) if group_members else "None"])

        return rows

    def _get_group_source(self) -> str:
        """Determine the source file for this group via loader metadata."""
        try:
            src = self.config.get_group_source_path(self.group_name)
            if src is None:
                return "unknown"
            return str(Path(src).resolve())
        except Exception:
            return "unknown"

    def _get_group_inventory_source(self) -> str:
        try:
            source_id = self.config.get_group_inventory_source_id(self.group_name)
        except Exception:
            source_id = None
        return source_id or "config"

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

        source = self._get_group_inventory_source()
        return f"group={self.group_name} source={source} device_count={device_count}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return None
        return [f"Detailed information for group: {self.group_name}"]
