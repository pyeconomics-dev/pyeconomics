# tests/data/catalog/catalog_world.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A stand-in for every installed provider, so every concept can resolve offline.

For each registered provider this builds a ``DataProvider`` subclass with the
real provider's metadata (class, terms, key, capabilities, extra) and a scripted
exchange, so the resolver's own rules and the base class's gates run for real.
What it returns is synthetic: for every ``(provider, series key)`` a catalog
candidate names, a series or table shaped as that candidate's source would
deliver it before the candidate's transforms. The shape is derived from the
concept's guarantees by undoing the transforms: a year-over-year concept's raw
series is an index, a ``convert`` to quarterly starts from business-daily data, a
``changes_only`` candidate starts from a daily step series, and a candidate that
names a column gets a table with that column.

This proves the catalog and the resolver agree end to end for all 100+ concepts
without a network, a key or a recorded response; the recorded-response tests
(test_recorded_concepts.py) prove real parsers for the concepts whose originators
have cassettes, and the live suite (tests/providers/test_live_concepts.py)
proves every concept against the real sources.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final

from catalog_support import month_end

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import RealtimePeriod
from pyeconomics.core.transforms import parse_transform
from pyeconomics.data import (
    Capability,
    ColumnMeta,
    DataProvider,
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    TableMeta,
    UnitRecord,
    catalog,
    registry,
)
from pyeconomics.data.catalog.definitions import Candidate, Concept, Shape
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.transport.base import Request, Response

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data import Query, Secret
    from pyeconomics.data.transport.base import Transport

__all__ = ["STUB_WHEN", "Fail", "world_registry"]

STUB_WHEN: Final = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)
_FIRST_DAY: Final = dt.date(2025, 1, 1)
_DAYS: Final = 650
_REALTIME: Final = RealtimePeriod(dt.date(2000, 1, 1))


class Fail:
    """A provider id whose requests should fail, for a test to inject."""

    def __init__(self) -> None:
        self.errors: dict[str, Exception] = {}


def _month_ends(
    first: tuple[int, int], last: tuple[int, int], step: int
) -> list[dt.date]:
    out: list[dt.date] = []
    line = first[0] * 12 + first[1] - 1
    stop = last[0] * 12 + last[1] - 1
    while line <= stop:
        year, month = divmod(line, 12)
        out.append(month_end(year, month + 1))
        line += step
    return out


def _dates(frequency: ObservationFrequency, year_end: int) -> list[dt.date]:
    if frequency is ObservationFrequency.MONTHLY:
        return _month_ends((2018, 1), (2026, 9), 1)
    if frequency is ObservationFrequency.QUARTERLY:
        return _month_ends((2018, 3), (2026, 9), 3)
    if frequency is ObservationFrequency.ANNUAL:
        return _month_ends((2000, year_end), (2026, year_end), 12)
    if frequency in {ObservationFrequency.DAILY, ObservationFrequency.IRREGULAR}:
        return [_FIRST_DAY + dt.timedelta(days=i) for i in range(_DAYS)]
    weekdays = [_FIRST_DAY + dt.timedelta(days=i) for i in range(_DAYS)]
    return [d for d in weekdays if d.weekday() < 5]


def _raw_shape(
    concept: Concept, candidate: Candidate
) -> tuple[ObservationFrequency, UnitKind | None]:
    """Undo a candidate's transforms: the frequency and kind its source delivers."""
    frequency = candidate.delivers or concept.frequency
    kind = concept.unit_kind
    for text in candidate.transforms:
        name = parse_transform(text).name
        if name in {"yoy", "pct_change"}:
            kind = UnitKind.INDEX_LEVEL
        elif name == "convert":
            frequency = ObservationFrequency.BUSINESS_DAILY
        elif name == "changes_only":
            frequency = ObservationFrequency.DAILY
    return frequency, kind


def _unit(kind: UnitKind | None) -> UnitRecord:
    if kind is UnitKind.MONEY:
        return UnitRecord(text="Dollars", kind=kind, currency="USD")
    return UnitRecord(text="Units", kind=kind)


