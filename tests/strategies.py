# tests/strategies.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Hypothesis strategies that generate valid inputs for any registered model.

:func:`inputs` reads a model's input fields (their unit markers, bounds, maximum
lengths, enums and literals) and returns a strategy of input mappings the model
accepts, one per draw, ready for ``run_model(model, mapping)``. For a model with
several calculations it draws a member of the union, with its ``calculation``
tag. The strategy also draws the model's own examples now and then, so a
realistic input is always in the mix.

Arrays are drawn short (at most :data:`MAX_ITEMS` items, or the field's minimum
length when that is larger) so a contract run stays fast; the bound a field
declares is the one ``registry.validate()`` already holds it to.

A bound on one field cannot say that two fields must agree (a strike below a
spot, an end after a start). When a model validates across fields, register a
strategy for it in :data:`OVERRIDES`; the contract suite then draws from that.
"""

from __future__ import annotations

import datetime as dt
import enum
import importlib
import math
import string
import types
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Final,
    Literal,
    TypeAliasType,
    Union,
    get_args,
    get_origin,
)

import annotated_types as at
from hypothesis import strategies as st
from pydantic import BaseModel
from pydantic.fields import FieldInfo

from pyeconomics.core import DEFAULT_BOUNDS, DEFAULT_DATE_BOUNDS, Unit, UnitKind
from pyeconomics.core.units import MAX_STRING_LENGTH

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Mapping, Sequence

    from hypothesis.strategies import SearchStrategy

    from pyeconomics.core import Model

__all__ = ["MAX_ITEMS", "MAX_TEXT", "OVERRIDES", "inputs"]

#: The most items a generated array holds, unless the field needs more.
MAX_ITEMS: Final = 12

#: The most characters a generated string holds.
MAX_TEXT: Final = 12

#: Strategies for models whose inputs a field-by-field draw cannot make valid,
#: keyed by model id. Each returns a strategy of input mappings.
OVERRIDES: Final[dict[str, Callable[[], SearchStrategy[dict[str, Any]]]]] = {}

_TEXT_ALPHABET: Final = string.ascii_letters + string.digits + " _-"
_FALLBACK_BOUND: Final = 1e6


@dataclass(frozen=True, slots=True)
class _Limits:
    """What a field's metadata says about its values."""

    low: Any = None
    high: Any = None
    low_open: bool = False
    high_open: bool = False
    min_length: int | None = None
    max_length: int | None = None
    pattern: str | None = None
    unit: UnitKind | None = None


def _flatten(metadata: Iterable[object]) -> list[object]:
    """Expand ``Field(...)`` objects and grouped constraints into their parts."""
    flat: list[object] = []
    for item in metadata:
        if isinstance(item, FieldInfo):
            flat.extend(_flatten(item.metadata))
        elif isinstance(item, at.GroupedMetadata):
            flat.extend(_flatten(item))
        else:
            flat.append(item)
    return flat


def _limits(metadata: Sequence[object]) -> _Limits:
    """Read the tightest bounds, lengths, pattern and unit out of the metadata."""
    lows: list[tuple[Any, bool]] = [
        (m.ge, False) for m in metadata if isinstance(m, at.Ge)
    ]
    lows += [(m.gt, True) for m in metadata if isinstance(m, at.Gt)]
    highs: list[tuple[Any, bool]] = [
        (m.le, False) for m in metadata if isinstance(m, at.Le)
    ]
    highs += [(m.lt, True) for m in metadata if isinstance(m, at.Lt)]
    low, low_open = max(lows, key=lambda b: (b[0], b[1]), default=(None, False))
    high, high_open = min(highs, key=lambda b: (b[0], not b[1]), default=(None, False))
    mins = [m.min_length for m in metadata if isinstance(m, at.MinLen)]
    maxes = [m.max_length for m in metadata if isinstance(m, at.MaxLen)]
    patterns = [p for m in metadata if (p := getattr(m, "pattern", None)) is not None]
    units = [m.kind for m in metadata if isinstance(m, Unit)]
    return _Limits(
        low=low,
        high=high,
        low_open=low_open,
        high_open=high_open,
        min_length=max(mins) if mins else None,
        max_length=min(maxes) if maxes else None,
        pattern=str(patterns[-1]) if patterns else None,
        unit=units[-1] if units else None,
    )


