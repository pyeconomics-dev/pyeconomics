# src/pyeconomics/data/types.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data layer's value types: Series and Table (ADR-0011 decisions 2-5).

A :class:`Series` is immutable: an index of dates, a tuple of values and its
:class:`SeriesMeta`. A :class:`Table` shares one index across named columns,
each with its :class:`ColumnMeta`, under one :class:`TableMeta`. The rules:

- **Bounds.** At most 100,000 observations (:data:`MAX_OBSERVATIONS`, ADR-0008's
  array bound) and 1,000 columns (:data:`MAX_COLUMNS`); anything larger is
  refused with :class:`~pyeconomics.core.errors.InputError`.
- **Missing values** are ``None``: JSON ``null`` and pandas ``NA``, never NaN.
  Values are finite floats; nothing fills a gap (decision 5).
- **Dates.** A period's observation is indexed by the period's last day, the
  period-end convention of ADR-0008 decision 4; the constructor refuses any
  other date. Weekly and biweekly data name the weekday a week ends on, and
  quarterly to annual data the month its year ends in (12 unless a fiscal
  year). The source's own convention, such as FRED's period starts, is kept
  in :attr:`SeriesMeta.source_dating`, and :meth:`Series.periods` returns the
  pandas periods (decision 3). Dates lie in
  :data:`~pyeconomics.core.provenance.DATA_DATE_BOUNDS`.
- **Units.** :class:`UnitRecord` keeps the source's unit text as published, the
  ADR-0008 unit kind where one applies, the scale and the currency. A rate,
  return, probability or volatility is a decimal with scale 1: its provider
  converted it with :func:`~pyeconomics.core.rates.percent_to_decimal`
  (decision 4).
- **Vintages.** From a source that keeps vintages, each observation carries
  its :class:`~pyeconomics.core.provenance.RealtimePeriod`; a date may then
  repeat, once per real-time period, and
  :class:`~pyeconomics.data.vintage.Vintage` selects among them (decision 6).
- **Notes.** A frame's metadata may carry ``notes``: what the source or the
  provider says about the data, each a snake_case code and, after ``": "``,
  a detail, such as ``revised_data`` (a source that keeps only current
  estimates) or ``footnote: P preliminary (2026-08-31, 2026-09-30)``.
- **Round trips.** :meth:`Series.canonical_json` and :meth:`Series.from_json`,
  and :meth:`Series.to_pandas` and :meth:`Series.from_pandas`, are lossless
  (and the same for :class:`Table`). pandas holds the index as
  ``datetime64[us]`` (ADR-0008 decision 9), the values as ``Float64`` and the
  metadata in ``attrs["pyeconomics"]``. Polars and Arrow stay the caller's
  (ADR-0008 decision 8).

No field can hold a credential, a request URL, a host or a path; the one URL
is the terms page inside :class:`~pyeconomics.data.terms.Terms`.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import (
...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
... )
>>> from pyeconomics.core import UnitKind
>>> terms = Terms(
...     licence=LicenceClass.HOSTED_SAFE,
...     terms_url="https://www.bls.gov/developers/termsOfService.htm",
...     checked=dt.date(2026, 10, 14),
...     attribution="Source: US Bureau of Labor Statistics.",
...     llm_use=LlmUse.ALLOWED,
...     cache=CachePolicy.ALLOWED,
... )
>>> meta = SeriesMeta(
...     provider="bls",
...     series_id="LNS14000000",
...     title="Unemployment rate",
...     unit=UnitRecord(text="Percent", kind=UnitKind.RATE),
...     frequency=ObservationFrequency.MONTHLY,
...     seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
...     source_dating=DateConvention.PERIOD_START,
...     terms=terms,
... )
>>> series = Series((dt.date(2026, 7, 31), dt.date(2026, 8, 31)), (0.042, None), meta)
>>> series.missing, [str(p) for p in series.periods()]
(1, ['2026-07', '2026-08'])
>>> Series.from_json(series.canonical_json()) == series
True
>>> Series.from_pandas(series.to_pandas()) == series
True

"""

from __future__ import annotations

import calendar
import datetime as dt
import itertools
import math
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import DATA_DATE_BOUNDS, RealtimePeriod
from pyeconomics.core.units import MAX_ARRAY_LENGTH, UnitKind
from pyeconomics.data.errors import DataError
from pyeconomics.data.terms import Terms

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

__all__ = [
    "DECIMAL_KINDS",
    "FRAME_SCHEMA_VERSION",
    "MAX_COLUMNS",
    "MAX_NOTES",
    "MAX_OBSERVATIONS",
    "PANDAS_ATTRS_KEY",
    "ColumnMeta",
    "DateConvention",
    "ObservationFrequency",
    "SeasonalAdjustment",
    "Series",
    "SeriesMeta",
    "Table",
    "TableMeta",
    "UnitRecord",
    "Weekday",
]

#: The most observations a series, or rows a table, holds (ADR-0008's bound).
MAX_OBSERVATIONS: Final = MAX_ARRAY_LENGTH
#: The most columns a table holds.
MAX_COLUMNS: Final = 1_000
#: The most notes a frame's metadata carries.
MAX_NOTES: Final = 32
#: The layout of a frame's canonical JSON; it goes up when a key changes.
FRAME_SCHEMA_VERSION: Final = 1
#: The key under which a pandas object's ``attrs`` hold the metadata.
PANDAS_ATTRS_KEY: Final = "pyeconomics"
#: The unit kinds whose values are decimals (ADR-0008 decision 1): scale 1.
DECIMAL_KINDS: Final = frozenset(
    {UnitKind.RATE, UnitKind.RETURN, UnitKind.PROBABILITY, UnitKind.VOLATILITY}
)

_MONTHS: Final = (
    "JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC",
)  # fmt: skip
_REALTIME_NAMES: Final = ("date", "realtime_start", "realtime_end")
_MAX_SCALE_EXPONENT: Final = 15
_MAX_COLUMN_NAME: Final = 128
_BIWEEKLY_SPAN: Final = dt.timedelta(days=13)
_SEMIANNUAL_SPAN: Final = 5  # months before a half-year's last month
_FIRST_WEEKEND_DAY: Final = 5  # date.weekday(): Saturday


class Weekday(StrEnum):
    """The day a weekly or biweekly period ends on."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"

    @property
    def number(self) -> int:
        """The day's number as :meth:`datetime.date.weekday` counts: Monday 0."""
        return tuple(Weekday).index(self)

    @property
    def pandas(self) -> str:
        """The day's pandas anchor, such as ``FRI``."""
        return self.value[:3].upper()


