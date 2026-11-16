# src/pyeconomics/models/fixed_income/credit_spread.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Credit spreads and default: ``fixed_income.credit_spread``.

Five calculations, discriminated on ``calculation``:

- ``expected_loss``: probability of default x loss given default x exposure;
- ``hazard_from_spread`` and ``spread_from_hazard``: the credit triangle,
  ``s = lambda (1 - R)``, which holds for a constant hazard rate and a spread
  under continuous compounding, with recovery as a fraction of par paid at
  default;
- ``survival``: the survival and cumulative default probabilities over a
  horizon at a constant hazard rate;
- ``spread_return``: the approximate excess return of a credit bond over a
  holding period, its carry less spread duration x the change in spread, less
  the expected loss.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Probability,
    Rate,
    Ratio,
    Reference,
    Symbol,
    Years,
    model,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["credit_spread"]

#: The largest exposure an input takes.
_MONEY_IN: Final = 1e12
#: The widest spread an input takes, and the highest recovery rate. Together
#: they keep the hazard rate s / (1 - R) within ADR-0008's rate bound of 10.
_SPREAD_MAX: Final = 1.0
_RECOVERY_MAX: Final = 0.9
_HAZARD_MAX: Final = 10.0
#: The longest horizon, in years.
_HORIZON_MAX: Final = 100.0
#: Bounds of the parts of a spread return: carry up to 1 x 10 years, a spread
#: duration up to 30 years times a change of 0.1 either way, a loss up to 1.
_RETURN_MAX: Final = 20.0


def _probability(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0.0, le=1.0, description=description)


def _recovery() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        0.4,
        ge=0.0,
        le=_RECOVERY_MAX,
        description="Recovery rate: the fraction of par recovered at default",
    )


