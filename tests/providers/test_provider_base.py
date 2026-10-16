# tests/providers/test_provider_base.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The provider contract's base class: queries, info, gates and the error taxonomy."""

from __future__ import annotations

import datetime as dt
import sys
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError
from stubs import HOST, NOW, Scripted, Stub, answer, series_for, stub_info
from toys import ToyJson

from pyeconomics.core import InputError
from pyeconomics.data import (
    Access,
    Authentication,
    AuthKind,
    Capability,
    Case,
    CredentialError,
    DataError,
    DataProvider,
    KeyPlacement,
    LicenceClass,
    LicenceError,
    ObservationFrequency,
    Platform,
    Query,
    RateLimit,
    RateLimitError,
    RealtimePeriod,
    ResponseError,
    SearchHit,
    Series,
    SeriesMeta,
    SeriesNotFoundError,
    Table,
    TransportError,
    configure,
)
from pyeconomics.data.providers.base import current_platform, tail
from pyeconomics.data.transport.base import Request

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pyeconomics.data.transport.base import Response

# --- Query --------------------------------------------------------------------


def test_a_query_names_series_a_window_a_size_and_a_vintage() -> None:
    query = Query.model_validate(
        {"series": ("GDPC1", "^GSPC"), "start": "2020-01-31", "end": "2021-01-31"}
    )
    assert query.start == dt.date(2020, 1, 31)
    assert query.max_observations == 100_000
    assert query.vintage == "latest"
    assert query.vintage_selector.label == "latest"


@pytest.mark.parametrize(
    "changes",
    [
        {"series": ()},
        {"series": ("A", "A")},
        {"series": ("has space",)},
        {"series": ("../etc",)},
        {"series": ("a?b=1",)},
        {"series": ("x" * 129,)},
        {"series": tuple(f"S{n}" for n in range(1_001))},
        {"start": "1699-12-31"},
        {"end": "2201-01-01"},
        {"start": "2021-01-01", "end": "2020-01-01"},
        {"max_observations": 0},
        {"max_observations": 100_001},
        {"vintage": "yesterday"},
        {"vintage": "xlatest"},
        {"vintage": "as_of:2020-13-01"},
        {"vintage": "as_of:1500-01-01"},
        {"surprise": 1},
    ],
)
def test_a_query_is_bounded(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        Query(**{"series": ("A",), **changes})


def test_a_query_is_frozen_and_hides_its_input_in_errors() -> None:
    query = Query(series=("A",))
    with pytest.raises(ValidationError):
        query.max_observations = 5  # type: ignore[misc]
    with pytest.raises(ValidationError) as caught:
        Query(series=("secret value with spaces",))
    assert "secret value" not in str(caught.value)


def test_a_thousand_series_ids_are_allowed() -> None:
    assert len(Query(series=tuple(f"S{n}" for n in range(1_000))).series) == 1_000


# --- ProviderInfo and its parts -----------------------------------------------


def test_info_turns_sequences_into_tuples_and_values_into_members() -> None:
    info = stub_info(
        capabilities=["fetch", "search"],
        platforms=["linux"],
        hosts=[HOST],
        access="https",
    )
    assert info.capabilities == (Capability.FETCH, Capability.SEARCH)
    assert info.platforms == (Platform.LINUX,)
    assert info.hosts == (HOST,)
    assert info.access is Access.HTTPS
    assert hash(info.rate_limits)


def test_info_keeps_what_it_cannot_coerce_for_the_rules_to_report() -> None:
    info = stub_info(capabilities=("fetchh",), access="ftp", hosts="not a tuple")
    assert info.capabilities == ("fetchh",)
    assert info.access == "ftp"
    assert str(info.hosts) == "not a tuple"


def test_the_key_variable_is_the_providers_id_in_capitals() -> None:
    keyed = stub_info(id="fred", auth=Authentication.key("api_key", KeyPlacement.QUERY))
    assert keyed.key_variable == "FRED_API_KEY"
    assert stub_info().key_variable is None
    assert stub_info(auth=Authentication.contact()).key_variable is None


def test_info_says_which_platforms_it_supports() -> None:
    info = stub_info(platforms=(Platform.WINDOWS,))
    assert info.supports(Platform.WINDOWS)
    assert not info.supports(Platform.LINUX)


def test_authentication_describes_a_key_a_contact_or_nothing() -> None:
    assert Authentication().kind is AuthKind.NONE
    auth = Authentication.key(
        "Authorization", KeyPlacement.HEADER, scheme="Bearer", required=False
    )
    assert (auth.placement, auth.scheme, auth.required) == (
        KeyPlacement.HEADER,
        "Bearer",
        False,
    )
    assert Authentication.contact().kind is AuthKind.CONTACT


@pytest.mark.parametrize(
    ("per", "seconds"), [("second", 1), ("minute", 60), ("day", 86_400)]
)
def test_a_rate_limit_knows_its_window(per: str, seconds: int) -> None:
    assert RateLimit(requests=3, per=per).window_seconds == seconds  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("linux", Platform.LINUX),
        ("linux2", Platform.LINUX),
        ("darwin", Platform.MACOS),
        ("win32", Platform.WINDOWS),
        ("cygwin", None),
        ("emscripten", Platform.PYODIDE),
        ("aix", None),
    ],
)
def test_the_platform_follows_sys_platform(
    monkeypatch: pytest.MonkeyPatch, name: str, expected: Platform | None
) -> None:
    monkeypatch.setattr(sys, "platform", name)
    assert current_platform() is expected


