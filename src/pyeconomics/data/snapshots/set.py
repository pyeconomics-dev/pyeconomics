# src/pyeconomics/data/snapshots/set.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the hosted snapshot keeps, computed from the catalog (ADR-0013 decision 6).

:func:`snapshot_set` walks every catalog concept, and every concept a registered
model's bindings name in any profile, and keeps each candidate series that

- a registered provider serves under ``hosted-safe`` terms (never a library-only,
  ``byok`` or ``premium-local`` source, so never FRED or ALFRED),
- comes from an originator (never an aggregator or a premium source), and
- whose terms allow storage (:func:`~pyeconomics.data.cache.policy.may_store`,
  the one storage gate). A hosted-safe candidate whose terms forbid storage is
  left out and listed in :attr:`SnapshotSet.excluded`, as is one this layout
  cannot express (a query option, or a parameter with no declared values).

A parameterized concept is expanded over the values declared here: the SEP's
``meeting`` over :data:`SEP_MEETINGS`. A series' own terms, known only once it
is fetched, are checked again by the writer, which keeps nothing they forbid.

Each entry is one provider series, fetched at ``latest``, or at ``all`` from a
source that keeps that series' vintages, so the reader can still answer a
real-time request. It is fetched whole, except where its source serves it only
by window: then from the first day :data:`HISTORY_STARTS` declares to the day of
the run. A concept that needs a window and has no declared start is left out.

This module is pure: it reads metadata only.

Examples
--------
>>> chosen = snapshot_set()
>>> chosen.get("treasury", "par_nominal").target
'treasury:par_nominal'
>>> any(entry.provider == "fred" for entry in chosen.entries)
False
"""

from __future__ import annotations

import datetime as dt
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.cache.policy import may_store
from pyeconomics.data.catalog.definitions import Candidate, Tier
from pyeconomics.data.errors import ProviderNotFoundError
from pyeconomics.data.providers.base import Capability

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core.model import Model
    from pyeconomics.data.catalog.definitions import Concept
    from pyeconomics.data.providers.base import ProviderInfo
    from pyeconomics.data.registry import ProviderRegistry

__all__ = [
    "DECLARED_VALUES",
    "HISTORY_STARTS",
    "SEP_MEETINGS",
    "Entry",
    "Excluded",
    "SnapshotSet",
    "bound_concepts",
    "snapshot_set",
]

#: The FOMC meetings with a Summary of Economic Projections the snapshot keeps,
#: each dated by its second day as the Board's projection tables are. A meeting
#: still to come is fetched from its day on; until then its fetch reports
#: ``series-not-found`` and nothing is kept. Extend it when the Board publishes
#: the next year's calendar.
SEP_MEETINGS: Final = (
    "2024-12-18",
    "2025-03-19",
    "2025-06-18",
    "2025-09-17",
    "2025-12-10",
    "2026-03-18",
    "2026-06-17",
    "2026-09-16",
    "2026-12-09",
)
#: The values each concept parameter is expanded over in a series key.
DECLARED_VALUES: Final[Mapping[str, tuple[str, ...]]] = {"meeting": SEP_MEETINGS}
#: Where the snapshot's history of a series starts, for a source that serves it
#: only by window. Treasury's curves are one file a month, from each curve's first
#: month. NY Fed answers a whole-history EFFR read with HTTP 400 (#135), and its
#: history holds a Sunday, 2003-07-20, that a business-day frame refuses (#196),
#: so its history starts the day after.
HISTORY_STARTS: Final[Mapping[tuple[str, str], dt.date]] = {
    ("treasury", "par_nominal"): dt.date(1990, 1, 1),
    ("treasury", "par_real"): dt.date(2003, 1, 1),
    ("nyfed", "effr"): dt.date(2003, 7, 21),
}

_PLACEHOLDER: Final = re.compile(r"\{([a-z_][a-z0-9_]*)\}")


@dataclass(frozen=True, slots=True, kw_only=True)
class Entry:
    """One provider series the snapshot keeps."""

    provider: str
    series: str
    vintage: str
    """``latest``, or ``all`` for a series whose source keeps its vintages."""
    concepts: tuple[str, ...]
    """The concepts it answers, sorted."""
    start: dt.date | None = None
    """The first day fetched, for a source that serves the series by window;
    ``None`` fetches its whole history."""

    @property
    def target(self) -> str:
        """The series as ``data.get`` names it: ``provider:series``."""
        return f"{self.provider}:{self.series}"


@dataclass(frozen=True, slots=True, kw_only=True)
class Excluded:
    """A hosted-safe originator candidate the snapshot leaves out, and why."""

    provider: str
    series: str
    concept: str
    reason: str
    """``storage_forbidden``, ``query_options``, ``undeclared_parameter`` or
    ``undeclared_window``."""


@dataclass(frozen=True, slots=True)
class SnapshotSet:
    """The series the snapshot keeps, by provider and series, and those left out."""

    entries: tuple[Entry, ...]
    excluded: tuple[Excluded, ...] = ()

    def __len__(self) -> int:
        """Return how many series the snapshot keeps."""
        return len(self.entries)

    def providers(self) -> tuple[str, ...]:
        """Return the providers the snapshot reads, sorted."""
        return tuple(sorted({entry.provider for entry in self.entries}))

    def of(self, provider: str) -> tuple[Entry, ...]:
        """Return one provider's entries, sorted by series."""
        return tuple(entry for entry in self.entries if entry.provider == provider)

    def get(self, provider: str, series: str) -> Entry | None:
        """Return the entry for a provider series, or ``None`` outside the set."""
        return next(
            (e for e in self.entries if e.provider == provider and e.series == series),
            None,
        )


