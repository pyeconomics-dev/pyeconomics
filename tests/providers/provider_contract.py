# tests/providers/provider_contract.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The contract every data provider keeps, checked offline and, under ``-m live``, live.

``tests/providers/test_provider_contract.py`` parametrizes these checks over the toy
providers and every registered provider. Each check takes a provider class:

- :func:`check_registered`: the provider validates, alone in a registry;
- :func:`check_cases`: every declared capability has a success case and every
  case has a cassette; every provider has a 404 and a 429 error case, and a 401
  or 403 case when it needs a key or a contact;
- :func:`check_success_case`: the recorded response parses into a valid result
  with units, frequency, seasonal adjustment, licence class, attribution, a
  retrieval time that is the cassette's ``recorded_on``, decimal rates, ``None``
  for missing values and, for a provider that keeps vintages, real-time periods;
- :func:`check_error_case`: an error cassette raises the taxonomy's error;
- :func:`check_foreign_hosts_refused`: the real transport refuses a foreign host
  and ``http://``, redirects included;
- :func:`check_rate_limits_hold`: on a fake clock, the declared limits hold;
- :func:`check_hosted_mode`: hosted mode refuses every class but hosted-safe and
  user-supplied before any request, whatever called it;
- :func:`check_synthesize`: a source not hosted-safe, or that forbids storage,
  has the ``synthesize`` hook the recorder needs.

A live run (``uv run pytest -m live --force-enable-socket tests/providers``)
sends the same cases through the real transport and the maintainer's or CI's
keys; it skips the error cases only a replay can provoke (429 and 5xx).
"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest
from fakes import BANNED, FIXED_NOW, FakeClock, FakePool, FakeRaw

from pyeconomics.data import (
    DataProvider,
    LicenceClass,
    LicenceError,
    Mode,
    Query,
    RateLimitError,
    SearchHit,
    Series,
    SeriesMeta,
    SeriesNotFoundError,
    Table,
    TransportError,
    configure,
    current_mode,
)
from pyeconomics.data.errors import CredentialError
from pyeconomics.data.providers.base import AuthKind, Capability, Case
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import Request, Transport
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.http import HttpTransport
from pyeconomics.data.transport.ratelimit import ProviderLimiter
from pyeconomics.data.transport.replay import ReplayTransport
from pyeconomics.data.types import DECIMAL_KINDS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo
    from pyeconomics.data.transport.base import Response

__all__ = [
    "CASSETTES",
    "RATE_BOUND",
    "SpyTransport",
    "check_cases",
    "check_error_case",
    "check_foreign_hosts_refused",
    "check_hosted_mode",
    "check_rate_limits_hold",
    "check_registered",
    "check_success_case",
    "check_synthesize",
    "load_cassette",
    "replay",
]

#: Where every provider's cassettes live: ``CASSETTES / <provider> / <case>.json``.
CASSETTES: Final = Path(__file__).resolve().parent / "cassettes"
#: A rate, return or volatility beyond this is almost surely percent, not a decimal.
RATE_BOUND: Final = 2.0
#: A key long enough for the key chain, for sending through a fake pool.
_PLAIN_KEY: Final = "k" * 24
#: Errors only a replay can provoke: a live source is not made to fail on request.
_REPLAY_ONLY: Final = (RateLimitError, TransportError)


class SpyTransport:
    """Wraps a transport and records the requests that reached it."""

    def __init__(self, inner: Transport) -> None:
        self.inner = inner
        self.sent: list[Request] = []

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Record the request, then send it through the wrapped transport."""
        self.sent.append(request)
        return self.inner.send(info, request, key=key)


def cassette_path(provider_id: str, case: Case) -> Path:
    """Return the file a case's cassette is stored in."""
    return CASSETTES / provider_id / f"{case.name}.json"


def load_cassette(provider_id: str, case: Case) -> Cassette:
    """Read a case's cassette."""
    return Cassette.from_json(cassette_path(provider_id, case).read_bytes())


def replay(provider_id: str, case: Case) -> ReplayTransport:
    """Return a transport that replays a case's cassette."""
    return ReplayTransport([load_cassette(provider_id, case)])


def _registry(provider: type[DataProvider]) -> ProviderRegistry:
    extra = provider.info.extra
    return ProviderRegistry.from_providers(
        provider, extras={extra: ()} if extra else None
    )


