# tests/models/performance/test_brinson_attribution.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``performance.brinson_attribution``: the attribution identities and errors.

The identities are the check: each period's effects sum to its active return,
and Carino's linked effects sum to the difference of the compound returns.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pandas as pd
import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.performance import brinson_attribution

CALCULATION = st.sampled_from(["bhb", "brinson_fachler"])


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(brinson_attribution, inputs).outputs


@st.composite
def weights(draw: st.DrawFn, periods: int, sectors: int) -> list[list[float]]:
    rows = []
    for _ in range(periods):
        raw = draw(st.lists(st.floats(0.01, 1.0), min_size=sectors, max_size=sectors))
        rows.append([w / sum(raw) for w in raw])
    return rows


@st.composite
def sectors(draw: st.DrawFn, max_periods: int = 6) -> dict[str, Any]:
    periods = draw(st.integers(1, max_periods))
    count = draw(st.integers(1, 6))
    returns = st.lists(
        st.lists(st.floats(-0.5, 0.5), min_size=count, max_size=count),
        min_size=periods,
        max_size=periods,
    )
    return {
        "portfolio_weights": draw(weights(periods, count)),
        "benchmark_weights": draw(weights(periods, count)),
        "portfolio_returns": draw(returns),
        "benchmark_returns": draw(returns),
    }


@pytest.mark.invariant(
    "performance.brinson_attribution", "effects_sum_to_active_return"
)
@given(calculation=CALCULATION, chosen=sectors())
def test_each_periods_effects_sum_to_its_active_return(
    calculation: str, chosen: dict[str, Any]
) -> None:
    out = run(calculation=calculation, **chosen)
    for k in range(out.periods):
        effects = (
            out.period_allocation[k]
            + out.period_selection[k]
            + out.period_interaction[k]
        )
        active = out.period_portfolio_returns[k] - out.period_benchmark_returns[k]
        assert math.isclose(effects, active, abs_tol=1e-14)
    wp, rp = (
        np.array(chosen["portfolio_weights"]),
        np.array(chosen["portfolio_returns"]),
    )
    assert np.allclose(out.period_portfolio_returns, (wp * rp).sum(axis=1), atol=1e-15)


@pytest.mark.invariant(
    "performance.brinson_attribution", "linked_effects_sum_to_geometric_active_return"
)
@given(calculation=CALCULATION, chosen=sectors())
def test_linked_effects_sum_to_the_compound_difference(
    calculation: str, chosen: dict[str, Any]
) -> None:
    out = run(calculation=calculation, **chosen)
    compound_p = math.prod(1 + r for r in out.period_portfolio_returns) - 1
    compound_b = math.prod(1 + r for r in out.period_benchmark_returns) - 1
    assert math.isclose(out.portfolio_return, compound_p, rel_tol=1e-12, abs_tol=1e-14)
    assert math.isclose(out.benchmark_return, compound_b, rel_tol=1e-12, abs_tol=1e-14)
    assert math.isclose(
        out.allocation + out.selection + out.interaction,
        out.active_return,
        abs_tol=1e-12,
    )
    assert math.isclose(sum(out.sector_allocation), out.allocation, abs_tol=1e-14)


@pytest.mark.invariant(
    "performance.brinson_attribution", "zero_effects_for_identical_portfolios"
)
@given(calculation=CALCULATION, chosen=sectors())
def test_a_portfolio_identical_to_its_benchmark_has_no_effects(
    calculation: str, chosen: dict[str, Any]
) -> None:
    chosen["benchmark_weights"] = chosen["portfolio_weights"]
    chosen["benchmark_returns"] = chosen["portfolio_returns"]
    out = run(calculation=calculation, **chosen)
    assert out.active_return == 0.0
    for effect in ("sector_allocation", "sector_selection", "sector_interaction"):
        assert all(e == 0.0 for e in getattr(out, effect))
    assert out.allocation == out.selection == out.interaction == 0.0


@given(chosen=sectors())
def test_both_methods_split_the_same_total_differently(chosen: dict[str, Any]) -> None:
    bhb = run(calculation="bhb", **chosen)
    fachler = run(calculation="brinson_fachler", **chosen)
    assert np.allclose(bhb.period_allocation, fachler.period_allocation, atol=1e-14)
    assert bhb.sector_selection == fachler.sector_selection


