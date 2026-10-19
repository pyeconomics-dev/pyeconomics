# src/pyeconomics/models/macro/solow_growth.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The Solow growth model: ``macro.solow_growth``.

Two calculations, discriminated on ``calculation``:

- ``steady_state``: Solow's (1956) model with a Cobb-Douglas technology
  :math:`y = k^\alpha` in output and capital per effective worker, saving rate
  :math:`s`, depreciation :math:`\delta`, population growth :math:`n` and
  labour-augmenting technology growing at :math:`g`. Capital settles where saving
  covers effective depreciation, :math:`s k^\alpha = (n + g + \delta) k`, so
  :math:`k^* = (s / (n + g + \delta))^{1/(1-\alpha)}`; consumption is highest at
  the golden-rule saving rate :math:`s = \alpha`; near the steady state the gap
  closes at the rate :math:`\lambda = (1 - \alpha)(n + g + \delta)` (Mankiw, Romer
  and Weil 1992), with a half-life of :math:`\ln 2 / \lambda`.
- ``growth_accounting``: Solow's (1957) decomposition of output growth into the
  contributions of capital, labour and human capital, each weighted by its share
  of income, and the residual, total factor productivity (TFP). With ``log``
  growth (the default) each period's growth is :math:`\ln(1 + g)`; ``discrete``
  is Solow's own arithmetic on the growth rates, whose TFP index he cumulated as
  :math:`A_t = A_{t-1}(1 + \Delta A / A)`.

Growth rates are decimals per period, and shares are fractions of income.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    Ratio,
    Reference,
    Return,
    Years,
    model,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["solow_growth"]

#: The longest growth-accounting sample: five centuries of years.
PERIODS_MAX: Final = 500
#: A capital share strictly inside (0, 1); the exponent 1 / (1 - alpha) is then at
#: most 20.
_SHARE_MIN: Final = 0.01
_SHARE_MAX: Final = 0.95
_DEPRECIATION_MAX: Final = 0.5
_GROWTH_MIN: Final = -0.1
_GROWTH_MAX: Final = 0.2
#: Capital, output and consumption per effective worker beyond this, and a
#: half-life beyond a million years, mean effective depreciation is too close to
#: zero for a steady state the model can represent: DomainError.
_LEVEL_MAX: Final = 1e15
_HALF_LIFE_MAX: Final = 1e6
#: A period's growth: a fall of 99% to a rise of 1,000%.
_PERIOD_GROWTH_MIN: Final = -0.99
_PERIOD_GROWTH_MAX: Final = 10.0
_CONTRIBUTION: Final = 100.0
_TFP_INDEX_MAX: Final = 1e15
#: Output growth this close to zero leaves TFP's share of it undefined.
_NO_GROWTH: Final = 1e-12

type Method = Literal["log", "discrete"]


# --- inputs ------------------------------------------------------------------


class SteadyStateInputs(ModelInputs):
    """Solow's (1956) model with Cobb-Douglas technology."""

    calculation: Literal["steady_state"] = Field(
        "steady_state", description="The steady state and convergence"
    )
    saving_rate: Ratio = Field(
        ge=0.0, le=1.0, description="s, the share of output saved and invested"
    )
    capital_share: Ratio = Field(
        1 / 3,
        ge=_SHARE_MIN,
        le=_SHARE_MAX,
        description="Alpha, capital's share of income (the Cobb-Douglas exponent)",
    )
    depreciation: Rate = Field(
        0.05, ge=0.0, le=_DEPRECIATION_MAX, description="Delta, per year"
    )
    population_growth: Rate = Field(
        0.01, ge=_GROWTH_MIN, le=_GROWTH_MAX, description="n, per year"
    )
    technology_growth: Rate = Field(
        0.02,
        ge=_GROWTH_MIN,
        le=_GROWTH_MAX,
        description="g, the growth of labour-augmenting technology per year",
    )


#: A growth rate is a return on the level, as ``pct_change`` reads it.
_Growth = Annotated[Return, Field(ge=_PERIOD_GROWTH_MIN, le=_PERIOD_GROWTH_MAX)]
_Growths = Annotated[tuple[_Growth, ...], ARRAY_INPUT]
_Shares = Annotated[tuple[Annotated[Rate, Field(ge=0.0, le=1.0)], ...], ARRAY_INPUT]