class ObservationFrequency(StrEnum):
    """How often a source observes a series (ADR-0011 decision 3).

    It is separate from :class:`~pyeconomics.core.compounding.Frequency`, which
    says how a rate compounds. Weekly and biweekly data name the weekday their
    periods end on; quarterly, semiannual and annual data the month their year
    ends in.

    Examples
    --------
    >>> ObservationFrequency.MONTHLY.pandas_alias()
    'ME'
    >>> ObservationFrequency.WEEKLY.pandas_alias(week_ends_on=Weekday.FRIDAY)
    'W-FRI'
    >>> ObservationFrequency.ANNUAL.pandas_alias(year_ends_in=9)
    'YE-SEP'

    """

    DAILY = "daily"
    BUSINESS_DAILY = "business_daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    ANNUAL = "annual"
    IRREGULAR = "irregular"

    @property
    def needs_weekday(self) -> bool:
        """Whether the periods end on a named weekday."""
        return self in {ObservationFrequency.WEEKLY, ObservationFrequency.BIWEEKLY}

    @property
    def needs_year_end(self) -> bool:
        """Whether the periods are fractions of a year that ends in a named month."""
        return self in {
            ObservationFrequency.QUARTERLY,
            ObservationFrequency.SEMIANNUAL,
            ObservationFrequency.ANNUAL,
        }

    def pandas_alias(
        self, *, week_ends_on: Weekday | None = None, year_ends_in: int = 12
    ) -> str | None:
        """Return the pandas 3 offset alias for period-end dates at this frequency.

        ``IRREGULAR`` has none. Semiannual data use ``6ME``, as
        :class:`~pyeconomics.core.compounding.Frequency` does.
        """
        week_ends_on, year_ends_in = _calendar(self, week_ends_on, year_ends_in)
        month = _MONTHS[year_ends_in - 1]
        aliases: dict[ObservationFrequency, str | None] = {
            ObservationFrequency.DAILY: "D",
            ObservationFrequency.BUSINESS_DAILY: "B",
            ObservationFrequency.MONTHLY: "ME",
            ObservationFrequency.QUARTERLY: f"QE-{month}",
            ObservationFrequency.SEMIANNUAL: "6ME",
            ObservationFrequency.ANNUAL: f"YE-{month}",
            ObservationFrequency.IRREGULAR: None,
        }
        if week_ends_on is not None:
            prefix = "2W" if self is ObservationFrequency.BIWEEKLY else "W"
            return f"{prefix}-{week_ends_on.pandas}"
        return aliases[self]


class SeasonalAdjustment(StrEnum):
    """Whether, and how, a source seasonally adjusted a series."""

    SEASONALLY_ADJUSTED = "seasonally_adjusted"
    SEASONALLY_ADJUSTED_ANNUAL_RATE = "seasonally_adjusted_annual_rate"
    NOT_SEASONALLY_ADJUSTED = "not_seasonally_adjusted"
    NOT_APPLICABLE = "not_applicable"


class DateConvention(StrEnum):
    """How the source itself dates an observation (ADR-0011 decision 3).

    pyeconomics always indexes a period by its last day; this records what the
    source published, so a reader can match the source's own tables.
    """

    PERIOD_START = "period_start"
    """The first day of the period, as FRED, BLS and BEA date months and quarters."""
    PERIOD_END = "period_end"
    """The last day of the period."""
    POINT_IN_TIME = "point_in_time"
    """The day of the observation itself, such as a daily rate or an event."""


# --- shared checks ------------------------------------------------------------

#: The months in one period of each month-based frequency.
_MONTHS_PER_PERIOD: Final = {
    ObservationFrequency.MONTHLY: 1,
    ObservationFrequency.QUARTERLY: 3,
    ObservationFrequency.SEMIANNUAL: 6,
    ObservationFrequency.ANNUAL: 12,
}


def _calendar(
    frequency: ObservationFrequency, week_ends_on: object, year_ends_in: object
) -> tuple[Weekday | None, int]:
    """Check a frequency's anchors: a weekday when it needs one, a year-end month."""
    if frequency.needs_weekday:
        if week_ends_on is None:
            msg = f"{frequency.value} data must name week_ends_on"
            raise f.fail(msg)
        weekday: Weekday | None = f.choice(Weekday, week_ends_on, "week_ends_on")
    elif week_ends_on is not None:
        msg = f"only weekly and biweekly data name week_ends_on, not {frequency.value}"
        raise f.fail(msg)
    else:
        weekday = None
    if isinstance(year_ends_in, bool) or not isinstance(year_ends_in, int):
        msg = f"year_ends_in must be a month number, not {year_ends_in!r}"
        raise f.fail(msg)
    if not 1 <= year_ends_in <= len(_MONTHS):
        msg = f"year_ends_in must be a month from 1 to 12, not {year_ends_in}"
        raise f.fail(msg)
    if year_ends_in != len(_MONTHS) and not frequency.needs_year_end:
        msg = f"{frequency.value} data have no fiscal year-end month"
        raise f.fail(msg)
    return weekday, year_ends_in


