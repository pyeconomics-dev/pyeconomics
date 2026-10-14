# src/pyeconomics/core/units.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Units and default bounds for model fields (ADR-0008 decisions 1-3).

Every numeric input and output field of a model declares one unit kind from
the closed vocabulary :class:`UnitKind`. The ``Annotated`` markers below
(:data:`Rate`, :data:`Money`, :data:`Years` and the rest) attach the kind to a
field, add it to the field's JSON Schema as ``x-unit``, and reject NaN and
infinity. Rates, returns, volatilities and probabilities are decimals:
``0.05`` is 5% (decision 1).

A field's bounds come from the model, which may narrow the defaults in
:data:`DEFAULT_BOUNDS` and widen them only with a recorded reason
(decision 3). Adding a unit kind is a reviewed code change here, not an ADR
change.

Examples
--------
>>> from pydantic import BaseModel, Field
>>> from pyeconomics.core import Rate, UnitKind, default_bounds
>>> class Inputs(BaseModel):
...     rate: Rate = Field(ge=-0.5, le=1.0, description="Annual yield")
>>> Inputs.model_json_schema()["properties"]["rate"]["x-unit"]
'rate'
>>> default_bounds(UnitKind.RATE)
Bounds(lower=-0.99, upper=10.0, lower_inclusive=True, upper_inclusive=True)

"""

from __future__ import annotations

import datetime as dt
import math
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Annotated, Final

import numpy as np
from pydantic import AllowInfNan, BeforeValidator

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pydantic import GetJsonSchemaHandler
    from pydantic.json_schema import JsonSchemaValue
    from pydantic_core import CoreSchema

__all__ = [
    "DEFAULT_BOUNDS",
    "DEFAULT_DATE_BOUNDS",
    "MAX_ARRAY_LENGTH",
    "MAX_STRING_LENGTH",
    "UNIT_SCHEMA_KEY",
    "Bounds",
    "Correlation",
    "Count",
    "DateBounds",
    "DateValue",
    "Days",
    "IndexLevel",
    "Money",
    "Periods",
    "Probability",
    "Rate",
    "Ratio",
    "Return",
    "Unit",
    "UnitKind",
    "Volatility",
    "Years",
    "default_bounds",
]

#: The JSON Schema keyword that carries a field's unit kind.
UNIT_SCHEMA_KEY: Final = "x-unit"


class UnitKind(StrEnum):
    """The closed vocabulary of unit kinds (ADR-0008 decision 2).

    A ``MONEY`` field takes its currency (ISO 4217) from an input field, or is
    currency-agnostic when the formula is linear in money and all its money
    fields share one currency.
    """

    RATE = "rate"
    """An interest rate, yield or spread, as a decimal per year."""
    RETURN = "return"
    """A return over a stated period, as a decimal."""
    MONEY = "money"
    """An amount of money in one currency."""
    YEARS = "years"
    """A length of time in years."""
    DAYS = "days"
    """A whole number of days."""
    PERIODS = "periods"
    """A number of compounding or payment periods, possibly fractional."""
    COUNT = "count"
    """A whole number of things."""
    RATIO = "ratio"
    """A dimensionless ratio that is not a rate or a return."""
    PROBABILITY = "probability"
    """A probability, as a decimal between 0 and 1."""
    VOLATILITY = "volatility"
    """A standard deviation of returns, as a decimal per year unless stated."""
    CORRELATION = "correlation"
    """A correlation coefficient between -1 and 1."""
    INDEX_LEVEL = "index_level"
    """The level of an index or a price relative to a base."""
    DATE = "date"
    """A calendar date."""


@dataclass(frozen=True, slots=True)
class Unit:
    """The ``Annotated`` metadata that gives a field its unit kind.

    Pydantic calls :meth:`__get_pydantic_json_schema__` when it builds a
    field's JSON Schema, which adds ``"x-unit": "<kind>"``.
    """

    kind: UnitKind

    def __get_pydantic_json_schema__(
        self, core_schema: CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        """Add ``x-unit`` to the field's JSON Schema."""
        schema = handler(core_schema)
        schema[UNIT_SCHEMA_KEY] = self.kind.value
        _unit_schema(schema)
        return schema


def _unit_schema(schema: JsonSchemaValue) -> None:
    """Preserve unit schemas when pydantic wraps bounds around validators.

    Pydantic emits Python constraint names for function-before schemas,
    including inside nullable fields. Date bounds remain runtime-only, as
    JSON Schema's numeric bounds do not apply to ISO date strings.
    """
    kind = schema.get(UNIT_SCHEMA_KEY)
    for constraint, keyword in (
        ("ge", "minimum"),
        ("gt", "exclusiveMinimum"),
        ("le", "maximum"),
        ("lt", "exclusiveMaximum"),
    ):
        if constraint in schema and kind is not None:
            bound = schema.pop(constraint)
            if kind != UnitKind.DATE.value:
                schema[keyword] = bound
    for value in schema.values():
        if isinstance(value, dict):
            _unit_schema(value)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    _unit_schema(item)


_FINITE = AllowInfNan(allow_inf_nan=False)


def _numeric_value(value: object) -> object:
    """Reject flags before pydantic can coerce them to zero or one."""
    if isinstance(value, bool | np.bool_):
        msg = "a numeric field cannot be a boolean"
        raise ValueError(msg)  # noqa: TRY004 - pydantic wraps validation failures
    return value


def _date_value(value: object) -> object:
    """Keep calendar date forms; refuse numeric epoch timestamps."""
    if isinstance(value, int | float | np.integer | np.floating | np.bool_):
        msg = "a date field cannot be a numeric epoch timestamp"
        raise ValueError(msg)  # noqa: TRY004 - pydantic wraps validation failures
    return value