def _growths(description: str, *, required: bool = True) -> Any:  # noqa: ANN401
    if required:
        return Field(min_length=1, max_length=PERIODS_MAX, description=description)
    return Field(None, min_length=1, max_length=PERIODS_MAX, description=description)


class GrowthAccountingInputs(ModelInputs):
    """Solow's (1957) growth accounting over a run of periods."""

    calculation: Literal["growth_accounting"] = Field(
        "growth_accounting", description="Growth accounting and the TFP residual"
    )
    output_growth: _Growths = _growths(
        "Growth of real output each period, Y(t) / Y(t-1) - 1"
    )
    capital_growth: _Growths = _growths("Growth of the capital stock each period")
    labour_growth: _Growths = _growths(
        "Growth of labour input (persons or hours) each period"
    )
    human_capital_growth: _Growths | None = _growths(
        "Growth of human capital per worker each period; none when left out",
        required=False,
    )
    labour_share: _Shares | None = Field(
        None,
        min_length=1,
        max_length=PERIODS_MAX,
        description="Labour's share of income each period; capital's is one less it",
    )
    capital_share: Ratio | None = Field(
        None,
        ge=0.0,
        le=1.0,
        description="A constant capital share, in place of labour_share",
    )
    method: Method = Field(
        "log",
        description=(
            "'log' accounts in log growth, ln(1 + g); 'discrete' in the growth "
            "rates themselves, Solow's (1957) arithmetic"
        ),
    )

    @model_validator(mode="after")
    def _aligned(self) -> Self:
        if (self.labour_share is None) == (self.capital_share is None):
            msg = "give one of labour_share (each period) and capital_share"
            raise ValueError(msg)
        periods = len(self.output_growth)
        for name in (
            "capital_growth",
            "labour_growth",
            "human_capital_growth",
            "labour_share",
        ):
            value = getattr(self, name)
            if value is not None and len(value) != periods:
                msg = f"{name} has {len(value)} periods; output_growth has {periods}"
                raise ValueError(msg)
        return self


