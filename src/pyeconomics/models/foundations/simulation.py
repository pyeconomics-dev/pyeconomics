# src/pyeconomics/models/foundations/simulation.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Seeded Monte Carlo: ``foundations.simulation``.

Two calculations, discriminated on ``calculation``, each drawing only from
``pyeconomics.core.generator(seed)`` (ADR-0008 decision 7):

- ``gbm``: paths of geometric Brownian motion, stepped exactly in log space,
  with optional antithetic variates; it reports the terminal distribution;
- ``bootstrap``: resamples of a sample with replacement, for the standard error
  and percentile interval of its mean, median or standard deviation.

Both are cost class HEAVY: every size is bounded so that the largest valid input
finishes in a few seconds (the worst case is measured in the step's pull
request), and the work is done in chunks of at most a few million draws so that
memory stays bounded too.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

import numpy as np
from pydantic import Field

from pyeconomics.core import (
    SEED_MAX,
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Probability,
    ProbabilityArray,
    Rate,
    Ratio,
    RatioArray,
    Reference,
    Symbol,
    Volatility,
    Years,
    generator,
    model,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.foundations._common import bounded

if TYPE_CHECKING:
    from collections.abc import Callable

    from numpy.typing import NDArray

__all__ = ["simulation"]

#: The bounds of a GBM run. Steps times paths is at most 1e8 normal draws.
_PATHS_MAX: Final = 100_000
_STEPS_MAX: Final = 1_000
#: Terminal values from inputs at their bounds reach about 1e27 (a drift of 1
#: over 30 years, six standard deviations up), so the terminal outputs widen an
#: index level's upper bound from 1e9 to 1e30.
_TERMINAL_MAX: Final = 1e30
#: The bounds of a bootstrap. Resamples times sample size is at most 1e7 draws.
_SAMPLE_MAX: Final = 1_000
_RESAMPLES_MAX: Final = 10_000
#: Statistics of a sample in [-1e6, 1e6]: a standard deviation of two values
#: at the extremes is 2e6 / sqrt(2).
_STATISTIC_MAX: Final = 1e7
#: How many draws one chunk holds.
_CHUNK: Final = 2_000_000

_Levels = Annotated[
    tuple[Annotated[IndexLevel, Field(ge=0, le=_TERMINAL_MAX)], ...], ARRAY_INPUT
]


def _seed() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        default=0,
        ge=0,
        le=SEED_MAX,
        description="Random seed (ADR-0008 decision 7): the same seed, the same draws",
    )


