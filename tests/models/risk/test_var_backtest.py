# tests/models/risk/test_var_backtest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``risk.var_backtest``: invariants, both series forms, and SciPy oracles.

The oracles recompute each likelihood ratio from SciPy's binomial and Bernoulli
log-probabilities and ``scipy.special.xlogy``, the p-values from
``scipy.stats.chi2``, and the traffic-light boundaries from
``scipy.stats.binom``; SciPy is imported at the top, so a missing one fails.
"""

from __future__ import annotations

import itertools
import math
from typing import Any

import numpy as np
import pytest
import scipy.special
import scipy.stats
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import InputError, run_model
from pyeconomics.models.risk import var_backtest

CONFIDENCE = st.floats(0.5, 0.9999)
HITS = st.lists(st.booleans(), min_size=2, max_size=300)
ZONES = {"green": 0, "yellow": 1, "red": 2}


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(var_backtest, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


@pytest.mark.invariant("risk.var_backtest", "likelihood_ratios_nonnegative")
@given(hits=HITS, confidence=CONFIDENCE)
def test_every_likelihood_ratio_is_nonnegative(
    hits: list[bool], confidence: float
) -> None:
    kupiec = run(calculation="kupiec", exceptions=hits, confidence=confidence)
    markov = run(calculation="christoffersen", exceptions=hits, confidence=confidence)
    assert kupiec.likelihood_ratio >= 0
    assert markov.lr_unconditional >= 0
    assert markov.lr_independence >= 0
    assert markov.lr_conditional_coverage >= 0


@pytest.mark.invariant("risk.var_backtest", "conditional_coverage_is_sum_of_parts")
@given(hits=HITS, confidence=CONFIDENCE)
def test_conditional_coverage_is_the_sum_of_its_parts(
    hits: list[bool], confidence: float
) -> None:
    out = run(calculation="christoffersen", exceptions=hits, confidence=confidence)
    assert math.isclose(
        out.lr_conditional_coverage,
        out.lr_unconditional + out.lr_independence,
        rel_tol=1e-9,
        abs_tol=1e-9,
    )


@pytest.mark.invariant("risk.var_backtest", "traffic_light_monotone_in_exceptions")
@given(
    size=st.integers(1, 600),
    first=st.integers(0, 600),
    second=st.integers(0, 600),
    confidence=st.sampled_from([0.95, 0.975, 0.99, 0.999]),
)
def test_more_exceptions_never_improve_the_zone(
    size: int, first: int, second: int, confidence: float
) -> None:
    fewer, more = sorted((min(first, size), min(second, size)))

    def light(count: int) -> Any:  # noqa: ANN401
        return run(
            calculation="basel_traffic_light",
            exceptions=[True] * count + [False] * (size - count),
            confidence=confidence,
        )

    low, high = light(fewer), light(more)
    assert ZONES[high.zone] >= ZONES[low.zone]
    if low.plus_factor is not None and high.plus_factor is not None:
        assert high.plus_factor >= low.plus_factor


@pytest.mark.oracle("risk.var_backtest")
@given(hits=HITS, confidence=CONFIDENCE)
def test_kupiec_matches_scipy_binomial_likelihoods(
    hits: list[bool], confidence: float
) -> None:
    out = run(calculation="kupiec", exceptions=hits, confidence=confidence)
    n, x = len(hits), sum(hits)
    p = 1 - confidence
    ratio = 2 * (
        scipy.stats.binom.logpmf(x, n, x / n) - scipy.stats.binom.logpmf(x, n, p)
    )
    assert math.isclose(out.likelihood_ratio, ratio, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(
        out.p_value, scipy.stats.chi2.sf(ratio, 1), rel_tol=1e-7, abs_tol=1e-12
    )
    critical = scipy.stats.chi2.ppf(0.95, 1)
    assert math.isclose(out.critical_value, critical, rel_tol=1e-12)


@pytest.mark.oracle("risk.var_backtest")
@given(hits=HITS, confidence=CONFIDENCE)
def test_christoffersen_matches_xlogy_likelihoods(
    hits: list[bool], confidence: float
) -> None:
    out = run(calculation="christoffersen", exceptions=hits, confidence=confidence)
    pairs = list(itertools.pairwise(hits))
    n = {(a, b): pairs.count((a, b)) for a in (False, True) for b in (False, True)}
    n00, n01 = n[False, False], n[False, True]
    n10, n11 = n[True, False], n[True, True]

    def xlogy(count: float, probability: float) -> float:
        counts = np.array([count], dtype=np.float64)
        probabilities = np.array([probability], dtype=np.float64)
        return float(scipy.special.xlogy(counts, probabilities)[0])

    p, later, total = 1 - confidence, n01 + n11, len(pairs)
    pi = later / total
    pi01 = n01 / (n00 + n01) if n00 + n01 else 0.0
    pi11 = n11 / (n10 + n11) if n10 + n11 else 0.0
    null = xlogy(total - later, 1 - p) + xlogy(later, p)
    rate = xlogy(total - later, 1 - pi) + xlogy(later, pi)
    markov = (
        xlogy(n00, 1 - pi01)
        + xlogy(n01, pi01)
        + xlogy(n10, 1 - pi11)
        + xlogy(n11, pi11)
    )
    assert (out.n00, out.n01, out.n10, out.n11) == (n00, n01, n10, n11)
    for name, value in (
        ("lr_unconditional", -2 * (null - rate)),
        ("lr_independence", -2 * (rate - markov)),
        ("lr_conditional_coverage", -2 * (null - markov)),
    ):
        assert math.isclose(getattr(out, name), value, rel_tol=1e-9, abs_tol=1e-9)
    assert math.isclose(
        out.p_value_conditional_coverage,
        scipy.stats.chi2.sf(out.lr_conditional_coverage, 2),
        rel_tol=1e-9,
        abs_tol=1e-12,
    )


@pytest.mark.oracle("risk.var_backtest")
@given(size=st.integers(1, 2000), confidence=st.sampled_from([0.95, 0.99, 0.999]))
def test_zone_boundaries_match_scipy_binomial(size: int, confidence: float) -> None:
    out = run(
        calculation="basel_traffic_light",
        exceptions=[False] * size,
        confidence=confidence,
    )
    law = scipy.stats.binom(size, 1 - confidence)
    yellow = max(1, next(k for k in range(size + 1) if law.cdf(k) >= 0.95))
    red = max(yellow, next(k for k in range(size + 1) if law.cdf(k) >= 0.9999))
    assert (out.yellow_from, out.red_from) == (yellow, red)
    assert out.zone == "green"  # no exception is never evidence against a VaR


def test_pnl_and_var_count_losses_beyond_the_var() -> None:
    pnl = [1.0, -3.0, -3.5, 0.0, -10.0]
    var = [3.0, 3.0, 3.0, 3.0, 9.0]
    from_pnl = run(
        calculation="kupiec", profit_and_loss=pnl, value_at_risk=var, confidence=0.9
    )
    from_hits = run(
        calculation="kupiec",
        exceptions=[False, False, True, False, True],
        confidence=0.9,
    )
    assert from_pnl == from_hits
    assert from_pnl.exceptions == 2  # a loss equal to the VaR is no exception


def test_table_2_holds_for_250_observations_at_99() -> None:
    for count, plus in ((4, 0.0), (5, 0.4), (6, 0.5), (7, 0.65), (8, 0.75), (9, 0.85)):
        out = run(
            calculation="basel_traffic_light",
            exceptions=[True] * count + [False] * (250 - count),
        )
        assert out.plus_factor == plus
    red = run(calculation="basel_traffic_light", exceptions=[True] * 30 + [False] * 220)
    assert (red.zone, red.plus_factor) == ("red", 1.0)


def test_a_yellow_zone_outside_table_2_has_no_plus_factor() -> None:
    found = result(
        calculation="basel_traffic_light",
        exceptions=[True] * 4 + [False] * 96,
    )
    assert found.outputs.zone == "yellow"
    assert found.outputs.plus_factor is None
    assert [w.code for w in found.warnings] == ["plus_factor_undefined"]


def test_no_exceptions_and_only_exceptions() -> None:
    none = run(calculation="christoffersen", exceptions=[False] * 50)
    assert (none.n00, none.lr_independence) == (49, 0.0)
    every = run(calculation="christoffersen", exceptions=[True] * 50)
    assert (every.n11, every.lr_independence) == (49, 0.0)
    assert every.reject_conditional_coverage


@pytest.mark.parametrize(
    "inputs",
    [
        {"calculation": "kupiec"},
        {"calculation": "kupiec", "exceptions": []},
        {"calculation": "kupiec", "profit_and_loss": [1.0]},
        {
            "calculation": "kupiec",
            "exceptions": [True],
            "profit_and_loss": [1.0],
            "value_at_risk": [1.0],
        },
        {
            "calculation": "kupiec",
            "profit_and_loss": [1.0, 2.0],
            "value_at_risk": [1.0],
        },
        {"calculation": "christoffersen", "exceptions": [True]},
    ],
)
def test_a_series_must_be_given_once_and_whole(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        run(**inputs)


@pytest.mark.parametrize(
    ("size", "confidence"), [(5, 0.99), (250, 0.9999), (500, 0.9999)]
)
def test_no_exception_is_green_even_in_a_short_sample(
    size: int, confidence: float
) -> None:
    found = result(
        calculation="basel_traffic_light",
        exceptions=[False] * size,
        confidence=confidence,
    )
    assert found.outputs.zone == "green"
    assert found.outputs.plus_factor == 0.0
    assert found.outputs.yellow_from >= 1
    assert found.warnings == ()
