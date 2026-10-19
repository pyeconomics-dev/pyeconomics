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


# --- portfolio: square matrices, distributions, one Kelly form ------------------


@st.composite
def _correlations(draw: st.DrawFn, size: int) -> list[list[float]]:
    """Draw a correlation matrix: usually positive definite, sometimes not."""
    if draw(st.integers(0, 9)) == 0:
        # A symmetric matrix of arbitrary correlations, rarely positive definite.
        cells = st.floats(min_value=-1.0, max_value=1.0)
        rows = [[1.0] * size for _ in range(size)]
        for i in range(size):
            for j in range(i + 1, size):
                rows[i][j] = rows[j][i] = draw(cells)
        return rows
    loadings = [
        draw(st.lists(st.floats(-1.0, 1.0), min_size=2, max_size=2))
        for _ in range(size)
    ]
    noise = draw(st.lists(st.floats(0.05, 1.0), min_size=size, max_size=size))
    raw = [
        [
            sum(a * b for a, b in zip(loadings[i], loadings[j], strict=True))
            + (noise[i] if i == j else 0.0)
            for j in range(size)
        ]
        for i in range(size)
    ]
    scale = [math.sqrt(raw[i][i]) for i in range(size)]
    return [
        [
            1.0 if i == j else max(-1.0, min(1.0, raw[i][j] / (scale[i] * scale[j])))
            for j in range(size)
        ]
        for i in range(size)
    ]