def _range(limits: _Limits) -> tuple[Any, Any]:
    """Return the field's bounds, filling a missing end from its unit's defaults."""
    low, high = limits.low, limits.high
    default = DEFAULT_BOUNDS.get(limits.unit) if limits.unit is not None else None
    if default is not None:
        low = default.lower if low is None else low
        high = default.upper if high is None else high
    return (
        -_FALLBACK_BOUND if low is None else low,
        _FALLBACK_BOUND if high is None else high,
    )


def _float(limits: _Limits) -> SearchStrategy[float]:
    low, high = _range(limits)
    return st.floats(
        min_value=float(low),
        max_value=float(high),
        exclude_min=limits.low_open,
        exclude_max=limits.high_open,
        allow_nan=False,
        allow_infinity=False,
        allow_subnormal=False,
    )


def _integer(limits: _Limits) -> SearchStrategy[int]:
    low, high = _range(limits)
    smallest = math.ceil(low)
    if limits.low_open and smallest == low:
        smallest += 1
    largest = math.floor(high)
    if limits.high_open and largest == high:
        largest -= 1
    return st.integers(min_value=smallest, max_value=largest)


def _date(limits: _Limits) -> SearchStrategy[dt.date]:
    low = limits.low if isinstance(limits.low, dt.date) else DEFAULT_DATE_BOUNDS.lower
    high = (
        limits.high if isinstance(limits.high, dt.date) else DEFAULT_DATE_BOUNDS.upper
    )
    if limits.low_open:
        low += dt.timedelta(days=1)
    if limits.high_open:
        high -= dt.timedelta(days=1)
    return st.dates(min_value=low, max_value=high)


def _text(limits: _Limits) -> SearchStrategy[str]:
    if limits.pattern is not None:
        return st.from_regex(limits.pattern, fullmatch=True)
    smallest = limits.min_length or 0
    largest = max(smallest, min(limits.max_length or MAX_STRING_LENGTH, MAX_TEXT))
    return st.text(alphabet=_TEXT_ALPHABET, min_size=smallest, max_size=largest)


def _sizes(limits: _Limits) -> tuple[int, int]:
    smallest = limits.min_length or 0
    return smallest, max(smallest, min(limits.max_length or MAX_ITEMS, MAX_ITEMS))


def _unwrap(annotation: object, metadata: list[object]) -> tuple[object, list[object]]:
    """Strip ``Annotated`` wrappers and type aliases, gathering their metadata."""
    while True:
        if isinstance(annotation, TypeAliasType):
            annotation = annotation.__value__
        elif get_origin(annotation) is Annotated:
            args = get_args(annotation)
            annotation = args[0]
            metadata = [*metadata, *_flatten(args[1:])]
        else:
            return annotation, metadata


def _array(annotation: object, limits: _Limits) -> SearchStrategy[Any]:
    args = get_args(annotation)
    if len(args) == 2 and args[1] is Ellipsis:
        smallest, largest = _sizes(limits)
        return st.lists(_strategy(args[0], []), min_size=smallest, max_size=largest)
    return st.tuples(*(_strategy(arg, []) for arg in args))


def _mapping(annotation: object, limits: _Limits) -> SearchStrategy[Any]:
    key, value = get_args(annotation) or (str, str)
    _, largest = _sizes(limits)
    return st.dictionaries(
        _strategy(key, []), _strategy(value, []), max_size=min(largest, 4)
    )


_SCALARS: Final[dict[object, Callable[[_Limits], SearchStrategy[Any]]]] = {
    bool: lambda _: st.booleans(),
    int: _integer,
    float: _float,
    str: _text,
    dt.date: _date,
}


