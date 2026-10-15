# tests/data/leakcheck.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The canary harness: does a key reach any sink? (ADR-0011 decision 13).

:func:`canary` makes a random 40-character key, registered as a
:class:`~pyeconomics.data.Secret` for a toy provider. A :class:`LeakCheck`
collects named sinks and :meth:`LeakCheck.assert_clean` fails with the names
of the sinks the canary reached, never the canary itself:

- ``log:<logger>``: every record, at DEBUG, on the root, ``pyeconomics`` and
  ``urllib3`` loggers, formatted with its traceback (:meth:`LeakCheck.logs`);
  :func:`log_urllib3_request` writes the lines urllib3 writes for a request,
  without the network;
- ``exception:<type>``: an exception's ``str``, ``repr`` and
  ``traceback.format_exception``, its context and cause included
  (:meth:`LeakCheck.exception`);
- ``warning:<category>``: every warning, as Python would show it
  (:meth:`LeakCheck.warnings`);
- ``manifest`` and ``result:<export>``: a result's manifest in canonical JSON
  and its ``to_dict``, ``to_json``, ``to_pandas`` and ``to_parquet`` bytes
  (:meth:`LeakCheck.result`).

Step 4 adds the transport: :meth:`LeakCheck.run` runs a call collecting its logs
and warnings, and either its result or its exception (tests/providers/
test_canary_transport.py). Steps 5 and 12 add their sinks with
:meth:`LeakCheck.add`: the cache file and bound manifests.