def _is_month_end(day: dt.date) -> bool:
    return day.day == calendar.monthrange(day.year, day.month)[1]


def _is_period_end(
    day: dt.date,
    frequency: ObservationFrequency,
    week_ends_on: Weekday | None,
    year_ends_in: int,
) -> bool:
    """Return whether ``day`` is the last day of a period at ``frequency``."""
    if week_ends_on is not None:
        return day.weekday() == week_ends_on.number
    if frequency is ObservationFrequency.BUSINESS_DAILY:
        return day.weekday() < _FIRST_WEEKEND_DAY
    step = _MONTHS_PER_PERIOD.get(frequency)
    if step is None:  # daily and irregular data end any day
        return True
    return _is_month_end(day) and (day.month - year_ends_in) % step == 0


def _values(values: object, rows: int, what: str) -> tuple[float | None, ...]:
    """Accept finite numbers or ``None``, one per row; numbers become floats."""
    items = f.sequence(values, what, max_items=MAX_OBSERVATIONS)
    if len(items) != rows:
        msg = f"{what} holds {len(items)} values for {rows} dates"
        raise f.fail(msg)
    return tuple(_value(item, what) for item in items)


def _value(value: object, what: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool | np.bool_) or not isinstance(
        value, int | float | np.integer | np.floating
    ):
        msg = f"{what} holds numbers or None, not {type(value).__name__}"
        raise f.fail(msg)
    try:
        number = float(value)
    except OverflowError as error:
        msg = f"{what} holds a number too large for a float"
        raise f.fail(msg) from error
    if not math.isfinite(number):
        msg = f"{what} holds a missing value as {number!r}; use None (never NaN)"
        raise f.fail(msg)
    return number


def _index(
    index: object,
    realtime: object,
    frequency: ObservationFrequency,
    week_ends_on: Weekday | None,
    year_ends_in: int,
) -> tuple[tuple[dt.date, ...], tuple[RealtimePeriod, ...] | None]:
    """Check the dates and any real-time periods, row by row."""
    dates = f.sequence(index, "index", max_items=MAX_OBSERVATIONS)
    checked = tuple(f.day(day, "each index date", DATA_DATE_BOUNDS) for day in dates)
    for day in checked:
        if not _is_period_end(day, frequency, week_ends_on, year_ends_in):
            msg = f"{day} is not the last day of a {frequency.value} period"
            raise f.fail(msg)
    if realtime is None:
        for earlier, later in itertools.pairwise(checked):
            if later <= earlier:
                msg = f"index dates must increase: {later} follows {earlier}"
                raise f.fail(msg)
        return checked, None
    periods = f.sequence(realtime, "realtime", max_items=MAX_OBSERVATIONS)
    if len(periods) != len(checked):
        msg = f"realtime holds {len(periods)} periods for {len(checked)} dates"
        raise f.fail(msg)
    typed = tuple(
        f.instance(period, RealtimePeriod, "each real-time period")
        for period in periods
    )
    rows = tuple(zip(checked, typed, strict=True))
    for (day, first), (next_day, second) in itertools.pairwise(rows):
        _check_order(day, first, next_day, second)
    return checked, typed


def _check_order(
    day: dt.date, earlier: RealtimePeriod, next_day: dt.date, later: RealtimePeriod
) -> None:
    """Rows sort by date, then real-time start; one date's periods never overlap."""
    if next_day < day:
        msg = f"index dates must not decrease: {next_day} follows {day}"
        raise f.fail(msg)
    if next_day == day and (
        earlier.realtime_end is None or earlier.realtime_end >= later.realtime_start
    ):
        msg = (
            f"the real-time periods of {day} must follow one another without "
            "overlapping"
        )
        raise f.fail(msg)


def _period_alias(
    frequency: ObservationFrequency, week_ends_on: Weekday | None, year_ends_in: int
) -> str:
    """Return the pandas period alias whose periods the index dates end."""
    month = _MONTHS[year_ends_in - 1]
    if week_ends_on is not None:
        prefix = "2W" if frequency is ObservationFrequency.BIWEEKLY else "W"
        return f"{prefix}-{week_ends_on.pandas}"
    aliases = {
        # pandas deprecates business-day periods; a business day is a day.
        ObservationFrequency.DAILY: "D",
        ObservationFrequency.BUSINESS_DAILY: "D",
        ObservationFrequency.MONTHLY: "M",
        ObservationFrequency.QUARTERLY: f"Q-{month}",
        ObservationFrequency.SEMIANNUAL: "6M",
        ObservationFrequency.ANNUAL: f"Y-{month}",
    }
    if frequency not in aliases:
        msg = "an irregular series has no periods"
        raise DataError(msg)
    return aliases[frequency]


def _period_start(day: dt.date, frequency: ObservationFrequency) -> dt.date:
    """Return a day inside the period whose alias pandas anchors at its start."""
    if frequency is ObservationFrequency.BIWEEKLY:
        return day - _BIWEEKLY_SPAN
    if frequency is ObservationFrequency.SEMIANNUAL:
        year, month = divmod(day.year * 12 + day.month - 1 - _SEMIANNUAL_SPAN, 12)
        return dt.date(year, month + 1, 1)
    return day


