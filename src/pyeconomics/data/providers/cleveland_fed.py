# src/pyeconomics/data/providers/cleveland_fed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Cleveland Fed monthly inflation expectations and real interest rates.

Ids: ``expected_inflation:1`` through ``expected_inflation:30``,
``real_rate:1m``, ``real_rate:1y``, ``real_rate:10y``,
``inflation_risk_premium:10`` and ``real_risk_premium:10``.
The published file retains revised estimates, not publication vintages.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import SeriesNotFoundError
from pyeconomics.data.providers import _research as r
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import DataProvider, ProviderInfo, Query, RateLimit
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import spreadsheet, workbook
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

PROVIDER: Final = "cleveland_fed"

__all__ = ["ClevelandFed"]
HOST: Final = "www.clevelandfed.org"
PATH: Final = (
    "/-/media/files/webcharts/inflationexpectations/inflation-expectations.xlsx"
)
NOTICE: Final = (
    "The information is used for noncommercial, personal, or "
    "educational purposes only (i.e., not for private gain)"
)
TERMS: Final = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://www.clevelandfed.org/privacy",
    checked=dt.date(2026, 10, 17),
    attribution="Source: Federal Reserve Bank of Cleveland.",
    notice=NOTICE,
    llm_use=LlmUse.UNCLEAR,
    cache=CachePolicy.ALLOWED,
)


def selection(series_id: str) -> tuple[str, str]:
    """Map only the model outputs the source actually publishes."""
    match = re.fullmatch(r"expected_inflation:([1-9]|[12][0-9]|30)", series_id)
    if match:
        return "Expected Inflation", f"{match[1]} year Expected Inflation"
    names = {
        "real_rate:1m": ("Real Interest Rate", "Real Rate 1-month"),
        "real_rate:1y": ("Real Interest Rate", "Real Rate 1-year"),
        "real_rate:10y": ("Real Interest Rate", "Real Rate 10-year"),
        "inflation_risk_premium:10": (
            "Ten-year Expected Chart",
            "Inflation Risk Premium",
        ),
        "real_risk_premium:10": ("Ten-year Expected Chart", "Real Risk Premium"),
    }
    if series_id not in names:
        raise SeriesNotFoundError(PROVIDER, series_id)
    return names[series_id]


class ClevelandFed(DataProvider):
    """Read the source's monthly workbook; convert every percent to a decimal."""

    info = ProviderInfo(
        id="cleveland_fed",
        name="Federal Reserve Bank of Cleveland",
        homepage="https://www.clevelandfed.org",
        terms=TERMS,
        hosts=(HOST,),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=86400,
    )
    cases = (
        *r.cases("expected_inflation:10"),
        *tuple(
            replace(c, name="real_" + c.name)
            for c in r.cases("real_rate:10y")
            if c.expect is None
        ),
        *tuple(
            replace(c, name="premium_" + c.name)
            for c in r.cases("inflation_risk_premium:10")
            if c.expect is None
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Read the model workbook from its fixed, allowlisted location."""
        series_id = r.single(query, self.info.id)
        selection(series_id)
        return (Request(host=HOST, path=PATH, series=series_id),)

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Read the requested column; preserve missing observations and revisions."""
        series_id = r.single(query, self.info.id)
        sheet, column = selection(series_id)
        rows = spreadsheet(responses[0].body, sheet, self.info.id)
        header = [str(c).strip() for c in rows[0]] if rows else []
        if column not in header:
            raise SeriesNotFoundError(self.info.id, series_id)
        position = header.index(column)
        pairs = []
        for row in rows[1:]:
            if row[0] is None:
                continue
            start = r.day(row[0], self.info.id)
            observed = s.month_end(start.year, start.month)
            if (query.start is None or observed >= query.start) and (
                query.end is None or observed <= query.end
            ):
                pairs.append(
                    (observed, r.number(row[position], self.info.id, percent=True))
                )
        if not pairs:
            raise SeriesNotFoundError(self.info.id, series_id)
        pairs.sort()
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=series_id,
            title=column,
            unit=UnitRecord(text="Percent", kind=UnitKind.RATE),
            frequency=ObservationFrequency.MONTHLY,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_START,
            terms=TERMS,
            notes=("revised_data",),
        )
        return Series(tuple(d for d, _ in pairs), tuple(v for _, v in pairs), meta)

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Preserve the sheet and column layout, never the published model outputs."""
        sheet, _ = selection(request.series or "")
        rows = spreadsheet(response.body, sheet, self.info.id)
        out = [rows[0]]
        for i, row in enumerate(rows[-3:]):
            out.append(
                tuple(
                    v
                    if j == 0 or v is None
                    else synthetic_value(seed, i * len(row) + j)
                    for j, v in enumerate(row)
                )
            )
        return replace(response, body=workbook({sheet: tuple(out)}))
