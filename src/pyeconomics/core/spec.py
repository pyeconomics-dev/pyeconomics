# src/pyeconomics/core/spec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The model specification: what a registered model declares about itself.

One catalog entry is one :class:`ModelSpec`: a permanent id, a version, a card's
worth of prose (formula, assumptions, limitations, references), an
:class:`Evidence` status, a :class:`CostClass`, invariants and examples, plus
the typed input and output models. The ``@model`` decorator in
:mod:`pyeconomics.core.model` builds one; ``registry.validate()`` rejects a
specification that is incomplete.

The classes here are plain frozen dataclasses that check nothing when they are
built. Completeness is the registry's job, so a specification with a gap can be
constructed, inspected and reported on rather than failing at import time.

Examples
--------
>>> from pyeconomics.core import DOMAINS, Evidence, Reference
>>> len(DOMAINS), Evidence.STANDARD.value
(15, 'standard')
>>> Reference(key="fisher1930", citation="Fisher (1930)", doi="10.1/x",
...           locator="Part I").locator
'Part I'

"""

from __future__ import annotations

import re
import types
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Final, Union, get_args, get_origin

from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core.binding import Binding

__all__ = [
    "CALCULATION_FIELD",
    "DEFAULT_ALIAS_REMOVAL",
    "DOMAINS",
    "MAX_SUMMARY_LENGTH",
    "MAX_TEXT_LENGTH",
    "MAX_TITLE_LENGTH",
    "MODEL_ID",
    "SNAKE_CASE",
    "Alias",
    "ChangelogEntry",
    "ChartKind",
    "ChartSpec",
    "CostClass",
    "Evidence",
    "Example",
    "Invariant",
    "ModelSpec",
    "Reference",
    "union_discriminator",
    "union_members",
]

#: The fifteen domains a model id may start with (ROADMAP section 4 7.2).
DOMAINS: Final = (
    "foundations",
    "econometrics",
    "macro",
    "international",
    "micro",
    "accounting",
    "corporate",
    "equity",
    "fixed_income",
    "derivatives",
    "alternatives",
    "portfolio",
    "asset_pricing",
    "risk",
    "performance",
)

#: A model id: ``<domain>.<name>``, or ``<domain>.<family>.<name>`` (ADR-0003).
MODEL_ID: Final = re.compile(r"[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*){1,2}")

#: A snake_case identifier: an invariant id, a warning code, an example name.
SNAKE_CASE: Final = re.compile(r"[a-z][a-z0-9_]*")

#: The input and output field that names a calculation in a discriminated union.
CALCULATION_FIELD: Final = "calculation"

#: The longest title, summary and prose item a specification may carry.
MAX_TITLE_LENGTH: Final = 80
MAX_SUMMARY_LENGTH: Final = 300
MAX_TEXT_LENGTH: Final = 1_000

#: The release that removes an alias unless the model names another (ADR-0003:
#: a name is removed only in a major release, after a minor one has warned).
DEFAULT_ALIAS_REMOVAL: Final = "2.0.0"


class Evidence(StrEnum):
    """How far to trust a model's premise, apart from whether its code is right.

    The statuses are ROADMAP section 5's "Model quality and governance" table.
    """

    STANDARD = "standard"
    """Textbook consensus, such as bond duration or the CAPM formula."""
    PRACTITIONER = "practitioner"
    """A widely used rule of thumb or convention, such as the rule of 72."""
    CONTESTED = "contested"
    """Under active academic or policy debate, such as r-star estimates."""
    REJECTED = "rejected"
    """Failed out of sample; kept for history and teaching."""
    HISTORICAL = "historical"
    """A superseded methodology, kept for reproducibility."""


class CostClass(StrEnum):
    """The compute cost a hosted service budgets for (ROADMAP section 5)."""

    INSTANT = "instant"
    """A closed form: microseconds to milliseconds."""
    LIGHT = "light"
    """Iteration or a modest simulation: well under a second."""
    HEAVY = "heavy"
    """Large simulations or optimisation: a hosted service caps or queues it."""


class ChartKind(StrEnum):
    """The kinds of chart a :class:`ChartSpec` can ask for."""

    LINE = "line"
    BAR = "bar"
    SCATTER = "scatter"
    BAND = "band"
    """A shaded band between the first two ``y`` fields (lower, then upper),
    with any further ``y`` fields drawn as lines over it: a fan chart."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Reference:
    """A source a model rests on.

    ROADMAP section 4 2.2 asks for a DOI or URL plus a page or table, so a
    reader can find the passage. A citation never copies a source's text.
    """

    key: str
    """A short unique label, such as ``fisher1930``."""
    citation: str
    """The reference in full: authors, year, title, publisher."""
    doi: str | None = None
    """The DOI, such as ``10.2307/2975974``."""
    url: str | None = None
    """An ``http`` or ``https`` link."""
    locator: str | None = None
    """Where in the source: a page, table, section, equation or chapter."""
    isbn: str | None = None
    """The ISBN of a book."""


@dataclass(frozen=True, slots=True, kw_only=True)
class Invariant:
    """A property the model guarantees for every valid input.

    Step 5's harness holds each invariant to a property test.
    """

    id: str
    """A snake_case id, unique within the model."""
    statement: str
    """The property, in plain words."""


