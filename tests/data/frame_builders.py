# tests/data/frame_builders.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Builders the data-layer tests share: terms, metadata, frames and vintages.

Every value is synthetic. The ALFRED-style history is hand-built: its dates
and real-time periods follow ALFRED's layout (a first release, then
revisions, each period ending the day before the next begins), and its numbers
are invented for the test.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import replace
from typing import Any

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    CachePolicy,
    ColumnMeta,
    DateConvention,
    LicenceClass,
    LlmUse,
    ObservationFrequency,
    RealtimePeriod,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    TableMeta,
    Terms,
    UnitRecord,
)

TERMS_URL = "https://www.example.org/legal/terms"

TERMS = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url=TERMS_URL,
    checked=dt.date(2026, 10, 14),
    attribution="Source: an example statistical agency.",
    notice="This product uses an example API but is not endorsed by its owner.",
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)

RATE = UnitRecord(text="Percent", kind=UnitKind.RATE)
RETRIEVED = dt.datetime(2026, 10, 14, 13, 30, 5, 123456, tzinfo=dt.UTC)


def series_meta(**changes: Any) -> SeriesMeta:  # noqa: ANN401 - any field
    """Return monthly rate metadata, with ``changes`` applied."""
    meta = SeriesMeta(
        provider="example",
        series_id="EXAMPLE_RATE",
        dataset="example_release",
        title="An example rate",
        unit=RATE,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        source_dating=DateConvention.PERIOD_START,
        terms=TERMS,
        retrieved_at=RETRIEVED,
    )
    return replace(meta, **changes)


def month_ends(count: int, year: int = 2020, month: int = 1) -> tuple[dt.date, ...]:
    """Return ``count`` consecutive month ends from ``year``-``month``."""
    days = []
    for offset in range(count):
        y, m = divmod(year * 12 + month - 1 + offset, 12)
        days.append(dt.date(y, m + 1, calendar.monthrange(y, m + 1)[1]))
    return tuple(days)


def monthly(values: tuple[float | None, ...], **changes: Any) -> Series:  # noqa: ANN401
    """Return a monthly series of ``values`` from January 2020."""
    return Series(month_ends(len(values)), values, series_meta(**changes))


def table_meta(**changes: Any) -> TableMeta:  # noqa: ANN401 - any field
    """Return monthly table metadata, with ``changes`` applied."""
    meta = TableMeta(
        provider="example",
        table_id="EXAMPLE_TABLE",
        dataset="example_release",
        title="An example table",
        frequency=ObservationFrequency.MONTHLY,
        source_dating=DateConvention.PERIOD_END,
        terms=TERMS,
        retrieved_at=RETRIEVED,
    )
    return replace(meta, **changes)


def column(name: str, **changes: Any) -> ColumnMeta:  # noqa: ANN401 - any field
    """Return a rate column named ``name``."""
    meta = ColumnMeta(
        name=name,
        unit=RATE,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        series_id=f"{name}_ID",
        title=f"The {name} column",
    )
    return replace(meta, **changes)


def two_column_table() -> Table:
    """Return a three-month table with a missing value in each column."""
    return Table(
        month_ends(3),
        (column("short"), column("long")),
        ((0.01, None, 0.03), (None, 0.05, 0.06)),
        table_meta(),
    )


# --- an ALFRED-style real-time history ----------------------------------------

Q1, Q2 = dt.date(2008, 3, 31), dt.date(2008, 6, 30)

#: (date, realtime_start, realtime_end, value): Q1 published, then revised
#: twice; Q2 published, then revised once. Each period ends the day before the
#: next one starts, and the latest values are still current.
HISTORY: tuple[tuple[dt.date, dt.date, dt.date | None, float], ...] = (
    (Q1, dt.date(2008, 4, 30), dt.date(2008, 5, 28), 0.006),
    (Q1, dt.date(2008, 5, 29), dt.date(2008, 6, 25), 0.009),
    (Q1, dt.date(2008, 6, 26), None, 0.010),
    (Q2, dt.date(2008, 7, 31), dt.date(2008, 8, 27), 0.019),
    (Q2, dt.date(2008, 8, 28), None, 0.033),
)


def quarterly_meta(**changes: Any) -> SeriesMeta:  # noqa: ANN401 - any field
    """Return quarterly growth metadata from a source that keeps vintages."""
    return series_meta(
        series_id="EXAMPLE_GROWTH",
        title="An example growth rate",
        unit=UnitRecord(text="Percent Change at Annual Rate", kind=UnitKind.RETURN),
        frequency=ObservationFrequency.QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
        terms=TERMS.with_overrides(
            licence=LicenceClass.LIBRARY_ONLY,
            llm_use=LlmUse.FORBIDDEN,
            cache=CachePolicy.FORBIDDEN,
        ),
        **changes,
    )


def history() -> Series:
    """Return :data:`HISTORY` as a real-time series."""
    return Series(
        tuple(row[0] for row in HISTORY),
        tuple(row[3] for row in HISTORY),
        quarterly_meta(),
        tuple(RealtimePeriod(row[1], row[2]) for row in HISTORY),
    )
