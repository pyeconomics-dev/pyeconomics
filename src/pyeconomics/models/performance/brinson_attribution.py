# src/pyeconomics/models/performance/brinson_attribution.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Brinson attribution, linked over periods: ``performance.brinson_attribution``.

From each period's sector weights and returns, for the portfolio
(:math:`w^p_i, r^p_i`) and its benchmark (:math:`w^b_i, r^b_i`), with
:math:`R = \sum w^p_i r^p_i` and :math:`B = \sum w^b_i r^b_i`, the active
return :math:`R - B` splits into three effects per sector. Two calculations,
discriminated on ``calculation``, differ in the allocation effect:

- ``bhb`` (Brinson, Hood and Beebower, 1986): allocation
  :math:`(w^p_i - w^b_i) r^b_i`;
- ``brinson_fachler`` (Brinson and Fachler, 1985): allocation
  :math:`(w^p_i - w^b_i)(r^b_i - B)`, against the total benchmark return, so
  overweighting a sector that beat the benchmark adds value;

and share selection :math:`w^b_i (r^p_i - r^b_i)` and interaction
:math:`(w^p_i - w^b_i)(r^p_i - r^b_i)`. Each period's effects sum to that
period's :math:`R_t - B_t`.

Over several periods the effects are linked with Carino's (1999) logarithmic
method: each period's effects are scaled by :math:`k_t / k`, where
:math:`k_t = \ln\frac{1 + R_t}{1 + B_t} / (R_t - B_t)` and :math:`k` is the
same for the compound returns (:math:`1 / (1 + B)` when the two are equal). The
linked effects then sum to the difference of the compound returns,
:math:`\prod (1 + R_t) - \prod (1 + B_t)`. Other linking methods (Menchero,
GRAP) are Phase 7's.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

import numpy as np
from pydantic import Field, model_validator

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Ratio,
    Reference,
    Return,
    compound_return,
    log_return,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.performance._common import MATRIX_INPUT, RETURN_MAX, bounded

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["brinson_attribution"]

#: The most periods: fifty years of months.
_PERIODS_MAX: Final = 600
#: The most sectors (or any other segments) a period may hold.
_SECTORS_MAX: Final = 100
#: How far a period's weights may sum from one before they are rejected; within
#: it, they are rescaled to sum to exactly one.
_WEIGHT_SUM: Final = 1e-6
#: Weights in [0, 1] summing to one and returns in [-1, 100] bound each period's
#: effects: the weights differ by at most 2 in total and the returns by at most
#: 101, so no effect or sum of effects exceeds 202. The period outputs allow
#: 1,000.
_EFFECT_OUT: Final = 1e3
#: The compound returns over many periods can pass 100 (10,000%), and Carino's
#: coefficients grow without bound as a return nears -100%: the linked outputs
#: allow 1e7, and DomainError beyond.
_LINKED_OUT: Final = 1e7

_WeightRow = Annotated[
    tuple[Annotated[Ratio, Field(ge=0.0, le=1.0)], ...],
    Field(min_length=1, max_length=_SECTORS_MAX),
    ARRAY_INPUT,
]
_ReturnRow = Annotated[
    tuple[Annotated[Return, Field(ge=-1.0, le=RETURN_MAX)], ...],
    Field(min_length=1, max_length=_SECTORS_MAX),
    ARRAY_INPUT,
]
_Weights = Annotated[tuple[_WeightRow, ...], MATRIX_INPUT]
_Returns = Annotated[tuple[_ReturnRow, ...], MATRIX_INPUT]


_PeriodReturns = Annotated[
    tuple[Annotated[Return, Field(ge=-1.0, le=RETURN_MAX)], ...], ARRAY_INPUT
]
_PeriodEffects = Annotated[
    tuple[Annotated[Return, Field(ge=-_EFFECT_OUT, le=_EFFECT_OUT)], ...], ARRAY_INPUT
]
_LinkedEffects = Annotated[
    tuple[Annotated[Return, Field(ge=-_LINKED_OUT, le=_LINKED_OUT)], ...], ARRAY_INPUT
]


