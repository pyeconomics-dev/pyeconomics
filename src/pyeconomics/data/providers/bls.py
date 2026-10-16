# src/pyeconomics/data/providers/bls.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""BLS: the US Bureau of Labor Statistics' Public Data API.

- **Keyed: API v2.** ``POST api.bls.gov/publicAPI/v2/timeseries/data/`` with
  the registration key in the JSON body (``registrationkey``, attached by the
  transport). A query asks for at most 50 series and 20 years, 500 queries a
  day; the series' catalog (title, seasonality, measure) comes with it.
- **Keyless: API v1.** With no key configured, the same request goes to v1 at
  its lower limits (25 series, 10 years, 25 queries a day), with no catalog, so
  a user without a key still gets data; the frame's notes say ``bls_keyless``.
  No :class:`~pyeconomics.data.errors.CredentialError` is raised.
- A larger query is split into series and year chunks and merged.
- **Values.** BLS dates a period by its name (``M01`` to ``M12``, ``Q01`` to
  ``Q04``, ``S01`` and ``S02``, ``A01``); the index is each period's last day.
  Annual averages (``M13``, ``Q05``, ``S03``) are left out. ``-`` is a missing
  value, and every footnote (``P`` preliminary, ``R`` revised and the
  survey's others) becomes a note naming its dates. A series whose catalog
  measures a percent or a rate becomes a decimal; without the catalog (v1) the
  unit is unknown and the values stay as published.
- **Terms** (https://www.bls.gov/developers/termsOfService.htm, read
  2026-10-15): BLS data are in the public domain and carry no end-use
  controls, so the class is ``hosted-safe``. Users must say that "BLS.gov
  cannot vouch for the data or analyses derived from these data after the data
  have been retrieved from BLS.gov." and cite the date the data were accessed,
  which each frame's notice adds.
- BLS answers its failures with HTTP 200 and a status in the body: a refused
  key, a spent daily quota and an unknown series are mapped from it, and its
  own passing failure (``REQUEST_FAILED``) is a
  :class:`~pyeconomics.data.errors.TransportError`, to try again.

Examples
--------
>>> Bls.info.id, Bls.info.auth.required, Bls.info.terms.licence.value
('bls', False, 'hosted-safe')
>>> period_day("2026", "M02"), period_day("2026", "Q03"), period_day("2026", "S01")
(datetime.date(2026, 2, 28), datetime.date(2026, 9, 30), datetime.date(2026, 6, 30))

"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    CredentialError,
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
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
from pyeconomics.data.transport.base import Request, Response
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
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["Bls"]

_ID: Final = "bls"
HOST: Final = "api.bls.gov"
V2_PATH: Final = "/publicAPI/v2/timeseries/data/"
V1_PATH: Final = "/publicAPI/v1/timeseries/data/"
#: The statement BLS's terms require of every user of its API, verbatim.
BLS_NOTICE: Final = (
    "BLS.gov cannot vouch for the data or analyses derived from these data after "
    "the data have been retrieved from BLS.gov."
)
BLS_TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.bls.gov/developers/termsOfService.htm",
    checked=dt.date(2026, 10, 15),
    attribution="Source: U.S. Bureau of Labor Statistics.",
    notice=BLS_NOTICE,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
#: Series and years per query: v2 with a key, v1 without (BLS's API FAQ).
KEYED_LIMITS: Final = (50, 20)
KEYLESS_LIMITS: Final = (25, 10)
_MISSING: Final = ("-",)
_PERIOD: Final = re.compile(r"([MQSA])(\d{2})")
_AVERAGES: Final = frozenset({"M13", "Q05", "S03"})
_FREQUENCIES: Final = {
    "M": ObservationFrequency.MONTHLY,
    "Q": ObservationFrequency.QUARTERLY,
    "S": ObservationFrequency.SEMIANNUAL,
    "A": ObservationFrequency.ANNUAL,
}
_MONTHS: Final = {"M": 1, "Q": 3, "S": 6, "A": 12}
_COUNTS: Final = {"M": 12, "Q": 4, "S": 2, "A": 1}
_ADJUSTMENTS: Final = {
    "seasonally adjusted": SeasonalAdjustment.SEASONALLY_ADJUSTED,
    "not seasonally adjusted": SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
}


def period_day(year: str, period: str) -> dt.date:
    """Return the last day of a BLS period such as ``M02``, ``Q03`` or ``S01``.

    Raises
    ------
    ResponseError
        For a period BLS does not document.
    """
    match = _PERIOD.fullmatch(period)
    if match is None or not year.isdecimal():
        msg = f"bls sent a period it does not document: {period[:8]!r}"
        raise ResponseError(msg, provider="bls")
    kind, number = match.group(1), int(match.group(2))
    if not 1 <= number <= _COUNTS[kind]:
        msg = f"bls sent a period it does not document: {period[:8]!r}"
        raise ResponseError(msg, provider="bls")
    return s.month_end(int(year), number * _MONTHS[kind])


def _years(query: Query, per_query: int) -> list[tuple[int, int] | None]:
    """Split the query's years into windows BLS accepts; ``None`` is its default.

    Without dates BLS returns its latest three years. A start without an end
    reads ``per_query`` years from the start.
    """
    start, end = query.start, query.end
    if end is not None:
        last = end.year
        first = start.year if start is not None else last - per_query + 1
    elif start is not None:
        first = start.year
        last = first + per_query - 1
    else:
        return [None]
    return [
        (year, min(year + per_query - 1, last))
        for year in range(first, last + 1, per_query)
    ]


def _status(body: dict[str, Any]) -> None:
    """Raise the error a body's status and messages report, if any."""
    status = body.get("status")
    messages = [str(m) for m in body.get("message") or () if isinstance(m, str)]
    lowered = " ".join(messages).casefold()
    if status == "REQUEST_SUCCEEDED":
        return
    if "key" in lowered and ("invalid" in lowered or "expired" in lowered):
        # The message repeats the key, so none of it is kept.
        msg = (
            "bls refused the registration key: set BLS_API_KEY to a key from "
            "data.bls.gov/registrationEngine, or unset it to read API v1 keyless"
        )
        raise CredentialError(msg, provider="bls")
    if "threshold" in lowered or "too many" in lowered or "limit" in lowered:
        msg = "bls's daily query limit is spent for this key or address"
        raise RateLimitError(msg, provider="bls")
    if status == "REQUEST_FAILED":
        # BLS answers a passing failure of its own this way, with HTTP 200 and
        # a generic message; the same request succeeds when sent again.
        msg = "bls failed to answer the request (REQUEST_FAILED); try again"
        raise TransportError(msg, provider="bls")
    msg = f"bls did not process the request (status {str(status)[:40]!r})"
    raise ResponseError(msg, provider="bls")


def _catalog_unit(catalog: dict[str, Any] | None) -> tuple[UnitRecord, bool]:
    """Read a unit from the series' catalog: whether it is a percent or a rate."""
    if not catalog:
        return UnitRecord(text="As published by BLS (unit not given by API v1)"), False
    measure = str(catalog.get("measure_data_type") or "").strip()
    title = str(catalog.get("series_title") or "")
    lowered = f"{measure} {title}".casefold()
    if "percent" in lowered or re.search(r"\brate\b", lowered):
        return UnitRecord(text=measure or "Percent", kind=UnitKind.RATE), True
    if "index" in lowered:
        return UnitRecord(text=measure or "Index", kind=UnitKind.INDEX_LEVEL), False
    return UnitRecord(text=measure or "As published by BLS"), False


class Bls(DataProvider):
    """The BLS Public Data API, keyed (v2) or keyless (v1)."""

    info = ProviderInfo(
        id="bls",
        name="US Bureau of Labor Statistics",
        homepage="https://www.bls.gov",
        terms=BLS_TERMS,
        auth=Authentication.key("registrationkey", KeyPlacement.BODY, required=False),
        hosts=(HOST,),
        # 50 requests per 10 seconds for both versions, held as 5 a second;
        # 500 queries a day with a key and 25 without (BLS's API FAQ).
        rate_limits=(
            RateLimit(requests=5, per="second"),
            RateLimit(requests=500, per="day"),
            RateLimit(requests=25, per="day", without_key=True),
        ),
        ttl_seconds=6 * 3_600,
    )
    cases = (
        Case(
            name="fetch_ok",
            operation=Capability.FETCH,
            argument=Query(
                series=("CUUR0000SA0",),
                start=dt.date(2024, 10, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_table",
            operation=Capability.FETCH,
            argument=Query(
                series=("LNS14000000", "LNS11300000"),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_keyless",
            operation=Capability.FETCH,
            argument=Query(
                series=("LNS14000000",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
            keyless=True,
        ),
        Case(
            name="fetch_preliminary",
            operation=Capability.FETCH,
            argument=Query(
                series=("CES0000000001",),
                start=dt.date(2026, 1, 1),
                end=dt.date(2026, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="error_unauthorized",
            operation=Capability.FETCH,
            argument=Query(
                series=("LNS14000000",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("ZZZNOTASERIES1",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(
                series=("LNS14000000",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """POST each chunk of series and years to v2 (keyed) or v1 (keyless)."""
        keyed = self.sends_key
        series_cap, year_cap = KEYED_LIMITS if keyed else KEYLESS_LIMITS
        requests = []
        for first in range(0, len(query.series), series_cap):
            chunk = list(query.series[first : first + series_cap])
            for window in _years(query, year_cap):
                body: dict[str, object] = {"seriesid": chunk}
                if window is not None:
                    body["startyear"], body["endyear"] = str(window[0]), str(window[1])
                if keyed:
                    body["catalog"] = True
                requests.append(
                    Request(
                        host=HOST,
                        path=V2_PATH if keyed else V1_PATH,
                        method="POST",
                        body=body,
                        series=chunk[0] if len(chunk) == 1 else None,
                    )
                )
        return requests

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Merge every chunk's rows into a series per id (a table for several)."""
        rows: dict[str, list[Any]] = {series: [] for series in query.series}
        catalogs: dict[str, dict[str, Any]] = {}
        unknown: set[str] = set()
        for response in responses:
            body = s.body_object(response, "bls")
            _status(body)
            unknown |= _unknown(body)
            results = body.get("Results")
            entries = results.get("series") if isinstance(results, dict) else None
            for entry in s.items(entries or [], "bls", "series"):
                series_id = s.text(entry, "seriesID", "bls").upper()
                if series_id not in rows:
                    continue
                rows[series_id].extend(s.items(entry.get("data"), "bls", "data"))
                catalog = entry.get("catalog")
                if isinstance(catalog, dict):
                    catalogs[series_id] = catalog
        for series_id in query.series:
            if series_id in unknown and not rows[series_id]:
                raise SeriesNotFoundError(_ID, series_id)
        accessed = max(response.retrieved_at for response in responses).date()
        frames = [
            self._series(
                series_id, rows[series_id], catalogs.get(series_id), accessed, query
            )
            for series_id in query.series
        ]
        if len(frames) == 1:
            return frames[0]
        return _table(frames, query)

    def _series(
        self,
        series_id: str,
        rows: list[Any],
        catalog: dict[str, Any] | None,
        accessed: dt.date,
        query: Query,
    ) -> Series:
        kinds = [
            str(row.get("period", ""))[:1]
            for row in rows
            if isinstance(row, dict) and row.get("period") not in _AVERAGES
        ]
        kind = max(set(kinds), key=kinds.count) if kinds else "M"
        unit, percent = _catalog_unit(catalog)
        values: dict[dt.date, float | None] = {}
        footnotes: dict[str, set[dt.date]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            period = str(row.get("period", ""))
            if period in _AVERAGES or not period.startswith(kind):
                continue
            day = period_day(str(row.get("year", "")), period)
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            values[day] = s.rate_or_value(
                s.number(row.get("value"), "bls", missing=_MISSING), percent=percent
            )
            for note in row.get("footnotes") or ():
                if isinstance(note, dict) and note.get("code"):
                    label = (
                        f"{str(note['code'])[:4]} {str(note.get('text') or '')[:120]}"
                    )
                    footnotes.setdefault(label.strip(), set()).add(day)
        notes = [
            s.dates_note("footnote", label, sorted(days))
            for label, days in sorted(footnotes.items())
        ]
        if catalog is None:
            notes.append(
                "bls_keyless: read through BLS API v1 without a key: no catalog, so "
                "no title, unit or seasonal adjustment, and lower limits"
            )
        title = str((catalog or {}).get("series_title") or series_id)[:256]
        adjustment = _ADJUSTMENTS.get(
            str((catalog or {}).get("seasonality") or "").casefold(),
            SeasonalAdjustment.NOT_APPLICABLE,
        )
        days = sorted(values)
        meta = SeriesMeta(
            provider="bls",
            series_id=series_id,
            dataset=str(catalog.get("survey_name"))[:256]
            if catalog and catalog.get("survey_name")
            else None,
            title=title.strip() or series_id,
            unit=unit,
            frequency=_FREQUENCIES[kind],
            seasonal_adjustment=adjustment,
            source_dating=DateConvention.PERIOD_START,
            terms=BLS_TERMS.with_overrides(
                notice=f"{BLS_NOTICE} Data accessed through the BLS Public Data API "
                f"on {accessed.isoformat()}."
            ),
            notes=tuple(notes[:32]),
        )
        return Series(tuple(days), tuple(values[day] for day in days), meta)


def _unknown(body: dict[str, Any]) -> set[str]:
    """Return the series a body's messages call invalid."""
    found = set()
    for message in body.get("message") or ():
        match = re.search(
            r"(?:Invalid Series|Series does not exist) for Series ([A-Za-z0-9]+)",
            str(message),
        )
        if match:
            found.add(match.group(1).upper())
    return found


def _table(frames: Sequence[Series], query: Query) -> Table:
    first = frames[0].meta
    if any(frame.meta.frequency is not first.frequency for frame in frames):
        msg = "bls puts series of one frequency in a table; fetch the others apart"
        raise DataError(msg, provider="bls")
    index = tuple(sorted({day for frame in frames for day in frame.index}))
    data = []
    for frame in frames:
        by_day = dict(zip(frame.index, frame.values, strict=True))
        data.append(tuple(by_day.get(day) for day in index))
    notes = tuple(
        dict.fromkeys(
            f"{note.split(': ', 1)[0]}: {frame.meta.series_id}"
            for frame in frames
            for note in frame.meta.notes
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
            provider="bls",
            table_id="+".join(query.series)[:128],
            title="BLS series",
            frequency=first.frequency,
            source_dating=DateConvention.PERIOD_START,
            terms=first.terms,
            notes=notes,
        ),
    )
