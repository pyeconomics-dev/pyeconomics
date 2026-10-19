# src/pyeconomics/data/catalog/transforms.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The transforms a concept and a binding apply to a series (ADR-0011 decision 15).

Each transform is a pure function of one series (or two) that returns a new
:class:`~pyeconomics.data.types.Series`, with its unit, frequency and notes
updated and its terms kept. The names and parameter schemas are declared in
:mod:`pyeconomics.core.transforms`; a test holds the two sets equal.
:func:`apply` runs a transform written as text (``yoy``,
``convert(to=quarterly,method=mean)``), and the resolver records that text in
the ``DataSource`` it returns.

The rules every transform keeps:

- **Never fill.** A value that cannot be computed from the observations that
  exist is ``None``, never an earlier value carried forward, an interpolation
  or a partial average. Going to a higher frequency puts each value on its own
  period's last day and leaves the other periods missing.
- **Never invent a date.** A result is indexed by dates its inputs imply: its
  own dates, the period ends of the frequency it converts to, or the dates it
  is aligned to.
- **Say what it cannot do.** A transform that cannot be applied, such as a
  year-over-year change of a daily series, a logarithm of a non-positive value
  or an alignment with no observation to read, raises
  :class:`~pyeconomics.data.errors.DataError` naming the reason.
