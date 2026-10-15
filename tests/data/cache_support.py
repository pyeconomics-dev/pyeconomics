# tests/data/cache_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Building blocks for the cache tests (tests/data/cache).

- :class:`WallClock`: the fake wall clock the cache reads, through
  ``cache.override(clock=...)`` (the ``wall`` fixture in tests/conftest.py).
- :func:`toy_case` and :func:`replay_case`: a toy provider's recorded case and a
  transport that replays its cassette, so a fetch is the real pipeline over a
  recorded response and ``ReplayTransport.served`` counts the requests it made.
- :class:`Storable` and :class:`Forbidden`: scripted providers over
  ``tests/providers/stubs.py`` that keep their results in the cache or never may.
- :func:`rows`, :func:`execute`: read and change the database file directly, the
  way a user (or a damaged disk) might, to prove what the cache does with it.
"""

from __future__ import annotations

import datetime as dt
import sqlite3
from contextlib import closing
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final, NoReturn

from provider_contract import replay
from stubs import NOW, STUB_TERMS, Scripted, Stub, answer, series_for, stub_info

from pyeconomics.data import (
    CachePolicy,
    Capability,
    LicenceClass,
    Query,
    RealtimePeriod,
    Series,
)
from pyeconomics.data.cache import store as store_module

if TYPE_CHECKING:
    from pathlib import Path

    import pytest

    from pyeconomics.data import Case, DataProvider, Fetched
    from pyeconomics.data.transport.replay import ReplayTransport

__all__ = [
    "START",
    "Forbidden",
    "Storable",
    "WallClock",
    "execute",
    "latest",
    "no_database",
    "replay_case",
    "revised",
    "rows",
    "scripted",
    "toy_case",
    "toy_query",
]

#: When the fake wall clock starts.
START: Final = NOW


class WallClock:
    """A fake wall clock: call it for the time, advance it for the future."""

    def __init__(self, start: dt.datetime = START) -> None:
        self.now = start

    def __call__(self) -> dt.datetime:
        """Return the fake time."""
        return self.now

    def advance(self, *, seconds: float = 0, days: float = 0) -> None:
        """Move the fake time forward."""
        self.now += dt.timedelta(seconds=seconds, days=days)


def toy_case(provider: type[DataProvider], name: str) -> Case:
    """Return one of a toy provider's recorded cases by name."""
    return next(case for case in provider.cases if case.name == name)


def toy_query(provider: type[DataProvider], name: str) -> Query:
    """Return the query of one of a toy provider's recorded fetch cases."""
    argument = toy_case(provider, name).argument
    assert isinstance(argument, Query)
    return argument


def replay_case(provider: type[DataProvider], name: str) -> ReplayTransport:
    """Return a transport that replays the cassette of a toy provider's case."""
    return replay(provider.info.id, toy_case(provider, name))


def latest(provider: DataProvider, transport: Scripted, **fields: object) -> Fetched:
    """Fetch series ``S`` of a scripted provider, with the query fields given."""
    return provider.fetch_with_origin({"series": ("S",), **fields}, transport=transport)


def no_database(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail if anything so much as asks for sqlite3: the store is unreachable."""

    def refuse() -> NoReturn:
        msg = "the store was reached"
        raise AssertionError(msg)

    monkeypatch.setattr(store_module, "_driver", refuse)


def scripted(*statuses: int) -> Scripted:
    """Return a transport that answers each request in turn with a response."""
    return Scripted(*(answer(status) for status in statuses or (200,)))


class Storable(Stub):
    """A scripted provider whose terms allow storage and which keeps vintages."""

    info = stub_info(
        ttl_seconds=3_600,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )


_FORBIDDEN_TERMS: Final = replace(
    STUB_TERMS, licence=LicenceClass.LIBRARY_ONLY, cache=CachePolicy.FORBIDDEN
)


class Forbidden(Stub):
    """A scripted provider whose terms forbid storage (as FRED's do)."""

    info = stub_info(
        id="forbidden_stub",
        terms=_FORBIDDEN_TERMS,
        ttl_seconds=3_600,
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )

    def __init__(self) -> None:
        super().__init__()
        self.parsed = lambda _r, _q: series_for(
            "forbidden_stub", terms=_FORBIDDEN_TERMS
        )


def revised(provider: str = "stub") -> Series:
    """Return a series whose single date was revised once: two real-time periods.

    The first value was published from 2000-01-01 to 2019-12-31, the second since
    2020-01-01, so every ``as_of`` date from 2000 on selects one.
    """
    base = series_for(provider, dates=1)
    first = RealtimePeriod(dt.date(2000, 1, 1), dt.date(2019, 12, 31))
    second = RealtimePeriod(dt.date(2020, 1, 1), None)
    return Series(base.index * 2, (0.01, 0.02), base.meta, (first, second))


def rows(path: Path, sql: str = "SELECT * FROM entries") -> list[tuple[Any, ...]]:
    """Read rows from a cache database straight through sqlite3."""
    with closing(sqlite3.connect(path)) as connection:
        return connection.execute(sql).fetchall()


def execute(path: Path, sql: str, *params: object) -> None:
    """Change a cache database straight through sqlite3, as a user could."""
    with closing(sqlite3.connect(path)) as connection:
        connection.execute(sql, params)
        connection.commit()
