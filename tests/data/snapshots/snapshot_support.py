# tests/data/snapshots/snapshot_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Helpers for the snapshot tests: hosted mode on a directory, toy sets and runs.

The writer runs over scripted providers (``tests/data/catalog/scripted.py``), so
the provider's own gates and the resolver's run for real while the answers come
from a script; a run is pinned to :data:`STARTED` with a fixed token. The
heartbeat goes to :class:`HeartbeatTransport`, which records what it was sent and
opens nothing.
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from catalog_support import HOSTED_TERMS, monthly
from scripted import registry_of, scripted

from pyeconomics.data import (
    CachePolicy,
    DataProvider,
    ProviderInfo,
    Series,
    config,
)
from pyeconomics.data.snapshots import codec, writer
from pyeconomics.data.snapshots.set import Entry, SnapshotSet
from pyeconomics.data.transport.base import Response

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from pathlib import Path

    import pytest

    from pyeconomics.data import Secret
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.data.transport.base import Request

__all__ = [
    "HEARTBEAT_URL",
    "STARTED",
    "WHEN",
    "HeartbeatTransport",
    "chosen",
    "entry",
    "forbidding",
    "frame",
    "hosted",
    "manifest_of",
    "object_of",
    "run",
    "values",
    "windowed",
]

#: When a scripted provider's response is retrieved (scripted.py's time).
WHEN = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)
#: When a test's run starts.
STARTED = dt.datetime(2026, 10, 15, 23, 30, tzinfo=dt.UTC)
#: A heartbeat URL of Better Stack's form; its token is made up.
HEARTBEAT_URL = "https://incidents.betterstack.com/api/v1/heartbeat/Tok3nForTestsOnly9"


def values(count: int, base: float = 0.04) -> list[float]:
    """Return ``count`` made-up decimals."""
    return [round(base + i / 1000, 6) for i in range(count)]


def hosted(monkeypatch: pytest.MonkeyPatch, directory: Path | None) -> None:
    """Switch to hosted mode, with ``directory`` as the snapshot when given."""
    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    if directory is None:
        monkeypatch.delenv("PYECONOMICS_SNAPSHOT_DIR", raising=False)
    else:
        monkeypatch.setenv("PYECONOMICS_SNAPSHOT_DIR", str(directory))
    config.reset()


def entry(
    provider: str,
    series: str,
    *,
    vintage: str = "latest",
    start: dt.date | None = None,
) -> Entry:
    """Return a set entry for a provider series."""
    return Entry(
        provider=provider,
        series=series,
        vintage=vintage,
        concepts=("us.toy.value",),
        start=start,
    )


def chosen(*entries: Entry) -> SnapshotSet:
    """Return a hand-made set of entries, sorted as the real one is."""
    return SnapshotSet(tuple(sorted(entries, key=lambda e: (e.provider, e.series))))


def forbidding(provider_id: str, script: Mapping[str, Any]) -> type[DataProvider]:
    """Return a hosted-safe scripted provider whose terms forbid storage."""
    base = scripted(provider_id, script)
    terms = HOSTED_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN)
    info = replace(base.info, terms=terms)
    return type(f"Forbidding_{provider_id}", (base,), {"info": info})


class HeartbeatTransport:
    """A transport that records each request and answers ``status``."""

    def __init__(self, status: int = 200) -> None:
        self.sent: list[tuple[ProviderInfo, Request]] = []
        self.status = status

    def send(
        self,
        info: ProviderInfo,
        request: Request,
        *,
        key: str | Secret | None = None,  # noqa: ARG002 - the Transport protocol's
    ) -> Response:
        """Record the request and answer it."""
        self.sent.append((info, request))
        return Response(self.status, b"", WHEN)


def run(  # noqa: PLR0913 - a run's seams
    directory: Path,
    *providers: type[DataProvider],
    entries: tuple[Entry, ...],
    started: dt.datetime = STARTED,
    nonce: str = "0000000a",
    transport: HeartbeatTransport | None = None,
    registry: ProviderRegistry | None = None,
) -> writer.Report:
    """Run the writer over scripted providers into ``directory``."""
    clock: Callable[[], dt.datetime] = lambda: started  # noqa: E731 - a fixed clock
    return writer.write(
        directory,
        chosen=chosen(*entries),
        registry=registry or registry_of(*providers),
        transport=transport,
        clock=clock,
        nonce=nonce,
    )


def manifest_of(directory: Path) -> codec.Manifest:
    """Read the directory's current.json."""
    return codec.decode_manifest((directory / codec.CURRENT).read_bytes())


def object_of(directory: Path, provider: str) -> dict[str, Any]:
    """Return the JSON document of the object current.json names for a provider."""
    ref = manifest_of(directory).providers[provider].object
    assert ref is not None
    document: dict[str, Any] = json.loads(
        gzip.decompress((directory / ref.name).read_bytes())
    )
    return document


def windowed(provider_id: str, script: Mapping[str, Any]) -> type[DataProvider]:
    """A scripted provider that answers only the days a query's window asks for."""
    from pyeconomics.data.resolver import trim  # noqa: PLC0415 - the resolver's cut

    base = scripted(provider_id, script)
    whole = base.parse

    def parse(self: DataProvider, responses: Any, query: Any) -> Any:  # noqa: ANN401
        return trim(whole(self, responses, query), query.start, query.end)

    return type(f"Windowed_{provider_id}", (base,), {"parse": parse})


def frame(
    provider: str,
    series_id: str,
    count: int = 6,
    **changes: Any,  # noqa: ANN401 - the frame builder's fields
) -> Series:
    """A monthly series of a provider, from 2024-01."""
    return monthly(values(count), provider=provider, series_id=series_id, **changes)
