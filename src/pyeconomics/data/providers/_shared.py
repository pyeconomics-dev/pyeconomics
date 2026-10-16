# src/pyeconomics/data/providers/_shared.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Helpers the built-in providers share: reading JSON bodies, numbers and periods.

Every helper raises :class:`~pyeconomics.data.errors.ResponseError` naming the
provider when a source sends something it did not promise, and never repeats
the body (it may echo a key). Nothing here does I/O.

Examples
--------
>>> import datetime as dt
>>> period_end(dt.date(2026, 4, 1), ObservationFrequency.QUARTERLY)
datetime.date(2026, 6, 30)
>>> number("1,234.5", "bea"), number("(NA)", "bea", missing=("(NA)",)) is None
(1234.5, True)

"""

from __future__ import annotations

import calendar
import datetime as dt
import math
import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.rates import percent_to_decimal
from pyeconomics.data.errors import ResponseError
from pyeconomics.data.types import ObservationFrequency

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from pyeconomics.data.transport.base import Response

__all__ = [
    "MONTHS_PER_PERIOD",
    "body_object",
    "dates_note",
    "items",
    "month_end",
    "number",
    "period_end",
    "rate_or_value",
    "text",
]

#: The months in one period of each month-based frequency.
MONTHS_PER_PERIOD: Final = {
    ObservationFrequency.MONTHLY: 1,
    ObservationFrequency.QUARTERLY: 3,
    ObservationFrequency.SEMIANNUAL: 6,
    ObservationFrequency.ANNUAL: 12,
}
_NUMBER: Final = re.compile(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
#: The most dates a note lists before it says how many more there are.
_NOTE_DATES: Final = 12


def month_end(year: int, month: int) -> dt.date:
    """Return the last day of a month."""
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def period_end(start: dt.date, frequency: ObservationFrequency) -> dt.date:
    """Return the last day of the period that starts on ``start``.

    A month-based period (a month, quarter, half-year or year) starting in
    ``start``'s month ends on the last day of its last month; any other
    frequency is dated by its own day, which is returned unchanged.
    """
    step = MONTHS_PER_PERIOD.get(frequency)
    if step is None:
        return start
    index = start.year * 12 + start.month - 1 + step - 1
    return month_end(index // 12, index % 12 + 1)


def body_object(response: Response, provider: str) -> dict[str, Any]:
    """Parse a response body that must be a JSON object."""
    body = response.json(provider=provider)
    if not isinstance(body, dict):
        msg = f"{provider} sent a body that is not a JSON object"
        raise ResponseError(msg, provider=provider)
    return body


def items(value: object, provider: str, what: str) -> list[Any]:
    """Return a JSON array, or fail naming what was expected."""
    if not isinstance(value, list):
        msg = f"{provider} sent no {what}"
        raise ResponseError(msg, provider=provider)
    return value


def text(mapping: object, key: str, provider: str) -> str:
    """Return a non-empty string field of a JSON object."""
    value = mapping.get(key) if isinstance(mapping, dict) else None
    if not isinstance(value, str) or not value.strip():
        msg = f"{provider} sent no {key}"
        raise ResponseError(msg, provider=provider)
    return value.strip()


def number(raw: object, provider: str, *, missing: Iterable[str] = ()) -> float | None:
    """Read a published number: thousands separators allowed; a marker is ``None``.

    ``missing`` lists the source's markers for a value it does not publish,
    such as FRED's ``.`` or BEA's ``(NA)``; an empty string is missing too.
    """
    if isinstance(raw, int | float) and not isinstance(raw, bool):
        value = float(raw)
    else:
        if not isinstance(raw, str):
            msg = f"{provider} sent a value that is neither a number nor text"
            raise ResponseError(msg, provider=provider)
        stripped = raw.strip()
        if not stripped or stripped in set(missing):
            return None
        plain = stripped.replace(",", "")
        if not _NUMBER.fullmatch(plain):
            msg = f"{provider} sent a value that is not a number: {stripped[:16]!r}"
            raise ResponseError(msg, provider=provider)
        value = float(plain)
    if not math.isfinite(value):
        msg = f"{provider} sent a value that is not finite"
        raise ResponseError(msg, provider=provider)
    return value


def rate_or_value(value: float | None, *, percent: bool) -> float | None:
    """Convert a percent to a decimal (ADR-0008 decision 1); keep anything else."""
    if value is None or not percent:
        return value
    return percent_to_decimal(value)


def dates_note(code: str, detail: str, days: Sequence[dt.date]) -> str:
    """Return a note naming the dates it applies to, the first dozen of them."""
    shown = ", ".join(day.isoformat() for day in days[:_NOTE_DATES])
    more = len(days) - _NOTE_DATES
    if more > 0:
        shown += f" and {more} more"
    return f"{code}: {detail} ({shown})"
