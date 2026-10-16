# src/pyeconomics/data/providers/fred.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""FRED and ALFRED: the Federal Reserve Bank of St. Louis's economic data.

One provider, ``fred``, reads both: FRED's current values and ALFRED's
vintages, which are the same API with real-time parameters.

- **v1** (``api.stlouisfed.org/fred/...``), the key in the ``api_key`` query
  parameter: series metadata (``fred/series``), its tags (``fred/series/tags``),
  observations (``fred/series/observations``), search (``fred/series/search``)
  and the dates a series changed (``fred/series/vintagedates``).
- **Vintages.** ``latest`` reads FRED's current values. ``all``, ``as_of`` and
  ``first_release`` read every real-time period from 1776-07-04 to 9999-12-31
  (``output_type=1``, observations by real-time period); each row carries its
  :class:`~pyeconomics.core.provenance.RealtimePeriod`, and the base class
  selects the vintage the query names.
- **v2 bulk.** A query whose first id is ``release:<release_id>`` reads a whole
  release in one paged request (``fred/v2/release/observations``), the key in
  an ``Authorization: Bearer`` header as FRED's v2 requires, and returns a
  table: every series of the release, or the ids that follow the release.
- **Conventions.** FRED dates a month, quarter, half-year or year by its first
  day; the provider indexes it by its last (``source_dating`` records
  ``period_start``). A ``.`` is a missing value. A series in percent becomes a
  decimal through ``percent_to_decimal``.
