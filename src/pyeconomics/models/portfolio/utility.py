# src/pyeconomics/models/portfolio/utility.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Utility, the risky share and the Kelly fraction: ``portfolio.utility``.

Four calculations, discriminated on ``calculation``:

- ``mean_variance_utility``: :math:`U = E[r] - \tfrac{1}{2} A \sigma^2` for a
  risk aversion :math:`A`, the certainty-equivalent return of a mean-variance
  investor;
- ``optimal_risky_share``: the share :math:`y^* = (E[r] - r_f) / (A\sigma^2)`
  of wealth in a risky portfolio, the rest at the risk-free rate, that
  maximizes that utility (Merton, 1969), with the combined portfolio's return,
  volatility and utility;
- ``certainty_equivalent``: the certain return worth as much as a gamble over
  discrete outcomes to an investor with constant relative risk aversion
  :math:`\gamma` (Pratt, 1964): :math:`1 + CE = \left(\sum p_i (1 +
  r_i)^{1-\gamma}\right)^{1/(1-\gamma)}`, and :math:`e^{\sum p_i \ln(1 + r_i)}`
  at :math:`\gamma = 1`;
- ``kelly``: the fraction of wealth that maximizes the expected logarithm of
  wealth (Kelly, 1956), for a discrete bet, :math:`f^* = p - (1 - p) / b` at net
  odds :math:`b`, or for a continuous asset, :math:`f^* = (\mu - r) / \sigma^2`,
  scaled by a fractional multiplier (half Kelly is 0.5).

Every output is the formula's value for the parameters given, the same for
every user.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self, cast

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Probability,
    ProbabilityArray,
    Rate,
    Ratio,
    Reference,
    Return,
    ReturnArray,
    Volatility,
    model,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["utility"]

#: The most outcomes a gamble may have.
_OUTCOMES_MAX: Final = 1_000
#: How far the probabilities may sum from one: rounding in the caller's data.
_PROBABILITY_SUM: Final = 1e-9
#: The risky-share and Kelly inputs: returns and rates within [-1, 1] a year,
#: a volatility of at least 1% and a risk aversion of at least 0.1 keep the
#: answers sized: |E - rf| <= 2 and A sigma^2 >= 1e-5, so the share is at most
#: 2e5 in size; the combined portfolio's volatility, |E - rf| / (A sigma), at
#: most 2,000; its return and utility at most 1 + 4 / 1e-5 = 400,001.
_RETURN_IN: Final = 1.0
_VOLATILITY_MIN: Final = 0.01
_AVERSION_MIN: Final = 0.1
_AVERSION_MAX: Final = 100.0
_SHARE_OUT: Final = 2e5
_COMBINED_RETURN_OUT: Final = 4.1e5
_COMBINED_VOLATILITY_OUT: Final = 2e3
#: The utility of the mean-variance calculation, E - A sigma^2 / 2, lies in
#: [-1 - 100 * 100 / 2, 10] for its input bounds.
_UTILITY_MIN: Final = -1e4
#: Net odds of a discrete bet: from 1-to-1000 against to 1000-to-1 for.
_ODDS_MIN: Final = 1e-3
_ODDS_MAX: Final = 1e3
#: The continuous Kelly fraction (mu - r) / sigma^2 is at most 2 / 1e-4 = 2e4
#: in size, and its growth rate at most 1 + 4 / 2e-4 = 20,001.
_KELLY_OUT: Final = 2e4
_GROWTH_OUT: Final = 2.1e4


def _aversion(description: str, low: float = _AVERSION_MIN) -> Any:  # noqa: ANN401
    return Field(ge=low, le=_AVERSION_MAX, description=description)


def _return_in(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_RETURN_IN, le=_RETURN_IN, description=description)


# --- inputs ------------------------------------------------------------------


class MeanVarianceUtilityInputs(ModelInputs):
    """A portfolio's expected return and volatility, and the investor's aversion."""

    calculation: Literal["mean_variance_utility"] = Field(
        "mean_variance_utility", description="Mean-variance utility, E - A sigma^2 / 2"
    )
    expected_return: Return = Field(
        ge=-1.0, le=10.0, description="Expected return per year"
    )
    # Zero is allowed, below the volatility kind's open lower end: a risk-free
    # asset has utility equal to its return.
    volatility: Volatility = Field(
        ge=0.0, le=10.0, description="Volatility per year; zero for a risk-free asset"
    )
    risk_aversion: Ratio = _aversion("Risk aversion A; zero is risk neutral", 0.0)


