# src/pyeconomics/data/providers/census.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Census: the US Census Bureau's Data API.

Every query carries the user's key (``key``, attached by the transport): since
May 2026 the Census Data API requires one on every data query. A series id
names the dataset and the variable, separated by ``/``:

- ``acs/acs1/<variable>``, ``acs/acs5/<variable>`` (and their ``subject`` and
  ``profile`` tables, ``acs/acs5/profile/<variable>``): an American Community
  Survey estimate, one request per year of the query (1-year 2005 on, 5-year
  2009 on; no standard 1-year release exists for 2020), for one place;
- ``eits/<program>/<category>/<data type>/<yes|no>``: an Economic Indicators
  time series, such as ``eits/marts/44X72/SM/yes`` (retail sales, seasonally
  adjusted), monthly or quarterly;
- ``intltrade/<exports|imports>/hs/<country code>``: the monthly total value
  of US goods exports to, or general imports from, a country (``-`` for all).

The place is :class:`CensusQuery`'s ``geography`` and ``within``, checked
against an allowlist of geography levels and numeric codes, never passed
through raw.

- **Values.** The API answers with an array of rows whose first row names the
  columns, every value text. ACS's annotation values (-666666666,
  -999999999, -888888888, -222222222, -333333333) and ``null`` are missing; a
  margin of error of -555555555 is controlled, so it is zero. Each is noted.
- **Errors.** Census answers a missing or refused key with a redirect to a
  page that echoes the request, key included; the provider follows no
  redirect, so the key never leaves again, and maps it to
  :class:`~pyeconomics.data.errors.CredentialError`. An unknown variable is
  HTTP 400 and no data HTTP 204.
- **Terms** (https://www.census.gov/data/developers/about/terms-of-service.html,
  read 2026-10-15; last revised 2026-04-14): any service may use the API and
  shows Census's notice; ``hosted-safe``. Census publishes no rate limit, so the
  provider holds itself to five requests a second and 500 a day.

Examples
--------
>>> Census.info.id, Census.info.follow_redirects
('census', False)
>>> CensusQuery(series=("acs/acs1/B19013_001E",), geography="state:06").geography
'state:06'

"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any, Final

from pydantic import field_validator

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    CredentialError,
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
)
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Authentication,
    Capability,
    Case,
    DataProvider,
    KeyPlacement,
    ProviderInfo,
    Query,
    RateLimit,
)
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

__all__ = ["Census"]

_ID: Final = "census"
HOST: Final = "api.census.gov"
#: The notice Census's terms of service require, verbatim.
CENSUS_NOTICE: Final = (
    "This product uses the Census Bureau Data API but is not endorsed or "
    "certified by the Census Bureau."
)
CENSUS_TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.census.gov/data/developers/about/terms-of-service.html",
    checked=dt.date(2026, 10, 15),
    attribution="Source: U.S. Census Bureau.",
    notice=CENSUS_NOTICE,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
#: The geography levels a query may name, as the API spells them.
GEOGRAPHY_LEVELS: Final = (
    "us",
    "region",
    "division",
    "state",
    "county",
    "county subdivision",
    "place",
    "tract",
    "block group",
    "metropolitan statistical area/micropolitan statistical area",
    "combined statistical area",
    "congressional district",
    "public use microdata area",
    "zip code tabulation area",
)
_CLAUSE: Final = re.compile(
    rf"({'|'.join(re.escape(level) for level in GEOGRAPHY_LEVELS)}):(\d{{1,7}})"
)
_ACS: Final = re.compile(
    r"acs/(acs1|acs5)(?:/(subject|profile))?/([A-Z][A-Z0-9_]{1,31})"
)
_EITS: Final = re.compile(
    r"eits/([a-z0-9]{2,12})/([A-Za-z0-9_]{1,24})/([A-Za-z0-9_]{1,24})/(yes|no)"
)
_TRADE: Final = re.compile(r"intltrade/(exports|imports)/hs/(\d{4}|-)")
_ACS_FIRST: Final = {"acs1": 2005, "acs5": 2009}
_ACS_GAPS: Final = {"acs1": frozenset({2020})}
#: ACS's annotation values for an estimate it cannot give (Census's notes).
_ANNOTATIONS: Final = {
    -666666666.0: "too few sample observations to compute",
    -999999999.0: "too few sample cases to display",
    -888888888.0: "not applicable or not available",
    -222222222.0: "margin of error not computable (too few observations)",
    -333333333.0: "margin of error not computable (open-ended median)",
}
_CONTROLLED: Final = -555555555.0
_TRADE_VALUES: Final = {"exports": "ALL_VAL_MO", "imports": "GEN_VAL_MO"}
_MONTH: Final = re.compile(r"(\d{4})-(\d{2})")
_QUARTER: Final = re.compile(r"(\d{4})-Q([1-4])")


