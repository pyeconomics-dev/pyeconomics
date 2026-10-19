# src/pyeconomics/models/macro/debt_dynamics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Public debt dynamics: ``macro.debt_dynamics``.

The debt-to-GDP ratio evolves by the government budget identity

.. math:: d_t = d_{t-1} \frac{1 + i_t}{1 + g_t} - p_t,

with :math:`d` debt over GDP, :math:`i_t` the effective nominal interest rate
(interest paid in period :math:`t` over the debt at the end of :math:`t - 1`),
:math:`g_t` nominal GDP growth and :math:`p_t` the primary balance over GDP (a
surplus is positive). From an initial ratio and paths of the three, the model
returns the ratio's path, the interest-growth differential :math:`i_t - g_t`
("r - g", nominal) and the primary balance that would hold the ratio where it
stood, :math:`p^*_t = d_{t-1} (i_t - g_t) / (1 + g_t)`. When :math:`i < g` a
primary deficit can be run with a stable ratio.
"""

from __future__ import annotations

from typing import Annotated, Final, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    Ratio,
    Reference,
    model,
)

__all__ = ["debt_dynamics"]

#: The longest path: a century of years.
PERIODS_MAX: Final = 100
#: Interest from -10% to 50%, nominal growth from -50% to 50%, a primary balance
#: within half of GDP, and an initial ratio up to ten times GDP.
_INTEREST_MIN: Final = -0.1
_INTEREST_MAX: Final = 0.5
_GROWTH_MIN: Final = -0.5
_GROWTH_MAX: Final = 0.5
_BALANCE_MAX: Final = 0.5
_RATIO_MAX: Final = 10.0
#: A path can compound past any sensible ratio (a growth factor of three a year
#: for a century); beyond a million times GDP the model raises DomainError.
_PATH_MAX: Final = 1e6

_Interest = Annotated[Rate, Field(ge=_INTEREST_MIN, le=_INTEREST_MAX)]
_Growth = Annotated[Rate, Field(ge=_GROWTH_MIN, le=_GROWTH_MAX)]
_Balance = Annotated[Ratio, Field(ge=-_BALANCE_MAX, le=_BALANCE_MAX)]
_PathRatio = Annotated[Ratio, Field(ge=-_PATH_MAX, le=_PATH_MAX)]
_Differential = Annotated[Rate, Field(ge=-1.0, le=1.0)]
#: The stabilizing balance is a ratio below the cap times (i - g) / (1 + g),
#: which is at most 1.0 / 0.5.
_Stabilizing = Annotated[Ratio, Field(ge=-2 * _PATH_MAX, le=2 * _PATH_MAX)]


class DebtDynamicsInputs(ModelInputs):
    initial_ratio: Ratio = Field(
        ge=0.0,
        le=_RATIO_MAX,
        description="Debt over GDP at the start, d0 (1.0 is 100% of GDP)",
    )
    interest_rate: Annotated[tuple[_Interest, ...], ARRAY_INPUT] = Field(
        min_length=1,
        max_length=PERIODS_MAX,
        description=(
            "The effective nominal interest rate each period: interest paid over "
            "the debt at the end of the period before"
        ),
    )
    nominal_growth: Annotated[tuple[_Growth, ...], ARRAY_INPUT] = Field(
        min_length=1,
        max_length=PERIODS_MAX,
        description="Nominal GDP growth each period",
    )
    primary_balance: Annotated[tuple[_Balance, ...], ARRAY_INPUT] = Field(
        min_length=1,
        max_length=PERIODS_MAX,
        description=(
            "The primary balance over GDP each period: revenue less non-interest "
            "spending, a deficit negative"
        ),
    )

    @model_validator(mode="after")
    def _one_path_length(self) -> Self:
        lengths = {
            len(self.interest_rate),
            len(self.nominal_growth),
            len(self.primary_balance),
        }
        if len(lengths) != 1:
            msg = (
                "interest_rate, nominal_growth and primary_balance need one value "
                f"per period each, not {len(self.interest_rate)}, "
                f"{len(self.nominal_growth)} and {len(self.primary_balance)}"
            )
            raise ValueError(msg)
        return self


class DebtDynamicsOutputs(ModelOutputs):
    debt_ratio_path: Annotated[tuple[_PathRatio, ...], ARRAY_INPUT] = Field(
        max_length=PERIODS_MAX, description="Debt over GDP at the end of each period"
    )
    final_ratio: Ratio = Field(
        ge=-_PATH_MAX, le=_PATH_MAX, description="Debt over GDP at the end"
    )
    change_in_ratio: Ratio = Field(
        ge=-2 * _PATH_MAX,
        le=2 * _PATH_MAX,
        description="The final ratio less the initial one",
    )
    interest_growth_differential: Annotated[tuple[_Differential, ...], ARRAY_INPUT] = (
        Field(
            max_length=PERIODS_MAX,
            description="r - g each period: the interest rate less nominal growth",
        )
    )
    stabilizing_balance: Annotated[tuple[_Stabilizing, ...], ARRAY_INPUT] = Field(
        max_length=PERIODS_MAX,
        description=(
            "The primary balance over GDP that would hold each period's ratio at "
            "the ratio before it"
        ),
    )


_BLANCHARD = Reference(
    key="blanchard",
    citation=(
        "Blanchard, O. (2019). Public Debt and Low Interest Rates. American "
        "Economic Review, 109(4), 1197-1229."
    ),
    doi="10.1257/aer.109.4.1197",
    locator="Section I: the debt dynamics when the safe rate is below growth",
)
_ESCOLANO = Reference(
    key="escolano2010",
    citation=(
        "Escolano, J. (2010). A Practical Guide to Public Debt Dynamics, Fiscal "
        "Sustainability, and Cyclical Adjustment of Budgetary Aggregates. "
        "International Monetary Fund, Technical Notes and Manuals 10/02."
    ),
    doi="10.5089/9781462396955.005",
    locator="Section II: the debt-ratio equation and the debt-stabilizing balance",
)
_CBO = Reference(
    key="cbo_ltbo",
    citation=(
        "Congressional Budget Office. The Long-Term Budget Outlook, and its "
        "supplemental long-term budget projections."
    ),
    url="https://www.cbo.gov/topics/budget/long-term-budget-projections",
    locator="Debt held by the public, net interest, primary deficits and GDP",
)


@model(
    id="macro.debt_dynamics",
    version=1,
    title="Public debt dynamics",
    summary=(
        "The path of debt to GDP from an initial ratio and paths of the effective "
        "interest rate, nominal growth and the primary balance, with r - g and the "
        "debt-stabilizing primary balance."
    ),
    formula=(
        r"d_t = d_{t-1}\,\frac{1 + i_t}{1 + g_t} - p_t",
        r"p^*_t = d_{t-1}\,\frac{i_t - g_t}{1 + g_t}, \quad r - g = i_t - g_t",
    ),
    assumptions=(
        (
            "The identity holds when debt changes only by interest and the primary "
            "balance; anything else that moves debt (other means of financing, "
            "valuation changes) is outside it."
        ),
        (
            "Rates and growth are per period, and the primary balance is a share "
            "of that period's GDP; the stabilizing balance holds the ratio at the "
            "one the path reached the period before."
        ),
        (
            "Profile: default binds US federal debt over GDP, the Treasury's "
            "average interest rate on its debt, nominal GDP growth over four "
            "quarters and the federal primary balance over GDP: a one-year path "
            "from the latest data."
        ),
    ),
    limitations=(
        (
            "A projection is only as good as its paths: the model assumes them and "
            "does not forecast rates, growth or policy."
        ),
        (
            "The default profile's debt is total public debt (including debt the "
            "government holds) and its interest rate the Treasury's average on "
            "interest-bearing debt, not CBO's debt held by the public."
        ),
        ("A path that compounds past a million times GDP raises DomainError."),
    ),
    references=(_ESCOLANO, _BLANCHARD, _CBO),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("public debt", "fiscal policy", "r minus g", "debt sustainability"),
    invariants=(
        Invariant(
            id="stabilizing_balance_holds_the_ratio",
            statement=(
                "Running each period's debt-stabilizing primary balance keeps the "
                "ratio at its initial value."
            ),
        ),
        Invariant(
            id="zero_balance_and_r_equal_g_hold_the_ratio",
            statement=(
                "With a zero primary balance and the interest rate equal to growth, "
                "the ratio does not move."
            ),
        ),
        Invariant(
            id="debt_rises_with_the_interest_rate",
            statement=(
                "With positive debt and no primary surplus, a higher interest rate "
                "in every period never lowers the ratio at any period."
            ),
        ),
    ),
    examples=(
        Example(
            name="five_year_projection",
            inputs={
                "initial_ratio": 1.0,
                "interest_rate": [0.033, 0.034, 0.035, 0.036, 0.036],
                "nominal_growth": [0.045, 0.042, 0.04, 0.039, 0.039],
                "primary_balance": [-0.03, -0.028, -0.027, -0.027, -0.026],
            },
            note="A ratio near 100% of GDP, with r - g below zero.",
        ),
    ),
    bindings=(
        Binding("initial_ratio", "us.fiscal.debt_to_gdp"),
        Binding(
            "interest_rate",
            "us.fiscal.average_interest_rate",
            as_of=AsOf.WINDOW,
            window=1,
        ),
        Binding(
            "nominal_growth", "us.output.nominal_gdp.yoy", as_of=AsOf.WINDOW, window=1
        ),
        Binding(
            "primary_balance",
            "us.fiscal.primary_balance_to_gdp",
            as_of=AsOf.WINDOW,
            window=1,
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def debt_dynamics(inputs: DebtDynamicsInputs) -> DebtDynamicsOutputs:
    """Run the debt-ratio identity along the paths."""
    ratio = inputs.initial_ratio
    path: list[float] = []
    stabilizing: list[float] = []
    for rate, growth, balance in zip(
        inputs.interest_rate,
        inputs.nominal_growth,
        inputs.primary_balance,
        strict=True,
    ):
        stabilizing.append(ratio * (rate - growth) / (1.0 + growth))
        # The growth factor first: with r equal to g it is exactly one.
        ratio = ratio * ((1.0 + rate) / (1.0 + growth)) - balance
        if not abs(ratio) <= _PATH_MAX:
            msg = (
                f"the debt ratio passes {_PATH_MAX:g} times GDP: the paths compound "
                "past anything this model represents"
            )
            raise DomainError(msg)
        path.append(ratio)
    rates = zip(inputs.interest_rate, inputs.nominal_growth, strict=True)
    return DebtDynamicsOutputs(
        debt_ratio_path=tuple(path),
        final_ratio=path[-1],
        change_in_ratio=path[-1] - inputs.initial_ratio,
        interest_growth_differential=tuple(i - g for i, g in rates),
        stabilizing_balance=tuple(stabilizing),
    )