def _terminal(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=0, le=_TERMINAL_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class GbmInputs(ModelInputs):
    """Geometric Brownian motion and the size of the simulation."""

    calculation: Literal["gbm"] = Field(
        "gbm", description="Monte Carlo of geometric Brownian motion"
    )
    initial_value: IndexLevel = Field(ge=0.01, le=1e6, description="Value at time 0")
    drift: Rate = Field(
        ge=-1.0, le=1.0, description="Expected growth rate mu, continuous, per year"
    )
    volatility: Volatility = Field(gt=0, le=3.0, description="Volatility per year")
    horizon: Years = Field(gt=0, le=30, description="Time to the horizon, in years")
    steps: Count = Field(252, ge=1, le=_STEPS_MAX, description="Time steps per path")
    paths: Count = Field(
        10_000, ge=4, le=_PATHS_MAX, description="Number of simulated paths"
    )
    antithetic: bool = Field(
        default=False,
        description="Pair each path with its mirror image (rounds paths up to even)",
    )
    percentiles: ProbabilityArray = Field(
        (0.05, 0.5, 0.95),
        min_length=1,
        max_length=99,
        description="Probabilities at which to report terminal quantiles",
    )
    level: IndexLevel | None = Field(
        None,
        ge=0.01,
        le=1e9,
        description="Level for the probability of ending below; null for the start",
    )
    seed: Count = _seed()


class BootstrapInputs(ModelInputs):
    """A sample, the statistic to bootstrap, and the size of the resampling."""

    calculation: Literal["bootstrap"] = Field(
        "bootstrap", description="Nonparametric bootstrap of a statistic"
    )
    sample: RatioArray = Field(
        min_length=2, max_length=_SAMPLE_MAX, description="The observed sample"
    )
    statistic: Literal["mean", "median", "standard_deviation"] = Field(
        "mean", description="The statistic to bootstrap (standard deviation: n - 1)"
    )
    resamples: Count = Field(
        1_000, ge=2, le=_RESAMPLES_MAX, description="Number of bootstrap resamples"
    )
    confidence: Probability = Field(
        0.95, ge=0.5, le=0.999, description="Coverage of the percentile interval"
    )
    seed: Count = _seed()


SimulationInputs = Annotated[
    GbmInputs | BootstrapInputs, Field(discriminator="calculation")
]


# --- outputs -----------------------------------------------------------------


class GbmOutputs(ModelOutputs):
    calculation: Literal["gbm"] = Field(
        "gbm", description="Monte Carlo of geometric Brownian motion"
    )
    terminal_mean: IndexLevel = _terminal("Mean terminal value")
    terminal_std: IndexLevel = _terminal("Standard deviation of terminal values")
    standard_error: IndexLevel = _terminal(
        "Standard error of the mean (from pair averages with antithetic variates)"
    )
    terminal_min: IndexLevel = _terminal("Smallest terminal value")
    terminal_max: IndexLevel = _terminal("Largest terminal value")
    percentile_values: _Levels = Field(
        max_length=99, description="Terminal quantiles at the requested probabilities"
    )
    probability_below: Probability = Field(
        ge=0, le=1, description="Share of paths ending below the level"
    )
    paths_simulated: Count = Field(ge=4, le=_PATHS_MAX, description="Paths simulated")


class BootstrapOutputs(ModelOutputs):
    calculation: Literal["bootstrap"] = Field(
        "bootstrap", description="Nonparametric bootstrap of a statistic"
    )
    estimate: Ratio = Field(
        ge=-_STATISTIC_MAX, le=_STATISTIC_MAX, description="Statistic of the sample"
    )
    standard_error: Ratio = Field(
        ge=0,
        le=_STATISTIC_MAX,
        description="Standard deviation of the bootstrap replicates (B - 1)",
    )
    interval_lower: Ratio = Field(
        ge=-_STATISTIC_MAX, le=_STATISTIC_MAX, description="Percentile interval, lower"
    )
    interval_upper: Ratio = Field(
        ge=-_STATISTIC_MAX, le=_STATISTIC_MAX, description="Percentile interval, upper"
    )


SimulationOutputs = Annotated[
    GbmOutputs | BootstrapOutputs, Field(discriminator="calculation")
]


# --- calculations ------------------------------------------------------------


def _log_drift(inputs: GbmInputs) -> float:
    """Return the mean of the terminal log-growth, (mu - sigma^2 / 2) T."""
    return (inputs.drift - 0.5 * inputs.volatility**2) * inputs.horizon


def _log_growth(inputs: GbmInputs, paths: int) -> NDArray[np.float64]:
    """Simulate the terminal log-growth of ``paths`` paths, step by step."""
    draws = generator(inputs.seed)
    steps = inputs.steps
    rows = max(1, _CHUNK // steps)
    shocks = np.empty(paths, dtype=np.float64)
    for start in range(0, paths, rows):
        count = min(rows, paths - start)
        shocks[start : start + count] = draws.standard_normal((count, steps)).sum(
            axis=1
        )
    step_scale = inputs.volatility * math.sqrt(inputs.horizon / steps)
    return _log_drift(inputs) + step_scale * shocks


def _gbm(inputs: GbmInputs) -> GbmOutputs:
    start = inputs.initial_value
    if inputs.antithetic:
        pairs = -(-inputs.paths // 2)
        growth = _log_growth(inputs, pairs)
        # The mirror path negates every shock: its log-growth is reflected
        # about the mean log-growth.
        mirrored = 2 * _log_drift(inputs) - growth
        values = start * np.exp(np.concatenate([growth, mirrored]))
        averages = 0.5 * (values[:pairs] + values[pairs:])
        standard_error = float(np.std(averages, ddof=1)) / math.sqrt(pairs)
    else:
        values = start * np.exp(_log_growth(inputs, inputs.paths))
        standard_error = float(np.std(values, ddof=1)) / math.sqrt(values.size)
    level = start if inputs.level is None else inputs.level
    quantiles = np.quantile(values, np.asarray(inputs.percentiles))

    def terminal(value: float, what: str) -> float:
        return bounded(value, 0.0, _TERMINAL_MAX, what)

    return GbmOutputs(
        terminal_mean=terminal(float(np.mean(values)), "terminal mean"),
        terminal_std=terminal(float(np.std(values, ddof=1)), "terminal deviation"),
        standard_error=terminal(standard_error, "standard error"),
        terminal_min=terminal(float(values.min()), "smallest terminal value"),
        terminal_max=terminal(float(values.max()), "largest terminal value"),
        percentile_values=tuple(
            terminal(float(q), "terminal quantile") for q in quantiles
        ),
        probability_below=float(np.mean(values < level)),
        paths_simulated=values.size,
    )


_STATISTICS: Final[dict[str, Callable[[NDArray[np.float64]], NDArray[np.float64]]]] = {
    "mean": lambda rows: np.mean(rows, axis=-1),
    "median": lambda rows: np.median(rows, axis=-1),
    "standard_deviation": lambda rows: np.std(rows, axis=-1, ddof=1),
}


def _bootstrap(inputs: BootstrapInputs) -> BootstrapOutputs:
    sample = np.asarray(inputs.sample, dtype=np.float64)
    statistic = _STATISTICS[inputs.statistic]
    draws = generator(inputs.seed)
    n, resamples = sample.size, inputs.resamples
    rows = max(1, _CHUNK // n)
    replicates = np.empty(resamples, dtype=np.float64)
    for start in range(0, resamples, rows):
        count = min(rows, resamples - start)
        picks = draws.integers(0, n, size=(count, n))
        replicates[start : start + count] = statistic(sample[picks])
    tail = (1 - inputs.confidence) / 2
    lower, upper = np.quantile(replicates, [tail, 1 - tail])
    return BootstrapOutputs(
        estimate=float(statistic(sample)),
        standard_error=float(np.std(replicates, ddof=1)),
        interval_lower=float(lower),
        interval_upper=float(upper),
    )


# --- the model ---------------------------------------------------------------

_GLASSERMAN = Reference(
    key="glasserman2003",
    citation=(
        "Glasserman, P. (2003). Monte Carlo Methods in Financial Engineering. Springer."
    ),
    url="https://openlibrary.org/isbn/9780387004518",
    isbn="9780387004518",
    locator=(
        "Section 3.2 (geometric Brownian motion) and Section 4.2 (antithetic variates)"
    ),
)
_EFRON = Reference(
    key="efron1993",
    citation=(
        "Efron, B. and Tibshirani, R. J. (1993). An Introduction to the "
        "Bootstrap. Chapman & Hall."
    ),
    url="https://openlibrary.org/isbn/9780412042317",
    isbn="9780412042317",
    locator=(
        "Chapter 6 (the bootstrap estimate of standard error) and Chapter 13 "
        "(percentile intervals)"
    ),
)


@model(
    id="foundations.simulation",
    version=1,
    title="Monte Carlo simulation",
    summary=(
        "Seeded Monte Carlo of geometric Brownian motion, with antithetic "
        "variates, and the nonparametric bootstrap of a mean, median or "
        "standard deviation."
    ),
    formula=(
        (
            r"S_{t + \Delta t} = S_t \exp\left((\mu - \tfrac{1}{2}\sigma^2)\Delta t"
            r" + \sigma \sqrt{\Delta t}\, Z\right)"
        ),
        r"E[S_T] = S_0 e^{\mu T}, \quad \mathrm{SE} = s / \sqrt{N}",
        (
            r"\widehat{se}_B = \sqrt{\frac{1}{B - 1}\sum_b (\hat\theta^*_b - "
            r"\bar\theta^*)^2}, \quad [\hat\theta^*_{(\alpha/2)}, "
            r"\hat\theta^*_{(1-\alpha/2)}]"
        ),
    ),
    symbols=(
        Symbol("S_t", "The value at time t"),
        Symbol("S_0", "The value now", "initial_value"),
        Symbol(r"\mu", "Drift per year", "drift"),
        Symbol(r"\sigma", "Volatility per year", "volatility"),
        Symbol(r"\Delta t", "The length of one step, in years"),
        Symbol("Z", "A standard normal draw"),
        Symbol(
            "E[S_T]",
            "The expected value at the horizon, which the simulated mean estimates",
            "terminal_mean",
        ),
        Symbol("T", "Horizon, in years", "horizon"),
        Symbol(
            r"\mathrm{SE}",
            "Standard error of the simulated mean",
            "standard_error",
        ),
        Symbol(
            "s",
            "Standard deviation of the simulated values at the horizon",
            "terminal_std",
        ),
        Symbol("N", "Number of simulated paths", "paths_simulated"),
        Symbol(
            r"\widehat{se}_B",
            "Bootstrap standard error of the statistic",
            "standard_error",
        ),
        Symbol("B", "Number of resamples", "resamples"),
        Symbol(r"\hat\theta^*_b", "The statistic computed on resample b"),
        Symbol(r"\alpha", "One less the confidence level"),
    ),
    assumptions=(
        (
            "GBM steps are exact in log space, so the terminal distribution is "
            "lognormal for any number of steps; steps change the draws only."
        ),
        (
            "With antithetic variates each path is paired with its mirror "
            "image, and the standard error comes from the pair averages."
        ),
        (
            "The bootstrap resamples the sample with replacement; quantiles "
            "interpolate linearly between order statistics."
        ),
        "The same seed gives the same result under one NumPy feature release.",
    ),
    limitations=(
        (
            "Results are estimates with Monte Carlo error, which the standard "
            "error measures; a different seed gives a different estimate."
        ),
        (
            "Sizes are capped (100,000 paths of 1,000 steps; 10,000 resamples "
            "of 1,000 observations); a terminal statistic above 1e30 raises "
            "DomainError."
        ),
        (
            "A percentile interval from a small sample can under-cover; the "
            "bootstrap does not correct its bias."
        ),
    ),
    references=(_GLASSERMAN, _EFRON),
    evidence=Evidence.STANDARD,
    cost=CostClass.HEAVY,
    tags=("monte carlo", "gbm", "bootstrap", "simulation"),
    invariants=(
        Invariant(
            id="terminal_values_positive",
            statement="Every simulated terminal value is above zero.",
        ),
        Invariant(
            id="same_seed_same_result",
            statement="The same inputs and seed give the same outputs.",
        ),
        Invariant(
            id="antithetic_reduces_variance",
            statement=(
                "For a monotone payoff such as the terminal value, antithetic "
                "variates do not raise the standard error of the mean."
            ),
        ),
    ),
    examples=(
        Example(
            name="one_year_of_a_stock",
            inputs={
                "calculation": "gbm",
                "initial_value": 100,
                "drift": 0.05,
                "volatility": 0.2,
                "horizon": 1,
                "steps": 12,
                "paths": 2000,
                "seed": 7,
            },
        ),
        Example(
            name="mouse_survival",
            inputs={
                "calculation": "bootstrap",
                "sample": [94, 197, 16, 38, 99, 141, 23],
                "resamples": 500,
                "seed": 7,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def simulation(inputs: SimulationInputs) -> SimulationOutputs:
    """Run the simulation the inputs select."""
    if isinstance(inputs, GbmInputs):
        return _gbm(inputs)
    return _bootstrap(inputs)
