"""Unified prompt component for TUI info and yes/no questions.

Provides a single, consistent ModalScreen-based UI for:
- show_info: transient informational notices (optionally auto-dismiss)
- ask_yes_no: simple yes/no questions with keyboard shortcuts

Falls back gracefully (returns False) if Textual is not available.
"""

from __future__ import annotations

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
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            ...

    class _Static:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            ...

    class _Vertical:  # type: ignore
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            ...

        def __enter__(self) -> _Vertical:
            return self

        def __exit__(self, *_: Any) -> bool:
            return False


class _PromptScreen(_ModalScreenBase):  # type: ignore[misc]
    DEFAULT_CSS = (
        "#nw-prompt { width: 70; border: round $surface; padding: 1 2; }\n"
        "#nw-prompt Static.title { content-align: center middle; text-style: bold; }\n"
        "#nw-prompt .buttons { content-align: center middle; height: 3; }\n"
    )

    def __init__(
        self,
        message: str,
        *,
        mode: str = "info",
        on_yes: Callable[[], None] | None = None,
        on_no: Callable[[], None] | None = None,
        on_close: Callable[[], None] | None = None,
    ) -> None:
        super().__init__()  # type: ignore[misc]
        self._message = message
        self._mode = mode
        self._on_yes = on_yes
        self._on_no = on_no
        self._on_close = on_close

    def compose(self) -> Any:
        with _Vertical(id="nw-prompt"):
            yield _Static(self._message, classes="title")
            with _Vertical(classes="buttons"):
                if self._mode == "yesno":
                    yield _Button("Yes [y]", id="btn-yes")
                    yield _Button("No [N]/Esc", id="btn-no")
                else:
                    yield _Button("OK [Enter]", id="btn-ok")

    def on_button_pressed(self, event: Any) -> None:
        bid = getattr(getattr(event, "button", None), "id", "")
        if bid == "btn-yes" and self._on_yes:
            self._on_yes()
        elif bid in {"btn-no", "btn-ok"}:
            if self._on_no and self._mode == "yesno":
                self._on_no()
            elif self._on_close and self._mode != "yesno":
                self._on_close()
        try:
            self.dismiss(None)  # type: ignore[call-arg]
        except Exception:
            pass

    def on_key(self, event: Any) -> None:
        key = str(getattr(event, "key", "")).lower()
        if self._mode == "yesno":
            if key == "y" and self._on_yes:
                self._on_yes()
                try:
                    self.dismiss(None)  # type: ignore[call-arg]
                except Exception:
                    pass
            elif key in {"n", "escape", "enter", "return"}:
                if self._on_no:
                    self._on_no()
                try:
                    self.dismiss(None)  # type: ignore[call-arg]
                except Exception:
                    pass
        elif key in {"enter", "return", "escape", "space"}:
            if self._on_close:
                self._on_close()
            try:
                self.dismiss(None)  # type: ignore[call-arg]
            except Exception:
                pass


class Prompt:
    @staticmethod
    def show_info(app: Any, message: str, *, timeout: float | None = 3.0) -> bool:
        """Show an informational prompt. Returns True if shown, False if not."""
        if _ModalScreenBase is object:
            return False
        try:
            screen = _PromptScreen(message, mode="info")
            app.push_screen(screen)
            if timeout:
                try:
                    app.set_timer(timeout, lambda: app.pop_screen())
                except Exception:
                    pass
            return True
        except Exception:
            return False

    @staticmethod
    async def ask_yes_no(app: Any, message: str, *, default_no: bool = True) -> bool:
        """Ask a yes/no question; return True for Yes, False for No.

        If Textual isn't available, returns not default_no.
        """
        if _ModalScreenBase is object:
            return not default_no
        fut: Any = None
        try:
            import asyncio

            loop = asyncio.get_running_loop()
            fut = loop.create_future()
        except Exception:
            fut = None

        result_box = {"val": not default_no}

        def _yes() -> None:
            result_box["val"] = True
            if fut and not fut.done():  # type: ignore[truthy-bool]
                fut.set_result(True)

        def _no() -> None:
            result_box["val"] = False
            if fut and not fut.done():  # type: ignore[truthy-bool]
                fut.set_result(False)

        try:
            app.push_screen(
                _PromptScreen(message, mode="yesno", on_yes=_yes, on_no=_no)
            )
        except Exception:
            return not default_no

        if fut is None:
            # No event loop available; rely on default
            return result_box["val"]

        try:
            return bool(await fut)
        except Exception:
            return result_box["val"]