- **Several vintages per date refuse.** A transform reads one value per date;
  select a vintage first (:meth:`pyeconomics.data.Vintage.select`). The result
  of a transform of a vintage-selected series keeps each date's own real-time
  period.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.data import (
...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
... )
>>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://example.org",
...     checked=dt.date(2026, 10, 15), attribution="Source: Example.",
...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
>>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.QUARTERLY,
...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
...     source_dating=DateConvention.PERIOD_END, terms=terms)
>>> days = tuple(dt.date(2025 + (q - 1) // 4, 3 * ((q - 1) % 4 + 1), d)
...              for q, d in zip(range(1, 6), (31, 30, 30, 31, 31)))
>>> series = Series(days, (100.0, 101.0, 102.0, 103.0, 104.0), meta)
>>> [round(v, 4) if v is not None else None for v in apply("yoy", series).values]
[None, None, None, None, 0.04]
>>> apply("convert(to=annual,method=last)", series).values
(103.0,)
"""

from __future__ import annotations

import calendar
import datetime as dt
import itertools
import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse, RealtimePeriod
from pyeconomics.core.transforms import ParsedTransform, parse_transform
from pyeconomics.data.errors import DataError
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    Series,
    SeriesMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping, Sequence

__all__ = [
    "IMPLEMENTATIONS",
    "add",
    "align_to",
    "apply",
    "asof",
    "changes_only",
    "convert",
    "diff",
    "lag",
    "log",
    "merge_terms",
    "pct_change",
    "period",
    "ratio",
    "window",
    "yoy",
]

_MONTHS_PER_PERIOD: Final = {
    ObservationFrequency.MONTHLY: 1,
    ObservationFrequency.QUARTERLY: 3,
    ObservationFrequency.SEMIANNUAL: 6,
    ObservationFrequency.ANNUAL: 12,
}
_TARGETS: Final = {
    "monthly": ObservationFrequency.MONTHLY,
    "quarterly": ObservationFrequency.QUARTERLY,
    "semiannual": ObservationFrequency.SEMIANNUAL,
    "annual": ObservationFrequency.ANNUAL,
}
_SPAN_DAYS: Final = {
    ObservationFrequency.DAILY: 1,
    ObservationFrequency.BUSINESS_DAILY: 1,
    ObservationFrequency.IRREGULAR: 1,
    ObservationFrequency.WEEKLY: 7,
    ObservationFrequency.BIWEEKLY: 14,
}
_DAYS_IN_WEEK: Final = 7
_LICENCE_RANK: Final = {
    LicenceClass.HOSTED_SAFE: 0,
    LicenceClass.USER_SUPPLIED: 1,
    LicenceClass.BYOK: 2,
    LicenceClass.PREMIUM_LOCAL: 3,
    LicenceClass.LIBRARY_ONLY: 4,
}
_LLM_RANK: Final = {LlmUse.ALLOWED: 0, LlmUse.UNCLEAR: 1, LlmUse.FORBIDDEN: 2}
_MAX_TEXT: Final = 1_000


# --- shared helpers -------------------------------------------------------------


def _fail(series: Series, message: str) -> DataError:
    return DataError(message, provider=series.meta.provider)


def _single(series: Series, what: str) -> None:
    """Refuse a series with several real-time rows for one date."""
    if len(set(series.index)) != len(series.index):
        msg = (
            f"{what} needs one value per date, but {series.meta.series_id} holds "
            "several vintages; select a vintage first"
        )
        raise _fail(series, msg)


def _month_count(day: dt.date) -> int:
    """Return a month's number on a line: ``year * 12 + month``."""
    return day.year * 12 + day.month


def _month_end(count: int) -> dt.date:
    year, month = divmod(count - 1, 12)
    return dt.date(year, month + 1, calendar.monthrange(year, month + 1)[1])


def _step(meta: SeriesMeta) -> int | None:
    """Months in one period, for a month-based frequency."""
    return _MONTHS_PER_PERIOD.get(meta.frequency)


def _ordinal(day: dt.date, meta: SeriesMeta) -> int | None:
    """Return a date's period number on a line, or ``None`` for a positional series.

    Month-based periods count in ``step`` months from the year-end month; weekly
    and biweekly periods count in weeks. Consecutive periods differ by one (by
    two for a biweekly series).
    """
    step = _step(meta)
    if step is not None:
        return (_month_count(day) - meta.year_ends_in) // step
    if meta.frequency in {ObservationFrequency.WEEKLY, ObservationFrequency.BIWEEKLY}:
        return day.toordinal() // _DAYS_IN_WEEK
    return None


def _stride(meta: SeriesMeta) -> int:
    """How far apart consecutive periods lie on the :func:`_ordinal` line."""
    return 2 if meta.frequency is ObservationFrequency.BIWEEKLY else 1


def _number(day: dt.date, meta: SeriesMeta) -> int:
    """Return a date's period number, for a series whose periods are numbered."""
    number = _ordinal(day, meta)
    if number is None:  # pragma: no cover - callers check first
        msg = f"{meta.series_id} has no period numbers"
        raise DataError(msg, provider=meta.provider)
    return number


def _back_rows(series: Series, count: int) -> list[int | None]:
    """Return the row ``count`` periods (or observations) before each date's row."""
    meta = series.meta
    size = len(series.index)
    if not series.index or _ordinal(series.index[0], meta) is None:
        return [row - count if row >= count else None for row in range(size)]
    rows = {_number(day, meta): row for row, day in enumerate(series.index)}
    stride = _stride(meta)
    return [rows.get(_number(day, meta) - count * stride) for day in series.index]


def _back(series: Series, count: int) -> list[float | None]:
    """Return the value ``count`` periods (or observations) before each date."""
    return [
        None if row is None else series.values[row] for row in _back_rows(series, count)
    ]


def _with_note(notes: tuple[str, ...], note: str) -> tuple[str, ...]:
    return notes if note in notes else (*notes, note)


def _derived(  # noqa: PLR0913 - the result's values, labels and dates are separate
    series: Series,
    values: Sequence[float | None],
    *,
    unit: UnitRecord,
    title: str,
    transform: str,
    index: Sequence[dt.date] | None = None,
    realtime: Sequence[RealtimePeriod] | None = None,
    **changes: object,
) -> Series:
    """Build the result series: new values, same terms, a note naming the transform."""
    meta = replace(
        series.meta,
        title=title[:256],
        unit=unit,
        notes=_with_note(series.meta.notes, f"transformed: {transform}"),
        **changes,  # type: ignore[arg-type]
    )
    use_realtime = series.realtime if realtime is None else tuple(realtime)
    return Series(
        tuple(series.index if index is None else index),
        tuple(values),
        meta,
        use_realtime,
    )


def _describe_unit(unit: UnitRecord, prefix: str) -> str:
    return f"{prefix} {unit.text}"[:256]


def merge_terms(first: Terms, second: Terms) -> Terms:
    """Return the terms a series derived from two sources carries.

    The strictest of each: the least permissive licence class (and its terms
    page), no storage if either forbids it, no language model if either
    forbids it, and both attributions and notices.

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import CachePolicy, LicenceClass, LlmUse, Terms
    >>> a = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://a.example",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: A.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> b = Terms(licence=LicenceClass.LIBRARY_ONLY, terms_url="https://b.example",
    ...     checked=dt.date(2026, 9, 1), attribution="Source: B.",
    ...     llm_use=LlmUse.FORBIDDEN, cache=CachePolicy.FORBIDDEN)
    >>> merged = merge_terms(a, b)
    >>> merged.licence.value, merged.cache.value, merged.checked.isoformat()
    ('library-only', 'forbidden', '2026-09-01')
    >>> merged.attribution
    'Source: A. Source: B.'
    """
    stricter = (
        second
        if _LICENCE_RANK[second.licence] > _LICENCE_RANK[first.licence]
        else first
    )
    attribution = first.attribution
    if second.attribution != first.attribution:
        attribution = f"{first.attribution} {second.attribution}"
    notices = [n for n in (first.notice, second.notice) if n]
    notice = None if not notices else " ".join(dict.fromkeys(notices))
    llm = max((first.llm_use, second.llm_use), key=lambda use: _LLM_RANK[use])
    cache = (
        CachePolicy.FORBIDDEN
        if CachePolicy.FORBIDDEN in {first.cache, second.cache}
        else CachePolicy.ALLOWED
    )
    return Terms(
        licence=stricter.licence,
        terms_url=stricter.terms_url,
        checked=min(first.checked, second.checked),
        attribution=attribution[:_MAX_TEXT],
        notice=None if notice is None else notice[:_MAX_TEXT],
        llm_use=llm,
        cache=cache,
    )


# --- change transforms ----------------------------------------------------------


def pct_change(series: Series, periods: int = 1) -> Series:
    """Return the fractional change from the observation ``periods`` back.

    Month-based, weekly and biweekly series count ``periods`` whole periods back
    by date, so a gap in the dates gives a missing value rather than a wrong
    comparison; daily, business-daily and irregular series count observations. A
    base that is not positive gives a missing value.

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import (
    ...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
    ...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
    ... )
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://x.example",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: X.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
    ...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.MONTHLY,
    ...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
    ...     source_dating=DateConvention.PERIOD_END, terms=terms)
    >>> months = (dt.date(2025, 1, 31), dt.date(2025, 2, 28), dt.date(2025, 3, 31))
    >>> pct_change(Series(months, (100.0, 110.0, 99.0), meta)).values
    (None, 0.10000000000000009, -0.09999999999999998)
    """
    _single(series, "pct_change")
    base = _back(series, periods)
    values = [
        None if value is None or prior is None or prior <= 0 else value / prior - 1
        for value, prior in zip(series.values, base, strict=True)
    ]
    return _derived(
        series,
        values,
        unit=UnitRecord(text="Fractional change", kind=UnitKind.RETURN),
        title=f"Change in {series.meta.title}",
        transform="pct_change" if periods == 1 else f"pct_change(periods={periods})",
    )


def yoy(series: Series) -> Series:
    """Return the fractional change from the same period one year earlier.

    Only month-based frequencies have a same period a year earlier. A date whose
    year-earlier observation is absent or missing gives a missing value. The
    result is a rate: the decimal change over a year.

    Raises
    ------
    DataError
        For a daily, weekly or irregular series.
    """
    _single(series, "yoy")
    step = _step(series.meta)
    if step is None:
        msg = (
            f"yoy needs a monthly, quarterly, semiannual or annual series, but "
            f"{series.meta.series_id} is {series.meta.frequency.value}"
        )
        raise _fail(series, msg)
    base = _back(series, 12 // step)
    values = [
        None if value is None or prior is None or prior <= 0 else value / prior - 1
        for value, prior in zip(series.values, base, strict=True)
    ]
    return _derived(
        series,
        values,
        unit=UnitRecord(text="Year-over-year change", kind=UnitKind.RATE),
        title=f"Year-over-year change in {series.meta.title}",
        transform="yoy",
    )


def diff(series: Series, periods: int = 1) -> Series:
    """Return the difference from the observation ``periods`` back, in its unit."""
    _single(series, "diff")
    base = _back(series, periods)
    values = [
        None if value is None or prior is None else value - prior
        for value, prior in zip(series.values, base, strict=True)
    ]
    unit = series.meta.unit
    return _derived(
        series,
        values,
        unit=replace(unit, text=_describe_unit(unit, "Change in")),
        title=f"Change in {series.meta.title}",
        transform="diff" if periods == 1 else f"diff(periods={periods})",
    )


def lag(series: Series, periods: int = 1) -> Series:
    """Return, on each date, the value of the observation ``periods`` back.

    The periods are counted as :func:`diff` counts them, so ``lag(periods=12)``
    of a monthly series is the value a year earlier and a date whose earlier
    observation is absent or missing is missing. Each value keeps the real-time
    period of the observation it was read from.

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import (
    ...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
    ...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
    ... )
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://x.example",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: X.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
    ...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.MONTHLY,
    ...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
    ...     source_dating=DateConvention.PERIOD_END, terms=terms)
    >>> months = (dt.date(2025, 1, 31), dt.date(2025, 2, 28), dt.date(2025, 3, 31))
    >>> lag(Series(months, (1.0, 2.0, 3.0), meta)).values
    (None, 1.0, 2.0)
    """
    _single(series, "lag")
    sources = _back_rows(series, periods)
    values = [None if source is None else series.values[source] for source in sources]
    realtime = None
    if series.realtime is not None:
        realtime = tuple(
            series.realtime[row if source is None else source]
            for row, source in enumerate(sources)
        )
    title = f"{series.meta.title}, {periods} period{'s' if periods > 1 else ''} earlier"
    return _derived(
        series,
        values,
        unit=series.meta.unit,
        title=title,
        transform="lag" if periods == 1 else f"lag(periods={periods})",
        realtime=realtime,
    )


def log(series: Series) -> Series:
    """Return the natural logarithm of each value.

    Raises
    ------
    DataError
        If a value is zero or negative: the logarithm is undefined there, and
        nothing replaces it.
    """
    _single(series, "log")
    values: list[float | None] = []
    for day, value in zip(series.index, series.values, strict=True):
        if value is None:
            values.append(None)
        elif value <= 0:
            msg = f"log is undefined for {value} on {day} in {series.meta.series_id}"
            raise _fail(series, msg)
        else:
            values.append(math.log(value))
    return _derived(
        series,
        values,
        unit=UnitRecord(text=_describe_unit(series.meta.unit, "Natural log of")),
        title=f"Natural log of {series.meta.title}",
        transform="log",
    )


def changes_only(series: Series) -> Series:
    """Keep the first observation and each date whose value differs from the last.

    A daily step series, such as a target rate in force each day, becomes the
    dates on which it changed. A missing value is skipped, not a change. The
    result is irregular.
    """
    _single(series, "changes_only")
    keep: list[int] = []
    previous: float | None = None
    for row, value in enumerate(series.values):
        if value is None:
            continue
        if previous is None or value != previous:
            keep.append(row)
        previous = value
    realtime = (
        None if series.realtime is None else [series.realtime[row] for row in keep]
    )
    return _derived(
        series,
        [series.values[row] for row in keep],
        unit=series.meta.unit,
        title=f"{series.meta.title} (changes)",
        transform="changes_only",
        index=[series.index[row] for row in keep],
        realtime=realtime,
        frequency=ObservationFrequency.IRREGULAR,
        week_ends_on=None,
        year_ends_in=12,
    )


def _common(first: Series, second: Series, what: str) -> list[tuple[int, int]]:
    """Return the row pairs of the dates two series share.

    Raises
    ------
    DataError
        If the frequencies or anchors differ, or the series share no date.
    """
    a, b = first.meta, second.meta
    if (
        a.frequency is not b.frequency
        or a.week_ends_on != b.week_ends_on
        or a.year_ends_in != b.year_ends_in
    ):
        msg = (
            f"{what} needs the same frequency: {a.series_id} is {a.frequency.value} "
            f"and {b.series_id} is {b.frequency.value}; convert one first"
        )
        raise _fail(first, msg)
    rows = {day: row for row, day in enumerate(second.index)}
    pairs = [(row, rows[day]) for row, day in enumerate(first.index) if day in rows]
    if not pairs:
        msg = f"{a.series_id} and {b.series_id} share no date"
        raise _fail(first, msg)
    return pairs


def _combined(  # noqa: PLR0913 - two series, their shared rows and the result's label
    first: Series,
    second: Series,
    pairs: list[tuple[int, int]],
    values: list[float | None],
    *,
    unit: UnitRecord,
    verb: str,
) -> Series:
    """Build the series two sources combine into: the stricter terms, both named."""
    a, b = first.meta, second.meta
    meta = replace(
        a,
        series_id=f"{a.series_id}/{b.series_id}"[:256],
        dataset="derived",
        title=f"{a.title} {verb} {b.title}"[:256],
        unit=unit,
        terms=merge_terms(a.terms, b.terms),
        retrieved_at=_later(a.retrieved_at, b.retrieved_at),
        notes=_with_note(
            a.notes,
            f"derived: {a.provider} {a.series_id} {verb} {b.provider} {b.series_id}"[
                :240
            ],
        ),
    )
    if first.realtime is not None:
        realtime: tuple[RealtimePeriod, ...] | None = tuple(
            first.realtime[row] for row, _ in pairs
        )
    elif second.realtime is not None:
        realtime = tuple(second.realtime[row] for _, row in pairs)
    else:
        realtime = None
    return Series(
        tuple(first.index[row] for row, _ in pairs), tuple(values), meta, realtime
    )


def ratio(first: Series, second: Series, *, excess: bool = False) -> Series:
    """Return ``first / second`` on the dates they share; ``excess`` subtracts one.

    The two series must share their frequency and anchors: a ratio never aligns
    for the caller, it only reads the dates both have. Each value is scaled by
    its unit's power of ten first, so billions over millions is a plain ratio. A
    missing value, or a zero divisor, gives a missing value. The terms are the
    stricter of the two.

    Raises
    ------
    DataError
        If the frequency or anchors differ, or the series share no date.
    """
    _single(first, "ratio")
    _single(second, "ratio")
    pairs = _common(first, second, "a ratio")
    a, b = first.meta, second.meta
    values: list[float | None] = []
    for left, right in pairs:
        x, y = first.values[left], second.values[right]
        if x is None or y is None or y == 0:
            values.append(None)
        else:
            result = (x * a.unit.scale) / (y * b.unit.scale)
            values.append(result - 1 if excess else result)
    return _combined(
        first,
        second,
        pairs,
        values,
        unit=UnitRecord(
            text="Ratio less one" if excess else "Ratio",
            kind=UnitKind.RATE if excess else UnitKind.RATIO,
        ),
        verb="over",
    )


def add(first: Series, second: Series) -> Series:
    """Return ``first + second`` on the dates they share, in the first's unit.

    Raises
    ------
    DataError
        If the frequency, anchors or unit kinds differ, or no date is shared.
    """
    _single(first, "add")
    _single(second, "add")
    a, b = first.meta, second.meta
    if a.unit.kind != b.unit.kind:
        msg = (
            f"add needs one unit kind: {a.series_id} is {a.unit.kind} and "
            f"{b.series_id} is {b.unit.kind}"
        )
        raise _fail(first, msg)
    pairs = _common(first, second, "add")
    values: list[float | None] = []
    for left, right in pairs:
        x, y = first.values[left], second.values[right]
        values.append(
            None
            if x is None or y is None
            else (x * a.unit.scale + y * b.unit.scale) / a.unit.scale
        )
    return _combined(
        first,
        second,
        pairs,
        values,
        unit=a.unit,
        verb="plus",
    )


def _later(first: dt.datetime | None, second: dt.datetime | None) -> dt.datetime | None:
    if first is None or second is None:
        return first or second
    return max(first, second)


# --- frequency conversion -------------------------------------------------------


def _group_number(day: dt.date, step: int, year_ends_in: int) -> int:
    """Return the number of the target period that contains ``day``."""
    return -((year_ends_in - _month_count(day)) // step)


def _group_end(number: int, step: int, year_ends_in: int) -> dt.date:
    return _month_end(number * step + year_ends_in)


def convert(series: Series, to: str, method: str) -> Series:
    """Convert a series to a month-based frequency by an explicit method.

    Aggregating (to a lower frequency) combines the observations of each target
    period: ``mean`` and ``sum`` need the period complete (every month of a
    month-based source, and for a daily or weekly source every observation up
    to the period's end), ``first`` and ``last`` read the period's first or last
    sub-period (month-based source) or observation, and ``period_end`` reads the
    observation dated on the period's last day. A period the series enters or
    leaves part-way is left out, and a period with a gap is missing. Going to a
    higher frequency allows only ``period_end``: each value stays on its own
    period's last day and the periods between are missing.

    Raises
    ------
    DataError
        For several vintages per date, an irregular conversion that is not
        possible, or a higher frequency with any method but ``period_end``.
    """
    _single(series, "convert")
    target = _TARGETS[to]
    meta = series.meta
    target_step = _MONTHS_PER_PERIOD[target]
    source_step = _step(meta)
    if source_step == target_step:
        return series
    if source_step is not None and source_step > target_step:
        return _upsample(series, target, method)
    return _aggregate(series, target, method, source_step)


def _year_end(meta: SeriesMeta, target: ObservationFrequency) -> int:
    return meta.year_ends_in if target.needs_year_end else 12


def _upsample(series: Series, target: ObservationFrequency, method: str) -> Series:
    meta = series.meta
    if method != "period_end":
        msg = (
            f"{meta.series_id} is {meta.frequency.value}, so converting to "
            f"{target.value} by {method} would invent values; only period_end "
            "places each value on its own date and leaves the rest missing"
        )
        raise _fail(series, msg)
    year_end = _year_end(meta, target)
    step = _MONTHS_PER_PERIOD[target]
    # A coarser frequency's period ends are always finer ones' (a fiscal year end
    # carries over), so this guards a hand-built series that breaks the rule.
    if any(
        (_month_count(day) - year_end) % step for day in series.index
    ):  # pragma: no cover
        msg = f"{meta.series_id}'s dates are not {target.value} period ends"
        raise _fail(series, msg)
    first, last = _month_count(series.index[0]), _month_count(series.index[-1])
    at = {_month_count(day): row for row, day in enumerate(series.index)}
    index: list[dt.date] = []
    values: list[float | None] = []
    realtime: list[RealtimePeriod] = []
    latest = 0
    for count in range(first, last + 1, step):
        row = at.get(count)
        if row is not None:
            latest = row
        index.append(_month_end(count))
        values.append(None if row is None else series.values[row])
        if series.realtime is not None:
            # A period with no source value is missing; it carries the real-time
            # period of the observation before it, which only labels a gap.
            realtime.append(series.realtime[latest])
    return _derived(
        series,
        values,
        unit=series.meta.unit,
        title=series.meta.title,
        transform=f"convert(to={target.value},method=period_end)",
        index=index,
        realtime=realtime if series.realtime is not None else None,
        frequency=target,
        week_ends_on=None,
        year_ends_in=year_end,
    )


@dataclass(frozen=True, slots=True)
class _Grid:
    """How a series' dates fall onto the periods of the frequency it converts to."""

    target_step: int
    """Months in one target period."""
    year_end: int
    """The month the target year ends in."""
    source_step: int | None
    """Months in one source period; ``None`` for a daily, weekly or irregular source."""

    def number(self, day: dt.date) -> int:
        """Return the number of the target period that contains ``day``."""
        return _group_number(day, self.target_step, self.year_end)

    def end(self, number: int) -> dt.date:
        """Return the last day of target period ``number``."""
        return _group_end(number, self.target_step, self.year_end)


def _aggregate(
    series: Series,
    target: ObservationFrequency,
    method: str,
    source_step: int | None,
) -> Series:
    meta = series.meta
    year_end = _year_end(meta, target) if source_step is not None else 12
    grid = _Grid(_MONTHS_PER_PERIOD[target], year_end, source_step)
    groups: dict[int, list[int]] = {}
    for row, day in enumerate(series.index):
        groups.setdefault(grid.number(day), []).append(row)
    kept = [n for n in sorted(groups) if _is_whole(series, groups[n], n, grid)]
    if not kept:
        msg = f"{meta.series_id} holds no complete {target.value} period"
        raise _fail(series, msg)
    index: list[dt.date] = []
    values: list[float | None] = []
    realtime: list[RealtimePeriod] = []
    latest = None if series.realtime is None else series.realtime[0]
    for number in range(kept[0], kept[-1] + 1):
        end = grid.end(number)
        value, stamp = _combine(series, groups.get(number, []), end, method, grid)
        index.append(end)
        values.append(value)
        if series.realtime is not None:
            # A missing period carries the last known real-time period, which
            # only labels the gap.
            latest = stamp or latest
            if latest is not None:
                realtime.append(latest)
    return _derived(
        series,
        values,
        unit=series.meta.unit,
        title=series.meta.title,
        transform=f"convert(to={target.value},method={method})",
        index=index,
        realtime=realtime if series.realtime is not None else None,
        frequency=target,
        week_ends_on=None,
        year_ends_in=year_end,
    )


def _is_whole(series: Series, rows: list[int], number: int, grid: _Grid) -> bool:
    """Check that the series covers the target period at both of its ends.

    A period it enters or leaves part-way is left out; a gap inside is not a
    reason to leave it out (it becomes a missing value).
    """
    end = grid.end(number)
    first_row, last_row = rows[0], rows[-1]
    first_day, last_day = series.index[first_row], series.index[last_row]
    before, after = first_row > 0, last_row < len(series.index) - 1
    if grid.source_step is not None:
        start_count = _month_count(end) - grid.target_step + grid.source_step
        starts = _month_count(first_day) == start_count
        ends = _month_count(last_day) == _month_count(end)
        return (starts or before) and (ends or after)
    span = _SPAN_DAYS[series.meta.frequency]
    tolerance = dt.timedelta(days=max(span - 1, _DAYS_IN_WEEK - 1))
    starts = first_day <= grid.end(number - 1) + dt.timedelta(days=1) + tolerance
    ends = last_day >= end - tolerance
    return (starts or before) and (ends or after)


def _combine(
    series: Series, rows: list[int], end: dt.date, method: str, grid: _Grid
) -> tuple[float | None, RealtimePeriod | None]:
    """Combine one target period's observations by ``method``.

    Returns the value and the real-time period of the observation it rests on.
    """
    if method == "period_end":
        match = next((row for row in rows if series.index[row] == end), None)
        return _read(series, match)
    if grid.source_step is None:
        return _combine_dense(series, rows, method)
    expected = grid.target_step // grid.source_step
    if method in {"mean", "sum"}:
        present = [row for row in rows if series.values[row] is not None]
        if len(present) != expected or len(rows) != expected:
            return None, None
        total = _total(series, rows)
        stamp = _read(series, rows[-1])[1]
        return (total / expected if method == "mean" else total), stamp
    return _read(series, _edge_row(series, rows, method, end, grid))


def _total(series: Series, rows: list[int]) -> float:
    """Sum the values of the given rows, which hold values (a missing one adds 0)."""
    total = 0.0
    for row in rows:
        value = series.values[row]
        if value is not None:
            total += value
    return total


def _read(
    series: Series, row: int | None
) -> tuple[float | None, RealtimePeriod | None]:
    """Return a row's value and real-time period; a missing row gives ``None``."""
    if row is None or series.values[row] is None:
        return None, None
    stamp = None if series.realtime is None else series.realtime[row]
    return series.values[row], stamp


def _combine_dense(
    series: Series, rows: list[int], method: str
) -> tuple[float | None, RealtimePeriod | None]:
    """Combine the observations of a daily, weekly or irregular source's period."""
    present = [row for row in rows if series.values[row] is not None]
    if not present:
        return None, None
    if method in {"mean", "sum"}:
        total = _total(series, present)
        stamp = _read(series, present[-1])[1]
        return (total / len(present) if method == "mean" else total), stamp
    return _read(series, present[0] if method == "first" else present[-1])


def _edge_row(
    series: Series, rows: list[int], method: str, end: dt.date, grid: _Grid
) -> int | None:
    """Find the row of a period's first or last sub-period, if it has a value."""
    if grid.source_step is None:  # pragma: no cover - callers check first
        return None
    last = _month_count(end)
    wanted = last if method == "last" else last - grid.target_step + grid.source_step
    for row in rows:
        if _month_count(series.index[row]) == wanted:
            return row if series.values[row] is not None else None
    return None


# --- alignment ------------------------------------------------------------------


def _non_missing(series: Series) -> list[int]:
    return [row for row, value in enumerate(series.values) if value is not None]


def _pick(series: Series, rows: Sequence[int], title: str, transform: str) -> Series:
    return _derived(
        series,
        [series.values[row] for row in rows],
        unit=series.meta.unit,
        title=title,
        transform=transform,
        index=[series.index[row] for row in rows],
        realtime=None
        if series.realtime is None
        else [series.realtime[row] for row in rows],
    )


def asof(series: Series, date: dt.date, max_age_days: int | None = None) -> Series:
    """Return the last non-missing observation on or before ``date``.

    The observation keeps its own date, so a stale value cannot pass for a fresh
    one. ``max_age_days`` bounds how old it may be.

    Raises
    ------
    DataError
        If no observation lies on or before ``date``, or the newest is older than
        ``max_age_days``.
    """
    _single(series, "asof")
    rows = [row for row in _non_missing(series) if series.index[row] <= date]
    if not rows:
        msg = f"{series.meta.series_id} has no observation on or before {date}"
        raise _fail(series, msg)
    row = rows[-1]
    age = (date - series.index[row]).days
    if max_age_days is not None and age > max_age_days:
        msg = (
            f"the last observation of {series.meta.series_id} on or before {date} is "
            f"{series.index[row]}, {age} days old; the limit is {max_age_days}"
        )
        raise _fail(series, msg)
    return _pick(
        series,
        [row],
        series.meta.title,
        f"asof(date={date.isoformat()})"
        if max_age_days is None
        else f"asof(date={date.isoformat()},max_age_days={max_age_days})",
    )


def _period_end_of(series: Series, date: dt.date) -> dt.date | None:
    meta = series.meta
    step = _step(meta)
    if step is not None:
        return _group_end(
            _group_number(date, step, meta.year_ends_in), step, meta.year_ends_in
        )
    if meta.week_ends_on is not None:
        gap = (meta.week_ends_on.number - date.weekday()) % _DAYS_IN_WEEK
        return date + dt.timedelta(days=gap)
    if meta.frequency in {
        ObservationFrequency.DAILY,
        ObservationFrequency.BUSINESS_DAILY,
    }:
        return date
    return None


def period(series: Series, date: dt.date) -> Series:
    """Return the observation of the period that contains ``date``.

    Raises
    ------
    DataError
        For an irregular series (it has no periods), or when the period has no
        observation or its value is missing.
    """
    _single(series, "period")
    end = _period_end_of(series, date)
    if end is None:
        msg = f"{series.meta.series_id} is irregular and has no periods"
        raise _fail(series, msg)
    for row, day in enumerate(series.index):
        if day == end:
            if series.values[row] is None:
                msg = f"{series.meta.series_id} is missing for the period ending {end}"
                raise _fail(series, msg)
            return _pick(
                series, [row], series.meta.title, f"period(date={date.isoformat()})"
            )
    msg = f"{series.meta.series_id} has no observation for the period ending {end}"
    raise _fail(series, msg)


def window(series: Series, count: int, date: dt.date) -> Series:
    """Return the last ``count`` observations on or before ``date``.

    Raises
    ------
    DataError
        If fewer than ``count`` exist, one is missing, or (for a regular series)
        they are not consecutive periods.
    """
    _single(series, "window")
    rows = [row for row, day in enumerate(series.index) if day <= date]
    chosen = rows[-count:]
    if len(chosen) < count:
        msg = (
            f"{series.meta.series_id} has {len(chosen)} observations on or before "
            f"{date}, fewer than the {count} asked for"
        )
        raise _fail(series, msg)
    if any(series.values[row] is None for row in chosen):
        msg = (
            f"{series.meta.series_id} is missing a value in the last {count} "
            "observations"
        )
        raise _fail(series, msg)
    numbers = [_ordinal(series.index[row], series.meta) for row in chosen]
    stride = _stride(series.meta)
    steps = [
        later - earlier
        for earlier, later in itertools.pairwise(n for n in numbers if n is not None)
    ]
    if len(steps) == len(numbers) - 1 and any(step != stride for step in steps):
        msg = (
            f"the last {count} observations of {series.meta.series_id} on or before "
            f"{date} are not consecutive periods"
        )
        raise _fail(series, msg)
    return _pick(
        series,
        chosen,
        series.meta.title,
        f"window(count={count},date={date.isoformat()})",
    )


def align_to(series: Series, target: Series, max_age_days: int | None = None) -> Series:
    """Read ``series`` on ``target``'s dates: the last observation on or before each.

    The result has ``target``'s dates and frequency and ``series``' values, unit
    and terms. This is the explicit rule that replaces a silent forward fill: the
    caller names the target dates, and ``max_age_days`` bounds the staleness.

    Raises
    ------
    DataError
        If a target date has no observation on or before it (or none within
        ``max_age_days``).
    """
    _single(series, "align_to")
    _single(target, "align_to")
    rows = _non_missing(series)
    found: list[int] = []
    for day in target.index:
        usable = [row for row in rows if series.index[row] <= day]
        if not usable:
            msg = f"{series.meta.series_id} has no observation on or before {day}"
            raise _fail(series, msg)
        row = usable[-1]
        age = (day - series.index[row]).days
        if max_age_days is not None and age > max_age_days:
            msg = (
                f"the last observation of {series.meta.series_id} on or before {day} "
                f"is {age} days old; the limit is {max_age_days}"
            )
            raise _fail(series, msg)
        found.append(row)
    text = (
        "align_to" if max_age_days is None else f"align_to(max_age_days={max_age_days})"
    )
    return _derived(
        series,
        [series.values[row] for row in found],
        unit=series.meta.unit,
        title=series.meta.title,
        transform=text,
        index=target.index,
        realtime=None
        if series.realtime is None
        else [series.realtime[row] for row in found],
        frequency=target.meta.frequency,
        week_ends_on=target.meta.week_ends_on,
        year_ends_in=target.meta.year_ends_in,
        source_dating=DateConvention.PERIOD_END,
    )


# --- dispatch -------------------------------------------------------------------

#: The implementation of every transform, by name: a test holds the names equal
#: to :data:`pyeconomics.core.transforms.TRANSFORMS`.
IMPLEMENTATIONS: Final[Mapping[str, Callable[..., Series]]] = {
    "pct_change": pct_change,
    "yoy": yoy,
    "diff": diff,
    "lag": lag,
    "log": log,
    "changes_only": changes_only,
    "ratio": ratio,
    "add": add,
    "convert": convert,
    "align_to": align_to,
    "asof": asof,
    "period": period,
    "window": window,
}


def _arguments(parsed: ParsedTransform) -> dict[str, object]:
    arguments: dict[str, object] = dict(parsed.arguments)
    if "date" in arguments:
        arguments["date"] = dt.date.fromisoformat(str(arguments["date"]))
    return arguments


def apply(transform: str, *operands: Series) -> Series:
    """Apply a transform written as text to its operand series.

    Parameters
    ----------
    transform
        ``name`` or ``name(key=value,...)``, checked against
        :data:`pyeconomics.core.transforms.TRANSFORMS`.
    operands
        One series, or two for ``ratio`` and ``align_to``.

    Raises
    ------
    InputError
        If the text is not a transform or the operand count is wrong.
    DataError
        If the transform cannot be applied to the data.
    """
    parsed = parse_transform(transform)
    if len(operands) != parsed.spec.operands:
        msg = f"{parsed.name} reads {parsed.spec.operands} series, not {len(operands)}"
        raise DataError(msg)
    return IMPLEMENTATIONS[parsed.name](*operands, **_arguments(parsed))