Never assert ``canary not in text``: pytest would print both sides. Collect
names and compare the list with ``[]``, as :meth:`LeakCheck.found_in` does.
"""

from __future__ import annotations

import contextlib
import importlib
import logging
import secrets
import traceback
import warnings
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, Protocol, TypeVar
from urllib.parse import quote, quote_plus

from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import Secret

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Mapping
    from pathlib import Path

    from pyeconomics.core.results import Result

__all__ = [
    "CANARY_LENGTH",
    "LOGGERS",
    "TOY_PROVIDER",
    "URLLIB3_CONNECTION_LINE",
    "URLLIB3_REQUEST_LINE",
    "URLLIB3_RETRY_LINE",
    "Canary",
    "Contact",
    "LeakCheck",
    "Needles",
    "canary",
    "contact_canary",
    "log_urllib3_request",
]

#: The toy provider canaries belong to.
TOY_PROVIDER: Final = "leakcheck_toy"
#: A canary's length: 20 random bytes as hex.
CANARY_LENGTH: Final = 40
#: The loggers whose records the harness collects; the root is "".
LOGGERS: Final = ("", "pyeconomics", "urllib3")

# urllib3 2.x's own DEBUG and WARNING lines (urllib3/connectionpool.py,
# HTTPConnectionPool._new_conn, _make_request and urlopen). The request line
# carries the path and query string, which is how a key in a query leaks.
URLLIB3_CONNECTION_LINE: Final = "Starting new HTTPS connection (%d): %s:%s"
URLLIB3_REQUEST_LINE: Final = '%s://%s:%s "%s %s %s" %s %s'
URLLIB3_RETRY_LINE: Final = "Retrying (%r) after connection broken by '%r': %s"


def _encoded(value: str) -> tuple[str, ...]:
    """A value and the forms URL encoding gives it, without repeats."""
    return tuple(dict.fromkeys((value, quote(value, safe=""), quote_plus(value))))


class Needles(Protocol):
    """Anything a LeakCheck searches for: the texts that must not leak."""

    def needles(self) -> tuple[str, ...]:
        """Return the texts to search every sink for."""
        ...


@dataclass(frozen=True)
class Canary:
    """A random key, registered for a toy provider.

    ``value`` is the key in plain text, for planting in a sink; its ``repr``
    never shows it.
    """

    held: Secret
    value: str = field(repr=False)

    @property
    def provider(self) -> str:
        """The toy provider the key belongs to."""
        return self.held.provider

    def needles(self) -> tuple[str, ...]:
        """The key and the forms URL encoding gives it."""
        return _encoded(self.value)


@dataclass(frozen=True)
class Contact:
    """A random SEC contact: personal data that must reach no sink either."""

    value: str = field(repr=False)

    def needles(self) -> tuple[str, ...]:
        """The contact and the forms URL encoding gives it."""
        return _encoded(self.value)


def contact_canary() -> Contact:
    """Make a random contact in the form SEC EDGAR asks for: a name and an email."""
    return Contact(f"pyeconomics canary {secrets.token_hex(8)}@example.org")


_T = TypeVar("_T")


def canary(provider: str = TOY_PROVIDER, *, value: str | None = None) -> Canary:
    """Make a random 40-character key and register it as a Secret.

    ``value`` replaces the random key, for a test that needs one with
    characters URL encoding changes; build it from ``secrets`` too.
    """
    planted = secrets.token_hex(CANARY_LENGTH // 2) if value is None else value
    return Canary(held=Secret(provider, planted), value=planted)


class _SinkHandler(logging.Handler):
    """Formats every record it sees, once, into a sink named after its logger."""

    def __init__(self, check: LeakCheck) -> None:
        super().__init__(level=logging.DEBUG)
        self.check = check
        self.seen: set[int] = set()
        self.setFormatter(
            logging.Formatter("%(name)s %(levelname)s %(message)s", validate=True)
        )

    def emit(self, record: logging.LogRecord) -> None:
        if id(record) in self.seen:
            return
        self.seen.add(id(record))
        self.check.add(f"log:{record.name or 'root'}", self.format(record))


@dataclass
class LeakCheck:
    """Named sinks, searched for a canary's needles."""

    canary: Needles
    sinks: dict[str, list[str]] = field(default_factory=dict)

    def add(self, sink: str, payload: str | bytes) -> None:
        """Record what reached a sink; bytes are read as UTF-8."""
        text = (
            payload.decode("utf-8", "replace")
            if isinstance(payload, bytes)
            else payload
        )
        self.sinks.setdefault(sink, []).append(text)

    def found_in(self, texts: Mapping[str, Iterable[str]]) -> list[str]:
        """Return the names, sorted, of the texts that hold a needle."""
        needles = self.canary.needles()
        return sorted(
            name
            for name, values in texts.items()
            if any(needle in text for text in values for needle in needles)
        )

    def leaks(self) -> list[str]:
        """Return the names of the sinks the canary reached."""
        return self.found_in(self.sinks)

    def assert_clean(self) -> None:
        """Fail with the names of the sinks the canary reached, never the canary.

        A check that collected nothing fails too: it would prove nothing.
        """
        if not self.sinks:
            msg = "the leak check collected no sink"
            raise AssertionError(msg)
        leaked = self.leaks()
        if leaked:
            msg = f"the canary reached {len(leaked)} sink(s): {', '.join(leaked)}"
            raise AssertionError(msg)

    @contextlib.contextmanager
    def logs(self, *names: str) -> Generator[None]:
        """Collect every record at DEBUG on :data:`LOGGERS` and ``names``."""
        handler = _SinkHandler(self)
        loggers = [logging.getLogger(name or None) for name in (*LOGGERS, *names)]
        levels = [logger.level for logger in loggers]
        for logger in loggers:
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
        try:
            yield
        finally:
            for logger, level in zip(loggers, levels, strict=True):
                logger.removeHandler(handler)
                logger.setLevel(level)

    @contextlib.contextmanager
    def warnings(self) -> Generator[None]:
        """Collect every warning raised in the body, as Python would show it."""
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            yield
        for warning in caught:
            shown = warnings.formatwarning(
                warning.message,
                warning.category,
                warning.filename,
                warning.lineno,
                warning.line,
            )
            self.add(f"warning:{warning.category.__name__}", shown)
            self.add(f"warning:{warning.category.__name__}", repr(warning.message))

    def exception(self, error: BaseException) -> None:
        """Collect an exception: its text, repr and formatted traceback."""
        sink = f"exception:{type(error).__name__}"
        self.add(sink, str(error))
        self.add(sink, repr(error))
        self.add(sink, "".join(traceback.format_exception(error)))

    def run(self, call: Callable[[], _T]) -> _T | None:
        """Run a call, collecting its logs and warnings and what it returns or raises.

        A returned value is collected as its ``repr`` and, when it has one, its
        canonical JSON; a raised exception is collected whole (:meth:`exception`)
        and the call returns ``None``.
        """
        outcome: _T | None = None
        with self.logs(), self.warnings():
            try:
                outcome = call()
            except Exception as error:  # noqa: BLE001 - every failure is a sink to search
                self.exception(error)
                return None
        self.add("result", repr(outcome))
        canonical = getattr(outcome, "canonical_json", None)
        if callable(canonical):
            self.add("result:canonical_json", canonical())
        return outcome

    def result(self, result: Result[Any, Any], directory: Path) -> None:
        """Collect a result's manifest and every export a user can write."""
        self.add("manifest", canonical_json(result.manifest.to_dict()))
        self.add("result:to_dict", repr(result.to_dict()))
        self.add("result:to_json", result.to_json())
        frame = result.to_pandas()
        self.add("result:to_pandas", frame.to_csv())
        self.add("result:to_pandas", repr(frame))
        path = directory / "result.parquet"
        result.to_parquet(path)
        self.add("result:to_parquet", path.read_bytes())
        # The test group installs pyarrow; a missing one fails, never skips.
        pq = importlib.import_module("pyarrow.parquet")

        table = pq.read_table(path)
        self.add("result:to_parquet", repr(table.to_pylist()))
        self.add("result:to_parquet", repr(table.schema.metadata))


def log_urllib3_request(url: str, *, host: str = "api.example.org") -> None:
    """Write the DEBUG and WARNING lines urllib3 writes for one request.

    ``url`` is the request target urllib3 logs: a path and query string.
    """
    logger = logging.getLogger("urllib3.connectionpool")
    logger.debug(URLLIB3_CONNECTION_LINE, 1, host, 443)
    logger.debug(
        URLLIB3_REQUEST_LINE, "https", host, 443, "GET", url, "HTTP/1.1", 200, 512
    )
    logger.warning(URLLIB3_RETRY_LINE, "Retry(total=4)", "ProtocolError()", url)
