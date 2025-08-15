"""TUI models and types (Pydantic v2).

Defines validated data structures used by the Textual UI and services layer
without importing the UI framework at module import time.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from pydantic import BaseModel, ConfigDict, Field


class SelectionState(BaseModel):
    """Current user selections and inputs.

    - Sets are validated from any iterable and de-duplicated.
    - ``command_text`` defaults to empty string.
    """

    model_config = ConfigDict(frozen=False)

    devices: set[str] = Field(default_factory=set)
    groups: set[str] = Field(default_factory=set)
    sequences: set[str] = Field(default_factory=set)
    command_text: str = ""


# Execution plan mapping device -> list of commands to run
ExecutionPlan = dict[str, list[str]]


class RunResult(BaseModel):
    """Summary of an execution run."""

    model_config = ConfigDict(frozen=True)

    total: int
    successes: int
    failures: int

    def human_summary(self) -> str:
        return (
            f"Devices completed: {self.successes} succeeded, "
            f"{self.failures} failed, total: {self.total}"
        )


class RunCallbacks(BaseModel):
    """Callbacks used to stream execution output.

    All callbacks should be fast and non-blocking. They may be invoked from a
    background thread. Implementations must be thread-safe.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    on_output: Callable[[str], None]
    on_error: Callable[[str], None]
    on_meta: Callable[[str], None]


def iter_commands(text: str) -> Iterable[str]:
    """Yield one command per non-empty line from free-form text."""
    for line in (text or "").splitlines():
        stripped = line.strip()
        if stripped:
            yield stripped
