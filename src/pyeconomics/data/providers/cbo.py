# src/pyeconomics/data/providers/cbo.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""CBO economic projections, each report dated by its public release.

Ids are ``quarterly:real_potential_gdp``, ``calendar:potential_lf``,
``fiscal:noncyclical_rate_of_unemployment``, ``quarterly:output_gap`` and
the other fields of CBO's economic_projections schema. The source's own
machine-readable repository is the automated-access route its data page
recommends. All five releases currently supplied there are retained.

Release dates: Budget and Economic Outlook 2024 (publication 59710),
June 2024 update (60039), January 2025 outlook (60870), September 2025
update (61236), February 2026 outlook (62105). A month label is never
silently interpreted as the first day of that month.
"""

# ruff: noqa: PLR2004 - source calendar and fixed spreadsheet layout constants

from __future__ import annotations

import csv
import datetime as dt
import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import ResponseError, SeriesNotFoundError
from pyeconomics.data.providers import _research as r
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import Capability, ProviderInfo, Query, RateLimit
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
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

PROVIDER: Final = "cbo"

__all__ = ["Cbo"]
HOST: Final = "raw.githubusercontent.com"
ROOT: Final = "/US-CBO/cbo-data/main/data/economic/economic_projections/"
RELEASES: Final = (
    dt.date(2024, 2, 7),
    dt.date(2024, 6, 18),
    dt.date(2025, 1, 17),
    dt.date(2025, 9, 12),
    dt.date(2026, 2, 11),
)
NOTICE: Final = (
    "Government documents are in the public domain and are not "
    "protected by copyright law."
)
TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.cbo.gov/about/privacy",
    checked=dt.date(2026, 10, 17),
    attribution="Source: Congressional Budget Office.",
    notice=NOTICE,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)


def selection(series_id: str) -> tuple[str, str]:
    """Only CBO's three documented frequency files and snake_case fields."""
    match = re.fullmatch(
        r"(quarterly|calendar|fiscal):([a-z][a-z0-9_]{0,79})", series_id
    )
    if not match:
        raise SeriesNotFoundError(PROVIDER, series_id)
    return match[1], match[2]


def records(body: bytes) -> list[dict[str, str]]:
    """Bound the number of long-format records before constructing a frame."""
    reader = csv.DictReader(body.decode("utf-8-sig").splitlines())
    if reader.fieldnames is None or not {"date", "variable", "value"} <= set(
        reader.fieldnames
    ):
        msg = "CBO supplied no documented CSV fields"
        raise ResponseError(msg, provider="cbo")
    out: list[dict[str, str]] = []
    for row in reader:
        if len(out) >= 250_000:
            msg = "CBO CSV exceeds its record cap"
            raise ResponseError(msg, provider="cbo")
        out.append(row)
    return out


class Cbo(r.VintageResearch):
    """Potential output, labour inputs, output gap and ten-year projections."""

    info = ProviderInfo(
        id="cbo",
        name="Congressional Budget Office",
        homepage="https://www.cbo.gov",
        terms=TERMS,
        hosts=(HOST,),
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        rate_limits=(RateLimit(requests=3, per="second"),),
        ttl_seconds=86400,
    )
    cases = (
        *r.cases("quarterly:real_potential_gdp", vintages=True),
        *tuple(
            replace(c, name="labour_" + c.name)
            for c in r.cases("calendar:potential_lf")
            if c.expect is None
        ),
        *tuple(
            replace(c, name="gap_" + c.name)
            for c in r.cases("quarterly:output_gap")
            if c.expect is None
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Fetch metadata and every available report, preserving exact release days."""
        series_id = r.single(query, self.info.id)
        frequency, _ = selection(series_id)
        return (
            Request(host=HOST, path=ROOT + "schema.json", series=series_id),
            *(
                Request(
                    host=HOST,
                    path=ROOT + frequency + "_" + day.strftime("%Y-%m") + ".csv",
                    series=series_id,
                )
                for day in RELEASES
            ),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Close intervals at the next report, including projections beyond release."""
        series_id = r.single(query, self.info.id)
        frequency, variable = selection(series_id)
        schema = s.body_object(responses[0], self.info.id)
        fields = schema.get("fields")
        field = fields.get(variable) if isinstance(fields, dict) else None
        if not isinstance(field, dict):
            raise SeriesNotFoundError(self.info.id, series_id)
        text = s.text(field, "unit", self.info.id)
        percent = "percent" in text.lower() or "%" in text
        if percent:
            unit = UnitRecord(text=text, kind=UnitKind.RATE)
        elif "bil" in text.lower() and ("dollar" in text.lower() or "$" in text):
            unit = UnitRecord(text=text, kind=UnitKind.MONEY, scale=1e9, currency="USD")
        elif "million" in text.lower():
            unit = UnitRecord(text=text, kind=UnitKind.COUNT, scale=1e6)
        else:
            unit = UnitRecord(
                text=text,
                kind=UnitKind.INDEX_LEVEL if "index" in text.lower() else None,
            )
        observations = []
        for published, response in zip(RELEASES, responses[1:], strict=True):
            for row in records(response.body):
                if row["variable"] == variable:
                    observed = r.period(row["date"], self.info.id)
                    observations.append(
                        (
                            observed,
                            published,
                            r.number(row["value"], self.info.id, percent=percent),
                        )
                    )
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=series_id,
            title=s.text(field, "description", self.info.id),
            unit=unit,
            frequency=ObservationFrequency.QUARTERLY
            if frequency == "quarterly"
            else ObservationFrequency.ANNUAL,
            year_ends_in=9 if frequency == "fiscal" else 12,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE
            if "SAAR" in text
            else SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_END,
            terms=TERMS,
            notes=(
                (
                    "release_dating: report publication day, not forecast period or "
                    "vintage month"
                ),
                (
                    "source_format: CBO official machine-readable economic "
                    "projections; available archive begins 2024-02"
                ),
            ),
        )
        return r.frame(observations, meta, query)

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Retain selected fields and at most 24 dated values per report."""
        _, variable = selection(request.series or "")
        if request.path.endswith("schema.json"):
            schema = s.body_object(response, self.info.id)
            fields = schema.get("fields", {})
            return replace(
                response,
                body=json.dumps({"fields": {variable: fields[variable]}}).encode(),
            )
        selected = [
            row for row in records(response.body) if row["variable"] == variable
        ][-min(24, query.max_observations) :]
        # These fields are controlled by CBO's snake_case/date/numeric schema;
        # no quotes or newlines are introduced by this projection.
        lines = [
            "date,variable,value",
            *(f"{row['date']},{row['variable']},{row['value']}" for row in selected),
        ]
        return replace(response, body=("\n".join(lines) + "\n").encode())
