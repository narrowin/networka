from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

from network_toolkit.tui.output_manager import OutputPanelManager


def test_output_panel_reset_clears_device_panes_and_buffers() -> None:
    """Reset removes per-device panes and buffers while retaining the All tab."""
    all_pane = SimpleNamespace(id="output-tab-all")
    device_pane = SimpleNamespace(id="output-tab-dev1")
    tabs = SimpleNamespace(children=[all_pane, device_pane], active=device_pane.id)
    tabs.remove = tabs.children.remove
    output_log = Mock()
    app = SimpleNamespace(
        query_one={"#output-log": output_log, "#output-tabs": tabs}.__getitem__,
        _output_lines=["stale output"],
        _output_device_logs={"dev1": Mock()},
        _output_device_lines={"dev1": ["stale output"]},
        _output_device_panes={"dev1": device_pane},
    )

    OutputPanelManager(app, compat=None).reset()

    output_log.clear.assert_called_once_with()
    assert tabs.children == [all_pane]
    assert tabs.active == all_pane.id
    assert app._output_lines == []
    assert app._output_device_logs == {}
    assert app._output_device_lines == {}
    assert app._output_device_panes == {}
