# tests/providers/test_bloomberg_spike.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Bloomberg contract spike: a session-based source fits ``DataProvider`` unchanged.

Phase 6 adds a Bloomberg provider over the Desktop API, a local session with no
HTTP in it. This spike proves, with a fake session, that the contract Step 4 fixes
already holds such a source, so Phase 6 adds it without changing the contract
(ROADMAP section 4 3.1). Nothing here imports Bloomberg's library, and every
number is invented.

The provider is premium-local, Windows-only and local-only, and keeps a hit budget:

- ``access=Access.SESSION`` and no hosts: the provider overrides
  :meth:`~pyeconomics.data.DataProvider.exchange` to talk to a
  :class:`SessionTransport` (open a service, send a request, iterate its events)
  and declares no host, so no HTTP transport can send for it;
- it names its service with a ``*.localhost`` request host, which the allowlist
  never admits;
- its tickers have spaces, so it widens the id pattern with a ``Query`` subclass;
- the session owns the clock, as the HTTP transport does, and reports a failure
  with the HTTP statuses the taxonomy already maps (404, 429), so the base class
  maps a session's errors with no new code;
- a limit error is never retried, because a session has no retry loop at all.

The findings are written up in ``docs/data/writing-a-provider.md``.
"""

from __future__ import annotations

import ast
import datetime as dt
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any, Final, Protocol, cast

import pytest
from fakes import BANNED, FakePool
from pydantic import StringConstraints, ValidationError
from stubs import Scripted
from toys import ToyJson

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    Access,
    CachePolicy,
    Capability,
    DataError,
    DataProvider,
    DateConvention,
    LicenceClass,
    LicenceError,
    LlmUse,
    ObservationFrequency,
    Platform,
    ProviderInfo,
    Query,
    RateLimitError,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    SeriesNotFoundError,
    Terms,
    UnitRecord,
    configure,
)
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import Request, Response, request_path
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.http import HttpTransport

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.transport.base import Transport

SERVICE: Final = "//blp/refdata"
LOGICAL_HOST: Final = "desktop-api.localhost"
NOW: Final = dt.datetime(2026, 10, 15, 17, 0, tzinfo=dt.UTC)
_TICKER = r"^[A-Za-z0-9^][A-Za-z0-9._:+*=@/^, -]{0,127}$"


# --- the session protocol -----------------------------------------------------


class Service(Protocol):
    """An open service: send a request, iterate the events it produces."""

    def send_request(
        self, operation: str, arguments: Mapping[str, object]
    ) -> Iterable[Mapping[str, object]]:
        """Send one request and return its events."""
        ...


class SessionTransport(Protocol):
    """A local session: open a service by its URI, and tell the time."""

    def open_service(self, uri: str) -> Service:
        """Open a service, such as the reference-data service."""
        ...

    def now(self) -> dt.datetime:
        """Return the time, in UTC: the session owns the clock."""
        ...


class FakeService:
    """Answers a historical-data request with synthetic prices, or an error."""

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    def send_request(
        self, operation: str, arguments: Mapping[str, object]
    ) -> Iterable[Mapping[str, object]]:
        self.session.requests.append((operation, dict(arguments)))
        if self.session.limit_reached:
            yield {
                "type": "RESPONSE_ERROR",
                "category": "LIMIT",
                "message": "daily limit",
            }
            return
        security = str(cast("Sequence[object]", arguments["securities"])[0])
        if security.startswith("NOSUCH"):
            yield {
                "type": "RESPONSE_ERROR",
                "category": "BAD_SEC",
                "message": "unknown",
            }
            return
        rows = [
            {
                "date": day,
                "PX_LAST": round(100 + 50 * synthetic_value(security, n), 2),
            }
            for n, day in enumerate(("2025-01-02", "2025-01-03", "2025-01-06"))
        ]
        yield {
            "type": "PARTIAL_RESPONSE",
            "securityData": {"security": security, "fieldData": rows[:2]},
        }
        yield {
            "type": "RESPONSE",
            "securityData": {"security": security, "fieldData": rows[2:]},
        }


class FakeSession:
    """A stand-in for the Desktop API session; it records what happens to it."""

    def __init__(self) -> None:
        self.opened: list[str] = []
        self.requests: list[tuple[str, dict[str, object]]] = []
        self.limit_reached = False

    def open_service(self, uri: str) -> Service:
        self.opened.append(uri)
        return FakeService(self)

    def now(self) -> dt.datetime:
        return NOW


# --- the provider -------------------------------------------------------------


class HitBudget:
    """Counts securities times fields before each request and refuses an overspend."""

    def __init__(self, limit: int) -> None:
        self.limit, self.used = limit, 0

    def reserve(self, hits: int, *, force: bool) -> bool:
        """Spend ``hits``, unless that exceeds the budget and the call is not forced."""
        if self.used + hits > self.limit and not force:
            return False
        self.used += hits
        return True


class BloombergQuery(Query):
    """A query whose ids may hold spaces, as tickers do, plus a budget override."""

    series: tuple[Annotated[str, StringConstraints(pattern=_TICKER)], ...]
    force: bool = False


class BloombergSpike(DataProvider):
    """A premium-local, Windows-only provider over a (fake) Desktop API session."""

    info = ProviderInfo(
        id="bloomberg_spike",
        name="Bloomberg Desktop API (contract spike)",
        homepage="https://www.bloomberg.com/professional",
        terms=Terms(
            licence=LicenceClass.PREMIUM_LOCAL,
            terms_url="https://www.bloomberg.com/notices/tos/",
            checked=dt.date(2026, 10, 15),
            attribution="Source: Bloomberg, on the user's own Terminal.",
            notice=(
                "Bloomberg is a trademark of its owner; this product is not "
                "affiliated with it."
            ),
            llm_use=LlmUse.FORBIDDEN,
            cache=CachePolicy.ALLOWED,
        ),
        capabilities=(Capability.FETCH,),
        access=Access.SESSION,
        hosts=(),
        platforms=(Platform.WINDOWS,),
        automated_collection=False,
    )
    query_type = BloombergQuery

    def __init__(
        self, session: SessionTransport | None = None, budget: HitBudget | None = None
    ) -> None:
        self.session = session
        self.budget = budget or HitBudget(1_000)

    def build_requests(self, query: Query) -> Sequence[Request]:
        """One historical-data request per security, to the logical service."""
        assert isinstance(query, BloombergQuery)
        return tuple(
            Request(
                host=LOGICAL_HOST,
                path=request_path("refdata", "HistoricalDataRequest"),
                method="POST",
                body={
                    "securities": [security],
                    "fields": ["PX_LAST"],
                    "force": query.force,
                },
                series=security,
            )
            for security in query.series
        )

    def exchange(
        self,
        requests: Sequence[Request],
        *,
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        """Send each request through the session; the HTTP transport is not used."""
        assert self.session is not None
        session = self.session
        responses: list[Response] = []
        for request in requests:
            body: Any = request.body
            hits = len(body["securities"]) * len(body["fields"])
            if not self.budget.reserve(hits, force=bool(body["force"])):
                msg = "the hit budget would be exceeded; raise it or force the call"
                raise RateLimitError(msg, provider=self.info.id)
            service = session.open_service(SERVICE)
            events = list(
                service.send_request(
                    "HistoricalDataRequest",
                    {"securities": body["securities"], "fields": body["fields"]},
                )
            )
            responses.append(_as_response(events, session.now()))
        return responses

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """One series of prices from the session's events."""
        events = responses[0].json(provider=self.info.id)
        assert isinstance(events, list)
        rows = [row for event in events for row in event["securityData"]["fieldData"]]
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=query.series[0],
            title=f"{query.series[0]} last price",
            unit=UnitRecord(text="Index points", kind=UnitKind.INDEX_LEVEL),
            frequency=ObservationFrequency.BUSINESS_DAILY,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.POINT_IN_TIME,
            terms=self.info.terms,
        )
        return Series(
            tuple(dt.date.fromisoformat(row["date"]) for row in rows),
            tuple(float(row["PX_LAST"]) for row in rows),
            meta,
        )