SolowGrowthInputs = Annotated[
    SteadyStateInputs | GrowthAccountingInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------

_Level = Annotated[Ratio, Field(ge=0.0, le=_LEVEL_MAX)]


class SteadyStateOutputs(ModelOutputs):
    calculation: Literal["steady_state"] = Field(
        "steady_state", description="The steady state and convergence"
    )
    capital_per_effective_worker: _Level = Field(description="k*")
    output_per_effective_worker: _Level = Field(description="y* = k* ** alpha")
    consumption_per_effective_worker: _Level = Field(description="c* = (1 - s) y*")
    capital_output_ratio: _Level = Field(description="k* / y* = s / (n + g + delta)")
    golden_rule_saving_rate: Ratio = Field(
        ge=0.0, le=1.0, description="The saving rate that maximizes c*: alpha"
    )
    golden_rule_capital: _Level | None = Field(
        description="k* at the golden-rule rate; None when it passes the bound"
    )
    golden_rule_consumption: _Level | None = Field(
        description="c* at the golden-rule rate; None when its capital does"
    )
    convergence_speed: Rate = Field(
        gt=0.0,
        le=1.0,
        description=(
            "Lambda = (1 - alpha)(n + g + delta): the share of the gap to the "
            "steady state closed a year"
        ),
    )
    half_life: Years = Field(
        gt=0.0,
        le=_HALF_LIFE_MAX,
        description="Years to close half the gap to the steady state, ln 2 / lambda",
    )


_Contribution = Annotated[Rate, Field(ge=-_CONTRIBUTION, le=_CONTRIBUTION)]


class GrowthAccountingOutputs(ModelOutputs):
    calculation: Literal["growth_accounting"] = Field(
        "growth_accounting", description="Growth accounting and the TFP residual"
    )
    output_growth: _Contribution = Field(
        description="Output growth, the average per period"
    )
    capital_contribution: _Contribution = Field(
        description="Capital's share times capital growth, the average per period"
    )
    labour_contribution: _Contribution = Field(
        description="Labour's share times labour growth, the average per period"
    )
    human_capital_contribution: _Contribution = Field(
        description="Labour's share times human capital growth, the average per period"
    )
    tfp_growth: _Contribution = Field(
        description="The residual: output growth less the contributions"
    )
    tfp_share: Ratio | None = Field(
        ge=-1e15,
        le=1e15,
        description="TFP growth over output growth; None with no output growth",
    )
    tfp_index: Annotated[
        tuple[Annotated[IndexLevel, Field(gt=0.0, le=_TFP_INDEX_MAX)], ...],
        ARRAY_INPUT,
    ] = Field(
        max_length=PERIODS_MAX,
        description="TFP at the end of each period, relative to its start (1.0)",
    )
    average_capital_share: Ratio = Field(
        ge=0.0, le=1.0, description="The capital share, averaged over the periods"
    )
    periods: Count = Field(ge=1, le=PERIODS_MAX, description="Periods accounted for")


SolowGrowthOutputs = Annotated[
    SteadyStateOutputs | GrowthAccountingOutputs, Field(discriminator="calculation")
]


# --- the arithmetic ------------------------------------------------------------


def _steady_capital(saving: float, share: float, effective: float) -> float | None:
    """Return (s / (n + g + delta)) ** (1 / (1 - alpha)), or None past the bound."""
    if saving == 0:
        return 0.0
    log_level = math.log(saving / effective) / (1.0 - share)
    if log_level > math.log(_LEVEL_MAX):
        return None
    return math.exp(log_level)


def _steady_state(inputs: SteadyStateInputs) -> SteadyStateOutputs:
    alpha, s = inputs.capital_share, inputs.saving_rate
    effective = (
        inputs.population_growth + inputs.technology_growth + inputs.depreciation
    )
    if effective <= 0:
        msg = (
            "with n + g + delta at or below zero, capital per effective worker "
            "grows without bound: there is no steady state"
        )
        raise DomainError(msg)
    speed = (1.0 - alpha) * effective
    half_life = math.log(2.0) / speed
    if half_life > _HALF_LIFE_MAX:
        msg = (
            f"the half-life passes {_HALF_LIFE_MAX:g} years: no practical steady state"
        )
        raise DomainError(msg)
    capital = _steady_capital(s, alpha, effective)
    if capital is None:
        msg = (
            f"capital per effective worker, (s / (n + g + delta)) ** (1 / (1 - "
            f"alpha)), would pass {_LEVEL_MAX:g}: the saving rate is too large for "
            "effective depreciation this small at this capital share"
        )
        raise DomainError(msg)
    output = capital**alpha
    golden = _steady_capital(alpha, alpha, effective)
    golden_consumption = None
    if golden is None:
        warn(
            "golden_rule_unrepresentable",
            f"golden-rule capital would pass {_LEVEL_MAX:g} at this capital share "
            "and effective depreciation, so the golden rule's levels are None",
        )
    else:
        golden_consumption = (1.0 - alpha) * golden**alpha
    return SteadyStateOutputs(
        capital_per_effective_worker=capital,
        output_per_effective_worker=output,
        consumption_per_effective_worker=(1.0 - s) * output,
        capital_output_ratio=s / effective,
        golden_rule_saving_rate=alpha,
        golden_rule_capital=golden,
        golden_rule_consumption=golden_consumption,
        convergence_speed=speed,
        half_life=half_life,
    )


def _accounted(
    inputs: GrowthAccountingInputs,
) -> tuple[list[float], list[float], list[float], list[float], list[float]]:
    """Return each period's capital share and growth of output, K, L and h."""
    periods = len(inputs.output_growth)
    if inputs.labour_share is not None:
        shares = [1.0 - share for share in inputs.labour_share]
    else:
        shares = [inputs.capital_share or 0.0] * periods
    human = inputs.human_capital_growth or (0.0,) * periods

    def growth(values: tuple[float, ...]) -> list[float]:
        if inputs.method == "log":
            return [math.log1p(v) for v in values]
        return list(values)

    return (
        shares,
        growth(inputs.output_growth),
        growth(inputs.capital_growth),
        growth(inputs.labour_growth),
        growth(tuple(human)),
    )


def _tfp_index(residuals: list[float], method: Method) -> tuple[float, ...]:
    levels: list[float] = []
    level = 0.0 if method == "log" else 1.0
    for residual in residuals:
        if method == "log":
            level += residual
            value = math.exp(level) if level < math.log(_TFP_INDEX_MAX) else math.inf
        else:
            level *= 1.0 + residual
            value = level
        if not 0 < value <= _TFP_INDEX_MAX:
            msg = (
                "the TFP index leaves (0, 1e15]: the residual falls by 100% or more "
                "in a period, or compounds beyond representation"
            )
            raise DomainError(msg)
        levels.append(value)
    return tuple(levels)


def _growth_accounting(inputs: GrowthAccountingInputs) -> GrowthAccountingOutputs:
    shares, output, capital, labour, human = _accounted(inputs)
    periods = len(output)
    capital_terms = [a * k for a, k in zip(shares, capital, strict=True)]
    labour_terms = [(1.0 - a) * n for a, n in zip(shares, labour, strict=True)]
    human_terms = [(1.0 - a) * h for a, h in zip(shares, human, strict=True)]
    residuals = [
        y - k - n - h
        for y, k, n, h in zip(
            output, capital_terms, labour_terms, human_terms, strict=True
        )
    ]

    def mean(values: list[float]) -> float:
        return math.fsum(values) / periods

    output_growth = mean(output)
    tfp = mean(residuals)
    share = None
    if abs(output_growth) < _NO_GROWTH:
        warn("no_output_growth", "output did not grow, so TFP's share is undefined")
    else:
        share = tfp / output_growth
    return GrowthAccountingOutputs(
        output_growth=output_growth,
        capital_contribution=mean(capital_terms),
        labour_contribution=mean(labour_terms),
        human_capital_contribution=mean(human_terms),
        tfp_growth=tfp,
        tfp_share=share,
        tfp_index=_tfp_index(residuals, inputs.method),
        average_capital_share=mean(shares),
        periods=periods,
    )


# --- the model -----------------------------------------------------------------

_SOLOW_1956 = Reference(
    key="solow1956",
    citation=(
        "Solow, R. M. (1956). A Contribution to the Theory of Economic Growth. "
        "Quarterly Journal of Economics, 70(1), 65-94."
    ),
    doi="10.2307/1884513",
    locator="Section IV, the Cobb-Douglas example and its equilibrium ratio",
)
_SOLOW_1957 = Reference(
    key="solow1957",
    citation=(
        "Solow, R. M. (1957). Technical Change and the Aggregate Production "
        "Function. Review of Economics and Statistics, 39(3), 312-320."
    ),
    doi="10.2307/1926047",
    locator="Equation (4) and Table 1: the residual and the index A(t), 1909-1949",
)
_MRW = Reference(
    key="mankiw1992",
    citation=(
        "Mankiw, N. G., Romer, D. and Weil, D. N. (1992). A Contribution to the "
        "Empirics of Economic Growth. Quarterly Journal of Economics, 107(2), "
        "407-437."
    ),
    doi="10.2307/2118477",
    locator="Section III: the speed of convergence, (n + g + delta)(1 - alpha)",
)
_PHELPS = Reference(
    key="phelps1961",
    citation=(
        "Phelps, E. S. (1961). The Golden Rule of Accumulation: A Fable for "
        "Growthmen. American Economic Review, 51(4), 638-643; reprinted in "
        "Studies in Macroeconomic Theory, Vol. 1, Academic Press (1980), 23-28."
    ),
    doi="10.1016/b978-0-12-554002-5.50007-8",
    locator="The saving rate that maximizes steady-state consumption",
)
_PWT = Reference(
    key="feenstra2015",
    citation=(
        "Feenstra, R. C., Inklaar, R. and Timmer, M. P. (2015). The Next "
        "Generation of the Penn World Table. American Economic Review, 105(10), "
        "3150-3182."
    ),
    doi="10.1257/aer.20130954",
    locator="Real GDP, capital stock, persons engaged, human capital, labour share",
)

_ECONOMIES: Final = ("us", "ca", "de", "fr", "gb", "it", "jp")


def _pwt_bindings(economy: str) -> tuple[Binding, ...]:
    """Bind 30 years of an economy's PWT growth rates and labour share."""
    profile = "default" if economy == "us" else economy
    growth = (
        ("output_growth", "rgdpna"),
        ("capital_growth", "rnna"),
        ("labour_growth", "emp"),
        ("human_capital_growth", "hc"),
    )
    return (
        *(
            Binding(
                field,
                f"pwt.{variable}.{economy}.annual",
                transform="pct_change",
                as_of=AsOf.WINDOW,
                window=30,
                profile=profile,
            )
            for field, variable in growth
        ),
        Binding(
            "labour_share",
            f"pwt.labsh.{economy}.annual",
            as_of=AsOf.WINDOW,
            window=30,
            profile=profile,
        ),
    )


@model(
    id="macro.solow_growth",
    version=1,
    title="Solow growth model",
    summary=(
        "The Solow steady state with Cobb-Douglas technology, the golden rule and "
        "the speed of convergence, and growth accounting into capital, labour, "
        "human capital and the TFP residual."
    ),
    formula=(
        (
            r"k^* = \left(\frac{s}{n + g + \delta}\right)^{\frac{1}{1-\alpha}}, "
            r"\quad y^* = k^{*\alpha}, \quad c^* = (1 - s)\,y^*, \quad "
            r"s_{gold} = \alpha"
        ),
        (
            r"\lambda = (1 - \alpha)(n + g + \delta), \quad "
            r"t_{1/2} = \frac{\ln 2}{\lambda}"
        ),
        (
            r"\Delta \ln Y = \alpha\,\Delta \ln K + (1 - \alpha)(\Delta \ln L + "
            r"\Delta \ln h) + \Delta \ln A"
        ),
    ),
    assumptions=(
        (
            "Constant returns and Cobb-Douglas technology, with technology "
            "labour-augmenting; the steady state is in units of effective labour."
        ),
        (
            "Growth accounting weights each period's input growth by that "
            "period's share (one less the labour share, or a constant capital "
            "share), averages over the periods, and leaves TFP as the residual."
        ),
        (
            "Profiles: default binds 30 years of the Penn World Table's US growth "
            "of real GDP (rgdpna), the capital stock (rnna), persons engaged (emp) "
            "and human capital (hc), and its labour share; ca, de, fr, gb, it and "
            "jp bind the same for those economies."
        ),
    ),
    limitations=(
        (
            "The residual measures everything the inputs miss, mismeasurement "
            "included, not technology alone."
        ),
        (
            "The PWT labour share is the share of the year that ends the growth "
            "period, not a two-year average; persons engaged are not hours."
        ),
        (
            "A steady state needs n + g + delta above zero; one that would pass "
            "1e15 per effective worker, or a half-life past a million years, "
            "raises DomainError, as does a TFP index that leaves (0, 1e15]. A "
            "golden rule past 1e15 leaves its levels None, with a warning."
        ),
    ),
    references=(_SOLOW_1956, _SOLOW_1957, _MRW, _PHELPS, _PWT),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=(
        "solow model",
        "economic growth",
        "growth accounting",
        "total factor productivity",
        "golden rule",
    ),
    invariants=(
        Invariant(
            id="steady_state_capital_rises_with_saving",
            statement="A higher saving rate never lowers steady-state capital.",
        ),
        Invariant(
            id="golden_rule_maximizes_steady_state_consumption",
            statement=(
                "No saving rate gives more steady-state consumption than the "
                "golden-rule rate, alpha."
            ),
        ),
        Invariant(
            id="contributions_sum_to_output_growth",
            statement=(
                "Capital, labour and human capital contributions and TFP growth "
                "add up to output growth."
            ),
        ),
    ),
    examples=(
        Example(
            name="textbook_steady_state",
            inputs={"calculation": "steady_state", "saving_rate": 0.25},
            note="Alpha of one third, n of 1%, g of 2% and delta of 5% a year.",
        ),
        Example(
            name="growth_accounting",
            inputs={
                "calculation": "growth_accounting",
                "output_growth": [0.025, 0.031, -0.004, 0.022],
                "capital_growth": [0.021, 0.024, 0.018, 0.017],
                "labour_growth": [0.012, 0.015, -0.02, 0.011],
                "human_capital_growth": [0.004, 0.004, 0.004, 0.004],
                "labour_share": [0.6, 0.6, 0.61, 0.6],
            },
        ),
    ),
    bindings=tuple(b for economy in _ECONOMIES for b in _pwt_bindings(economy)),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def solow_growth(inputs: SolowGrowthInputs) -> SolowGrowthOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], SolowGrowthOutputs]]] = {
    SteadyStateInputs: _steady_state,
    GrowthAccountingInputs: _growth_accounting,
}
