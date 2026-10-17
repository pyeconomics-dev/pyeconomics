# src/pyeconomics/data/providers/_finance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Pure conventions shared by the research-finance file providers."""

from __future__ import annotations

import csv
import datetime as dt
import re
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
)
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Capability,
    Case,
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.types import (
    ColumnMeta,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Table,
    TableMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.data.transport.base import Response

RATE = UnitRecord(text="Return", kind=UnitKind.RETURN)
Rows = dict[dt.date, dict[str, float | None]]
MAX_CSV_ROWS = 1_000_000
MAX_CSV_COLUMNS = 1000
MAX_CSV_CELLS = 5_000_000


def info(  # noqa: PLR0913, PLR0917 - complete source metadata
    provider: str,
    name: str,
    homepage: str,
    terms_url: str,
    attribution: str,
    notice: str | None,
    hosts: tuple[str, ...],
    *,
    hosted: bool = False,
) -> ProviderInfo:
    """Declare conservative research-only terms unless expressly permitted."""
    return ProviderInfo(
        id=provider,
        name=name,
        homepage=homepage,
        hosts=hosts,
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE if hosted else LicenceClass.LIBRARY_ONLY,
            terms_url=terms_url,
            checked=dt.date(2026, 10, 17),
            attribution=attribution,
            notice=notice,
            llm_use=LlmUse.UNCLEAR,
            cache=CachePolicy.ALLOWED,
        ),
        capabilities=(Capability.FETCH, Capability.BULK),
        rate_limits=(RateLimit(requests=1, per="second"),),
        max_response_bytes=96 * 1024 * 1024,
        ttl_seconds=86400,
    )


def single(query: Query, provider: str) -> str:
    """Require a single dataset whose native frequency is kept intact."""
    if len(query.series) != 1:
        msg = "fetch each finance dataset separately"
        raise DataError(msg, provider=provider)
    return query.series[0]


def cases(*datasets: str) -> tuple[Case, ...]:
    """Exercise every declared file layout and actual empty-date selection."""
    first = Query(series=(datasets[0],), max_observations=3)
    return (
        *(
            Case(
                name=f"fetch_{i}",
                operation=Capability.FETCH,
                argument=Query(series=(dataset,), max_observations=3),
            )
            for i, dataset in enumerate(datasets)
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=first.model_copy(
                update={"start": dt.date(1700, 1, 1), "end": dt.date(1700, 1, 2)}
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=first,
            expect=RateLimitError,
            simulate=429,
        ),
    )


def table(  # noqa: PLR0913, PLR0917 - frame, query and source metadata
    rows: Rows,
    units: Mapping[str, UnitRecord],
    query: Query,
    source: ProviderInfo,
    response: Response,
    frequency: ObservationFrequency,
    *,
    notes: tuple[str, ...] = (),
) -> Table:
    """Filter dates before the row bound; never fill gaps or coerce units."""
    index = tuple(
        sorted(
            d
            for d in rows
            if (query.start is None or d >= query.start)
            and (query.end is None or d <= query.end)
        )
    )[-query.max_observations :]
    if not index or not units:
        raise SeriesNotFoundError(source.id, query.series[0])
    names = tuple(units)
    return Table(
        index,
        tuple(
            ColumnMeta(
                name=n,
                unit=units[n],
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            )
            for n in names
        ),
        tuple(tuple(rows[d].get(n) for d in index) for n in names),
        TableMeta(
            provider=source.id,
            table_id=query.series[0],
            title=query.series[0],
            frequency=frequency,
            source_dating=DateConvention.PERIOD_END,
            terms=source.terms,
            retrieved_at=response.retrieved_at,
            notes=notes,
        ),
    )


def csv_rows(body: bytes) -> list[list[str]]:
    """Read UTF-8 CSV with row, column and cell bounds, including a source BOM."""
    rows: list[list[str]] = []
    cells = 0
    text = body.decode("utf-8-sig")
    lines = (
        match.group()
        for match in re.finditer(r"[^\r\n]*(?:\r\n|[\r\n]|$)", text)
        if match.start() != match.end()
    )
    for row in csv.reader(lines):
        cells += len(row)
        if (
            len(rows) >= MAX_CSV_ROWS
            or len(row) > MAX_CSV_COLUMNS
            or cells > MAX_CSV_CELLS
        ):
            msg = "finance CSV exceeds its row, column or cell bound"
            raise ResponseError(msg, provider="finance")
        rows.append(row)
    return rows


def day(label: str, frequency: ObservationFrequency) -> dt.date:
    """Parse compact and ISO dates, preserving the period-end convention."""
    text = label.strip()
    if re.fullmatch(r"\d{8}", text):
        return dt.date(int(text[:4]), int(text[4:6]), int(text[6:]))
    if re.fullmatch(r"\d{6}", text):
        return s.month_end(int(text[:4]), int(text[4:]))
    if re.fullmatch(r"\d{4}", text):
        return dt.date(int(text), 12, 31)
    observed = dt.date.fromisoformat(text[:10])
    if frequency is ObservationFrequency.MONTHLY:
        return s.month_end(observed.year, observed.month)
    return observed


def value(raw: object, provider: str, *, percent: bool = False) -> float | None:
    """Read a source's declared missing markers, without a numerical heuristic."""
    if raw is None:
        return None
    return s.rate_or_value(
        s.number(raw, provider, missing=("NA", "N/A", ".", "nan")), percent=percent
    )


def slug(text: str) -> str:
    """Name a published category without a request path or an arbitrary URL."""
    return re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
