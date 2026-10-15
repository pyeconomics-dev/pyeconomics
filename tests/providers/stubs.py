# tests/providers/stubs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Small building blocks for the provider tests: an info, a stub provider, a transport.

``Stub`` is a provider whose hooks call functions the test sets, so one class
exercises every path of :class:`~pyeconomics.data.providers.base.DataProvider`
without a source behind it. ``Scripted`` is a transport that answers from a list.
"""

from __future__ import annotations

import calendar
import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    Authentication,
    CachePolicy,
    Capability,
    DataProvider,
    DateConvention,
    LicenceClass,
    LlmUse,
    ObservationFrequency,
    ProviderInfo,
    Query,
    RateLimit,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Terms,
    UnitRecord,
)
from pyeconomics.data.transport.base import Request, Response

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from pyeconomics.data.credentials import Secret

__all__ = [
    "HOST",
    "NOW",
    "STUB_TERMS",
    "Scripted",
    "Stub",
    "answer",
    "series_for",
    "stub_info",
]

HOST: Final = "api.stub.example.org"
NOW: Final = dt.datetime(2026, 10, 15, 16, 0, tzinfo=dt.UTC)
STUB_TERMS: Final = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.stub.example.org/terms",
    checked=dt.date(2026, 10, 15),
    attribution="Source: the stub agency.",
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)


def stub_info(**changes: Any) -> ProviderInfo:
    """Return a valid, keyless, hosted-safe info, with ``changes`` applied."""
    info = ProviderInfo(
        id="stub",
        ttl_seconds=0,  # the provider tests exercise the pipeline, not the cache
        name="Stub agency",
        homepage="https://www.stub.example.org",
        terms=STUB_TERMS,
        hosts=(HOST,),
        rate_limits=(RateLimit(requests=10, per="second"),),
        auth=Authentication(),
    )
    return replace(info, **changes)


def answer(status: int = 200, body: bytes = b"{}", /, **headers: str) -> Response:
    """Return a response stamped ``NOW``."""
    return Response(status, body, NOW, tuple(headers.items()))


def series_for(provider: str = "stub", *, dates: int = 3, **meta: Any) -> Series:
    """Return a monthly series of ``dates`` observations for ``provider``."""
    index = tuple(
        dt.date(2025, month, calendar.monthrange(2025, month)[1])
        for month in range(1, dates + 1)
    )
    series_meta = SeriesMeta(
        provider=provider,
        series_id="S",
        title="A stub series",
        unit=UnitRecord(text="Percent", kind=UnitKind.RATE),
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED,
        source_dating=DateConvention.PERIOD_END,
        terms=STUB_TERMS,
    )
    return Series(
        index, tuple(0.01 * (i + 1) for i in range(dates)), replace(series_meta, **meta)
    )


class Stub(DataProvider):
    """A provider whose hooks call functions the test sets as attributes."""

    info = stub_info(
        capabilities=(
            Capability.FETCH,
            Capability.SEARCH,
            Capability.DESCRIBE,
            Capability.VINTAGES,
        )
    )

    def __init__(self) -> None:
        self.requests: Sequence[Any] = (Request(host=HOST, path="/v1/x", series="S"),)
        self.parsed: Callable[[Sequence[Response], Query], Any] = lambda _r, _q: (
            series_for()
        )
        self.searched: Callable[[Sequence[Response]], Any] = lambda _r: ()
        self.described: Callable[[Sequence[Response]], Any] = lambda _r: None
        self.dated: Callable[[Sequence[Response]], Any] = lambda _r: ()
        self.classify: Callable[[Request, Response], Any] = lambda _q, _r: None

    def build_requests(self, query: Query) -> Sequence[Request]:
        return self.requests

    def parse(self, responses: Sequence[Response], query: Query) -> Any:
        return self.parsed(responses, query)

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        return self.requests

    def parse_search(self, responses: Sequence[Response], text: str, limit: int) -> Any:
        return self.searched(responses)

    def build_describe(self, series_id: str) -> Sequence[Request]:
        return self.requests

    def parse_describe(self, responses: Sequence[Response], series_id: str) -> Any:
        return self.described(responses)

    def build_vintages(self, series_id: str) -> Sequence[Request]:
        return self.requests

    def parse_vintages(self, responses: Sequence[Response], series_id: str) -> Any:
        return self.dated(responses)

    def classify_error(self, request: Request, response: Response) -> Any:
        return self.classify(request, response)


class Scripted:
    """A transport that answers from a list and records what it was asked."""

    def __init__(self, *responses: Response) -> None:
        self.responses = list(responses)
        self.sent: list[tuple[str, Request, str | Secret | None]] = []

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,
    ) -> Response:
        """Record the request and return the next scripted response."""
        self.sent.append((info.id, request, key))
        return self.responses.pop(0)
