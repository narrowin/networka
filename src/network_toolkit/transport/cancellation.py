"""Cooperative cancellation shared by the reads of one parallel operation."""

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from threading import Event

from scrapli.ffi_types import Cancel


class OperationCancellation:
    """Cancel native reads and wake connection retry delays together."""

    def __init__(self) -> None:
        self.native = Cancel()
        self._event = Event()

    @property
    def cancelled(self) -> bool:
        return self.native.cancelled

    def cancel(self) -> None:
        self.native.cancel()
        self._event.set()

    def wait(self, seconds: float) -> bool:
        return self._event.wait(seconds)


_cancel: ContextVar[OperationCancellation | None] = ContextVar(
    "networka_operation_cancel", default=None
)


def current_cancel() -> OperationCancellation | None:
    """The native cancellation token, if this operation has a cancellation scope."""
    return _cancel.get()


@contextmanager
def cancellable_operation() -> Iterator[OperationCancellation]:
    """Let copied worker contexts share a token without affecting other operations."""
    cancel = OperationCancellation()
    token = _cancel.set(cancel)
    try:
        yield cancel
    finally:
        _cancel.reset(token)