def check_registered(provider: type[DataProvider]) -> None:
    """The provider passes every validate() rule and can be fetched by id."""
    registry = _registry(provider)
    registry.validate()
    assert registry.get(provider.info.id).info == provider.info


def _first(cases: Sequence[Case], capability: Capability) -> Case | None:
    return next(
        (c for c in cases if c.operation is capability and c.expect is None), None
    )


def check_cases(provider: type[DataProvider]) -> None:
    """Every capability and every required error has a case with a cassette."""
    info, cases = provider.info, provider.cases
    for capability in info.capabilities:
        if capability is not Capability.BULK:
            assert _first(cases, capability), f"no success case for {capability.value}"
    undeclared = [c.name for c in cases if c.operation not in info.capabilities]
    assert undeclared == [], f"cases for undeclared capabilities: {undeclared}"
    expected = {c.expect for c in cases if c.expect}
    required = {SeriesNotFoundError, RateLimitError}
    if info.auth.kind in {AuthKind.KEY, AuthKind.CONTACT}:
        required.add(CredentialError)
    assert required <= expected, (
        f"error cases needed: {sorted(e.__name__ for e in required - expected)}"
    )
    names = [case.name for case in cases]
    assert len(set(names)) == len(names), "case names are unique"
    missing = [c.name for c in cases if not cassette_path(info.id, c).is_file()]
    assert missing == [], f"no cassette for {missing}"


def _check_decimals(
    unit_kind: object, scale: float, values: Sequence[float | None]
) -> None:
    if unit_kind not in DECIMAL_KINDS:
        return
    assert scale == 1.0, "a rate is a decimal with scale 1"
    present = [v for v in values if v is not None]
    assert all(math.isfinite(v) for v in present)
    bound = 1.0 if str(unit_kind) == "probability" else RATE_BOUND
    assert all(abs(v) <= bound for v in present), (
        f"a rate beyond {bound} is percent, not a decimal"
    )


def check_frame(
    provider: type[DataProvider],
    case: Case,
    frame: object,
    *,
    recorded_on: dt.datetime | None,
) -> None:
    """A fetched series or table is valid, labelled and in the right units."""
    info = provider.info
    assert isinstance(frame, Series | Table)
    meta = frame.meta
    assert meta.provider == info.id
    terms = meta.terms
    assert (terms.terms_url, terms.attribution, terms.checked) == (
        info.terms.terms_url,
        info.terms.attribution,
        info.terms.checked,
    )
    assert terms.attribution.strip()
    assert meta.retrieved_at is not None
    if recorded_on is not None:
        assert meta.retrieved_at == recorded_on
    if isinstance(frame, Series):
        _check_decimals(frame.meta.unit.kind, frame.meta.unit.scale, frame.values)
    else:
        for column, values in zip(frame.columns, frame.data, strict=True):
            _check_decimals(column.unit.kind, column.unit.scale, values)
            assert column.seasonal_adjustment is not None
    if meta.frequency.pandas_alias() is not None:
        assert len(frame.periods()) == len(frame)
    assert not any(
        isinstance(v, float) and math.isnan(v)
        for column in ([frame.values] if isinstance(frame, Series) else frame.data)
        for v in column
    ), "a missing value is None, never NaN"
    query = case.argument
    assert isinstance(query, Query)
    assert len(frame) <= query.max_observations
    if Capability.VINTAGES in info.capabilities and query.vintage == "all":
        assert frame.has_realtime, (
            "a source that keeps vintages returns real-time periods"
        )
    assert type(frame).from_json(frame.canonical_json()) == frame


def check_success_case(
    provider: type[DataProvider],
    case: Case,
    transport: Transport,
    *,
    recorded_on: dt.datetime | None = None,
) -> None:
    """Run a success case and check what comes back."""
    instance = provider()
    result: Any = instance.run_case(case, transport=transport)
    if case.operation is Capability.FETCH:
        check_frame(provider, case, result, recorded_on=recorded_on)
    elif case.operation is Capability.SEARCH:
        assert result
        assert all(isinstance(hit, SearchHit) for hit in result)
    elif case.operation is Capability.DESCRIBE:
        assert isinstance(result, SeriesMeta)
        assert result.provider == provider.info.id
        assert result.retrieved_at is not None
        if recorded_on is not None:
            assert result.retrieved_at == recorded_on
    else:
        assert result == tuple(sorted(set(result)))
        assert all(isinstance(day, dt.date) for day in result)


