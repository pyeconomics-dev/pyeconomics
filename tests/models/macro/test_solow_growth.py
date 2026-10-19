# tests/models/macro/test_solow_growth.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.solow_growth``: the steady state's invariants and growth accounting's."""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.macro import solow_growth

#: Shares up to 0.75 keep k* = (s / (n + g + delta)) ** (1 / (1 - alpha)) within
#: its 1e15 bound for effective depreciation of at least 1%.
SHARES = st.floats(0.05, 0.75)
DEPRECIATION = st.floats(0.0, 0.2)
GROWTH = st.floats(-0.02, 0.05)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(solow_growth, inputs).outputs


def steady(**inputs: Any) -> Any:  # noqa: ANN401
    return run(calculation="steady_state", **inputs)


@st.composite
def economies(draw: st.DrawFn) -> dict[str, float]:
    """Parameters with effective depreciation comfortably above zero."""
    alpha = draw(SHARES)
    n, g = draw(GROWTH), draw(GROWTH)
    delta = draw(st.floats(max(0.0, 0.01 - n - g), 0.2))
    return {
        "capital_share": alpha,
        "population_growth": n,
        "technology_growth": g,
        "depreciation": delta,
    }


@pytest.mark.invariant("macro.solow_growth", "steady_state_capital_rises_with_saving")
@given(economy=economies(), low=st.floats(0.0, 1.0), high=st.floats(0.0, 1.0))
def test_more_saving_never_lowers_steady_state_capital(
    economy: dict[str, float], low: float, high: float
) -> None:
    low, high = sorted((low, high))
    less = steady(saving_rate=low, **economy)
    more = steady(saving_rate=high, **economy)
    assert more.capital_per_effective_worker >= less.capital_per_effective_worker
    assert more.output_per_effective_worker >= less.output_per_effective_worker


@pytest.mark.invariant(
    "macro.solow_growth", "golden_rule_maximizes_steady_state_consumption"
)
@given(economy=economies(), saving=st.floats(0.0, 1.0))
def test_no_saving_rate_beats_the_golden_rule(
    economy: dict[str, float], saving: float
) -> None:
    outputs = steady(saving_rate=saving, **economy)
    golden = steady(saving_rate=economy["capital_share"], **economy)
    assert outputs.golden_rule_saving_rate == economy["capital_share"]
    assert outputs.consumption_per_effective_worker <= (
        golden.consumption_per_effective_worker * (1 + 1e-12)
    )
    assert outputs.golden_rule_consumption == pytest.approx(
        golden.consumption_per_effective_worker, rel=1e-12
    )


@st.composite
def accounts(draw: st.DrawFn) -> dict[str, Any]:
    size = draw(st.integers(1, 60))
    # Growth of -10% to 15% a period keeps the TFP index inside (0, 1e15] over 60
    # periods, so every draw is checked.
    growth = st.lists(st.floats(-0.1, 0.15), min_size=size, max_size=size)
    inputs: dict[str, Any] = {
        "calculation": "growth_accounting",
        "output_growth": draw(growth),
        "capital_growth": draw(growth),
        "labour_growth": draw(growth),
        "method": draw(st.sampled_from(["log", "discrete"])),
    }
    if draw(st.booleans()):
        inputs["human_capital_growth"] = draw(growth)
    if draw(st.booleans()):
        inputs["labour_share"] = draw(
            st.lists(st.floats(0.0, 1.0), min_size=size, max_size=size)
        )
    else:
        inputs["capital_share"] = draw(st.floats(0.0, 1.0))
    return inputs


@pytest.mark.invariant("macro.solow_growth", "contributions_sum_to_output_growth")
@given(inputs=accounts())
def test_the_contributions_add_up_to_output_growth(inputs: dict[str, Any]) -> None:
    outputs = run(**inputs)
    parts = (
        outputs.capital_contribution
        + outputs.labour_contribution
        + outputs.human_capital_contribution
        + outputs.tfp_growth
    )
    assert parts == pytest.approx(outputs.output_growth, abs=1e-12)


def test_the_steady_state_formulas() -> None:
    outputs = steady(
        saving_rate=0.25,
        capital_share=1 / 3,
        population_growth=0.01,
        technology_growth=0.02,
        depreciation=0.05,
    )
    k = (0.25 / 0.08) ** 1.5
    assert outputs.capital_per_effective_worker == pytest.approx(k, rel=1e-14)
    assert outputs.output_per_effective_worker == pytest.approx(k ** (1 / 3), rel=1e-14)
    assert outputs.capital_output_ratio == pytest.approx(3.125, rel=1e-15)
    assert outputs.convergence_speed == pytest.approx(0.08 * 2 / 3, rel=1e-15)
    assert outputs.half_life == pytest.approx(math.log(2) / (0.08 * 2 / 3), rel=1e-14)