class CensusQuery(Query):
    """A query with the place it is about.

    ``geography`` is one place, ``<level>:<code>`` (``us:1``, ``state:06``,
    ``county:037``); ``within`` its parents, such as ``state:06`` for a county,
    several separated by a space. Levels come from :data:`GEOGRAPHY_LEVELS` and
    codes are digits, so nothing a caller writes reaches the request raw.
    """

    geography: str = "us:1"
    within: str | None = None

    @field_validator("geography")
    @classmethod
    def _one_place(cls, value: str) -> str:
        if not _CLAUSE.fullmatch(value):
            msg = (
                "geography is one place, <level>:<digits>, with a level the "
                "Census API names (us, state, county ...)"
            )
            raise ValueError(msg)
        return value

    @field_validator("within")
    @classmethod
    def _parents(cls, value: str | None) -> str | None:
        if value is not None and not all(
            _CLAUSE.fullmatch(part) for part in value.split(" ")
        ):
            msg = "within is <level>:<digits> clauses separated by one space"
            raise ValueError(msg)
        return value


def _time(text: str) -> tuple[dt.date, ObservationFrequency]:
    month = _MONTH.fullmatch(text)
    if month:
        return s.month_end(int(month.group(1)), int(month.group(2))), (
            ObservationFrequency.MONTHLY
        )
    quarter = _QUARTER.fullmatch(text)
    if quarter:
        return s.month_end(int(quarter.group(1)), 3 * int(quarter.group(2))), (
            ObservationFrequency.QUARTERLY
        )
    msg = f"census sent a time it does not document: {text[:12]!r}"
    raise ResponseError(msg, provider="census")


def _time_range(query: Query) -> str | None:
    start = (
        f"from {query.start.year:04d}-{query.start.month:02d}" if query.start else ""
    )
    end = f"to {query.end.year:04d}-{query.end.month:02d}" if query.end else ""
    joined = " ".join(part for part in (start, end) if part)
    return joined or None


def _rows(response: Response) -> tuple[list[str], list[list[Any]]]:
    """Read the API's array of rows; the first names the columns."""
    if response.status == 204 or not response.body.strip():  # noqa: PLR2004 - no data
        return [], []
    body = response.json(provider="census")
    if (
        not isinstance(body, list)
        or not body
        or not all(isinstance(row, list) for row in body)
    ):
        msg = "census sent a body that is not an array of rows"
        raise ResponseError(msg, provider="census")
    header = [str(name) for name in body[0]]
    return header, body[1:]


