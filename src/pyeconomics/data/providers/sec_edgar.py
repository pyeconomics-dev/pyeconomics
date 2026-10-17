# src/pyeconomics/data/providers/sec_edgar.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""SEC EDGAR JSON APIs with transport-only contact handling.

``records`` accepts ``submissions:CIK``. Numeric ``fetch`` accepts
``concept:CIK:taxonomy:tag:unit``, ``facts:CIK:taxonomy:tag:unit`` or
``frame:taxonomy:tag:unit:CY2024Q1I:CIK``. CIKs are normalized to ten digits.
XBRL facts retain their actual end dates and are never calendar-aligned by guess.
When multiple filings report one end date, the latest filed observation wins.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import DataError, RateLimitError, SeriesNotFoundError
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Authentication,
    AuthKind,
    Capability,
    Case,
    DataProvider,
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.records import Filing, Records
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, request_path
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

__all__ = ["SecEdgar"]

_ID: Final = "sec_edgar"

_TOKEN: Final = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}")
_PERIOD: Final = re.compile(r"CY\d{4}(?:Q[1-4]I?)?")
_TAXONOMIES: Final = frozenset({"us-gaap", "ifrs-full", "dei", "srt"})


def cik(value: str) -> str:
    """Normalize a CIK, rejecting paths and nonnumeric identifiers."""
    if not re.fullmatch(r"[0-9]{1,10}", value):
        msg = "sec_edgar CIK must contain one to ten digits"
        raise DataError(msg, provider="sec_edgar")
    return value.zfill(10)


def _parts(query: Query) -> list[str]:
    if len(query.series) != 1:
        msg = "sec_edgar takes one dataset per query"
        raise DataError(msg, provider="sec_edgar")
    parts = query.series[0].split(":")
    if any(not _TOKEN.fullmatch(p) and not p.isdecimal() for p in parts[2:]):
        msg = "sec_edgar tags and units must be identifiers"
        raise DataError(msg, provider="sec_edgar")
    return parts