def test_a_search_hit_checks_its_text_and_frequency() -> None:
    hit = SearchHit(
        series_id="GDP",
        title="Gross domestic product",
        frequency=ObservationFrequency.MONTHLY,
    )
    assert hit.frequency is not None
    for bad in (
        {"series_id": "bad id", "title": "t"},
        {"series_id": "A", "title": ""},
        {"series_id": "A", "title": "t", "unit": "see https://x"},
        {"series_id": "A", "title": "t", "frequency": "hourly"},
    ):
        with pytest.raises(InputError):
            SearchHit(**bad)  # type: ignore[arg-type]


def test_a_case_fits_its_operation() -> None:
    assert Case(name="ok", operation=Capability.SEARCH, argument="x").expect is None
    for bad in (
        {"operation": Capability.FETCH, "argument": "text"},
        {"operation": Capability.SEARCH, "argument": Query(series=("A",))},
        {"operation": Capability.BULK, "argument": "x"},
        {"operation": Capability.SEARCH, "argument": "x", "name": "Not snake"},
    ):
        with pytest.raises(InputError):
            Case(**{"name": "case", **bad})  # type: ignore[arg-type]


def test_tail_keeps_the_most_recent_rows_of_a_series_and_a_table() -> None:
    series = series_for(dates=5)
    assert tail(series, 2).index == series.index[-2:]
    assert tail(series, 9) is series
    toy = ToyJson()
    # a table, through the toy's fetch_table cassette
    from provider_contract import replay  # noqa: PLC0415

    case = next(c for c in ToyJson.cases if c.name == "fetch_table")
    table = toy.run_case(case, transport=replay("toy_json", case))
    assert isinstance(table, Table)
    short = tail(table, 2)
    assert short.index == table.index[-2:]
    assert short.data[0] == table.data[0][-2:]


def test_tail_keeps_each_rows_real_time_period() -> None:
    from provider_contract import replay  # noqa: PLC0415
    from toys import ToyVintage  # noqa: PLC0415

    case = next(c for c in ToyVintage.cases if c.name == "fetch_all")
    frame = ToyVintage().run_case(case, transport=replay("toy_vintage", case))
    assert isinstance(frame, Series)
    assert frame.realtime is not None
    last = tail(frame, 2)
    assert last.realtime == frame.realtime[-2:]


# --- the public operations are final ------------------------------------------


@pytest.mark.parametrize(
    "name", ["fetch", "search", "describe", "vintages", "run_case"]
)
def test_a_subclass_cannot_override_a_gated_operation(name: str) -> None:
    with pytest.raises(TypeError, match=name):
        type("Cheat", (DataProvider,), {name: lambda self: None})


def test_a_hook_that_is_not_implemented_says_which() -> None:
    class Bare(DataProvider):
        info = stub_info()

    with pytest.raises(NotImplementedError, match="build_requests"):
        Bare().build_requests(Query(series=("A",)))
    with pytest.raises(NotImplementedError, match="synthesize"):
        Bare().synthesize(Request(host=HOST, path="/"), answer(), seed="s")


