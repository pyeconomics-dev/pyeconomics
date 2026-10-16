# tests/providers/test_provider_fred.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""FRED and ALFRED's quirks, offline: units, dates, vintages, copyright, v2, errors.

Each test answers the provider's requests with ALFRED-shaped bodies whose
numbers are invented; nothing here is FRED data (its terms forbid storing any).
The one test that reads FRED is ``test_live_alfred_*`` (``-m live``): it pins a
first release and a later revision of real GDP growth, each cited to BEA's own
news release.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
from cache_support import no_database
from canned import Canned, http, ok, param, rounded
from fakes import FakePool, FakeRaw
from leakcheck import LeakCheck, canary

from pyeconomics.data import (
    CredentialError,
    DataError,
    Query,
    ResponseError,
    SeriesNotFoundError,
    Table,
    Vintage,
    config,
)
from pyeconomics.data.providers.fred import (
    FRED_NOTICE,
    FRED_TERMS,
    Fred,
    copyright_terms,
)
from pyeconomics.data.transport.base import Request
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    Weekday,
)

UNRATE = {
    "id": "UNRATE",
    "title": "Unemployment Rate",
    "frequency": "Monthly",
    "frequency_short": "M",
    "units": "Percent",
    "seasonal_adjustment": "Seasonally Adjusted",
    "seasonal_adjustment_short": "SA",
    "notes": "The unemployment rate.",
}
GDP = {
    "id": "A191RL1Q225SBEA",
    "title": "Real Gross Domestic Product",
    "frequency": "Quarterly",
    "frequency_short": "Q",
    "units": "Percent Change from Preceding Period",
    "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
    "seasonal_adjustment_short": "SAAR",
    "notes": "",
}
PUBLIC = [{"name": "public domain: citation requested", "group_id": "cc"}]


def row(
    date: str, value: str, start: str = "2026-10-15", end: str = "2026-10-15"
) -> dict[str, str]:
    return {"date": date, "value": value, "realtime_start": start, "realtime_end": end}


def route(
    entry: dict[str, Any],
    rows: list[dict[str, str]],
    tags: list[dict[str, str]] = PUBLIC,
) -> Canned:
    def answer(request: Request) -> Any:
        if request.path == "/fred/series":
            return ok({"seriess": [entry]})
        if request.path == "/fred/series/tags":
            return ok({"tags": tags})
        return ok({"observations": rows})

    return Canned(answer)


# --- units, dates and missing values ------------------------------------------


def test_a_percent_series_is_a_decimal_indexed_by_period_ends() -> None:
    transport = route(
        UNRATE,
        [row("2025-02-01", "4.1"), row("2025-01-01", "."), row("2024-12-01", "4.2")],
    )
    series = Fred().fetch(
        Query(series=("UNRATE",), max_observations=3), transport=transport
    )
    assert isinstance(series, Series)
    assert series.index == (
        dt.date(2024, 12, 31),
        dt.date(2025, 1, 31),
        dt.date(2025, 2, 28),
    )
    assert rounded(series.values) == (0.042, None, 0.041)
    meta = series.meta
    assert meta.unit.kind is not None
    assert meta.unit.kind.value == "rate"
    assert meta.source_dating is DateConvention.PERIOD_START
    assert meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED
    assert meta.terms == FRED_TERMS
    assert meta.notes == ("copyright: public domain, citation requested",)
    observations = transport.sent[2]
    assert (param(observations, "sort_order"), param(observations, "limit")) == (
        "desc",
        "3",
    )
    assert param(observations, "realtime_start") is None


def test_a_date_window_asks_from_new_year_and_keeps_the_periods_that_end_in_it() -> (
    None
):
    rows = [
        row("2024-07-01", "1.0"),
        row("2024-10-01", "2.0"),
        row("2025-01-01", "3.0"),
    ]
    transport = route({**GDP, "units": "Billions of Chained 2017 Dollars"}, rows)
    series = Fred().fetch(
        Query(series=("GDPC1",), start=dt.date(2024, 10, 1), end=dt.date(2025, 3, 31)),
        transport=transport,
    )
    assert series.index == (dt.date(2024, 12, 31), dt.date(2025, 3, 31))
    assert isinstance(series, Series)
    assert series.values == (2.0, 3.0)
    assert isinstance(series, Series)
    unit = series.meta.unit
    assert (unit.kind.value if unit.kind else None, unit.scale, unit.currency) == (
        "money",
        1e9,
        "USD",
    )
    observations = transport.sent[2]
    assert param(observations, "observation_start") == "2024-01-01"
    assert param(observations, "observation_end") == "2025-03-31"


