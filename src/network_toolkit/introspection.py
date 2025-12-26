# SPDX-FileCopyrightText: 2025-present Network Team <network@company.com>
#
# SPDX-License-Identifier: MIT
"""Config introspection infrastructure for tracing value origins.

Inspired by Dynaconf's inspect_settings() pattern, this module provides
the "Where did X come from?" feature for configuration values.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class LoaderType(str, Enum):
    """Source type for a configuration value."""

    CONFIG_FILE = "config_file"
    ENV_VAR = "env_var"
    DOTENV = "dotenv"
    GROUP = "group"
    SSH_CONFIG = "ssh_config"
    PYDANTIC_DEFAULT = "default"
    CLI = "cli"
    INTERACTIVE = "interactive"


@dataclass(frozen=True)
class FieldHistory:
    """A single historical record for a configuration field value.

    Attributes
    ----------
    field_name : str
        Name of the configuration field (e.g., 'user', 'password', 'host')
    value : Any
        The value that was set
    loader : LoaderType
        The source type that provided this value
    identifier : str | None
        Additional identifier (e.g., env var name, file path, group name)
    line_number : int | None
        Line number in the source file, if applicable
    merged : bool
        Whether this value was merged from multiple sources
    """

    field_name: str
    value: Any
    loader: LoaderType
    identifier: str | None = None
    line_number: int | None = None
    merged: bool = False

    def format_source(self) -> str:
        """Format the source as a human-readable string.

        Returns
        -------
        str
            Human-readable source description
        """
        if self.loader == LoaderType.ENV_VAR:
            return f"env: {self.identifier}" if self.identifier else "env"
        elif self.loader == LoaderType.DOTENV:
            return f"dotenv: {self.identifier}" if self.identifier else "dotenv"
        elif self.loader == LoaderType.CONFIG_FILE:
            if self.identifier:
                path = Path(self.identifier)
                # Show relative path if possible
                try:
                    rel_path = path.relative_to(Path.cwd())
                    loc = str(rel_path)
                except ValueError:
                    loc = str(path)
                if self.line_number:
                    return f"{loc}:{self.line_number}"
                return loc
            return "config"
        elif self.loader == LoaderType.GROUP:
            return f"group: {self.identifier}" if self.identifier else "group"
        elif self.loader == LoaderType.SSH_CONFIG:
            return f"ssh_config: {self.identifier}" if self.identifier else "ssh_config"
        elif self.loader == LoaderType.PYDANTIC_DEFAULT:
            return "default"
        elif self.loader == LoaderType.CLI:
            return "cli"
        elif self.loader == LoaderType.INTERACTIVE:
            return "interactive"
        return str(self.loader.value)


@dataclass
class ConfigHistory:
    """Tracks the history of configuration field values.

    This class maintains a record of all values set for each field,
    allowing introspection of where the current value came from and
    what other values were considered.
    """

    _history: dict[str, list[FieldHistory]] = field(default_factory=dict)

    def record(self, entry: FieldHistory) -> None:
        """Record a field history entry.

        Parameters
        ----------
        entry : FieldHistory
            The history entry to record
        """
        if entry.field_name not in self._history:
            self._history[entry.field_name] = []
        self._history[entry.field_name].append(entry)

    def record_field(
        self,
        field_name: str,
        value: Any,
        loader: LoaderType,
        identifier: str | None = None,
        line_number: int | None = None,
        *,
        merged: bool = False,
    ) -> None:
        """Convenience method to record a field value.

        Parameters
        ----------
        field_name : str
            Name of the field
        value : Any
            The value being set
        loader : LoaderType
            Source type
        identifier : str | None
            Additional identifier
        line_number : int | None
            Line number in source file
        merged : bool
            Whether this was merged
        """
        entry = FieldHistory(
            field_name=field_name,
            value=value,
            loader=loader,
            identifier=identifier,
            line_number=line_number,
            merged=merged,
        )
        self.record(entry)

    def get_history(self, field_name: str) -> list[FieldHistory]:
        """Get the history of values for a field.

        Parameters
        ----------
        field_name : str
            Name of the field

        Returns
        -------
        list[FieldHistory]
            List of history entries, oldest first
        """
        return self._history.get(field_name, [])

    def get_current(self, field_name: str) -> FieldHistory | None:
        """Get the current (most recent) value for a field.

        Parameters
        ----------
        field_name : str
            Name of the field

        Returns
        -------
        FieldHistory | None
            The most recent history entry, or None if no history
        """
        history = self.get_history(field_name)
        return history[-1] if history else None

    def get_all_fields(self) -> list[str]:
        """Get all field names that have history.

        Returns
        -------
        list[str]
            List of field names
        """
        return list(self._history.keys())

    def clear(self) -> None:
        """Clear all history."""
        self._history.clear()

    def merge_from(self, other: ConfigHistory) -> None:
        """Merge history from another ConfigHistory instance.

        Parameters
        ----------
        other : ConfigHistory
            History to merge from
        """
        for _field_name, entries in other._history.items():
            for entry in entries:
                self.record(entry)

    def to_dict(self) -> dict[str, list[dict[str, Any]]]:
        """Convert to a dictionary representation.

        Returns
        -------
        dict[str, list[dict[str, Any]]]
            Dictionary mapping field names to lists of history entries
        """
        result: dict[str, list[dict[str, Any]]] = {}
        for field_name, entries in self._history.items():
            result[field_name] = [
                {
                    "value": entry.value,
                    "loader": entry.loader.value,
                    "identifier": entry.identifier,
                    "line_number": entry.line_number,
                    "merged": entry.merged,
                    "source": entry.format_source(),
                }
                for entry in entries
            ]
        return result


@dataclass
class CredentialResolutionTrace:
    """Traces the resolution of a credential through the precedence chain.

    This captures not just where the final value came from, but which
    sources were checked and skipped during resolution.
    """

    credential_type: str  # 'username' or 'password'
    final_value: str | None
    final_source: FieldHistory | None
    checked_sources: list[tuple[str, FieldHistory | None]] = field(default_factory=list)

    def add_checked(self, source_name: str, result: FieldHistory | None) -> None:
        """Record a source that was checked during resolution.

        Parameters
        ----------
        source_name : str
            Name of the source (e.g., 'cli_override', 'device_config')
        result : FieldHistory | None
            The history entry if a value was found, None otherwise
        """
        self.checked_sources.append((source_name, result))

    def format_trace(self) -> list[str]:
        """Format the resolution trace as human-readable lines.

        Returns
        -------
        list[str]
            Lines describing the resolution process
        """
        lines = [f"Resolution trace for {self.credential_type}:"]
        for source_name, result in self.checked_sources:
            if result is not None:
                status = f"found: {result.format_source()}"
                if result == self.final_source:
                    status += " [SELECTED]"
            else:
                status = "not set"
            lines.append(f"  {source_name}: {status}")
        return lines
