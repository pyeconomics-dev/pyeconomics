# src/pyeconomics/data/catalog/checks.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The catalog's structural rules, reported as ``<concept>: [<rule>] <detail>``.

Importing the catalog already checks what needs no registry: ids, transforms,
tiers and placeholders. These rules need the provider registry, so they run in
``pyeconomics.data.registry.validate()`` for the installed registry (and in a
test):

``concept-provider``
    A candidate names a provider that is not registered or cannot fetch.
``concept-series``
    A candidate's series key is one its provider refuses to build a request for.
    The check builds the request and sends nothing; for a provider that needs an
    extra it runs only with ``deep=True``, since building the request imports the
    extra's client library.
``concept-operand``
    A derived candidate names a concept the catalog does not have, or one that
    is not a series.
``concept-cycle``
    Derived concepts depend on one another in a loop.

A concept that is library-only throughout is legitimate (the Dallas Fed's
trimmed-mean PCE), so the rules do not demand a hosted candidate.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final

from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.data.catalog import CONCEPTS
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived, Shape
from pyeconomics.data.errors import DataError, ProviderNotFoundError
from pyeconomics.data.providers.base import Capability
from pyeconomics.data.providers.rules import Problem

if TYPE_CHECKING:
    from pyeconomics.data.providers.base import DataProvider
    from pyeconomics.data.registry import ProviderRegistry

__all__ = ["RULES", "problems"]

#: Every rule slug :func:`problems` can report.
RULES: Final = (
    "concept-provider",
    "concept-series",
    "concept-operand",
    "concept-cycle",
)

_SAMPLE_START: Final = dt.date(2020, 1, 1)
_SAMPLE_END: Final = dt.date(2020, 12, 31)


def _sample(concept: Concept, candidate: Candidate) -> str:
    """Fill a series key's placeholders with the parameters' examples."""
    examples = {p.name: p.example for p in concept.parameters}
    return candidate.series.format_map(examples)


def _series_problem(
    provider: DataProvider, concept: Concept, candidate: Candidate
) -> str | None:
    """Return why a provider refuses a candidate's series key, if it does."""
    fields: dict[str, object] = {
        "series": (_sample(concept, candidate),),
        "start": _SAMPLE_START,
        "end": _SAMPLE_END,
        **dict(candidate.options),
    }
    try:
        provider.build_requests(provider.query_type.model_validate(fields))
    except MissingOptionalDependencyError:
        return None  # the extra is not installed here; the key cannot be judged
    except (DataError, ValueError, TypeError, KeyError, IndexError) as error:
        lines = str(error).splitlines()
        return lines[0][:200] if lines else type(error).__name__
    return None


def _candidate_problems(
    concept: Concept, candidate: Candidate, registry: ProviderRegistry, *, deep: bool
) -> list[Problem]:
    try:
        provider = registry.get(candidate.provider)
    except ProviderNotFoundError:
        return [
            Problem(
                concept.id,
                "concept-provider",
                f"candidate {candidate.provider}:{candidate.series} names a "
                "provider that is not registered",
            )
        ]
    if Capability.FETCH not in provider.info.capabilities:
        return [
            Problem(
                concept.id,
                "concept-provider",
                f"{candidate.provider} cannot fetch, so it cannot answer a concept",
            )
        ]
    if provider.info.extra is not None and not deep:
        return []  # building its request imports the optional client library
    reason = _series_problem(provider, concept, candidate)
    if reason is None:
        return []
    return [
        Problem(
            concept.id,
            "concept-series",
            f"{candidate.provider} refuses the series {candidate.series!r}: {reason}",
        )
    ]


def _derived_problems(concept: Concept, candidate: Derived) -> list[Problem]:
    found: list[Problem] = []
    for operand in candidate.operands:
        other = CONCEPTS.get(operand.concept)
        if other is None:
            found.append(
                Problem(
                    concept.id,
                    "concept-operand",
                    f"derived from {operand.concept}, which the catalog lacks",
                )
            )
        elif other.shape is not Shape.SERIES:
            found.append(
                Problem(
                    concept.id,
                    "concept-operand",
                    f"derived from {operand.concept}, which is a table",
                )
            )
    return found


def _cycles() -> list[Problem]:
    """Find derived concepts that depend on themselves, directly or not."""
    edges = {
        concept.id: [
            operand.concept
            for candidate in concept.candidates
            if isinstance(candidate, Derived)
            for operand in candidate.operands
        ]
        for concept in CONCEPTS.values()
    }
    found: list[Problem] = []
    for start in sorted(edges):
        seen: set[str] = set()
        stack = list(edges[start])
        while stack:
            current = stack.pop()
            if current == start:
                found.append(Problem(start, "concept-cycle", "is derived from itself"))
                break
            if current in seen:
                continue
            seen.add(current)
            stack.extend(edges.get(current, ()))
    return found


def problems(registry: ProviderRegistry, *, deep: bool = False) -> list[Problem]:
    """Return every structural problem of the catalog against a provider registry.

    Parameters
    ----------
    registry
        The providers to check the catalog against.
    deep
        Also build a request for the series of a provider that needs an extra,
        which imports its client library (and so the HTTP stack). The default
        leaves those to a test, because ``registry.validate()`` must not import
        the transport (ADR-0011 decision 10).
    """
    found: list[Problem] = []
    for concept in CONCEPTS.values():
        for candidate in concept.candidates:
            if isinstance(candidate, Candidate):
                found += _candidate_problems(concept, candidate, registry, deep=deep)
            else:
                found += _derived_problems(concept, candidate)
    return found + _cycles()
