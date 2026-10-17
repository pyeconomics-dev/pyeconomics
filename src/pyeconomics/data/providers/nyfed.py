# src/pyeconomics/data/providers/nyfed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""New York Fed reference rates, operations and research estimates.

Dataset ids: ``sofr``, ``effr``, ``obfr``, ``tgcr``, ``bgcr``, ``repo``,
``reverse_repo``, ``soma``, ``acm``, ``lw``, ``hlw`` and ``nowcast``.
An r* id may select a source-labelled vintage sheet: ``lw:2005q1`` or
``hlw:2025Q1``. A sheet label is a data vintage, not an availability date;
no artificial release date is assigned to historical HLW estimates.
"""

from __future__ import annotations

import datetime as dt
import re
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
from pyeconomics.data.transport.files import legacy_spreadsheet, spreadsheet
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

__all__ = ["NyFed"]

_ID: Final = "nyfed"

NOTICE: Final = (
    "\u00a9 2026 Federal Reserve Bank of New York. Content from the New York Fed "
    "subject to the Terms of Use at newyorkfed.org."
)
_RATE: Final = UnitRecord(text="Percent", kind=UnitKind.RATE)
_USD: Final = UnitRecord(text="Dollars", kind=UnitKind.MONEY, currency="USD")
_BILLIONS: Final = UnitRecord(
    text="Billions of dollars", kind=UnitKind.MONEY, currency="USD", scale=1e9
)
_RATES: Final = frozenset({"sofr", "effr", "obfr", "tgcr", "bgcr"})
_WORKBOOKS: Final = {
    "lw": "Laubach_Williams",
    "hlw": "Holston_Laubach_Williams",
}
_NOWCAST: Final = (
    "/medialibrary/Research/Interactives/Data/NowCast/downloads/"
    "New-York-Fed-Staff-Nowcast_download_data"
)


def _reference_notice(name: str) -> str:
    return (
        f"{NOTICE} The {name.upper()} is subject to the Terms of Use posted at "
        f"newyorkfed.org. The New York Fed is not responsible for publication of "
        f"the {name.upper()} by pyeconomics, does not sanction or endorse any "
        "particular republication, and has no liability for your use."
    )


class NyFed(DataProvider):
    """The NY Fed's Markets API and published research files."""

    info = ProviderInfo(
        id="nyfed",
        name="Federal Reserve Bank of New York",
        homepage="https://www.newyorkfed.org",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.newyorkfed.org/privacy/termsofuse.html",
            checked=dt.date(2026, 10, 16),
            attribution="Source: Federal Reserve Bank of New York.",
            notice=NOTICE,
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        hosts=("markets.newyorkfed.org", "www.newyorkfed.org"),
        capabilities=(Capability.FETCH, Capability.BULK),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=86400,
    )
    cases = (
        *(
            Case(
                name=name,
                operation=Capability.FETCH,
                argument=Query(series=(name,), max_observations=3),
            )
            for name in (
                *sorted(_RATES),
                "repo",
                "reverse_repo",
                "soma",
                "acm",
                "lw",
                "hlw",
                "nowcast",
            )
        ),
        Case(
            name="lw_vintage",
            operation=Capability.FETCH,
            argument=Query(series=("lw:2005q1",), max_observations=3),
        ),
        Case(
            name="hlw_vintage",
            operation=Capability.FETCH,
            argument=Query(series=("hlw:2025Q1",), max_observations=3),
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("sofr",),
                start=dt.date(1900, 1, 1),
                end=dt.date(1900, 1, 2),
                max_observations=3,
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(series=("sofr",), max_observations=3),
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

    def build_requests(self, query: Query) -> Sequence[Request]:  # noqa: C901, PLR0912 - one allowlisted branch per dataset
        """Select a fixed route or research file; accept no caller URL."""
        if len(query.series) != 1:
            msg = "nyfed takes one dataset per query"
            raise DataError(msg, provider="nyfed")
        name, _, vintage = query.series[0].partition(":")
        host = "www.newyorkfed.org"
        params = []
        if name in _RATES:
            host = "markets.newyorkfed.org"
            group = "unsecured" if name in {"effr", "obfr"} else "secured"
            if query.start or query.end:
                path = f"/api/rates/{group}/{name}/search.json"
                if query.start:
                    params.append(("startDate", query.start.isoformat()))
                if query.end:
                    params.append(("endDate", query.end.isoformat()))
            else:
                count = min(query.max_observations, 10000)
                path = f"/api/rates/{group}/{name}/last/{count}.json"
        elif name in {"repo", "reverse_repo"}:
            host = "markets.newyorkfed.org"
            kind = "repo" if name == "repo" else "reverserepo"
            count = min(query.max_observations, 100)
            path = f"/api/rp/{kind}/all/results/last/{count}.json"
        elif name == "soma":
            host, path = "markets.newyorkfed.org", "/api/soma/summary.json"
        elif name == "acm":
            path = "/medialibrary/media/research/data_indicators/ACMTermPremium.xls"
        elif name in _WORKBOOKS:
            if vintage and not re.fullmatch(r"20\d{2}[qQ][1-4]", vintage):
                msg = "nyfed rstar vintage is the source-labelled quarter YYYYqN"
                raise DataError(msg, provider="nyfed")
            kind = "real_time" if vintage else "current"
            path = (
                "/medialibrary/media/research/economists/williams/data/"
                f"{_WORKBOOKS[name]}_{kind}_estimates.xlsx"
            )
        elif name == "nowcast":
            path = _NOWCAST
        else:
            msg = "nyfed dataset is not allowlisted"
            raise SeriesNotFoundError(_ID, query.series[0])
        return (
            Request(host=host, path=path, params=tuple(params), series=query.series[0]),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Read each dataset's documented units, dating and notices."""
        name, _, vintage = query.series[0].partition(":")
        response = responses[0]
        notes: tuple[str, ...] = ()
        if name in _WORKBOOKS or name == "nowcast":
            rows, units = self._xlsx(response, name, vintage)
            authors = (
                "Thomas Laubach and John C. Williams"
                if name == "lw"
                else "Kathryn Holston, Thomas Laubach and John C. Williams"
                if name == "hlw"
                else "Federal Reserve Bank of New York research staff"
            )
            notes = (f"source_vintage: {vintage or 'current'}", f"authors: {authors}")
            if name in _WORKBOOKS and not vintage:
                notes += ("revised_data",)

        elif name == "acm":
            cells = legacy_spreadsheet(response.body, "ACM Daily", "nyfed")
            names = tuple(str(n) for n in cells[0][1:])
            units = dict.fromkeys(names, _RATE)
            rows = {
                dt.datetime.strptime(str(row[0]), "%d-%b-%Y")
                .replace(tzinfo=dt.UTC)
                .date(): {
                    n: s.rate_or_value(
                        s.number(row[i + 1], "nyfed", missing=("NA",)), percent=True
                    )
                    for i, n in enumerate(names)
                }
                for row in cells[1:]
            }
            notes = (
                (
                    "acm: Tobias Adrian, Richard Crump and Emanuel Moench; "
                    "daily one- through ten-year "
                    "term premia, fitted yields and risk-neutral yields"
                ),
            )
        else:
            rows, units = self._markets(response, name)
        rows = {
            d: row
            for d, row in rows.items()
            if (not query.start or d >= query.start)
            and (not query.end or d <= query.end)
        }
        if not rows:
            raise SeriesNotFoundError(_ID, query.series[0])
        index = tuple(sorted(rows))[-query.max_observations :]
        names = tuple(units)
        terms = (
            replace(self.info.terms, notice=_reference_notice(name))
            if name in _RATES
            else self.info.terms
        )
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
                provider="nyfed",
                table_id=query.series[0],
                title=query.series[0],
                frequency=(
                    ObservationFrequency.QUARTERLY
                    if name in _WORKBOOKS
                    else ObservationFrequency.BUSINESS_DAILY
                    if name in _RATES or name == "acm"
                    else ObservationFrequency.IRREGULAR
                ),
                source_dating=(
                    DateConvention.PERIOD_START
                    if name in _WORKBOOKS and not vintage
                    else DateConvention.PERIOD_END
                ),
                terms=terms,
                retrieved_at=response.retrieved_at,
                notes=notes,
            ),
        )

    def _markets(
        self, response: Response, name: str
    ) -> tuple[dict[dt.date, dict[str, float | None]], dict[str, UnitRecord]]:
        body = s.body_object(response, "nyfed")
        names: tuple[str, ...]
        if name in _RATES:
            raw = s.items(body.get("refRates"), "nyfed", "reference rates")
            field, names = (
                "effectiveDate",
                (
                    "percentRate",
                    "percentPercentile1",
                    "percentPercentile25",
                    "percentPercentile75",
                    "percentPercentile99",
                    "volumeInBillions",
                ),
            )
        elif name == "soma":
            raw = s.items(body.get("soma", {}).get("summary"), "nyfed", "SOMA summary")
            field, names = (
                "asOfDate",
                (
                    "mbs",
                    "cmbs",
                    "tips",
                    "frn",
                    "tipsInflationCompensation",
                    "notesbonds",
                    "bills",
                    "agencies",
                    "total",
                ),
            )
        else:
            root = "repo"
            raw = s.items(body.get(root, {}).get("operations"), "nyfed", "operations")
            field, names = "operationDate", ("totalAmtSubmitted", "totalAmtAccepted")
        units = {
            n: _RATE
            if n.startswith("percent")
            else _BILLIONS
            if n == "volumeInBillions"
            else _USD
            for n in names
        }
        rows: dict[dt.date, dict[str, float | None]] = {}
        for row in raw:
            day = dt.date.fromisoformat(row[field])
            values = {
                n: s.rate_or_value(
                    s.number(
                        row[n] if row.get(n) is not None else "",
                        "nyfed",
                        missing=("NA",),
                    ),
                    percent=n.startswith("percent"),
                )
                for n in names
            }
            # Repo may have morning and afternoon operations on the same day.
            # Sum daily volumes rather than silently keeping the last operation.
            if day in rows and name in {"repo", "reverse_repo"}:
                values = {n: (rows[day][n] or 0) + (values[n] or 0) for n in names}
            rows[day] = values
        return rows, units

    def _xlsx(
        self, response: Response, name: str, vintage: str
    ) -> tuple[dict[dt.date, dict[str, float | None]], dict[str, UnitRecord]]:
        sheet = vintage or (
            "Forecasts By Quarter"
            if name == "nowcast"
            else "data"
            if name == "lw"
            else "HLW Estimates"
        )
        cells = spreadsheet(response.body, sheet, "nyfed")
        header_at = next(
            i
            for i, row in enumerate(cells)
            if isinstance(row[0], str)
            and row[0].casefold() in {"date", "forecast date"}
        )
        header = cells[header_at]
        columns: dict[int, str] = {}
        if name == "nowcast":
            columns = {
                i: str(value)
                for i, value in enumerate(header)
                if i and value and re.fullmatch(r"20\d{2}Q[1-4]", str(value))
            }
        elif name == "lw":
            # Keep one-sided and two-sided estimates distinct. The older
            # vintage files put one-sided rstar at a different column.
            for i, value in enumerate(header):
                if value in {"rstar", "g", "z", "Output gap"}:
                    prefix = (
                        "two_sided_"
                        if str(value).replace(" ", "_") in columns.values()
                        else ""
                    )
                    columns[i] = prefix + str(value).replace(" ", "_")
        else:
            group = ""
            for i, value in enumerate(header):
                previous = cells[header_at - 1][i]
                if previous:
                    group = str(previous)
                if value in {"US", "Canada", "Euro Area"}:
                    group_name = (
                        "rstar"
                        if "Natural Rate" in group
                        else "g"
                        if "Growth" in group
                        else "z"
                        if "Determinants" in group
                        else "output_gap"
                    )
                    columns[i] = group_name + "_" + str(value).replace(" ", "_")
        units = dict.fromkeys(columns.values(), _RATE)
        rows = {}
        for row in cells[header_at + 1 :]:
            stamp = row[0]
            if not isinstance(stamp, dt.datetime):
                continue
            day = (
                stamp.date()
                if name == "nowcast"
                else s.period_end(
                    stamp.date().replace(month=(stamp.month - 1) // 3 * 3 + 1, day=1),
                    ObservationFrequency.QUARTERLY,
                )
            )
            rows[day] = {
                n: s.rate_or_value(
                    s.number(
                        row[i] if row[i] is not None else "", "nyfed", missing=("NA",)
                    ),
                    percent=True,
                )
                for i, n in columns.items()
            }
        return rows, units
