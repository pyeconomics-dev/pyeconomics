# src/pyeconomics/data/catalog/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The semantic catalog: one vocabulary for data (ADR-0011 decision 15).

A *concept* is a quantity with an id (``us.inflation.pce_core.yoy``), a
definition in our own words, the unit kind, frequency and seasonal adjustment
every answer guarantees, and candidate provider series in fallback order. The
catalog ships as Python modules, one per topic, so the wheel carries it and
importing it validates every id, transform and tier. Concept ids are permanent
once released: ``pyeconomics.data.registry.validate()`` reports a released id
that is missing here.

The catalog is plain data. Resolving a concept to a series is
:mod:`pyeconomics.data.resolver`'s job; the transforms a candidate lists are
:mod:`pyeconomics.data.catalog.transforms`; their names live in
:mod:`pyeconomics.core.transforms`, which core can read without importing the
data layer.

Examples
--------
>>> from pyeconomics.data import catalog
>>> concept = catalog.get("us.unemployment.rate")
>>> concept.title, [c.provider for c in concept.candidates]
('Unemployment rate', ['bls', 'fred'])
>>> "us.inflation.pce_core.yoy" in catalog.ids()
True
>>> try:
...     catalog.get("us.inflation.pce_core")
... except LookupError as error:
...     print(type(error).__name__, error.close_matches[0])
ConceptNotFoundError us.inflation.pce_core.yoy
"""

from __future__ import annotations

import difflib
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from pyeconomics.data.catalog import (
    factors,
    fiscal,
    growth,
    international,
    labour,
    markets,
    output,
    prices,
    projections,
    rates,
)
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Parameter,
    Shape,
    Tier,
)
from pyeconomics.data.errors import ConceptNotFoundError

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "CONCEPTS",
    "Candidate",
    "Concept",
    "Derived",
    "Operand",
    "Parameter",
    "Shape",
    "Tier",
    "concepts",
    "get",
    "ids",
]

_MODULES: Final = (
    prices,
    labour,
    output,
    rates,
    projections,
    fiscal,
    growth,
    factors,
    markets,
    international,
)


def _collect() -> Mapping[str, Concept]:
    found: dict[str, Concept] = {}
    for module in _MODULES:
        for concept in module.CONCEPTS:
            if concept.id in found:
                msg = f"the catalog defines {concept.id!r} twice"
                raise ValueError(msg)
            found[concept.id] = concept
    return MappingProxyType(dict(sorted(found.items())))


#: Every concept, by id, sorted.
CONCEPTS: Final[Mapping[str, Concept]] = _collect()


def ids() -> tuple[str, ...]:
    """Return every concept id, sorted."""
    return tuple(CONCEPTS)


def concepts() -> tuple[Concept, ...]:
    """Return every concept, sorted by id."""
    return tuple(CONCEPTS.values())


def get(concept_id: str) -> Concept:
    """Return the concept with this id.

    Raises
    ------
    ConceptNotFoundError
        If the catalog has no such concept; the error lists close matches.
    """
    found = CONCEPTS.get(concept_id)
    if found is not None:
        return found
    asked: object = concept_id
    matches = (
        difflib.get_close_matches(asked, list(CONCEPTS), n=3, cutoff=0.7)
        if isinstance(asked, str)
        else []
    )
    raise ConceptNotFoundError(str(asked), close_matches=matches)
