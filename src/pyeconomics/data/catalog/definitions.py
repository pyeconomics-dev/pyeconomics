# src/pyeconomics/data/catalog/definitions.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The shapes of the catalog: a concept and the candidates that can answer it.

A :class:`Concept` is one quantity in one vocabulary (ADR-0011 decision 15): an
id such as ``us.inflation.pce_core.yoy``, a definition in our own words, and the
unit kind, observation frequency and seasonal adjustment every answer
guarantees. It lists its :class:`Candidate` series in fallback order: the
originator first, then a library-only aggregator on the user's own key, then
premium-only sources (Phase 6 fills that tier). Each candidate names a provider,
the provider's series key, an optional table column and the transforms that
make the series match the definition exactly, because the resolver fails over
only between identical definitions (ROADMAP §4 6.5). A derived candidate,
:class:`Derived`, combines the answers of other concepts instead.

Everything here is plain, frozen data checked at import: ids against the
grammar, transforms against :mod:`pyeconomics.core.transforms`, tiers in
order, and every ``{placeholder}`` in a series key against the concept's
declared :class:`Parameter`. Whether a candidate's provider is registered, and
whether a derived concept's operands exist, is
:func:`pyeconomics.data.catalog.validate`'s job, because it needs the registry.

Examples
--------
>>> from pyeconomics.core import UnitKind
>>> from pyeconomics.data import ObservationFrequency, SeasonalAdjustment
>>> concept = Concept(
...     id="us.unemployment.rate",
...     title="Unemployment rate",
...     definition="The share of the civilian labour force that is unemployed.",
...     unit_kind=UnitKind.RATE,
...     frequency=ObservationFrequency.MONTHLY,
...     seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED,
...     candidates=(
...         Candidate(provider="bls", series="LNS14000000"),
...         Candidate(provider="fred", series="UNRATE", tier=Tier.AGGREGATOR),
...     ),
... )
>>> [c.provider for c in concept.candidates if isinstance(c, Candidate)]
['bls', 'fred']
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.core import _fields as f
from pyeconomics.core.provenance import CONCEPT_ID_PATTERN
from pyeconomics.core.transforms import canonical_transform, parse_transform
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = [
    "MAX_CANDIDATES",
    "Candidate",
    "Concept",
    "Derived",
    "Operand",
    "Parameter",
    "Shape",
    "Tier",
]

#: The most candidates one concept lists.
MAX_CANDIDATES: Final = 8
_MAX_DEFINITION: Final = 1_000
_PAIR: Final = 2
_MONTHS: Final = 12
_PLACEHOLDER: Final = re.compile(r"\{([a-z][a-z0-9_]*)\}")
_PROVIDER: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
_OPTION_VALUE = str | int | bool


class Tier(StrEnum):
    """Where a candidate stands in the fallback order (ADR-0011 decision 15)."""

    ORIGINATOR = "originator"
    """The body that publishes the data, on its own terms."""
    AGGREGATOR = "aggregator"
    """A library-only aggregator reached on the user's own key, such as FRED."""
    PREMIUM = "premium"
    """A premium-only source; Phase 6 adds the first."""


class Shape(StrEnum):
    """Whether a concept answers with one series or a table of columns."""

    SERIES = "series"
    TABLE = "table"


@dataclass(frozen=True, slots=True, kw_only=True)
class Parameter:
    """A value a concept needs from its caller, such as an SEP meeting date.

    The value fills a ``{name}`` placeholder in a candidate's series key. It is
    checked against ``pattern`` first, so a caller selects among what the
    catalog allows and cannot reach a provider with anything else.
    """

    name: str
    pattern: str
    """A regular expression the whole value must match."""
    summary: str
    example: str

    def __post_init__(self) -> None:
        """Check the name, the pattern and that the example satisfies it."""
        f.identifier(self.name, "parameter name")
        f.text(self.summary, "parameter summary")
        try:
            compiled = re.compile(self.pattern)
        except re.error as error:
            msg = f"parameter {self.name!r}: bad pattern: {error}"
            raise f.fail(msg) from None
        if not compiled.fullmatch(self.example):
            msg = (
                f"parameter {self.name!r}: the example {self.example!r} does not match"
            )
            raise f.fail(msg)

    def check(self, value: object) -> str:
        """Return ``value`` if it matches the pattern, else raise ``InputError``."""
        if not isinstance(value, str) or not re.fullmatch(self.pattern, value):
            msg = (
                f"the parameter {self.name!r} must match {self.pattern}, such as "
                f"{self.example!r}, not {value!r}"
            )
            raise f.fail(msg)
        if "{" in value or "}" in value:
            msg = f"the parameter {self.name!r} cannot hold a brace: {value!r}"
            raise f.fail(msg)
        return value


