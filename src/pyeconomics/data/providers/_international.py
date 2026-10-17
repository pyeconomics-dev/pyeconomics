# src/pyeconomics/data/providers/_international.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Pure helpers for the international providers: periods, units and tables."""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LlmUse
from pyeconomics.data.errors import DataError, ResponseError
from pyeconomics.data.providers._shared import month_end
from pyeconomics.data.terms import CachePolicy
from pyeconomics.data.types import (
    ColumnMeta,
    ObservationFrequency,
    Series,
    Table,
    TableMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query


def period(value: str, provider: str) -> tuple[dt.date, ObservationFrequency]:
    """Read an annual, quarterly, monthly or ISO daily period at its end."""
    if re.fullmatch(r"\d{4}", value):
        return dt.date(int(value), 12, 31), ObservationFrequency.ANNUAL
    match = re.fullmatch(r"(\d{4})-?Q([1-4])", value)
    if match:
        return month_end(
            int(match[1]), int(match[2]) * 3
        ), ObservationFrequency.QUARTERLY
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if match:
        return month_end(int(match[1]), int(match[2])), ObservationFrequency.MONTHLY
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return dt.date.fromisoformat(value), ObservationFrequency.DAILY
    msg = "source sent an unsupported observation period"
    raise ResponseError(msg, provider=provider)


def unit(text: str, *, multiplier: int = 0) -> tuple[UnitRecord, bool]:
    """Recognize explicitly published percent units; never infer from values."""
    plain = text.casefold().replace("per cent", "percent")
    percent = (
        plain
        in {"pc", "pcpa", "pa", "pc_ann", "pc_yoy", "pc_chg", "percent", "%", "pct"}
        or "percent" in plain
        or "%" in plain
    )
    if percent:
        return UnitRecord(text=text, kind=UnitKind.RATE), True
    if "index" in plain:
        return UnitRecord(
            text=text, kind=UnitKind.INDEX_LEVEL, scale=10.0**multiplier
        ), False
    if (
        plain in {"usd", "us dollar", "us dollars"}
        or "us$" in plain
        or "us dollars" in plain
    ):
        return UnitRecord(
            text=text, kind=UnitKind.MONEY, currency="USD", scale=10.0**multiplier
        ), False
    return UnitRecord(
        text=text or "Not specified by source", scale=10.0**multiplier
    ), False


def combine(frames: Sequence[Series], query: Query) -> Series | Table:
    """Align series explicitly into a table without filling missing values."""
    if len(frames) == 1:
        return frames[0]
    first = frames[0].meta
    if any(f.meta.frequency != first.frequency for f in frames):
        msg = "fetch different frequencies separately"
        raise DataError(msg, provider=first.provider)
    terms = first.terms
    restricted = next(
        (f.meta.terms for f in frames if f.meta.terms.licence.value != "hosted-safe"),
        None,
    )
    if restricted is not None:
        terms = restricted
    if any(frame.meta.terms.llm_use.value == "forbidden" for frame in frames):
        terms = replace(terms, llm_use=LlmUse.FORBIDDEN)
    elif any(frame.meta.terms.llm_use.value == "unclear" for frame in frames):
        terms = replace(terms, llm_use=LlmUse.UNCLEAR)
    if any(frame.meta.terms.cache.value == "forbidden" for frame in frames):
        terms = replace(terms, cache=CachePolicy.FORBIDDEN)
    days = tuple(sorted({day for frame in frames for day in frame.index}))[
        -query.max_observations :
    ]
    columns = []
    data = []
    for i, frame in enumerate(frames):
        columns.append(
            ColumnMeta(
                name=f"series_{i + 1}",
                series_id=frame.meta.series_id,
                title=frame.meta.title,
                unit=frame.meta.unit,
                seasonal_adjustment=frame.meta.seasonal_adjustment,
            )
        )
        lookup = dict(zip(frame.index, frame.values, strict=True))
        data.append(tuple(lookup.get(day) for day in days))
    meta = TableMeta(
        provider=first.provider,
        table_id="selection",
        dataset=first.dataset,
        title=first.title,
        frequency=first.frequency,
        source_dating=first.source_dating,
        terms=terms,
        retrieved_at=first.retrieved_at,
        notes=(
            "revised_data",
            "alignment: union of observation dates; gaps remain missing",
        ),
    )
    return Table(days, tuple(columns), tuple(data), meta)


def window(frame: Series, query: Query) -> Series:
    """Keep requested observation dates and the most recent size-bounded tail."""
    rows = [
        (d, v)
        for d, v in zip(frame.index, frame.values, strict=True)
        if (query.start is None or d >= query.start)
        and (query.end is None or d <= query.end)
    ]
    rows = rows[-query.max_observations :]
    return replace(
        frame, index=tuple(d for d, _ in rows), values=tuple(v for _, v in rows)
    )
