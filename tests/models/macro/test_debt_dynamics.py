# tests/models/macro/test_debt_dynamics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.debt_dynamics``: the identity's invariants, its paths and its bounds."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.macro import debt_dynamics

RATES = st.floats(-0.1, 0.5)
GROWTH = st.floats(-0.3, 0.5)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return run_model(debt_dynamics, inputs).outputs


@st.composite
def paths(draw: st.DrawFn, size: int | None = None) -> dict[str, Any]:
    periods = size or draw(st.integers(1, 40))
    return {
        "initial_ratio": draw(st.floats(0.0, 3.0)),
        "interest_rate": draw(st.lists(RATES, min_size=periods, max_size=periods)),
        "nominal_growth": draw(st.lists(GROWTH, min_size=periods, max_size=periods)),
        "primary_balance": draw(
            st.lists(st.floats(-0.1, 0.1), min_size=periods, max_size=periods)
        ),
    }


@pytest.mark.invariant("macro.debt_dynamics", "stabilizing_balance_holds_the_ratio")
@given(drawn=paths(), ratio=st.floats(0.0, 0.4))
def test_running_the_stabilizing_balance_holds_the_ratio(
    drawn: dict[str, Any], ratio: float
) -> None:
    # A ratio of at most 0.4 keeps every stabilizing balance, at most
    # 0.4 x 0.8 / 0.7, inside the input's bound of 0.5: no draw is wasted.
    drawn["initial_ratio"] = ratio
    balances = [
        ratio * (i - g) / (1 + g)
        for i, g in zip(drawn["interest_rate"], drawn["nominal_growth"], strict=True)
    ]
    drawn["primary_balance"] = balances
    outputs = run(**drawn)
    # The model reads each period's ratio off the path, which carries rounding.
    assert outputs.stabilizing_balance == pytest.approx(
        tuple(balances), rel=1e-12, abs=1e-15
    )
    for value in outputs.debt_ratio_path:
        assert value == pytest.approx(ratio, rel=1e-12, abs=1e-15)


@pytest.mark.invariant(
    "macro.debt_dynamics", "zero_balance_and_r_equal_g_hold_the_ratio"
)
@given(ratio=st.floats(0.0, 10.0), rates=st.lists(RATES, min_size=1, max_size=100))
def test_r_equal_to_g_with_no_primary_balance_holds_the_ratio(
    ratio: float, rates: list[float]
) -> None:
    outputs = run(
        initial_ratio=ratio,
        interest_rate=rates,
        nominal_growth=rates,
        primary_balance=[0.0] * len(rates),
    )
    assert outputs.debt_ratio_path == (ratio,) * len(rates)
    assert outputs.interest_growth_differential == (0.0,) * len(rates)
    assert outputs.change_in_ratio == 0.0


@pytest.mark.invariant("macro.debt_dynamics", "debt_rises_with_the_interest_rate")
@given(drawn=paths(), bump=st.floats(0.0, 0.1))
def test_a_higher_interest_rate_never_lowers_the_ratio(
    drawn: dict[str, Any], bump: float
) -> None:
    drawn["primary_balance"] = [min(b, 0.0) for b in drawn["primary_balance"]]
    higher = dict(drawn)
    higher["interest_rate"] = [min(0.5, i + bump) for i in drawn["interest_rate"]]
    try:
        base, more = run(**drawn), run(**higher)
    except DomainError:
        return  # a path past a million times GDP
    for low, high in zip(base.debt_ratio_path, more.debt_ratio_path, strict=True):
        assert high >= low * (1 - 1e-12)


def test_the_identity_one_step_at_a_time() -> None:
    outputs = run(
        initial_ratio=1.0,
        interest_rate=[0.04, 0.03],
        nominal_growth=[0.02, 0.05],
        primary_balance=[-0.01, 0.02],
    )
    first = 1.0 * 1.04 / 1.02 + 0.01
    second = first * 1.03 / 1.05 - 0.02
    assert outputs.debt_ratio_path == pytest.approx((first, second), rel=1e-15)
    assert outputs.stabilizing_balance == pytest.approx(
        (0.02 / 1.02, first * -0.02 / 1.05), rel=1e-14
    )
    assert outputs.interest_growth_differential == pytest.approx((0.02, -0.02))
    assert outputs.final_ratio == outputs.debt_ratio_path[-1]


def test_r_below_g_lets_a_deficit_hold_the_ratio_down() -> None:
    outputs = run(
        initial_ratio=1.0,
        interest_rate=[0.02] * 10,
        nominal_growth=[0.04] * 10,
        primary_balance=[-0.01] * 10,
    )
    assert outputs.final_ratio < 1.0
    assert all(b < 0 for b in outputs.stabilizing_balance)


def test_paths_of_different_lengths_are_refused() -> None:
    with pytest.raises(InputError, match="one value per period"):
        run(
            initial_ratio=1.0,
            interest_rate=[0.03, 0.03],
            nominal_growth=[0.04],
            primary_balance=[0.0, 0.0],
        )


def test_a_path_that_compounds_past_its_bound_is_refused() -> None:
    with pytest.raises(DomainError, match=r"1e\+06 times GDP"):
        run(
            initial_ratio=10.0,
            interest_rate=[0.5] * 100,
            nominal_growth=[-0.5] * 100,
            primary_balance=[0.0] * 100,
        )
