"""Layout builders for the Textual TUI.

Pure functions that compose the widget tree. Keeps UI structure separate from
behavior, enabling easier testing and maintenance.
"""

from __future__ import annotations

from typing import Any

from network_toolkit.tui.constants import (
    ID_ACTIONS_TABS,
    ID_BOTTOM,
    ID_FILTER_DEVICES,
    ID_FILTER_GROUPS,
    ID_FILTER_OUTPUT,
    ID_FILTER_SEQUENCES,
    ID_FILTER_SUMMARY,
    ID_HELP_LOG,
    ID_HELP_PANEL,
    ID_INPUT_COMMANDS,
    ID_LAYOUT,
    ID_LIST_DEVICES,
    ID_LIST_GROUPS,
    ID_LIST_SEQUENCES,
    ID_OUTPUT_LOG,
    ID_OUTPUT_PANEL,
    ID_RUN_BUTTON,
    ID_RUN_STATUS,
    ID_RUN_SUMMARY,
    ID_SUMMARY_PANEL,
    ID_TAB_COMMANDS,
    ID_TAB_DEVICES,
    ID_TAB_GROUPS,
    ID_TAB_SEQUENCES,
    ID_TARGETS_TABS,
    LBL_ACTIONS,
    LBL_HELP,
    LBL_OUTPUT,
    LBL_PRESS_ENTER,
    LBL_RUN,
    LBL_SUMMARY,
    LBL_TARGETS,
)


def compose_root(compat: Any) -> Any:
    header = compat.Header
    footer = compat.Footer
    vertical = compat.Vertical
    horizontal = compat.Horizontal
    static = compat.Static
    tabbed_content = compat.TabbedContent
    tab_pane = compat.TabPane

    yield header(show_clock=True)
    with vertical(id=ID_LAYOUT):
        with horizontal(id="top"):
            with vertical(classes="panel"):
                yield static(LBL_TARGETS, classes="pane-title title")
                with tabbed_content(id=ID_TARGETS_TABS):
                    with tab_pane("Devices", id=ID_TAB_DEVICES):
                        yield _filter_input(
                            compat, ID_FILTER_DEVICES, "Filter devices..."
                        )
                        yield compat.SelectionList(id=ID_LIST_DEVICES, classes="scroll")
                    with tab_pane("Groups", id=ID_TAB_GROUPS):
                        yield _filter_input(
                            compat, ID_FILTER_GROUPS, "Filter groups..."
                        )
                        yield compat.SelectionList(id=ID_LIST_GROUPS, classes="scroll")
            with vertical(classes="panel"):
                yield static(LBL_ACTIONS, classes="pane-title title")
                with tabbed_content(id=ID_ACTIONS_TABS):
                    with tab_pane("Sequences", id=ID_TAB_SEQUENCES):
                        yield _filter_input(
                            compat, ID_FILTER_SEQUENCES, "Filter sequences..."
                        )
                        yield compat.SelectionList(
                            id=ID_LIST_SEQUENCES, classes="scroll"
                        )
                    with tab_pane("Commands", id=ID_TAB_COMMANDS):
                        yield compat.Input(
                            placeholder="Enter a command and press Enter to run",
                            id=ID_INPUT_COMMANDS,
                        )
                yield static(LBL_PRESS_ENTER, classes="title")
                yield compat.Button(LBL_RUN, id=ID_RUN_BUTTON)
        with vertical(id=ID_BOTTOM):
            yield static("Status: idle", id=ID_RUN_STATUS)
            with vertical(classes="panel hidden", id=ID_SUMMARY_PANEL):
                yield static(LBL_SUMMARY, classes="pane-title title")
                yield compat.TextLogClass(id=ID_RUN_SUMMARY, classes="scroll")
                yield _filter_input(compat, ID_FILTER_SUMMARY, "Filter summary...")
            with vertical(classes="panel hidden", id=ID_HELP_PANEL):
                yield static(LBL_HELP, classes="pane-title title")
                yield compat.TextLogClass(id=ID_HELP_LOG, classes="scroll")
            with vertical(classes="panel hidden", id=ID_OUTPUT_PANEL):
                yield static(LBL_OUTPUT, classes="pane-title title")
                yield compat.TextLogClass(id=ID_OUTPUT_LOG, classes="scroll")
                yield _filter_input(compat, ID_FILTER_OUTPUT, "Filter output...")
    yield footer()


def _filter_input(compat: Any, element_id: str, placeholder: str) -> Any:
    return compat.Input(placeholder=placeholder, id=element_id, classes="search")