def _values(kind: UnitKind | None, count: int, *, steps: bool) -> list[float]:
    base = 0.02 if kind in {UnitKind.RATE, UnitKind.RETURN, UnitKind.RATIO} else 100.0
    increment = 0.0001 if base < 1 else 1.0
    if steps:
        return [base + increment * 25 * (i // 40) for i in range(count)]
    return [base + increment * i for i in range(count)]


def _columns(users: list[tuple[Concept, Candidate]]) -> list[str]:
    """Name the columns a source table needs for every candidate that reads it."""
    names: list[str] = []
    for _, candidate in users:
        if candidate.column is not None:
            wanted = [candidate.column]
        elif candidate.columns:
            wanted = [source for _, source in candidate.columns]
        elif candidate.keep is not None:
            stem = candidate.keep.strip("^$")
            wanted = [f"x{stem}2026", f"x{stem}2027"]
        else:
            wanted = ["c1", "c2", "c3"]
        names += [n for n in wanted if n not in names]
    return names


def _frame(
    info_id: str,
    terms: object,
    users: list[tuple[Concept, Candidate]],
    series_key: str,
    *,
    vintaged: bool,
) -> Series | Table:
    concept, candidate = users[0]
    frequency, kind = _raw_shape(concept, candidate)
    year_end = concept.year_ends_in
    index = _dates(frequency, year_end)
    if frequency is ObservationFrequency.IRREGULAR:
        index = index[::45]
    realtime = tuple(_REALTIME for _ in index) if vintaged else None
    adjustment = (
        concept.seasonal_adjustment
        if concept.seasonal_adjustment is not SeasonalAdjustment.NOT_APPLICABLE
        else SeasonalAdjustment.NOT_APPLICABLE
    )
    steps = any(parse_transform(t).name == "changes_only" for t in candidate.transforms)
    values = _values(kind, len(index), steps=steps)
    anchor = year_end if frequency.needs_year_end else 12
    if concept.shape is Shape.TABLE or any(c.column is not None for _, c in users):
        names = _columns(users)
        columns = tuple(
            ColumnMeta(name=n, unit=_unit(kind), seasonal_adjustment=adjustment)
            for n in names
        )
        meta = TableMeta(
            provider=info_id,
            table_id=series_key,
            title=f"Stub table for {concept.id}",
            frequency=frequency,
            source_dating=DateConvention.PERIOD_END,
            terms=terms,  # type: ignore[arg-type]
            year_ends_in=anchor,
        )
        return Table(
            tuple(index), columns, tuple(tuple(values) for _ in names), meta, realtime
        )
    meta_s = SeriesMeta(
        provider=info_id,
        series_id=series_key,
        title=f"Stub series for {concept.id}",
        unit=_unit(kind),
        frequency=frequency,
        seasonal_adjustment=adjustment,
        source_dating=DateConvention.PERIOD_END,
        terms=terms,  # type: ignore[arg-type]
        year_ends_in=anchor,
    )
    return Series(tuple(index), tuple(values), meta_s, realtime)


def _specs() -> dict[tuple[str, str], list[tuple[Concept, Candidate]]]:
    """Group the catalog's candidates by the provider series they read."""
    found: dict[tuple[str, str], list[tuple[Concept, Candidate]]] = {}
    for concept in catalog.concepts():
        examples = {p.name: p.example for p in concept.parameters}
        for candidate in concept.candidates:
            if isinstance(candidate, Candidate):
                key = candidate.series.format_map(examples)
                found.setdefault((candidate.provider, key), []).append(
                    (concept, candidate)
                )
    return found


def world_registry(fail: Fail | None = None) -> ProviderRegistry:
    """Build a registry of stand-ins for every installed provider."""
    real = registry.installed()
    specs = _specs()
    failures = fail.errors if fail is not None else {}
    classes: list[type[DataProvider]] = []
    for provider_id in real.ids():
        info = real.provider_class(provider_id).info

        def build_requests(self: DataProvider, query: Query) -> Sequence[Request]:
            host = self.info.hosts[0] if self.info.hosts else "api.example.org"
            return (Request(host=host, path="/stub", series=query.series[0]),)

        def exchange(
            self: DataProvider,
            requests: Sequence[Request],
            *,
            key: str | Secret | None,
            transport: Transport | None,
        ) -> Sequence[Response]:
            error = failures.get(self.info.id)
            if error is not None:
                raise error
            return (Response(200, b"{}", STUB_WHEN),)

        def parse(
            self: DataProvider, responses: Sequence[Response], query: Query
        ) -> Series | Table:
            return _frame(
                self.info.id,
                self.info.terms,
                specs[self.info.id, query.series[0]],
                query.series[0],
                vintaged=Capability.VINTAGES in self.info.capabilities,
            )

        classes.append(
            type(
                f"Stub_{provider_id}",
                (DataProvider,),
                {
                    "info": info,
                    "query_type": real.provider_class(provider_id).query_type,
                    "build_requests": build_requests,
                    "exchange": exchange,
                    "parse": parse,
                    "__module__": __name__,
                },
            )
        )
    return ProviderRegistry.from_providers(*classes)