class OptimalRiskyShareInputs(ModelInputs):
    """A risky portfolio, a risk-free rate and the investor's aversion."""

    calculation: Literal["optimal_risky_share"] = Field(
        "optimal_risky_share", description="Utility-maximizing share in the risky asset"
    )
    expected_return: Return = _return_in(
        "Expected return of the risky portfolio a year"
    )
    risk_free_rate: Rate = Field(
        ge=-0.99, le=_RETURN_IN, description="Risk-free rate a year"
    )
    volatility: Volatility = Field(
        ge=_VOLATILITY_MIN,
        le=10.0,
        description="Volatility of the risky portfolio a year",
    )
    risk_aversion: Ratio = _aversion("Risk aversion A, above zero")


class CertaintyEquivalentInputs(ModelInputs):
    """A gamble over discrete returns, and constant relative risk aversion."""

    calculation: Literal["certainty_equivalent"] = Field(
        "certainty_equivalent", description="Certainty-equivalent return under CRRA"
    )
    outcomes: ReturnArray = Field(
        min_length=1, max_length=_OUTCOMES_MAX, description="Possible returns"
    )
    probabilities: ProbabilityArray = Field(
        min_length=1,
        max_length=_OUTCOMES_MAX,
        description="Probability of each outcome; they sum to one",
    )
    relative_risk_aversion: Ratio = _aversion(
        "Relative risk aversion gamma; 1 is log utility, 0 risk neutral", 0.0
    )

    @model_validator(mode="after")
    def _a_distribution(self) -> Self:
        if len(self.probabilities) != len(self.outcomes):
            msg = (
                f"give one probability per outcome: {len(self.outcomes)} outcomes, "
                f"{len(self.probabilities)} probabilities"
            )
            raise ValueError(msg)
        total = math.fsum(self.probabilities)
        if abs(total - 1.0) > _PROBABILITY_SUM:
            msg = f"the probabilities must sum to one, not {total!r}"
            raise ValueError(msg)
        return self


class KellyInputs(ModelInputs):
    """A discrete bet (probability and odds) or a continuous asset (drift and risk)."""

    calculation: Literal["kelly"] = Field(
        "kelly", description="Kelly fraction of a bet or an asset"
    )
    win_probability: Probability | None = Field(
        None, ge=0.0, le=1.0, description="Discrete bet: probability of winning"
    )
    odds: Ratio | None = Field(
        None,
        ge=_ODDS_MIN,
        le=_ODDS_MAX,
        description="Discrete bet: net odds, the profit per unit staked on a win",
    )
    drift: Rate | None = Field(
        None,
        ge=-_RETURN_IN,
        le=_RETURN_IN,
        description="Continuous asset: expected (arithmetic) return a year",
    )
    risk_free_rate: Rate | None = Field(
        None,
        ge=-0.99,
        le=_RETURN_IN,
        description="Continuous asset: risk-free rate a year; zero if omitted",
    )
    volatility: Volatility | None = Field(
        None,
        ge=_VOLATILITY_MIN,
        le=10.0,
        description="Continuous asset: volatility a year",
    )
    multiplier: Ratio = Field(
        1.0,
        gt=0.0,
        le=1.0,
        description="Fraction of the full Kelly fraction to use; 0.5 is half Kelly",
    )

    @model_validator(mode="after")
    def _one_form(self) -> Self:
        bet = (self.win_probability, self.odds)
        asset = (self.drift, self.volatility)
        if all(v is not None for v in bet) and all(
            v is None for v in (*asset, self.risk_free_rate)
        ):
            return self
        if all(v is not None for v in asset) and all(v is None for v in bet):
            return self
        msg = (
            "give win_probability and odds for a discrete bet, or drift and "
            "volatility (and optionally risk_free_rate) for a continuous asset"
        )
        raise ValueError(msg)


