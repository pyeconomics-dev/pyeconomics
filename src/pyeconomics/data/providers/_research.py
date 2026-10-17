# src/pyeconomics/data/providers/_research.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Pure common conventions for the research sources."""

# ruff: noqa: PLR2004 - source calendar and fixed spreadsheet layout constants

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING

from pyeconomics.core.provenance import RealtimePeriod
from pyeconomics.data.errors import DataError, ResponseError, SeriesNotFoundError
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import Capability, Case, DataProvider, Query
from pyeconomics.data.types import Series, SeriesMeta
from pyeconomics.data.vintage import Vintage, VintageKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.transport.base import Request, Response

Rows = tuple[tuple[object, ...], ...]
Observation = tuple[dt.date, dt.date, float | None]


def single(query: Query, provider: str) -> str:
    """Require one selection; independent vintage calendars must not be aligned."""
    if len(query.series) != 1:
        msg = "fetch each research series separately to preserve its vintage calendar"
        raise DataError(msg, provider=provider)
    return query.series[0]


def number(
    value: object, provider: str, *, percent: bool = False, missing_codes: bool = False
) -> float | None:
    """Read spreadsheet missing markers and convert declared percentages."""
    if value is None or (
        missing_codes
        and isinstance(value, str | int | float)
        and value in {-99, -999, "-99", "-999"}
    ):
        return None
    return s.rate_or_value(
        s.number(value, provider, missing=("#N/A", "NA", "N/A", ".")),
        percent=percent,
    )


def integer(value: object, provider: str) -> int:
    """Read a bounded integral calendar component without coercing arbitrary text."""
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    msg = "source supplied a nonintegral calendar component"
    raise ResponseError(msg, provider=provider)


def day(value: object, provider: str) -> dt.date:
    """Read Excel dates or ISO dates without exposing untrusted cell text."""
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    if isinstance(value, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return dt.date.fromisoformat(value)
    msg = "source supplied an invalid observation or publication date"
    raise ResponseError(msg, provider=provider)


def period(value: object, provider: str) -> dt.date:
    """Read YYYY:Qn, YYYYqN, YYYY:Mn or an annual year, always period-end."""
    text = str(value).strip()
    match = re.fullmatch(r"(\d{4}):?([QqMm])(\d{1,2})", text)
    if match:
        year, kind, index = int(match[1]), match[2].upper(), int(match[3])
        if (kind == "Q" and 1 <= index <= 4) or (kind == "M" and 1 <= index <= 12):
            return s.month_end(year, index * 3 if kind == "Q" else index)
    month = re.fullmatch(r"(\d{4}):(0[1-9]|1[0-2])", text)
    if month:
        return s.month_end(int(month[1]), int(month[2]))
    if re.fullmatch(r"(?:CY|FY)?\d{4}", text):
        return dt.date(
            int(text[-4:]),
            9 if text.startswith("FY") else 12,
            30 if text.startswith("FY") else 31,
        )
    msg = "source supplied an invalid period label"
    raise ResponseError(msg, provider=provider)


def frame(rows: Sequence[Observation], meta: SeriesMeta, query: Query) -> Series:
    """Close revision intervals per observation before applying the selector."""
    grouped: dict[dt.date, dict[dt.date, float | None]] = {}
    for observed, published, value in rows:
        if (query.start is None or observed >= query.start) and (
            query.end is None or observed <= query.end
        ):
            revisions = grouped.setdefault(observed, {})
            if published in revisions:
                msg = "source repeats an observation at the same vintage"
                raise ResponseError(msg, provider=meta.provider)
            revisions[published] = value
    if not grouped:
        raise SeriesNotFoundError(meta.provider, meta.series_id)
    index, values, realtime = [], [], []
    selector = query.vintage_selector
    for observed, revisions in sorted(grouped.items()):
        dates = sorted(revisions)
        selected = selected_dates(dates, selector)
        for published in selected:
            i = dates.index(published)
            index.append(observed)
            values.append(revisions[published])
            realtime.append(
                RealtimePeriod(
                    realtime_start=published,
                    realtime_end=dates[i + 1] - dt.timedelta(days=1)
                    if i + 1 < len(dates)
                    else None,
                )
            )
    count = query.max_observations
    return Series(
        tuple(index[-count:]), tuple(values[-count:]), meta, tuple(realtime[-count:])
    )


def selected_dates(dates: list[dt.date], selector: Vintage) -> list[dt.date]:
    """Choose before applying the frame bound, keeping early as-of rows visible."""
    if selector.on is not None:
        available = [day for day in dates if day <= selector.on]
        return available[-1:]
    if selector.kind is VintageKind.ALL:
        return dates
    if selector.kind is VintageKind.FIRST_RELEASE:
        return dates[:1]
    return dates[-1:]


class VintageResearch(DataProvider):
    """Vintages are read from the same source records as observations."""

    def build_vintages(self, series_id: str) -> Sequence[Request]:
        """Fetch the source's complete publication history."""
        return self.build_requests(Query(series=(series_id,), vintage="all"))

    def parse_vintages(
        self, responses: Sequence[Response], series_id: str
    ) -> Sequence[dt.date]:
        """Return distinct publication dates, never observation dates."""
        result = self.parse(responses, Query(series=(series_id,), vintage="all"))
        if result.realtime is None:
            msg = "vintage source returned no publication dates"
            raise ResponseError(msg, provider=self.info.id)
        return sorted({p.realtime_start for p in result.realtime})


def cases(series_id: str, *, vintages: bool = False) -> tuple[Case, ...]:
    """Cases for every vintage selector, including a real empty-date request."""
    from pyeconomics.data.errors import RateLimitError  # noqa: PLC0415

    sample = Query(series=(series_id,), max_observations=3)
    base = (
        Case(name="fetch_ok", operation=Capability.FETCH, argument=sample),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=sample.model_copy(
                update={"start": dt.date(1700, 1, 1), "end": dt.date(1700, 1, 2)}
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=sample,
            expect=RateLimitError,
            simulate=429,
        ),
    )
    if not vintages:
        return base
    return (
        *base,
        Case(name="vintages_ok", operation=Capability.VINTAGES, argument=series_id),
        Case(
            name="fetch_all",
            operation=Capability.FETCH,
            argument=sample.model_copy(update={"vintage": "all"}),
        ),
        Case(
            name="fetch_first",
            operation=Capability.FETCH,
            argument=sample.model_copy(update={"vintage": "first_release"}),
        ),
    )