# --- fetch: gates, mapping and checks -----------------------------------------


def constant(value: object) -> Callable[[Sequence[Response]], object]:
    """Return a hook that answers ``value`` whatever the responses are."""
    return lambda _responses: value


def fetch(stub: Stub, transport: Scripted, **changes: Any) -> Any:
    return stub.fetch({"series": ("S",), **changes}, transport=transport)


def test_a_fetch_returns_the_parsed_series_stamped_with_the_retrieval_time() -> None:
    transport = Scripted(answer())
    result = fetch(Stub(), transport)
    assert isinstance(result, Series)
    assert result.meta.retrieved_at == NOW
    assert [s[1].host for s in transport.sent] == [HOST]


def test_a_fetch_keeps_the_time_a_provider_set() -> None:
    stub, when = Stub(), dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    stub.parsed = lambda _r, _q: series_for(retrieved_at=when)
    assert fetch(stub, Scripted(answer())).meta.retrieved_at == when


def test_the_latest_response_time_stamps_a_multi_request_fetch() -> None:
    stub = Stub()
    stub.requests = (
        Request(host=HOST, path="/v1/a", series="A"),
        Request(host=HOST, path="/v1/b", series="B"),
    )
    later = replace_time(answer(), NOW + dt.timedelta(seconds=5))
    result = fetch(stub, Scripted(answer(), later))
    assert result.meta.retrieved_at == NOW + dt.timedelta(seconds=5)


def replace_time(response: Any, when: dt.datetime) -> Any:
    return replace(response, retrieved_at=when)


def test_a_query_may_be_a_mapping_and_a_bad_one_is_an_input_error() -> None:
    stub = Stub()
    assert fetch(stub, Scripted(answer()), max_observations=2)
    with pytest.raises(InputError):
        stub.fetch({"series": ()}, transport=Scripted())
    with pytest.raises(InputError):
        stub.fetch(["not", "a", "mapping"], transport=Scripted())  # type: ignore[arg-type]
    other = Query(series=("S",), vintage="all")
    assert stub.fetch(other, transport=Scripted(answer()))


def test_a_fetch_trims_to_the_most_recent_observations() -> None:
    stub = Stub()
    stub.parsed = lambda _r, _q: series_for(dates=6)
    result = fetch(stub, Scripted(answer()), max_observations=2)
    assert len(result) == 2
    assert result.index[-1] == dt.date(2025, 6, 30)


def test_a_capability_the_provider_lacks_is_refused_before_any_request() -> None:
    class FetchOnly(Stub):
        info = stub_info()

    transport = Scripted()
    with pytest.raises(DataError, match="does not support search"):
        FetchOnly().search("x", transport=transport)
    assert transport.sent == []


def test_a_platform_the_provider_does_not_run_on_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class WindowsOnly(Stub):
        info = stub_info(platforms=(Platform.WINDOWS,))

    monkeypatch.setattr(sys, "platform", "linux")
    transport = Scripted()
    with pytest.raises(DataError, match="does not run on linux"):
        WindowsOnly().fetch(Query(series=("S",)), transport=transport)
    monkeypatch.setattr(sys, "platform", "aix")
    with pytest.raises(DataError, match="does not run on aix"):
        WindowsOnly().fetch(Query(series=("S",)), transport=transport)
    assert transport.sent == []


def test_a_vintage_the_source_does_not_keep_is_refused_before_any_request() -> None:
    class NoVintages(Stub):
        info = stub_info()

    transport = Scripted()
    for label in ("first_release", "as_of:2020-01-01"):
        with pytest.raises(DataError, match="keeps no vintages"):
            NoVintages().fetch(Query(series=("S",), vintage=label), transport=transport)
    assert transport.sent == []
    for label in ("latest", "all"):
        NoVintages().fetch(
            Query(series=("S",), vintage=label), transport=Scripted(answer())
        )


