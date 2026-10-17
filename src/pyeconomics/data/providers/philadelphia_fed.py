# src/pyeconomics/data/providers/philadelphia_fed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Philadelphia Fed real-time matrices and SPF forecasts.

Ids are ``rtd:ROUTPUT``, ``rtd:P``, ``rtd:RUC``, or e.g.
``spf:median:RGDP:3`` / ``spf:mean:CPI:A`` / ``spf:median:CPI10``.
SPF 1 is the preceding quarter, 2 the survey quarter, 3 the next quarter;
A is the survey year, B the next year. Long-term forecasts index the survey
quarter and retain their horizon in metadata. Surveys before 1990Q2 lack
known publication dates and are excluded, rather than assigned invented dates.
"""

# ruff: noqa: PLR2004 - source calendar and fixed spreadsheet layout constants

from __future__ import annotations

import datetime as dt
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

PROVIDER: Final = "philadelphia_fed"

__all__ = ["PhiladelphiaFed"]
HOST: Final = "www.philadelphiafed.org"
ROOT: Final = "/-/media/FRBP/Assets/Surveys-And-Data/"
SPF: Final = ROOT + "survey-of-professional-forecasters/"
NOTICE: Final = (
    "The content provided on this website may be used for "
    "informational, educational, and research purposes only."
)
TERMS: Final = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://www.philadelphiafed.org/about-us/privacy-notice",
    checked=dt.date(2026, 10, 17),
    attribution=(
        "Source: Federal Reserve Bank of Philadelphia. Croushore and "
        "Stark (2001), A Real-Time Data Set for Macroeconomists."
    ),
    notice=NOTICE,
    llm_use=LlmUse.UNCLEAR,
    cache=CachePolicy.ALLOWED,
)
# Only documented quarterly-vintage products are admitted. Industrial-production
# monthly vintages use actual release dates, a different dating rule.
MATRICES: Final = {
    "ROUTPUT": (
        "ROUTPUTQvQd.xlsx",
        "ROUTPUT",
        "Billions of real dollars",
        UnitKind.MONEY,
        False,
    ),
    "P": ("PQvQd.xlsx", "P", "GDP price index", UnitKind.INDEX_LEVEL, False),
    "PCONX": (
        "PCONXQvQd.xlsx",
        "PCONX",
        "Core PCE price index",
        UnitKind.INDEX_LEVEL,
        False,
    ),
    "RUC": ("rucQvMd.xlsx", "ruc", "Percent", UnitKind.RATE, True),
}
_RATES: Final = frozenset(
    {
        "UNEMP",
        "TBILL",
        "BOND",
        "BAABOND",
        "TBOND",
        "CPI",
        "CORECPI",
        "PCE",
        "COREPCE",
        "UBAR",
        "CPI5YR",
        "PCE5YR",
        "CPI10",
        "PCE10",
        "RGDP10",
        "PROD10",
        "STOCK10",
        "BOND10",
        "BILL10",
    }
)


def selection(series_id: str) -> tuple[str, str, str, str]:
    """Validate the bounded source id before constructing any request."""
    parts = series_id.split(":")
    if len(parts) == 2 and parts[0] == "rtd" and parts[1] in MATRICES:
        return "rtd", "", parts[1], ""
    if (
        len(parts) in {3, 4}
        and parts[0] in {"spf", "spf_growth"}
        and parts[1] in {"mean", "median"}
        and re.fullmatch(r"[A-Z][A-Z0-9_]{0,31}", parts[2])
        and (len(parts) == 3 or parts[3] in {*"123456ABCD"})
    ):
        return parts[0], parts[1], parts[2], parts[3] if len(parts) == 4 else ""
    raise SeriesNotFoundError(PROVIDER, series_id)


def release_dates(body: bytes) -> dict[tuple[int, int], dt.date]:
    """Read the published release calendar; some rows omit the repeated year."""
    dates: dict[tuple[int, int], dt.date] = {}
    year = 0
    for line in body.decode("utf-8", "replace").splitlines():
        match = re.match(
            r"\s*(?:(\d{4})\s+)?Q([1-4])\s+.*?(\d{1,2}/\d{1,2}/\d{2,4})\**\s*$", line
        )
        if not match:
            continue
        if match[1]:
            year = int(match[1])
        if not year:
            continue
        month, day, release_year = map(int, match[3].split("/"))
        if release_year < 100:
            release_year += 1900 if release_year >= 90 else 2000
        dates[year, int(match[2])] = dt.date(release_year, month, day)
    return dates


def matrix_rows(
    rows: r.Rows, variable: str
) -> tuple[ObservationFrequency, UnitRecord, list[r.Observation], tuple[str, ...]]:
    """Read documented matrix column vintages."""
    frequency = (
        ObservationFrequency.MONTHLY
        if variable == "RUC"
        else ObservationFrequency.QUARTERLY
    )
    _, _, text, unit_kind, percent = MATRICES[variable]
    unit = UnitRecord(
        text=text,
        kind=unit_kind,
        scale=1e9 if unit_kind is UnitKind.MONEY else 1,
        currency="USD" if unit_kind is UnitKind.MONEY else None,
    )
    observations: list[r.Observation] = []
    available: set[dt.date] = set()
    for j, header in enumerate(rows[0][1:], 1):
        match = re.fullmatch(
            re.escape(variable) + r"(\d{2})Q([1-4])", str(header), re.IGNORECASE
        )
        if not match:
            msg = "real-time matrix has an undocumented vintage label"
            raise ResponseError(msg, provider=PROVIDER)
        year = int(match[1]) + (1900 if int(match[1]) >= 50 else 2000)
        published = dt.date(year, int(match[2]) * 3 - 1, 15)
        for row in rows[1:]:
            if row[0] is None:
                continue
            observed = r.period(row[0], PROVIDER)
            value = r.number(row[j], PROVIDER, percent=percent, missing_codes=True)
            if value is not None:
                available.add(observed)
            if observed in available:
                observations.append((observed, published, value))
    notes = (
        (
            "vintage_dating: quarterly snapshots as known on the 15th of "
            "February, May, August and November"
        ),
    )
    return frequency, unit, observations, notes


def survey_unit(variable: str, *, growth: bool) -> tuple[UnitRecord, bool]:
    """Read units from the SPF documentation, not from the numeric magnitude."""
    if (
        growth
        or variable in _RATES
        or variable.startswith(("SPR_", "RR", "CPI", "PCE"))
    ):
        return UnitRecord(text="Percent", kind=UnitKind.RATE), True
    if variable in {
        "NGDP",
        "RGDP",
        "RCONSUM",
        "RNRESIN",
        "RRESINV",
        "RFEDGOV",
        "RSLGOV",
        "RCBI",
        "REXPORT",
        "CPROF",
    }:
        return UnitRecord(
            text="Billions of dollars (real series: source base year varies)",
            kind=UnitKind.MONEY,
            scale=1e9,
            currency="USD",
        ), False
    if variable == "EMP":
        return UnitRecord(
            text="Thousands of jobs", kind=UnitKind.COUNT, scale=1e3
        ), False
    if variable == "HOUSING":
        return UnitRecord(
            text="Millions of housing starts, annual rate",
            kind=UnitKind.COUNT,
            scale=1e6,
        ), False
    if variable in {"PGDP", "INDPROD"}:
        return UnitRecord(
            text="Index, base year varies", kind=UnitKind.INDEX_LEVEL
        ), False
    raise SeriesNotFoundError(PROVIDER, variable)


def survey_rows(
    rows: r.Rows,
    variable: str,
    horizon: str,
    series_id: str,
    calendar: bytes,
) -> tuple[ObservationFrequency, UnitRecord, list[r.Observation], tuple[str, ...]]:
    """Read survey horizons and exact publication dates."""
    growth = series_id.startswith("spf_growth:")
    dates = release_dates(calendar)
    header = ("d" + variable.lower() if growth else variable) + horizon
    if header not in rows[0]:
        raise SeriesNotFoundError(PROVIDER, series_id)
    position = rows[0].index(header)
    annual = horizon in {"A", "B", "C", "D"}
    frequency = (
        ObservationFrequency.ANNUAL if annual else ObservationFrequency.QUARTERLY
    )
    unit, percent = survey_unit(variable, growth=growth)
    observations = []
    for row in rows[1:]:
        if row[0] is None or row[1] is None:
            continue
        year, quarter = r.integer(row[0], PROVIDER), r.integer(row[1], PROVIDER)
        survey_release = dates.get((year, quarter))
        if survey_release is None:
            continue
        if annual:
            observed = dt.date(year + ord(horizon) - ord("A"), 12, 31)
        elif horizon:
            offset = year * 4 + quarter - 1 + int(horizon) - 2
            observed = s.month_end(offset // 4, (offset % 4 + 1) * 3)
        else:
            observed = s.month_end(year, quarter * 3)
        observations.append(
            (
                observed,
                survey_release,
                r.number(row[position], PROVIDER, percent=percent, missing_codes=True),
            )
        )
    notes = (
        "survey_horizon: " + (horizon or variable),
        (
            "publication_dates: published SPF news-release calendar; unknown "
            "dates excluded"
        ),
    )
    return frequency, unit, observations, notes


class PhiladelphiaFed(r.VintageResearch):
    """RTDSM matrices and mean/median SPF levels, dated by their release calendar."""

    info = ProviderInfo(
        id="philadelphia_fed",
        name="Federal Reserve Bank of Philadelphia",
        homepage="https://www.philadelphiafed.org",
        terms=TERMS,
        hosts=(HOST,),
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=86400,
    )
    cases = (
        *(
            replace(c, name="growth_" + c.name)
            for c in r.cases("spf_growth:median:RGDP:3")
            if c.expect is None
        ),
        *(
            replace(c, name="price_" + c.name)
            for c in r.cases("rtd:P")
            if c.expect is None
        ),
        *(
            replace(c, name="core_price_" + c.name)
            for c in r.cases("rtd:PCONX")
            if c.expect is None
        ),
        *(
            replace(c, name="unemployment_" + c.name)
            for c in r.cases("rtd:RUC")
            if c.expect is None
        ),
        *r.cases("rtd:ROUTPUT", vintages=True),
        *tuple(
            replace(c, name="spf_" + c.name)
            for c in r.cases("spf:median:CPI:3")
            if c.expect is None
        ),
        *tuple(
            replace(c, name="annual_" + c.name)
            for c in r.cases("spf:mean:UNEMP:A")
            if c.expect is None
        ),
        *tuple(
            replace(c, name="long_" + c.name)
            for c in r.cases("spf:median:CPI10")
            if c.expect is None
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Read one matrix or the SPF levels workbook and its release calendar."""
        series_id = r.single(query, self.info.id)
        kind, statistic, variable, _ = selection(series_id)
        if kind == "rtd":
            return (
                Request(
                    host=HOST,
                    path=ROOT
                    + "real-time-data/data-files/xlsx/"
                    + MATRICES[variable][0],
                    series=series_id,
                ),
            )
        return (
            Request(
                host=HOST,
                path=SPF
                + "historical-data/"
                + statistic
                + ("Growth.xlsx" if kind == "spf_growth" else "Level.xlsx"),
                series=series_id,
            ),
            Request(host=HOST, path=SPF + "spf-release-dates.txt", series=series_id),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Map matrix columns or SPF surveys to closed real-time intervals."""
        series_id = r.single(query, self.info.id)
        kind, _, variable, horizon = selection(series_id)
        rows = spreadsheet(
            responses[0].body,
            MATRICES[variable][1] if kind == "rtd" else variable,
            self.info.id,
        )
        if not rows:
            raise SeriesNotFoundError(self.info.id, series_id)
        if kind == "rtd":
            frequency, unit, observations, notes = matrix_rows(rows, variable)
        else:
            frequency, unit, observations, notes = survey_rows(
                rows,
                variable,
                horizon,
                series_id,
                responses[1].body,
            )
        if kind != "rtd":
            # 1990Q2 and Q3 were released together; the later survey supersedes
            # the earlier annual forecast on that same publication day.
            latest = {(d, v): x for d, v, x in observations}
            observations = [(d, v, x) for (d, v), x in latest.items()]
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=series_id,
            title=variable,
            unit=unit,
            frequency=frequency,
            seasonal_adjustment=(
                SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE
                if unit.kind is UnitKind.MONEY
                or kind == "spf_growth"
                or variable == "HOUSING"
                else SeasonalAdjustment.SEASONALLY_ADJUSTED
                if kind == "rtd" or variable in {"EMP", "INDPROD", "PGDP", "UNEMP"}
                else SeasonalAdjustment.NOT_APPLICABLE
            ),
            source_dating=DateConvention.PERIOD_END,
            terms=TERMS,
            notes=notes,
        )
        return r.frame(observations, meta, query)

    def parse_vintages(
        self, responses: Sequence[Response], series_id: str
    ) -> Sequence[dt.date]:
        """List source publication dates without truncating the matrix to a frame."""
        kind, _, variable, horizon = selection(series_id)
        rows = spreadsheet(
            responses[0].body,
            MATRICES[variable][1] if kind == "rtd" else variable,
            self.info.id,
        )
        if not rows:
            return ()
        if kind == "rtd":
            _, _, observations, _ = matrix_rows(rows, variable)
        else:
            _, _, observations, _ = survey_rows(
                rows,
                variable,
                horizon,
                series_id,
                responses[1].body,
            )
        return sorted({published for _, published, _ in observations})

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep minimal real layouts, replacing every observed forecast or level."""
        kind, _, variable, _ = selection(request.series or "")
        if request.path.endswith(".txt"):
            return response
        sheet = MATRICES[variable][1] if kind == "rtd" else variable
        rows = spreadsheet(response.body, sheet, self.info.id)
        header = rows[0]
        kept = rows[-3:]
        if kind == "rtd":
            positions = [0, *range(max(1, len(header) - 3), len(header))]
        else:
            positions = list(range(len(header)))
        out = [tuple(header[j] for j in positions)]
        for i, row in enumerate(kept):
            out.append(
                tuple(
                    row[j]
                    if j < (1 if kind == "rtd" else 2)
                    or row[j] in {None, -99, -999, "NA", "N/A", "-99", "-999", "."}
                    or (isinstance(row[j], str) and row[j].startswith("#"))
                    else synthetic_value(seed, i * len(header) + j)
                    for j in positions
                )
            )
        return replace(response, body=workbook({sheet: tuple(out)}))
