# src/pyeconomics/surfaces/series.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The options a series request takes, the same on every surface.

The REST API's ``GET /v1/series/{target}`` reads them from its query, and MCP's
``get_series`` from its arguments; both hand them on as text, and
:func:`series_arguments` turns that text into
:func:`pyeconomics.data.get`'s keyword arguments, so an option added here
reaches the data layer from each surface by the same path. The command line's
``data get`` declares the same options as its own (``--transform``), and the
parity suite holds the four surfaces' answers equal (tests/parity/).

Nothing here loads the data layer: a date is read with the core's own parser,
and a transform is checked by :func:`pyeconomics.data.get` itself.

Examples
--------
>>> series_arguments({"start": "2024-01-01", "transform": "yoy"})
{'start': datetime.date(2024, 1, 1), 'transform': 'yoy'}
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Final, TypedDict

from pyeconomics.core import _fields as f

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

__all__ = ["DATE_OPTIONS", "SERIES_OPTIONS", "SeriesArguments", "series_arguments"]

#: The options of a series request: ``data.get``'s, as text.
SERIES_OPTIONS: Final = ("start", "end", "as_of", "vintage", "provider", "transform")
#: The options that hold a date (``YYYY-MM-DD``).
DATE_OPTIONS: Final = frozenset({"start", "end", "as_of"})


class SeriesArguments(TypedDict, total=False):
    """The keyword arguments of :func:`pyeconomics.data.get` a request may set."""

    start: dt.date
    end: dt.date
    as_of: dt.date
    vintage: str
    provider: str
    transform: str


def series_arguments(options: Mapping[str, str]) -> SeriesArguments:
    """Return ``data.get``'s keyword arguments for a request's text options.

    An option the request did not send is left out; a name that is not one of
    :data:`SERIES_OPTIONS` is ignored (each surface refuses it first).

    Raises
    ------
    InputError
        If a date option is not an ISO date.
    """
    arguments = SeriesArguments()
    if (start := options.get("start")) is not None:
        arguments["start"] = f.parse_day(start, "start")
    if (end := options.get("end")) is not None:
        arguments["end"] = f.parse_day(end, "end")
    if (as_of := options.get("as_of")) is not None:
        arguments["as_of"] = f.parse_day(as_of, "as_of")
    if (vintage := options.get("vintage")) is not None:
        arguments["vintage"] = vintage
    if (provider := options.get("provider")) is not None:
        arguments["provider"] = provider
    if (transform := options.get("transform")) is not None:
        arguments["transform"] = transform
    return arguments