def _part(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_RETURN_MAX, le=_RETURN_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class ExpectedLossInputs(ModelInputs):
    """A default probability, a loss given default and an exposure."""

    calculation: Literal["expected_loss"] = Field(
        "expected_loss", description="Expected credit loss"
    )
    probability_of_default: Probability = _probability(
        "Probability of default over the horizon"
    )
    loss_given_default: Probability = _probability(
        "Fraction of the exposure lost at default (1 less the recovery rate)"
    )
    exposure: Money = Field(ge=0.0, le=_MONEY_IN, description="Exposure at default")


class HazardFromSpreadInputs(ModelInputs):
    """A credit spread and a recovery rate."""

    calculation: Literal["hazard_from_spread"] = Field(
        "hazard_from_spread", description="Hazard rate implied by a spread"
    )
    spread: Rate = Field(
        ge=0.0,
        le=_SPREAD_MAX,
        description="Credit spread over the risk-free rate, continuously compounded",
    )
    recovery_rate: Probability = _recovery()


class SpreadFromHazardInputs(ModelInputs):
    """A hazard rate and a recovery rate."""

    calculation: Literal["spread_from_hazard"] = Field(
        "spread_from_hazard", description="Spread implied by a hazard rate"
    )
    hazard_rate: Rate = Field(
        ge=0.0, le=_HAZARD_MAX, description="Default intensity per year"
    )
    recovery_rate: Probability = _recovery()


class SurvivalInputs(ModelInputs):
    """A hazard rate and a horizon."""

    calculation: Literal["survival"] = Field(
        "survival", description="Survival and default probabilities"
    )
    hazard_rate: Rate = Field(
        ge=0.0, le=_HAZARD_MAX, description="Default intensity per year"
    )
    horizon: Years = Field(ge=0.0, le=_HORIZON_MAX, description="Horizon in years")


class SpreadReturnInputs(ModelInputs):
    """A bond's spread, its spread duration, and what happens over a horizon."""

    calculation: Literal["spread_return"] = Field(
        "spread_return", description="Approximate excess return from the spread"
    )
    spread: Rate = Field(
        ge=0.0, le=_SPREAD_MAX, description="Credit spread per year at the start"
    )
    holding_period: Years = Field(
        gt=0.0, le=10.0, description="Holding period in years"
    )
    spread_duration: Years = Field(
        ge=0.0, le=30.0, description="Spread duration: price change per unit of spread"
    )
    spread_change: Rate = Field(
        ge=-0.1, le=0.1, description="Change in the spread over the holding period"
    )
    probability_of_default: Probability = _probability(
        "Probability of default over the holding period"
    )
    loss_given_default: Probability = _probability("Fraction lost at default")


CreditSpreadInputs = Annotated[
    ExpectedLossInputs
    | HazardFromSpreadInputs
    | SpreadFromHazardInputs
    | SurvivalInputs
    | SpreadReturnInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class ExpectedLossOutputs(ModelOutputs):
    calculation: Literal["expected_loss"] = Field(
        "expected_loss", description="Expected credit loss"
    )
    expected_loss: Money = Field(
        ge=0.0, le=_MONEY_IN, description="Probability x loss given default x exposure"
    )
    loss_rate: Probability = _probability("Expected loss as a fraction of the exposure")


class HazardFromSpreadOutputs(ModelOutputs):
    calculation: Literal["hazard_from_spread"] = Field(
        "hazard_from_spread", description="Hazard rate implied by a spread"
    )
    hazard_rate: Rate = Field(
        ge=0.0, le=_HAZARD_MAX, description="Default intensity per year: s / (1 - R)"
    )
    one_year_default_probability: Probability = _probability(
        "Probability of default within a year: 1 - exp(-hazard)"
    )


class SpreadFromHazardOutputs(ModelOutputs):
    calculation: Literal["spread_from_hazard"] = Field(
        "spread_from_hazard", description="Spread implied by a hazard rate"
    )
    spread: Rate = Field(
        ge=0.0, le=_HAZARD_MAX, description="Credit spread: hazard x (1 - R)"
    )


class SurvivalOutputs(ModelOutputs):
    calculation: Literal["survival"] = Field(
        "survival", description="Survival and default probabilities"
    )
    survival_probability: Probability = _probability(
        "Probability of no default by the horizon: exp(-hazard x T)"
    )
    default_probability: Probability = _probability(
        "Probability of default by the horizon"
    )


class SpreadReturnOutputs(ModelOutputs):
    calculation: Literal["spread_return"] = Field(
        "spread_return", description="Approximate excess return from the spread"
    )
    carry: Ratio = _part("Spread earned over the holding period")
    spread_change_return: Ratio = _part("-Spread duration x the change in spread")
    expected_loss: Ratio = _part("Probability of default x loss given default")
    spread_return: Ratio = _part("Carry plus the spread-change return less the loss")


CreditSpreadOutputs = Annotated[
    ExpectedLossOutputs
    | HazardFromSpreadOutputs
    | SpreadFromHazardOutputs
    | SurvivalOutputs
    | SpreadReturnOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _expected_loss(inputs: ExpectedLossInputs) -> ExpectedLossOutputs:
    rate = inputs.probability_of_default * inputs.loss_given_default
    return ExpectedLossOutputs(expected_loss=rate * inputs.exposure, loss_rate=rate)


def _hazard_from_spread(inputs: HazardFromSpreadInputs) -> HazardFromSpreadOutputs:
    # At the input bounds, 1.0 / (1 - 0.9) rounds to 10.000000000000002.
    hazard = min(inputs.spread / (1.0 - inputs.recovery_rate), _HAZARD_MAX)
    return HazardFromSpreadOutputs(
        hazard_rate=hazard, one_year_default_probability=-math.expm1(-hazard)
    )


def _spread_from_hazard(inputs: SpreadFromHazardInputs) -> SpreadFromHazardOutputs:
    return SpreadFromHazardOutputs(
        spread=inputs.hazard_rate * (1.0 - inputs.recovery_rate)
    )


def _survival(inputs: SurvivalInputs) -> SurvivalOutputs:
    exponent = -inputs.hazard_rate * inputs.horizon
    return SurvivalOutputs(
        survival_probability=math.exp(exponent),
        default_probability=-math.expm1(exponent),
    )


def _spread_return(inputs: SpreadReturnInputs) -> SpreadReturnOutputs:
    carry = inputs.spread * inputs.holding_period
    change = -inputs.spread_duration * inputs.spread_change
    loss = inputs.probability_of_default * inputs.loss_given_default
    return SpreadReturnOutputs(
        carry=carry,
        spread_change_return=change,
        expected_loss=loss,
        spread_return=carry + change - loss,
    )


# --- the model ---------------------------------------------------------------

_HULL = Reference(
    key="hull2018",
    citation=(
        "Hull, J. C. (2018). Options, Futures, and Other Derivatives, 10th ed. Pearson."
    ),
    url="https://openlibrary.org/isbn/9780134472089",
    isbn="9780134472089",
    locator=(
        "Chapter 24, Credit Risk (hazard rates, and the hazard rate implied by a "
        "bond yield spread and a recovery rate)"
    ),
)
_FABOZZI = Reference(
    key="fabozzi2005",
    citation=(
        "Fabozzi, F. J. (2005). Fixed Income Mathematics: Analytical and "
        "Statistical Techniques, 4th ed. McGraw-Hill."
    ),
    url="https://openlibrary.org/isbn/9780071460736",
    isbn="9780071460736",
    locator="Chapter 18 (credit risk concepts and measures for corporate bonds)",
)


@model(
    id="fixed_income.credit_spread",
    version=1,
    title="Credit spread and default",
    summary=(
        "Expected loss, the credit triangle between spread and hazard rate, "
        "survival probabilities and the approximate excess return from a spread."
    ),
    formula=(
        r"EL = PD \times LGD \times EAD",
        r"s = \lambda (1 - R), \quad \lambda = \frac{s}{1 - R}",
        r"S(T) = e^{-\lambda T}, \quad PD(T) = 1 - e^{-\lambda T}",
        r"r_{excess} \approx s\,t - D_s\,\Delta s - PD \times LGD",
    ),
    symbols=(
        Symbol("EL", "Expected loss", "expected_loss"),
        Symbol("PD", "Probability of default", "probability_of_default"),
        Symbol(
            "LGD",
            "Loss given default, as a share of the exposure",
            "loss_given_default",
        ),
        Symbol("EAD", "Exposure at default", "exposure"),
        Symbol("s", "Credit spread per year", "spread"),
        Symbol(
            r"\lambda",
            "Hazard rate: the default intensity per year",
            "hazard_rate",
        ),
        Symbol("R", "Recovery rate", "recovery_rate"),
        Symbol("S(T)", "Probability of surviving to time T", "survival_probability"),
        Symbol("PD(T)", "Probability of defaulting by time T", "default_probability"),
        Symbol("T", "Horizon, in years", "horizon"),
        Symbol(
            "r_{excess}",
            "Approximate excess return of the bond over a matched government bond",
            "spread_return",
        ),
        Symbol("t", "Holding period, in years", "holding_period"),
        Symbol("D_s", "Spread duration", "spread_duration"),
        Symbol(
            r"\Delta s",
            "Change in the spread over the holding period",
            "spread_change",
        ),
    ),
    assumptions=(
        (
            "The hazard rate is constant, so default times are exponential, and "
            "the spread and the hazard rate are continuously compounded."
        ),
        (
            "The credit triangle assumes recovery is a fraction of par paid at "
            "default, and that the spread compensates for expected default loss "
            "alone (no liquidity or risk premium)."
        ),
        (
            "The spread return is first order in the spread change and treats the "
            "expected loss as incurred over the holding period."
        ),
    ),
    limitations=(
        (
            "The spread return omits convexity, the roll-down of the spread and "
            "the risk-free rate's own change."
        ),
        "Hazard rates that vary with time, and correlated defaults, are out of scope.",
    ),
    references=(_HULL, _FABOZZI),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("credit", "spread", "hazard rate", "default probability", "expected loss"),
    invariants=(
        Invariant(
            id="spread_hazard_round_trip",
            statement=(
                "The spread from the hazard rate implied by a spread is that spread."
            ),
        ),
        Invariant(
            id="survival_decreases_with_horizon",
            statement="Survival probability does not rise as the horizon lengthens.",
        ),
        Invariant(
            id="expected_loss_within_exposure",
            statement="The expected loss is between zero and the exposure.",
        ),
    ),
    examples=(
        Example(
            name="loan_expected_loss",
            inputs={
                "calculation": "expected_loss",
                "probability_of_default": 0.02,
                "loss_given_default": 0.6,
                "exposure": 1_000_000,
            },
        ),
        Example(
            name="hazard_from_200bp",
            inputs={"calculation": "hazard_from_spread", "spread": 0.02},
        ),
        Example(
            name="spread_from_hazard",
            inputs={"calculation": "spread_from_hazard", "hazard_rate": 0.03},
        ),
        Example(
            name="five_year_survival",
            inputs={"calculation": "survival", "hazard_rate": 0.0333, "horizon": 5},
        ),
        Example(
            name="one_year_excess_return",
            inputs={
                "calculation": "spread_return",
                "spread": 0.015,
                "holding_period": 1,
                "spread_duration": 6.5,
                "spread_change": 0.0025,
                "probability_of_default": 0.01,
                "loss_given_default": 0.6,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def credit_spread(inputs: CreditSpreadInputs) -> CreditSpreadOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], CreditSpreadOutputs]]] = {
    ExpectedLossInputs: _expected_loss,
    HazardFromSpreadInputs: _hazard_from_spread,
    SpreadFromHazardInputs: _spread_from_hazard,
    SurvivalInputs: _survival,
    SpreadReturnInputs: _spread_return,
}
