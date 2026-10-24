# src/pyeconomics/server/logs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What a server logs, and where: single lines, never a traceback.

The app logs on two loggers:

- ``pyeconomics.server``: one record per problem, holding its slug, status,
  error type name and scrubbed detail
  (:func:`~pyeconomics.surfaces.problems.record`), never a raw message;
- ``pyeconomics.server.access``: one record per request, holding the method,
  the route's template (``/v1/series/{target}``, never the path or the query a
  caller sent), the status and the time taken.

:func:`configure` sends pyeconomics' records to a stream as single lines with
no traceback, and gives the root logger a handler that drops what other
libraries log, whose messages can name hosts, paths and request lines.
``pyeconomics serve`` and every worker process call it once, at start.

Examples
--------
>>> import io, logging
>>> stream = io.StringIO()
>>> handler = configure(stream)
>>> logging.getLogger(ACCESS_LOGGER).info("GET %s %d", "/healthz", 200)
>>> stream.getvalue().splitlines()
['INFO pyeconomics.server.access: GET /healthz 200']
>>> release(handler)
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from _typeshed import SupportsWrite

__all__ = ["ACCESS_LOGGER", "FORMAT", "LOGGER", "NoTraceback", "configure", "release"]

#: The logger of problems and of the server's own events.
LOGGER: Final = "pyeconomics.server"
#: The logger of the one record per request.
ACCESS_LOGGER: Final = "pyeconomics.server.access"
#: The layout of a line.
FORMAT: Final = "%(levelname)s %(name)s: %(message)s"

_PACKAGE: Final = "pyeconomics"


class _Silence(logging.NullHandler):
    """The root handler that :func:`configure` adds and :func:`release` drops."""


class NoTraceback(logging.Filter):
    """Drop a record's traceback and stack, which name files and values."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Keep the record, without ``exc_info``, ``exc_text`` or ``stack_info``."""
        record.exc_info = None
        record.exc_text = None
        record.stack_info = None
        return True


def configure(stream: SupportsWrite[str], level: int = logging.INFO) -> logging.Handler:
    """Send pyeconomics' records at ``level`` and up to ``stream``; drop the rest.

    Returns the handler, for :func:`release`.
    """
    handler = logging.StreamHandler(stream)
    handler.setFormatter(logging.Formatter(FORMAT))
    handler.addFilter(NoTraceback())
    package = logging.getLogger(_PACKAGE)
    package.addHandler(handler)
    package.setLevel(level)
    package.propagate = False
    root = logging.getLogger()
    if not any(isinstance(item, _Silence) for item in root.handlers):
        # Without a handler the root logger would print other libraries'
        # warnings through logging.lastResort.
        root.addHandler(_Silence())
    return handler


def release(handler: logging.Handler) -> None:
    """Undo :func:`configure`: remove the handler and let records propagate."""
    package = logging.getLogger(_PACKAGE)
    package.removeHandler(handler)
    package.setLevel(logging.NOTSET)
    package.propagate = True
    root = logging.getLogger()
    for item in [item for item in root.handlers if isinstance(item, _Silence)]:
        root.removeHandler(item)
