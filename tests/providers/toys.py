# tests/providers/toys.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Two toy data providers, so every rule of the contract is exercised before Step 6.

They are tests only and never ship. Both talk to invented APIs on reserved
``example.org`` hosts; their numbers are made up.

- ``toy_json``: a hosted-safe, keyed JSON source. The key is a query parameter.
  It dates months by their first day and publishes percent, so its provider
  converts both; a ``.`` is a missing value; an unknown series is HTTP 400 with a
  JSON message (``classify_error`` maps it); one series is marked restricted, which
  overrides the class, ``llm_use`` and cache policy for that series.
- ``toy_vintage``: a library-only source that keeps vintages and forbids storage.
  It has no key and publishes real-time periods as ALFRED does, with
  ``9999-12-31`` for a value that is still current; its cassettes are synthetic.

``CASES`` is what the recorder would record and the contract suite replays; the
cassettes under ``tests/providers/cassettes`` are built from the responses in
``build_toy_cassettes.py``.
"""

from __future__ import annotations

import calendar
import datetime as dt
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.rates import percent_to_decimal
from pyeconomics.data import (
    Authentication,
    CachePolicy,
    Capability,
    Case,
    ColumnMeta,
    DataProvider,
    DateConvention,
    KeyPlacement,
    LicenceClass,
    LlmUse,
    ObservationFrequency,
    ProviderInfo,
    Query,
    RateLimit,
    RealtimePeriod,
    ResponseError,
    SearchHit,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    SeriesNotFoundError,
    Table,
    TableMeta,
    Terms,
    UnitRecord,
)
from pyeconomics.data.errors import (
    CredentialError,
    RateLimitError,
    TransportError,
)
from pyeconomics.data.transport.base import Request, Response, request_path
from pyeconomics.data.transport.cassette import synthetic_value

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data import DataError

__all__ = [
    "JSON_HOST",
    "TOY_JSON_TERMS",
    "TOY_VINTAGE_TERMS",
    "VINTAGE_HOST",
    "ToyJson",
    "ToyVintage",
]

JSON_HOST: Final = "api.toyjson.example.org"
VINTAGE_HOST: Final = "api.toyvintage.example.org"
#: ALFRED's marker for a value that is still current.
_CURRENT: Final = "9999-12-31"

TOY_JSON_TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.toyjson.example.org/terms",
    checked=dt.date(2026, 10, 15),
    attribution="Source: Toy JSON Agency (a test fixture with invented numbers).",
    notice="This product uses the Toy JSON API but is not endorsed by Toy JSON Agency.",
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
TOY_VINTAGE_TERMS: Final = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://www.toyvintage.example.org/terms",
    checked=dt.date(2026, 10, 15),
    attribution="Source: Toy Vintage Bank (a test fixture with invented numbers).",
    llm_use=LlmUse.FORBIDDEN,
    cache=CachePolicy.FORBIDDEN,
)
_RESTRICTED: Final = TOY_JSON_TERMS.with_overrides(
    licence=LicenceClass.LIBRARY_ONLY,
    llm_use=LlmUse.FORBIDDEN,
    cache=CachePolicy.FORBIDDEN,
)
_ADJUSTMENT: Final = {
    "SA": SeasonalAdjustment.SEASONALLY_ADJUSTED,
    "NSA": SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
    "SAAR": SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
}
_FREQUENCY: Final = {
    "monthly": ObservationFrequency.MONTHLY,
    "quarterly": ObservationFrequency.QUARTERLY,
}


def month_end(day: dt.date) -> dt.date:
    """Return the last day of ``day``'s month."""
    return dt.date(day.year, day.month, calendar.monthrange(day.year, day.month)[1])