def _read_only(inputs: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(inputs))


@dataclass(frozen=True, slots=True, kw_only=True)
class Example:
    """A worked input a model must accept and run.

    For a model with several calculations, ``inputs`` carries the
    ``calculation`` that selects one.
    """

    name: str
    """A snake_case name, unique within the model."""
    inputs: Mapping[str, object]
    """Field values as a caller would pass them."""
    note: str | None = None
    """What the example shows."""

    def __post_init__(self) -> None:
        """Keep a read-only copy of ``inputs``."""
        object.__setattr__(self, "inputs", _read_only(self.inputs))


@dataclass(frozen=True, slots=True, kw_only=True)
class ChartSpec:
    """A chart of a model's array outputs, rendered by ``Result.plot()``."""

    id: str
    """A snake_case id, unique within the model."""
    title: str
    kind: ChartKind
    x: str
    """The output field plotted on the horizontal axis."""
    y: tuple[str, ...]
    """The output fields plotted on the vertical axis."""
    x_label: str | None = None
    y_label: str | None = None
    calculation: str | None = None
    """The calculation the chart belongs to, for a model with several."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ChangelogEntry:
    """One line of a model's history."""

    version: int
    """The model version the entry describes."""
    note: str
    """What changed, and why a number moved if one did."""


@dataclass(frozen=True, slots=True)
class Alias:
    """A retired id that still resolves to a model, with a warning (ADR-0003)."""

    id: str
    removed_in: str = DEFAULT_ALIAS_REMOVAL
    """The release that removes the alias: a major release."""


def _as_tuple(value: Iterable[object] | str) -> tuple[object, ...]:
    """Turn a list into a tuple, and a lone string into a one-item tuple."""
    if isinstance(value, str):
        return (value,)
    return tuple(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class ModelSpec:
    """Everything a registered model declares about itself.

    Nothing is checked when a specification is built; ``registry.validate()``
    rejects an incomplete one, naming the model and the rule.
    """

    id: str
    """The permanent dotted id (ADR-0003), such as ``fixed_income.duration``."""
    version: int
    """Starts at 1 and goes up whenever outputs for some valid input change, or
    a schema changes."""
    title: str
    summary: str
    inputs: object
    """The input model, or a discriminated union of them on ``calculation``."""
    outputs: object
    """The output model, or a discriminated union matching the inputs."""
    tags: tuple[str, ...] = ()
    formula: tuple[str, ...] = ()
    """One or more LaTeX strings."""
    assumptions: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    references: tuple[Reference, ...] = ()
    evidence: Evidence | None = None
    cost: CostClass | None = None
    invariants: tuple[Invariant, ...] = ()
    no_invariants_reason: str | None = None
    """Why the model declares no invariant, when it declares none."""
    examples: tuple[Example, ...] = ()
    charts: tuple[ChartSpec, ...] = ()
    aliases: tuple[Alias, ...] = ()
    changelog: tuple[ChangelogEntry, ...] = ()
    bindings: tuple[Binding, ...] = ()
    """The data that fills input fields, grouped into profiles; empty for a model
    that reads no data (ADR-0011 decision 16)."""
    extra: str | None = None
    """The pyeconomics extra whose library ``compute`` imports, or ``None``."""

    def __post_init__(self) -> None:
        """Hold every sequence as a tuple, and every alias as an :class:`Alias`."""
        for name in (
            "tags",
            "formula",
            "assumptions",
            "limitations",
            "references",
            "invariants",
            "examples",
            "charts",
            "changelog",
            "bindings",
        ):
            object.__setattr__(self, name, _as_tuple(getattr(self, name)))
        aliases = tuple(
            Alias(id=a) if isinstance(a, str) else a for a in _as_tuple(self.aliases)
        )
        object.__setattr__(self, "aliases", aliases)

    @property
    def domain(self) -> str:
        """The first segment of the id."""
        return self.id.partition(".")[0]

    @property
    def input_models(self) -> tuple[object, ...]:
        """The input model, or the members of the input union."""
        return union_members(self.inputs)

    @property
    def output_models(self) -> tuple[object, ...]:
        """The output model, or the members of the output union."""
        return union_members(self.outputs)


def union_members(annotation: object) -> tuple[object, ...]:
    """Return the members of a union annotation, or the type itself.

    ``Annotated`` wrappers are looked through, so ``Annotated[A | B,
    Field(discriminator="calculation")]`` gives ``(A, B)``.

    Examples
    --------
    >>> union_members(int), union_members(int | str)
    ((<class 'int'>,), (<class 'int'>, <class 'str'>))
    """
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    if get_origin(annotation) in {Union, types.UnionType}:
        return get_args(annotation)
    return (annotation,)


def union_discriminator(annotation: object) -> str | None:
    """Return the discriminator an ``Annotated`` union names, if any.

    Examples
    --------
    >>> from typing import Annotated
    >>> from pydantic import Field
    >>> union_discriminator(Annotated[int | str, Field(discriminator="kind")])
    'kind'
    >>> union_discriminator(int) is None
    True
    """
    if get_origin(annotation) is not Annotated:
        return None
    for metadata in get_args(annotation)[1:]:
        if isinstance(metadata, FieldInfo) and isinstance(metadata.discriminator, str):
            return metadata.discriminator
    return None
