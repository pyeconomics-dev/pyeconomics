# src/pyeconomics/data/providers/treasury.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Treasury par curves and the FiscalData API, using allowlisted datasets.

Query ids are ``par_nominal``, ``par_real``, ``debt``, ``statement`` and
``average_interest``. FiscalData columns retain their published units and
category identifiers; curve columns are decimal rates by tenor.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import DataError, RateLimitError, SeriesNotFoundError
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Capability,
    Case,
    DataProvider,
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
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
    from collections.abc import Sequence

__all__ = ["Treasury"]

_ID: Final = "treasury"

TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://home.treasury.gov/footer/privacy-act",
    checked=dt.date(2026, 10, 16),
    attribution="Source: U.S. Department of the Treasury.",
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
_CURVES: Final = {
    "par_nominal": "daily_treasury_yield_curve",
    "par_real": "daily_treasury_real_yield_curve",
}
_DATASETS: Final = {
    "debt": ("v2/accounting/od/debt_to_penny", ("tot_pub_debt_out_amt",)),
    "statement": (
        "v1/accounting/mts/mts_table_1",
        (
            "current_month_gross_rcpt_amt",
            "current_month_gross_outly_amt",
            "current_month_dfct_sur_amt",
        ),
    ),
    "average_interest": (
        "v2/accounting/od/avg_interest_rates",
        ("avg_interest_rate_amt",),
    ),
}
_RATE: Final = UnitRecord(text="Percent", kind=UnitKind.RATE)
_MONEY: Final = UnitRecord(text="Dollars", kind=UnitKind.MONEY, currency="USD")


def _case(name: str) -> Case:
    return Case(
        name=name,
        operation=Capability.FETCH,
        argument=Query(
            series=(name,),
            start=dt.date(2025, 1, 1),
            end=dt.date(2025, 1, 31),
            max_observations=24,
        ),
    )