@pytest.mark.parametrize(
    ("units", "kind", "scale"),
    [
        ("Thousands of Persons", "count", 1e3),
        ("Index 1982-1984=100", "index_level", 1.0),
        ("Basis Points", None, 1.0),
        ("U.S. Dollars to One Euro", None, 1.0),
    ],
)
def test_units_are_read_from_freds_text(
    units: str, kind: str | None, scale: float
) -> None:
    series = Fred().fetch(
        Query(series=("X1",), max_observations=1),
        transport=route({**UNRATE, "units": units}, [row("2025-01-01", "12.5")]),
    )
    assert isinstance(series, Series)
    found = series.meta.unit
    assert (found.kind.value if found.kind else None, found.scale) == (kind, scale)
    assert isinstance(series, Series)
    assert series.values == (12.5,)


def test_a_weekly_series_ends_its_weeks_on_freds_named_day() -> None:
    entry = {
        **UNRATE,
        "frequency": "Weekly, Ending Saturday",
        "frequency_short": "W",
        "units": "Number",
    }
    series = Fred().fetch(
        Query(series=("ICSA",), max_observations=2),
        transport=route(
            entry, [row("2025-01-11", "210000"), row("2025-01-04", "201000")]
        ),
    )
    assert series.meta.frequency is ObservationFrequency.WEEKLY
    assert series.meta.week_ends_on is Weekday.SATURDAY
    assert series.meta.source_dating is DateConvention.PERIOD_END


def test_a_daily_series_is_dated_by_its_day() -> None:
    entry = {
        **UNRATE,
        "frequency": "Daily",
        "frequency_short": "D",
        "seasonal_adjustment_short": "NA",
    }
    series = Fred().fetch(
        Query(series=("DGS10",), max_observations=2),
        transport=route(entry, [row("2025-06-03", "4.46"), row("2025-06-02", ".")]),
    )
    assert series.index == (dt.date(2025, 6, 2), dt.date(2025, 6, 3))
    assert series.meta.source_dating is DateConvention.POINT_IN_TIME
    assert isinstance(series, Series)
    assert series.meta.seasonal_adjustment is SeasonalAdjustment.NOT_APPLICABLE


def test_an_undocumented_seasonal_adjustment_is_refused() -> None:
    entry = {**UNRATE, "seasonal_adjustment_short": "ZZ"}
    with pytest.raises(ResponseError, match="seasonal adjustment"):
        Fred().fetch(Query(series=("X1",)), transport=route(entry, []))


def test_several_series_share_one_index_and_vintages_take_one() -> None:
    def answer(request: Request) -> Any:
        series_id = param(request, "series_id")
        if request.path == "/fred/series":
            return ok({"seriess": [{**UNRATE, "id": series_id}]})
        if request.path == "/fred/series/tags":
            return ok({"tags": PUBLIC})
        dates = ["2025-01-01", "2025-02-01"] if series_id == "A1" else ["2025-02-01"]
        return ok({"observations": [row(day, "1.0") for day in dates]})

    table = Fred().fetch(Query(series=("A1", "B2")), transport=Canned(answer))
    assert isinstance(table, Table)
    assert table.data == ((0.01, 0.01), (None, 0.01))
    with pytest.raises(DataError, match="one series at a time"):
        Fred().build_requests(Query(series=("A1", "B2"), vintage="all"))


def test_a_table_refuses_mixed_frequencies() -> None:
    def answer(request: Request) -> Any:
        series_id = param(request, "series_id")
        entry = UNRATE if series_id == "A1" else GDP
        if request.path == "/fred/series":
            return ok({"seriess": [{**entry, "id": series_id}]})
        if request.path == "/fred/series/tags":
            return ok({"tags": PUBLIC})
        return ok({"observations": [row("2025-01-01", "1.0")]})

    with pytest.raises(DataError, match="one frequency"):
        Fred().fetch(Query(series=("A1", "B2")), transport=Canned(answer))


