# tests/models/portfolio/test_utility.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``portfolio.utility``: its invariants, its edge cases, and SciPy as an oracle.

The oracle is ``scipy.optimize.minimize_scalar``, which finds the fraction
maximizing the expected log growth numerically; the Kelly closed form must
agree. SciPy is imported at the top, so a missing library fails the suite.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import scipy.optimize
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import InputError, run_model
from pyeconomics.models.portfolio import utility


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(utility, inputs).outputs


AVERSION = st.floats(0.0, 100.0)


@st.composite
def gambles(draw: st.DrawFn) -> dict[str, Any]:
    size = draw(st.integers(1, 6))
    outcomes = draw(st.lists(st.floats(-0.9, 2.0), min_size=size, max_size=size))
    raw = draw(st.lists(st.floats(0.01, 1.0), min_size=size, max_size=size))
    total = sum(raw)
    return {"outcomes": outcomes, "probabilities": [p / total for p in raw]}


@pytest.mark.invariant("portfolio.utility", "utility_falls_as_aversion_rises")
@given(
    mean=st.floats(-1.0, 10.0),
    vol=st.floats(0.0, 10.0),
    low=AVERSION,
    high=AVERSION,
    gamble=gambles(),
)
def test_utility_never_rises_with_aversion(
    mean: float, vol: float, low: float, high: float, gamble: dict[str, Any]
) -> None:
    low, high = min(low, high), max(low, high)
    common = {"calculation": "mean_variance_utility", "expected_return": mean}
    assert (
        run(**common, volatility=vol, risk_aversion=high).utility
        <= run(**common, volatility=vol, risk_aversion=low).utility
    )
    ce = {"calculation": "certainty_equivalent", **gamble}
    lower = run(**ce, relative_risk_aversion=high).certainty_equivalent
    upper = run(**ce, relative_risk_aversion=low).certainty_equivalent
    assert lower <= upper + 1e-12 * (1 + abs(upper))


@pytest.mark.invariant("portfolio.utility", "optimal_share_inverse_in_aversion")
@given(
    mean=st.floats(-1.0, 1.0),
    rate=st.floats(-0.99, 1.0),
    vol=st.floats(0.01, 10.0),
    aversion=st.floats(0.1, 50.0),
)
def test_doubling_aversion_halves_the_share(
    mean: float, rate: float, vol: float, aversion: float
) -> None:
    common = {
        "calculation": "optimal_risky_share",
        "expected_return": mean,
        "risk_free_rate": rate,
        "volatility": vol,
    }
    once = run(**common, risk_aversion=aversion).optimal_share
    twice = run(**common, risk_aversion=2 * aversion).optimal_share
    assert math.isclose(once, 2 * twice, rel_tol=1e-12, abs_tol=1e-300)


@pytest.mark.invariant("portfolio.utility", "kelly_zero_without_edge")
@given(
    odds=st.floats(0.001, 1000.0),
    drift=st.floats(-0.99, 1.0),
    vol=st.floats(0.01, 10.0),
)
def test_no_edge_means_no_bet(odds: float, drift: float, vol: float) -> None:
    bet = run(calculation="kelly", win_probability=1 / (1 + odds), odds=odds)
    assert math.isclose(bet.full_kelly, 0.0, abs_tol=1e-12)
    assert bet.fraction <= 1e-12
    asset = run(calculation="kelly", drift=drift, risk_free_rate=drift, volatility=vol)
    assert asset.full_kelly == 0.0
    assert asset.fraction == 0.0
    assert asset.growth_rate == drift


@pytest.mark.invariant("portfolio.utility", "certainty_equivalent_below_mean")
@given(gamble=gambles(), gamma=AVERSION)
def test_the_certainty_equivalent_is_below_the_mean(
    gamble: dict[str, Any], gamma: float
) -> None:
    found = run(
        calculation="certainty_equivalent", relative_risk_aversion=gamma, **gamble
    )
    assert (
        min(gamble["outcomes"]) <= found.certainty_equivalent <= found.expected_return
    )
    assert found.risk_premium >= 0


@pytest.mark.oracle("portfolio.utility")
@given(
    p=st.floats(0.05, 0.95),
    odds=st.floats(0.2, 20.0),
    drift=st.floats(-0.5, 0.5),
    rate=st.floats(-0.1, 0.1),
    vol=st.floats(0.05, 1.0),
)
def test_kelly_maximizes_growth_as_scipy_finds(
    p: float, odds: float, drift: float, rate: float, vol: float
) -> None:
    q = 1 - p
    bet = run(calculation="kelly", win_probability=p, odds=odds)
    if bet.full_kelly > 1e-3:
        found = scipy.optimize.minimize_scalar(
            lambda f: -(p * math.log1p(f * odds) + q * math.log1p(-f)),
            bounds=(0.0, 0.999999),
            method="bounded",
            options={"xatol": 1e-12},
        )
        assert math.isclose(bet.full_kelly, found.x, abs_tol=1e-6)
    asset = run(calculation="kelly", drift=drift, risk_free_rate=rate, volatility=vol)
    found = scipy.optimize.minimize_scalar(
        lambda f: -(rate + f * (drift - rate) - 0.5 * f * f * vol * vol)
    )
    assert math.isclose(asset.full_kelly, found.x, rel_tol=1e-6, abs_tol=1e-6)