def test_a_golden_rule_past_its_bound_leaves_the_steady_state_standing() -> None:
    result = run_model(
        solow_growth,
        {"calculation": "steady_state", "saving_rate": 0.2, "capital_share": 0.95},
    )
    outputs = result.outputs
    assert outputs.capital_per_effective_worker == pytest.approx((0.2 / 0.08) ** 20)
    assert outputs.golden_rule_capital is None
    assert outputs.golden_rule_consumption is None
    assert [w.code for w in result.warnings] == ["golden_rule_unrepresentable"]


def test_no_saving_leaves_nothing() -> None:
    outputs = steady(saving_rate=0.0)
    assert outputs.capital_per_effective_worker == 0.0
    assert outputs.output_per_effective_worker == 0.0
    assert outputs.consumption_per_effective_worker == 0.0
    assert outputs.golden_rule_capital > 0


@pytest.mark.parametrize(
    "economy",
    [
        {"population_growth": 0.0, "technology_growth": 0.0, "depreciation": 0.0},
        {"population_growth": -0.05, "technology_growth": 0.0, "depreciation": 0.01},
        {"population_growth": 0.0, "technology_growth": 0.0, "depreciation": 1e-9},
    ],
)
def test_no_steady_state_without_effective_depreciation(
    economy: dict[str, float],
) -> None:
    with pytest.raises(DomainError):
        steady(saving_rate=0.3, **economy)


def test_capital_beyond_its_bound_is_refused() -> None:
    with pytest.raises(DomainError, match="saving rate is too large"):
        steady(
            saving_rate=1.0,
            capital_share=0.95,
            population_growth=0.0,
            technology_growth=0.0,
            depreciation=1e-3,
        )


def test_the_two_methods_differ_by_their_arithmetic() -> None:
    inputs = {
        "calculation": "growth_accounting",
        "output_growth": [0.03, 0.02],
        "capital_growth": [0.04, 0.01],
        "labour_growth": [0.01, 0.0],
        "capital_share": 0.3,
    }
    logs = run(**inputs)
    discrete = run(**inputs, method="discrete")
    assert logs.output_growth == pytest.approx(
        (math.log1p(0.03) + math.log1p(0.02)) / 2
    )
    assert discrete.output_growth == pytest.approx(0.025)
    tfp = [0.03 - 0.3 * 0.04 - 0.7 * 0.01, 0.02 - 0.3 * 0.01]
    assert discrete.tfp_index == pytest.approx(
        (1 + tfp[0], (1 + tfp[0]) * (1 + tfp[1]))
    )
    assert logs.tfp_index[-1] == pytest.approx(math.exp(2 * logs.tfp_growth))
    assert logs.average_capital_share == 0.3


def test_labour_shares_weight_each_period() -> None:
    outputs = run(
        calculation="growth_accounting",
        output_growth=[0.0, 0.0],
        capital_growth=[0.1, 0.1],
        labour_growth=[0.0, 0.0],
        labour_share=[0.6, 0.8],
        method="discrete",
    )
    assert outputs.capital_contribution == pytest.approx((0.4 * 0.1 + 0.2 * 0.1) / 2)
    assert outputs.average_capital_share == pytest.approx(0.3)


def test_no_output_growth_leaves_the_tfp_share_undefined() -> None:
    result = run_model(
        solow_growth,
        {
            "calculation": "growth_accounting",
            "output_growth": [0.0],
            "capital_growth": [0.02],
            "labour_growth": [0.01],
            "capital_share": 0.3,
        },
    )
    assert result.outputs.tfp_share is None
    assert [w.code for w in result.warnings] == ["no_output_growth"]


def test_a_tfp_index_that_collapses_is_refused() -> None:
    with pytest.raises(DomainError, match="TFP index"):
        run(
            calculation="growth_accounting",
            output_growth=[-0.99],
            capital_growth=[1.0],
            labour_growth=[1.0],
            capital_share=0.5,
            method="discrete",
        )


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"capital_share": 0.3, "labour_share": [0.6, 0.6]}, "one of labour_share"),
        ({}, "one of labour_share"),
        ({"capital_share": 0.3, "labour_growth": [0.01]}, "labour_growth has 1"),
    ],
)
def test_inputs_out_of_line_are_refused(changes: dict[str, Any], message: str) -> None:
    inputs = {
        "calculation": "growth_accounting",
        "output_growth": [0.03, 0.02],
        "capital_growth": [0.04, 0.01],
        "labour_growth": [0.01, 0.0],
    } | changes
    with pytest.raises(InputError, match=message):
        run(**inputs)
