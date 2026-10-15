# src/pyeconomics/core/provenance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Data provenance: what a result records about the data it read (ADR-0011).

Models never import the data layer, and neither does any other part of core,
so the vocabulary a manifest needs to describe a run's data lives here and
:mod:`pyeconomics.data` re-exports it (ADR-0011 decision 1):

- :class:`LicenceClass`: ADR-0005's five licence classes (decision 7);
- :class:`LlmUse`: whether a source's terms let its data reach a language
  model (decision 8);
- :class:`RealtimePeriod`: the real-time period over which an observation was
  the published value, with ALFRED's semantics (decision 6);
- :class:`DataSource`: one source a result read, its vintage, window,
  transforms, retrieval time, licence and attribution (decision 16).

None of these can hold a credential, a request URL, a host or a path. The one
URL a record carries is its source's public terms page, which must be
``https`` with no user information, port, query or fragment, and every other
text refuses ``://``.

``pyeconomics.core`` also exports :func:`pyeconomics.core.random.provenance`
under the name ``provenance``, which hides this module's name there, as the
``model`` decorator hides :mod:`pyeconomics.core.model`. Import from this
module by its path, or import the names from ``pyeconomics.core``.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.core.provenance import LicenceClass, RealtimePeriod
>>> RealtimePeriod(dt.date(2008, 1, 30), dt.date(2008, 2, 28)).covers(
...     dt.date(2008, 2, 1)
... )
True
>>> LicenceClass.LIBRARY_ONLY.hosted_allowed
False

"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.units import DateBounds

__all__ = [
    "CONCEPT_ID_PATTERN",
    "DATA_DATE_BOUNDS",
    "MAX_FALLBACK_CHAIN",
    "MAX_TRANSFORMS",
    "MAX_WARNINGS",
    "VINTAGE_LABEL_PATTERN",
    "DataSource",
    "LicenceClass",
    "LlmUse",
    "RealtimePeriod",
]

#: Observation and real-time dates the data layer accepts (ADR-0011 decision
#: 3). Wider than a model field's 1900 floor (ADR-0008 decision 3), because
#: long-run series start earlier: Shiller's in 1871, and ALFRED's real-time
#: origin is 1776-07-04.
DATA_DATE_BOUNDS: Final = DateBounds(dt.date(1700, 1, 1), dt.date(2200, 12, 31))

#: A concept id: dotted snake_case of three or four parts, such as
#: ``us.inflation.pce_core.yoy`` or ``factors.ff5.us.monthly`` (decision 15).
CONCEPT_ID_PATTERN: Final = re.compile(
    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*(?:\.[a-z0-9]+(?:_[a-z0-9]+)*){2,3}"
)

#: How a record names the vintage it read: ``latest``, ``first_release``,
#: ``all`` or ``as_of:YYYY-MM-DD`` (decision 6; :class:`pyeconomics.data.Vintage`
#: writes and reads these labels).
VINTAGE_LABEL_PATTERN: Final = re.compile(
    r"latest|first_release|all|as_of:\d{4}-\d{2}-\d{2}"
)

#: The most transforms one record lists.
MAX_TRANSFORMS: Final = 32
#: The most providers one fallback chain lists.
MAX_FALLBACK_CHAIN: Final = 16
#: The most warning codes one record carries.
MAX_WARNINGS: Final = 32


class LicenceClass(StrEnum):
    """Where a source's data may flow (ADR-0005; ADR-0011 decision 7).

    Examples
    --------
    >>> [c.value for c in LicenceClass if c.hosted_allowed]
    ['hosted-safe', 'user-supplied']

    """

    HOSTED_SAFE = "hosted-safe"
    """Terms allow display by a third-party service, with attribution."""
    LIBRARY_ONLY = "library-only"
    """Personal-use, non-commercial, no-caching or scraped terms."""
    BYOK = "byok"
    """The user's own paid subscription."""
    PREMIUM_LOCAL = "premium-local"
    """Licensed to a machine or seat."""
    USER_SUPPLIED = "user-supplied"
    """The user's own files."""

    @property
    def hosted_allowed(self) -> bool:
        """Whether hosted mode may serve the class (ADR-0005 rule 1)."""
        return self in {LicenceClass.HOSTED_SAFE, LicenceClass.USER_SUPPLIED}


class LlmUse(StrEnum):
    """Whether a source's terms let its data reach a language model (decision 8).

    Phase 4's MCP server and AI narrative read it: they withhold ``forbidden``
    data and gate ``unclear`` data.
    """

    ALLOWED = "allowed"
    FORBIDDEN = "forbidden"
    UNCLEAR = "unclear"