# --- edges and errors ------------------------------------------------------------


def test_a_certain_win_stakes_everything_the_multiplier_allows() -> None:
    found = run(calculation="kelly", win_probability=1.0, odds=2.0, multiplier=0.5)
    assert found.full_kelly == 1.0
    assert found.fraction == 0.5
    assert math.isclose(found.growth_rate, math.log(2.0), rel_tol=1e-15)


def test_a_bet_against_the_edge_stakes_nothing() -> None:
    found = run(calculation="kelly", win_probability=0.3, odds=1.0)
    assert found.full_kelly < 0
    assert found.fraction == 0.0
    assert found.growth_rate == 0.0


def test_a_continuous_asset_without_a_rate_uses_zero() -> None:
    found = run(calculation="kelly", drift=0.05, volatility=0.2)
    assert math.isclose(found.full_kelly, 1.25, rel_tol=1e-12)


@pytest.mark.parametrize(
    "inputs",
    [
        {"win_probability": 0.5},
        {"win_probability": 0.5, "odds": 1.0, "drift": 0.1},
        {"drift": 0.1},
        {"drift": 0.1, "volatility": 0.2, "odds": 1.0},
        {"win_probability": 0.5, "odds": 1.0, "risk_free_rate": 0.01},
        {},
    ],
)
def test_kelly_takes_exactly_one_form(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError, match="discrete bet"):
        run(calculation="kelly", **inputs)


@pytest.mark.parametrize(
    ("probabilities", "match"),
    [([0.5], "one probability per outcome"), ([0.5, 0.4], "sum to one")],
)
def test_a_gamble_needs_a_distribution(probabilities: list[float], match: str) -> None:
    with pytest.raises(InputError, match=match):
        run(
            calculation="certainty_equivalent",
            outcomes=[0.1, -0.1],
            probabilities=probabilities,
            relative_risk_aversion=2,
        )


@pytest.mark.parametrize("gamma", [1.0, 3.0])
def test_a_possible_total_loss_is_worth_a_total_loss_to_a_log_investor_or_worse(
    gamma: float,
) -> None:
    found = run(
        calculation="certainty_equivalent",
        outcomes=[-1.0, 0.5],
        probabilities=[0.1, 0.9],
        relative_risk_aversion=gamma,
    )
    assert found.certainty_equivalent == -1.0


def test_a_sure_total_loss_below_log_utility() -> None:
    found = run(
        calculation="certainty_equivalent",
        outcomes=[-1.0],
        probabilities=[1.0],
        relative_risk_aversion=0.5,
    )
    assert found.certainty_equivalent == -1.0


def test_a_possible_total_loss_counts_for_little_below_log_utility() -> None:
    found = run(
        calculation="certainty_equivalent",
        outcomes=[-1.0, 0.44],
        probabilities=[0.5, 0.5],
        relative_risk_aversion=0.5,
    )
    # (0.5 * 0 + 0.5 * 1.2)^2 - 1 = -0.64
    assert math.isclose(found.certainty_equivalent, -0.64, rel_tol=1e-12)


def test_outcomes_with_no_probability_are_ignored() -> None:
    found = run(
        calculation="certainty_equivalent",
        outcomes=[-1.0, 0.2],
        probabilities=[0.0, 1.0],
        relative_risk_aversion=5,
    )
    assert math.isclose(found.certainty_equivalent, 0.2, rel_tol=1e-12)


@pytest.mark.parametrize("gamma", [1 - 1e-15, 1 + 1e-15, 1 - 1e-12, 1 + 1e-9])
def test_the_certainty_equivalent_is_continuous_at_log_utility(gamma: float) -> None:
    # Review regression: ln(sum) / (1 - gamma) cancelled near gamma = 1 and
    # returned values 22% off log utility's.
    gamble = {"outcomes": [0.5, -0.2], "probabilities": [0.5, 0.5]}
    at_one = run(calculation="certainty_equivalent", relative_risk_aversion=1, **gamble)
    near = run(
        calculation="certainty_equivalent", relative_risk_aversion=gamma, **gamble
    )
    assert math.isclose(
        near.certainty_equivalent, at_one.certainty_equivalent, rel_tol=1e-7
    )