# --- ALFRED's vintages ---------------------------------------------------------

#: ALFRED-shaped rows for one quarter: an advance estimate, a second estimate
#: and a revision still current. The numbers are invented.
REVISIONS = [
    row("2023-07-01", "4.9", "2023-10-26", "2023-11-28"),
    row("2023-07-01", "5.2", "2023-11-29", "2023-12-20"),
    row("2023-07-01", "4.4", "2023-12-21", "9999-12-31"),
    row("2023-10-01", "3.3", "2024-01-25", "9999-12-31"),
]


def vintage_series(vintage: str) -> Series:
    transport = route(GDP, REVISIONS)
    series = Fred().fetch(
        Query(series=("A191RL1Q225SBEA",), vintage=vintage), transport=transport
    )
    observations = transport.sent[2]
    assert param(observations, "realtime_start") == "1776-07-04"
    assert param(observations, "realtime_end") == "9999-12-31"
    assert param(observations, "output_type") == "1"
    assert isinstance(series, Series)
    return series


def test_all_vintages_keep_every_real_time_period() -> None:
    series = vintage_series("all")
    assert series.has_realtime
    assert len(series) == len(REVISIONS)
    assert series.realtime is not None
    assert series.realtime[2].realtime_end is None
    assert series.realtime[0].realtime_end == dt.date(2023, 11, 28)


def test_first_release_as_of_and_latest_select_the_right_values() -> None:
    q3, q4 = dt.date(2023, 9, 30), dt.date(2023, 12, 31)
    first = vintage_series("first_release")
    assert dict(zip(first.index, first.values, strict=True)) == {
        q3: pytest.approx(0.049),
        q4: pytest.approx(0.033),
    }
    as_of = vintage_series("as_of:2023-12-01")
    assert dict(zip(as_of.index, as_of.values, strict=True)) == {
        q3: pytest.approx(0.052)
    }
    later = vintage_series("as_of:2024-06-30")
    assert dict(zip(later.index, later.values, strict=True)) == {
        q3: pytest.approx(0.044),
        q4: pytest.approx(0.033),
    }
    before = vintage_series("as_of:2023-10-25")
    assert len(before) == 0


def test_vintage_dates_come_back_sorted_and_distinct() -> None:
    body = {"vintage_dates": ["2023-11-29", "2023-10-26", "2023-11-29"]}
    days = Fred().vintages("A191RL1Q225SBEA", transport=Canned(lambda _: ok(body)))
    assert days == (dt.date(2023, 10, 26), dt.date(2023, 11, 29))


# --- copyright gates -------------------------------------------------------------


@pytest.mark.parametrize(
    ("tags", "notes", "first_note", "restricted"),
    [
        (
            [{"name": "copyrighted: pre-approval required", "group_id": "cc"}],
            "",
            "copyright: pre-approval required",
            True,
        ),
        (
            [
                {"name": "copyrighted: citation required", "group_id": "cc"},
                {"name": "moody's", "group_id": "src"},
            ],
            "",
            "copyright: pre-approval required",
            True,
        ),
        (
            [{"name": "copyrighted: citation required", "group_id": "cc"}],
            "",
            "copyright: citation required",
            True,
        ),
        ([], "Copyright, 2026, Some Owner.", "copyright: citation required", True),
        (
            PUBLIC,
            "Copyright notes that do not matter here.",
            "copyright: public domain, citation requested",
            False,
        ),
        ([], "", None, False),
    ],
    ids=[
        "pre-approval",
        "moodys-overrides-label",
        "citation",
        "notes-say-copyright",
        "public-domain",
        "untagged",
    ],
)
def test_copyright_tags_set_the_notice_and_notes(
    tags: list[dict[str, str]],
    notes: str,
    first_note: str | None,
    restricted: bool,  # noqa: FBT001 - a parametrized flag
) -> None:
    terms, found = copyright_terms(tags, notes)
    assert (found[0] if found else None) == first_note
    assert (terms.notice != FRED_NOTICE) is restricted
    assert terms.notice is not None
    assert terms.notice.startswith(FRED_NOTICE)
    assert (terms.terms_url, terms.licence, terms.cache) == (
        FRED_TERMS.terms_url,
        FRED_TERMS.licence,
        FRED_TERMS.cache,
    )


