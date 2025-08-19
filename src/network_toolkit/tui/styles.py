"""Application styling for the TUI."""

APP_CSS = """
/* Main layout */
#main-layout {
    layout: vertical;
    height: 100%;
}

#top-section {
    layout: horizontal;
    height: 1fr;
    border: round $surface;
}

/* Panels */
.panel {
    border: round $surface;
    padding: 1;
    margin: 1;
}

.panel-title {
    text-align: center;
    text-style: bold;
    color: $secondary;
    height: 3;
    content-align: center middle;
}

#targets-panel {
    width: 1fr;
}

#actions-panel {
    width: 1fr;
}

/* Selection lists */
SelectionList {
    height: 1fr;
}

SelectionList > .option--selected {
    background: $primary;
    color: $text;
    text-style: bold;
}

/* Status bar */
.status-bar {
    height: 3;
    background: $surface;
    border: round $primary;
}

#status-text {
    content-align: center middle;
    text-style: bold;
}

/* Output panel */
#output-panel {
    height: auto;
    max-height: 20;
}

#output-panel.hidden {
    display: none;
}

.log {
    height: 1fr;
    border: round $surface;
    scrollbar-gutter: stable;
}

/* Buttons */
#run-button {
    margin: 1 0;
    width: 100%;
}

/* Inputs */
Input {
    margin-bottom: 1;
}

/* Tabs */
TabbedContent {
    height: 1fr;
}

TabPane {
    padding: 1;
}

/* Theme variants */
.status-bar.-running {
    background: $warning;
}

.status-bar.-success {
    background: $success;
}

.status-bar.-error {
    background: $error;
}
"""