def quarter_end(day: dt.date) -> dt.date:
    """Return the last day of ``day``'s calendar quarter."""
    return month_end(dt.date(day.year, 3 * ((day.month - 1) // 3) + 3, 1))


def _object(value: object, provider: str, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        msg = f"{provider} sent {what} that is not an object"
        raise ResponseError(msg, provider=provider)
    return value


def _text(payload: dict[str, Any], key: str, provider: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        msg = f"{provider} sent no {key}"
        raise ResponseError(msg, provider=provider)
    return value


def _percent(raw: object) -> float | None:
    """Read a percent as a decimal; the source's ``.`` is a missing value."""
    if raw == ".":
        return None
    if not isinstance(raw, str):
        msg = "a value is text"
        raise ResponseError(msg)
    return percent_to_decimal(float(raw))


def _day(raw: object, provider: str) -> dt.date:
    try:
        return dt.date.fromisoformat(str(raw))
    except ValueError:
        msg = f"{provider} sent a date that is not YYYY-MM-DD"
        raise ResponseError(msg, provider=provider) from None


class ToyJson(DataProvider):
    """A hosted-safe, keyed JSON source (see the module docstring)."""

    info = ProviderInfo(
        id="toy_json",
        name="Toy JSON Agency",
        homepage="https://www.toyjson.example.org",
        terms=TOY_JSON_TERMS,
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
        auth=Authentication.key("api_key", KeyPlacement.QUERY),
        hosts=(JSON_HOST,),
        rate_limits=(
            RateLimit(requests=5, per="second"),
            RateLimit(requests=120, per="minute"),
        ),
    )
    cases = (
        Case(
            name="fetch_ok",
            operation=Capability.FETCH,
            argument=Query(
                series=("TOYRATE",),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 6, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_table",
            operation=Capability.FETCH,
            argument=Query(
                series=("TOYRATE", "TOYGROWTH"),
                start=dt.date(2025, 1, 1),
                end=dt.date(2025, 6, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="fetch_restricted",
            operation=Capability.FETCH,
            argument=Query(series=("TOYRESTRICTED",), max_observations=24),
        ),
        Case(name="search_ok", operation=Capability.SEARCH, argument="rate"),
        Case(name="describe_ok", operation=Capability.DESCRIBE, argument="TOYRATE"),
        Case(
            name="error_unauthorized",
            operation=Capability.FETCH,
            argument=Query(series=("TOYRATE",), max_observations=24),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_unknown_series",
            operation=Capability.FETCH,
            argument=Query(series=("NOSUCHSERIES",), max_observations=24),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_not_found",
            operation=Capability.DESCRIBE,
            argument="MISSING",
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.SEARCH,
            argument="limit",
            expect=RateLimitError,
        ),
        Case(
            name="error_unavailable",
            operation=Capability.SEARCH,
            argument="outage",
            expect=TransportError,
        ),
        Case(
            name="error_malformed",
            operation=Capability.SEARCH,
            argument="garbage",
            expect=ResponseError,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """One observations request per series."""
        window = (
            *((("observation_start", query.start.isoformat()),) if query.start else ()),
            *((("observation_end", query.end.isoformat()),) if query.end else ()),
        )
        return tuple(
            Request(
                host=JSON_HOST,
                path=request_path("v1", "observations"),
                params=(
                    ("series_id", series),
                    *window,
                    ("limit", str(query.max_observations)),
                ),
                series=series,
            )
            for series in query.series
        )

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """The source answers an unknown series with HTTP 400 and a message."""
        if response.status == 400:
            try:
                body = response.json(provider="toy_json")
            except ResponseError:
                return None
            if isinstance(body, dict) and "does not exist" in str(
                body.get("error_message", "")
            ):
                return SeriesNotFoundError("toy_json", request.series or "unknown")
        return None

    def _one(self, response: Response, series_id: str) -> Series:
        payload = _object(response.json(provider="toy_json"), "toy_json", "a body")
        rows = payload.get("observations")
        if not isinstance(rows, list):
            msg = "toy_json sent no observations"
            raise ResponseError(msg, provider="toy_json")
        index: list[dt.date] = []
        values: list[float | None] = []
        for row in rows:
            entry = _object(row, "toy_json", "an observation")
            index.append(month_end(_day(entry.get("date"), "toy_json")))
            values.append(_percent(entry.get("value")))
        restricted = payload.get("license") == "restricted"
        meta = SeriesMeta(
            provider="toy_json",
            series_id=series_id,
            title=_text(payload, "title", "toy_json"),
            unit=UnitRecord(
                text=_text(payload, "units", "toy_json"), kind=UnitKind.RATE
            ),
            frequency=_FREQUENCY[_text(payload, "frequency", "toy_json")],
            seasonal_adjustment=_ADJUSTMENT[
                _text(payload, "seasonal_adjustment", "toy_json")
            ],
            source_dating=DateConvention.PERIOD_START,
            terms=_RESTRICTED if restricted else TOY_JSON_TERMS,
        )
        return Series(tuple(index), tuple(values), meta)

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """A series for one id; a table of columns for several."""
        frames = [
            self._one(response, series)
            for response, series in zip(responses, query.series, strict=True)
        ]
        if len(frames) == 1:
            return frames[0]
        index = frames[0].index
        if any(frame.index != index for frame in frames):
            msg = "toy_json sent series on different dates"
            raise ResponseError(msg, provider="toy_json")
        first = frames[0].meta
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
            tuple(frame.values for frame in frames),
            TableMeta(
                provider="toy_json",
                table_id="+".join(query.series)[:128],
                title="Toy JSON series",
                frequency=first.frequency,
                source_dating=first.source_dating,
                terms=TOY_JSON_TERMS,
            ),
        )

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        """A single search request."""
        return (
            Request(
                host=JSON_HOST,
                path=request_path("v1", "search"),
                params=(("q", text), ("limit", str(limit))),
            ),
        )

    def parse_search(
        self, responses: Sequence[Response], text: str, limit: int
    ) -> Sequence[SearchHit]:
        """Hits from the results list."""
        payload = _object(responses[0].json(provider="toy_json"), "toy_json", "a body")
        results = payload.get("results")
        if not isinstance(results, list):
            msg = "toy_json sent no results"
            raise ResponseError(msg, provider="toy_json")
        hits = []
        for result in results:
            entry = _object(result, "toy_json", "a result")
            hits.append(
                SearchHit(
                    series_id=_text(entry, "series_id", "toy_json"),
                    title=_text(entry, "title", "toy_json"),
                    frequency=_FREQUENCY.get(str(entry.get("frequency"))),
                    unit=str(entry["units"]) if "units" in entry else None,
                )
            )
        return hits[:limit]

    def build_describe(self, series_id: str) -> Sequence[Request]:
        """A single request for the series' metadata."""
        return (
            Request(
                host=JSON_HOST,
                path=request_path("v1", "series", series_id),
                series=series_id,
            ),
        )

    def parse_describe(
        self, responses: Sequence[Response], series_id: str
    ) -> SeriesMeta:
        """Metadata from the series object."""
        payload = _object(responses[0].json(provider="toy_json"), "toy_json", "a body")
        return SeriesMeta(
            provider="toy_json",
            series_id=series_id,
            title=_text(payload, "title", "toy_json"),
            unit=UnitRecord(
                text=_text(payload, "units", "toy_json"), kind=UnitKind.RATE
            ),
            frequency=_FREQUENCY[_text(payload, "frequency", "toy_json")],
            seasonal_adjustment=_ADJUSTMENT[
                _text(payload, "seasonal_adjustment", "toy_json")
            ],
            source_dating=DateConvention.PERIOD_START,
            terms=TOY_JSON_TERMS,
        )


class ToyVintage(DataProvider):
    """A library-only source that keeps vintages and forbids storage."""

    info = ProviderInfo(
        id="toy_vintage",
        name="Toy Vintage Bank",
        homepage="https://www.toyvintage.example.org",
        terms=TOY_VINTAGE_TERMS,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        hosts=(VINTAGE_HOST,),
        rate_limits=(RateLimit(requests=60, per="minute"),),
        automated_collection=False,
    )
    cases = (
        Case(
            name="fetch_all",
            operation=Capability.FETCH,
            argument=Query(series=("TOYGDP",), vintage="all", max_observations=24),
        ),
        Case(name="vintages_ok", operation=Capability.VINTAGES, argument="TOYGDP"),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("NOSUCHSERIES",), vintage="all", max_observations=24
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.VINTAGES,
            argument="TOYLIMITED",
            expect=RateLimitError,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """One request per series for every real-time period."""
        return tuple(
            Request(
                host=VINTAGE_HOST,
                path=request_path("v1", "observations"),
                params=(
                    ("series", series),
                    ("realtime_start", "1776-07-04"),
                    ("realtime_end", _CURRENT),
                ),
                series=series,
            )
            for series in query.series
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """A series whose rows carry their real-time periods."""
        payload = _object(
            responses[0].json(provider="toy_vintage"), "toy_vintage", "a body"
        )
        rows = payload.get("observations")
        if not isinstance(rows, list):
            msg = "toy_vintage sent no observations"
            raise ResponseError(msg, provider="toy_vintage")
        index, values, periods = [], [], []
        for row in rows:
            entry = _object(row, "toy_vintage", "an observation")
            index.append(_day(entry.get("date"), "toy_vintage"))
            values.append(_percent(entry.get("value")))
            end = _day(entry.get("realtime_end"), "toy_vintage")
            periods.append(
                RealtimePeriod(
                    _day(entry.get("realtime_start"), "toy_vintage"),
                    None if end.isoformat() == _CURRENT else end,
                )
            )
        meta = SeriesMeta(
            provider="toy_vintage",
            series_id=query.series[0],
            title=_text(payload, "title", "toy_vintage"),
            unit=UnitRecord(text="Percent Change, Annual Rate", kind=UnitKind.RATE),
            frequency=ObservationFrequency.QUARTERLY,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
            source_dating=DateConvention.PERIOD_END,
            terms=TOY_VINTAGE_TERMS,
        )
        return Series(tuple(index), tuple(values), meta, tuple(periods))

    def build_vintages(self, series_id: str) -> Sequence[Request]:
        """A single request for the dates the series changed."""
        return (
            Request(
                host=VINTAGE_HOST,
                path=request_path("v1", "vintagedates"),
                params=(("series", series_id),),
                series=series_id,
            ),
        )

    def parse_vintages(
        self, responses: Sequence[Response], series_id: str
    ) -> Sequence[dt.date]:
        """The vintage dates, as the source lists them."""
        payload = _object(
            responses[0].json(provider="toy_vintage"), "toy_vintage", "a body"
        )
        dates = payload.get("vintage_dates")
        if not isinstance(dates, list):
            msg = "toy_vintage sent no vintage_dates"
            raise ResponseError(msg, provider="toy_vintage")
        return [_day(raw, "toy_vintage") for raw in dates]

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Replace every observed value with a synthetic one."""
        import json  # noqa: PLC0415 - only the recorder needs it

        payload = json.loads(response.body)
        for position, row in enumerate(payload.get("observations", ())):
            row["value"] = f"{synthetic_value(seed, position):.4f}"
        return Response(
            response.status,
            json.dumps(payload, separators=(",", ":")).encode(),
            response.retrieved_at,
            response.headers,
        )