@dataclass(frozen=True, slots=True, kw_only=True)
class Candidate:
    """One provider series that can answer a concept, with its transforms."""

    provider: str
    """The provider's permanent id."""
    series: str
    """The provider's series key; ``{name}`` fills from a concept parameter."""
    column: str | None = None
    """The column to take when the provider answers with a table; ``{name}``
    fills from a concept parameter, as in the series key."""
    columns: tuple[tuple[str, str], ...] = ()
    """For a table concept, ``(concept column, provider column)`` pairs: the
    columns kept, renamed. Empty keeps every column as the provider names it."""
    keep: str | None = None
    """For a table concept, a regular expression: keep the columns it matches."""
    transforms: tuple[str, ...] = ()
    """Transforms applied in order after the fetch, each as canonical text."""
    tier: Tier = Tier.ORIGINATOR
    delivers: ObservationFrequency | None = None
    """The frequency the provider labels the data with, when it differs from the
    concept's cadence class (Treasury labels business days irregular)."""
    options: tuple[tuple[str, _OPTION_VALUE], ...] = ()
    """Extra fields for the provider's own query model."""
    vintages: bool = True
    """Whether the provider keeps this series' vintages, where it keeps any.
    ``False`` for a series a vintage-keeping provider serves only as it stands
    (FRED's daily rates, which ALFRED does not hold): a real-time request skips
    it, and a binding reads it as revised data."""
    note: str | None = None
    """A sentence for the concept page: a quirk of this source."""

    def __post_init__(self) -> None:
        """Check every field and canonicalise the transforms."""
        if not _PROVIDER.fullmatch(self.provider):
            msg = f"a provider id is snake_case, not {self.provider!r}"
            raise f.fail(msg)
        f.text(self.series, "a candidate's series key", max_length=128)
        f.optional_text(self.column, "a candidate's column")
        f.optional_text(self.keep, "a candidate's keep pattern")
        self._check_selection()
        f.choice(Tier, self.tier, "tier")
        if self.delivers is not None:
            f.choice(ObservationFrequency, self.delivers, "delivers")
        f.optional_text(self.note, "a candidate's note", max_length=_MAX_DEFINITION)
        f.flag(self.vintages, "vintages")
        object.__setattr__(
            self, "transforms", tuple(canonical_transform(t) for t in self.transforms)
        )
        for transform in self.transforms:
            if parse_transform(transform).spec.operands != 1:
                msg = f"{transform!r} reads two series; use a derived candidate"
                raise f.fail(msg)
        for name, value in self.options:
            f.identifier(name, "an option name")
            given: object = value
            if not isinstance(given, _OPTION_VALUE):
                msg = f"option {name!r} is text, a whole number or a flag"
                raise f.fail(msg)

    def _check_selection(self) -> None:
        """Check how the candidate picks columns: at most one way, each valid."""
        if self.keep is not None:
            try:
                re.compile(self.keep)
            except re.error as error:
                msg = f"{self.provider}:{self.series}: bad keep pattern: {error}"
                raise f.fail(msg) from None
        if (self.column is not None) + bool(self.columns) + (self.keep is not None) > 1:
            msg = f"{self.provider}:{self.series}: use one of column, columns or keep"
            raise f.fail(msg)
        for pair in self.columns:
            f.text(pair[0], "a concept column")
            f.text(pair[1], "a provider column")

    @property
    def placeholders(self) -> frozenset[str]:
        """The parameter names the series key and the column use."""
        found = _PLACEHOLDER.findall(self.series)
        if self.column is not None:
            found += _PLACEHOLDER.findall(self.column)
        return frozenset(found)


