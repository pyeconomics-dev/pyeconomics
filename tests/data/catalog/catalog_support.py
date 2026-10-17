# tests/data/catalog/catalog_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Builders the catalog tests share: synthetic series on regular dates.

Every number is invented. The helpers build period-end dates for the frequencies
the transforms handle, and wrap values in a :class:`~pyeconomics.data.Series`
with the metadata a test needs to vary.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    CachePolicy,
    DateConvention,
    LicenceClass,
    LlmUse,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    Terms,
    UnitRecord,
    Weekday,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

HOSTED_TERMS = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.example.org/legal/terms",
    checked=dt.date(2026, 10, 15),
    attribution="Source: an example statistical agency.",
    notice="This product is not endorsed by the example agency.",
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
LIBRARY_TERMS = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://www.example.org/legal/library",
    checked=dt.date(2026, 9, 1),
    attribution="Source: an example library-only aggregator.",
    llm_use=LlmUse.FORBIDDEN,
    cache=CachePolicy.FORBIDDEN,
)

_MONTHS = {
    ObservationFrequency.MONTHLY: 1,
    ObservationFrequency.QUARTERLY: 3,
    ObservationFrequency.SEMIANNUAL: 6,
    ObservationFrequency.ANNUAL: 12,
}


def month_end(year: int, month: int) -> dt.date:
    """Return the last day of a month."""
    return dt.date(year, month, calendar.monthrange(year, month)[1])


def period_ends(
    frequency: ObservationFrequency,
    first: tuple[int, int],
    count: int,
    year_end: int = 12,
) -> tuple[dt.date, ...]:
    """Return ``count`` consecutive period-end dates at a month-based frequency.

    ``first`` is the (year, month) of the first period's last month.
    """
    step = _MONTHS[frequency]
    year, month = first
    assert (month - year_end) % step == 0, "first is not a period end"
    out: list[dt.date] = []
    line = year * 12 + month - 1
    for _ in range(count):
        y, m = divmod(line, 12)
        out.append(month_end(y, m + 1))
        line += step
    return tuple(out)


def days(start: dt.date, count: int) -> tuple[dt.date, ...]:
    """Return ``count`` consecutive calendar days from ``start``."""
    return tuple(start + dt.timedelta(days=i) for i in range(count))


def meta(
    frequency: ObservationFrequency = ObservationFrequency.MONTHLY,
    **changes: Any,
) -> SeriesMeta:
    """Return index-level metadata at ``frequency``, with ``changes`` applied."""
    base = SeriesMeta(
        provider="demo",
        series_id="X",
        title="An example series",
        unit=UnitRecord(text="Index", kind=UnitKind.INDEX_LEVEL),
        frequency=frequency,
        week_ends_on=Weekday.FRIDAY
        if frequency in {ObservationFrequency.WEEKLY, ObservationFrequency.BIWEEKLY}
        else None,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        source_dating=DateConvention.PERIOD_END,
        terms=HOSTED_TERMS,
    )
    return replace(base, **changes)


def series(
    frequency: ObservationFrequency,
    index: Sequence[dt.date],
    values: Iterable[float | None],
    *,
    realtime: Sequence[RealtimePeriod] | None = None,
    **changes: Any,
) -> Series:
    """Build a series at ``frequency`` on ``index`` with ``values``."""
    return Series(
        tuple(index),
        tuple(values),
        meta(frequency, **changes),
        None if realtime is None else tuple(realtime),
    )


def monthly(
    values: Iterable[float | None],
    first: tuple[int, int] = (2024, 1),
    **changes: Any,
) -> Series:
    """Build a monthly series from ``values``, starting at ``first``."""
    items = list(values)
    return series(
        ObservationFrequency.MONTHLY,
        period_ends(ObservationFrequency.MONTHLY, first, len(items)),
        items,
        **changes,
    )


def quarterly(
    values: Iterable[float | None],
    first: tuple[int, int] = (2024, 3),
    **changes: Any,
) -> Series:
    """Build a quarterly series from ``values``, starting at ``first``."""
    items = list(values)
    return series(
        ObservationFrequency.QUARTERLY,
        period_ends(ObservationFrequency.QUARTERLY, first, len(items)),
        items,
        **changes,
    )


def as_series(frame: Series | Table) -> Series:
    """Return a resolved frame known to be a series, for a typed test."""
    assert isinstance(frame, Series)
    return frame


def as_table(frame: Series | Table) -> Table:
    """Return a resolved frame known to be a table, for a typed test."""
    assert isinstance(frame, Table)
    return frame