def _periods(
    index: tuple[dt.date, ...],
    frequency: ObservationFrequency,
    week_ends_on: Weekday | None,
    year_ends_in: int,
) -> pd.PeriodIndex:
    alias = _period_alias(frequency, week_ends_on, year_ends_in)
    starts = [_period_start(day, frequency) for day in index]
    return _datetimes(starts).to_period(alias)


def _datetimes(days: Sequence[dt.date | None], name: str = "date") -> pd.DatetimeIndex:
    """Build a ``datetime64[us]`` index; ``None`` becomes ``NaT``."""
    array = np.array(days, dtype="datetime64[D]").astype("datetime64[us]")
    return pd.DatetimeIndex(array, name=name)


def _pandas_index(
    index: tuple[dt.date, ...], realtime: tuple[RealtimePeriod, ...] | None
) -> pd.Index[Any]:
    if realtime is None:
        return _datetimes(index)
    return pd.MultiIndex.from_arrays(
        [
            _datetimes(index),
            _datetimes([period.realtime_start for period in realtime]),
            _datetimes([period.realtime_end for period in realtime]),
        ],
        names=list(_REALTIME_NAMES),
    )


def _dates_of(index: pd.Index[Any], what: str) -> list[dt.date | None]:
    """Read midnight, timezone-naive timestamps back as dates (``NaT`` as None)."""
    if not isinstance(index, pd.DatetimeIndex) or index.tz is not None:
        msg = f"{what} must be a timezone-naive DatetimeIndex"
        raise f.fail(msg)
    present = index[index.notna()]
    if not present.equals(present.normalize()):
        msg = f"{what} holds a time of day; dates only"
        raise f.fail(msg)
    return [
        None if gone else stamp.date()
        for stamp, gone in zip(index, index.isna(), strict=True)
    ]


def _from_pandas_index(
    index: pd.Index[Any],
) -> tuple[tuple[dt.date, ...], tuple[RealtimePeriod, ...] | None]:
    """Read the dates, and any real-time periods, from a pandas index."""
    if not isinstance(index, pd.MultiIndex):
        days = _dates_of(index, "the index")
        return tuple(
            f.day(day, "each index date", DATA_DATE_BOUNDS) for day in days
        ), None
    if tuple(index.names) != _REALTIME_NAMES:
        msg = f"a real-time index has the levels {list(_REALTIME_NAMES)}"
        raise f.fail(msg)
    days, starts, ends = (
        _dates_of(index.get_level_values(level), level) for level in _REALTIME_NAMES
    )
    realtime = tuple(
        RealtimePeriod(
            f.day(start, "realtime_start", DATA_DATE_BOUNDS),
            f.optional_day(end, "realtime_end", DATA_DATE_BOUNDS),
        )
        for start, end in zip(starts, ends, strict=True)
    )
    return tuple(
        f.day(day, "each index date", DATA_DATE_BOUNDS) for day in days
    ), realtime


def _pandas_values(values: pd.Series[Any]) -> list[object]:
    """Read values back; whatever pandas treats as missing becomes ``None``."""
    return [None if pd.isna(value) else value for value in values.tolist()]


def _attrs(obj: pd.Series[Any] | pd.DataFrame, kind: str) -> Mapping[str, object]:
    attrs = obj.attrs.get(PANDAS_ATTRS_KEY)
    if not isinstance(attrs, dict) or attrs.get("type") != kind:
        msg = f"the pandas object carries no {kind} metadata; pass meta="
        raise f.fail(msg)
    return attrs


def _realtime_dicts(
    realtime: tuple[RealtimePeriod, ...] | None,
) -> list[list[str | None]] | None:
    if realtime is None:
        return None
    return [
        [
            period.realtime_start.isoformat(),
            None if period.realtime_end is None else period.realtime_end.isoformat(),
        ]
        for period in realtime
    ]


def _realtime_from(value: object) -> tuple[RealtimePeriod, ...] | None:
    if value is None:
        return None
    pairs = f.sequence(value, "realtime", max_items=MAX_OBSERVATIONS)
    periods = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:  # noqa: PLR2004 - a pair
            msg = "realtime holds [realtime_start, realtime_end] pairs"
            raise f.fail(msg)
        periods.append(
            RealtimePeriod(
                f.parse_day(pair[0], "realtime_start"),
                f.parse_optional_day(pair[1], "realtime_end"),
            )
        )
    return tuple(periods)


def _index_from(value: object) -> tuple[dt.date, ...]:
    days = f.sequence(value, "index", max_items=MAX_OBSERVATIONS)
    return tuple(f.parse_day(day, "each index date") for day in days)


def _frame(data: object, kind: str, keys: Sequence[str]) -> Mapping[str, object]:
    fields = f.mapping(data, f"a {kind}", keys)
    version = fields["schema_version"]
    if (
        fields["type"] != kind
        or isinstance(version, bool)
        or version != FRAME_SCHEMA_VERSION
    ):
        msg = (
            f"not a {kind} of schema {FRAME_SCHEMA_VERSION}: type "
            f"{fields['type']!r}, schema {fields['schema_version']!r}"
        )
        raise f.fail(msg)
    return fields


def _iso(value: dt.datetime | None) -> str | None:
    return None if value is None else value.isoformat()