@dataclass(frozen=True, slots=True)
class RealtimePeriod:
    """The real-time period over which an observation was the published value.

    The semantics are ALFRED's: a value published on ``realtime_start`` stayed
    current through ``realtime_end``, the day before a revision replaced it.
    ``realtime_end`` is ``None`` while the value is still current (ALFRED writes
    9999-12-31). Both ends are inclusive.

    Examples
    --------
    >>> import datetime as dt
    >>> period = RealtimePeriod(dt.date(2008, 1, 30))
    >>> period.covers(dt.date(2026, 10, 14)), period.to_dict()
    (True, {'realtime_start': '2008-01-30', 'realtime_end': None})

    """

    realtime_start: dt.date
    realtime_end: dt.date | None = None

    def __post_init__(self) -> None:
        """Check both ends lie in :data:`DATA_DATE_BOUNDS`, in order."""
        start = f.day(self.realtime_start, "realtime_start", DATA_DATE_BOUNDS)
        end = f.optional_day(self.realtime_end, "realtime_end", DATA_DATE_BOUNDS)
        if end is not None and end < start:
            msg = f"realtime_end {end} is before realtime_start {start}"
            raise f.fail(msg)

    @property
    def is_current(self) -> bool:
        """Whether the value is still the published one."""
        return self.realtime_end is None

    def covers(self, day: dt.date) -> bool:
        """Return whether the value was the published one on ``day``."""
        return self.realtime_start <= day and (
            self.realtime_end is None or day <= self.realtime_end
        )

    def to_dict(self) -> dict[str, object]:
        """Return the period as JSON-ready values."""
        return {
            "realtime_start": self.realtime_start.isoformat(),
            "realtime_end": None
            if self.realtime_end is None
            else self.realtime_end.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: object) -> RealtimePeriod:
        """Read a period back from :meth:`to_dict`'s form."""
        fields = f.mapping(data, "a real-time period", _REALTIME_KEYS)
        return cls(
            f.parse_day(fields["realtime_start"], "realtime_start"),
            f.parse_optional_day(fields["realtime_end"], "realtime_end"),
        )


_REALTIME_KEYS: Final = ("realtime_start", "realtime_end")


