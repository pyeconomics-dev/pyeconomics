# src/pyeconomics/data/providers/penn_world_table.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""PWT 11.0 country series, CC BY 4.0 with the authors' required citation.

Ids are ``USA:rgdpna``, ``USA:rkna``, ``DEU:emp`` and analogous country/variable
pairs from the numeric columns. Shares are already decimals; they are not
divided by 100. Release version 11.0 is recorded independently of retrieval.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import ResponseError, SeriesNotFoundError
from pyeconomics.data.providers import _research as r
from pyeconomics.data.providers.base import DataProvider, ProviderInfo, Query, RateLimit
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
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

PROVIDER: Final = "penn_world_table"

__all__ = ["PennWorldTable"]
HOST: Final = "dataverse.nl"
PATH: Final = "/api/access/datafile/554105"
NOTICE: Final = (
    "Feenstra, Robert C., Robert Inklaar and Marcel P. Timmer "
    '(2015), "The Next Generation of the Penn World Table" American'
    " Economic Review, 105(10), 3150-3182, available for download "
    "at www.ggdc.net/pwt"
)
TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.rug.nl/ggdc/productivity/pwt/",
    checked=dt.date(2026, 10, 17),
    attribution=(
        "Penn World Table 11.0 by Robert C. Feenstra, Robert Inklaar "
        "and Marcel P. Timmer."
    ),
    notice=NOTICE,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)


def selection(series_id: str) -> tuple[str, str]:
    """Validate country and variable ids without accepting a URL or path."""
    match = re.fullmatch(r"([A-Z]{3}):([a-z][a-z0-9_]{0,31})", series_id)
    if (
        not match
        or match[2].startswith("i_")
        or match[2] in {"countrycode", "country", "currency_unit", "year"}
    ):
        raise SeriesNotFoundError(PROVIDER, series_id)
    return match[1], match[2]


def unit_record(variable: str, text: str) -> UnitRecord:
    """Read the release legend without rescaling already-decimal shares."""
    if "mil. 2021US$" in text:
        return UnitRecord(text=text, kind=UnitKind.MONEY, scale=1e6, currency="USD")
    if variable in {"emp", "pop"}:
        return UnitRecord(text=text, kind=UnitKind.COUNT, scale=1e6)
    if variable in {"labsh", "irr", "delta"} or variable.startswith("csh_"):
        return UnitRecord(text=text, kind=UnitKind.RATE)
    return UnitRecord(
        text=text,
        kind=UnitKind.INDEX_LEVEL
        if "index" in text.lower() or "2021=1" in text
        else None,
    )


class PennWorldTable(DataProvider):
    """The current PWT release, pinned to the release's permanent Dataverse file."""

    info = ProviderInfo(
        id="penn_world_table",
        name="Penn World Table",
        homepage="https://www.rug.nl/ggdc/productivity/pwt/",
        terms=TERMS,
        hosts=(HOST, "objectstore.surf.nl"),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=2592000,
    )
    cases = (
        *r.cases("USA:rgdpna"),
        *tuple(
            replace(c, name="capital_" + c.name)
            for c in r.cases("USA:rkna")
            if c.expect is None
        ),
        *tuple(
            replace(c, name="share_" + c.name)
            for c in r.cases("USA:labsh")
            if c.expect is None
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Allow the release file to redirect only to its declared storage host."""
        series_id = r.single(query, self.info.id)
        selection(series_id)
        return (Request(host=HOST, path=PATH, series=series_id),)

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Read national accounts and factor inputs with source-defined units."""
        series_id = r.single(query, self.info.id)
        country, variable = selection(series_id)
        body = responses[0].body
        info = spreadsheet(body, "Info", self.info.id)
        if not info or str(info[0][0]).strip() != "Penn World Table, version 11.0":
            msg = "PWT file does not identify the declared release version"
            raise ResponseError(msg, provider=self.info.id)
        rows = spreadsheet(body, "Data", self.info.id)
        header = rows[0] if rows else ()
        if variable not in header or not all(
            x in header for x in ("countrycode", "year")
        ):
            raise SeriesNotFoundError(self.info.id, series_id)
        column, geography, year_column = (
            header.index(variable),
            header.index("countrycode"),
            header.index("year"),
        )
        legend = spreadsheet(body, "Legend", self.info.id)
        text = next(
            (str(row[1]) for row in legend if len(row) > 1 and row[0] == variable), None
        )
        if text is None:
            raise SeriesNotFoundError(self.info.id, series_id)
        unit = unit_record(variable, text)
        pairs = []
        for row in rows[1:]:
            if row[geography] != country:
                continue
            year = row[year_column]
            if not isinstance(year, int) or isinstance(year, bool):
                msg = "PWT supplied a nonintegral year"
                raise ResponseError(msg, provider=self.info.id)
            observed = dt.date(year, 12, 31)
            if (query.start is None or observed >= query.start) and (
                query.end is None or observed <= query.end
            ):
                pairs.append((observed, r.number(row[column], self.info.id)))
        if not pairs:
            raise SeriesNotFoundError(self.info.id, series_id)
        pairs.sort()
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=series_id,
            title=text,
            unit=unit,
            frequency=ObservationFrequency.ANNUAL,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_END,
            terms=TERMS,
            notes=(
                "release_version: 11.0",
                "release_date: 2025-10-07",
                "licence: CC BY 4.0",
                "revised_data",
            ),
        )
        return Series(tuple(d for d, _ in pairs), tuple(v for _, v in pairs), meta)

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep only the selected country, column and a bounded published tail."""
        country, variable = selection(request.series or "")
        rows = spreadsheet(response.body, "Data", self.info.id)
        header = rows[0]
        columns = [header.index(x) for x in ("countrycode", "year", variable)]
        selected = [row for row in rows[1:] if row[columns[0]] == country][
            -min(query.max_observations, 24) :
        ]
        legend = spreadsheet(response.body, "Legend", self.info.id)
        return replace(
            response,
            body=workbook(
                {
                    "Info": (("Penn World Table, version 11.0",),),
                    "Legend": tuple(
                        row[:2]
                        for row in legend
                        if row[0] in {"Variable name", variable}
                    ),
                    "Data": (
                        tuple(header[j] for j in columns),
                        *(tuple(row[j] for j in columns) for row in selected),
                    ),
                }
            ),
        )