def bound_concepts(models: Iterable[Model[Any, Any]]) -> frozenset[str]:
    """Return every concept the models' bindings name, in every profile."""
    return frozenset(
        binding.concept for model in models for binding in model.spec.bindings
    )


def _installed_models() -> tuple[Model[Any, Any], ...]:
    from pyeconomics import registry as model_registry  # noqa: PLC0415 - discovery

    return tuple(model_registry.get(model_id) for model_id in model_registry.ids())


def _expanded(
    concept: Concept, candidate: Candidate
) -> tuple[tuple[str, ...], str | None]:
    """Return the series keys a candidate names, or the reason it cannot be kept."""
    names = _PLACEHOLDER.findall(candidate.series)
    if not names:
        return (candidate.series,), None
    if len(names) != 1 or names[0] not in DECLARED_VALUES:
        return (), "undeclared_parameter"
    parameter = next(p for p in concept.parameters if p.name == names[0])
    return (
        tuple(
            candidate.series.format_map({parameter.name: parameter.check(value)})
            for value in DECLARED_VALUES[parameter.name]
        ),
        None,
    )


def _hosted_originator(
    candidate: Candidate, providers: ProviderRegistry
) -> ProviderInfo | None:
    """Return a candidate's provider when it is a hosted-safe originator."""
    if candidate.tier is not Tier.ORIGINATOR:
        return None
    try:
        info = providers.provider_class(candidate.provider).info
    except ProviderNotFoundError:
        return None
    return info if info.terms.licence is LicenceClass.HOSTED_SAFE else None


def _kept(
    concept: Concept, candidate: Candidate, info: ProviderInfo
) -> tuple[tuple[str, ...], str | None]:
    """Return a candidate's series keys, or the reason the snapshot leaves it out."""
    keys, problem = _expanded(concept, candidate)
    if problem is None and candidate.options:
        problem = "query_options"
    if problem is None and concept.needs_window:
        undeclared = [k for k in keys if (info.id, k) not in HISTORY_STARTS]
        problem = "undeclared_window" if undeclared else None
    if problem is None and not may_store(info.terms):
        problem = "storage_forbidden"
    return keys, problem


def snapshot_set(
    *,
    registry: ProviderRegistry | None = None,
    models: Iterable[Model[Any, Any]] | None = None,
) -> SnapshotSet:
    """Compute the series the hosted snapshot keeps.

    Parameters
    ----------
    registry
        The provider registry; the installed one by default.
    models
        The models whose bindings' concepts join the catalog's; every registered
        model by default.
    """
    providers = registry or provider_registry.installed()
    wanted = {concept.id for concept in catalog.concepts()}
    wanted |= bound_concepts(_installed_models() if models is None else models)
    found: dict[tuple[str, str], set[str]] = defaultdict(set)
    vintaged: set[tuple[str, str]] = set()
    excluded: list[Excluded] = []
    for concept_id in sorted(wanted):
        concept = catalog.get(concept_id)
        for candidate in concept.candidates:
            if not isinstance(candidate, Candidate):
                continue
            info = _hosted_originator(candidate, providers)
            if info is None:
                continue
            keys, problem = _kept(concept, candidate, info)
            if problem is not None:
                excluded.append(
                    Excluded(
                        provider=info.id,
                        series=candidate.series,
                        concept=concept.id,
                        reason=problem,
                    )
                )
                continue
            keeps = Capability.VINTAGES in info.capabilities and candidate.vintages
            for key in keys:
                found[info.id, key].add(concept.id)
                if keeps:
                    vintaged.add((info.id, key))
    entries = tuple(
        Entry(
            provider=provider,
            series=series,
            vintage="all" if (provider, series) in vintaged else "latest",
            concepts=tuple(sorted(concepts)),
            start=HISTORY_STARTS.get((provider, series)),
        )
        for (provider, series), concepts in sorted(found.items())
    )
    return SnapshotSet(entries, tuple(excluded))