def check_error_case(
    provider: type[DataProvider], case: Case, transport: Transport
) -> None:
    """An error cassette raises the taxonomy's error, naming the provider."""
    assert case.expect is not None
    with pytest.raises(case.expect) as caught:
        provider().run_case(case, transport=transport)
    assert caught.value.provider == provider.info.id
    assert str(caught.value)


def check_foreign_hosts_refused(provider: type[DataProvider]) -> None:
    """The real transport refuses a foreign host and ``http://``, even on a redirect."""
    info = provider.info
    if not info.hosts:
        return
    clock = FakeClock()

    def transport(pool: FakePool) -> HttpTransport:
        return HttpTransport(
            pool=pool, clock=clock.monotonic, sleep=clock.sleep, now=lambda: FIXED_NOW
        )

    foreign = FakePool(BANNED)
    with pytest.raises(TransportError):
        transport(foreign).send(
            info, Request(host="foreign.example.net", path="/v1/x"), key=_PLAIN_KEY
        )
    assert foreign.calls == []
    own = Request(host=info.hosts[0], path="/v1/x")
    for target in (
        f"http://{info.hosts[0]}/v1/x",
        "https://foreign.example.net/v1/x",
        "https://user@" + info.hosts[0] + "/v1/x",
    ):
        pool = FakePool(FakeRaw(302, headers={"Location": target}), BANNED)
        with pytest.raises(TransportError):
            transport(pool).send(info, own, key=_PLAIN_KEY)
        assert len(pool.calls) == 1, "the redirect was not followed"


def check_rate_limits_hold(provider: type[DataProvider]) -> None:
    """On a fake clock, no window ever holds more requests than its limit."""
    info = provider.info
    if not info.rate_limits:
        return
    clock = FakeClock()
    limiter = ProviderLimiter(info.id, info.rate_limits, clock.monotonic)
    grants: list[float] = []
    biggest = max(limit.requests for limit in info.rate_limits)
    for _ in range(3 * biggest + 5):
        try:
            limiter.acquire(clock.sleep)
        except RateLimitError:
            break
        grants.append(clock.now)
    assert len(grants) > 1
    for limit in info.rate_limits:
        window = float(limit.window_seconds)
        for first, later in zip(grants, grants[limit.requests :], strict=False):
            assert later - first >= window - 1e-9, (
                f"more than {limit.requests} requests within a {limit.per}"
            )


def check_hosted_mode(provider: type[DataProvider]) -> None:
    """Hosted mode refuses all but hosted-safe and user-supplied, before a request."""
    case = next(
        (
            c
            for c in provider.cases
            if c.expect is None and c.operation is Capability.FETCH
        ),
        None,
    )
    assert case is not None, "a provider needs a fetch case"
    request = provider().build_requests(case.argument)[0]  # type: ignore[arg-type]
    configure(mode="hosted")
    assert current_mode() is Mode.HOSTED
    for licence in LicenceClass:
        info = replace(
            provider.info, terms=replace(provider.info.terms, licence=licence)
        )
        variant = type(f"As{licence.name.title()}", (provider,), {"info": info})
        spy = SpyTransport(replay(provider.info.id, case))
        if licence.hosted_allowed:
            try:
                variant().run_case(case, transport=spy)
            except LicenceError:
                # A series may carry its own class (the terms of one series); that
                # check follows the request, so the request was sent.
                assert spy.sent
            assert spy.sent, f"{licence.value} is allowed, so the request is sent"
            continue
        with pytest.raises(LicenceError) as refused:
            variant().run_case(case, transport=spy)
        assert spy.sent == [], f"{licence.value} reached the transport"
        assert licence.value in str(refused.value)
        assert info.terms.terms_url in str(refused.value)
        # Whatever called it: the transports refuse on their own too.
        with pytest.raises(LicenceError):
            replay(provider.info.id, case).send(info, request)
        with pytest.raises(LicenceError):
            HttpTransport(pool=FakePool(BANNED)).send(info, request, key=_PLAIN_KEY)


def check_synthesize(provider: type[DataProvider]) -> None:
    """A source the Recording rule makes synthetic has a ``synthesize`` hook."""
    terms = provider.info.terms
    if terms.licence is LicenceClass.HOSTED_SAFE and terms.cache.value != "forbidden":
        return
    assert provider.synthesize is not DataProvider.synthesize, (
        "a source that is not hosted-safe, or forbids storage, records synthetic "
        "values: implement synthesize()"
    )
