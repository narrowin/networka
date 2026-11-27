# SPDX-License-Identifier: MIT
"""Centralized table generation system for Networka."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Protocol

from pydantic import BaseModel
from rich.console import OverflowMethod
from rich.table import Table
from rich.text import Text

from network_toolkit.common.output import OutputManager, OutputMode
from network_toolkit.common.styles import StyleName


class TableColumn(BaseModel):
    """Table column definition with semantic styling."""

    header: str
    style: StyleName | None = None
    no_wrap: bool = False
    overflow: OverflowMethod = "ellipsis"


class TableDefinition(BaseModel):
    """Complete table definition with metadata."""

    title: str
    columns: list[TableColumn]
    show_header: bool = True


class TableDataProvider(Protocol):
    """Protocol for objects that can provide table data."""

    def get_table_definition(self) -> TableDefinition:
        """Get the table structure definition."""
        ...

    def get_table_rows(self) -> list[list[str]]:
        """Get the table data rows."""
        ...

    def get_raw_output(self) -> str | None:
        """Get raw mode output. Return None to use default raw formatting."""
        ...

    def get_verbose_info(self) -> list[str] | None:
        """Get additional verbose information. Return None if no verbose info."""
        ...


class TableGenerator:
    """Centralized table generation with consistent styling and output modes."""

    def __init__(self, output_manager: OutputManager):
        """Initialize table generator."""
        self.style_manager = output_manager.style_manager
        self.output_manager = output_manager

    def create_table(self, definition: TableDefinition) -> Table:
        """Create a styled table from definition."""
        table = self.style_manager.create_table(title=Text(definition.title))

        for column in definition.columns:
            table.add_column(
                column.header,
                style=self.style_manager.get_style(column.style)
                if column.style
                else None,
                no_wrap=column.no_wrap,
                overflow=column.overflow,
            )

        return table

    def render_table(self, provider: TableDataProvider, verbose: bool = False) -> None:
        """Generate and print table from data provider."""
        # Handle raw mode
        if self.output_manager.mode == OutputMode.RAW:
            raw_output = provider.get_raw_output()
            if raw_output:
                # Provider has custom raw output
                self.output_manager.print_output(raw_output.rstrip())
            else:
                # Generate default raw output
                self._print_default_raw(provider)
            return

        # Handle normal table rendering
        definition = provider.get_table_definition()
        rows = provider.get_table_rows()
        title = Text(
            definition.title, style=self.style_manager.get_style(StyleName.BOLD) or ""
        )

        if not rows:
            self.output_manager.console.print(title)
            self.output_manager.print_blank_line()
            self.output_manager.print_text(
                self.style_manager.format_message(
                    "No data available", StyleName.WARNING
                )
            )
            return

        # Display title
        self.output_manager.console.print(title)
        self.output_manager.print_blank_line()

        # Create and populate table
        table = self.create_table(definition)
        for row in rows:
            table.add_row(*(Text(cell) for cell in row))

        # Print table
        self.output_manager.print_table(table)
        self.output_manager.print_blank_line()

        # Print summary (only for list-type tables, not single-item info)
        # Single-item info tables have titles like "Device: name", "Group: name", etc.
        is_single_item_info = any(
            definition.title.startswith(prefix)
            for prefix in [
                "Device:",
                "Group:",
                "Vendor Sequence:",
                "Global Sequence:",
                "Device Sequence:",
            ]
        )

        if not is_single_item_info:
            self.output_manager.print_text(
                self.style_manager.format_message(
                    f"Total items: {len(rows)}", StyleName.INFO
                )
            )

        # Print verbose information if requested
        if verbose:
            verbose_info = provider.get_verbose_info()
            if verbose_info:
                self.output_manager.print_blank_line()
                for info_line in verbose_info:
                    self.output_manager.console.print(Text(info_line))

    def _print_default_raw(self, provider: TableDataProvider) -> None:
        """Print default raw mode output."""
        definition = provider.get_table_definition()
        rows = provider.get_table_rows()

        if not rows:
            return

        # Simple key=value format for raw mode
        for row in rows:
            values: list[str] = []
            for column, value in zip(definition.columns, row, strict=True):
                # Convert header to lowercase key
                key = column.header.lower().replace(" ", "_")
                # Escape spaces and special chars in values
                clean_value = str(value).replace(" ", "_").replace(",", ";")
                values.append(f"{key}={clean_value}")
            self.output_manager.print_output(" ".join(values))


class BaseTableProvider(ABC):
    """Abstract base class for table data providers."""

    @abstractmethod
    def get_table_definition(self) -> TableDefinition:
        """Get the table structure definition."""
        ...

    @abstractmethod
    def get_table_rows(self) -> list[list[str]]:
        """Get the table data rows."""
        ...

    def get_raw_output(self) -> str | None:
        """Default implementation returns None for default raw formatting."""
        return None

    def get_verbose_info(self) -> list[str] | None:
        """Default implementation returns None for no verbose info."""
        return None