UtilityInputs = Annotated[
    MeanVarianceUtilityInputs
    | OptimalRiskyShareInputs
    | CertaintyEquivalentInputs
    | KellyInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


class MeanVarianceUtilityOutputs(ModelOutputs):
    calculation: Literal["mean_variance_utility"] = Field(
        "mean_variance_utility", description="Mean-variance utility, E - A sigma^2 / 2"
    )
    utility: Return = Field(
        ge=_UTILITY_MIN,
        le=10.0,
        description="Utility: the certainty-equivalent return a year",
    )
    risk_penalty: Ratio = Field(
        ge=0.0, le=-_UTILITY_MIN, description="The penalty for risk, A sigma^2 / 2"
    )


class OptimalRiskyShareOutputs(ModelOutputs):
    calculation: Literal["optimal_risky_share"] = Field(
        "optimal_risky_share", description="Utility-maximizing share in the risky asset"
    )
    optimal_share: Ratio = Field(
        ge=-_SHARE_OUT,
        le=_SHARE_OUT,
        description=(
            "Share of wealth in the risky portfolio; above 1 borrows, below 0 is short"
        ),
    )
    expected_return: Return = Field(
        ge=-1.0,
        le=_COMBINED_RETURN_OUT,
        description="Combined portfolio's expected return",
    )
    volatility: Volatility = Field(
        ge=0.0,
        le=_COMBINED_VOLATILITY_OUT,
        description="Combined portfolio's volatility",
    )
    utility: Return = Field(
        ge=-1.0, le=_COMBINED_RETURN_OUT, description="Combined portfolio's utility"
    )
    sharpe_ratio: Ratio = Field(
        ge=-200.0, le=200.0, description="Sharpe ratio of the risky portfolio"
    )


class CertaintyEquivalentOutputs(ModelOutputs):
    calculation: Literal["certainty_equivalent"] = Field(
        "certainty_equivalent", description="Certainty-equivalent return under CRRA"
    )
    certainty_equivalent: Return = Field(
        ge=-1.0,
        le=100.0,
        description="Certain return with the gamble's expected utility",
    )
    expected_return: Return = Field(
        ge=-1.0, le=100.0, description="Probability-weighted mean of the outcomes"
    )
    risk_premium: Return = Field(
        ge=0.0, le=101.0, description="Expected return less the certainty equivalent"
    )


class KellyOutputs(ModelOutputs):
    calculation: Literal["kelly"] = Field(
        "kelly", description="Kelly fraction of a bet or an asset"
    )
    form: Literal["discrete", "continuous"] = Field(
        description="Which Kelly formula applied"
    )
    full_kelly: Ratio = Field(
        ge=-_KELLY_OUT,
        le=_KELLY_OUT,
        description="The growth-maximizing fraction; at or below zero there is no edge",
    )
    fraction: Ratio = Field(
        ge=-_KELLY_OUT,
        le=_KELLY_OUT,
        description=(
            "The multiplier times the full fraction; for a discrete bet never below "
            "zero, as a bet cannot be taken short"
        ),
    )
    growth_rate: Rate = Field(
        ge=-0.99,
        le=_GROWTH_OUT,
        description=(
            "Expected log growth at that fraction: per bet, or a year for a "
            "continuous asset"
        ),
    )


UtilityOutputs = Annotated[
    MeanVarianceUtilityOutputs
    | OptimalRiskyShareOutputs
    | CertaintyEquivalentOutputs
    | KellyOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _mean_variance_utility(
    inputs: MeanVarianceUtilityInputs,
) -> MeanVarianceUtilityOutputs:
    penalty = 0.5 * inputs.risk_aversion * inputs.volatility**2
    return MeanVarianceUtilityOutputs(
        utility=inputs.expected_return - penalty, risk_penalty=penalty
    )


def _optimal_risky_share(inputs: OptimalRiskyShareInputs) -> OptimalRiskyShareOutputs:
    premium = inputs.expected_return - inputs.risk_free_rate
    variance = inputs.volatility**2
    share = premium / (inputs.risk_aversion * variance)
    # At the optimum, y*(E - rf) = premium^2 / (A sigma^2) and the utility is
    # rf plus half of that.
    gain = share * premium
    return OptimalRiskyShareOutputs(
        optimal_share=share,
        expected_return=inputs.risk_free_rate + gain,
        volatility=abs(share) * inputs.volatility,
        utility=inputs.risk_free_rate + 0.5 * gain,
        sharpe_ratio=premium / inputs.volatility,
    )


def _certainty_equivalent(
    inputs: CertaintyEquivalentInputs,
) -> CertaintyEquivalentOutputs:
    weights = np.asarray(inputs.probabilities, dtype=np.float64)
    weights = weights / weights.sum()
    outcomes = np.asarray(inputs.outcomes, dtype=np.float64)
    held = weights > 0
    weights, outcomes = weights[held], outcomes[held]
    # A weighted mean lies between the outcomes; rounding must not move it out.
    mean = math.fsum((weights * outcomes).tolist())
    mean = min(max(mean, float(outcomes.min())), float(outcomes.max()))
    gamma = inputs.relative_risk_aversion
    ce = mean if gamma == 0 else _crra(outcomes, weights, gamma)
    # The power mean lies between the outcomes and below the arithmetic mean;
    # rounding must not put it outside.
    ce = min(max(ce, float(outcomes.min())), mean)
    return CertaintyEquivalentOutputs(
        certainty_equivalent=ce, expected_return=mean, risk_premium=mean - ce
    )


def _crra(
    outcomes: np.ndarray[Any, Any], weights: np.ndarray[Any, Any], gamma: float
) -> float:
    """Return the CRRA certainty equivalent, summing in log space."""
    if np.any(outcomes == -1.0) and gamma >= 1:
        # Utility of nothing is minus infinity: no certain return is as bad,
        # save a total loss.
        return -1.0
    with np.errstate(divide="ignore"):
        logs = np.log1p(outcomes)
    if gamma == 1:
        return math.expm1(math.fsum((weights * logs).tolist()))
    power = 1.0 - gamma
    # power > 0 here wherever a log is -inf, so those terms are exp(-inf) = 0.
    scaled = power * logs
    finite = np.isfinite(scaled)
    if not finite.any():
        return -1.0
    if finite.all() and float(np.max(np.abs(scaled))) <= 1.0:
        # Near log utility the power is tiny, and ln(sum) / power cancels
        # catastrophically; expm1 and log1p keep every digit of the small sum.
        mean = math.fsum((weights * np.expm1(scaled)).tolist())
        return math.expm1(math.log1p(mean) / power)
    peak = float(np.max(scaled[finite]))
    total = float(np.sum(weights[finite] * np.exp(scaled[finite] - peak)))
    return math.expm1((peak + math.log(total)) / power)


def _kelly(inputs: KellyInputs) -> KellyOutputs:
    if inputs.win_probability is not None and inputs.odds is not None:
        p, b = inputs.win_probability, inputs.odds
        q = 1.0 - p
        full = p - q / b
        fraction = inputs.multiplier * max(full, 0.0)
        growth = p * math.log1p(fraction * b)
        if q > 0:
            growth += q * math.log1p(-fraction)
        return KellyOutputs(
            form="discrete", full_kelly=full, fraction=fraction, growth_rate=growth
        )
    drift = cast("float", inputs.drift)  # the validator set both
    volatility = cast("float", inputs.volatility)
    rate = inputs.risk_free_rate or 0.0
    variance = volatility * volatility
    full = (drift - rate) / variance
    fraction = inputs.multiplier * full
    growth = rate + fraction * (drift - rate) - 0.5 * fraction * fraction * variance
    return KellyOutputs(
        form="continuous", full_kelly=full, fraction=fraction, growth_rate=growth
    )


# --- the model ---------------------------------------------------------------

_KELLY = Reference(
    key="kelly1956",
    citation=(
        "Kelly, J. L. (1956). A new interpretation of information rate. Bell "
        "System Technical Journal, 35(4), 917-926."
    ),
    doi="10.1002/j.1538-7305.1956.tb03809.x",
    locator="pp. 919-920, the even-money fraction maximizing the growth rate",
)
_THORP = Reference(
    key="thorp2006",
    citation=(
        "Thorp, E. O. (2006). The Kelly criterion in blackjack, sports betting "
        "and the stock market. In Handbook of Asset and Liability Management, "
        "Vol. 1, 385-428. Elsevier."
    ),
    doi="10.1016/S1872-0978(06)01009-X",
    isbn="9780444508751",
    locator=(
        "Section 2, pp. 389-391, bets at even money and at b-to-1 odds; "
        "Section 7.1, eqs. (7.1)-(7.3), the continuous approximation"
    ),
)
_MERTON = Reference(
    key="merton1969",
    citation=(
        "Merton, R. C. (1969). Lifetime portfolio selection under uncertainty: "
        "the continuous-time case. The Review of Economics and Statistics, 51(3), "
        "247-257."
    ),
    doi="10.2307/1926560",
    locator="Section IV, eqs. (25) and (29'), constant relative risk aversion",
)
_PRATT = Reference(
    key="pratt1964",
    citation=(
        "Pratt, J. W. (1964). Risk aversion in the small and in the large. "
        "Econometrica, 32(1/2), 122-136."
    ),
    doi="10.2307/1913738",
    locator="The definition of the risk premium, the paper's opening equation",
)


@model(
    id="portfolio.utility",
    version=1,
    title="Utility, risky share and Kelly fraction",
    summary=(
        "Mean-variance utility, the utility-maximizing risky share, the CRRA "
        "certainty equivalent of a gamble, and the Kelly fraction."
    ),
    formula=(
        r"U = E[r] - \tfrac{1}{2} A \sigma^2",
        r"y^* = \frac{E[r] - r_f}{A \sigma^2}",
        (
            r"1 + CE = \Big(\sum_i p_i (1 + r_i)^{1 - \gamma}\Big)^{1/(1 - \gamma)}, "
            r"\quad \gamma = 1:\ 1 + CE = e^{\sum_i p_i \ln(1 + r_i)}"
        ),
        (
            r"f^*_{bet} = p - \frac{1 - p}{b}, \quad f^*_{asset} = \frac{\mu - r}"
            r"{\sigma^2}, \quad g = r + f(\mu - r) - \tfrac{1}{2} f^2 \sigma^2"
        ),
    ),
    assumptions=(
        (
            "Mean-variance utility and the risky share take returns and "
            "volatilities a year as decimals, and a risk aversion A on the scale "
            "where U = E - A sigma^2 / 2."
        ),
        (
            "The certainty equivalent takes discrete outcomes whose probabilities "
            "sum to one (within 1e-9; they are rescaled to exactly one)."
        ),
        (
            "A discrete bet wins b per unit staked with probability p and loses the "
            "stake otherwise; a continuous asset follows geometric Brownian motion "
            "with the given drift and volatility, rebalanced continuously."
        ),
        (
            "Every output is a formula result for the parameters the user "
            "supplies, the same for every user: not investment advice, and not "
            "advice to take any allocation or bet."
        ),
    ),
    limitations=(
        (
            "The risky share and the continuous Kelly fraction need a volatility of "
            "at least 1% and returns within [-1, 1] a year, which keeps them "
            "representable; leverage and short sales are unconstrained."
        ),
        (
            "Full Kelly assumes the probabilities and odds, or drift and "
            "volatility, are known exactly; with estimation error it over-bets, "
            "which is why fractional Kelly is offered."
        ),
    ),
    references=(_KELLY, _THORP, _MERTON, _PRATT),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("utility", "risk aversion", "certainty equivalent", "kelly"),
    invariants=(
        Invariant(
            id="utility_falls_as_aversion_rises",
            statement=(
                "Mean-variance utility, and the CRRA certainty equivalent, never "
                "rise as risk aversion rises."
            ),
        ),
        Invariant(
            id="optimal_share_inverse_in_aversion",
            statement=(
                "The optimal risky share times the risk aversion does not depend "
                "on the risk aversion: doubling A halves the share."
            ),
        ),
        Invariant(
            id="kelly_zero_without_edge",
            statement=(
                "With no edge (b p = 1 - p for a bet, a drift equal to the "
                "risk-free rate for an asset) the Kelly fraction is zero."
            ),
        ),
        Invariant(
            id="certainty_equivalent_below_mean",
            statement=(
                "The certainty equivalent lies between the lowest outcome and the "
                "expected return, so the risk premium is never negative."
            ),
        ),
    ),
    examples=(
        Example(
            name="utility_of_a_risky_portfolio",
            inputs={
                "calculation": "mean_variance_utility",
                "expected_return": 0.08,
                "volatility": 0.2,
                "risk_aversion": 3,
            },
        ),
        Example(
            name="risky_share",
            inputs={
                "calculation": "optimal_risky_share",
                "expected_return": 0.08,
                "risk_free_rate": 0.03,
                "volatility": 0.2,
                "risk_aversion": 4,
            },
        ),
        Example(
            name="fifty_fifty_gamble",
            inputs={
                "calculation": "certainty_equivalent",
                "outcomes": [0.5, -0.2],
                "probabilities": [0.5, 0.5],
                "relative_risk_aversion": 2,
            },
        ),
        Example(
            name="even_money_bet",
            inputs={"calculation": "kelly", "win_probability": 0.55, "odds": 1},
        ),
        Example(
            name="half_kelly_asset",
            inputs={
                "calculation": "kelly",
                "drift": 0.08,
                "risk_free_rate": 0.03,
                "volatility": 0.2,
                "multiplier": 0.5,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def utility(inputs: UtilityInputs) -> UtilityOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], UtilityOutputs]]] = {
    MeanVarianceUtilityInputs: _mean_variance_utility,
    OptimalRiskyShareInputs: _optimal_risky_share,
    CertaintyEquivalentInputs: _certainty_equivalent,
    KellyInputs: _kelly,
}
