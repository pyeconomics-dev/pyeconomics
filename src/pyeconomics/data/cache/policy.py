# src/pyeconomics/data/cache/policy.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the cache may keep, for how long and what a fetch reports (ADR-0011).

This module is pure: it reads no clock, file or environment. The cache's
I/O lives in :mod:`~pyeconomics.data.cache.store` and the package itself, which
pass it the time and the settings.

- :func:`may_store` is the licence gate (ADR-0005 rule 4). A source, or a
  series, whose terms forbid storage has **no cache path at all**: no read, no
  write, no file and no opt-in. ``user-supplied`` data is processed in memory
  for one run and never stored either.
- :class:`CacheKey` names an entry by provider, dataset, series, the canonical
  query without credentials and the vintage label. A query with a field named
  like a credential has no key and is never cached.
- :func:`expiry` gives an open entry (``latest``, ``first_release``, ``all`` or
  an ``as_of`` date still within :data:`CLOSED_AFTER` of today) the provider's
  time-to-live, or the configured override, and a *closed past vintage* none: it
  lives until the size cap evicts it, because a source never rewrites it.
- :class:`Fetched` is what ``DataProvider.fetch_with_origin`` returns: the frame
  and an :class:`Origin` saying whether the cache or offline mode served it.
  :meth:`Fetched.source` turns both into the
  :class:`~pyeconomics.core.provenance.DataSource` record a manifest carries.

Examples
--------
>>> import datetime as dt
>>> now = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)
>>> expiry("latest", now=now, ttl=3600).isoformat()
'2026-10-15T13:00:00+00:00'
>>> expiry("as_of:2020-03-31", now=now, ttl=3600) is None
True
>>> expiry("as_of:2026-10-15", now=now, ttl=3600).isoformat()
'2026-10-15T13:00:00+00:00'

"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import MAX_WARNINGS, DataSource, LicenceClass
from pyeconomics.data.redaction import is_credential_parameter
from pyeconomics.data.terms import CachePolicy
from pyeconomics.data.types import Series, SeriesMeta, Table
from pyeconomics.data.vintage import Vintage, VintageKind

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.terms import Terms

__all__ = [
    "CLOSED_AFTER",
    "DEFAULT_TTL_SECONDS",
    "DISCARDED_WARNING",
    "NOTE_WARNINGS",
    "OFFLINE_WARNING",
    "CacheKey",
    "Fetched",
    "Origin",
    "expiry",
    "is_closed",
    "may_store",
    "offline_message",
]

#: The warning code on a record served by offline mode.
OFFLINE_WARNING: Final = "served_offline"
#: The warning code for an entry that failed its checks and was deleted.
DISCARDED_WARNING: Final = "cache_entry_discarded"
#: The frame notes (``SeriesMeta.notes``) a record repeats as a warning code:
#: the ones that say something about the whole series a run read. ``revised_data``
#: is a source that keeps only its current estimates, so a historical evaluation
#: on it uses information not available at the time; ``bls_keyless`` is a series
#: read without a catalog, so its unit and seasonal adjustment are unknown. The
#: dated notes (footnotes, annotations, missing-value markers) stay on the frame.
NOTE_WARNINGS: Final = frozenset({"revised_data", "bls_keyless"})
#: An ``as_of`` vintage is closed once its date is more than this long ago. A
#: source dates a vintage in its own time zone, so the margin keeps "yesterday"
#: from counting as closed while it may still change.
CLOSED_AFTER: Final = dt.timedelta(days=1)

#: A provider's default time-to-live for open entries: one hour.
DEFAULT_TTL_SECONDS: Final = 3_600

_SHOWN_SERIES: Final = 5


def may_store(terms: Terms) -> bool:
    """Return whether data under ``terms`` may be written to disk.

    ``False`` for a source or series whose terms forbid storage, and for
    ``user-supplied`` data, which is processed in memory for one run (ADR-0005).

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.core.provenance import LlmUse
    >>> from pyeconomics.data.terms import Terms
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://example.org",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: Example.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> may_store(terms), may_store(terms.with_overrides(cache=CachePolicy.FORBIDDEN))
    (True, False)

    """
    return (
        terms.cache is CachePolicy.ALLOWED
        and terms.licence is not LicenceClass.USER_SUPPLIED
    )


def is_closed(vintage: str, *, today: dt.date) -> bool:
    """Return whether a vintage label names data a source will not change.

    Only ``as_of:<date>`` can be closed, once ``date`` lies more than
    :data:`CLOSED_AFTER` before ``today``. ``latest``, ``first_release`` and
    ``all`` grow as the source publishes, so they are never closed.

    Examples
    --------
    >>> import datetime as dt
    >>> today = dt.date(2026, 10, 15)
    >>> is_closed("as_of:2020-03-31", today=today), is_closed("latest", today=today)
    (True, False)
    >>> is_closed("as_of:2026-10-14", today=today)
    False
    """
    selector = Vintage.parse(vintage)
    return (
        selector.kind is VintageKind.AS_OF
        and selector.on is not None
        and selector.on < today - CLOSED_AFTER
    )


def expiry(vintage: str, *, now: dt.datetime, ttl: int) -> dt.datetime | None:
    """Return when an entry written ``now`` stops being fresh, or ``None``.

    ``None`` is a closed past vintage: it never expires and leaves the cache
    only when the size cap evicts it.
    """
    if is_closed(vintage, today=now.date()):
        return None
    return now + dt.timedelta(seconds=ttl)


def _where(series: Sequence[str]) -> str:
    shown = ", ".join(series[:_SHOWN_SERIES])
    extra = len(series) - _SHOWN_SERIES
    return f"series {shown}" + (f" and {extra} more" if extra > 0 else "")