def test_a_vintage_is_selected_from_the_rows_a_provider_returns() -> None:
    stub = Stub()
    base = series_for(dates=2)
    rows = Series(
        (base.index[0], base.index[0], base.index[1]),
        (0.01, 0.02, 0.03),
        base.meta,
        (
            RealtimePeriod(dt.date(2025, 2, 1), dt.date(2025, 2, 9)),
            RealtimePeriod(dt.date(2025, 2, 10)),
            RealtimePeriod(dt.date(2025, 3, 1)),
        ),
    )
    stub.parsed = lambda _r, _q: rows
    assert fetch(stub, Scripted(answer()), vintage="first_release").values == (
        0.01,
        0.03,
    )
    assert fetch(stub, Scripted(answer()), vintage="latest").values == (0.02, 0.03)
    assert len(fetch(stub, Scripted(answer()), vintage="all")) == 3
    assert fetch(stub, Scripted(answer()), vintage="as_of:2025-02-05").values == (0.01,)


@pytest.mark.parametrize(
    ("status", "error", "text"),
    [
        (401, CredentialError, "HTTP 401"),
        (403, CredentialError, "HTTP 403"),
        (404, SeriesNotFoundError, "has no series 'S'"),
        (429, RateLimitError, "HTTP 429"),
        (500, TransportError, "HTTP 500"),
        (503, TransportError, "HTTP 503"),
        (400, ResponseError, "HTTP 400"),
        (301, ResponseError, "HTTP 301"),
    ],
)
def test_the_final_status_maps_to_the_error_taxonomy(
    status: int, error: type[DataError], text: str
) -> None:
    transport = Scripted(answer(status))
    with pytest.raises(error, match=text) as caught:
        fetch(Stub(), transport)
    assert caught.value.provider == "stub"
    assert caught.value.__context__ is None


def test_a_credential_error_names_the_variable_that_would_fix_it() -> None:
    class Keyed(Stub):
        info = stub_info(
            id="keyed", auth=Authentication.key("api_key", KeyPlacement.QUERY)
        )

    with pytest.raises(CredentialError, match="KEYED_API_KEY") as caught:
        fetch(Keyed(), Scripted(answer(401)))
    assert "keys.html" in str(caught.value)


def test_a_rate_limit_error_carries_the_retry_after() -> None:
    with pytest.raises(RateLimitError) as caught:
        fetch(Stub(), Scripted(answer(429, **{"retry-after": "45"})))
    assert caught.value.retry_after == 45.0
    with pytest.raises(RateLimitError) as without:
        fetch(Stub(), Scripted(answer(429)))
    assert without.value.retry_after is None


def test_a_missing_series_without_a_name_is_named_by_its_path() -> None:
    stub = Stub()
    stub.requests = (Request(host=HOST, path="/v1/things/42"),)
    with pytest.raises(SeriesNotFoundError, match="/v1/things/42"):
        fetch(stub, Scripted(answer(404)))


def test_a_provider_may_map_its_own_error_body_first() -> None:
    stub = Stub()
    stub.classify = lambda req, resp: (
        SeriesNotFoundError("stub", req.series or "?") if resp.status == 400 else None
    )
    with pytest.raises(SeriesNotFoundError):
        fetch(stub, Scripted(answer(400)))
    with pytest.raises(ResponseError):
        fetch(stub, Scripted(answer(422)))
    fetch(stub, Scripted(answer(200)))  # a success never reaches the hook's mapping


def test_the_default_exchange_stops_at_the_first_failure() -> None:
    stub = Stub()
    stub.requests = (
        Request(host=HOST, path="/v1/a", series="A"),
        Request(host=HOST, path="/v1/b", series="B"),
    )
    transport = Scripted(answer(404), answer())
    with pytest.raises(SeriesNotFoundError):
        fetch(stub, transport)
    assert len(transport.sent) == 1


def test_a_key_given_to_a_fetch_reaches_the_transport() -> None:
    transport = Scripted(answer())
    Stub().fetch(Query(series=("S",)), key="an-explicit-key-value", transport=transport)
    assert transport.sent[0][2] == "an-explicit-key-value"


@pytest.mark.parametrize(
    "built",
    [(), "text", [object()], tuple(Request(host=HOST, path="/") for _ in range(1_001))],
)
def test_a_provider_must_build_between_one_and_a_thousand_requests(built: Any) -> None:
    stub = Stub()
    stub.requests = built
    with pytest.raises(DataError, match="must build between 1 and 1000"):
        fetch(stub, Scripted())


