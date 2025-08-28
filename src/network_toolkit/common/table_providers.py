# SPDX-License-Identifier: MIT
"""Table data providers for centralized table generation using Pydantic v2."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from network_toolkit.common.styles import StyleName
from network_toolkit.common.table_generator import (
    BaseTableProvider,
    TableColumn,
    TableDefinition,
)
from network_toolkit.config import NetworkConfig, get_supported_device_types
from network_toolkit.ip_device import (
    get_supported_device_types as get_device_descriptions,
)
from network_toolkit.platforms.factory import (
    get_supported_platforms as get_platform_ops,
)

if TYPE_CHECKING:
    pass


class LocalOnlyProvider(BaseModel, BaseTableProvider):
    """Base class for providers that only work with local config data.

    These providers never need network connectivity, credentials, or connection parameters.
    They only display information from configuration files and local data.
    """

    pass


class DeviceListTableProvider(LocalOnlyProvider):
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


class GroupListTableProvider(LocalOnlyProvider):
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


class TransportTypesTableProvider(LocalOnlyProvider):
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


class VendorSequencesTableProvider(LocalOnlyProvider):
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


class GlobalSequencesTableProvider(BaseModel, BaseTableProvider):
    """Provider for global sequences table."""

    config: NetworkConfig
    verbose: bool = False

    def get_table_definition(self) -> TableDefinition:
        columns = [
            TableColumn(header="Sequence Name", style=StyleName.DEVICE),
            TableColumn(header="Description", style=StyleName.SUCCESS),
            TableColumn(header="Commands", style=StyleName.OUTPUT),
        ]

        if self.verbose:
            columns.append(TableColumn(header="Tags", style=StyleName.WARNING))

        return TableDefinition(title="Global Sequences", columns=columns)

    def get_table_rows(self) -> list[list[str]]:
        """Get global sequences data."""
        rows = []
        global_sequences = self.config.global_command_sequences or {}

        for seq_name, sequence in global_sequences.items():
            # Handle both string commands and command objects
            if hasattr(sequence, "commands"):
                if isinstance(sequence.commands[0], str):
                    commands_str = ", ".join(sequence.commands)
                else:
                    commands_str = ", ".join([cmd.command for cmd in sequence.commands])
            else:
                commands_str = "N/A"

            row = [
                seq_name,
                getattr(sequence, "description", "N/A") or "N/A",
                commands_str[:50] + "..." if len(commands_str) > 50 else commands_str,
            ]

            if self.verbose:
                tags = ", ".join(getattr(sequence, "tags", [])) or "None"
                row.append(tags)

            rows.append(row)

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        global_sequences = self.config.global_command_sequences or {}
        lines = []
        for seq_name in global_sequences.keys():
            lines.append(f"sequence={seq_name} type=global")
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        global_sequences = self.config.global_command_sequences or {}
        total_sequences = len(global_sequences)
        return [f"Total global sequences: {total_sequences}"]


class SupportedPlatformsTableProvider(LocalOnlyProvider):
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


class GlobalSequenceInfoTableProvider(LocalOnlyProvider):
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
            ["Source", "Global (config)"],
            ["Command Count", str(len(getattr(self.sequence, "commands", [])))],
        ]

        # Add individual commands
        commands = getattr(self.sequence, "commands", [])
        if self.verbose or len(commands) <= 3:
            for i, cmd in enumerate(commands, 1):
                rows.append([f"Command {i}", str(cmd)])
        elif len(commands) > 3:
            for i, cmd in enumerate(commands[:3], 1):
                rows.append([f"Command {i}", str(cmd)])
            rows.append(["...", f"({len(commands) - 3} more commands)"])

        # Add tags if available
        tags = getattr(self.sequence, "tags", [])
        if tags:
            rows.append(["Tags", ", ".join(tags)])

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        commands = getattr(self.sequence, "commands", [])
        return f"sequence={self.sequence_name} type=global commands={len(commands)}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        return [f"Global sequence '{self.sequence_name}' details"]


class VendorSequenceInfoTableProvider(LocalOnlyProvider):
    """Provider for vendor sequence info table."""

    sequence_name: str
    sequence_record: Any  # SequenceRecord object
    vendor_names: list[str]
    verbose: bool = False

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title=f"Vendor Sequence: {self.sequence_name}",
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
            ["Source", "Built-in vendor sequences"],
            ["Command Count", str(len(getattr(self.sequence_record, "commands", [])))],
        ]

        # Add individual commands if verbose or few commands
        commands = getattr(self.sequence_record, "commands", [])
        if self.verbose or len(commands) <= 3:
            for i, cmd in enumerate(commands, 1):
                rows.append([f"Command {i}", str(cmd)])
        elif len(commands) > 3:
            for i, cmd in enumerate(commands[:3], 1):
                rows.append([f"Command {i}", str(cmd)])
            rows.append(["...", f"({len(commands) - 3} more commands)"])

        return rows

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


class TransportInfoTableProvider(LocalOnlyProvider):
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


class DeviceTypesInfoTableProvider(LocalOnlyProvider):
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


class DeviceInfoTableProvider(LocalOnlyProvider):
    """Provider for device configuration information (local config only).

    This provider shows only the device configuration data from local config files.
    It does not require or display any connection parameters, credentials, or network-related information.
    """

    config: NetworkConfig
    device_name: str
    # Note: interactive_creds removed - not needed for local config display

    def get_table_definition(self) -> TableDefinition:
        return TableDefinition(
            title=f"Device: {self.device_name}",
            columns=[
                TableColumn(header="Property", style=StyleName.DEVICE),
                TableColumn(header="Value", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get device configuration data (local config only)."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return [["Error", f"Device '{self.device_name}' not found"]]

        device_config = devices[self.device_name]
        rows = []

        # Device configuration information (from config files only)
        rows.append(["Name", self.device_name])
        rows.append(["Host", device_config.host])
        rows.append(["Description", device_config.description or "N/A"])
        rows.append(["Device Type", device_config.device_type])
        rows.append(["Model", device_config.model or "N/A"])
        rows.append(["Platform", device_config.platform or "N/A"])
        rows.append(["Location", device_config.location or "N/A"])
        rows.append(
            ["Tags", ", ".join(device_config.tags) if device_config.tags else "None"]
        )

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return f"device={self.device_name} error=not_found"

        device_config = devices[self.device_name]
        lines = []
        lines.append(f"name={self.device_name}")
        lines.append(f"host={device_config.host}")
        lines.append(f"device_type={device_config.device_type}")
        if device_config.description:
            lines.append(f"description={device_config.description}")
        if device_config.model:
            lines.append(f"model={device_config.model}")
        if device_config.platform:
            lines.append(f"platform={device_config.platform}")
        if device_config.location:
            lines.append(f"location={device_config.location}")
        if device_config.tags:
            lines.append(f"tags={','.join(device_config.tags)}")
        return " ".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        devices = self.config.devices or {}
        if self.device_name not in devices:
            return [f"Device '{self.device_name}' not found in configuration"]

        return [
            f"Configuration loaded from: {self.config.source_info}",
            "Device configuration shows static metadata only",
            f"Use 'nw run {self.device_name} <command>' for live device operations",
        ]


class GroupInfoTableProvider(LocalOnlyProvider):
    """Provider for group information table."""

    config: NetworkConfig
    group_name: str

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

        rows.append(["Name", self.group_name])
        rows.append(["Description", getattr(group, "description", "N/A") or "N/A"])
        rows.append(["Device Count", str(len(getattr(group, "devices", [])))])
        rows.append(["Devices", ", ".join(getattr(group, "devices", []))])

        return rows

    def get_raw_output(self) -> str | None:
        """Get raw data for JSON/CSV output."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return f"group={self.group_name} error=not_found"

        group = device_groups[self.group_name]
        device_count = len(getattr(group, "devices", []))
        return f"group={self.group_name} device_count={device_count}"

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information."""
        device_groups = self.config.device_groups or {}
        if self.group_name not in device_groups:
            return None
        return [f"Detailed information for group: {self.group_name}"]
