# tests/models/international/test_parity_conditions.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``international.parity_conditions``: its invariants and the cross-entry test.

The covered-parity forward is held to ``derivatives.forwards``' ``fx_forward``,
which computes it from money-market rates on day counts; the relations
themselves are identities with no oracle library to add.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import DomainError, run_model
from pyeconomics.models.derivatives import forwards
from pyeconomics.models.international import parity_conditions

SPOTS = st.floats(min_value=1e-6, max_value=1e6)
RATES = st.floats(min_value=-0.05, max_value=1.0)
INFLATION = st.floats(min_value=-0.2, max_value=1.0)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(parity_conditions, inputs).outputs


@pytest.mark.invariant(
    "international.parity_conditions", "parity_forward_matches_derivatives_forwards"
)
@given(
    spot=SPOTS,
    days=st.integers(min_value=1, max_value=3650),
    quote_rate=RATES,
    base_rate=RATES,
)
def test_the_parity_forward_is_the_derivatives_fx_forward(
    spot: float, days: int, quote_rate: float, base_rate: float
) -> None:
    parity = run(
        calculation="covered_interest_parity",
        spot=spot,
        quote_rate=quote_rate,
        base_rate=base_rate,
        years=days / 365,
        compounding="simple",
    )
    forward = run_model(
        forwards,
        {
            "calculation": "fx_forward",
            "spot": spot,
            "days": days,
            "quote_rate": quote_rate,
            "base_rate": base_rate,
            "quote_day_count": "act_365_fixed",
            "base_day_count": "act_365_fixed",
        },
    ).outputs
    assert math.isclose(parity.forward_rate, forward.forward_rate, rel_tol=1e-14)
    assert math.isclose(
        parity.forward_premium, forward.forward_premium, rel_tol=1e-12, abs_tol=1e-14
    )


@pytest.mark.invariant("international.parity_conditions", "real_rate_identity")
@given(
    quote_rate=RATES,
    base_rate=RATES,
    quote_inflation=INFLATION,
    base_inflation=INFLATION,
)
def test_real_rates_and_inflation_give_the_nominal_rates(
    quote_rate: float, base_rate: float, quote_inflation: float, base_inflation: float
) -> None:
    result = run(
        calculation="international_fisher",
        quote_rate=quote_rate,
        base_rate=base_rate,
        quote_inflation=quote_inflation,
        base_inflation=base_inflation,
    )
    assert math.isclose(
        (1 + result.quote_real_rate) * (1 + quote_inflation),
        1 + quote_rate,
        rel_tol=1e-14,
    )
    assert math.isclose(
        (1 + result.base_real_rate) * (1 + base_inflation), 1 + base_rate, rel_tol=1e-14
    )
    assert math.isclose(
        1 + result.expected_change, (1 + quote_rate) / (1 + base_rate), rel_tol=1e-14
    )


@given(
    spot=SPOTS,
    quote_rate=RATES,
    base_rate=RATES,
    years=st.floats(min_value=0.01, max_value=10.0),
    compounding=st.sampled_from(["simple", "periodic", "continuous"]),
)
def test_uncovered_parity_expects_the_covered_forward(
    spot: float, quote_rate: float, base_rate: float, years: float, compounding: str
) -> None:
    common = {
        "spot": spot,
        "quote_rate": quote_rate,
        "base_rate": base_rate,
        "years": years,
        "compounding": compounding,
    }
    covered = run(calculation="covered_interest_parity", **common)
    uncovered = run(calculation="uncovered_interest_parity", **common)
    assert uncovered.expected_spot == covered.forward_rate
    assert uncovered.expected_change == covered.forward_premium


def test_equal_inflation_leaves_relative_ppp_at_the_spot() -> None:
    result = run(
        calculation="relative_ppp",
        spot=1.3,
        quote_inflation=0.04,
        base_inflation=0.04,
        years=7,
    )
    assert result.expected_spot == 1.3
    assert result.expected_change == 0.0


def test_a_spot_far_above_ppp_is_refused() -> None:
    with pytest.raises(DomainError, match="PPP rate"):
        run(calculation="absolute_ppp", quote_price=1.0, base_price=1.0, spot=1000.0)