def test_an_exchange_must_return_one_response_per_request() -> None:
    class Short(Stub):
        def exchange(self, requests: Any, *, key: Any, transport: Any) -> Any:
            return []

    with pytest.raises(DataError, match="a Response per request"):
        fetch(Short(), Scripted())


def test_a_session_exchange_still_has_every_status_checked() -> None:
    class Session(Stub):
        info = stub_info(access=Access.SESSION, hosts=(), rate_limits=())

        def exchange(self, requests: Any, *, key: Any, transport: Any) -> Any:
            return [answer(503) for _ in requests]

    with pytest.raises(TransportError):
        fetch(Session(), Scripted())


def test_parse_must_return_the_providers_own_frame() -> None:
    stub = Stub()
    stub.parsed = lambda _r, _q: series_for("someone_else")
    with pytest.raises(DataError, match="its own Series or Table"):
        fetch(stub, Scripted(answer()))
    stub.parsed = lambda _r, _q: "a string"
    with pytest.raises(DataError, match="its own Series or Table"):
        fetch(stub, Scripted(answer()))


def test_hosted_mode_refuses_a_series_whose_own_terms_bar_it() -> None:
    stub = Stub()
    restricted = stub.info.terms.with_overrides(licence=LicenceClass.LIBRARY_ONLY)
    stub.parsed = lambda _r, _q: series_for(terms=restricted)
    assert fetch(stub, Scripted(answer()))  # library mode serves it
    configure(mode="hosted")
    with pytest.raises(LicenceError, match="library-only"):
        fetch(stub, Scripted(answer()))


def test_hosted_mode_refuses_a_library_only_provider_before_any_request() -> None:
    class Library(Stub):
        info = replace(
            Stub.info,
            terms=replace(stub_info().terms, licence=LicenceClass.LIBRARY_ONLY),
        )

    configure(mode="hosted")
    transport = Scripted()
    for call in (
        lambda: Library().fetch(Query(series=("S",)), transport=transport),
        lambda: Library().search("x", transport=transport),
        lambda: Library().describe("S", transport=transport),
        lambda: Library().vintages("S", transport=transport),
    ):
        with pytest.raises(LicenceError):
            call()
    assert transport.sent == []


# --- search, describe and vintages --------------------------------------------


def test_search_returns_at_most_the_limit_of_hits() -> None:
    stub = Stub()
    hits = tuple(SearchHit(series_id=f"S{n}", title=f"Series {n}") for n in range(5))
    stub.searched = lambda _r: hits
    assert stub.search("rate", limit=5, transport=Scripted(answer())) == hits
    with pytest.raises(DataError, match="at most 3 SearchHit"):
        stub.search("rate", limit=3, transport=Scripted(answer()))
    stub.searched = lambda _r: ("not a hit",)
    with pytest.raises(DataError, match="SearchHit"):
        stub.search("rate", transport=Scripted(answer()))


@pytest.mark.parametrize("limit", [0, 101, True])
def test_search_bounds_its_limit(limit: int) -> None:
    with pytest.raises(InputError):
        Stub().search("rate", limit=limit, transport=Scripted())


def test_search_refuses_empty_text() -> None:
    with pytest.raises(InputError):
        Stub().search("   ", transport=Scripted())


def test_describe_returns_the_providers_own_metadata_with_a_time() -> None:
    stub = Stub()
    meta = series_for().meta
    stub.described = lambda _r: meta
    described = stub.describe("S", transport=Scripted(answer()))
    assert described.series_id == "S"
    assert described.retrieved_at == NOW
    stub.described = lambda _r: replace(meta, provider="other")
    with pytest.raises(DataError, match="its own SeriesMeta"):
        stub.describe("S", transport=Scripted(answer()))
    stub.described = lambda _r: "text"
    with pytest.raises(DataError, match="its own SeriesMeta"):
        stub.describe("S", transport=Scripted(answer()))


def test_describe_refuses_a_series_whose_terms_hosted_mode_bars() -> None:
    stub = Stub()
    stub.described = lambda _r: replace(
        series_for().meta,
        terms=stub.info.terms.with_overrides(licence=LicenceClass.BYOK),
    )
    configure(mode="hosted")
    with pytest.raises(LicenceError):
        stub.describe("S", transport=Scripted(answer()))