@dataclass(frozen=True, slots=True, kw_only=True)
class DataSource:
    """One source a result read: what, which vintage, and on what terms.

    Phase 3 Step 12 puts these records into manifest schema 2, one per bound
    input field. A record names the data but never the request: it holds no
    URL but the terms page, no host, no path and no credential, so it can
    travel with exports and shared files.

    Examples
    --------
    >>> import datetime as dt
    >>> source = DataSource(
    ...     provider="treasury",
    ...     series_id="par_yield_curve",
    ...     licence=LicenceClass.HOSTED_SAFE,
    ...     attribution="Source: US Department of the Treasury.",
    ...     terms_url="https://home.treasury.gov/",
    ...     llm_use=LlmUse.ALLOWED,
    ...     observation_start=dt.date(2026, 1, 2),
    ...     observation_end=dt.date(2026, 10, 9),
    ... )
    >>> DataSource.from_json(source.canonical_json()) == source
    True

    """

    provider: str
    """The provider's permanent id, such as ``fred``."""
    series_id: str
    """The provider's own id for the series or table."""
    dataset: str | None = None
    """The provider's dataset, release or table family, when it has one."""
    concept: str | None = None
    """The catalog concept the series was resolved for, if any."""
    field: str | None = None
    """The model input field the data filled, when a binding read it."""
    vintage: str | None = None
    """The vintage read, as a label (:data:`VINTAGE_LABEL_PATTERN`), when the
    source keeps vintages."""
    realtime: RealtimePeriod | None = None
    """The real-time period the values were read as of, if one."""
    observation_start: dt.date | None = None
    """The first observation date read."""
    observation_end: dt.date | None = None
    """The last observation date read."""
    transforms: tuple[str, ...] = ()
    """The transforms applied, in order, each with its parameters."""
    retrieved_at: dt.datetime | None = None
    """When the provider fetched the data, in UTC: a fact about the data."""
    licence: LicenceClass
    """The licence class that governed the data."""
    attribution: str
    """The source's attribution text."""
    notice: str | None = None
    """The notice the source requires wherever its data appears."""
    terms_url: str | None = None
    """The source's public terms page; required unless the data is
    user-supplied."""
    llm_use: LlmUse
    """Whether the source's terms let the data reach a language model."""
    cache_hit: bool = False
    """Whether the data came from the local cache rather than the source."""
    served_offline: bool = False
    """Whether offline mode served it."""
    fallback_chain: tuple[str, ...] = ()
    """The providers a resolver tried, in order, ending with this one; empty
    when no resolver chose it."""
    warnings: tuple[str, ...] = ()
    """Warning codes about the data, such as ``revised_data`` or
    ``served_offline``."""

    def __post_init__(self) -> None:
        """Check every field; normalize enums, tuples and the time to UTC."""
        provider = f.identifier(self.provider, "provider")
        f.text(self.series_id, "series_id")
        f.optional_text(self.dataset, "dataset")
        _pattern(self.concept, "concept", CONCEPT_ID_PATTERN)
        if self.field is not None:
            f.identifier(self.field, "field")
        _pattern(self.vintage, "vintage", VINTAGE_LABEL_PATTERN)
        if self.realtime is not None:
            f.instance(self.realtime, RealtimePeriod, "realtime")
        self._check_window()
        licence = f.choice(LicenceClass, self.licence, "licence")
        f.text(self.attribution, "attribution", max_length=f.MAX_TEXT_LENGTH)
        f.optional_text(self.notice, "notice", max_length=f.MAX_TEXT_LENGTH)
        if self.terms_url is not None:
            f.terms_url(self.terms_url)
        elif licence is not LicenceClass.USER_SUPPLIED:
            msg = f"terms_url is required for {licence.value} data"
            raise f.fail(msg)
        f.flag(self.cache_hit, "cache_hit")
        f.flag(self.served_offline, "served_offline")
        chain = f.identifiers(
            self.fallback_chain, "fallback_chain", max_items=MAX_FALLBACK_CHAIN
        )
        if chain and chain[-1] != provider:
            msg = f"fallback_chain must end with the provider {provider!r}"
            raise f.fail(msg)
        items = f.sequence(self.transforms, "transforms", max_items=MAX_TRANSFORMS)
        normalized = {
            "transforms": tuple(f.text(item, "each transform") for item in items),
            "retrieved_at": f.optional_instant(self.retrieved_at, "retrieved_at"),
            "licence": licence,
            "llm_use": f.choice(LlmUse, self.llm_use, "llm_use"),
            "fallback_chain": chain,
            "warnings": f.identifiers(
                self.warnings, "warnings", max_items=MAX_WARNINGS
            ),
        }
        for name, value in normalized.items():
            object.__setattr__(self, name, value)

    def _check_window(self) -> None:
        start = f.optional_day(
            self.observation_start, "observation_start", DATA_DATE_BOUNDS
        )
        end = f.optional_day(self.observation_end, "observation_end", DATA_DATE_BOUNDS)
        if (start is None) != (end is None):
            msg = "observation_start and observation_end are both set or both None"
            raise f.fail(msg)
        if start is not None and end is not None and end < start:
            msg = f"observation_end {end} is before observation_start {start}"
            raise f.fail(msg)

    def to_dict(self) -> dict[str, object]:
        """Return the record as JSON-ready values; every key is always present."""
        return {
            "provider": self.provider,
            "series_id": self.series_id,
            "dataset": self.dataset,
            "concept": self.concept,
            "field": self.field,
            "vintage": self.vintage,
            "realtime": None if self.realtime is None else self.realtime.to_dict(),
            "observation_start": _iso(self.observation_start),
            "observation_end": _iso(self.observation_end),
            "transforms": list(self.transforms),
            "retrieved_at": None
            if self.retrieved_at is None
            else self.retrieved_at.isoformat(),
            "licence": self.licence.value,
            "attribution": self.attribution,
            "notice": self.notice,
            "terms_url": self.terms_url,
            "llm_use": self.llm_use.value,
            "cache_hit": self.cache_hit,
            "served_offline": self.served_offline,
            "fallback_chain": list(self.fallback_chain),
            "warnings": list(self.warnings),
        }

    def canonical_json(self) -> bytes:
        """Return the record as canonical JSON (RFC 8785)."""
        return canonical_json(self.to_dict())

    @classmethod
    def from_dict(cls, data: object) -> DataSource:
        """Read a record back from :meth:`to_dict`'s form, refusing any other."""
        # The constructor checks every value; only the JSON forms that are not
        # already Python values are converted here.
        values: dict[str, Any] = dict(f.mapping(data, "a data source", _SOURCE_KEYS))
        realtime = values["realtime"]
        values["realtime"] = (
            None if realtime is None else RealtimePeriod.from_dict(realtime)
        )
        for name in ("observation_start", "observation_end"):
            values[name] = f.parse_optional_day(values[name], name)
        values["retrieved_at"] = f.parse_instant(values["retrieved_at"], "retrieved_at")
        for name in ("transforms", "fallback_chain", "warnings"):
            values[name] = _array(values[name], name)
        return cls(**values)

    @classmethod
    def from_json(cls, document: str | bytes) -> DataSource:
        """Read a record back from its canonical JSON."""
        return cls.from_dict(f.load_json(document))


_SOURCE_KEYS: Final = (
    "provider",
    "series_id",
    "dataset",
    "concept",
    "field",
    "vintage",
    "realtime",
    "observation_start",
    "observation_end",
    "transforms",
    "retrieved_at",
    "licence",
    "attribution",
    "notice",
    "terms_url",
    "llm_use",
    "cache_hit",
    "served_offline",
    "fallback_chain",
    "warnings",
)


def _iso(value: dt.date | None) -> str | None:
    return None if value is None else value.isoformat()


def _pattern(value: object, what: str, pattern: re.Pattern[str]) -> None:
    """Accept ``None`` or text that matches ``pattern`` in full."""
    if value is not None and not pattern.fullmatch(f.text(value, what)):
        msg = f"{what} {value!r} does not match {pattern.pattern}"
        raise f.fail(msg)


def _array(value: object, what: str) -> tuple[object, ...]:
    """Read a JSON array whose items the record checks as it is built."""
    if not isinstance(value, list):
        msg = f"{what} must be a JSON array, not {type(value).__name__}"
        raise f.fail(msg)
    return tuple(value)