# --- metadata -----------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class UnitRecord:
    """A series' unit: as the source published it, and what it means here.

    Examples
    --------
    >>> UnitRecord(text="Billions of Dollars", kind=UnitKind.MONEY, scale=1e9,
    ...            currency="USD").scale
    1000000000.0

    """

    text: str
    """The unit as the source published it, such as ``Percent``."""
    kind: UnitKind | None = None
    """The ADR-0008 unit kind, where one applies."""
    scale: float = 1.0
    """The power of ten the values are in: 1e9 for billions. A decimal kind
    (:data:`DECIMAL_KINDS`) has scale 1."""
    currency: str | None = None
    """The ISO 4217 currency of a money series."""

    def __post_init__(self) -> None:
        """Check the text, kind, scale and currency."""
        f.text(self.text, "unit text")
        kind = None if self.kind is None else f.choice(UnitKind, self.kind, "unit kind")
        if kind is UnitKind.DATE:
            msg = "a series' values are numbers; date is not a value unit"
            raise f.fail(msg)
        scale = _value(self.scale, "scale")
        exponent = 0 if scale is None or scale <= 0 else round(math.log10(scale))
        if (
            scale is None
            or abs(exponent) > _MAX_SCALE_EXPONENT
            or scale != float(f"1e{exponent}")
        ):
            msg = f"scale must be a power of ten from 1e-15 to 1e15, not {self.scale!r}"
            raise f.fail(msg)
        if kind in DECIMAL_KINDS and scale != 1.0:
            msg = f"{kind.value} values are decimals with scale 1, not {scale!r}"
            raise f.fail(msg)
        _currency(self.currency)
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "scale", scale)

    def to_dict(self) -> dict[str, object]:
        """Return the unit as JSON-ready values."""
        return {
            "text": self.text,
            "kind": None if self.kind is None else self.kind.value,
            "scale": self.scale,
            "currency": self.currency,
        }

    @classmethod
    def from_dict(cls, data: object) -> UnitRecord:
        """Read a unit back from :meth:`to_dict`'s form."""
        keys = ("text", "kind", "scale", "currency")
        values: dict[str, Any] = dict(f.mapping(data, "a unit", keys))
        return cls(**values)


def _notes(value: object) -> tuple[str, ...]:
    """Accept notes: a snake_case code, then optionally ``": "`` and a detail."""
    items = f.sequence(value, "notes", max_items=MAX_NOTES)
    checked = tuple(
        f.text(item, "each note", max_length=f.MAX_TEXT_LENGTH) for item in items
    )
    for note in checked:
        f.identifier(note.split(": ", 1)[0], "a note's code")
    if len(set(checked)) != len(checked):
        msg = "notes must not repeat a note"
        raise f.fail(msg)
    return checked


def _currency(value: object) -> None:
    """Accept ``None`` or an ISO 4217 code: three uppercase ASCII letters."""
    if value is not None and not (
        isinstance(value, str)
        and len(value) == 3  # noqa: PLR2004 - ISO 4217 codes
        and value.isascii()
        and value.isupper()
        and value.isalpha()
    ):
        msg = f"currency must be an ISO 4217 code such as USD, not {value!r}"
        raise f.fail(msg)


@dataclass(frozen=True, slots=True, kw_only=True)
class SeriesMeta:
    """What a series is, where it came from and on what terms."""

    provider: str
    """The provider's permanent id."""
    series_id: str
    """The provider's own id for the series."""
    dataset: str | None = None
    """The provider's dataset or release, when it has one."""
    title: str
    """The series' title, as the source gives it."""
    unit: UnitRecord
    """The values' unit."""
    frequency: ObservationFrequency
    """How often the source observes the series."""
    week_ends_on: Weekday | None = None
    """The weekday a weekly or biweekly period ends on."""
    year_ends_in: int = 12
    """The month a quarterly, semiannual or annual series' year ends in."""
    seasonal_adjustment: SeasonalAdjustment
    """Whether the source seasonally adjusted the series."""
    source_dating: DateConvention
    """How the source itself dates an observation."""
    terms: Terms
    """The terms the series' data came under (the provider's, or the series'
    own where its source marks it differently)."""
    retrieved_at: dt.datetime | None = None
    """When the provider fetched it, in UTC."""
    notes: tuple[str, ...] = ()
    """What the source or the provider says about the data: each a snake_case
    code, then optionally ``": "`` and a detail (``revised_data``,
    ``footnote: P preliminary (2026-08-31)``)."""

    def __post_init__(self) -> None:
        """Check every field; accept enum values as well as members."""
        f.identifier(self.provider, "provider")
        f.text(self.series_id, "series_id")
        f.optional_text(self.dataset, "dataset")
        f.text(self.title, "title")
        f.instance(self.unit, UnitRecord, "unit")
        f.instance(self.terms, Terms, "terms")
        frequency = f.choice(ObservationFrequency, self.frequency, "frequency")
        weekday, _ = _calendar(frequency, self.week_ends_on, self.year_ends_in)
        normalized = {
            "frequency": frequency,
            "week_ends_on": weekday,
            "seasonal_adjustment": f.choice(
                SeasonalAdjustment, self.seasonal_adjustment, "seasonal_adjustment"
            ),
            "source_dating": f.choice(
                DateConvention, self.source_dating, "source_dating"
            ),
            "retrieved_at": f.optional_instant(self.retrieved_at, "retrieved_at"),
            "notes": _notes(self.notes),
        }
        for name, value in normalized.items():
            object.__setattr__(self, name, value)

    @property
    def pandas_alias(self) -> str | None:
        """The pandas offset alias of the series' period ends."""
        return self.frequency.pandas_alias(
            week_ends_on=self.week_ends_on, year_ends_in=self.year_ends_in
        )

    def to_dict(self) -> dict[str, object]:
        """Return the metadata as JSON-ready values."""
        return {
            "provider": self.provider,
            "series_id": self.series_id,
            "dataset": self.dataset,
            "title": self.title,
            "unit": self.unit.to_dict(),
            "frequency": self.frequency.value,
            "week_ends_on": None
            if self.week_ends_on is None
            else self.week_ends_on.value,
            "year_ends_in": self.year_ends_in,
            "seasonal_adjustment": self.seasonal_adjustment.value,
            "source_dating": self.source_dating.value,
            "terms": self.terms.to_dict(),
            "retrieved_at": _iso(self.retrieved_at),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: object) -> SeriesMeta:
        """Read metadata back from :meth:`to_dict`'s form."""
        values: dict[str, Any] = dict(
            f.mapping(data, "series metadata", _SERIES_META_KEYS)
        )
        values["unit"] = UnitRecord.from_dict(values["unit"])
        values["terms"] = Terms.from_dict(values["terms"])
        values["retrieved_at"] = f.parse_instant(values["retrieved_at"], "retrieved_at")
        return cls(**values)