def _structured(
    annotation: object, origin: object, limits: _Limits
) -> SearchStrategy[Any]:
    """Build a strategy for a literal, an enum, a container or a nested model."""
    if origin is Literal:
        return st.sampled_from(get_args(annotation))
    if isinstance(annotation, type) and issubclass(annotation, enum.Enum):
        return st.sampled_from([member.value for member in annotation])
    if annotation is tuple or origin is tuple:
        return _array(annotation, limits)
    if annotation is dict or origin is dict:
        return _mapping(annotation, limits)
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return _fields(annotation)
    msg = f"no strategy for the type {annotation!r}"
    raise TypeError(msg)


def _strategy(annotation: object, metadata: Sequence[object]) -> SearchStrategy[Any]:
    """Build a strategy for one annotation and the metadata that applies to it."""
    annotation, collected = _unwrap(annotation, list(metadata))
    origin = get_origin(annotation)
    if origin in {Union, types.UnionType}:
        return st.one_of(
            *(
                st.none() if member is type(None) else _strategy(member, collected)
                for member in get_args(annotation)
            )
        )
    limits = _limits(collected)
    builder = _SCALARS.get(annotation)
    if builder is not None:
        return builder(limits)
    return _structured(annotation, origin, limits)


def _fields(cls: type[BaseModel]) -> SearchStrategy[dict[str, Any]]:
    """Draw a mapping of field values for one input model."""
    required: dict[str, SearchStrategy[Any]] = {}
    optional: dict[str, SearchStrategy[Any]] = {}
    for name, info in cls.model_fields.items():
        key = info.alias or name
        strategy = _strategy(info.annotation, _flatten(info.metadata))
        # A one-value Literal is a discriminator tag: a union needs it present.
        is_tag = (
            get_origin(info.annotation) is Literal
            and len(get_args(info.annotation)) == 1
        )
        (required if info.is_required() or is_tag else optional)[key] = strategy
    return st.fixed_dictionaries(required, optional=optional)


def inputs(model: Model[Any, Any]) -> SearchStrategy[Mapping[str, Any]]:
    """Return a strategy of valid input mappings for ``model``.

    A model listed in :data:`OVERRIDES` draws from its own strategy. Otherwise
    the draw follows each field's declared bounds, lengths and enums, picks a
    member of a discriminated union, and sometimes returns one of the model's
    examples.

    Raises
    ------
    TypeError
        If a field has a type no strategy covers; ``registry.validate()`` already
        rejects such a field, so this means the model is not valid.
    """
    override = OVERRIDES.get(model.id)
    if override is not None:
        return override()
    generated = st.one_of(
        *(
            _fields(member)
            for member in model.spec.input_models
            if isinstance(member, type) and issubclass(member, BaseModel)
        )
    )
    examples = [dict(example.inputs) for example in model.spec.examples]
    return st.one_of(generated, st.sampled_from(examples)) if examples else generated


# --- overrides for catalog models with rules between fields ---------------------


def _drop_none(annotation: object) -> object:
    """Return a nullable annotation without its ``None`` member."""
    annotation, _ = _unwrap(annotation, [])
    if get_origin(annotation) in {Union, types.UnionType}:
        members = [m for m in get_args(annotation) if m is not type(None)]
        return members[0] if len(members) == 1 else annotation
    return annotation


def _field(cls: type[BaseModel], name: str) -> SearchStrategy[Any]:
    """Draw one field's value, never ``None``."""
    info = cls.model_fields[name]
    return _strategy(_drop_none(info.annotation), _flatten(info.metadata))


@st.composite
def _one_omitted(
    draw: st.DrawFn, cls: type[BaseModel], names: Sequence[str]
) -> dict[str, Any]:
    """Draw ``cls``'s inputs with exactly one of ``names`` left out."""
    omitted = draw(st.sampled_from(names))
    drawn = draw(_fields(cls))
    for name in names:
        drawn.pop(name, None)
        if name != omitted:
            drawn[name] = draw(_field(cls, name))
    return drawn