def offline_message(
    provider: str, series: Sequence[str], *, forbidden: bool, reason: str | None = None
) -> str:
    """Say why offline mode cannot serve a fetch; it names no path or URL.

    Parameters
    ----------
    provider
        The provider id.
    series
        The series the query names.
    forbidden
        Whether the source's terms forbid storage, so nothing of it is ever
        cached.
    reason
        Why the cache is unusable, when it is.

    Examples
    --------
    >>> print(offline_message("fred", ["GDPC1"], forbidden=True))
    fred cannot be served offline: its terms forbid storing its data, so none of it is ever cached (series GDPC1); fetch it online
    """  # noqa: E501 - doctest output lines cannot wrap
    where = _where(series)
    if forbidden:
        return (
            f"{provider} cannot be served offline: its terms forbid storing its "
            f"data, so none of it is ever cached ({where}); fetch it online"
        )
    if reason is not None:
        return f"offline mode has no usable cache for {provider} ({where}): {reason}"
    return (
        f"offline mode has no cached copy of {provider} {where}; fetch it online "
        "once to cache it (a series whose terms forbid storage is never cached)"
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class CacheKey:
    """What identifies one entry: the provider, dataset, series, query and vintage.

    Build one with :meth:`of`. The query is its canonical JSON (RFC 8785) with
    every field a provider's query model has, which never includes a credential:
    a key travels beside the query, not in it.
    """

    provider: str
    dataset: str
    """The query's ``dataset`` field when it has one, otherwise ``""``."""
    series: str
    """The query's series ids, comma-separated, in query order."""
    query: str
    vintage: str

    @classmethod
    def of(cls, provider: str, query: Query) -> CacheKey | None:
        """Return the key of a query, or ``None`` when it must not be cached.

        A query with a field named like a credential (``api_key``, ``token``, ...)
        has no key, so nothing of it can reach the store; neither does one whose
        fields have no canonical JSON.

        Examples
        --------
        >>> from pyeconomics.data.providers.base import Query
        >>> key = CacheKey.of("demo", Query(series=("GDP",), vintage="latest"))
        >>> key.series, key.vintage, key.dataset
        ('GDP', 'latest', '')
        """
        try:
            fields = query.model_dump(mode="json")
            if any(is_credential_parameter(name) for name in fields):
                return None
            document = canonical_json(fields).decode("utf-8")
        except (TypeError, ValueError):
            return None
        dataset = fields.get("dataset")
        return cls(
            provider=provider,
            dataset=dataset if isinstance(dataset, str) else "",
            series=",".join(query.series),
            query=document,
            vintage=query.vintage,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Origin:
    """Where a fetched frame came from, beyond the source itself.

    A live fetch has the default origin. The fields map onto the
    :class:`~pyeconomics.core.provenance.DataSource` record.
    """

    cache_hit: bool = False
    """Whether the local cache served it."""
    served_offline: bool = False
    """Whether offline mode served it (always from the cache)."""
    warnings: tuple[str, ...] = ()
    """Warning codes about the data: ``served_offline`` and
    ``cache_entry_discarded``."""


@dataclass(frozen=True, slots=True)
class Fetched:
    """A fetched frame, the vintage it was asked for and where it came from.

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import (
    ...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
    ...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
    ... )
    >>> when = dt.datetime(2026, 10, 14, 9, 30, tzinfo=dt.UTC)
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://example.org",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: Example.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
    ...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.ANNUAL,
    ...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
    ...     source_dating=DateConvention.PERIOD_END, terms=terms, retrieved_at=when)
    >>> days = (dt.date(2023, 12, 31), dt.date(2024, 12, 31))
    >>> series = Series(days, (1.0, 2.0), meta)
    >>> record = Fetched(series, Origin(cache_hit=True), "latest").source()
    >>> record.cache_hit, record.retrieved_at == when, record.observation_end
    (True, True, datetime.date(2024, 12, 31))
    """

    frame: Series | Table
    origin: Origin
    vintage: str
    """The vintage label the fetch asked for."""

    def source(self) -> DataSource:
        """Return the provenance record of this fetch.

        It names the data, never the request: the series or table id, the
        dataset, the vintage label, the observation window, the retrieval time
        (a cached entry keeps its original one), the licence, attribution, notice,
        terms page and ``llm_use`` the data came under, and whether the cache or
        offline mode served it. Its warning codes are the origin's, then the
        frame's notes that say something about the whole series
        (:data:`NOTE_WARNINGS`). A binding adds the concept, the field and the
        transforms (Phase 3 Step 12) with :func:`dataclasses.replace`.
        """
        frame, meta = self.frame, self.frame.meta
        terms = meta.terms
        codes = (note.partition(": ")[0] for note in meta.notes)
        warnings = dict.fromkeys(
            (*self.origin.warnings, *(c for c in codes if c in NOTE_WARNINGS))
        )
        identifier = meta.series_id if isinstance(meta, SeriesMeta) else meta.table_id
        window = (frame.index[0], frame.index[-1]) if frame.index else (None, None)
        return DataSource(
            provider=meta.provider,
            series_id=identifier,
            dataset=meta.dataset,
            vintage=self.vintage,
            observation_start=window[0],
            observation_end=window[1],
            retrieved_at=meta.retrieved_at,
            licence=terms.licence,
            attribution=terms.attribution,
            notice=terms.notice,
            terms_url=terms.terms_url,
            llm_use=terms.llm_use,
            cache_hit=self.origin.cache_hit,
            served_offline=self.origin.served_offline,
            warnings=tuple(warnings)[:MAX_WARNINGS],
        )
