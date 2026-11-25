"""Synchronous Networka sessions backed by Scrapli 2's native CLI."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from threading import Lock, Timer
from typing import Any

from scrapli import (
    AuthOptions,
    Cli,
    LookupKeyValue,
    ReadCallback,
    SessionOptions,
    TransportBinOptions,
    TransportSsh2Options,
    TransportTelnetOptions,
)
from scrapli.exceptions import (
    EOFException,
    OperationException,
    ScrapliException,
    TransportException,
)
from scrapli.ffi_types import Cancel
from scrapli.transport import Options

from network_toolkit.exceptions import DeviceExecutionError, OperationUnconfirmedError
from network_toolkit.transport.interfaces import CommandResult

logger = logging.getLogger(__name__)
_ROUTEROS_SUFFIX = "+ct511w4098h"
_LEGACY_ROUTEROS_SUFFIX = "+cet511w4098h"
_NS_PER_SECOND = 1_000_000_000
# RouterOS reports a rejected command with one of these at the start of the reply.
_ROUTEROS_ERROR_PREFIXES = (
    "syntax error",
    "bad command name",
    "expected end of command",
    "input does not match any value",
    "failure:",
    "no such item",
)


def _transport_options(params: dict[str, Any]) -> Options:
    backend = (params.get("transport") or "system").lower()
    strict = params.get("auth_strict_key", False)
    ssh_config = params.get("ssh_config_file", True)
    if backend == "system":
        return TransportBinOptions(
            enable_strict_key=strict,
            ssh_config_path=None if ssh_config else os.devnull,
        )
    if backend == "ssh2":
        if ssh_config:
            msg = "ssh2 requires ssh_config_file: false. Use system for OpenSSH configuration."
            raise ValueError(msg)
        return TransportSsh2Options(
            known_hosts_path=str(Path.home() / ".ssh/known_hosts") if strict else None
        )
    if backend == "telnet":
        return TransportTelnetOptions()
    msg = (
        f"Unsupported Scrapli 2 transport {backend!r}. Choose system, ssh2, or telnet."
    )
    raise ValueError(msg)


class ScrapliSyncTransport:
    """Serialize access to each native session, including open and close."""

    def __init__(
        self, driver: Cli, command_timeout_ns: int, *, routeros: bool = False
    ) -> None:
        self._driver = driver
        self._command_timeout_ns = command_timeout_ns
        self._routeros = routeros
        self._force_close = False
        self._lock = Lock()

    @classmethod
    def from_connection_params(cls, params: dict[str, Any]) -> ScrapliSyncTransport:
        platform = params.get("platform")
        routeros = platform == "mikrotik_routeros"
        username = params["auth_username"]
        if routeros:
            # RouterOS can redraw an intermediate prompt with the legacy console mode.
            username = username.removesuffix(_LEGACY_ROUTEROS_SUFFIX)
            if not username.endswith(_ROUTEROS_SUFFIX):
                username += _ROUTEROS_SUFFIX
        open_seconds = min(
            params.get("timeout_socket", 30), params.get("timeout_transport", 30)
        )
        enable_password = params.get("auth_enable_password")
        # Scrapli needs the initial timeout before allocating its native pointer.
        driver = Cli(
            params["host"],
            port=params.get("port"),
            definition_file_or_name=platform,
            auth_options=AuthOptions(
                username=username,
                password=params["auth_password"],
                lookups=[LookupKeyValue("enable", enable_password)]
                if enable_password
                else None,
            ),
            transport_options=_transport_options(params),
            session_options=SessionOptions(
                return_char="\r" if routeros else None,
                operation_timeout_ns=int(open_seconds * _NS_PER_SECOND),
            ),
        )
        if enable_password:
            # libscrapli 0.0.8 logs the resolved enable reply at DEBUG.
            driver.logger.setLevel(logging.WARNING)
        return cls(
            driver,
            int(params.get("timeout_ops", 30) * _NS_PER_SECOND),
            routeros=routeros,
        )

    def open(self) -> None:
        with self._lock:
            try:
                self._driver.open()
                self._force_close = False
            except Exception:
                if self._driver.ptr is not None:
                    try:
                        self._driver.close(force=True)
                    except Exception:
                        logger.debug(
                            "Could not close the partially opened session",
                            exc_info=True,
                        )
                raise

    def close(self) -> None:
        with self._lock:
            if self._driver.ptr is not None:
                self._driver.close(force=self._force_close)

    def send_command(self, command: str) -> CommandResult:
        with self._lock:
            try:
                result = self._driver.send_input(
                    command, operation_timeout_ns=self._command_timeout_ns
                )
            except (ScrapliException, OSError) as exc:
                msg = "Device did not acknowledge the command"
                raise OperationUnconfirmedError(msg, command=command) from exc
        output = result.result
        failed = result.failed
        if self._routeros:
            first, _, remainder = output.partition("\n")
            first = first.rstrip("\r").strip()
            if first == command or re.fullmatch(
                r"\[[^\]\r\n]+\][^>\r\n]*>\s*" + re.escape(command), first
            ):
                output = remainder
            failed = failed or output.lstrip().startswith(_ROUTEROS_ERROR_PREFIXES)
        return CommandResult(result=output, failed=failed)

    def send_interactive(
        self,
        interact_events: list[tuple[str, str, bool]],
        timeout_ops: float,
        *,
        expect_disconnect: bool = False,
    ) -> str:
        if (
            len(interact_events) != 2
            or not interact_events[0][1]
            or interact_events[1][1]
        ):
            msg = "Scrapli 2 expects a command with one exact prompt and one reply"
            raise DeviceExecutionError(msg)
        command, prompt, _ = interact_events[0]
        reply, _, hidden = interact_events[1]
        with self._lock:
            if expect_disconnect:
                if hidden:
                    msg = "A restart confirmation must use a non-secret reply"
                    raise DeviceExecutionError(msg)
                return self._confirm_disconnect(command, prompt, reply, timeout_ops)
            try:
                result = self._driver.send_prompted_input(
                    command,
                    prompt,
                    "",
                    reply,
                    hidden_response=hidden,
                    operation_timeout_ns=int(timeout_ops * _NS_PER_SECOND),
                )
            except (ScrapliException, OSError) as exc:
                msg = "Device did not acknowledge the interactive operation"
                raise OperationUnconfirmedError(msg, command=command) from exc
        if result.failed:
            msg = "Device rejected the interactive operation"
            raise DeviceExecutionError(
                msg, command=command, details={"error": result.result}
            )
        return result.result

    def _confirm_disconnect(
        self, command: str, prompt: str, reply: str, timeout_ops: float
    ) -> str:
        """Send the reply once and distinguish a subsequent EOF from a lost prompt."""
        cancel = Cancel()
        reply_sent = False

        def confirm(driver: Cli, _recent: str, _output: str) -> None:
            nonlocal reply_sent
            if cancel.cancelled:
                msg = "Restart confirmation deadline exceeded"
                raise OperationException(msg)
            driver.write_and_return(reply)
            reply_sent = True

        timeout = Timer(timeout_ops, cancel.cancel)
        timeout.daemon = True
        timeout.start()
        try:
            self._driver.read_with_callbacks(
                [
                    ReadCallback(
                        name="restart confirmation",
                        contains=prompt,
                        search_depth=len(prompt) * 2,
                        once=True,
                        callback=confirm,
                    )
                ],
                initial_input=command,
                cancel=cancel,
                operation_timeout_ns=int(timeout_ops * _NS_PER_SECOND),
            )
        except (ScrapliException, OSError) as exc:
            # The native result API wraps EOF and SSH2 socket loss in OperationException.
            reason = (
                str(exc).partition(":")[0]
                if isinstance(exc, OperationException)
                else ""
            )
            end_of_stream = isinstance(exc, EOFException) or reason == "EOF"
            ssh2_connection_lost = isinstance(
                self._driver.transport_options, TransportSsh2Options
            ) and (isinstance(exc, TransportException) or reason == "Transport")
            if reply_sent and (end_of_stream or ssh2_connection_lost):
                self._force_close = True
                return "Restart confirmation sent and the session ended"
            msg = "Device did not acknowledge the restart confirmation"
            raise OperationUnconfirmedError(msg, command=command) from exc
        finally:
            timeout.cancel()

        msg = "Device did not acknowledge the restart confirmation"
        raise OperationUnconfirmedError(msg, command=command)