def _matrix(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(min_length=1, max_length=_PERIODS_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class _Sectors(ModelInputs):
    """Sector weights and returns, one row per period, one column per sector."""

    portfolio_weights: _Weights = _matrix(
        "Portfolio weight of each sector, one row per period; each row sums to one"
    )
    benchmark_weights: _Weights = _matrix(
        "Benchmark weight of each sector, one row per period; each row sums to one"
    )
    portfolio_returns: _Returns = _matrix(
        "Portfolio return in each sector, one row per period"
    )
    benchmark_returns: _Returns = _matrix(
        "Benchmark return in each sector, one row per period"
    )

    @model_validator(mode="after")
    def _one_shape(self) -> Self:
        matrices = {
            "portfolio_weights": self.portfolio_weights,
            "benchmark_weights": self.benchmark_weights,
            "portfolio_returns": self.portfolio_returns,
            "benchmark_returns": self.benchmark_returns,
        }
        periods = len(self.portfolio_weights)
        sectors = len(self.portfolio_weights[0])
        for name, rows in matrices.items():
            if len(rows) != periods or any(len(row) != sectors for row in rows):
                msg = (
                    f"{name} must have {periods} rows of {sectors} sectors, as "
                    "portfolio_weights has"
                )
                raise ValueError(msg)
        for name in ("portfolio_weights", "benchmark_weights"):
            for period, row in enumerate(matrices[name]):
                total = math.fsum(row)
                if abs(total - 1.0) > _WEIGHT_SUM:
                    msg = f"{name} in period {period} sum to {total!r}, not one"
                    raise ValueError(msg)
        return self


class BhbInputs(_Sectors):
    calculation: Literal["bhb"] = Field(
        "bhb", description="Brinson-Hood-Beebower: allocation against zero"
    )


class BrinsonFachlerInputs(_Sectors):
    calculation: Literal["brinson_fachler"] = Field(
        "brinson_fachler",
        description="Brinson-Fachler: allocation against the total benchmark return",
    )


BrinsonAttributionInputs = Annotated[
    BhbInputs | BrinsonFachlerInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------


class _Attribution(ModelOutputs):
    periods: Count = Field(ge=1, le=_PERIODS_MAX, description="Number of periods")
    sectors: Count = Field(ge=1, le=_SECTORS_MAX, description="Number of sectors")
    period_portfolio_returns: _PeriodReturns = Field(
        max_length=_PERIODS_MAX, description="Portfolio return R_t of each period"
    )
    period_benchmark_returns: _PeriodReturns = Field(
        max_length=_PERIODS_MAX, description="Benchmark return B_t of each period"
    )
    period_allocation: _PeriodEffects = Field(
        max_length=_PERIODS_MAX, description="Allocation effect of each period"
    )
    period_selection: _PeriodEffects = Field(
        max_length=_PERIODS_MAX, description="Selection effect of each period"
    )
    period_interaction: _PeriodEffects = Field(
        max_length=_PERIODS_MAX, description="Interaction effect of each period"
    )
    sector_allocation: _LinkedEffects = Field(
        max_length=_SECTORS_MAX, description="Linked allocation effect of each sector"
    )
    sector_selection: _LinkedEffects = Field(
        max_length=_SECTORS_MAX, description="Linked selection effect of each sector"
    )
    sector_interaction: _LinkedEffects = Field(
        max_length=_SECTORS_MAX, description="Linked interaction effect of each sector"
    )
    allocation: Return = Field(
        ge=-_LINKED_OUT, le=_LINKED_OUT, description="Total linked allocation effect"
    )
    selection: Return = Field(
        ge=-_LINKED_OUT, le=_LINKED_OUT, description="Total linked selection effect"
    )
    interaction: Return = Field(
        ge=-_LINKED_OUT, le=_LINKED_OUT, description="Total linked interaction effect"
    )
    portfolio_return: Return = Field(
        ge=-1.0, le=_LINKED_OUT, description="Compound portfolio return"
    )
    benchmark_return: Return = Field(
        ge=-1.0, le=_LINKED_OUT, description="Compound benchmark return"
    )
    active_return: Return = Field(
        ge=-_LINKED_OUT,
        le=_LINKED_OUT,
        description="Compound portfolio return less the compound benchmark return",
    )


class BhbOutputs(_Attribution):
    calculation: Literal["bhb"] = Field(
        "bhb", description="Brinson-Hood-Beebower: allocation against zero"
    )


class BrinsonFachlerOutputs(_Attribution):
    calculation: Literal["brinson_fachler"] = Field(
        "brinson_fachler",
        description="Brinson-Fachler: allocation against the total benchmark return",
    )


BrinsonAttributionOutputs = Annotated[
    BhbOutputs | BrinsonFachlerOutputs, Field(discriminator="calculation")
]


# --- calculations ------------------------------------------------------------


def _rows(rows: tuple[tuple[float, ...], ...]) -> NDArray[np.float64]:
    return np.asarray(rows, dtype=np.float64)


def _log_ratio(portfolio: float, benchmark: float) -> float:
    """Return ln((1 + R) / (1 + B)), accurate when R and B are close."""
    return math.log1p((portfolio - benchmark) / (1.0 + benchmark))


def _coefficient(portfolio: float, benchmark: float) -> float:
    """Return Carino's k_t: ln((1 + R) / (1 + B)) / (R - B), or 1 / (1 + B)."""
    gap = portfolio - benchmark
    if gap == 0:
        return 1.0 / (1.0 + benchmark)
    return _log_ratio(portfolio, benchmark) / gap


def _linking(
    portfolio: NDArray[np.float64], benchmark: NDArray[np.float64]
) -> tuple[NDArray[np.float64], float, float, float]:
    """Return each period's k_t / k, the compound returns and their difference.

    Everything comes from the summed logs. With D = sum ln((1 + R_t) / (1 + B_t))
    and L the larger of the two compound log returns, R - B is
    sign(D) e^L (1 - e^-|D|) and 1 / k = (R - B) / D, so k_t / k is
    k_t e^L (1 - e^-|D|) / |D|: no compound return near -1 is subtracted or
    divided by, and the linked effects sum to R - B as computed.
    """
    total_p = compound_return(portfolio.tolist())
    total_b = compound_return(benchmark.tolist())
    if portfolio.size == 1:
        return np.ones(1), total_p, total_b, total_p - total_b
    if np.any(portfolio <= -1) or np.any(benchmark <= -1):
        msg = (
            "Carino linking takes the logarithm of 1 + R_t and 1 + B_t, so no "
            "period's portfolio or benchmark return may be -100%"
        )
        raise DomainError(msg)
    total_p = bounded(total_p, -1.0, _LINKED_OUT, "compound portfolio return")
    total_b = bounded(total_b, -1.0, _LINKED_OUT, "compound benchmark return")
    pairs = list(zip(portfolio.tolist(), benchmark.tolist(), strict=True))
    gap = math.fsum(_log_ratio(p, b) for p, b in pairs)
    peak = log_return(benchmark.tolist()) + max(gap, 0.0)
    shrink = -math.expm1(-abs(gap))
    active = math.copysign(math.exp(peak) * shrink, gap) if gap else 0.0
    inverse_k = math.exp(peak) * (shrink / abs(gap) if gap else 1.0)
    scale = np.array([_coefficient(p, b) * inverse_k for p, b in pairs])
    return scale, total_p, total_b, active


def _attribute(inputs: _Sectors, *, fachler: bool) -> dict[str, Any]:
    wp, wb = _rows(inputs.portfolio_weights), _rows(inputs.benchmark_weights)
    wp = wp / wp.sum(axis=1, keepdims=True)
    wb = wb / wb.sum(axis=1, keepdims=True)
    rp, rb = _rows(inputs.portfolio_returns), _rows(inputs.benchmark_returns)
    portfolio = (wp * rp).sum(axis=1)
    benchmark = (wb * rb).sum(axis=1)
    # Rescaled weights are convex, so each period's returns lie in the range of
    # its sector returns; rounding must not put them outside [-1, 100].
    portfolio = np.clip(portfolio, -1.0, RETURN_MAX)
    benchmark = np.clip(benchmark, -1.0, RETURN_MAX)
    reference = rb - benchmark[:, None] if fachler else rb
    allocation = (wp - wb) * reference
    selection = wb * (rp - rb)
    interaction = (wp - wb) * (rp - rb)
    scale, total_p, total_b, active = _linking(portfolio, benchmark)

    def linked(effect: NDArray[np.float64], name: str) -> tuple[float, ...]:
        by_sector = (scale[:, None] * effect).sum(axis=0)
        return tuple(
            bounded(float(v), -_LINKED_OUT, _LINKED_OUT, name) for v in by_sector
        )

    sector_allocation = linked(allocation, "linked allocation effect")
    sector_selection = linked(selection, "linked selection effect")
    sector_interaction = linked(interaction, "linked interaction effect")
    return {
        "periods": portfolio.size,
        "sectors": wp.shape[1],
        "period_portfolio_returns": tuple(portfolio.tolist()),
        "period_benchmark_returns": tuple(benchmark.tolist()),
        "period_allocation": tuple(allocation.sum(axis=1).tolist()),
        "period_selection": tuple(selection.sum(axis=1).tolist()),
        "period_interaction": tuple(interaction.sum(axis=1).tolist()),
        "sector_allocation": sector_allocation,
        "sector_selection": sector_selection,
        "sector_interaction": sector_interaction,
        "allocation": bounded(
            math.fsum(sector_allocation), -_LINKED_OUT, _LINKED_OUT, "allocation"
        ),
        "selection": bounded(
            math.fsum(sector_selection), -_LINKED_OUT, _LINKED_OUT, "selection"
        ),
        "interaction": bounded(
            math.fsum(sector_interaction), -_LINKED_OUT, _LINKED_OUT, "interaction"
        ),
        "portfolio_return": total_p,
        "benchmark_return": total_b,
        "active_return": bounded(active, -_LINKED_OUT, _LINKED_OUT, "active return"),
    }


def _bhb(inputs: BhbInputs) -> BhbOutputs:
    return BhbOutputs(**_attribute(inputs, fachler=False))


def _brinson_fachler(inputs: BrinsonFachlerInputs) -> BrinsonFachlerOutputs:
    return BrinsonFachlerOutputs(**_attribute(inputs, fachler=True))


# --- the model ---------------------------------------------------------------

_BHB = Reference(
    key="bhb1986",
    citation=(
        "Brinson, G. P., Hood, L. R. and Beebower, G. L. (1986). Determinants of "
        "portfolio performance. Financial Analysts Journal, 42(4), 39-44."
    ),
    doi="10.2469/faj.v42.n4.39",
    locator="Tables 1-3, the quadrant framework and its decomposition",
)
_FACHLER = Reference(
    key="fachler1985",
    citation=(
        "Brinson, G. P. and Fachler, N. (1985). Measuring non-US equity "
        "portfolio performance. The Journal of Portfolio Management, 11(3), "
        "73-76."
    ),
    doi="10.3905/jpm.1985.409005",
    locator="The allocation effect relative to the total benchmark return",
)
_CARINO = Reference(
    key="carino1999",
    citation=(
        "Carino, D. R. (1999). Combining attribution effects over time. The "
        "Journal of Performance Measurement, 3(4), 5-14. The journal is not "
        "online; the method is set out in Bacon (2008), ch. 8, Multi-period "
        "Attribution, the DOI given."
    ),
    doi="10.1002/9781119206309.ch8",
    locator="Bacon (2008) pp. 191-193, the logarithmic coefficients k_t and k",
)
_BACON = Reference(
    key="bacon2008",
    citation=(
        "Bacon, C. R. (2008). Practical Portfolio Performance Measurement and "
        "Attribution, 2nd ed. Wiley."
    ),
    doi="10.1002/9781119206309.ch5",
    isbn="9780470059289",
    locator="Chapter 5, pp. 117-134: Brinson-Hood-Beebower and Brinson-Fachler",
)

_TWO_SECTORS: Final = {
    "portfolio_weights": [[0.7, 0.3], [0.6, 0.4]],
    "benchmark_weights": [[0.6, 0.4], [0.6, 0.4]],
    "portfolio_returns": [[0.05, 0.02], [-0.01, 0.03]],
    "benchmark_returns": [[0.04, 0.025], [-0.02, 0.02]],
}


@model(
    id="performance.brinson_attribution",
    version=1,
    title="Brinson attribution",
    summary=(
        "Brinson-Hood-Beebower and Brinson-Fachler allocation, selection and "
        "interaction effects, single-period and linked over periods with "
        "Carino's method."
    ),
    formula=(
        (
            r"A^{BHB}_i = (w^p_i - w^b_i) r^b_i, \quad A^{BF}_i = (w^p_i - w^b_i)"
            r"(r^b_i - B)"
        ),
        r"S_i = w^b_i (r^p_i - r^b_i), \quad I_i = (w^p_i - w^b_i)(r^p_i - r^b_i)",
        (
            r"k_t = \frac{\ln(1 + R_t) - \ln(1 + B_t)}{R_t - B_t}, \quad "
            r"E^{linked} = \sum_t \frac{k_t}{k} E_t"
        ),
    ),
    assumptions=(
        (
            "Each period's sector weights are long only, in [0, 1], and sum to "
            "one within 1e-6; they are rescaled to sum to exactly one."
        ),
        (
            "Sector returns are buy-and-hold within the period. A sector the "
            "portfolio does not hold still needs a return: give the benchmark's, "
            "and its selection and interaction effects are zero."
        ),
        (
            "The linked effects sum to the difference of the compound returns, "
            "not to the compound (geometric) excess (1 + R) / (1 + B) - 1."
        ),
    ),
    limitations=(
        (
            "Linking more than one period raises DomainError when a period's "
            "portfolio or benchmark return is -100%, or when a compound return "
            "or linked effect passes 1e7."
        ),
        (
            "Interaction is reported apart, not folded into selection; currency, "
            "fixed-income and other multi-factor attributions are out of scope."
        ),
    ),
    references=(_BHB, _FACHLER, _CARINO, _BACON),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=("attribution", "brinson", "allocation", "selection", "carino"),
    invariants=(
        Invariant(
            id="effects_sum_to_active_return",
            statement=(
                "In each period, allocation, selection and interaction sum to "
                "the portfolio return less the benchmark return."
            ),
        ),
        Invariant(
            id="linked_effects_sum_to_geometric_active_return",
            statement=(
                "The linked effects sum to the compound portfolio return less the "
                "compound benchmark return."
            ),
        ),
        Invariant(
            id="zero_effects_for_identical_portfolios",
            statement=(
                "A portfolio with the benchmark's weights and returns has every "
                "effect zero."
            ),
        ),
    ),
    examples=(
        Example(
            name="two_sectors_two_periods_bhb",
            inputs={"calculation": "bhb", **_TWO_SECTORS},
        ),
        Example(
            name="two_sectors_two_periods_brinson_fachler",
            inputs={"calculation": "brinson_fachler", **_TWO_SECTORS},
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def brinson_attribution(inputs: BrinsonAttributionInputs) -> BrinsonAttributionOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], BrinsonAttributionOutputs]]
] = {
    BhbInputs: _bhb,
    BrinsonFachlerInputs: _brinson_fachler,
}
