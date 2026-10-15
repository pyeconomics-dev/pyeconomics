# src/pyeconomics/data/vintage.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Vintages: which published version of the data to read (ADR-0011 decision 6).

A source that keeps vintages, such as ALFRED, publishes each observation over
one or more real-time periods: the first release, then each revision. A
:class:`~pyeconomics.data.types.Series` from such a source carries every row's
:class:`~pyeconomics.core.provenance.RealtimePeriod`, and a :class:`Vintage`
selects one row per date:

- :meth:`Vintage.latest`: each date's most recent value in the frame;
- :meth:`Vintage.as_of`: the value that was published on a date, the one whose
  real-time period covers it; dates not yet published then are left out;
- :meth:`Vintage.first_release`: each date's earliest published value;
- :meth:`Vintage.all`: every row, unchanged.

Historical evaluation defaults to ``as_of`` the evaluation date wherever the
source keeps vintages; elsewhere it reads the latest data and says so
(``revised_data``). That choice is the binding layer's (Phase 3 Step 12):
here, ``as_of`` and ``first_release`` on a frame without real-time periods
raise rather than fall back.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import Vintage
>>> Vintage.as_of(dt.date(2008, 12, 16)).label
'as_of:2008-12-16'
>>> Vintage.parse("first_release") == Vintage.first_release()
True

"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import TYPE_CHECKING, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.provenance import (
    DATA_DATE_BOUNDS,
    VINTAGE_LABEL_PATTERN,
    RealtimePeriod,
)
from pyeconomics.data.errors import DataError
from pyeconomics.data.types import Series, Table

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Callable

__all__ = ["Vintage", "VintageKind"]

_AS_OF: Final = "as_of:"


class VintageKind(StrEnum):
    """The four ways to choose among an observation's published values."""

    LATEST = "latest"
    AS_OF = "as_of"
    FIRST_RELEASE = "first_release"
    ALL = "all"


@dataclass(frozen=True, slots=True)
class Vintage:
    """A choice of published values; build one with its class methods."""

    kind: VintageKind
    on: dt.date | None = None
    """The date ``as_of`` reads the data as published on; ``None`` otherwise."""

    def __post_init__(self) -> None:
        """Check that only ``as_of`` names a date, and that it is in bounds."""
        kind = f.choice(VintageKind, self.kind, "kind")
        object.__setattr__(self, "kind", kind)
        if kind is VintageKind.AS_OF:
            f.day(self.on, "the as_of date", DATA_DATE_BOUNDS)
        elif self.on is not None:
            msg = f"only an as_of vintage names a date, not {kind.value}"
            raise f.fail(msg)

    @classmethod
    def latest(cls) -> Vintage:
        """Select each date's most recent value."""
        return cls(VintageKind.LATEST)

    @classmethod
    def as_of(cls, on: dt.date) -> Vintage:
        """Select the values as published on ``on``."""
        return cls(VintageKind.AS_OF, on)

    @classmethod
    def first_release(cls) -> Vintage:
        """Select each date's first published value."""
        return cls(VintageKind.FIRST_RELEASE)

    @classmethod
    def all(cls) -> Vintage:
        """Select every published value of every date."""
        return cls(VintageKind.ALL)

    @property
    def label(self) -> str:
        """The vintage as a data source record names it."""
        if self.on is not None:
            return f"{_AS_OF}{self.on.isoformat()}"
        return self.kind.value

    @classmethod
    def parse(cls, label: str) -> Vintage:
        """Read a vintage back from its :attr:`label`."""
        if not VINTAGE_LABEL_PATTERN.fullmatch(f.text(label, "a vintage label")):
            msg = f"{label!r} is not a vintage label"
            raise f.fail(msg)
        if label.startswith(_AS_OF):
            return cls.as_of(f.parse_day(label.removeprefix(_AS_OF), "the as_of date"))
        return cls(VintageKind(label))

    def select[F: (Series, Table)](self, frame: F) -> F:
        """Return the rows of ``frame`` this vintage chooses, one per date.

        The rows keep their real-time periods, so each value still says when it
        was published. ``all`` returns the frame itself, and so does ``latest``
        on a frame without real-time periods.

        Raises
        ------
        DataError
            For ``as_of`` or ``first_release`` on a frame without real-time
            periods: the source keeps no vintages to choose from.

        """
        if self.kind is VintageKind.ALL:
            return frame
        realtime = frame.realtime
        if realtime is None:
            if self.kind is VintageKind.LATEST:
                return frame
            msg = (
                f"{frame.meta.provider} keeps no vintages of this data, so "
                f"{self.label} cannot be selected; read the latest data instead"
            )
            raise DataError(msg, provider=frame.meta.provider)
        rows = _choose(frame.index, realtime, self._picker())
        return _take(frame, rows, tuple(realtime[row] for row in rows))

    def _picker(self) -> Callable[[list[tuple[int, RealtimePeriod]]], int | None]:
        if self.on is not None:
            return _covering(self.on)
        if self.kind is VintageKind.FIRST_RELEASE:
            return lambda group: group[0][0]
        return lambda group: group[-1][0]


def _covering(on: dt.date) -> Callable[[list[tuple[int, RealtimePeriod]]], int | None]:
    """Pick the row whose real-time period covers ``on``, if any."""
    return lambda group: next((row for row, period in group if period.covers(on)), None)


def _choose(
    index: tuple[dt.date, ...],
    realtime: tuple[RealtimePeriod, ...],
    pick: Callable[[list[tuple[int, RealtimePeriod]]], int | None],
) -> list[int]:
    """Group rows by date (they sort by real-time start within one) and pick."""
    chosen: list[int] = []
    group: list[tuple[int, RealtimePeriod]] = []
    for row, (day, period) in enumerate(zip(index, realtime, strict=True)):
        if group and index[group[0][0]] != day:
            _append(chosen, pick(group))
            group = []
        group.append((row, period))
    if group:
        _append(chosen, pick(group))
    return chosen


def _append(chosen: list[int], row: int | None) -> None:
    if row is not None:
        chosen.append(row)


def _take[F: (Series, Table)](
    frame: F, rows: list[int], realtime: tuple[RealtimePeriod, ...]
) -> F:
    index = tuple(frame.index[row] for row in rows)
    if isinstance(frame, Series):
        values = tuple(frame.values[row] for row in rows)
        return replace(frame, index=index, values=values, realtime=realtime)
    data = tuple(tuple(column[row] for row in rows) for column in frame.data)
    return replace(frame, index=index, data=data, realtime=realtime)