@dataclass(frozen=True, slots=True)
class Operand:
    """One concept a derived candidate reads, with transforms applied first."""

    concept: str
    transforms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Check the concept id and canonicalise the transforms."""
        if not CONCEPT_ID_PATTERN.fullmatch(self.concept):
            msg = f"{self.concept!r} is not a concept id"
            raise f.fail(msg)
        object.__setattr__(
            self, "transforms", tuple(canonical_transform(t) for t in self.transforms)
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class Derived:
    """A candidate that combines the answers of two other concepts.

    ``transform`` is a two-operand transform (``ratio``, ``add``) applied to the
    operands, in order, after each has its own transforms. The result carries one
    ``DataSource`` record per operand.
    """

    operands: tuple[Operand, ...]
    transform: str
    tier: Tier = Tier.ORIGINATOR
    note: str | None = None

    def __post_init__(self) -> None:
        """Check the operands and that the transform combines exactly two."""
        if len(self.operands) != _PAIR:
            msg = "a derived candidate combines exactly two concepts"
            raise f.fail(msg)
        for operand in self.operands:
            f.instance(operand, Operand, "an operand")
        parsed = parse_transform(self.transform)
        if parsed.spec.operands != _PAIR:
            msg = f"{self.transform!r} does not combine two concepts"
            raise f.fail(msg)
        object.__setattr__(self, "transform", parsed.text())
        f.choice(Tier, self.tier, "tier")
        f.optional_text(self.note, "a candidate's note", max_length=_MAX_DEFINITION)


@dataclass(frozen=True, slots=True, kw_only=True)
class Concept:
    """One catalog concept: its id, its guarantees and its candidates in order."""

    id: str
    title: str
    definition: str
    unit_kind: UnitKind | None
    """The unit kind every answer has; ``None`` only for a table of mixed kinds."""
    frequency: ObservationFrequency
    seasonal_adjustment: SeasonalAdjustment
    candidates: tuple[Candidate | Derived, ...]
    shape: Shape = Shape.SERIES
    unit_text: str | None = None
    """The unit in words for the page: ``decimal per year``, ``index, 2017=100``."""
    year_ends_in: int = 12
    """The month the concept's year ends in (CBO's fiscal year ends in 9)."""
    needs_window: bool = False
    """Whether the sources need explicit ``start`` and ``end`` dates."""
    parameters: tuple[Parameter, ...] = ()
    notes: tuple[str, ...] = ()
    """What a user should know that the definition does not say."""
    section: str = "Other"
    """The heading the concept's page is filed under."""

    def __post_init__(self) -> None:
        """Check the id, the texts, the shape and the candidates' order."""
        if not CONCEPT_ID_PATTERN.fullmatch(self.id):
            msg = f"{self.id!r} is not a concept id (dotted snake_case, 3 or 4 parts)"
            raise f.fail(msg)
        f.text(self.title, f"{self.id}: title")
        f.text(self.definition, f"{self.id}: definition", max_length=_MAX_DEFINITION)
        f.optional_text(self.unit_text, f"{self.id}: unit_text")
        if self.unit_kind is None:
            if self.shape is not Shape.TABLE:
                msg = f"{self.id}: only a table concept may leave unit_kind out"
                raise f.fail(msg)
        else:
            f.choice(UnitKind, self.unit_kind, "unit_kind")
        f.choice(ObservationFrequency, self.frequency, "frequency")
        f.choice(SeasonalAdjustment, self.seasonal_adjustment, "seasonal_adjustment")
        f.choice(Shape, self.shape, "shape")
        f.flag(self.needs_window, "needs_window")
        if not 1 <= self.year_ends_in <= _MONTHS:
            msg = f"{self.id}: year_ends_in is a month from 1 to 12"
            raise f.fail(msg)
        for note in self.notes:
            f.text(note, f"{self.id}: a note", max_length=_MAX_DEFINITION)
        self._check_candidates()

    def _check_candidates(self) -> None:
        if not 1 <= len(self.candidates) <= MAX_CANDIDATES:
            msg = f"{self.id}: lists 1 to {MAX_CANDIDATES} candidates"
            raise f.fail(msg)
        declared = {parameter.name for parameter in self.parameters}
        if len(declared) != len(self.parameters):
            msg = f"{self.id}: repeats a parameter"
            raise f.fail(msg)
        used: set[str] = set()
        previous = Tier.ORIGINATOR
        order = tuple(Tier)
        for candidate in self.candidates:
            checked: object = candidate
            if not isinstance(checked, Candidate | Derived):
                msg = f"{self.id}: a candidate is a Candidate or a Derived"
                raise f.fail(msg)
            if order.index(candidate.tier) < order.index(previous):
                msg = (
                    f"{self.id}: candidates run originator, then aggregator, then "
                    "premium; this one is out of order"
                )
                raise f.fail(msg)
            previous = candidate.tier
            used |= self._check_shape(candidate)
        if used != declared:
            msg = (
                f"{self.id}: the placeholders {sorted(used)} and the declared "
                f"parameters {sorted(declared)} differ"
            )
            raise f.fail(msg)

    def _check_shape(self, candidate: Candidate | Derived) -> frozenset[str]:
        """Check a candidate suits the concept's shape; return its placeholders."""
        if self.shape is not Shape.TABLE:
            return (
                candidate.placeholders
                if isinstance(candidate, Candidate)
                else frozenset()
            )
        if isinstance(candidate, Derived):
            msg = f"{self.id}: a derived candidate answers a series concept"
            raise f.fail(msg)
        if candidate.column is not None:
            msg = f"{self.id}: a table concept takes columns, not a column"
            raise f.fail(msg)
        if candidate.transforms:
            msg = f"{self.id}: transforms read a series, not a table"
            raise f.fail(msg)
        return candidate.placeholders

    @property
    def originators(self) -> tuple[Candidate | Derived, ...]:
        """The originator candidates, in order."""
        return tuple(c for c in self.candidates if c.tier is Tier.ORIGINATOR)