@st.composite
def _same_length(
    draw: st.DrawFn, cls: type[BaseModel], names: Sequence[str]
) -> dict[str, Any]:
    """Draw ``cls``'s inputs with the arrays ``names`` all of one length."""
    drawn = draw(_fields(cls))
    first = cls.model_fields[names[0]]
    limits = _limits(_flatten(first.metadata))
    size = draw(st.integers(*_sizes(limits)).filter(lambda n: n >= 1))
    for name in names:
        info = cls.model_fields[name]
        annotation, _ = _unwrap(info.annotation, [])
        item = get_args(annotation)[0]
        drawn[name] = draw(st.lists(_strategy(item, []), min_size=size, max_size=size))
    return drawn


def _time_value() -> SearchStrategy[dict[str, Any]]:
    """``foundations.time_value``: solve omits one key; dated flows need dates."""
    # The package exports the Model under the module's name, so import by path.
    module = importlib.import_module("pyeconomics.models.foundations.time_value")
    tv = module.time_value
    special = {module.SolveInputs, module.XnpvInputs, module.XirrInputs}
    plain = [
        _fields(member)
        for member in tv.spec.input_models
        if isinstance(member, type)
        and issubclass(member, BaseModel)
        and member not in special
    ]
    return st.one_of(
        *plain,
        _one_omitted(
            module.SolveInputs,
            ("periods", "rate", "present_value", "payment", "future_value"),
        ),
        _same_length(module.XnpvInputs, ("cash_flows", "dates")),
        _same_length(module.XirrInputs, ("cash_flows", "dates")),
        st.sampled_from([dict(example.inputs) for example in tv.spec.examples]),
    )


OVERRIDES["foundations.time_value"] = _time_value


# --- fixed income: dates that describe a bond, curves, calls ----------------------

_BOND_EARLIEST: Final = dt.date(1902, 1, 1)
_BOND_LATEST: Final = DEFAULT_DATE_BOUNDS.upper


def _accepts(cls: type[BaseModel]) -> Callable[[dict[str, Any]], bool]:
    """Return a filter that keeps the mappings ``cls`` validates."""

    def accepted(drawn: dict[str, Any]) -> bool:
        try:
            cls.model_validate(drawn)
        except ValueError:
            return False
        return True

    return accepted


@st.composite
def _increasing(draw: st.DrawFn, low: float, high: float, size: int) -> list[float]:
    """Draw ``size`` strictly increasing values in ``[low, high]``, two places apart."""
    values = draw(
        st.lists(
            st.floats(min_value=low, max_value=high).map(lambda x: round(x, 2)),
            min_size=size,
            max_size=size,
            unique=True,
        )
    )
    return sorted(values)