class SecEdgar(DataProvider):
    """Submissions and XBRL data; a configured SEC contact is required."""

    info = ProviderInfo(
        id="sec_edgar",
        name="US Securities and Exchange Commission",
        homepage="https://www.sec.gov",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.sec.gov/about/privacy-information",
            checked=dt.date(2026, 10, 16),
            attribution="Source: U.S. Securities and Exchange Commission, EDGAR.",
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        auth=Authentication(kind=AuthKind.CONTACT),
        hosts=("data.sec.gov",),
        capabilities=(Capability.FETCH, Capability.RECORDS),
        rate_limits=(RateLimit(requests=10, per="second"),),
        ttl_seconds=3600,
    )
    cases = (
        Case(
            name="submissions",
            operation=Capability.RECORDS,
            argument=Query(series=("submissions:320193",), max_observations=24),
        ),
        *(
            Case(
                name=kind,
                operation=Capability.FETCH,
                argument=Query(
                    series=(f"{kind}:320193:us-gaap:Assets:USD",),
                    start=dt.date(2024, 1, 1),
                    end=dt.date(2025, 12, 31),
                    max_observations=24,
                ),
            )
            for kind in ("concept", "facts")
        ),
        Case(
            name="frame",
            operation=Capability.FETCH,
            argument=Query(
                series=("frame:us-gaap:Assets:USD:CY2024Q1I:320193",),
                max_observations=24,
            ),
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:NonexistentTag:USD",),
                max_observations=24,
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:Assets:USD",), max_observations=24
            ),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def build_records(self, query: Query) -> Sequence[Request]:
        """Build submissions requests without accepting document paths."""
        parts = _parts(query)
        if len(parts) != len(("submissions", "CIK")) or parts[0] != "submissions":
            msg = "sec_edgar records require submissions:CIK"
            raise DataError(msg, provider="sec_edgar")
        return (
            Request(
                host="data.sec.gov",
                path=request_path("submissions", f"CIK{cik(parts[1])}.json"),
            ),
        )

    def parse_records(self, responses: Sequence[Response], query: Query) -> Records:
        """Return bounded typed filings, omitting addresses and document filenames."""
        company = cik(_parts(query)[1])
        body = s.body_object(responses[0], "sec_edgar")
        recent = body.get("filings", {}).get("recent", {})
        accessions = s.items(recent.get("accessionNumber"), "sec_edgar", "accessions")
        rows = []
        for i, accession in enumerate(accessions):
            day = dt.date.fromisoformat(recent["filingDate"][i])
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            report = recent.get("reportDate", [""] * len(accessions))[i]
            rows.append(
                Filing(
                    cik=company,
                    accession=accession,
                    form=recent["form"][i],
                    filed=day,
                    report_date=dt.date.fromisoformat(report) if report else None,
                )
            )
            if len(rows) == query.max_observations:
                break
        return Records(
            provider="sec_edgar",
            terms=self.info.terms,
            retrieved_at=responses[0].retrieved_at,
            rows=tuple(rows),
        )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep a handful of genuine observations in the source's format."""
        from pyeconomics.data.transport.recording import trim_response  # noqa: PLC0415

        return trim_response(self.info.id, request, response, query)

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Build only the documented XBRL routes and taxonomies."""
        p = _parts(query)
        segments: tuple[str, ...]
        if (
            len(p) == len(("concept", "CIK", "taxonomy", "tag", "unit"))
            and p[0] in {"concept", "facts"}
            and p[2] in _TAXONOMIES
        ):
            company = f"CIK{cik(p[1])}"
            segments = (
                ("companyfacts", company + ".json")
                if p[0] == "facts"
                else ("companyconcept", company, p[2], p[3] + ".json")
            )
        elif (
            len(p) == len(("frame", "taxonomy", "tag", "unit", "period", "CIK"))
            and p[0] == "frame"
            and p[1] in _TAXONOMIES
            and _PERIOD.fullmatch(p[4])
        ):
            cik(p[5])
            segments = ("frames", p[1], p[2], p[3], p[4] + ".json")
        else:
            msg = "sec_edgar query must name a documented concept, facts or frame"
            raise DataError(msg, provider="sec_edgar")
        return (
            Request(host="data.sec.gov", path=request_path("api", "xbrl", *segments)),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Select the requested unit and latest filing per actual period end."""
        p = _parts(query)
        body = s.body_object(responses[0], "sec_edgar")
        if p[0] == "facts":
            body = body.get("facts", {}).get(p[2], {}).get(p[3], {})
        if p[0] == "frame":
            raw = [
                row for row in body.get("data", []) if cik(str(row["cik"])) == cik(p[5])
            ]
            unit = p[3]
        else:
            unit = p[4]
            raw = body.get("units", {}).get(unit, [])
        by_day: dict[dt.date, tuple[str, float | None]] = {}
        for row in raw:
            day = dt.date.fromisoformat(row["end"])
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            filed = str(row.get("filed", ""))
            if day not in by_day or filed >= by_day[day][0]:
                by_day[day] = (filed, s.number(row["val"], "sec_edgar"))
        if not by_day:
            raise SeriesNotFoundError(_ID, query.series[0])
        index = tuple(sorted(by_day))[-query.max_observations :]
        units = (
            UnitRecord(text=unit, kind=UnitKind.MONEY, currency=unit)
            if unit in {"USD", "EUR", "CAD"}
            else UnitRecord(text=unit)
        )
        return Series(
            index,
            tuple(by_day[d][1] for d in index),
            SeriesMeta(
                provider="sec_edgar",
                series_id=query.series[0],
                title=query.series[0],
                unit=units,
                frequency=ObservationFrequency.IRREGULAR,
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
                source_dating=DateConvention.PERIOD_END,
                terms=self.info.terms,
                retrieved_at=responses[0].retrieved_at,
                notes=(
                    "latest_filing: latest filing retained for each actual period end",
                ),
            ),
        )