def test_a_moodys_series_says_pre_approval_on_its_frame() -> None:
    tags = [
        {"name": "moody's", "group_id": "src"},
        {"name": "copyrighted: citation required", "group_id": "cc"},
    ]
    series = Fred().fetch(
        Query(series=("BAA",), max_observations=1),
        transport=route({**UNRATE, "id": "BAA"}, [row("2025-01-01", "6.0")], tags),
    )
    assert "pre-approval" in (series.meta.terms.notice or "")
    assert any(note.startswith("moodys:") for note in series.meta.notes)


# --- search and describe --------------------------------------------------------


def test_search_and_describe_read_freds_series_objects() -> None:
    hits = Fred().search(
        "unemployment",
        limit=1,
        transport=Canned(lambda _: ok({"seriess": [UNRATE, GDP]})),
    )
    assert [(hit.series_id, hit.frequency) for hit in hits] == [
        ("UNRATE", ObservationFrequency.MONTHLY)
    ]

    def answer(request: Request) -> Any:
        return ok(
            {"seriess": [GDP]} if request.path == "/fred/series" else {"tags": PUBLIC}
        )

    meta = Fred().describe("A191RL1Q225SBEA", transport=Canned(answer))
    assert meta.frequency is ObservationFrequency.QUARTERLY
    assert (
        meta.seasonal_adjustment is SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE
    )


# --- v2 bulk release observations --------------------------------------------------


def release_page(
    series: list[dict[str, Any]], *, more: Any = False, cursor: str | None = None
) -> Any:
    body: dict[str, Any] = {
        "has_more": more,
        "release": {"release_id": 53, "name": "Gross Domestic Product"},
        "series": series,
    }
    if cursor:
        body["next_cursor"] = cursor
    return ok(body)


def bulk_entry(series_id: str, dates: list[str]) -> dict[str, Any]:
    return {
        "series_id": series_id,
        "title": f"Series {series_id}",
        "frequency": "Quarterly",
        "units": "Percent",
        "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
        "copyright_id": None,
        "notes": "",
        "observations": [{"date": day, "value": "2.0"} for day in dates],
    }


def test_a_release_is_one_paged_v2_request_that_asks_for_the_header_key() -> None:
    pages = iter(
        [
            release_page(
                [bulk_entry("A1", ["2025-01-01"])], more="true", cursor="A1,2025-01-01"
            ),
            release_page(
                [bulk_entry("A1", ["2025-04-01"]), bulk_entry("B2", ["2025-04-01"])]
            ),
        ]
    )
    transport = Canned(lambda _: next(pages))
    table = Fred().fetch(Query(series=("release:53",)), transport=transport)
    assert isinstance(table, Table)
    assert [column.name for column in table.columns] == ["A1", "B2"]
    assert table.index == (dt.date(2025, 3, 31), dt.date(2025, 6, 30))
    assert table.data == ((0.02, 0.02), (None, 0.02))
    assert table.meta.title == "Gross Domestic Product"
    first, second = transport.sent
    assert first.path == "/fred/v2/release/observations"
    assert first.key_placement == "header"
    assert param(first, "next_cursor") is None
    assert param(second, "next_cursor") == "A1,2025-01-01"


def test_a_release_keeps_the_ids_named_after_it_and_names_a_missing_one() -> None:
    page = release_page(
        [bulk_entry("A1", ["2025-01-01"]), bulk_entry("B2", ["2025-01-01"])]
    )
    table = Fred().fetch(
        Query(series=("release:53", "B2")), transport=Canned(lambda _: page)
    )
    assert isinstance(table, Table)
    assert [column.name for column in table.columns] == ["B2"]
    with pytest.raises(SeriesNotFoundError):
        Fred().fetch(
            Query(series=("release:53", "C3")), transport=Canned(lambda _: page)
        )
    with pytest.raises(DataError, match="comes first"):
        Fred().build_requests(Query(series=("GDP", "release:53")))