@pytest.mark.parametrize("series_id", ["", "a b", "../x", 7])
def test_describe_and_vintages_check_the_series_id(series_id: Any) -> None:
    with pytest.raises(InputError):
        Stub().describe(series_id, transport=Scripted())
    with pytest.raises(InputError):
        Stub().vintages(series_id, transport=Scripted())


def test_vintages_are_sorted_distinct_dates() -> None:
    stub = Stub()
    days = (dt.date(2008, 1, 30), dt.date(2008, 2, 28))
    stub.dated = lambda _r: list(days)
    assert stub.vintages("S", transport=Scripted(answer())) == days
    for bad in ([days[1], days[0]], [days[0], days[0]]):
        stub.dated = constant(bad)
        with pytest.raises(DataError, match="sorted, distinct"):
            stub.vintages("S", transport=Scripted(answer()))
    stub.dated = lambda _r: ["2008-01-30"]
    with pytest.raises(InputError):
        stub.vintages("S", transport=Scripted(answer()))


def test_run_case_dispatches_to_the_named_operation() -> None:
    stub = Stub()
    meta = series_for().meta
    stub.described = lambda _r: meta
    stub.dated = lambda _r: (dt.date(2008, 1, 30),)
    stub.searched = lambda _r: ()
    cases = [
        Case(name="a", operation=Capability.FETCH, argument=Query(series=("S",))),
        Case(name="b", operation=Capability.SEARCH, argument="x"),
        Case(name="c", operation=Capability.DESCRIBE, argument="S"),
        Case(name="d", operation=Capability.VINTAGES, argument="S"),
    ]
    results = [stub.run_case(c, transport=Scripted(answer())) for c in cases]
    assert [type(r) for r in results] == [Series, tuple, SeriesMeta, tuple]


# --- hooks left alone, and branches the happy paths skip ----------------------


def test_every_hook_a_provider_does_not_override_says_so() -> None:
    class Bare(DataProvider):
        info = stub_info()

    bare, query = Bare(), Query(series=("S",))
    calls: dict[str, Callable[[], object]] = {
        "build_requests": lambda: bare.build_requests(query),
        "parse": lambda: bare.parse([], query),
        "build_search": lambda: bare.build_search("x", 1),
        "parse_search": lambda: bare.parse_search([], "x", 1),
        "build_describe": lambda: bare.build_describe("S"),
        "parse_describe": lambda: bare.parse_describe([], "S"),
        "build_vintages": lambda: bare.build_vintages("S"),
        "parse_vintages": lambda: bare.parse_vintages([], "S"),
    }
    for name, call in calls.items():
        with pytest.raises(NotImplementedError, match=name):
            call()
    assert bare.classify_error(Request(host=HOST, path="/"), answer(500)) is None


def test_info_leaves_what_is_neither_text_nor_a_collection_for_the_rules() -> None:
    info = stub_info(capabilities=7, platforms=None, access=3)
    raw: object = (info.capabilities, info.platforms, info.access)
    assert raw == (7, None, 3)
    odd: object = Authentication(kind=5).kind  # type: ignore[arg-type]
    assert odd == 5


def test_describe_and_fetch_keep_a_retrieval_time_the_provider_set() -> None:
    stub, when = Stub(), dt.datetime(2020, 1, 1, tzinfo=dt.UTC)
    stub.described = lambda _r: replace(series_for().meta, retrieved_at=when)
    assert stub.describe("S", transport=Scripted(answer())).retrieved_at == when
    from provider_contract import replay  # noqa: PLC0415

    case = next(c for c in ToyJson.cases if c.name == "fetch_table")
    table = ToyJson().run_case(case, transport=replay("toy_json", case))
    assert isinstance(table, Table)
    stamped = replace(table, meta=replace(table.meta, retrieved_at=when))
    stub.parsed = lambda _r, _q: replace(
        stamped, meta=replace(stamped.meta, provider="stub")
    )
    kept = fetch(stub, Scripted(answer()))
    assert isinstance(kept, Table)
    assert kept.meta.retrieved_at == when
    stub.parsed = lambda _r, _q: replace(
        table, meta=replace(table.meta, provider="stub", retrieved_at=None)
    )
    assert fetch(stub, Scripted(answer())).meta.retrieved_at == NOW
