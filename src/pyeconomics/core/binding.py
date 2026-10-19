# src/pyeconomics/core/binding.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Data bindings: which data fills a model's input fields (ADR-0011 decision 16).

A model stays a pure function. What it declares is a :class:`Binding`: an input
field, the catalog concept that can fill it, an optional transform, the rule
that picks the observation (or window of observations) at the evaluation date,
and the vintage policy. Bindings group into named *profiles*, each one complete
set (``default`` is required): realized data, a forecast source, another
economy. The declarations are plain data, so a model can carry them and
``registry.validate()`` can check their structure without core importing the
data layer; resolving a profile is :func:`pyeconomics.bind`, which lives in
:mod:`pyeconomics.data.bindings` and returns a :class:`Bound`.

A :class:`Bound` is what ``bind`` hands to ``run``: the values by input field,
the profile, and one :class:`~pyeconomics.core.provenance.DataSource` record per
bound field. A field the caller supplied instead of reading is recorded as
user-supplied, and a field read as revised data (a source that keeps no
vintages, or a policy that asks for the latest) carries the ``revised_data``
warning code: nothing passes revised data off as real-time.

Neither class can hold a credential, a request URL, a host or a path.

Examples
--------
>>> from pyeconomics.core.binding import AsOf, Binding, VintagePolicy
>>> binding = Binding("unemployment", "us.unemployment.rate")
>>> binding.as_of is AsOf.LAST_ON_OR_BEFORE, binding.vintage is VintagePolicy.REAL_TIME
(True, True)
>>> binding.to_dict()["profile"]
'default'

"""

from __future__ import annotations

import re
import types
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Annotated,
    Final,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
)

from pydantic import BaseModel

from pyeconomics.core import _fields as f
from pyeconomics.core._annotations import flatten, max_length
from pyeconomics.core.provenance import (
    DATA_DATE_BOUNDS,
    DataSource,
    LicenceClass,
    LlmUse,
)
from pyeconomics.core.spec import (
    CALCULATION_FIELD,
    union_discriminator,
    union_members,
)
from pyeconomics.core.units import Unit, UnitKind

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Mapping

__all__ = [
    "DEFAULT_PROFILE",
    "REVISED_DATA",
    "USER_PROVIDER",
    "AsOf",
    "Binding",
    "Bound",
    "CandidateNote",
    "FieldShape",
    "VintagePolicy",
    "calculations",
    "field_shapes",
    "user_supplied",
]

#: The profile every bound model must declare.
DEFAULT_PROFILE: Final = "default"

#: The warning code of data that is not what was published at the evaluation date.
REVISED_DATA: Final = "revised_data"

#: The provider id of a value the caller supplied instead of reading.
USER_PROVIDER: Final = "user"

#: The most records one bound set holds (one per bound field).
_MAX_SOURCES: Final = 256
_PROFILE: Final = re.compile(r"[a-z][a-z0-9_]*")
_UNIONS: Final = (Union, types.UnionType)


class AsOf(StrEnum):
    """How a binding picks its value at the evaluation date.

    Each rule is one of the alignment transforms of
    :mod:`pyeconomics.core.transforms`, so a record shows the rule that ran.
    """

    LAST_ON_OR_BEFORE = "last_on_or_before"
    """The last observation on or before the date (``asof``)."""
    PERIOD = "period"
    """The observation of the period that contains the date (``period``)."""
    WINDOW = "window"
    """The last ``window`` observations on or before the date, for an array
    field (``window``)."""


class VintagePolicy(StrEnum):
    """Which published version of the data a binding reads."""

    REAL_TIME = "real_time"
    """The values as published by the evaluation date, wherever the source keeps
    vintages. A source that keeps none is read as revised data, and says so."""
    LATEST = "latest"
    """The latest values, which are revised data and are labelled as such."""


@dataclass(frozen=True, slots=True)
class Binding:
    """One input field's data: a catalog concept, a rule and a vintage policy.

    Nothing is checked when a binding is built, as for the rest of a model's
    specification: ``registry.validate()`` reports a field that does not exist,
    a field bound twice in one profile, a window on a scalar field (or an array
    without one), a missing ``default`` profile, a concept id outside the
    grammar and a transform the vocabulary does not declare.

    Examples
    --------
    >>> Binding(
    ...     "inflation",
    ...     "us.inflation.cpi.yoy",
    ...     as_of=AsOf.PERIOD,
    ...     vintage=VintagePolicy.LATEST,
    ...     profile="realized",
    ... ).as_of.value
    'period'
    """

    field: str
    """The model input field the data fills."""
    concept: str
    """The catalog concept id (``us.inflation.cpi.yoy``)."""
    transform: str | None = None
    """One more transform, applied to the resolved series before the as-of rule,
    written as :mod:`pyeconomics.core.transforms` does."""
    as_of: AsOf = AsOf.LAST_ON_OR_BEFORE
    window: int | None = None
    """The number of observations of an :attr:`AsOf.WINDOW` binding."""
    vintage: VintagePolicy = VintagePolicy.REAL_TIME
    profile: str = DEFAULT_PROFILE
    """The named set of bindings this one belongs to."""

    def to_dict(self) -> dict[str, object]:
        """Return the binding as JSON-ready values; every key is always present."""
        return {
            "field": self.field,
            "concept": self.concept,
            "transform": self.transform,
            "as_of": getattr(self.as_of, "value", self.as_of),
            "window": self.window,
            "vintage": getattr(self.vintage, "value", self.vintage),
            "profile": self.profile,
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateNote:
    """One source that can fill a concept, as a model's card describes it.

    The card is built in core, which cannot read the catalog, so the data layer
    supplies these (:func:`pyeconomics.data.bindings.candidate_notes`).
    """

    provider: str
    """The provider id, or ``derived`` for a concept built from two others."""
    licence: LicenceClass | None
    """The provider's licence class; ``None`` for a derived candidate."""
    attribution: str | None = None
    notice: str | None = None
    """The notice the source requires wherever its data appears."""