ONE = {
    "portfolio_weights": [[0.5, 0.5]],
    "benchmark_weights": [[0.5, 0.5]],
    "portfolio_returns": [[0.1, -0.1]],
    "benchmark_returns": [[0.05, 0.0]],
}


def test_matrices_may_be_numpy_arrays_or_dataframes() -> None:
    expected = run(calculation="bhb", **ONE)
    as_arrays = {k: np.array(v) for k, v in ONE.items()}
    assert run(calculation="bhb", **as_arrays) == expected
    as_frames = {k: pd.DataFrame(v) for k, v in ONE.items()}
    assert run(calculation="bhb", **as_frames) == expected


def test_an_oversized_matrix_is_refused_before_conversion() -> None:
    with pytest.raises(InputError, match="at most 60000 entries"):
        run(calculation="bhb", **{**ONE, "portfolio_returns": np.zeros((601, 100))})


def test_a_single_period_total_loss_needs_no_linking() -> None:
    out = run(
        calculation="bhb",
        **{
            **ONE,
            "portfolio_returns": [[-1.0, -1.0]],
            "benchmark_returns": [[-1.0, -1.0]],
        },
    )
    assert out.portfolio_return == -1.0
    assert out.active_return == 0.0


def test_linking_a_total_loss_is_a_domain_error() -> None:
    with pytest.raises(DomainError, match="Carino linking"):
        run(
            calculation="bhb",
            portfolio_weights=[[1.0], [1.0]],
            benchmark_weights=[[1.0], [1.0]],
            portfolio_returns=[[-1.0], [0.1]],
            benchmark_returns=[[0.1], [0.1]],
        )


def test_a_compound_return_past_its_bound_is_a_domain_error() -> None:
    periods = 4
    with pytest.raises(DomainError, match="outside its bounds"):
        run(
            calculation="bhb",
            portfolio_weights=[[1.0]] * periods,
            benchmark_weights=[[1.0]] * periods,
            portfolio_returns=[[100.0]] * periods,
            benchmark_returns=[[0.0]] * periods,
        )


@pytest.mark.parametrize(
    ("change", "match"),
    [
        (
            {"portfolio_returns": [[0.1, -0.1], [0.0, 0.0]]},
            "must have 1 rows of 2 sectors",
        ),
        ({"benchmark_weights": [[0.5, 0.25, 0.25]]}, "must have 1 rows of 2 sectors"),
        ({"portfolio_weights": [[0.5, 0.4]]}, "sum to"),
        ({"benchmark_weights": [[0.6, 0.6]]}, "sum to"),
    ],
)
def test_the_matrices_must_agree(change: dict[str, Any], match: str) -> None:
    with pytest.raises(InputError, match=match):
        run(calculation="bhb", **{**ONE, **change})


def test_weights_within_rounding_of_one_are_rescaled() -> None:
    out = run(calculation="bhb", **{**ONE, "portfolio_weights": [[0.5000004, 0.5]]})
    assert math.isclose(
        out.allocation + out.selection + out.interaction,
        out.active_return,
        abs_tol=1e-15,
    )


@pytest.mark.parametrize(
    ("held", "index"),
    [(-0.6, -0.6), (0.0, -0.6), (-0.6, -0.5), (-0.55, 0.0)],
)
def test_linking_near_a_total_loss_keeps_the_identity(
    held: float, index: float
) -> None:
    # Review regression: a compound return rounding to -1 divided by zero in
    # Carino's k, and near it the linked effects missed the active return.
    periods = 50
    out = run(
        calculation="bhb",
        portfolio_weights=[[0.5, 0.5]] * periods,
        benchmark_weights=[[0.5, 0.5]] * periods,
        portfolio_returns=[[held, held]] * periods,
        benchmark_returns=[[index, index]] * periods,
    )
    effects = out.allocation + out.selection + out.interaction
    assert math.isclose(effects, out.active_return, rel_tol=1e-12, abs_tol=1e-300)
    exact = (1 + held) ** periods - (1 + index) ** periods
    assert math.isclose(out.active_return, exact, rel_tol=1e-12, abs_tol=1e-300)