def test_a_page_that_says_more_without_a_cursor_is_refused() -> None:
    page = release_page([bulk_entry("A1", ["2025-01-01"])], more=True)
    with pytest.raises(ResponseError, match="no cursor"):
        Fred().fetch(Query(series=("release:53",)), transport=Canned(lambda _: page))


# --- errors ------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("message", "error"),
    [
        (
            "Bad Request.  The value for variable api_key is not registered.",
            CredentialError,
        ),
        ("Bad Request.  The series does not exist.", SeriesNotFoundError),
        ("Bad Request.  Something else.", ResponseError),
    ],
)
def test_freds_400_messages_map_to_the_taxonomy(
    message: str, error: type[Exception]
) -> None:
    answer = ok({"error_code": 400, "error_message": message}, status=400)
    with pytest.raises(error):
        Fred().fetch(Query(series=("UNRATE",)), transport=Canned(lambda _: answer))


def test_a_400_without_json_falls_to_the_default_mapping() -> None:
    with pytest.raises(ResponseError):
        Fred().fetch(
            Query(series=("UNRATE",)),
            transport=Canned(lambda _: ok(b"<html>", status=400)),
        )


# --- never stored, never leaked ------------------------------------------------------


def test_fred_never_reaches_the_cache_or_creates_a_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    no_database(monkeypatch)
    for _ in range(2):  # the second fetch would be a cache hit for a storable source
        transport = route(UNRATE, [row("2025-01-01", "4.0")])
        Fred().fetch(Query(series=("UNRATE",), max_observations=1), transport=transport)
        assert len(transport.sent) == 3
    assert not config.cache_dir().exists()


def series_answers() -> list[FakeRaw]:
    return [
        FakeRaw(200, json.dumps(body).encode(), {"Content-Type": "application/json"})
        for body in (
            {"seriess": [UNRATE]},
            {"tags": PUBLIC},
            {"observations": [row("2025-01-01", "4.0")]},
        )
    ]


def test_a_canary_key_in_the_v1_query_string_reaches_no_sink() -> None:
    held = canary("fred")
    pool = FakePool(*series_answers())
    check = LeakCheck(held)
    series = check.run(
        lambda: Fred().fetch(
            Query(series=("UNRATE",), max_observations=1),
            key=held.value,
            transport=http(pool),
        )
    )
    assert series is not None
    assert all(held.value in call.url for call in pool.calls)
    assert all("Authorization" not in call.headers for call in pool.calls)
    check.add("series", series.canonical_json() if isinstance(series, Series) else b"")
    check.assert_clean()


def test_a_canary_key_in_the_v2_authorization_header_reaches_no_sink() -> None:
    held = canary("fred")
    page = {"has_more": False, "series": [bulk_entry("A1", ["2025-01-01"])]}
    pool = FakePool(
        FakeRaw(200, json.dumps(page).encode(), {"Content-Type": "application/json"})
    )
    check = LeakCheck(held)
    table = check.run(
        lambda: Fred().fetch(
            Query(series=("release:53",)), key=held.value, transport=http(pool)
        )
    )
    assert table is not None
    (call,) = pool.calls
    assert call.headers["Authorization"] == f"Bearer {held.value}"
    assert held.value not in call.url
    failing = FakePool(
        *[FakeRaw(503, f'{{"message": "bad {held.value}"}}'.encode())] * 5
    )
    check.run(
        lambda: Fred().fetch(
            Query(series=("release:53",)), key=held.value, transport=http(failing)
        )
    )
    check.assert_clean()


# --- recording -----------------------------------------------------------------------