def _as_response(events: list[Mapping[str, object]], when: dt.datetime) -> Response:
    """Wrap a session's events as a response, mapping its errors to HTTP statuses."""
    errors = [event for event in events if event.get("type") == "RESPONSE_ERROR"]
    status = 200
    if errors:
        status = {"LIMIT": 429, "BAD_SEC": 404}.get(str(errors[0].get("category")), 400)
    return Response(status, json.dumps(events).encode(), when)


def provider(**kwargs: Any) -> tuple[BloombergSpike, FakeSession]:
    session = FakeSession()
    return BloombergSpike(session, **kwargs), session


@pytest.fixture(autouse=True)
def _windows(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Desktop API is Windows-only; most tests run as if on Windows."""
    monkeypatch.setattr(sys, "platform", "win32")


# --- the spike ----------------------------------------------------------------


def test_a_session_source_validates_with_no_change_to_the_contract() -> None:
    ProviderRegistry.from_providers(BloombergSpike).validate(released={})
    assert BloombergSpike.info.hosts == ()
    assert BloombergSpike.info.access is Access.SESSION


def test_a_fetch_goes_through_the_session_and_returns_a_valid_series() -> None:
    spike, session = provider()
    series = spike.fetch({"series": ("SPX Index",), "force": False})
    assert isinstance(series, Series)
    assert series.meta.series_id == "SPX Index"
    assert len(series) == 3
    assert series.meta.retrieved_at == NOW
    assert session.opened == [SERVICE]
    assert session.requests[0][0] == "HistoricalDataRequest"
    assert Series.from_json(series.canonical_json()) == series
    assert all(90 < value < 160 for value in series.values if value is not None)


def test_tickers_with_spaces_need_the_widened_query_not_the_default() -> None:
    spike, _ = provider()
    with pytest.raises(ValidationError):
        Query(series=("SPX Index",))  # the default id pattern forbids spaces
    assert spike.fetch(BloombergQuery(series=("IBM US Equity",)))


def test_the_provider_runs_only_on_windows(monkeypatch: pytest.MonkeyPatch) -> None:
    spike, session = provider()
    monkeypatch.setattr(sys, "platform", "linux")
    with pytest.raises(DataError, match="does not run on linux"):
        spike.fetch({"series": ("SPX Index",)})
    monkeypatch.setattr(sys, "platform", "darwin")
    with pytest.raises(DataError, match="does not run on macos"):
        spike.fetch({"series": ("SPX Index",)})
    assert session.opened == []


def test_hosted_mode_refuses_it_before_a_session_is_opened() -> None:
    spike, session = provider()
    configure(mode="hosted")
    with pytest.raises(LicenceError, match="premium-local"):
        spike.fetch({"series": ("SPX Index",)})
    assert session.opened == []
    assert session.requests == []


def test_the_hit_budget_refuses_an_overspend_unless_forced() -> None:
    spike, session = provider(budget=HitBudget(2))
    spike.fetch({"series": ("SPX Index",)})
    spike.fetch({"series": ("INDU Index",)})
    sent = len(session.requests)
    with pytest.raises(RateLimitError, match="hit budget"):
        spike.fetch({"series": ("NDX Index",)})
    assert len(session.requests) == sent  # refused before the session saw it
    assert spike.fetch({"series": ("NDX Index",), "force": True})
    assert spike.budget.used == 3


def test_the_budget_counts_securities_times_fields() -> None:
    spike, session = provider(budget=HitBudget(2))
    with pytest.raises(RateLimitError):
        spike.fetch({"series": ("A Index", "B Index", "C Index")})
    assert len(session.requests) == 2  # two securities fit, the third did not


def test_a_limit_error_from_the_session_is_a_rate_limit_error_and_is_not_retried() -> (
    None
):
    spike, session = provider()
    session.limit_reached = True
    with pytest.raises(RateLimitError) as caught:
        spike.fetch({"series": ("SPX Index",)})
    assert caught.value.provider == "bloomberg_spike"
    assert len(session.requests) == 1


def test_an_unknown_security_is_a_series_not_found_error() -> None:
    spike, _ = provider()
    with pytest.raises(SeriesNotFoundError, match="NOSUCH Equity"):
        spike.fetch({"series": ("NOSUCH Equity",)})


def test_an_http_transport_cannot_send_for_a_session_provider() -> None:
    request = BloombergSpike().build_requests(BloombergQuery(series=("SPX Index",)))[0]
    pool = FakePool(BANNED)
    with pytest.raises(DataError, match="not a declared host"):
        HttpTransport(pool=pool).send(BloombergSpike.info, request)
    assert pool.calls == []


def test_the_logical_host_is_not_a_real_one() -> None:
    assert LOGICAL_HOST.endswith(".localhost")
    assert LOGICAL_HOST not in ToyJson.info.hosts


def test_nothing_imports_the_vendor_library() -> None:
    name = "blp" + "api"
    assert name not in sys.modules
    root = Path(__file__).resolve().parents[2]
    offenders: list[str] = []
    for tree in ("src", "tests", "scripts"):
        for path in (root / tree).rglob("*.py"):
            try:
                parsed = ast.parse(path.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(parsed):
                names = (
                    [alias.name for alias in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module or ""]
                    if isinstance(node, ast.ImportFrom)
                    else []
                )
                if any(n == name or n.startswith(name + ".") for n in names):
                    offenders.append(path.relative_to(root).as_posix())
    assert offenders == []


def test_a_session_provider_ignores_the_http_transport_it_is_given() -> None:
    spike, session = provider()
    transport = Scripted()
    assert spike.fetch({"series": ("SPX Index",)}, transport=transport)
    assert transport.sent == []
    assert session.opened == [SERVICE]