_SERIES_META_KEYS: Final = (
    "provider",
    "series_id",
    "dataset",
    "title",
    "unit",
    "frequency",
    "week_ends_on",
    "year_ends_in",
    "seasonal_adjustment",
    "source_dating",
    "terms",
    "retrieved_at",
    "notes",
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ColumnMeta:
    """One column of a table: its name, the source's id for it, and its unit."""

    name: str
    """The column's name, unique within its table."""
    unit: UnitRecord
    """The column's unit."""
    seasonal_adjustment: SeasonalAdjustment
    """Whether the source seasonally adjusted the column."""
    series_id: str | None = None
    """The source's own id for the column's series, when it has one."""
    title: str | None = None
    """The column's title, when the source gives one."""

    def __post_init__(self) -> None:
        """Check every field."""
        f.text(self.name, "column name", max_length=_MAX_COLUMN_NAME)
        f.instance(self.unit, UnitRecord, "unit")
        object.__setattr__(
            self,
            "seasonal_adjustment",
            f.choice(
                SeasonalAdjustment, self.seasonal_adjustment, "seasonal_adjustment"
            ),
        )
        f.optional_text(self.series_id, "series_id")
        f.optional_text(self.title, "title")

    def to_dict(self) -> dict[str, object]:
        """Return the column metadata as JSON-ready values."""
        return {
            "name": self.name,
            "unit": self.unit.to_dict(),
            "seasonal_adjustment": self.seasonal_adjustment.value,
            "series_id": self.series_id,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: object) -> ColumnMeta:
        """Read column metadata back from :meth:`to_dict`'s form."""
        values: dict[str, Any] = dict(f.mapping(data, "column metadata", _COLUMN_KEYS))
        values["unit"] = UnitRecord.from_dict(values["unit"])
        return cls(**values)


_COLUMN_KEYS: Final = ("name", "unit", "seasonal_adjustment", "series_id", "title")


@dataclass(frozen=True, slots=True, kw_only=True)
class TableMeta:
    """What a table is, where it came from and on what terms."""

    provider: str
    """The provider's permanent id."""
    table_id: str
    """The provider's own id for the table."""
    dataset: str | None = None
    """The provider's dataset or release, when it has one."""
    title: str
    """The table's title, as the source gives it."""
    frequency: ObservationFrequency
    """How often the source observes the rows."""
    week_ends_on: Weekday | None = None
    """The weekday a weekly or biweekly period ends on."""
    year_ends_in: int = 12
    """The month a quarterly, semiannual or annual table's year ends in."""
    source_dating: DateConvention
    """How the source itself dates a row."""
    terms: Terms
    """The terms the table's data came under."""
    retrieved_at: dt.datetime | None = None
    """When the provider fetched it, in UTC."""
    notes: tuple[str, ...] = ()
    """What the source or the provider says about the data (see
    :attr:`SeriesMeta.notes`)."""

    def __post_init__(self) -> None:
        """Check every field; accept enum values as well as members."""
        f.identifier(self.provider, "provider")
        f.text(self.table_id, "table_id")
        f.optional_text(self.dataset, "dataset")
        f.text(self.title, "title")
        f.instance(self.terms, Terms, "terms")
        frequency = f.choice(ObservationFrequency, self.frequency, "frequency")
        weekday, _ = _calendar(frequency, self.week_ends_on, self.year_ends_in)
        normalized = {
            "frequency": frequency,
            "week_ends_on": weekday,
            "source_dating": f.choice(
                DateConvention, self.source_dating, "source_dating"
            ),
            "retrieved_at": f.optional_instant(self.retrieved_at, "retrieved_at"),
            "notes": _notes(self.notes),
        }
        for name, value in normalized.items():
            object.__setattr__(self, name, value)

    @property
    def pandas_alias(self) -> str | None:
        """The pandas offset alias of the table's period ends."""
        return self.frequency.pandas_alias(
            week_ends_on=self.week_ends_on, year_ends_in=self.year_ends_in
        )

    def to_dict(self) -> dict[str, object]:
        """Return the metadata as JSON-ready values."""
        return {
            "provider": self.provider,
            "table_id": self.table_id,
            "dataset": self.dataset,
            "title": self.title,
            "frequency": self.frequency.value,
            "week_ends_on": None
            if self.week_ends_on is None
            else self.week_ends_on.value,
            "year_ends_in": self.year_ends_in,
            "source_dating": self.source_dating.value,
            "terms": self.terms.to_dict(),
            "retrieved_at": _iso(self.retrieved_at),
            "notes": list(self.notes),
        }

    @classmethod
    def from_dict(cls, data: object) -> TableMeta:
        """Read metadata back from :meth:`to_dict`'s form."""
        values: dict[str, Any] = dict(
            f.mapping(data, "table metadata", _TABLE_META_KEYS)
        )
        values["terms"] = Terms.from_dict(values["terms"])
        values["retrieved_at"] = f.parse_instant(values["retrieved_at"], "retrieved_at")
        return cls(**values)


_TABLE_META_KEYS: Final = (
    "provider",
    "table_id",
    "dataset",
    "title",
    "frequency",
    "week_ends_on",
    "year_ends_in",
    "source_dating",
    "terms",
    "retrieved_at",
    "notes",
)


# --- frames -------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Series:
    """One series: dates, values and metadata, immutable.

    Parameters
    ----------
    index
        The observation dates, each its period's last day, increasing; with
        ``realtime``, a date repeats once per real-time period, in order.
    values
        One finite number or ``None`` (missing) per date.
    meta
        What the series is and the terms it came under.
    realtime
        One real-time period per date, from a source that keeps vintages.

    """

    index: tuple[dt.date, ...]
    values: tuple[float | None, ...]
    meta: SeriesMeta
    realtime: tuple[RealtimePeriod, ...] | None = None

    def __post_init__(self) -> None:
        """Check the bounds, dates, values and real-time periods."""
        f.instance(self.meta, SeriesMeta, "meta")
        meta = self.meta
        index, realtime = _index(
            self.index,
            self.realtime,
            meta.frequency,
            meta.week_ends_on,
            meta.year_ends_in,
        )
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "realtime", realtime)
        object.__setattr__(self, "values", _values(self.values, len(index), "values"))

    def __len__(self) -> int:
        """Return the number of observations."""
        return len(self.index)

    @property
    def missing(self) -> int:
        """The number of missing (``None``) observations."""
        return sum(value is None for value in self.values)

    @property
    def has_realtime(self) -> bool:
        """Whether the observations carry real-time periods."""
        return self.realtime is not None

    def periods(self) -> pd.PeriodIndex:
        """Return each observation's period as a pandas ``Period``.

        Raises
        ------
        DataError
            For an irregular series, which has no periods.

        """
        meta = self.meta
        return _periods(
            self.index, meta.frequency, meta.week_ends_on, meta.year_ends_in
        )

    def to_dict(self) -> dict[str, object]:
        """Return the series as JSON-ready values."""
        return {
            "schema_version": FRAME_SCHEMA_VERSION,
            "type": "series",
            "meta": self.meta.to_dict(),
            "index": [day.isoformat() for day in self.index],
            "values": list(self.values),
            "realtime": _realtime_dicts(self.realtime),
        }

    def canonical_json(self) -> bytes:
        """Return the series as canonical JSON (RFC 8785)."""
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: object) -> Series:
        """Read a series back from :meth:`to_dict`'s form, refusing any other."""
        fields = _frame(data, "series", _SERIES_KEYS)
        index = _index_from(fields["index"])
        return cls(
            index,
            _values(fields["values"], len(index), "values"),
            SeriesMeta.from_dict(fields["meta"]),
            _realtime_from(fields["realtime"]),
        )

    @classmethod
    def from_json(cls, document: str | bytes) -> Series:
        """Read a series back from its canonical JSON."""
        return cls.from_dict(f.load_json(document))

    def to_pandas(self) -> pd.Series[Any]:
        """Return a pandas ``Float64`` series, missing values as ``NA``.

        The index is a ``datetime64[us]`` ``DatetimeIndex`` named ``date``, or,
        with real-time periods, a ``MultiIndex`` of ``date``,
        ``realtime_start`` and ``realtime_end`` (``NaT`` while current). The
        metadata is in ``attrs["pyeconomics"]``.
        """
        result = pd.Series(
            pd.array(list(self.values), dtype="Float64"),
            index=_pandas_index(self.index, self.realtime),
            name=self.meta.series_id,
        )
        result.attrs[PANDAS_ATTRS_KEY] = {"type": "series", "meta": self.meta.to_dict()}
        return result

    @classmethod
    def from_pandas(
        cls, series: pd.Series[Any], meta: SeriesMeta | None = None
    ) -> Series:
        """Build a series from pandas, reading the metadata from its ``attrs``.

        Parameters
        ----------
        series
            A series laid out as :meth:`to_pandas` lays it out.
        meta
            The metadata, when ``series.attrs`` does not hold it.

        """
        if meta is None:
            meta = SeriesMeta.from_dict(_attrs(series, "series")["meta"])
        index, realtime = _from_pandas_index(series.index)
        values = _values(_pandas_values(series), len(index), "values")
        return cls(index, values, meta, realtime)