class Census(DataProvider):
    """The Census Data API: ACS, economic indicators and international trade."""

    info = ProviderInfo(
        id="census",
        name="US Census Bureau",
        homepage="https://www.census.gov",
        terms=CENSUS_TERMS,
        auth=Authentication.key("key", KeyPlacement.QUERY),
        hosts=(HOST,),
        # Census publishes no rate limit; these are the provider's own.
        rate_limits=(
            RateLimit(requests=5, per="second"),
            RateLimit(requests=500, per="day"),
        ),
        follow_redirects=False,
        ttl_seconds=6 * 3_600,
    )
    query_type = CensusQuery
    cases = (
        Case(
            name="fetch_acs",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("acs/acs1/B19013_001E",),
                start=dt.date(2022, 1, 1),
                end=dt.date(2024, 12, 31),
                geography="state:06",
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_eits",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("eits/marts/44X72/SM/yes",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2025, 6, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_trade",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("intltrade/exports/hs/5700",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2025, 6, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="error_unauthorized",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("acs/acs1/B19013_001E",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                geography="state:06",
                max_observations=24,
            ),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("acs/acs1/B99999_999E",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                geography="state:06",
                max_observations=24,
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=CensusQuery(
                series=("acs/acs1/B19013_001E",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                geography="state:06",
                max_observations=24,
            ),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """One request per ACS year, or one per time series."""
        place = (
            query
            if isinstance(query, CensusQuery)
            else CensusQuery(**query.model_dump())
        )
        if len(place.series) != 1:
            msg = "census answers one series id per fetch; fetch the others apart"
            raise DataError(msg, provider="census")
        series_id = place.series[0]
        acs = _ACS.fullmatch(series_id)
        if acs:
            return self._acs(acs, place)
        eits = _EITS.fullmatch(series_id)
        if eits:
            program, category, data_type, adjusted = eits.groups()
            params = [
                ("get", "cell_value,time_slot_id,error_data"),
                ("category_code", category),
                ("data_type_code", data_type),
                ("seasonally_adj", adjusted),
                ("for", "us:*"),
            ]
            return (self._timeseries(("eits", program), params, place, series_id),)
        trade = _TRADE.fullmatch(series_id)
        if trade:
            direction, country = trade.groups()
            params = [
                ("get", f"{_TRADE_VALUES[direction]},CTY_NAME"),
                ("CTY_CODE", country),
            ]
            return (
                self._timeseries(
                    ("intltrade", direction, "hs"), params, place, series_id
                ),
            )
        msg = (
            f"{series_id!r} is not a census series id: acs/<acs1|acs5>[/subject|"
            "/profile]/<variable>, eits/<program>/<category>/<data type>/<yes|no> "
            "or intltrade/<exports|imports>/hs/<country code>"
        )
        raise DataError(msg, provider="census")

    def _acs(self, match: re.Match[str], query: CensusQuery) -> tuple[Request, ...]:
        survey, table, variable = match.groups()
        years = acs_years(survey, query)
        params = [("get", f"NAME,{variable}"), ("for", query.geography)]
        if query.within:
            params.append(("in", query.within))
        segments = ("data", "{year}", "acs", survey, *((table,) if table else ()))
        return tuple(
            Request(
                host=HOST,
                path=request_path(
                    *(str(year) if part == "{year}" else part for part in segments)
                ),
                params=tuple(params),
                series=query.series[0],
            )
            for year in years
        )

    def _timeseries(
        self,
        segments: tuple[str, ...],
        params: list[tuple[str, str]],
        query: CensusQuery,
        series_id: str,
    ) -> Request:
        window = _time_range(query)
        if window is None:
            msg = "a census time series query names its start or end"
            raise DataError(msg, provider="census")
        return Request(
            host=HOST,
            path=request_path("data", "timeseries", *segments),
            params=(*params, ("time", window)),
            series=series_id,
        )

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """Map a redirect to a refused key and a 400 to an unknown variable."""
        if 300 <= response.status < 400:  # noqa: PLR2004 - HTTP redirects
            msg = (
                "census refused the request's key: set CENSUS_API_KEY to a key from "
                "api.census.gov/data/key_signup.html"
            )
            return CredentialError(msg, provider="census")
        if response.status == 400:  # noqa: PLR2004 - HTTP bad request
            text = response.body[:512].decode("utf-8", "replace").casefold()
            if "unknown variable" in text or "unknown predicate" in text:
                return SeriesNotFoundError("census", request.series or "unknown")
        return None

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Return a series of one place over time."""
        series_id = query.series[0]
        acs = _ACS.fullmatch(series_id)
        if acs:
            return self._parse_acs(responses, query, acs)
        return self._parse_timeseries(responses, query, series_id)

    def _parse_acs(
        self, responses: Sequence[Response], query: Query, match: re.Match[str]
    ) -> Series:
        survey, _, variable = match.groups()
        values: dict[dt.date, float | None] = {}
        annotated: dict[str, list[dt.date]] = {}
        place = ""
        for response, year in zip(responses, acs_years(survey, query), strict=True):
            header, rows = _rows(response)
            day = dt.date(year, 12, 31)
            if not rows:
                continue
            if variable not in header:
                raise SeriesNotFoundError(_ID, query.series[0])
            row = rows[0]
            place = str(row[header.index("NAME")]) if "NAME" in header else place
            values[day] = _annotated(
                row[header.index(variable)], variable, day, annotated
            )
        if not values:
            raise SeriesNotFoundError(_ID, query.series[0])
        days = sorted(values)
        notes = [
            s.dates_note("annotation", label, sorted(found))
            for label, found in sorted(annotated.items())
        ]
        meta = SeriesMeta(
            provider="census",
            series_id=query.series[0],
            dataset=f"acs/{survey}",
            title=f"{variable}, {place}"[:256] if place else variable,
            unit=UnitRecord(text="As published by the Census Bureau"),
            frequency=ObservationFrequency.ANNUAL,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_END,
            terms=CENSUS_TERMS,
            notes=tuple(notes),
        )
        return Series(tuple(days), tuple(values[day] for day in days), meta)

    def _parse_timeseries(
        self, responses: Sequence[Response], query: Query, series_id: str
    ) -> Series:
        header, rows = _rows(responses[0])
        if not rows:
            raise SeriesNotFoundError(_ID, series_id)
        trade = _TRADE.fullmatch(series_id)
        column = _TRADE_VALUES[trade.group(1)] if trade else "cell_value"
        if column not in header or "time" not in header:
            msg = f"census sent no {column} or time column"
            raise ResponseError(msg, provider="census")
        values: dict[dt.date, float | None] = {}
        frequencies = set()
        for row in rows:
            day, frequency = _time(str(row[header.index("time")]))
            frequencies.add(frequency)
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            values[day] = s.number(row[header.index(column)], "census")
        if len(frequencies) > 1:
            msg = "census sent periods of more than one frequency for one series"
            raise ResponseError(msg, provider="census")
        frequency = frequencies.pop()
        days = sorted(values)
        if trade:
            unit = UnitRecord(text="US dollars", kind=UnitKind.MONEY, currency="USD")
            adjustment = SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
            title = f"US goods {trade.group(1)}, country code {trade.group(2)}"
            dataset = f"intltrade/{trade.group(1)}/hs"
        else:
            eits = _EITS.fullmatch(series_id)
            program, category, data_type, adjusted = eits.groups()  # type: ignore[union-attr]
            unit = UnitRecord(text=f"Census data type {data_type}")
            adjustment = (
                SeasonalAdjustment.SEASONALLY_ADJUSTED
                if adjusted == "yes"
                else SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
            )
            title = f"{program} {category} {data_type}"
            dataset = f"eits/{program}"
        meta = SeriesMeta(
            provider="census",
            series_id=series_id,
            dataset=dataset,
            title=title,
            unit=unit,
            frequency=frequency,
            seasonal_adjustment=adjustment,
            source_dating=DateConvention.PERIOD_START,
            terms=CENSUS_TERMS,
        )
        return Series(tuple(days), tuple(values[day] for day in days), meta)


def acs_years(survey: str, query: Query) -> list[int]:
    """Return the years an ACS query reads: one request each, in order.

    The survey's first year bounds them, and a year with no standard release
    (the 1-year ACS of 2020) is skipped.

    Raises
    ------
    DataError
        Without both dates, or when no release falls between them.
    """
    if query.start is None or query.end is None:
        msg = "an ACS query names its years: give start and end"
        raise DataError(msg, provider="census")
    years = [
        year
        for year in range(max(query.start.year, _ACS_FIRST[survey]), query.end.year + 1)
        if year not in _ACS_GAPS.get(survey, frozenset())
    ]
    if not years:
        msg = f"the ACS {survey} has no release in the years asked for"
        raise DataError(msg, provider="census")
    return years


def _annotated(
    raw: object, variable: str, day: dt.date, annotated: dict[str, list[dt.date]]
) -> float | None:
    value = s.number(raw, "census") if raw is not None else None
    if raw is None:
        annotated.setdefault("null: no data for this geography", []).append(day)
        return None
    if value == _CONTROLLED and variable.endswith("M"):
        annotated.setdefault("-555555555: controlled, margin of error zero", []).append(
            day
        )
        return 0.0
    if value in _ANNOTATIONS:
        annotated.setdefault(f"{int(value)}: {_ANNOTATIONS[value]}", []).append(day)
        return None
    return value