@st.composite
def _assets(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw ``cls``'s inputs with expected returns and a matching risk matrix."""
    drawn = draw(_fields(cls))
    size = draw(st.integers(min_value=1, max_value=6))
    for name in ("covariance", "volatilities", "correlations", "weights"):
        drawn.pop(name, None)
    drawn["expected_returns"] = draw(
        st.lists(
            st.one_of(st.floats(-0.5, 0.5), st.floats(-1.0, 100.0)),
            min_size=size,
            max_size=size,
        )
    )
    vols = draw(
        st.lists(
            st.one_of(st.floats(0.01, 1.0), st.floats(1e-6, 10.0)),
            min_size=size,
            max_size=size,
        )
    )
    correlations = draw(_correlations(size))
    if draw(st.booleans()):
        drawn["volatilities"], drawn["correlations"] = vols, correlations
    else:
        drawn["covariance"] = [
            [correlations[i][j] * vols[i] * vols[j] for j in range(size)]
            for i in range(size)
        ]
    if "weights" in cls.model_fields:
        drawn["weights"] = draw(
            st.lists(st.floats(-100.0, 100.0), min_size=size, max_size=size)
        )
    return drawn


def _mean_variance() -> SearchStrategy[dict[str, Any]]:
    """``portfolio.mean_variance``: square matrices that fit the expected returns."""
    module = importlib.import_module("pyeconomics.models.portfolio.mean_variance")
    members = (
        module.PortfolioInputs,
        module.FrontierInputs,
        module.MinimumVarianceInputs,
        module.TangencyInputs,
    )
    return st.one_of(
        *(_assets(member).filter(_accepts(member)) for member in members),
        st.sampled_from(
            [dict(example.inputs) for example in module.mean_variance.spec.examples]
        ),
    )


OVERRIDES["portfolio.mean_variance"] = _mean_variance


@st.composite
def _distribution(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw a gamble: outcomes and probabilities that sum to one."""
    drawn = draw(_fields(cls))
    size = draw(st.integers(min_value=1, max_value=MAX_ITEMS))
    drawn["outcomes"] = draw(
        st.lists(
            st.one_of(st.floats(-1.0, 1.0), st.floats(-1.0, 100.0)),
            min_size=size,
            max_size=size,
        )
    )
    raw = draw(st.lists(st.floats(0.0, 1.0), min_size=size, max_size=size))
    total = sum(raw)
    drawn["probabilities"] = (
        [1.0 / size] * size if total == 0 else [min(p / total, 1.0) for p in raw]
    )
    return drawn


@st.composite
def _kelly(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw a discrete bet or a continuous asset, never a mix of the two."""
    drawn = draw(_fields(cls))
    for name in ("win_probability", "odds", "drift", "volatility", "risk_free_rate"):
        drawn.pop(name, None)
    names: tuple[str, ...]
    if draw(st.booleans()):
        names = ("win_probability", "odds")
    else:
        names = ("drift", "volatility")
        if draw(st.booleans()):
            names = (*names, "risk_free_rate")
    for name in names:
        drawn[name] = draw(_field(cls, name))
    return drawn


def _utility() -> SearchStrategy[dict[str, Any]]:
    """``portfolio.utility``: distributions sum to one; Kelly takes one form."""
    module = importlib.import_module("pyeconomics.models.portfolio.utility")
    return st.one_of(
        _fields(module.MeanVarianceUtilityInputs),
        _fields(module.OptimalRiskyShareInputs),
        _distribution(module.CertaintyEquivalentInputs).filter(
            _accepts(module.CertaintyEquivalentInputs)
        ),
        _kelly(module.KellyInputs),
        st.sampled_from(
            [dict(example.inputs) for example in module.utility.spec.examples]
        ),
    )


OVERRIDES["portfolio.utility"] = _utility


# --- performance: aligned series, flows inside their span, sector matrices -------

#: A long series: compounding over hundreds of periods overflows or rounds a
#: run of losses to -100%, which a dozen periods never reach.
_LONG: Final = st.integers(min_value=100, max_value=800)
#: A return repeated for a whole series: steady losses, steady large gains.
_EXTREME_RUN: Final = st.sampled_from([-0.6, -0.065, 0.5, 1.0, 100.0])


@st.composite
def _dated_flows(
    draw: st.DrawFn, drawn: dict[str, Any], *, required: bool
) -> dict[str, Any]:
    """Give ``drawn`` a start, an end and flows dated between them."""
    start = draw(
        st.dates(min_value=DEFAULT_DATE_BOUNDS.lower, max_value=dt.date(2190, 1, 1))
    )
    end = start + dt.timedelta(days=draw(st.integers(1, 3_650)))
    size = draw(st.integers(0, 6))
    days = (end - start).days
    offsets = draw(st.lists(st.integers(0, days), min_size=size, max_size=size))
    drawn.update(
        start_date=start,
        end_date=end,
        flows=draw(st.lists(st.floats(-1e6, 1e6), min_size=size, max_size=size)),
        flow_dates=[start + dt.timedelta(days=d) for d in sorted(offsets)],
    )
    if not required:
        for name in ("periods", "flow_times", "periods_per_year"):
            drawn.pop(name, None)
    return drawn


@st.composite
def _time_weighted(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw valuations, and one flow per valuation but the last, or none."""
    drawn = draw(_fields(cls))
    size = draw(st.one_of(st.integers(2, MAX_ITEMS), _LONG))
    drawn["values"] = draw(
        st.lists(
            st.one_of(st.floats(50.0, 200.0), st.floats(0.0, 1e12)),
            min_size=size,
            max_size=size,
        )
    )
    drawn["flows"] = []
    if draw(st.booleans()):
        drawn["flows"] = draw(
            st.lists(
                st.one_of(st.floats(-40.0, 40.0), st.floats(-1e12, 1e12)),
                min_size=size - 1,
                max_size=size - 1,
            )
        )
    return drawn


@st.composite
def _periodic_flows(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw a span in periods and flows at times inside it."""
    drawn = draw(_fields(cls))
    for name in ("start_date", "end_date", "flow_dates"):
        drawn.pop(name, None)
    span = draw(st.floats(min_value=0.01, max_value=1_000.0))
    size = draw(st.integers(0, 6))
    drawn.update(
        periods=span,
        flows=draw(st.lists(st.floats(-1e6, 1e6), min_size=size, max_size=size)),
        flow_times=draw(st.lists(st.floats(0.0, span), min_size=size, max_size=size)),
    )
    return drawn


def _return_measurement() -> SearchStrategy[dict[str, Any]]:
    """``performance.return_measurement``: flows fit their values, times or dates."""
    module = importlib.import_module(
        "pyeconomics.models.performance.return_measurement"
    )
    money = module.MoneyWeightedInputs
    dietz = module.ModifiedDietzInputs
    return st.one_of(
        _time_weighted(module.TimeWeightedInputs).filter(
            _accepts(module.TimeWeightedInputs)
        ),
        _periodic_flows(money).filter(_accepts(money)),
        _fields(money)
        .flatmap(lambda d: _dated_flows(d, required=False))
        .filter(_accepts(money)),
        _fields(dietz)
        .flatmap(lambda d: _dated_flows(d, required=True))
        .filter(_accepts(dietz)),
        st.sampled_from(
            [
                dict(example.inputs)
                for example in module.return_measurement.spec.examples
            ]
        ),
    )


OVERRIDES["performance.return_measurement"] = _return_measurement


@st.composite
def _aligned_series(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw portfolio, benchmark and risk-free returns of one length."""
    drawn = draw(_fields(cls))
    size = draw(st.one_of(st.integers(2, MAX_ITEMS), _LONG))
    series = st.one_of(
        st.lists(
            st.one_of(st.floats(-0.2, 0.2), st.floats(-1.0, 100.0)),
            min_size=size,
            max_size=size,
        ),
        _EXTREME_RUN.map(lambda r: [r] * size),
    )
    drawn["returns"] = draw(series)
    drawn["benchmark_returns"] = (
        list(drawn["returns"]) if draw(st.integers(0, 4)) == 0 else draw(series)
    )
    drawn["risk_free_returns"] = draw(series) if draw(st.booleans()) else []
    return drawn


def _risk_adjusted() -> SearchStrategy[dict[str, Any]]:
    """``performance.risk_adjusted``: three series over the same periods."""
    module = importlib.import_module("pyeconomics.models.performance.risk_adjusted")
    return st.one_of(
        _aligned_series(module.RiskAdjustedInputs),
        st.sampled_from(
            [dict(example.inputs) for example in module.risk_adjusted.spec.examples]
        ),
    )


OVERRIDES["performance.risk_adjusted"] = _risk_adjusted


@st.composite
def _sector_weights(draw: st.DrawFn, periods: int, sectors: int) -> list[list[float]]:
    """Draw one row of weights in [0, 1] summing to one for each period."""
    rows = []
    for _ in range(periods):
        raw = draw(st.lists(st.floats(0.0, 1.0), min_size=sectors, max_size=sectors))
        total = sum(raw)
        rows.append(
            [1.0 / sectors] * sectors
            if total == 0
            else [min(w / total, 1.0) for w in raw]
        )
    return rows


@st.composite
def _sectors(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw four matrices of one shape, sometimes a portfolio equal to its benchmark."""
    drawn = draw(_fields(cls))
    periods = draw(st.one_of(st.integers(1, 4), st.integers(30, 60)))
    sectors = draw(st.integers(1, 5))
    returns = st.one_of(
        st.lists(
            st.lists(
                st.one_of(st.floats(-0.3, 0.3), st.floats(-1.0, 100.0)),
                min_size=sectors,
                max_size=sectors,
            ),
            min_size=periods,
            max_size=periods,
        ),
        _EXTREME_RUN.map(lambda r: [[r] * sectors] * periods),
    )
    drawn["portfolio_weights"] = draw(_sector_weights(periods, sectors))
    drawn["benchmark_returns"] = draw(returns)
    if draw(st.integers(0, 4)) == 0:
        drawn["benchmark_weights"] = drawn["portfolio_weights"]
        drawn["portfolio_returns"] = drawn["benchmark_returns"]
    else:
        drawn["benchmark_weights"] = draw(_sector_weights(periods, sectors))
        drawn["portfolio_returns"] = draw(returns)
    return drawn


def _brinson_attribution() -> SearchStrategy[dict[str, Any]]:
    """``performance.brinson_attribution``: one shape; weights sum to one."""
    module = importlib.import_module(
        "pyeconomics.models.performance.brinson_attribution"
    )
    return st.one_of(
        _sectors(module.BhbInputs).filter(_accepts(module.BhbInputs)),
        _sectors(module.BrinsonFachlerInputs).filter(
            _accepts(module.BrinsonFachlerInputs)
        ),
        st.sampled_from(
            [
                dict(example.inputs)
                for example in module.brinson_attribution.spec.examples
            ]
        ),
    )


OVERRIDES["performance.brinson_attribution"] = _brinson_attribution


# --- risk: exception series; econometrics: a design that matches its response --


@st.composite
def _backtest(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw exceptions, or P&L and VaR of one length, sometimes all hits or none."""
    drawn = draw(_fields(cls))
    size = draw(st.one_of(st.integers(2, MAX_ITEMS), _LONG, st.just(250)))
    hits = draw(
        st.one_of(
            st.lists(st.booleans(), min_size=size, max_size=size),
            st.sampled_from([True, False]).map(lambda h: [h] * size),
        )
    )
    for name in ("exceptions", "profit_and_loss", "value_at_risk"):
        drawn.pop(name, None)
    if draw(st.booleans()):
        drawn["exceptions"] = hits
    else:
        var = draw(st.lists(st.floats(0.0, 1e6), min_size=size, max_size=size))
        drawn["value_at_risk"] = var
        drawn["profit_and_loss"] = [
            -2 * v - 1 if hit else v for hit, v in zip(hits, var, strict=True)
        ]
    return drawn


def _var_backtest() -> SearchStrategy[dict[str, Any]]:
    """``risk.var_backtest``: one series, given as exceptions or as P&L and VaR."""
    module = importlib.import_module("pyeconomics.models.risk.var_backtest")
    return st.one_of(
        *(
            _backtest(cls)
            for cls in (
                module.KupiecInputs,
                module.ChristoffersenInputs,
                module.TrafficLightInputs,
            )
        ),
        st.sampled_from(
            [dict(example.inputs) for example in module.var_backtest.spec.examples]
        ),
    )


OVERRIDES["risk.var_backtest"] = _var_backtest

#: Regression values: moderate, extreme, and integers (whose powers are exact).
_REGRESSION_VALUE: Final = st.one_of(
    st.floats(-10.0, 10.0),
    st.floats(-1e15, 1e15),
    st.integers(-20, 20).map(float),
)


@st.composite
def _regression(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """Draw a response and a design of matching rows, sometimes collinear."""
    drawn = draw(_fields(cls))
    width = draw(st.integers(1, 4))
    constant = draw(st.booleans())
    terms = width + int(constant)
    rows = draw(st.one_of(st.integers(terms + 1, terms + 12), _LONG))
    design = [
        draw(st.lists(_REGRESSION_VALUE, min_size=width, max_size=width))
        for _ in range(rows)
    ]
    if width > 1 and draw(st.integers(0, 5)) == 0:
        factor = draw(st.floats(-3.0, 3.0))
        for row in design:
            row[-1] = factor * row[0]
    if draw(st.integers(0, 5)) == 0:
        slope = draw(st.floats(-5.0, 5.0))
        response = [1.0 + slope * row[0] for row in design]
    else:
        response = draw(st.lists(_REGRESSION_VALUE, min_size=rows, max_size=rows))
    drawn.update(
        response=response,
        design=design,
        add_constant=constant,
        names=None,
        hac_lags=draw(st.one_of(st.none(), st.integers(0, rows - 1))),
    )
    return drawn


def _ols() -> SearchStrategy[dict[str, Any]]:
    """``econometrics.ols``: the design's rows match the response."""
    module = importlib.import_module("pyeconomics.models.econometrics.ols")
    return st.one_of(
        _regression(module.OlsInputs).filter(_accepts(module.OlsInputs)),
        st.sampled_from([dict(example.inputs) for example in module.ols.spec.examples]),
    )


OVERRIDES["econometrics.ols"] = _ols


# --- macro: one resource gap, one neutral rate, a previous rate to smooth from ---

_GAP_FIELDS: Final = (
    "gap_measure",
    "output_gap",
    "unemployment",
    "natural_unemployment",
)
_NEUTRAL_FIELDS: Final = ("neutral_real_rate", "neutral_nominal_rate")
_LAGGED_FIELDS: Final = (
    "output_gap_lagged",
    "unemployment_lagged",
    "natural_unemployment_lagged",
)


@st.composite
def _resource_gap(draw: st.DrawFn, cls: type[BaseModel]) -> tuple[dict[str, Any], str]:
    """Draw one resource gap: an output gap, or unemployment and its natural rate."""
    measure = draw(st.sampled_from(["output", "unemployment"]))
    drawn: dict[str, Any] = {}
    if draw(st.booleans()):
        drawn["gap_measure"] = measure
    if measure == "output":
        drawn["output_gap"] = draw(_field(cls, "output_gap"))
    else:
        drawn["unemployment"] = draw(_field(cls, "unemployment"))
        drawn["natural_unemployment"] = draw(_field(cls, "natural_unemployment"))
    return drawn, measure


@st.composite
def _policy_level(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """A level rule: one gap, one form of the neutral rate, smoothing with a rate."""
    drawn = draw(_fields(cls))
    for name in (*_GAP_FIELDS, *_NEUTRAL_FIELDS, "previous_rate"):
        drawn.pop(name, None)
    gap, _ = draw(_resource_gap(cls))
    neutral = draw(st.sampled_from(_NEUTRAL_FIELDS))
    drawn |= gap | {neutral: draw(_field(cls, neutral))}
    if drawn.get("smoothing", 0.0) > 0 or draw(st.booleans()):
        drawn["previous_rate"] = draw(_field(cls, "previous_rate"))
    return drawn


@st.composite
def _policy_first_difference(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """The first-difference rule: the gap now and four quarters back, one measure."""
    drawn = draw(_fields(cls))
    for name in (*_GAP_FIELDS, *_LAGGED_FIELDS):
        drawn.pop(name, None)
    gap, measure = draw(_resource_gap(cls))
    drawn |= gap
    if measure == "output":
        drawn["output_gap_lagged"] = draw(_field(cls, "output_gap_lagged"))
    else:
        drawn["unemployment_lagged"] = draw(_field(cls, "unemployment_lagged"))
        if draw(st.booleans()):
            drawn["natural_unemployment_lagged"] = draw(
                _field(cls, "natural_unemployment_lagged")
            )
    return drawn


def _ordered(
    draw: st.DrawFn, element: SearchStrategy[float], size: int
) -> tuple[list[float], list[float], list[float]]:
    """Draw low, central and high paths, ordered at each horizon."""
    triples = [
        sorted(draw(st.lists(element, min_size=3, max_size=3))) for _ in range(size)
    ]
    return [t[0] for t in triples], [t[1] for t in triples], [t[2] for t in triples]


@st.composite
def _policy_path(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """A path: equal-length forecasts, an ordered band, what the rule needs."""
    drawn = draw(_fields(cls))
    for name in list(drawn):
        if name.endswith("_path") or name in (*_NEUTRAL_FIELDS, "previous_rate"):
            drawn.pop(name)
    drawn.pop("gap_measure", None)
    size = draw(st.integers(min_value=1, max_value=MAX_ITEMS))
    if drawn["rule"] != "adjusted_taylor_1993":
        drawn.pop("cumulative_shortfall", None)  # the adjusted rule's alone
    inflation = st.floats(min_value=-0.2, max_value=0.5)
    gaps = st.floats(min_value=-0.3, max_value=0.3)
    rates = st.floats(min_value=0.0, max_value=0.3)
    measure = draw(st.sampled_from(["output", "unemployment"]))
    banded = draw(st.booleans())
    low, middle, high = _ordered(draw, inflation, size)
    drawn["inflation_path"] = middle
    if banded:
        drawn |= {"inflation_low_path": low, "inflation_high_path": high}
    if draw(st.booleans()):
        drawn["gap_measure"] = measure
    element = gaps if measure == "output" else rates
    stem = "output_gap" if measure == "output" else "unemployment"
    low, middle, high = _ordered(draw, element, size)
    drawn[f"{stem}_path"] = middle
    if banded and draw(st.booleans()):
        drawn |= {f"{stem}_low_path": low, f"{stem}_high_path": high}
    natural = st.lists(rates, min_size=size, max_size=size)
    if measure == "unemployment":
        drawn["natural_unemployment_path"] = draw(natural)
    lagged = st.lists(element, min_size=size, max_size=size)
    return drawn | _path_rule_inputs(draw, cls, drawn, stem, (lagged, natural))


def _path_rule_inputs(
    draw: st.DrawFn,
    cls: type[BaseModel],
    drawn: dict[str, Any],
    stem: str,
    paths: tuple[SearchStrategy[list[float]], SearchStrategy[list[float]]],
) -> dict[str, Any]:
    """What a path's rule needs: lagged paths, or a neutral rate and a rate."""
    lagged, natural = paths
    extra: dict[str, Any] = {}
    if drawn["rule"] == "first_difference":
        extra["previous_rate"] = draw(_field(cls, "previous_rate"))
        extra[f"{stem}_lagged_path"] = draw(lagged)
        if stem == "unemployment" and draw(st.booleans()):
            extra["natural_unemployment_lagged_path"] = draw(natural)
        return extra
    neutral = draw(st.sampled_from(_NEUTRAL_FIELDS))
    extra[neutral] = draw(_field(cls, neutral))
    if drawn.get("smoothing", 0.0) > 0 or draw(st.booleans()):
        extra["previous_rate"] = draw(_field(cls, "previous_rate"))
    return extra


def _policy_rule() -> SearchStrategy[dict[str, Any]]:
    """``macro.policy_rule``: each calculation's cross-field rules, constructively."""
    module = importlib.import_module("pyeconomics.models.macro.policy_rule")
    levels = (
        module.Taylor1993Inputs,
        module.Taylor1999Inputs,
        module.BalancedApproachInputs,
        module.ShortfallsInputs,
        module.AdjustedTaylor1993Inputs,
    )
    return st.one_of(
        *(_policy_level(cls) for cls in levels),
        _policy_first_difference(module.FirstDifferenceInputs),
        _policy_path(module.PathInputs),
        st.sampled_from(
            [dict(example.inputs) for example in module.policy_rule.spec.examples]
        ),
    )


OVERRIDES["macro.policy_rule"] = _policy_rule


@st.composite
def _neutral_member(draw: st.DrawFn, cls: type[BaseModel]) -> dict[str, Any]:
    """A neutral-rate input: a policy rate and inflation together, or neither."""
    drawn = draw(_fields(cls))
    drawn.pop("policy_rate", None)
    drawn.pop("inflation", None)
    if draw(st.booleans()):
        drawn["policy_rate"] = draw(_field(cls, "policy_rate"))
        drawn["inflation"] = draw(_field(cls, "inflation"))
    return drawn


def _neutral_rate() -> SearchStrategy[dict[str, Any]]:
    """``macro.neutral_rate``: a policy rate needs inflation to make it real."""
    module = importlib.import_module("pyeconomics.models.macro.neutral_rate")
    rule = module.neutral_rate
    return st.one_of(
        *(
            _neutral_member(member)
            for member in rule.spec.input_models
            if isinstance(member, type) and issubclass(member, BaseModel)
        ),
        st.sampled_from([dict(example.inputs) for example in rule.spec.examples]),
    )


OVERRIDES["macro.neutral_rate"] = _neutral_rate
