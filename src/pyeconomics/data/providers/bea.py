# src/pyeconomics/data/providers/bea.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""BEA: the US Bureau of Economic Analysis' Data API.

Every request is ``GET apps.bea.gov/api/data?method=GetData`` with the user's
36-character UserID (``UserID``, attached by the transport). A series id names
the dataset and the selection, separated by ``/``:

- ``NIPA/<table>/<A|Q|M>[/<line>]`` and
  ``NIUnderlyingDetail/<table>/<A|Q|M>[/<line>]``: a National Income and
  Product Accounts table (``T10101`` is real GDP's percent change) at a
  frequency, and one of its lines, or every line as a table;
- ``Regional/<table>/<line>/<geography>``: a regional table's line for one
  county, state or area code (five digits) or every ``STATE``, ``MSA``,
  ``PORT`` or ``TERR`` as a table;
- ``ITA/<indicator>/<area or country>/<A|QSA|QNSA>``: an International
  Transactions Accounts indicator.

The years asked for come from the query's dates (all years without them).

- **Values.** ``DataValue`` is formatted with thousands separators;
  ``(NA)``, ``(D)``, ``(NM)``, ``(L)``, ``(S)``, ``---`` and an empty value are
  missing (BEA's "not available", "suppressed to avoid disclosure", "not
  meaningful", "less than half the unit shown" and the like), noted on the
  frame. ``UNIT_MULT`` is the power of ten of the values; a percent becomes a
  decimal. A period is ``YYYY``, ``YYYYQn`` or ``YYYYMn``, indexed by its last
  day.
- **Current estimates only.** The API serves BEA's latest estimates, never
  the values first published, so every frame records ``revised_data``.
- **Limits** (BEA's API user guide): 100 requests, 100 MB and 30 errors a
  minute, a throttled request answered with HTTP 429 and ``Retry-After``.
  Other failures come back with HTTP 200 and an ``Error`` object, which the
  provider maps: code 1 is a refused UserID, code 7 a spent quota.
- **Terms** (https://apps.bea.gov/API/_pdf/bea_api_tos.pdf, read 2026-10-15):
  the API may be used to "search, display, analyze, retrieve, view and
  otherwise get information from BEA data" in any service, which shows BEA's
  notice; ``hosted-safe``.

Examples
--------
>>> Bea.info.id, Bea.info.terms.licence.value
('bea', 'hosted-safe')
>>> parse_id("NIPA/T10101/Q/1")
Selection(dataset='NIPA', table='T10101', frequency='Q', line='1', geography=None)
>>> time_period("2024Q3"), time_period("2024M2"), time_period("2024")
(datetime.date(2024, 9, 30), datetime.date(2024, 2, 29), datetime.date(2024, 12, 31))

"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

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

__all__ = ["Bea"]

_ID: Final = "bea"
HOST: Final = "apps.bea.gov"
PATH: Final = "/api/data"
#: The notice BEA's API terms of service require, verbatim.
BEA_NOTICE: Final = (
    "This product uses the Bureau of Economic Analysis (BEA) Data API but is not "
    "endorsed or certified by BEA."
)
BEA_TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://apps.bea.gov/API/_pdf/bea_api_tos.pdf",
    checked=dt.date(2026, 10, 15),
    attribution="Source: U.S. Bureau of Economic Analysis.",
    notice=BEA_NOTICE,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
REVISED_NOTE: Final = (
    "revised_data: BEA's API serves its current estimates, not the values as "
    "first published"
)
_MISSING: Final = ("(NA)", "(D)", "(NM)", "(L)", "(S)", "(X)", "---", "n.a.", "n.s.")
_TOKEN: Final = re.compile(r"[A-Za-z0-9_]{1,64}")
_NIPA_FREQUENCIES: Final = {"A", "Q", "M"}
_ITA_FREQUENCIES: Final = {"A", "QSA", "QNSA"}
_GEOGRAPHY: Final = re.compile(r"\d{5}|STATE|MSA|PORT|TERR")
_PERIOD: Final = re.compile(r"(\d{4})(?:([QM])(\d{1,2}))?")
_FREQUENCY: Final = {
    None: ObservationFrequency.ANNUAL,
    "Q": ObservationFrequency.QUARTERLY,
    "M": ObservationFrequency.MONTHLY,
}
_NIPA: Final = ("NIPA", "NIUnderlyingDetail")


@dataclass(frozen=True, slots=True)
class Selection:
    """What a BEA series id selects."""

    dataset: str
    table: str
    frequency: str | None
    line: str | None
    geography: str | None


def parse_id(series_id: str) -> Selection:
    """Read a BEA series id (see the module docstring).

    Raises
    ------
    DataError
        For an id that names no dataset BEA's provider reads, or a part that
        is not a plain token.
    """
    parts = series_id.split("/")
    dataset = parts[0]
    if not all(_TOKEN.fullmatch(part) for part in parts):
        msg = f"a bea series id is plain tokens separated by '/', not {series_id!r}"
        raise DataError(msg, provider="bea")
    if dataset in _NIPA and len(parts) in {3, 4} and parts[2] in _NIPA_FREQUENCIES:
        line = parts[3] if len(parts) == 4 else None  # noqa: PLR2004 - its parts
        return Selection(dataset, parts[1], parts[2], line, None)
    if dataset == "Regional" and len(parts) == 4 and _GEOGRAPHY.fullmatch(parts[3]):  # noqa: PLR2004
        return Selection(dataset, parts[1], None, parts[2], parts[3])
    if dataset == "ITA" and len(parts) == 4 and parts[3] in _ITA_FREQUENCIES:  # noqa: PLR2004
        return Selection(dataset, parts[1], parts[3], None, parts[2])
    msg = (
        f"{series_id!r} is not a bea series id: NIPA/<table>/<A|Q|M>[/<line>], "
        "NIUnderlyingDetail/..., Regional/<table>/<line>/<geography> or "
        "ITA/<indicator>/<area>/<A|QSA|QNSA>"
    )
    raise DataError(msg, provider="bea")


def time_period(text: str) -> dt.date:
    """Return the last day of a BEA ``TimePeriod``: ``2024``, ``2024Q3``, ``2024M2``."""
    match = _PERIOD.fullmatch(text.strip())
    if match is None:
        msg = f"bea sent a time period it does not document: {text[:12]!r}"
        raise ResponseError(msg, provider="bea")
    year, kind, number = int(match.group(1)), match.group(2), match.group(3)
    if kind is None:
        return dt.date(year, 12, 31)
    months = int(number) * (3 if kind == "Q" else 1)
    if not 1 <= months <= 12:  # noqa: PLR2004 - months in a year
        msg = f"bea sent a time period it does not document: {text[:12]!r}"
        raise ResponseError(msg, provider="bea")
    return s.month_end(year, months)


def _years(query: Query) -> str:
    if query.start is None and query.end is None:
        return "X"
    last = query.end.year if query.end is not None else None
    first = query.start.year if query.start is not None else None
    if first is None or last is None:
        return "X"
    return ",".join(str(year) for year in range(first, last + 1))


def _error(body: dict[str, Any]) -> None:
    """Raise the error BEA's ``Error`` object reports, if there is one."""
    root = body.get("BEAAPI")
    if not isinstance(root, dict):
        msg = "bea sent a body without its BEAAPI object"
        raise ResponseError(msg, provider="bea")
    results = root.get("Results")
    error = root.get("Error") or (
        results.get("Error") if isinstance(results, dict) else None
    )
    if isinstance(error, list):
        error = error[0] if error else None
    if not isinstance(error, dict):
        return
    code = str(error.get("APIErrorCode", "")).strip()
    extra = error.get("ErrorDetail")
    detail = " ".join(
        str(part)
        for part in (
            error.get("APIErrorDescription") or error.get("error") or "",
            extra.get("Description", "") if isinstance(extra, dict) else "",
        )
    )
    lowered = detail.casefold()
    if code == "1" or "userid" in lowered.replace(" ", ""):
        msg = (
            "bea refused the UserID: set BEA_API_KEY to the 36-character UserID "
            "from apps.bea.gov/API/signup"
        )
        raise CredentialError(msg, provider="bea")
    if code == "7" or "quota" in lowered:
        msg = "bea is rate limiting requests (100 a minute; 30 errors a minute)"
        raise RateLimitError(msg, provider="bea", retry_after=60.0)
    if code == "40" or "invalid" in lowered or "does not exist" in lowered:
        raise SeriesNotFoundError(_ID, "the requested table or line")
    msg = f"bea could not answer the request (BEA error code {code[:8] or 'none'})"
    raise ResponseError(msg, provider="bea")


def _unit(row: dict[str, Any]) -> tuple[UnitRecord, bool]:
    unit = str(row.get("CL_UNIT") or "").strip() or "As published by BEA"
    metric = str(row.get("METRIC_NAME") or row.get("Metric_Name") or "").strip()
    try:
        power = int(str(row.get("UNIT_MULT") or "0").strip())
    except ValueError:
        power = 0
    lowered = f"{unit} {metric}".casefold()
    text = f"{metric}, {unit}" if metric and metric not in unit else unit
    if "percent" in lowered:
        return UnitRecord(text=text[:256], kind=UnitKind.RATE), True
    scale = float(f"1e{power}") if -15 <= power <= 15 else 1.0  # noqa: PLR2004
    if "dollar" in lowered or unit.upper() == "USD":
        return UnitRecord(
            text=text[:256], kind=UnitKind.MONEY, scale=scale, currency="USD"
        ), False
    if "index" in lowered or "quantity" in lowered:
        return UnitRecord(
            text=text[:256], kind=UnitKind.INDEX_LEVEL, scale=scale
        ), False
    return UnitRecord(text=text[:256], scale=scale), False


def _adjustment(notes: str, frequency: ObservationFrequency) -> SeasonalAdjustment:
    lowered = notes.casefold()
    if "not seasonally adjusted" in lowered:
        return SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
    if "annual rate" in lowered and frequency is not ObservationFrequency.ANNUAL:
        return SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE
    if "seasonally adjusted" in lowered:
        return SeasonalAdjustment.SEASONALLY_ADJUSTED
    return SeasonalAdjustment.NOT_APPLICABLE


class Bea(DataProvider):
    """The BEA Data API: NIPA, NIUnderlyingDetail, Regional and ITA."""

    info = ProviderInfo(
        id="bea",
        name="US Bureau of Economic Analysis",
        homepage="https://www.bea.gov",
        terms=BEA_TERMS,
        auth=Authentication.key("UserID", KeyPlacement.QUERY),
        hosts=(HOST,),
        rate_limits=(RateLimit(requests=100, per="minute"),),
        ttl_seconds=6 * 3_600,
    )
    cases = (
        Case(
            name="fetch_ok",
            operation=Capability.FETCH,
            argument=Query(
                series=("NIPA/T10101/Q/1",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_table",
            operation=Capability.FETCH,
            argument=Query(
                series=("NIPA/T10101/A",),
                start=dt.date(2023, 1, 1),
                end=dt.date(2024, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_regional",
            operation=Capability.FETCH,
            argument=Query(
                series=("Regional/SAINC1/3/06000",),
                start=dt.date(2020, 1, 1),
                end=dt.date(2024, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_ita",
            operation=Capability.FETCH,
            argument=Query(
                series=("ITA/BalGds/AllCountries/QSA",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="error_unauthorized",
            operation=Capability.FETCH,
            argument=Query(
                series=("NIPA/T10101/A/1",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                max_observations=24,
            ),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("NIPA/TNOSUCH/A/1",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                max_observations=24,
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(
                series=("NIPA/T10101/A/1",),
                start=dt.date(2024, 1, 1),
                end=dt.date(2024, 12, 31),
                max_observations=24,
            ),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """One GetData request per series id."""
        return tuple(
            self._request(parse_id(series_id), series_id, query)
            for series_id in query.series
        )

    def _request(self, selection: Selection, series_id: str, query: Query) -> Request:
        params: list[tuple[str, str]] = [
            ("method", "GetData"),
            ("datasetname", selection.dataset),
            ("ResultFormat", "JSON"),
        ]
        years = _years(query)
        if selection.dataset in _NIPA:
            params += [
                ("TableName", selection.table),
                ("Frequency", selection.frequency or "A"),
                ("Year", years),
            ]
        elif selection.dataset == "Regional":
            params += [
                ("TableName", selection.table),
                ("LineCode", selection.line or "1"),
                ("GeoFips", selection.geography or "STATE"),
                ("Year", "ALL" if years == "X" else years),
            ]
        else:
            params += [
                ("Indicator", selection.table),
                ("AreaOrCountry", selection.geography or "AllCountries"),
                ("Frequency", selection.frequency or "A"),
                ("Year", "All" if years == "X" else years),
            ]
        return Request(host=HOST, path=PATH, params=tuple(params), series=series_id)

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Return a series per id; a table for a whole table or several places."""
        frames: list[Series | Table] = []
        for response, series_id in zip(responses, query.series, strict=True):
            if not response.body.strip():
                msg = "bea sent an empty body (a request without a UserID)"
                raise CredentialError(msg, provider="bea")
            body = s.body_object(response, "bea")
            _error(body)
            frames.append(self._frame(body, parse_id(series_id), series_id, query))
        if len(frames) == 1:
            return frames[0]
        msg = "bea answers one series id per fetch; fetch the others apart"
        raise DataError(msg, provider="bea")

    def _frame(
        self, body: dict[str, Any], selection: Selection, series_id: str, query: Query
    ) -> Series | Table:
        results = body["BEAAPI"].get("Results")
        if isinstance(results, list):
            results = results[0] if results else {}
        if not isinstance(results, dict):
            msg = "bea sent no Results"
            raise ResponseError(msg, provider="bea")
        rows = [
            row
            for row in s.items(results.get("Data"), "bea", "Data")
            if isinstance(row, dict)
        ]
        notes_text = " ".join(
            str(note.get("NoteText", ""))
            for note in results.get("Notes") or ()
            if isinstance(note, dict)
        )
        groups = self._groups(rows, selection)
        if not groups:
            raise SeriesNotFoundError(_ID, series_id)
        title = _table_title(results, selection)
        frames = [
            self._series(
                key,
                label=label,
                rows=group,
                selection=selection,
                series_id=series_id,
                query=query,
                notes_text=notes_text,
            )
            for key, (label, group) in groups.items()
        ]
        if len(frames) == 1 and selection.geography not in {
            "STATE",
            "MSA",
            "PORT",
            "TERR",
        }:
            return frames[0]
        return _table(frames, series_id, title)

    def _groups(
        self, rows: list[dict[str, Any]], selection: Selection
    ) -> dict[str, tuple[str, list[dict[str, Any]]]]:
        """Group a response's rows into the series it holds, keyed by line or place."""
        groups: dict[str, tuple[str, list[dict[str, Any]]]] = {}
        for row in rows:
            if selection.dataset in _NIPA:
                key = str(row.get("LineNumber", "")).strip()
                if selection.line is not None and key != selection.line:
                    continue
                label = str(row.get("LineDescription") or f"Line {key}")
            elif selection.dataset == "Regional":
                key = str(row.get("GeoFips", "")).strip()
                label = str(row.get("GeoName") or key)
            else:
                key = str(row.get("TimeSeriesId") or selection.table).strip()
                label = str(row.get("TimeSeriesDescription") or selection.table)
            groups.setdefault(key, (label, []))[1].append(row)
        return groups

    def _series(  # noqa: PLR0913 - each is a part of the selection
        self,
        key: str,
        *,
        label: str,
        rows: list[dict[str, Any]],
        selection: Selection,
        series_id: str,
        query: Query,
        notes_text: str,
    ) -> Series:
        unit, percent = _unit(rows[0])
        values: dict[dt.date, float | None] = {}
        markers: dict[str, list[dt.date]] = {}
        kinds = set()
        for row in rows:
            period = str(row.get("TimePeriod", ""))
            match = _PERIOD.fullmatch(period.strip())
            kinds.add(match.group(2) if match else None)
            day = time_period(period)
            if (query.start and day < query.start) or (query.end and day > query.end):
                continue
            raw = row.get("DataValue")
            value = s.number(raw, "bea", missing=_MISSING)
            if value is None:
                markers.setdefault(str(raw).strip() or "blank", []).append(day)
            values[day] = s.rate_or_value(value, percent=percent)
        if len(kinds) > 1:
            msg = "bea sent periods of more than one frequency for one series"
            raise ResponseError(msg, provider="bea")
        frequency = _FREQUENCY[kinds.pop() if kinds else None]
        notes = [REVISED_NOTE]
        notes += [
            s.dates_note("missing", f"BEA marks {marker}", sorted(days))
            for marker, days in sorted(markers.items())
        ]
        days = sorted(values)
        part = key if selection.dataset != "ITA" else None
        meta = SeriesMeta(
            provider="bea",
            series_id=series_id
            if part is None or selection.line
            else f"{series_id}/{part}",
            dataset=selection.dataset,
            title=label.strip()[:256] or series_id,
            unit=unit,
            frequency=frequency,
            seasonal_adjustment=_adjustment(notes_text, frequency),
            source_dating=DateConvention.PERIOD_START,
            terms=BEA_TERMS,
            notes=tuple(notes[:32]),
        )
        return Series(tuple(days), tuple(values[day] for day in days), meta)


def _table_title(results: dict[str, Any], selection: Selection) -> str:
    for note in results.get("Notes") or ():
        if (
            isinstance(note, dict)
            and str(note.get("NoteRef", "")).strip() == selection.table
        ):
            return str(note.get("NoteText") or selection.table)[:256]
    statistic = results.get("Statistic")
    if isinstance(statistic, str) and statistic.strip():
        return statistic.strip()[:256]
    return f"BEA {selection.dataset} {selection.table}"


def _table(frames: Sequence[Series], series_id: str, title: str) -> Table:
    first = frames[0].meta
    index = tuple(sorted({day for frame in frames for day in frame.index}))
    data = []
    for frame in frames:
        by_day = dict(zip(frame.index, frame.values, strict=True))
        data.append(tuple(by_day.get(day) for day in index))
    names = [frame.meta.title[:120] for frame in frames]
    columns = []
    seen: set[str] = set()
    for frame, name in zip(frames, names, strict=True):
        unique = name if name not in seen else f"{name} ({frame.meta.series_id[-24:]})"
        seen.add(unique)
        columns.append(
            ColumnMeta(
                name=unique[:128],
                unit=frame.meta.unit,
                seasonal_adjustment=frame.meta.seasonal_adjustment,
                series_id=frame.meta.series_id,
                title=frame.meta.title,
            )
        )
    notes = tuple(dict.fromkeys(note for frame in frames for note in frame.meta.notes))
    return Table(
        index,
        tuple(columns),
        tuple(data),
        TableMeta(
            provider="bea",
            table_id=series_id,
            dataset=first.dataset,
            title=title,
            frequency=first.frequency,
            source_dating=DateConvention.PERIOD_START,
            terms=BEA_TERMS,
            notes=notes[:32],
        ),
    )
