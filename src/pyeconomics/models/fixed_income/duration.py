# src/pyeconomics/models/fixed_income/duration.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Duration: ``fixed_income.duration``.

Four calculations on a fixed-coupon bond, discriminated on ``calculation``:

- ``macaulay_modified``: the Macaulay duration (the present-value-weighted mean
  time to the bond's payments, Macaulay 1938) and the modified duration, from
  its yield to maturity;
- ``effective``: the duration from repricing the bond off a spot curve shifted
  down and up in parallel (a central difference, with the shift an input);
- ``key_rate``: the same for triangular shifts of the curve at key tenors, which
  sum to a parallel shift;
- ``dv01``: the money duration per 0.0001 of yield, the price change for a
  one-basis-point move.

Bond terms and cash flows are those of ``fixed_income.bond_pricing``; yields and
spot rates compound at the coupon frequency, under street convention.
"""

from __future__ import annotations

from itertools import pairwise
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelOutputs,
    Money,
    Rate,
    Reference,
    Years,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.fixed_income._bonds import (
    KEYS_MAX,
    MONEY_OUT,
    YIELD_MAX,
    YIELD_MIN,
    BondTerms,
    CurveTerms,
    bond_flows,
    bounded,
    curve_price,
    key_rate_shift,
    macaulay_duration,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["duration"]

#: The largest duration an output holds, in years. The Macaulay duration of a
#: bond maturing within 100 years is at most 100; divided by 1 + y/f at the
#: lowest yield and curve, it stays below 115. The effective and key-rate
#: durations are central differences of the same quantity.
_DURATION_MAX: Final = 200.0
#: One basis point.
_BASIS_POINT: Final = 1e-4

_KeyTenors = Annotated[
    tuple[Annotated[Years, Field(gt=0.0, le=100.0)], ...], ARRAY_INPUT
]
_Durations = Annotated[
    tuple[Annotated[Years, Field(ge=0.0, le=_DURATION_MAX)], ...], ARRAY_INPUT
]


def _yield() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=YIELD_MIN,
        le=YIELD_MAX,
        description="Yield to maturity per year, compounded at the coupon frequency",
    )


def _duration(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=_DURATION_MAX, description=description)


def _full() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=MONEY_OUT, description="Full (dirty) price at settlement")


# --- inputs ------------------------------------------------------------------


class MacaulayModifiedInputs(BondTerms):
    """A bond and its yield to maturity."""

    calculation: Literal["macaulay_modified"] = Field(
        "macaulay_modified", description="Macaulay and modified duration"
    )
    yield_to_maturity: Rate = _yield()


class EffectiveInputs(CurveTerms):
    """A bond and a spot curve."""

    calculation: Literal["effective"] = Field(
        "effective", description="Effective duration off a spot curve"
    )


class KeyRateInputs(CurveTerms):
    """A bond, a spot curve and the key tenors to shift it at."""

    calculation: Literal["key_rate"] = Field(
        "key_rate", description="Key-rate durations off a spot curve"
    )
    key_tenors: _KeyTenors = Field(
        min_length=1,
        max_length=KEYS_MAX,
        description="Key tenors in years, increasing",
    )

    @model_validator(mode="after")
    def _increasing_keys(self) -> Self:
        keys = self.key_tenors
        if any(later <= earlier for earlier, later in pairwise(keys)):
            msg = "the key tenors must be strictly increasing"
            raise ValueError(msg)
        return self


class Dv01Inputs(BondTerms):
    """A bond and its yield to maturity."""

    calculation: Literal["dv01"] = Field(
        "dv01", description="Price value of a basis point"
    )
    yield_to_maturity: Rate = _yield()


DurationInputs = Annotated[
    MacaulayModifiedInputs | EffectiveInputs | KeyRateInputs | Dv01Inputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class MacaulayModifiedOutputs(ModelOutputs):
    calculation: Literal["macaulay_modified"] = Field(
        "macaulay_modified", description="Macaulay and modified duration"
    )
    macaulay_duration: Years = _duration(
        "Present-value-weighted mean time to the payments"
    )
    modified_duration: Years = _duration(
        "Macaulay duration over 1 + y/f: the relative price change per unit of yield"
    )
    full_price: Money = _full()


class EffectiveOutputs(ModelOutputs):
    calculation: Literal["effective"] = Field(
        "effective", description="Effective duration off a spot curve"
    )
    effective_duration: Years = _duration(
        "(P_down - P_up) / (2 P bump): relative price change per unit shift"
    )
    full_price: Money = _full()
    price_down: Money = Field(
        ge=0.0, le=MONEY_OUT, description="Full price with the curve shifted down"
    )
    price_up: Money = Field(
        ge=0.0, le=MONEY_OUT, description="Full price with the curve shifted up"
    )


class KeyRateOutputs(ModelOutputs):
    calculation: Literal["key_rate"] = Field(
        "key_rate", description="Key-rate durations off a spot curve"
    )
    key_rate_durations: _Durations = Field(
        max_length=KEYS_MAX, description="Duration to each key tenor's shift"
    )
    effective_duration: Years = _duration("Duration to a parallel shift")
    full_price: Money = _full()


class Dv01Outputs(ModelOutputs):
    calculation: Literal["dv01"] = Field(
        "dv01", description="Price value of a basis point"
    )
    dv01: Money = Field(
        ge=0.0,
        le=MONEY_OUT,
        description=(
            "Modified duration x full price x 0.0001: the price change per basis point"
        ),
    )
    modified_duration: Years = _duration("Modified duration")
    full_price: Money = _full()


DurationOutputs = Annotated[
    MacaulayModifiedOutputs | EffectiveOutputs | KeyRateOutputs | Dv01Outputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _modified(
    inputs: MacaulayModifiedInputs | Dv01Inputs,
) -> tuple[float, float, float]:
    """Return the full price and the Macaulay and modified durations."""
    flows = bond_flows(inputs)
    y = inputs.yield_to_maturity
    full, macaulay = macaulay_duration(flows, y)
    full = bounded(full, 0.0, MONEY_OUT, "full price")
    return full, macaulay, macaulay / (1 + y / flows.periods_per_year)


def _macaulay_modified(inputs: MacaulayModifiedInputs) -> MacaulayModifiedOutputs:
    full, macaulay, modified = _modified(inputs)
    return MacaulayModifiedOutputs(
        macaulay_duration=macaulay, modified_duration=modified, full_price=full
    )


def _dv01(inputs: Dv01Inputs) -> Dv01Outputs:
    full, _, modified = _modified(inputs)
    return Dv01Outputs(
        dv01=bounded(modified * full * _BASIS_POINT, 0.0, MONEY_OUT, "dv01"),
        modified_duration=modified,
        full_price=full,
    )


def _central(
    inputs: CurveTerms, shift: Callable[[float], float] | None
) -> tuple[float, float, float, float]:
    """Return the base, down and up prices and the central-difference duration."""
    flows = bond_flows(inputs)
    tenors, rates, h = inputs.curve_tenors, inputs.curve_rates, inputs.bump
    weight = shift or (lambda _: 1.0)
    base = curve_price(flows, tenors, rates)
    down = curve_price(flows, tenors, rates, lambda t: -h * weight(t))
    up = curve_price(flows, tenors, rates, lambda t: h * weight(t))
    for value, what in ((base, "full price"), (down, "price down"), (up, "price up")):
        bounded(value, 0.0, MONEY_OUT, what)
    duration = (down - up) / (2 * h * base)
    return base, down, up, bounded(duration, 0.0, _DURATION_MAX, "duration")


def _effective(inputs: EffectiveInputs) -> EffectiveOutputs:
    base, down, up, duration = _central(inputs, None)
    return EffectiveOutputs(
        effective_duration=duration, full_price=base, price_down=down, price_up=up
    )


def _key_rate(inputs: KeyRateInputs) -> KeyRateOutputs:
    keys = inputs.key_tenors
    base, _, _, parallel = _central(inputs, None)
    durations = tuple(
        _central(inputs, key_rate_shift(keys, index))[3] for index in range(len(keys))
    )
    return KeyRateOutputs(
        key_rate_durations=durations, effective_duration=parallel, full_price=base
    )


# --- the model ---------------------------------------------------------------

_MACAULAY = Reference(
    key="macaulay1938",
    citation=(
        "Macaulay, F. R. (1938). Some Theoretical Problems Suggested by the "
        "Movements of Interest Rates, Bond Yields and Stock Prices in the "
        "United States since 1856. National Bureau of Economic Research."
    ),
    url="https://www.nber.org/books-and-chapters/some-theoretical-problems-suggested-movements-interest-rates-bond-yields-and-stock-prices-united/concept-long-term-interest-rates",
    locator=(
        "Chapter II, The Concept of Long Term Interest Rates, pp. 24-53 "
        "(duration as the weighted mean time to a bond's payments)"
    ),
)
_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator="Chapter 4, Table 4.6 (calculation of duration) and modified duration",
)
_HO = Reference(
    key="ho1992",
    citation=(
        "Ho, T. S. Y. (1992). Key Rate Durations: Measures of Interest Rate "
        "Risks. The Journal of Fixed Income 2(2), 29-44."
    ),
    doi="10.3905/jfi.1992.408049",
    locator="Key rate shifts (triangular shifts that sum to a parallel shift)",
)
_BOND = {
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
}
_CURVE = {
    "curve_tenors": [0.5, 1, 2, 5, 10, 30],
    "curve_rates": [0.043, 0.042, 0.041, 0.042, 0.045, 0.048],
}


@model(
    id="fixed_income.duration",
    version=2,
    title="Bond duration",
    summary=(
        "Macaulay and modified duration from a yield, effective and key-rate "
        "duration off a spot curve, and DV01 of a fixed-coupon bond."
    ),
    formula=(
        r"D_{Mac} = \frac{1}{P}\sum_j \frac{t_j}{f}\,\frac{CF_j}{(1 + y/f)^{t_j}}",
        r"D_{mod} = \frac{D_{Mac}}{1 + y/f}",
        r"D_{eff} = \frac{P(z - h) - P(z + h)}{2 P(z) h}",
        r"KRD_k = \frac{P(z - h s_k) - P(z + h s_k)}{2 P(z) h}, \quad \sum_k s_k = 1",
        r"DV01 = D_{mod}\,P \times 0.0001",
    ),
    assumptions=(
        (
            "Times t_j are counted in coupon periods from settlement, as in "
            "fixed_income.bond_pricing; the yield compounds at the coupon "
            "frequency, under street convention."
        ),
        (
            "The spot curve is linear in its rates between nodes and flat "
            "beyond them; its rates compound at the coupon frequency."
        ),
        (
            "A key tenor's shift is 1 at the tenor, falls linearly to 0 at its "
            "neighbours, and stays at 1 beyond the first and last keys."
        ),
        "The bond has no embedded option, so its cash flows do not move with rates.",
    ),
    limitations=(
        (
            "A price above 1e15, which only a face value near 1e9 off a curve "
            "near -10% for a century, shifted down, reaches, raises DomainError."
        ),
        (
            "Effective and key-rate durations are central differences: their "
            "error is second order in the bump."
        ),
        "Options, prepayments and credit are out of scope.",
    ),
    references=(_MACAULAY, _HULL, _HO),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    tags=("bond", "duration", "key rate", "dv01", "interest rate risk"),
    invariants=(
        Invariant(
            id="zero_coupon_macaulay_equals_maturity",
            statement=(
                "A zero-coupon bond's Macaulay duration is its time to maturity, "
                "in years of coupon periods."
            ),
        ),
        Invariant(
            id="modified_equals_macaulay_over_periodic_factor",
            statement="The modified duration is the Macaulay duration over 1 + y/f.",
        ),
        Invariant(
            id="key_rates_sum_to_effective",
            statement=(
                "Key-rate durations, whose shifts sum to a parallel shift, sum to "
                "the effective duration, to the central difference's error."
            ),
        ),
        Invariant(
            id="duration_falls_as_coupon_rises",
            statement=(
                "With the yield and dates fixed, a higher coupon rate gives a "
                "Macaulay duration no longer."
            ),
        ),
        Invariant(
            id="dv01_positive",
            statement="An option-free bond's DV01 is positive.",
        ),
    ),
    examples=(
        Example(
            name="ten_year_note",
            inputs={
                "calculation": "macaulay_modified",
                **_BOND,
                "yield_to_maturity": 0.045,
            },
        ),
        Example(
            name="effective_off_a_curve",
            inputs={"calculation": "effective", **_BOND, **_CURVE},
        ),
        Example(
            name="key_rates",
            inputs={
                "calculation": "key_rate",
                **_BOND,
                **_CURVE,
                "key_tenors": [2, 5, 10, 30],
            },
        ),
        Example(
            name="dv01_per_million",
            inputs={
                "calculation": "dv01",
                **_BOND,
                "face_value": 1_000_000,
                "yield_to_maturity": 0.045,
            },
        ),
    ),
    changelog=(
        ChangelogEntry(version=1, note="First version."),
        ChangelogEntry(
            version=2,
            note="Correct US 30/360 long-stub accrual and discount times (#89).",
        ),
    ),
)
def duration(inputs: DurationInputs) -> DurationOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[BondTerms], Callable[[Any], DurationOutputs]]] = {
    MacaulayModifiedInputs: _macaulay_modified,
    EffectiveInputs: _effective,
    KeyRateInputs: _key_rate,
    Dv01Inputs: _dv01,
}
