"""Constants for the TUI: IDs, labels, and CSS.

Keeping these in one place avoids magic strings scattered across the codebase.
"""

from __future__ import annotations

# Widget IDs
ID_LAYOUT = "layout"
ID_TOP = "top"
ID_BOTTOM = "bottom"
ID_OUTPUT_PANEL = "output-panel"
ID_SUMMARY_PANEL = "summary-panel"
ID_HELP_PANEL = "help-panel"
ID_OUTPUT_LOG = "output-log"
ID_RUN_STATUS = "run-status"
ID_HELP_LOG = "help-log"
ID_CANCEL_DIALOG = "cancel-dialog"

ID_TARGETS_TABS = "targets-tabs"
ID_ACTIONS_TABS = "actions-tabs"

ID_FILTER_DEVICES = "filter-devices"
ID_FILTER_GROUPS = "filter-groups"
ID_FILTER_SEQUENCES = "filter-sequences"
ID_FILTER_SUMMARY = "filter-summary"
ID_FILTER_OUTPUT = "filter-output"

ID_LIST_DEVICES = "list-devices"
ID_LIST_GROUPS = "list-groups"
ID_LIST_SEQUENCES = "list-sequences"
ID_RUN_SUMMARY = "run-summary"

ID_INPUT_COMMANDS = "input-commands"
ID_RUN_BUTTON = "run-button"

# Tab pane IDs
ID_TAB_DEVICES = "tab-devices"
ID_TAB_GROUPS = "tab-groups"
ID_TAB_SEQUENCES = "tab-sequences"
ID_TAB_COMMANDS = "tab-commands"

# Labels
LBL_TARGETS = "Targets"
LBL_ACTIONS = "Actions"
LBL_SUMMARY = "Summary"
LBL_OUTPUT = "Output"
LBL_HELP = "Help"
LBL_CANCEL = "Cancel"
LBL_PRESS_ENTER = "Press Enter to run"
LBL_RUN = "Run"

# Startup notice
STARTUP_NOTICE = "Prototype: This TUI is a work in progress — expect rough edges."


# Basic CSS used by the app
CSS = """
#layout { height: 1fr; }
#top { height: 1fr; }
#bottom { height: auto; }
#bottom.expanded { height: 3fr; }
#output-log { height: 1fr; }
#summary-panel { height: 1fr; }
.hidden { display: none; }
#top > .panel { height: 1fr; }
.panel Static.title { content-align: center middle; color: $secondary; }
.panel { border: round $surface; padding: 1 1; }
.pane-title { height: 3; content-align: center middle; text-style: bold; }
.search { height: 3; }
.scroll { height: 1fr; overflow: auto; }
/* Improve visibility of selected items (full-line) in SelectionList */
/* Cover multiple Textual versions/states (class-based only) */
SelectionList .selected,
SelectionList .is-selected,
SelectionList .option--selected,
SelectionList .selection-list--option--selected,
SelectionList *.-selected,
SelectionList *.-highlight,
SelectionList .selection-list--option.-selected,
SelectionList .selection-list--option.--selected,
#list-devices .selected,
#list-devices .is-selected,
#list-devices .option--selected,
#list-devices .selection-list--option--selected,
#list-devices *.-selected,
#list-devices *.-highlight,
#list-devices .selection-list--option.-selected,
#list-devices .selection-list--option.--selected,
#list-groups .selected,
#list-groups .is-selected,
#list-groups .option--selected,
#list-groups .selection-list--option--selected,
#list-groups *.-selected,
#list-groups *.-highlight,
#list-groups .selection-list--option.-selected,
#list-groups .selection-list--option.--selected,
#list-sequences .selected,
#list-sequences .is-selected,
#list-sequences .option--selected,
#list-sequences .selection-list--option--selected,
#list-sequences *.-selected,
#list-sequences *.-highlight,
#list-sequences .selection-list--option.-selected,
#list-sequences .selection-list--option.--selected {
    background: #0057d9;
    color: #ffffff;
    text-style: bold;
}
"""
