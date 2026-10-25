# tests/data/catalog/scripted.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Scripted providers: a source that answers from a table, for resolver tests.

A scripted provider is a real :class:`~pyeconomics.data.DataProvider` subclass with
real metadata, so the resolver's gates (mode, key, vintage, platform) and the base
class's (licence, status, vintage selection, size bound) run for real. Only the
exchange is replaced: instead of a transport it reads each series from a script,
which holds a frame or an exception to raise. Every request is recorded in
``calls``, so a test can prove that a refused candidate was never asked.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING

from catalog_support import HOSTED_TERMS

from pyeconomics.data import (
    Authentication,
    Capability,
    DataProvider,
    KeyPlacement,
    LicenceClass,
    LlmUse,
    ProviderInfo,
    Query,
    SearchHit,
    Series,
    SeriesMeta,
    Table,
)
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import Request, Response

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pyeconomics.data import Secret
    from pyeconomics.data.transport.base import Transport

__all__ = ["calls_of", "registry_of", "scripted"]

_WHEN = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)


def scripted(  # noqa: PLR0913, C901 - a provider with every optional capability
    provider_id: str,
    script: Mapping[str, Series | Table | Exception],
    *,
    licence: LicenceClass = LicenceClass.HOSTED_SAFE,
    llm_use: LlmUse = LlmUse.ALLOWED,
    capabilities: Sequence[Capability] = (Capability.FETCH,),
    keyed: bool = False,
    extra: str | None = None,
    hits: Sequence[SearchHit] | Exception = (),
    described: SeriesMeta | None = None,
    changed: Sequence[dt.date] = (),
) -> type[DataProvider]:
    """Build a provider class that answers from ``script``.

    The script maps a series id to the frame to return or the exception to raise
    when the provider is asked for it. A series not in the script is unknown.
    """
    terms = HOSTED_TERMS.with_overrides(licence=licence, llm_use=llm_use)
    info = ProviderInfo(
        id=provider_id,
        name=f"Scripted {provider_id}",
        homepage="https://www.example.org",
        terms=terms,
        capabilities=tuple(capabilities),
        auth=Authentication.key("api_key", KeyPlacement.QUERY)
        if keyed
        else Authentication(),
        hosts=("api.example.org",),
        extra=extra,
    )
    calls: list[Query] = []

    def build_requests(self: DataProvider, query: Query) -> Sequence[Request]:
        calls.append(query)
        return (Request(host="api.example.org", path="/v1/x", series=query.series[0]),)

    def exchange(
        self: DataProvider,
        requests: Sequence[Request],
        *,
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        found = script.get(requests[0].series or "")
        if isinstance(found, Exception):
            raise found
        if isinstance(hits, Exception) and requests[0].path == "/v1/search":
            raise hits
        return (Response(200, b"{}", _WHEN),)

    def build_search(self: DataProvider, text: str, limit: int) -> Sequence[Request]:
        return (Request(host="api.example.org", path="/v1/search"),)

    def parse_search(
        self: DataProvider, responses: Sequence[Response], text: str, limit: int
    ) -> Sequence[SearchHit]:
        assert not isinstance(hits, Exception)
        return tuple(hits)[:limit]

    def build_describe(self: DataProvider, series_id: str) -> Sequence[Request]:
        return (Request(host="api.example.org", path="/v1/describe"),)

    def parse_describe(
        self: DataProvider, responses: Sequence[Response], series_id: str
    ) -> SeriesMeta:
        assert described is not None
        return described

    def build_vintages(self: DataProvider, series_id: str) -> Sequence[Request]:
        return (Request(host="api.example.org", path="/v1/vintages"),)

    def parse_vintages(
        self: DataProvider, responses: Sequence[Response], series_id: str
    ) -> Sequence[dt.date]:
        return tuple(changed)

    def parse(
        self: DataProvider, responses: Sequence[Response], query: Query
    ) -> Series | Table:
        found = script[query.series[0]]
        assert not isinstance(found, Exception)
        return found

    namespace: dict[str, object] = {
        "info": info,
        "build_requests": build_requests,
        "exchange": exchange,
        "parse": parse,
        "build_search": build_search,
        "parse_search": parse_search,
        "build_describe": build_describe,
        "parse_describe": parse_describe,
        "build_vintages": build_vintages,
        "parse_vintages": parse_vintages,
        "calls": calls,
        "__module__": __name__,
    }
    return type(f"Scripted_{provider_id}", (DataProvider,), namespace)


def calls_of(provider: type[DataProvider]) -> list[Query]:
    """Return the queries a scripted provider class was asked."""
    found: list[Query] = provider.calls  # type: ignore[attr-defined]
    return found


def registry_of(*providers: type[DataProvider]) -> ProviderRegistry:
    """Build an isolated registry of scripted providers."""
    return ProviderRegistry.from_providers(*providers)