def test_synthesize_replaces_every_value_and_keeps_the_structure() -> None:
    request = Request(host="api.stlouisfed.org", path="/fred/series/observations")
    body = {
        "observations": [row("2025-01-01", "4.1"), row("2025-02-01", ".")],
        "count": 2,
    }
    made = Fred().synthesize(request, ok(body), seed="UNRATE")
    rows = json.loads(made.body)["observations"]
    assert rows[0]["value"] != "4.1"
    assert 0.0 <= float(rows[0]["value"]) <= 1.0
    assert rows[1]["value"] == "."
    assert [r["date"] for r in rows] == ["2025-01-01", "2025-02-01"]
    page = {
        "has_more": True,
        "next_cursor": "x",
        "series": [bulk_entry(f"S{i}", ["2025-01-01"] * 30) for i in range(6)],
    }
    trimmed = json.loads(Fred().synthesize(request, ok(page), seed="r").body)
    assert len(trimmed["series"]) == 4
    assert all(len(entry["observations"]) == 24 for entry in trimmed["series"])
    assert trimmed["has_more"] is False
    assert "next_cursor" not in trimmed
    search = {"seriess": [{**UNRATE, "notes": "x" * 500}]}
    assert (
        len(
            json.loads(Fred().synthesize(request, ok(search), seed="s").body)[
                "seriess"
            ][0]["notes"]
        )
        == 160
    )


# --- live: ALFRED's first release against a later revision (ROADMAP 3.8) ----------


@pytest.mark.live
def test_live_alfred_returns_the_first_release_and_a_later_revision() -> None:
    """Real GDP growth, 2023 Q3 (A191RL1Q225SBEA, percent, SAAR), as ALFRED keeps it.

    - First published as 4.9 percent: BEA, "Gross Domestic Product, Third Quarter
      2023 (Advance Estimate)", 2023-10-26, Table 1 ("Real Gross Domestic Product
      and Related Measures: Percent Change From Preceding Period"), line 1.
    - Revised to 4.4 percent: BEA, "Gross Domestic Product (Third Estimate),
      Corporate Profits (Revised Estimate), and GDP by Industry, Second Quarter
      2024 and Annual Update", 2024-09-26, Table 1, line 1.

    ALFRED's vintages carry each value from its release date: 4.9 as of
    2023-11-01, 4.4 as of 2025-01-01.
    """
    from pyeconomics.data.transport import default_transport  # noqa: PLC0415

    quarter = dt.date(2023, 9, 30)
    fred = Fred()

    def value(vintage: str) -> float | None:
        series = fred.fetch(
            Query(
                series=("A191RL1Q225SBEA",),
                start=dt.date(2023, 7, 1),
                end=dt.date(2023, 9, 30),
                vintage=vintage,
            ),
            transport=default_transport(),
        )
        assert isinstance(series, Series)
        return dict(zip(series.index, series.values, strict=True))[quarter]

    assert value("first_release") == pytest.approx(0.049)
    assert value("as_of:2023-11-01") == pytest.approx(0.049)
    assert value("as_of:2025-01-01") == pytest.approx(0.044)
    selected = Vintage.as_of(dt.date(2025, 1, 1)).label
    assert selected == "as_of:2025-01-01"


# --- the recorded ALFRED cassette (synthetic values) ------------------------------


def test_the_recorded_alfred_cassette_selects_each_vintage_from_its_rows() -> None:
    """Every vintage replays from the one cassette: the requests do not differ.

    The expected values are worked out here from the rows themselves, so the
    test holds whatever synthetic numbers the cassette carries.
    """
    from provider_contract import replay, replay_key  # noqa: PLC0415

    (case,) = [c for c in Fred.cases if c.name == "fetch_vintages"]
    query = case.argument
    assert isinstance(query, Query)

    def fetch(vintage: str) -> Series:
        found = Fred().fetch(
            query.model_copy(update={"vintage": vintage}),
            key=replay_key(Fred, case),
            transport=replay("fred", case),
        )
        assert isinstance(found, Series)
        return found

    every = fetch("all")
    assert every.realtime is not None
    rows = list(zip(every.index, every.realtime, every.values, strict=True))
    assert len({period.realtime_start for _, period, _ in rows}) > 1, "several vintages"
    first = {day: value for day, _, value in reversed(rows)}
    picked = fetch("first_release")
    assert dict(zip(picked.index, picked.values, strict=True)) == first
    for _, period, _ in rows:
        on = period.realtime_start
        expected = {day: value for day, p, value in rows if p.covers(on)}
        chosen = fetch(f"as_of:{on.isoformat()}")
        assert dict(zip(chosen.index, chosen.values, strict=True)) == expected
    latest = {day: value for day, _, value in rows}
    newest = fetch("as_of:2026-10-01")
    assert dict(zip(newest.index, newest.values, strict=True)) == latest
