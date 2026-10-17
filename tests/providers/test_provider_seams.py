# tests/providers/test_provider_seams.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The contract's seams the first real providers needed (Phase 3 Step 6).

- a key slot per placement (``Authentication.alternates``) that a request names
  with ``Request.key_placement`` (FRED's v1 query parameter and v2 header);
- ``DataProvider.sends_key`` for the hooks of a source whose key is optional,
  ``credentials.withheld`` and a keyless ``Case`` (BLS's keyless v1);
- a limit that counts only requests without a key (``RateLimit.without_key``);
- paging through ``next_page`` (FRED v2's cursor);
- ``ProviderInfo.follow_redirects`` and ``classify_error`` for any status outside
  2xx (Census's key redirect);
- a recorder that simulates a 429 or a 5xx (``Case.simulate``), which no
  well-behaved client provokes.
"""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any, ClassVar, cast

import pytest
from canned import Canned, http, ok
from fakes import FakeClock, FakePool, FakeRaw
from stubs import HOST, NOW, Stub, stub_info

from pyeconomics.core.errors import InputError
from pyeconomics.data import (
    Authentication,
    Capability,
    Case,
    CredentialError,
    DataError,
    KeyPlacement,
    KeySlot,
    Query,
    RateLimit,
    RateLimitError,
    ResponseError,
    Series,
    SeriesNotFoundError,
)
from pyeconomics.data.credentials import has_key, resolve_key, withheld
from pyeconomics.data.providers.base import DataProvider, sends_key
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import (
    MAX_REQUESTS_PER_OPERATION,
    Request,
    Response,
)
from pyeconomics.data.transport.ratelimit import ProviderLimiter

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "record_cassettes.py"


def _recorder() -> Any:
    spec = importlib.util.spec_from_file_location("record_cassettes", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["record_cassettes"] = module
    spec.loader.exec_module(module)
    return module


recorder = _recorder()

SLOTS = Authentication.key(
    "api_key",
    KeyPlacement.QUERY,
    alternates=(KeySlot(KeyPlacement.HEADER, "Authorization", "Bearer"),),
)


def problems(info: Any) -> list[str]:
    provider = type("Probe", (Stub,), {"info": info})
    return [
        f"[{p.rule}] {p.detail}"
        for p in ProviderRegistry.from_providers(provider).problems()
    ]


# --- key slots ------------------------------------------------------------------------


def test_a_request_names_the_slot_its_key_goes_in() -> None:
    info = stub_info(auth=SLOTS)
    pool = FakePool(FakeRaw(200, b"{}"), FakeRaw(200, b"{}"))
    wire = http(pool)
    key = "k" * 32
    wire.send(info, Request(host=HOST, path="/v1/x"), key=key)
    wire.send(info, Request(host=HOST, path="/v2/x", key_placement="header"), key=key)
    first, second = pool.calls
    assert f"api_key={key}" in first.url
    assert "Authorization" not in first.headers
    assert second.headers["Authorization"] == f"Bearer {key}"
    assert key not in second.url


def test_a_placement_the_source_does_not_declare_is_refused() -> None:
    info = stub_info(auth=Authentication.key("api_key", KeyPlacement.QUERY))
    with pytest.raises(CredentialError, match="no header placement"):
        http(FakePool()).send(
            info, Request(host=HOST, path="/v1/x", key_placement="header"), key="k" * 32
        )
    with pytest.raises(InputError):
        Request(host=HOST, path="/v1/x", key_placement="cookie")
    assert SLOTS.slot("body") is None
    assert SLOTS.slot("query") == KeySlot(KeyPlacement.QUERY, "api_key")


@pytest.mark.parametrize(
    ("auth", "expected"),
    [
        (
            Authentication.key(
                "api_key",
                KeyPlacement.QUERY,
                alternates=(KeySlot(KeyPlacement.QUERY, "key"),),
            ),
            "each key placement is declared once",
        ),
        (
            Authentication.key(
                "api_key",
                KeyPlacement.QUERY,
                alternates=(KeySlot(KeyPlacement.HEADER, "X-Thing"),),
            ),
            "'X-Thing' is not a name the redaction layer recognises",
        ),
        (
            Authentication.key("api_key", KeyPlacement.QUERY, alternates=("header",)),  # type: ignore[arg-type]
            "alternates must be a tuple of KeySlot",
        ),
        (
            Authentication(alternates=(KeySlot(KeyPlacement.HEADER, "Authorization"),)),
            "declares no key placement",
        ),
    ],
)
def test_the_auth_rule_checks_every_slot(auth: Authentication, expected: str) -> None:
    found = problems(stub_info(auth=auth))
    assert any(expected in problem for problem in found), found


# --- an optional key ------------------------------------------------------------------


class Optional(DataProvider):
    """A source whose key is optional: keyed and keyless paths."""

    info = stub_info(
        id="optional_stub",
        auth=Authentication.key("api_key", KeyPlacement.QUERY, required=False),
        rate_limits=(
            RateLimit(requests=10, per="second"),
            RateLimit(requests=2, per="day", without_key=True),
        ),
        ttl_seconds=0,
    )
    seen: ClassVar[list[bool]] = []
    cases = (
        Case(
            name="keyless",
            operation=Capability.FETCH,
            argument=Query(series=("S",)),
            keyless=True,
        ),
    )

    def build_requests(self, query: Query) -> Any:
        self.seen.append(self.sends_key)
        return (
            Request(host=HOST, path="/v2/x" if self.sends_key else "/v1/x", series="S"),
        )

    def parse(self, responses: Any, query: Query) -> Any:
        self.seen.append(self.sends_key)
        from stubs import series_for  # noqa: PLC0415

        return series_for("optional_stub", dates=1)


def test_the_hooks_learn_whether_a_key_is_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    Optional.seen = []
    transport = Canned(lambda _: ok({}))
    Optional().fetch(Query(series=("S",)), transport=transport)
    Optional().fetch(
        Query(series=("S",), max_observations=5), key="k" * 32, transport=transport
    )
    monkeypatch.setenv("OPTIONAL_STUB_API_KEY", "k" * 32)
    Optional().fetch(Query(series=("S",), max_observations=6), transport=transport)
    assert Optional.seen == [False, False, True, True, True, True]
    assert [request.path for request in transport.sent] == ["/v1/x", "/v2/x", "/v2/x"]
    assert Optional().sends_key is True  # outside an operation: the chain has one
    with withheld("optional_stub"):
        assert Optional().sends_key is False
        assert not has_key("optional_stub")
        with pytest.raises(CredentialError):
            resolve_key("optional_stub")
        assert resolve_key("optional_stub", "e" * 32).provider == "optional_stub"
    assert has_key("optional_stub")


def test_sends_key_follows_the_authentication() -> None:
    assert sends_key(stub_info()) is False
    assert (
        sends_key(stub_info(auth=Authentication.key("api_key", KeyPlacement.QUERY)))
        is True
    )
    assert sends_key(Optional.info) is False
    assert sends_key(Optional.info, "k" * 32) is True


def test_a_keyless_case_withholds_the_key_and_refuses_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPTIONAL_STUB_API_KEY", "k" * 32)
    transport = Canned(lambda _: ok({}))
    (case,) = Optional.cases
    Optional().run_case(case, transport=transport)
    assert transport.sent[-1].path == "/v1/x"
    with pytest.raises(DataError, match="takes no key"):
        Optional().run_case(case, key="k" * 32, transport=transport)
    with pytest.raises(InputError):
        Case(
            name="x",
            operation=Capability.FETCH,
            argument=Query(series=("S",)),
            keyless=True,
            invalid_key=True,
        )


def test_a_keyless_limit_counts_only_requests_without_a_key() -> None:
    clock = FakeClock()
    limiter = ProviderLimiter(
        "optional_stub", Optional.info.rate_limits, clock.monotonic
    )
    limiter.acquire(clock.sleep)
    limiter.acquire(clock.sleep)
    with pytest.raises(RateLimitError):
        limiter.acquire(clock.sleep)
    for _ in range(20):
        limiter.acquire(clock.sleep, keyed=True)


def test_the_transport_holds_a_keyless_request_to_the_keyless_limit() -> None:
    pool = FakePool(*[FakeRaw(200, b"{}")] * 3)
    wire = http(pool)
    request = Request(host=HOST, path="/v1/x")
    wire.send(Optional.info, request)
    wire.send(Optional.info, request)
    with pytest.raises(RateLimitError):
        wire.send(Optional.info, request)
    wire.send(Optional.info, request, key="k" * 32)
    assert len(pool.calls) == 3


@pytest.mark.parametrize(
    ("limits", "auth", "expected"),
    [
        (
            (RateLimit(requests=1, per="day", without_key=True),),
            Authentication.key("api_key", KeyPlacement.QUERY),
            "belongs to a source whose key is optional",
        ),
        (
            (RateLimit(requests=1, per="day", without_key=cast("bool", "yes")),),
            Optional.info.auth,
            "without_key is true or false",
        ),
        (
            (RateLimit(requests=1, per="day"), RateLimit(requests=2, per="day")),
            Optional.info.auth,
            "one per second, minute, hour or day",
        ),
    ],
)
def test_the_rate_limit_rule_checks_keyless_limits(
    limits: Any, auth: Authentication, expected: str
) -> None:
    found = problems(stub_info(rate_limits=limits, auth=auth))
    assert any(expected in problem for problem in found), found


# --- paging ---------------------------------------------------------------------------


class Paged(Stub):
    info = stub_info(id="paged_stub", ttl_seconds=0)
    pages = 3

    def next_page(self, request: Request, response: Response) -> Request | None:
        number = int(dict(request.params).get("page", "1"))
        return (
            replace(request, params=(("page", str(number + 1)),))
            if number < self.pages
            else None
        )

    def parse(self, responses: Any, query: Query) -> Any:
        self.received = len(responses)
        from stubs import series_for  # noqa: PLC0415

        return series_for("paged_stub", dates=1)


def test_the_default_exchange_follows_every_page() -> None:
    transport = Canned(lambda _: ok({}))
    provider = Paged()
    provider.fetch(Query(series=("S",)), transport=transport)
    assert [dict(request.params).get("page") for request in transport.sent] == [
        None,
        "2",
        "3",
    ]
    assert provider.received == 3


def test_paging_stops_at_the_request_cap_and_a_failed_page_maps_to_its_error() -> None:
    endless = type("Endless", (Paged,), {"pages": MAX_REQUESTS_PER_OPERATION + 5})
    with pytest.raises(DataError, match="more than"):
        endless().fetch(Query(series=("S",)), transport=Canned(lambda _: ok({})))
    statuses = iter([200, 404])
    with pytest.raises(SeriesNotFoundError):
        Paged().fetch(
            Query(series=("T",)),
            transport=Canned(lambda _: ok({}, status=next(statuses))),
        )


def test_an_exchange_that_returns_failed_extra_pages_is_refused() -> None:
    class Custom(Stub):
        info = stub_info(id="custom_stub", ttl_seconds=0)

        def exchange(self, requests: Any, *, key: Any, transport: Any) -> Any:
            return [ok({}), ok({}, status=500)]

    with pytest.raises(ResponseError, match="failed page"):
        Custom().fetch(Query(series=("S",)), transport=Canned(lambda _: ok({})))


# --- redirects ------------------------------------------------------------------------


def test_a_source_that_follows_no_redirect_sees_it_in_classify_error() -> None:
    seen: list[int] = []

    class NoFollow(Stub):
        info = stub_info(id="nofollow_stub", follow_redirects=False, ttl_seconds=0)

        def classify_error(self, request: Request, response: Response) -> Any:
            seen.append(response.status)
            return CredentialError("refused by redirect", provider="nofollow_stub")

    pool = FakePool(FakeRaw(302, b"", {"Location": f"https://{HOST}/elsewhere"}))
    with pytest.raises(CredentialError):
        NoFollow().fetch(Query(series=("S",)), transport=http(pool))
    assert seen == [302]
    assert len(pool.calls) == 1
    assert problems(stub_info(follow_redirects="no")) != []


def test_an_unclassified_redirect_is_a_response_error() -> None:
    class NoFollow(Stub):
        info = stub_info(id="nofollow_stub2", follow_redirects=False, ttl_seconds=0)

    pool = FakePool(FakeRaw(301, b"", {"Location": f"https://{HOST}/elsewhere"}))
    with pytest.raises(ResponseError, match="HTTP 301"):
        NoFollow().fetch(Query(series=("S",)), transport=http(pool))


# --- simulated failures in the recorder -----------------------------------------------


def test_a_simulated_case_sends_nothing_and_records_a_synthetic_failure() -> None:
    from toys import ToyJson  # noqa: PLC0415

    case = Case(
        name="error_rate_limited",
        operation=Capability.FETCH,
        argument=Query(series=("TOYRATE",), max_observations=24),
        expect=RateLimitError,
        simulate=429,
    )
    banned = Canned(lambda _: pytest.fail("a simulated case sends nothing"))
    cassette = recorder.record_case(ToyJson(), case, banned, NOW)
    assert cassette.synthetic is True
    (record,) = cassette.requests
    assert record.response.status == 429
    assert dict(record.response.headers)["retry-after"] == "60"
    reply = recorder.SimulatingTransport(503, NOW).send(
        ToyJson.info, Request(host=HOST, path="/x")
    )
    assert (reply.status, reply.body) == (503, b"")


@pytest.mark.parametrize(
    "fields",
    [{"simulate": 404, "expect": SeriesNotFoundError}, {"simulate": 429}],
    ids=["not-a-limit-or-outage", "no-expected-error"],
)
def test_a_simulated_case_stands_in_for_a_limit_or_an_outage_only(
    fields: dict[str, Any],
) -> None:
    with pytest.raises(InputError):
        Case(
            name="x",
            operation=Capability.FETCH,
            argument=Query(series=("S",)),
            **fields,
        )


# --- frame notes ----------------------------------------------------------------------


def test_notes_travel_with_a_frame_and_are_checked() -> None:
    from stubs import series_for  # noqa: PLC0415

    series = series_for(
        "stub", notes=("revised_data", "footnote: P preliminary (2026-08-31)")
    )
    assert Series.from_json(series.canonical_json()) == series
    assert Series.from_pandas(series.to_pandas()) == series
    for bad in (
        ("Not Snake: x",),
        ("revised_data", "revised_data"),
        ("x://y",),
        ("a",) * 33,
    ):
        with pytest.raises(InputError):
            series_for("stub", notes=bad)
    assert dt.date(2026, 1, 1) < NOW.date()