- **Terms** (https://fred.stlouisfed.org/legal/, read 2026-10-15). FRED is
  ``library-only``: its terms forbid storing, caching or archiving any FRED
  content (prohibition (l)), so the provider has no cache path, and forbid
  using it for the development or training of machine-learning systems,
  large language models included (prohibition (k)), so ``llm_use`` is
  ``forbidden``. Every application shows FRED's notice. A series' copyright
  tags set its notice and its redistribution status: a ``copyrighted:
  pre-approval required`` series, and every series sourced from Moody's
  whatever its tag, needs its owner's written permission beyond personal use
  (ROADMAP section 5, "Data terms").

Examples
--------
>>> Fred.info.id, Fred.info.terms.licence.value, Fred.info.terms.cache.value
('fred', 'library-only', 'forbidden')
>>> [request.path for request in Fred().build_requests(Query(series=("GDPC1",)))]
['/fred/series', '/fred/series/tags', '/fred/series/observations']

"""

from __future__ import annotations

import datetime as dt
import json
import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse, RealtimePeriod
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
    KeySlot,
    ProviderInfo,
    Query,
    RateLimit,
    SearchHit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, request_path
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.types import (
    ColumnMeta,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    TableMeta,
    UnitRecord,
    Weekday,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["Fred"]

HOST: Final = "api.stlouisfed.org"
#: The notice FRED's terms require wherever its data appear, verbatim.
FRED_NOTICE: Final = (
    "This product uses the FRED® API but is not endorsed or certified by the "
    "Federal Reserve Bank of St. Louis."
)
FRED_TERMS: Final = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://fred.stlouisfed.org/legal/",
    checked=dt.date(2026, 10, 15),
    attribution="Source: Federal Reserve Bank of St. Louis, FRED®.",
    notice=FRED_NOTICE,
    llm_use=LlmUse.FORBIDDEN,
    cache=CachePolicy.FORBIDDEN,
)
#: ALFRED's whole real-time range: its first and its "still current" dates.
REALTIME_ORIGIN: Final = "1776-07-04"
REALTIME_CURRENT: Final = "9999-12-31"
#: The prefix of a v2 bulk query's first id: ``release:<release_id>``.
RELEASE_PREFIX: Final = "release:"
_RELEASE: Final = re.compile(r"release:([1-9][0-9]{0,8})")
_MISSING: Final = (".",)
_V1_LIMIT: Final = 100_000
_V2_PAGE: Final = 500_000
_SEARCH_NOTES: Final = 160
_MAX_CURSOR: Final = 256
#: The most rows of one list a synthetic cassette keeps (the Recording rule).
_KEPT: Final = 24
_PER_SERIES: Final = 3  # series, tags, observations
_FREQUENCIES: Final = {
    "D": ObservationFrequency.DAILY,
    "W": ObservationFrequency.WEEKLY,
    "BW": ObservationFrequency.BIWEEKLY,
    "M": ObservationFrequency.MONTHLY,
    "Q": ObservationFrequency.QUARTERLY,
    "SA": ObservationFrequency.SEMIANNUAL,
    "A": ObservationFrequency.ANNUAL,
}
_FREQUENCY_NAMES: Final = {
    "Daily": "D",
    "Weekly": "W",
    "Biweekly": "BW",
    "Monthly": "M",
    "Quarterly": "Q",
    "Semiannual": "SA",
    "Annual": "A",
}
_ADJUSTMENTS: Final = {
    "SA": SeasonalAdjustment.SEASONALLY_ADJUSTED,
    "SSA": SeasonalAdjustment.SEASONALLY_ADJUSTED,
    "SAAR": SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
    "NSA": SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
    "NA": SeasonalAdjustment.NOT_APPLICABLE,
}
_ADJUSTMENT_NAMES: Final = {
    "Seasonally Adjusted": "SA",
    "Smoothed Seasonally Adjusted": "SSA",
    "Seasonally Adjusted Annual Rate": "SAAR",
    "Not Seasonally Adjusted": "NSA",
    "Not Applicable": "NA",
}
_SCALES: Final = {"Thousands": 1e3, "Millions": 1e6, "Billions": 1e9, "Trillions": 1e12}
_DOLLARS: Final = re.compile(
    r"(?:(Thousands|Millions|Billions|Trillions) of )?"
    r"(?:Chained \d{4} |Real \d{4} )?(?:U\.S\. )?Dollars"
)
_PERSONS: Final = re.compile(r"(?:(Thousands|Millions) of )?(?:Persons|Units|Number)")
#: FRED's "Citation & Copyright" tags (group ``cc``), lower case as the API sends them.
PRE_APPROVAL: Final = "copyrighted: pre-approval required"
CITATION_REQUIRED: Final = "copyrighted: citation required"
PUBLIC_DOMAIN: Final = "public domain: citation requested"
_PRE_APPROVAL_NOTICE: Final = (
    f"{FRED_NOTICE} This series is copyrighted by a third party: any use beyond "
    "personal use needs the copyright holder's written permission (FRED's "
    "copyrighted: pre-approval required)."
)
_CITATION_NOTICE: Final = (
    f"{FRED_NOTICE} This series is copyrighted by a third party: cite the "
    "copyright holder its notes name (FRED's copyrighted: citation required)."
)


def _unit(units: str) -> tuple[UnitRecord, bool]:
    """Read FRED's unit text: the record, and whether values are percent."""
    lowered = units.casefold()
    if "percent" in lowered or "basis points" in lowered:
        # A percent (a level, a change or a share) and a percentage point are
        # decimals here (ADR-0008 decision 1); basis points stay as published.
        if "basis points" in lowered:
            return UnitRecord(text=units), False
        return UnitRecord(text=units, kind=UnitKind.RATE), True
    dollars = _DOLLARS.fullmatch(units)
    if dollars:
        scale = _SCALES.get(dollars.group(1) or "", 1.0)
        return UnitRecord(
            text=units, kind=UnitKind.MONEY, scale=scale, currency="USD"
        ), False
    persons = _PERSONS.fullmatch(units)
    if persons:
        scale = _SCALES.get(persons.group(1) or "", 1.0)
        return UnitRecord(text=units, kind=UnitKind.COUNT, scale=scale), False
    if lowered.startswith("index"):
        return UnitRecord(text=units, kind=UnitKind.INDEX_LEVEL), False
    return UnitRecord(text=units), False


def _code(value: str, names: dict[str, str]) -> str:
    """Return a short code from either the code itself or FRED's long name."""
    return names.get(value, value)


def _frequency(entry: dict[str, Any]) -> tuple[ObservationFrequency, str]:
    """Return a series' frequency and FRED's long text for it."""
    long = s.text(entry, "frequency", "fred")
    short = entry.get("frequency_short")
    code = short if isinstance(short, str) and short else long.split(",")[0]
    found = _FREQUENCIES.get(_code(code.strip(), _FREQUENCY_NAMES))
    return (found or ObservationFrequency.IRREGULAR), long


def _adjustment(entry: dict[str, Any]) -> SeasonalAdjustment:
    short = entry.get("seasonal_adjustment_short")
    code = (
        short
        if isinstance(short, str) and short
        else s.text(entry, "seasonal_adjustment", "fred")
    )
    found = _ADJUSTMENTS.get(_code(code.strip(), _ADJUSTMENT_NAMES))
    if found is None:
        msg = f"fred sent a seasonal adjustment it does not document: {code[:24]!r}"
        raise ResponseError(msg, provider="fred")
    return found


def _weekday(long: str, days: Sequence[dt.date]) -> Weekday | None:
    """Return the weekday a weekly series' periods end on, from text or dates."""
    for day in Weekday:
        if day.value.title() in long:
            return day
    if days:
        return tuple(Weekday)[days[0].weekday()]
    return Weekday.FRIDAY


def _day(raw: object) -> dt.date:
    try:
        return dt.date.fromisoformat(str(raw))
    except ValueError:
        msg = "fred sent a date that is not YYYY-MM-DD"
        raise ResponseError(msg, provider="fred") from None


def _realtime(row: dict[str, Any]) -> RealtimePeriod:
    end = row.get("realtime_end")
    return RealtimePeriod(
        _day(row.get("realtime_start")),
        None if end == REALTIME_CURRENT else _day(end),
    )


def copyright_terms(
    tags: Sequence[object], notes: str
) -> tuple[Terms, tuple[str, ...]]:
    """Return a series' terms and notes from its tags (ADR-0011 decision 7).

    A ``copyrighted: pre-approval required`` tag, or any Moody's source tag
    whatever the series' own label, makes the notice say that use beyond
    personal use needs the owner's permission; ``copyrighted: citation
    required`` (or "Copyright" in the series' notes, FRED's other marker) says
    to cite the owner. A public-domain series keeps FRED's own notice.

    Examples
    --------
    >>> terms, notes = copyright_terms(
    ...     [{"name": "moody's", "group_id": "src"}], "Copyright, Moody's."
    ... )
    >>> notes[0]
    'copyright: pre-approval required'

    """
    names = {
        str(tag.get("name", "")).casefold()
        for tag in tags
        if isinstance(tag, dict) and tag.get("group_id") == "cc"
    }
    moodys = any(
        isinstance(tag, dict)
        and tag.get("group_id") == "src"
        and "moody" in str(tag.get("name", "")).casefold()
        for tag in tags
    )
    if PRE_APPROVAL in names or moodys:
        found: tuple[str, ...] = ("copyright: pre-approval required",)
        if moodys:
            found += ("moodys: Moody's series count as pre-approval required",)
        return FRED_TERMS.with_overrides(notice=_PRE_APPROVAL_NOTICE), found
    if CITATION_REQUIRED in names or (
        PUBLIC_DOMAIN not in names and "copyright" in notes.casefold()
    ):
        return FRED_TERMS.with_overrides(notice=_CITATION_NOTICE), (
            "copyright: citation required",
        )
    if PUBLIC_DOMAIN in names:
        return FRED_TERMS, ("copyright: public domain, citation requested",)
    return FRED_TERMS, ()


class Fred(DataProvider):
    """FRED and ALFRED (see the module docstring)."""

    info = ProviderInfo(
        id="fred",
        name="FRED and ALFRED, Federal Reserve Bank of St. Louis",
        homepage="https://fred.stlouisfed.org",
        terms=FRED_TERMS,
        capabilities=(
            Capability.FETCH,
            Capability.SEARCH,
            Capability.DESCRIBE,
            Capability.VINTAGES,
            Capability.BULK,
        ),
        auth=Authentication.key(
            "api_key",
            KeyPlacement.QUERY,
            alternates=(KeySlot(KeyPlacement.HEADER, "Authorization", "Bearer"),),
        ),
        hosts=(HOST,),
        # v1 allows 120 requests a minute, v2 2 a second (FRED's error pages).
        rate_limits=(
            RateLimit(requests=2, per="second"),
            RateLimit(requests=120, per="minute"),
        ),
    )
    cases = (
        Case(
            name="fetch_ok",
            operation=Capability.FETCH,
            argument=Query(
                series=("UNRATE",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_table",
            operation=Capability.FETCH,
            argument=Query(
                series=("UNRATE", "CIVPART"),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_vintages",
            operation=Capability.FETCH,
            argument=Query(
                series=("A191RL1Q225SBEA",),
                start=dt.date(2023, 7, 1),
                end=dt.date(2023, 9, 30),
                vintage="all",
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_copyrighted",
            operation=Capability.FETCH,
            argument=Query(
                series=("BAA",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 6, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="search_ok",
            operation=Capability.SEARCH,
            argument="civilian unemployment rate",
        ),
        Case(
            name="fetch_release",
            operation=Capability.FETCH,
            argument=Query(series=("release:89",), max_observations=24),
        ),
        Case(name="describe_ok", operation=Capability.DESCRIBE, argument="GDPC1"),
        Case(
            name="vintages_ok",
            operation=Capability.VINTAGES,
            argument="A191RL1Q225SBEA",
        ),
        Case(
            name="error_unauthorized",
            operation=Capability.FETCH,
            argument=Query(series=("UNRATE",), max_observations=24),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(series=("NOSUCHSERIES1",), max_observations=24),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(series=("UNRATE",), max_observations=24),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    # --- fetch -------------------------------------------------------------------

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Three v1 requests per series, or one paged v2 request for a release."""
        release = _RELEASE.fullmatch(query.series[0])
        if release is not None:
            return (self._release_request(release.group(1), None),)
        if any(series_id.startswith(RELEASE_PREFIX) for series_id in query.series):
            msg = "a release id comes first in a query, and only once"
            raise DataError(msg, provider="fred")
        if len(query.series) > 1 and query.vintage != "latest":
            msg = "fetch one series at a time for its vintages"
            raise DataError(msg, provider="fred")
        return tuple(
            request
            for series_id in query.series
            for request in self._series_requests(series_id, query)
        )

    def _series_requests(self, series_id: str, query: Query) -> tuple[Request, ...]:
        plain = (("series_id", series_id), ("file_type", "json"))
        window: list[tuple[str, str]] = []
        if query.start is not None:
            # FRED dates a period by its first day, and every period is calendar
            # aligned, so the period holding the start began on or after 1
            # January: ask from there and keep the periods that end in range.
            window.append(("observation_start", f"{query.start.year:04d}-01-01"))
        if query.end is not None:
            window.append(("observation_end", query.end.isoformat()))
        if query.vintage == "latest":
            rows = [("sort_order", "desc"), ("limit", str(query.max_observations))]
            if query.start is not None or query.end is not None:
                rows = [("limit", str(_V1_LIMIT))]
        else:
            rows = [
                ("realtime_start", REALTIME_ORIGIN),
                ("realtime_end", REALTIME_CURRENT),
                ("output_type", "1"),
                ("limit", str(_V1_LIMIT)),
            ]
        return (
            Request(
                host=HOST,
                path=request_path("fred", "series"),
                params=plain,
                series=series_id,
            ),
            Request(
                host=HOST,
                path=request_path("fred", "series", "tags"),
                params=plain,
                series=series_id,
            ),
            Request(
                host=HOST,
                path=request_path("fred", "series", "observations"),
                params=(*plain, *window, *rows),
                series=series_id,
            ),
        )

    def _release_request(self, release_id: str, cursor: str | None) -> Request:
        params = [
            ("release_id", release_id),
            ("format", "json"),
            ("limit", str(_V2_PAGE)),
        ]
        if cursor is not None:
            params.append(("next_cursor", cursor))
        return Request(
            host=HOST,
            path=request_path("fred", "v2", "release", "observations"),
            params=tuple(params),
            series=f"{RELEASE_PREFIX}{release_id}",
            key_placement=KeyPlacement.HEADER.value,
        )

    def next_page(self, request: Request, response: Response) -> Request | None:
        """Follow v2's cursor while ``has_more`` says another page waits."""
        if not request.path.startswith("/fred/v2/"):
            return None
        body = s.body_object(response, "fred")
        more = body.get("has_more")
        if more not in {True, "true"}:
            return None
        cursor = body.get("next_cursor")
        if not isinstance(cursor, str) or not cursor or len(cursor) > _MAX_CURSOR:
            msg = "fred said more pages follow but sent no cursor"
            raise ResponseError(msg, provider="fred")
        release = dict(request.params)["release_id"]
        return self._release_request(release, cursor)

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Return a series per id (a table for several), or a release's table."""
        release = _RELEASE.fullmatch(query.series[0])
        if release is not None:
            return self._release_table(responses, query, release.group(1))
        frames = [
            self._series(responses[i * _PER_SERIES : (i + 1) * _PER_SERIES], query)
            for i in range(len(query.series))
        ]
        if len(frames) == 1:
            return frames[0]
        return _table(frames, "+".join(query.series)[:128], "FRED series")

    def _meta(
        self, responses: Sequence[Response]
    ) -> tuple[dict[str, Any], Terms, tuple[str, ...]]:
        series = s.items(
            s.body_object(responses[0], "fred").get("seriess"), "fred", "series"
        )
        if not series or not isinstance(series[0], dict):
            msg = "fred sent no series"
            raise ResponseError(msg, provider="fred")
        entry = series[0]
        tags = s.items(s.body_object(responses[1], "fred").get("tags"), "fred", "tags")
        notes = entry.get("notes")
        terms, found = copyright_terms(tags, notes if isinstance(notes, str) else "")
        return entry, terms, found

    def _series(self, responses: Sequence[Response], query: Query) -> Series:
        entry, terms, notes = self._meta(responses)
        series_id = s.text(entry, "id", "fred")
        frequency, long = _frequency(entry)
        unit, percent = _unit(s.text(entry, "units", "fred"))
        rows = s.items(
            s.body_object(responses[2], "fred").get("observations"),
            "fred",
            "observations",
        )
        vintages = query.vintage != "latest"
        kept: list[tuple[dt.date, RealtimePeriod | None, float | None]] = []
        for row in rows:
            if not isinstance(row, dict):
                msg = "fred sent an observation that is not an object"
                raise ResponseError(msg, provider="fred")
            day = s.period_end(_day(row.get("date")), frequency)
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            value = s.rate_or_value(
                s.number(row.get("value"), "fred", missing=_MISSING), percent=percent
            )
            kept.append((day, _realtime(row) if vintages else None, value))
        kept.sort(
            key=lambda item: (
                item[0],
                item[1].realtime_start if item[1] else dt.date.min,
            )
        )
        days = [day for day, _, _ in kept]
        meta = SeriesMeta(
            provider="fred",
            series_id=series_id,
            title=s.text(entry, "title", "fred"),
            unit=unit,
            frequency=frequency,
            week_ends_on=_weekday(long, days) if frequency.needs_weekday else None,
            seasonal_adjustment=_adjustment(entry),
            source_dating=_dating(frequency),
            terms=terms,
            notes=notes,
        )
        realtime = (
            tuple(period for _, period, _ in kept if period) if vintages else None
        )
        return Series(tuple(days), tuple(value for _, _, value in kept), meta, realtime)

    def _release_table(
        self, responses: Sequence[Response], query: Query, release_id: str
    ) -> Table:
        wanted = query.series[1:]
        found: dict[str, dict[str, Any]] = {}
        title = f"FRED release {release_id}"
        for response in responses:
            body = s.body_object(response, "fred")
            release = body.get("release")
            if isinstance(release, dict) and isinstance(release.get("name"), str):
                title = release["name"][:200]
            for entry in s.items(body.get("series"), "fred", "series"):
                if not isinstance(entry, dict):
                    continue
                series_id = s.text(entry, "series_id", "fred")
                if wanted and series_id not in wanted:
                    continue
                kept = found.setdefault(series_id, {**entry, "observations": []})
                kept["observations"].extend(
                    s.items(entry.get("observations"), "fred", "observations")
                )
        missing = [series_id for series_id in wanted if series_id not in found]
        if missing:
            raise SeriesNotFoundError(Fred.info.id, missing[0])
        frames = [self._bulk_series(entry, query) for entry in found.values()]
        if not frames:
            msg = f"fred's release {release_id} holds no series"
            raise ResponseError(msg, provider="fred")
        return _table(frames, f"{RELEASE_PREFIX}{release_id}", title)

    def _bulk_series(self, entry: dict[str, Any], query: Query) -> Series:
        """One series of a v2 release, which carries no tags: FRED's own terms."""
        frequency, long = _frequency(entry)
        unit, percent = _unit(s.text(entry, "units", "fred"))
        pairs = sorted(
            (
                s.period_end(_day(row.get("date")), frequency),
                s.rate_or_value(
                    s.number(row.get("value"), "fred", missing=_MISSING),
                    percent=percent,
                ),
            )
            for row in entry["observations"]
            if isinstance(row, dict)
        )
        pairs = [
            pair
            for pair in pairs
            if not (query.start and pair[0] < query.start)
            and not (query.end and pair[0] > query.end)
        ]
        # v2 sends the series' "Citation & Copyright" tag as copyright_id, and no
        # source tags: a Moody's series is known by its notes.
        notes = entry.get("notes")
        text = notes if isinstance(notes, str) else ""
        tags: list[dict[str, str]] = []
        if isinstance(entry.get("copyright_id"), str):
            tags.append({"group_id": "cc", "name": entry["copyright_id"]})
        if "moody" in text.casefold():
            tags.append({"group_id": "src", "name": "moody's"})
        terms, found = copyright_terms(tags, text)
        meta = SeriesMeta(
            provider="fred",
            series_id=s.text(entry, "series_id", "fred"),
            title=s.text(entry, "title", "fred"),
            unit=unit,
            frequency=frequency,
            week_ends_on=_weekday(long, [day for day, _ in pairs])
            if frequency.needs_weekday
            else None,
            seasonal_adjustment=_adjustment(entry),
            source_dating=_dating(frequency),
            terms=terms,
            notes=found,
        )
        return Series(tuple(day for day, _ in pairs), tuple(v for _, v in pairs), meta)

    # --- search, describe, vintages ---------------------------------------------

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        """One v1 series search."""
        return (
            Request(
                host=HOST,
                path=request_path("fred", "series", "search"),
                params=(
                    ("search_text", text),
                    ("limit", str(limit)),
                    ("file_type", "json"),
                ),
            ),
        )

    def parse_search(
        self,
        responses: Sequence[Response],
        text: str,  # noqa: ARG002 - the hook's signature
        limit: int,
    ) -> Sequence[SearchHit]:
        """Return hits from the ``seriess`` list."""
        body = s.body_object(responses[0], "fred")
        hits = []
        for entry in s.items(body.get("seriess"), "fred", "series")[:limit]:
            frequency, _ = _frequency(entry)
            hits.append(
                SearchHit(
                    series_id=s.text(entry, "id", "fred"),
                    title=s.text(entry, "title", "fred")[:256],
                    frequency=frequency,
                    unit=s.text(entry, "units", "fred")[:256],
                )
            )
        return hits

    def build_describe(self, series_id: str) -> Sequence[Request]:
        """Ask for the series' metadata and its tags."""
        plain = (("series_id", series_id), ("file_type", "json"))
        return (
            Request(
                host=HOST,
                path=request_path("fred", "series"),
                params=plain,
                series=series_id,
            ),
            Request(
                host=HOST,
                path=request_path("fred", "series", "tags"),
                params=plain,
                series=series_id,
            ),
        )

    def parse_describe(
        self,
        responses: Sequence[Response],
        series_id: str,  # noqa: ARG002 - the hook's signature
    ) -> SeriesMeta:
        """Return the series' metadata, with its copyright terms."""
        entry, terms, notes = self._meta(responses)
        frequency, long = _frequency(entry)
        unit, _ = _unit(s.text(entry, "units", "fred"))
        return SeriesMeta(
            provider="fred",
            series_id=s.text(entry, "id", "fred"),
            title=s.text(entry, "title", "fred"),
            unit=unit,
            frequency=frequency,
            week_ends_on=_weekday(long, ()) if frequency.needs_weekday else None,
            seasonal_adjustment=_adjustment(entry),
            source_dating=_dating(frequency),
            terms=terms,
            notes=notes,
        )

    def build_vintages(self, series_id: str) -> Sequence[Request]:
        """Ask for the dates the series changed (ALFRED's vintage dates)."""
        return (
            Request(
                host=HOST,
                path=request_path("fred", "series", "vintagedates"),
                params=(
                    ("series_id", series_id),
                    ("file_type", "json"),
                    ("limit", "10000"),
                ),
                series=series_id,
            ),
        )

    def parse_vintages(
        self,
        responses: Sequence[Response],
        series_id: str,  # noqa: ARG002 - the hook's signature
    ) -> Sequence[dt.date]:
        """Return the vintage dates, oldest first."""
        body = s.body_object(responses[0], "fred")
        return sorted(
            {
                _day(raw)
                for raw in s.items(body.get("vintage_dates"), "fred", "vintage dates")
            }
        )

    # --- errors and recording -----------------------------------------------------

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """Map v1's HTTP 400 messages: a refused key, an unknown series."""
        if response.status != 400:  # noqa: PLR2004 - FRED's "Bad Request"
            return None
        try:
            body = response.json(provider="fred")
        except ResponseError:
            return None
        message = ""
        if isinstance(body, dict):
            message = str(body.get("error_message") or body.get("message") or "")
        lowered = message.casefold()
        if "api_key" in lowered or "api key" in lowered:
            text = (
                "fred refused the key (HTTP 400): set FRED_API_KEY to a key "
                "registered at fredaccount.stlouisfed.org"
            )
            return CredentialError(text, provider="fred")
        if "does not exist" in lowered or "not found" in lowered:
            return SeriesNotFoundError("fred", request.series or "unknown")
        return None

    def synthesize(
        self,
        request: Request,  # noqa: ARG002 - the hook's signature
        response: Response,
        *,
        seed: str,
    ) -> Response:
        """Replace every observed value; trim notes and a release's size.

        Titles, units, dates, real-time periods and missing markers stay; a v2
        release keeps its first four series and their last 24 observations, so
        a cassette stays within its caps.
        """
        payload = json.loads(response.body)
        rows = list(payload.get("observations", ()))
        if isinstance(payload.get("seriess"), list):
            payload["seriess"] = [_short(entry) for entry in payload["seriess"][:_KEPT]]
        if isinstance(payload.get("series"), list):
            payload["series"] = [_short(entry) for entry in payload["series"][:4]]
            for entry in payload["series"]:
                entry["observations"] = entry.get("observations", [])[-_KEPT:]
                rows.extend(entry["observations"])
            payload["has_more"] = False
            payload.pop("next_cursor", None)
        for position, row in enumerate(rows):
            if row.get("value") not in _MISSING:
                row["value"] = f"{synthetic_value(seed, position):.4f}"
        return Response(
            response.status,
            json.dumps(payload, separators=(",", ":")).encode(),
            response.retrieved_at,
            response.headers,
        )


def _short(entry: dict[str, Any]) -> dict[str, Any]:
    """Shorten a series' notes, which a synthetic cassette need not keep whole."""
    if isinstance(entry.get("notes"), str):
        entry["notes"] = entry["notes"][:_SEARCH_NOTES]
    return entry


def _dating(frequency: ObservationFrequency) -> DateConvention:
    if frequency in s.MONTHS_PER_PERIOD:
        return DateConvention.PERIOD_START
    if frequency.needs_weekday:
        return DateConvention.PERIOD_END
    return DateConvention.POINT_IN_TIME


def _table(frames: Sequence[Series], table_id: str, title: str) -> Table:
    """Columns that share one index: every date any series has, ``None`` elsewhere."""
    first = frames[0].meta
    if any(
        (frame.meta.frequency, frame.meta.week_ends_on)
        != (first.frequency, first.week_ends_on)
        for frame in frames
    ):
        msg = "fred puts series of one frequency in a table; fetch the others apart"
        raise DataError(msg, provider="fred")
    index = tuple(sorted({day for frame in frames for day in frame.index}))
    data = []
    for frame in frames:
        by_day = dict(zip(frame.index, frame.values, strict=True))
        data.append(tuple(by_day.get(day) for day in index))
    # The table carries the most restrictive of its series' terms.
    notices = [frame.meta.terms for frame in frames]
    terms = next(
        (t for t in notices if t.notice == _PRE_APPROVAL_NOTICE),
        next((t for t in notices if t.notice != FRED_NOTICE), FRED_TERMS),
    )
    notes = tuple(
        dict.fromkeys(
            f"{code}: {frame.meta.series_id}, {detail}"
            for frame in frames
            for code, _, detail in (note.partition(": ") for note in frame.meta.notes)
        )
    )[:32]
    return Table(
        index,
        tuple(
            ColumnMeta(
                name=frame.meta.series_id,
                unit=frame.meta.unit,
                seasonal_adjustment=frame.meta.seasonal_adjustment,
                series_id=frame.meta.series_id,
                title=frame.meta.title,
            )
            for frame in frames
        ),
        tuple(data),
        TableMeta(
            provider="fred",
            table_id=table_id,
            title=title,
            frequency=first.frequency,
            week_ends_on=first.week_ends_on,
            source_dating=first.source_dating,
            terms=terms,
            notes=notes,
        ),
    )