class Treasury(DataProvider):
    """Published Treasury par curves and three FiscalData datasets."""

    info = ProviderInfo(
        id="treasury",
        name="US Department of the Treasury",
        homepage="https://home.treasury.gov",
        terms=TERMS,
        hosts=("home.treasury.gov", "api.fiscaldata.treasury.gov"),
        capabilities=(Capability.FETCH, Capability.BULK),
        rate_limits=(RateLimit(requests=5, per="second"),),
        ttl_seconds=6 * 3600,
    )
    cases = (
        *(_case(name) for name in (*_CURVES, *_DATASETS)),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(series=("unknown",), max_observations=24),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(series=("debt",), max_observations=24),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep a handful of genuine observations in the source's format."""
        from pyeconomics.data.transport.recording import trim_response  # noqa: PLC0415

        return trim_response(self.info.id, request, response, query)

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Build fixed dataset requests; a caller cannot supply a path."""
        name = query.series[0]
        if len(query.series) != 1:
            msg = "treasury takes one dataset per query"
            raise DataError(msg, provider="treasury")
        if name in _CURVES:
            # A month is the smallest published file; use the last response's
            # timestamp only when dates were omitted (no clock in this module).
            if query.start is None or query.end is None:
                msg = "curve queries require start and end"
                raise DataError(msg, provider="treasury")
            first = query.start.year * 12 + query.start.month - 1
            last = query.end.year * 12 + query.end.month - 1
            return tuple(
                Request(
                    host="home.treasury.gov",
                    path="/resource-center/data-chart-center/interest-rates/pages/xml",
                    params=(
                        ("data", _CURVES[name]),
                        (
                            "field_tdr_date_value_month",
                            f"{m // 12:04d}{m % 12 + 1:02d}",
                        ),
                    ),
                    series=name,
                )
                for m in range(first, last + 1)
            )
        if name not in _DATASETS:
            # Ask the fixed invalid endpoint to record the source's real 404.
            return (
                Request(
                    host="api.fiscaldata.treasury.gov",
                    path="/services/api/fiscal_service/v2/accounting/od/unknown",
                    series=name,
                ),
            )
        dataset, _ = _DATASETS[name]
        filters = []
        if query.start:
            filters.append(f"record_date:gte:{query.start.isoformat()}")
        if query.end:
            filters.append(f"record_date:lte:{query.end.isoformat()}")
        params = [
            ("format", "json"),
            ("sort", "-record_date"),
            ("page[size]", str(min(query.max_observations, 1000))),
            ("page[number]", "1"),
        ]
        if filters:
            params.append(("filter", ",".join(filters)))
        return (
            Request(
                host="api.fiscaldata.treasury.gov",
                path="/services/api/fiscal_service/" + dataset,
                params=tuple(params),
                series=name,
            ),
        )

    def next_page(self, request: Request, response: Response) -> Request | None:
        """Follow page numbers, ignoring upstream link URLs."""
        if request.host != "api.fiscaldata.treasury.gov":
            return None
        body = s.body_object(response, "treasury")
        params = dict(request.params)
        page = int(params["page[number]"])
        total = int(body.get("meta", {}).get("total-pages", 1))
        if page >= total:
            return None
        params["page[number]"] = str(page + 1)
        return replace(request, params=tuple(params.items()))

    def parse(self, responses: Sequence[Response], query: Query) -> Table:  # noqa: C901 - distinct XML curve and fiscal JSON formats
        """Parse safe XML or JSON, preserving categories as separate columns."""
        name = query.series[0]
        rows: dict[dt.date, dict[str, float | None]] = {}
        units: dict[str, UnitRecord] = {}
        if name in _CURVES:
            from defusedxml.ElementTree import fromstring  # noqa: PLC0415

            for response in responses:
                root = fromstring(response.body)
                for entry in root.iter():
                    if entry.tag.rsplit("}", 1)[-1] != "properties":
                        continue
                    cells = {c.tag.rsplit("}", 1)[-1]: c.text for c in entry}
                    day = dt.date.fromisoformat(str(cells["NEW_DATE"])[:10])
                    if (query.start and day < query.start) or (
                        query.end and day > query.end
                    ):
                        continue
                    row = rows.setdefault(day, {})
                    for key, value in cells.items():
                        if key.startswith(("BC_", "TC_")):
                            row[key] = s.rate_or_value(
                                s.number(value or "", "treasury", missing=("N/A",)),
                                percent=True,
                            )
                            units[key] = _RATE
        else:
            for response in responses:
                body = s.body_object(response, "treasury")
                for row in s.items(body.get("data"), "treasury", "data"):
                    day = dt.date.fromisoformat(s.text(row, "record_date", "treasury"))
                    category = str(
                        row.get("security_desc") or row.get("classification_id") or ""
                    )
                    for field in _DATASETS[name][1]:
                        key = (category + ":" if category else "") + field
                        value = s.number(
                            row[field], "treasury", missing=("null", "N/A")
                        )
                        rows.setdefault(day, {})[key] = s.rate_or_value(
                            value, percent=name == "average_interest"
                        )
                        units[key] = (
                            _RATE
                            if name == "average_interest"
                            else replace(_MONEY, text="Millions of dollars", scale=1e6)
                            if name == "statement"
                            else _MONEY
                        )
        if not rows:
            raise SeriesNotFoundError(_ID, query.series[0])
        index = tuple(sorted(rows))[-query.max_observations :]
        names = tuple(sorted(units))
        notes = (
            (
                (
                    "methodology_change: Treasury adopted a monotone convex spline "
                    "on December 6, 2021"
                ),
            )
            if name in _CURVES
            else ()
        )
        return Table(
            index,
            tuple(
                ColumnMeta(
                    name=n,
                    unit=units[n],
                    seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
                )
                for n in names
            ),
            tuple(tuple(rows[d].get(n) for d in index) for n in names),
            TableMeta(
                provider="treasury",
                table_id=name,
                title=name,
                frequency=ObservationFrequency.IRREGULAR,
                source_dating=DateConvention.PERIOD_END,
                terms=self.info.terms,
                retrieved_at=responses[-1].retrieved_at,
                notes=notes,
            ),
        )