_NUMERIC = BeforeValidator(_numeric_value)
_DATE = BeforeValidator(_date_value)

Rate = Annotated[float, Unit(UnitKind.RATE), _FINITE, _NUMERIC]
"""A rate, yield or spread as a decimal (``0.05`` is 5%)."""
Return = Annotated[float, Unit(UnitKind.RETURN), _FINITE, _NUMERIC]
"""A return as a decimal."""
Money = Annotated[float, Unit(UnitKind.MONEY), _FINITE, _NUMERIC]
"""An amount of money."""
Years = Annotated[float, Unit(UnitKind.YEARS), _FINITE, _NUMERIC]
"""A time in years."""
Days = Annotated[int, Unit(UnitKind.DAYS), _NUMERIC]
"""A whole number of days."""
Periods = Annotated[float, Unit(UnitKind.PERIODS), _FINITE, _NUMERIC]
"""A number of periods, possibly fractional."""
Count = Annotated[int, Unit(UnitKind.COUNT), _NUMERIC]
"""A whole number of things."""
Ratio = Annotated[float, Unit(UnitKind.RATIO), _FINITE, _NUMERIC]
"""A dimensionless ratio."""
Probability = Annotated[float, Unit(UnitKind.PROBABILITY), _FINITE, _NUMERIC]
"""A probability as a decimal."""
Volatility = Annotated[float, Unit(UnitKind.VOLATILITY), _FINITE, _NUMERIC]
"""A volatility as a decimal."""
Correlation = Annotated[float, Unit(UnitKind.CORRELATION), _FINITE, _NUMERIC]
"""A correlation coefficient."""
IndexLevel = Annotated[float, Unit(UnitKind.INDEX_LEVEL), _FINITE, _NUMERIC]
"""An index level."""
DateValue = Annotated[dt.date, Unit(UnitKind.DATE), _DATE]
"""A calendar date."""


@dataclass(frozen=True, slots=True)
class Bounds:
    """Finite numeric bounds, each end inclusive unless stated.

    Examples
    --------
    >>> volatility = Bounds(0.0, 10.0, lower_inclusive=False)
    >>> volatility.contains(0.0), volatility.contains(0.2)
    (False, True)

    """

    lower: float
    upper: float
    lower_inclusive: bool = True
    upper_inclusive: bool = True

    def __post_init__(self) -> None:
        """Reject infinite, NaN or inverted bounds."""
        if not (math.isfinite(self.lower) and math.isfinite(self.upper)):
            msg = f"bounds must be finite, not [{self.lower}, {self.upper}]"
            raise ValueError(msg)
        if self.lower >= self.upper:
            msg = f"the lower bound {self.lower} is not below {self.upper}"
            raise ValueError(msg)

    def contains(self, value: float) -> bool:
        """Return whether ``value`` lies within the bounds."""
        above = value >= self.lower if self.lower_inclusive else value > self.lower
        below = value <= self.upper if self.upper_inclusive else value < self.upper
        return above and below


@dataclass(frozen=True, slots=True)
class DateBounds:
    """Inclusive bounds on a calendar date."""

    lower: dt.date
    upper: dt.date

    def __post_init__(self) -> None:
        """Reject inverted bounds."""
        if self.lower >= self.upper:
            msg = f"the lower bound {self.lower} is not before {self.upper}"
            raise ValueError(msg)

    def contains(self, value: dt.date) -> bool:
        """Return whether ``value`` lies within the bounds."""
        return self.lower <= value <= self.upper


#: Default bounds per numeric unit kind (ADR-0008 decision 3). A model may
#: narrow them, and widen them only with a recorded reason.
DEFAULT_BOUNDS: Final[Mapping[UnitKind, Bounds]] = MappingProxyType(
    {
        UnitKind.RATE: Bounds(-0.99, 10.0),
        UnitKind.RETURN: Bounds(-1.0, 100.0),
        UnitKind.MONEY: Bounds(-1e15, 1e15),
        UnitKind.YEARS: Bounds(0.0, 200.0),
        UnitKind.DAYS: Bounds(0.0, 73_050.0),
        UnitKind.PERIODS: Bounds(0.0, 100_000.0),
        UnitKind.COUNT: Bounds(0.0, 1e9),
        UnitKind.RATIO: Bounds(-1e6, 1e6),
        UnitKind.PROBABILITY: Bounds(0.0, 1.0),
        UnitKind.VOLATILITY: Bounds(0.0, 10.0, lower_inclusive=False),
        UnitKind.CORRELATION: Bounds(-1.0, 1.0),
        UnitKind.INDEX_LEVEL: Bounds(0.0, 1e9),
    }
)

#: Default bounds on a date field.
DEFAULT_DATE_BOUNDS: Final = DateBounds(dt.date(1900, 1, 1), dt.date(2200, 12, 31))

#: Default maximum number of items in an array field.
MAX_ARRAY_LENGTH: Final = 100_000

#: Default maximum number of characters in a string field.
MAX_STRING_LENGTH: Final = 256


def default_bounds(kind: UnitKind) -> Bounds:
    """Return the default bounds of a numeric unit kind.

    Raises
    ------
    KeyError
        For :attr:`UnitKind.DATE`, whose bounds are
        :data:`DEFAULT_DATE_BOUNDS`.

    """
    if kind is UnitKind.DATE:
        msg = "dates use DEFAULT_DATE_BOUNDS"
        raise KeyError(msg)
    return DEFAULT_BOUNDS[kind]