@st.composite
def _bond(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw ``cls``'s inputs with dates, calls and a curve that fit together."""
    drawn = draw(_fields(cls))
    settlement = draw(
        st.dates(min_value=_BOND_EARLIEST, max_value=dt.date(2190, 12, 31))
    )
    term = draw(st.integers(min_value=1, max_value=36_525))
    maturity = min(settlement + dt.timedelta(days=term), _BOND_LATEST)
    drawn.update(settlement=settlement, maturity=maturity)
    drawn.pop("issue_date", None)
    if draw(st.booleans()):
        before = dt.timedelta(days=draw(st.integers(min_value=0, max_value=800)))
        drawn["issue_date"] = max(settlement - before, _BOND_EARLIEST)
    fields = cls.model_fields
    if "curve_tenors" in fields:
        size = draw(st.integers(min_value=1, max_value=8))
        drawn["curve_tenors"] = draw(_increasing(0.01, 100.0, size))
        drawn["curve_rates"] = draw(
            st.lists(
                st.floats(min_value=-0.1, max_value=1.0), min_size=size, max_size=size
            )
        )
    if "key_tenors" in fields:
        size = draw(st.integers(min_value=1, max_value=6))
        drawn["key_tenors"] = draw(_increasing(0.01, 100.0, size))
    if "call_date" in fields or "call_dates" in fields:
        bonds = importlib.import_module("pyeconomics.models.fixed_income._bonds")
        terms = {k: v for k, v in drawn.items() if k in bonds.BondTerms.model_fields}
        try:
            dates = bonds.payment_dates(bonds.BondTerms.model_validate(terms))
        except ValueError:
            dates = (maturity,)
        if "call_date" in fields:
            drawn["call_date"] = draw(st.sampled_from(dates))
        else:
            size = draw(st.integers(min_value=1, max_value=4))
            drawn["call_dates"] = draw(
                st.lists(st.sampled_from(dates), min_size=size, max_size=size)
            )
            drawn["call_prices"] = draw(
                st.lists(
                    st.floats(min_value=1.0, max_value=200.0),
                    min_size=size,
                    max_size=size,
                )
            )
    return drawn


def _fixed_income(model_id: str) -> Callable[[], SearchStrategy[dict[str, Any]]]:
    """A strategy for a fixed-income model whose inputs describe bonds or curves."""

    def strategy() -> SearchStrategy[dict[str, Any]]:
        name = model_id.removeprefix("fixed_income.")
        module = importlib.import_module(f"pyeconomics.models.fixed_income.{name}")
        found = getattr(module, name)
        bonds = importlib.import_module("pyeconomics.models.fixed_income._bonds")
        members = [
            member
            for member in found.spec.input_models
            if isinstance(member, type) and issubclass(member, BaseModel)
        ]
        drawn = [
            (
                _bond(member)
                if issubclass(member, bonds.BondTerms)
                else _fields(member)
            ).filter(_accepts(member))
            for member in members
        ]
        examples = [dict(example.inputs) for example in found.spec.examples]
        return st.one_of(*drawn, st.sampled_from(examples))

    return strategy


for _id in (
    "fixed_income.bond_pricing",
    "fixed_income.curve_bootstrap",
    "fixed_income.duration",
    "fixed_income.convexity",
):
    OVERRIDES[_id] = _fixed_income(_id)


# --- derivatives: swap schedules and curves -----------------------------------


@st.composite
def _curve(draw: st.DrawFn, drawn: dict[str, Any]) -> dict[str, Any]:
    """Give ``drawn`` a zero curve: increasing tenors, one rate for each."""
    size = draw(st.integers(min_value=1, max_value=8))
    drawn["curve_tenors"] = draw(_increasing(0.01, 100.0, size))
    drawn["curve_rates"] = draw(
        st.lists(st.floats(min_value=-0.1, max_value=1.0), min_size=size, max_size=size)
    )
    return drawn


@st.composite
def _dated_swap(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw a dated swap: valuation, start and payment dates in order, a curve."""
    drawn = draw(_fields(cls))
    latest = DEFAULT_DATE_BOUNDS.upper
    valuation = draw(
        st.dates(min_value=DEFAULT_DATE_BOUNDS.lower, max_value=dt.date(2190, 1, 1))
    )
    start = valuation + dt.timedelta(days=draw(st.integers(0, 3_650)))
    gaps = draw(st.lists(st.integers(1, 400), min_size=1, max_size=MAX_ITEMS))
    payments: list[dt.date] = []
    day = start
    for gap in gaps:
        day += dt.timedelta(days=gap)
        if day > latest:
            break
        payments.append(day)
    drawn.update(
        valuation_date=valuation,
        start_date=start,
        payment_dates=payments or [min(start + dt.timedelta(days=1), latest)],
    )
    return draw(_curve(drawn))


def _interest_rate_swap() -> SearchStrategy[dict[str, Any]]:
    """``derivatives.interest_rate_swap``: equal lengths, ordered dates, curves."""
    module = importlib.import_module(
        "pyeconomics.models.derivatives.interest_rate_swap"
    )
    swap = module.interest_rate_swap
    return st.one_of(
        _same_length(module.DiscountFactorInputs, ("accruals", "discount_factors")),
        _fields(module.ZeroCurveInputs).flatmap(_curve),
        _dated_swap(module.DatedInputs).filter(_accepts(module.DatedInputs)),
        st.sampled_from([dict(example.inputs) for example in swap.spec.examples]),
    )


OVERRIDES["derivatives.interest_rate_swap"] = _interest_rate_swap