def user_supplied(field: str, *, concept: str | None = None) -> DataSource:
    """Return the record of a field's value the caller supplied.

    The record names the field (and the concept it replaces), never the value:
    the value is an input, and the manifest already fingerprints the inputs.

    Examples
    --------
    >>> record = user_supplied("short_rate", concept="us.fed_funds.target_upper")
    >>> record.provider, record.licence.value, record.retrieved_at
    ('user', 'user-supplied', None)
    """
    return DataSource(
        provider=USER_PROVIDER,
        series_id="override",
        concept=concept,
        field=field,
        licence=LicenceClass.USER_SUPPLIED,
        attribution="Value supplied by the caller.",
        llm_use=LlmUse.ALLOWED,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class Bound:
    """A model's inputs read from data, with the record of every source.

    ``values`` holds the input fields by name: a float, or a tuple of floats for
    an array field, in the field's own unit. ``sources`` holds one record per
    bound field, sorted by field. Run it with ``pyeconomics.run(model_id,
    bound)``; the result's manifest carries the records.

    Examples
    --------
    >>> bound = Bound(
    ...     model_id="macro.toy",
    ...     profile="default",
    ...     values={"rate": 0.05},
    ...     sources=(user_supplied("rate"),),
    ... )
    >>> bound.values["rate"], bound.overridden, bound.revised
    (0.05, ('rate',), ())
    """

    model_id: str
    """The model the values were bound for; ``run`` refuses any other."""
    profile: str
    values: Mapping[str, object]
    sources: tuple[DataSource, ...] = ()
    as_of: dt.date | None = None
    """The evaluation date, or ``None`` for the latest data."""

    def __post_init__(self) -> None:
        """Check the parts; hold the values read-only and the records sorted."""
        f.text(self.model_id, "model_id")
        if not _PROFILE.fullmatch(f.text(self.profile, "profile")):
            msg = f"profile {self.profile!r} is not a snake_case name"
            raise f.fail(msg)
        values = f.mapping(self.values, "the bound values", tuple(self.values))
        for name in values:
            f.identifier(name, "a bound field")
        items = f.sequence(self.sources, "sources", max_items=_MAX_SOURCES)
        records = tuple(f.instance(item, DataSource, "a source") for item in items)
        f.optional_day(self.as_of, "as_of", DATA_DATE_BOUNDS)
        ordered = MappingProxyType(dict(sorted(values.items())))
        object.__setattr__(self, "values", ordered)
        object.__setattr__(
            self, "sources", tuple(sorted(records, key=lambda r: r.field or ""))
        )

    @property
    def overridden(self) -> tuple[str, ...]:
        """The fields whose value the caller supplied instead of reading."""
        return tuple(
            source.field
            for source in self.sources
            if source.provider == USER_PROVIDER and source.field is not None
        )

    @property
    def revised(self) -> tuple[str, ...]:
        """The fields read as revised data rather than as published by the date."""
        return tuple(
            source.field
            for source in self.sources
            if REVISED_DATA in source.warnings and source.field is not None
        )

    def to_dict(self) -> dict[str, object]:
        """Return the bound values and their records as JSON-ready values."""
        return {
            "model_id": self.model_id,
            "profile": self.profile,
            "as_of": None if self.as_of is None else self.as_of.isoformat(),
            "values": {
                name: list(value) if isinstance(value, tuple) else value
                for name, value in self.values.items()
            },
            "data_sources": [source.to_dict() for source in self.sources],
        }


# --- reading a model's input fields ------------------------------------------------


@dataclass(frozen=True, slots=True)
class FieldShape:
    """What a binding needs to know about one input field."""

    kind: UnitKind | None
    """The unit kind of the field, or of an array field's items."""
    array: bool
    """Whether the field is a tuple (it takes a window)."""
    max_length: int | None = None
    """An array field's declared maximum length."""


def _shape(tp: object, metadata: list[object]) -> FieldShape:
    """Read one annotation's unit kind and whether it is an array."""
    while get_origin(tp) is Annotated or isinstance(tp, TypeAliasType):
        if isinstance(tp, TypeAliasType):
            tp = tp.__value__
            continue
        args = get_args(tp)
        tp = args[0]
        metadata = [*metadata, *flatten(args[1:])]
    origin = get_origin(tp)
    if origin in _UNIONS:
        members = [member for member in get_args(tp) if member is not type(None)]
        return (
            _shape(members[0], metadata)
            if members
            else FieldShape(kind=None, array=False)
        )
    if tp is tuple or origin is tuple:
        args = get_args(tp)
        inner = _shape(args[0], []) if args else FieldShape(kind=None, array=False)
        return FieldShape(kind=inner.kind, array=True, max_length=max_length(metadata))
    units = [item for item in metadata if isinstance(item, Unit)]
    return FieldShape(kind=units[-1].kind if units else None, array=False)


def calculations(inputs: object) -> dict[str, type[BaseModel]]:
    """Map each calculation of a union of inputs to the input model it takes.

    A model whose inputs are one model, not a union on ``calculation``, gives an
    empty mapping. A bind of a union model reads only the fields of the
    calculation the caller names, so a profile can serve every calculation.

    Examples
    --------
    >>> from typing import Annotated, Literal
    >>> from pydantic import Field
    >>> from pyeconomics.core import Rate
    >>> from pyeconomics.core.model import ModelInputs
    >>> class A(ModelInputs):
    ...     calculation: Literal["a"] = Field("a", description="A")
    ...     rate: Rate = Field(ge=0, le=1, description="A rate")
    >>> class B(ModelInputs):
    ...     calculation: Literal["b"] = Field("b", description="B")
    >>> family = calculations(Annotated[A | B, Field(discriminator="calculation")])
    >>> sorted(family["a"].model_fields), sorted(family["b"].model_fields)
    (['calculation', 'rate'], ['calculation'])
    >>> calculations(A)
    {}
    """
    if union_discriminator(inputs) != CALCULATION_FIELD:
        return {}
    found: dict[str, type[BaseModel]] = {}
    for member in union_members(inputs):
        if not (isinstance(member, type) and issubclass(member, BaseModel)):
            continue  # pragma: no cover - registry.validate() refuses such a union
        tag = member.model_fields.get(CALCULATION_FIELD)
        if tag is not None and isinstance(tag.default, str):
            found[tag.default] = member
    return found


def field_shapes(inputs: object) -> dict[str, tuple[FieldShape, ...]]:
    """Describe every field of an input model, or of each member of a union.

    A field appears once per member that declares it, so a family of
    calculations that shares a field gives one entry for each.

    Examples
    --------
    >>> from pydantic import Field, create_model
    >>> from pyeconomics.core import Rate, RateArray
    >>> from pyeconomics.core.model import ModelInputs
    >>> Inputs = create_model(
    ...     "Inputs",
    ...     __base__=ModelInputs,
    ...     rate=(Rate, Field(ge=0, le=1, description="A rate")),
    ...     path=(RateArray, Field(max_length=8, description="A path")),
    ... )
    >>> shapes = field_shapes(Inputs)
    >>> shapes["rate"][0].array, shapes["path"][0].array, shapes["path"][0].max_length
    (False, True, 8)
    """
    found: dict[str, list[FieldShape]] = {}
    for member in union_members(inputs):
        if not (isinstance(member, type) and issubclass(member, BaseModel)):
            continue
        for name, info in member.model_fields.items():
            shape = _shape(info.annotation, flatten(info.metadata))
            found.setdefault(name, []).append(shape)
    return {name: tuple(shapes) for name, shapes in found.items()}
