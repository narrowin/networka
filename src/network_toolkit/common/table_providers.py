# SPDX-License-Identifier: MIT
"""Table data providers for centralized table generation using Pydantic v2."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

from network_toolkit.common.styles import StyleName
from network_toolkit.common.table_generator import TableColumn, TableDefinition
from network_toolkit.config import NetworkConfig, get_supported_device_types
from network_toolkit.ip_device import (
    get_supported_device_types as get_device_descriptions,
)
from network_toolkit.platforms.factory import (
    get_supported_platforms as get_platform_ops,
)

if TYPE_CHECKING:
    from network_toolkit.sequence_manager import SequenceRecord


class DeviceListTableProvider(BaseModel):
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


class GroupListTableProvider(BaseModel):
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


class TransportTypesTableProvider(BaseModel):
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


class SupportedPlatformsTableProvider(BaseModel):
    """Provides supported platforms table data using Pydantic v2."""

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for device types."""
        return TableDefinition(
            title="Device Types",
            columns=[
                TableColumn(header="Device Type", style=StyleName.PLATFORM),
                TableColumn(header="Description", style=StyleName.OUTPUT),
                TableColumn(header="Platform Ops", style=StyleName.SUCCESS),
                TableColumn(header="Transport Support", style=StyleName.TRANSPORT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for device types."""
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

    def get_raw_output(self) -> str:
        """Get raw mode output for device types."""
        device_types = get_supported_device_types()
        device_descriptions = get_device_descriptions()
        platform_ops = get_platform_ops()

        lines = []
        for device_type in sorted(device_types):
            description = device_descriptions.get(device_type, "No description")
            has_platform_ops = "yes" if device_type in platform_ops else "no"
            lines.append(
                f"device_type={device_type} description={description} platform_ops={has_platform_ops} transport=scrapli"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for device types."""
        device_types = get_supported_device_types()
        platform_ops = get_platform_ops()

        return [
            f"Total device types: {len(device_types)}",
            f"With platform operations: {len(platform_ops)}",
            "Available transports: scrapli (default)",
            "",
            "Usage Examples:",
            "  # Use in device configuration:",
            "  devices:",
            "    my_device:",
            "      host: 192.168.1.1",
            "      device_type: mikrotik_routeros",
            "      transport_type: scrapli  # Optional, defaults to scrapli",
            "",
            "  # Use with IP addresses:",
            "    nw run 192.168.1.1 my_command --device-type mikrotik_routeros",
        ]


class VendorSequencesTableProvider(BaseModel):
    """Provides vendor sequences table data using Pydantic v2."""

    vendor: str
    sequences: dict[str, SequenceRecord]
    category_filter: str | None = None

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for vendor sequences."""
        return TableDefinition(
            title=f"{self.vendor.title()} Sequences",
            columns=[
                TableColumn(header="Name", style=StyleName.SEQUENCE),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Category", style=StyleName.WARNING),
                TableColumn(header="Commands", style=StyleName.OUTPUT),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for vendor sequences."""
        rows = []
        for name, seq in self.sequences.items():
            if self.category_filter and seq.category != self.category_filter:
                continue

            rows.append(
                [
                    name,
                    seq.description,
                    seq.category or "N/A",
                    f"{len(seq.commands)} commands",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for vendor sequences."""
        lines = []
        for name, seq in self.sequences.items():
            if self.category_filter and seq.category != self.category_filter:
                continue
            category = seq.category or "none"
            commands_count = len(seq.commands)
            lines.append(
                f"sequence={name} vendor={self.vendor} category={category} commands={commands_count}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for vendor sequences."""
        filtered_sequences = {
            name: seq
            for name, seq in self.sequences.items()
            if not self.category_filter or seq.category == self.category_filter
        }

        if not filtered_sequences:
            return None

        return [
            f"Total {self.vendor} sequences: {len(filtered_sequences)}",
            f"Vendor: {self.vendor}",
            f"Category filter: {self.category_filter or 'None'}",
            "",
            "Usage Examples:",
            f"  nw run <device> <sequence_name>  # Run {self.vendor} sequence",
        ]


class GlobalSequencesTableProvider(BaseModel):
    """Provides global sequences table data using Pydantic v2."""

    sequences: dict[str, object]  # CommandSequence objects

    model_config = {"arbitrary_types_allowed": True}

    def get_table_definition(self) -> TableDefinition:
        """Get table definition for global sequences."""
        return TableDefinition(
            title="Global Sequences",
            columns=[
                TableColumn(header="Name", style=StyleName.SEQUENCE),
                TableColumn(header="Description", style=StyleName.SUCCESS),
                TableColumn(header="Commands", style=StyleName.OUTPUT),
                TableColumn(header="Tags", style=StyleName.WARNING),
            ],
        )

    def get_table_rows(self) -> list[list[str]]:
        """Get table rows for global sequences."""
        rows = []
        for name, seq in self.sequences.items():
            # Handle CommandSequence object attributes
            description = getattr(seq, "description", "N/A")
            commands = getattr(seq, "commands", [])
            tags = getattr(seq, "tags", None)

            rows.append(
                [
                    name,
                    description,
                    f"{len(commands)} commands",
                    ", ".join(tags) if tags else "None",
                ]
            )
        return rows

    def get_raw_output(self) -> str:
        """Get raw mode output for global sequences."""
        lines = []
        for name, seq in self.sequences.items():
            description = getattr(seq, "description", "N/A")
            commands = getattr(seq, "commands", [])
            tags = getattr(seq, "tags", None)
            tags_str = ",".join(tags) if tags else "none"
            lines.append(
                f"sequence={name} type=global description={description} commands={len(commands)} tags={tags_str}"
            )
        return "\n".join(lines)

    def get_verbose_info(self) -> list[str] | None:
        """Get verbose information for global sequences."""
        if not self.sequences:
            return None

        return [
            f"Total global sequences: {len(self.sequences)}",
            "Type: Global (vendor-independent)",
            "",
            "Usage Examples:",
            "  nw run <device> <sequence_name>  # Run global sequence",
        ]
