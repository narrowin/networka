"""Small reusable modal dialogs for the TUI.

These utilities import Textual lazily and return False when a dialog cannot be
shown (e.g., Textual not installed). Callers should provide a fallback.
"""

from __future__ import annotations

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportGeneralTypeIssues=false
from collections.abc import Callable
from typing import Any

try:  # Optional at import time; provide stubs if unavailable
    from textual.containers import Vertical as _Vertical  # type: ignore
    from textual.screen import ModalScreen as _ModalScreenBase  # type: ignore
    from textual.widgets import Button as _Button  # type: ignore
    from textual.widgets import Static as _Static
except Exception:  # pragma: no cover - textual not installed
    _ModalScreenBase = object  # type: ignore

    class _Button:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    class _Static:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    class _Vertical:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None: ...

        def __enter__(self) -> _Vertical:
            return self

        def __exit__(self, *_: Any) -> bool:
            return False


class _ConfirmDialog(_ModalScreenBase):  # type: ignore[misc]
    DEFAULT_CSS = (
        "#nw-dialog { width: 70; border: round $surface; padding: 1 2; }\n"
        "#nw-dialog Static.title { content-align: center middle; text-style: bold; }\n"
        "#nw-dialog .buttons { content-align: center middle; height: 3; }\n"
    )

    def __init__(
        self, message: str, on_yes: Callable[[], None], on_no: Callable[[], None]
    ) -> None:
        super().__init__()  # type: ignore[misc]
        self._message = message
        self._on_yes = on_yes
        self._on_no = on_no

    def compose(self) -> Any:
        with _Vertical(id="nw-dialog"):
            yield _Static(self._message, classes="title")
            with _Vertical(classes="buttons"):
                yield _Button("Yes [y]", id="btn-yes")
                yield _Button("No [N]/Esc", id="btn-no")

    def on_button_pressed(self, event: Any) -> None:
        bid = getattr(getattr(event, "button", None), "id", "")
        if bid == "btn-yes":
            self._on_yes()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif bid == "btn-no":
            self._on_no()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass

    def on_key(self, event: Any) -> None:
        key = str(getattr(event, "key", "")).lower()
        if key in {"y"}:
            self._on_yes()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif key in {"n", "escape", "enter", "return"}:
            self._on_no()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass


class _CancelModeDialog(_ModalScreenBase):  # type: ignore[misc]
    DEFAULT_CSS = (
        "#nw-dialog { width: 70; border: round $surface; padding: 1 2; }\n"
        "#nw-dialog Static.title { content-align: center middle; text-style: bold; }\n"
        "#nw-dialog .buttons { content-align: center middle; height: 3; }\n"
    )

    def __init__(
        self,
        on_soft: Callable[[], None],
        on_hard: Callable[[], None],
        on_abort: Callable[[], None],
    ) -> None:
        super().__init__()  # type: ignore[misc]
        self._on_soft = on_soft
        self._on_hard = on_hard
        self._on_abort = on_abort

    def compose(self) -> Any:
        with _Vertical(id="nw-dialog"):
            yield _Static(
                "Cancel type? Soft [s] (recommended) or Hard [h]. Hard will close sessions immediately and may leave devices in a partial state.",
                classes="title",
            )
            with _Vertical(classes="buttons"):
                yield _Button("Soft cancel [s]", id="btn-soft")
                yield _Button("Hard cancel [h] (disconnect sessions)", id="btn-hard")
                yield _Button("Keep running [N]/Esc", id="btn-no")

    def on_button_pressed(self, event: Any) -> None:
        bid = getattr(getattr(event, "button", None), "id", "")
        if bid == "btn-soft":
            self._on_soft()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif bid == "btn-hard":
            self._on_hard()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif bid == "btn-no":
            self._on_abort()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass

    def on_key(self, event: Any) -> None:
        key = str(getattr(event, "key", "")).lower()
        if key in {"s", "enter", "return"}:
            self._on_soft()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif key == "h":
            self._on_hard()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass
        elif key in {"n", "escape"}:
            self._on_abort()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass


def show_confirm_dialog(
    app: Any,
    message: str,
    *,
    on_yes: Callable[[], None],
    on_no: Callable[[], None],
) -> bool:
    """Show a simple Yes/No modal confirmation dialog.

    Returns True if a dialog was shown; False if Textual isn't available.
    """
    # If ModalScreen is not available, bail out so caller can fallback
    if _ModalScreenBase is object:
        return False
    try:
        app.push_screen(_ConfirmDialog(message, on_yes, on_no))
        return True
    except Exception:
        return False


def show_cancel_mode_dialog(
    app: Any,
    *,
    on_soft: Callable[[], None],
    on_hard: Callable[[], None],
    on_abort: Callable[[], None],
) -> bool:
    if _ModalScreenBase is object:
        return False
    try:
        app.push_screen(_CancelModeDialog(on_soft, on_hard, on_abort))
        return True
    except Exception:
        return False