_SERIES_KEYS: Final = ("schema_version", "type", "meta", "index", "values", "realtime")


@dataclass(frozen=True, slots=True)
class Table:
    """Columns that share one index of dates, immutable.

    Parameters
    ----------
    index
        The row dates, as :class:`Series` takes them.
    columns
        Each column's metadata; names are unique.
    data
        One tuple of values per column, each one value per row.
    meta
        What the table is and the terms it came under.
    realtime
        One real-time period per row, from a source that keeps vintages.

    """

    index: tuple[dt.date, ...]
    columns: tuple[ColumnMeta, ...]
    data: tuple[tuple[float | None, ...], ...]
    meta: TableMeta
    realtime: tuple[RealtimePeriod, ...] | None = None

    def __post_init__(self) -> None:
        """Check the bounds, dates, columns, values and real-time periods."""
        f.instance(self.meta, TableMeta, "meta")
        meta = self.meta
        index, realtime = _index(
            self.index,
            self.realtime,
            meta.frequency,
            meta.week_ends_on,
            meta.year_ends_in,
        )
        items = f.sequence(self.columns, "columns", max_items=MAX_COLUMNS)
        columns = tuple(f.instance(item, ColumnMeta, "each column") for item in items)
        names = [column.name for column in columns]
        if len(set(names)) != len(names):
            msg = "column names must be unique"
            raise f.fail(msg)
        data = f.sequence(self.data, "data", max_items=MAX_COLUMNS)
        if len(data) != len(columns):
            msg = f"data holds {len(data)} columns of values for {len(columns)} columns"
            raise f.fail(msg)
        values = tuple(
            _values(column, len(index), f"column {name!r}")
            for name, column in zip(names, data, strict=True)
        )
        object.__setattr__(self, "index", index)
        object.__setattr__(self, "realtime", realtime)
        object.__setattr__(self, "columns", columns)
        object.__setattr__(self, "data", values)

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.index)

    @property
    def column_names(self) -> tuple[str, ...]:
        """The columns' names, in order."""
        return tuple(column.name for column in self.columns)

    @property
    def has_realtime(self) -> bool:
        """Whether the rows carry real-time periods."""
        return self.realtime is not None

    def column(self, name: str) -> Series:
        """Return one column as a series with the table's dates and terms.

        The series' id is the column's ``series_id`` when it has one, else its
        name, and its dataset is the table's id.

        Raises
        ------
        KeyError
            If the table has no column of that name.

        """
        try:
            position = self.column_names.index(name)
        except ValueError:
            msg = f"the table has no column {name!r}"
            raise KeyError(msg) from None
        column, meta = self.columns[position], self.meta
        series_meta = SeriesMeta(
            provider=meta.provider,
            series_id=column.series_id or column.name,
            dataset=meta.table_id,
            title=column.title or column.name,
            unit=column.unit,
            frequency=meta.frequency,
            week_ends_on=meta.week_ends_on,
            year_ends_in=meta.year_ends_in,
            seasonal_adjustment=column.seasonal_adjustment,
            source_dating=meta.source_dating,
            terms=meta.terms,
            retrieved_at=meta.retrieved_at,
        )
        return Series(self.index, self.data[position], series_meta, self.realtime)

    def periods(self) -> pd.PeriodIndex:
        """Return each row's period as a pandas ``Period``."""
        meta = self.meta
        return _periods(
            self.index, meta.frequency, meta.week_ends_on, meta.year_ends_in
        )

    def to_dict(self) -> dict[str, object]:
        """Return the table as JSON-ready values; ``data`` holds one list per column."""
        return {
            "schema_version": FRAME_SCHEMA_VERSION,
            "type": "table",
            "meta": self.meta.to_dict(),
            "columns": [column.to_dict() for column in self.columns],
            "index": [day.isoformat() for day in self.index],
            "data": [list(values) for values in self.data],
            "realtime": _realtime_dicts(self.realtime),
        }

    def canonical_json(self) -> bytes:
        """Return the table as canonical JSON (RFC 8785)."""
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: object) -> Table:
        """Read a table back from :meth:`to_dict`'s form, refusing any other."""
        fields = _frame(data, "table", _TABLE_KEYS)
        columns = f.sequence(fields["columns"], "columns", max_items=MAX_COLUMNS)
        data = f.sequence(fields["data"], "data", max_items=MAX_COLUMNS)
        index = _index_from(fields["index"])
        return cls(
            index,
            tuple(ColumnMeta.from_dict(column) for column in columns),
            tuple(_values(values, len(index), "each column") for values in data),
            TableMeta.from_dict(fields["meta"]),
            _realtime_from(fields["realtime"]),
        )

    @classmethod
    def from_json(cls, document: str | bytes) -> Table:
        """Read a table back from its canonical JSON."""
        return cls.from_dict(f.load_json(document))

    def to_pandas(self) -> pd.DataFrame:
        """Return a pandas frame of ``Float64`` columns, missing values as ``NA``.

        The index is laid out as :meth:`Series.to_pandas` lays it out, and
        ``attrs["pyeconomics"]`` holds the table's and the columns' metadata.
        """
        frame = pd.DataFrame(
            {
                column.name: pd.array(list(values), dtype="Float64")
                for column, values in zip(self.columns, self.data, strict=True)
            },
            index=_pandas_index(self.index, self.realtime),
        )
        frame.attrs[PANDAS_ATTRS_KEY] = {
            "type": "table",
            "meta": self.meta.to_dict(),
            "columns": [column.to_dict() for column in self.columns],
        }
        return frame

    @classmethod
    def from_pandas(
        cls,
        frame: pd.DataFrame,
        meta: TableMeta | None = None,
        columns: Sequence[ColumnMeta] | None = None,
    ) -> Table:
        """Build a table from pandas, reading the metadata from its ``attrs``.

        Parameters
        ----------
        frame
            A frame laid out as :meth:`to_pandas` lays it out.
        meta, columns
            The table's and the columns' metadata, when ``frame.attrs`` does
            not hold them. The columns' names must match the frame's, in order.

        """
        if meta is None or columns is None:
            attrs = _attrs(frame, "table")
            if meta is None:
                meta = TableMeta.from_dict(attrs["meta"])
            if columns is None:
                stored = f.sequence(attrs["columns"], "columns", max_items=MAX_COLUMNS)
                columns = [ColumnMeta.from_dict(column) for column in stored]
        names = [column.name for column in columns]
        if [str(name) for name in frame.columns] != names:
            msg = f"the frame's columns {list(frame.columns)} are not {names}"
            raise f.fail(msg)
        index, realtime = _from_pandas_index(frame.index)
        data = tuple(
            _values(_pandas_values(frame.iloc[:, position]), len(index), repr(name))
            for position, name in enumerate(names)
        )
        return cls(index, tuple(columns), data, meta, realtime)


_TABLE_KEYS: Final = (
    "schema_version",
    "type",
    "meta",
    "columns",
    "index",
    "data",
    "realtime",
)
