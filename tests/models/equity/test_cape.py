# tests/models/equity/test_cape.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``equity.cape``: its invariants, an oracle, refusals.

The oracle is pandas: Shiller's file computes a month's CAPE as its real price
over the mean of the previous 120 months' real earnings, which is a rolling
mean shifted by one month. Built that way over a long synthetic history, it must
agree with the model at every month.
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
from pyeconomics.models.equity import cape

LEVELS = st.floats(min_value=1.0, max_value=1000.0)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return run_model(cape, inputs).outputs


@pytest.mark.invariant("equity.cape", "constant_real_earnings_give_price_over_earnings")
@given(
    price=LEVELS,
    real=st.floats(min_value=0.1, max_value=100.0),
    level=LEVELS,
    cpi=st.lists(LEVELS, min_size=1, max_size=150),
)
def test_constant_real_earnings_give_price_over_earnings(
    price: float, real: float, level: float, cpi: list[float]
) -> None:
    earnings = [real * c / level for c in cpi]
    out = run(price=price, price_cpi=level, earnings=earnings, cpi=cpi, real_yield=0.01)
    assert math.isclose(out.cape, price / real, rel_tol=1e-12)
    assert math.isclose(out.average_real_earnings, real, rel_tol=1e-12)


@pytest.mark.invariant("equity.cape", "cape_yield_is_the_reciprocal")
@given(
    price=LEVELS,
    level=LEVELS,
    window=st.lists(
        st.tuples(st.floats(min_value=-20.0, max_value=200.0), LEVELS),
        min_size=1,
        max_size=150,
    ),
)
def test_the_cape_yield_is_the_reciprocal(
    price: float, level: float, window: list[tuple[float, float]]
) -> None:
    earnings, cpi = zip(*window, strict=True)
    result = run_model(
        cape,
        {
            "price": price,
            "price_cpi": level,
            "earnings": earnings,
            "cpi": cpi,
            "nominal_yield": 0.03,
            "inflation": 0.02,
        },
    )
    out = result.outputs
    if out.cape is None:
        assert [w.code for w in result.warnings] == ["no_positive_earnings"]
        assert out.cape_yield < 1e-6
    else:
        assert math.isclose(out.cape * out.cape_yield, 1.0, rel_tol=1e-12)
    assert math.isclose(out.excess_cape_yield, out.cape_yield - 0.01, abs_tol=1e-12)


@pytest.mark.oracle("equity.cape")
def test_cape_agrees_with_a_rolling_mean_over_a_long_history() -> None:
    months = 600
    t = np.arange(months)
    rng_free = np.sin(t / 7.0)  # deterministic waves, no randomness
    frame = pd.DataFrame(
        {
            "price": 100 * np.exp(0.004 * t) * (1 + 0.1 * rng_free),
            "earnings": 6 * np.exp(0.003 * t) * (1 + 0.2 * np.cos(t / 11.0)),
            "cpi": 20 * np.exp(0.0025 * t),
        }
    )
    real_price = frame["price"] / frame["cpi"]
    real_earnings = frame["earnings"] / frame["cpi"]
    expected = real_price / real_earnings.rolling(120).mean().shift(1)
    for month in range(120, months, 37):
        window = slice(month - 120, month)
        out = run(
            price=float(frame["price"][month]),
            price_cpi=float(frame["cpi"][month]),
            earnings=frame["earnings"][window].tolist(),
            cpi=frame["cpi"][window].tolist(),
            real_yield=0.01,
        )
        assert math.isclose(out.cape, float(expected[month]), rel_tol=1e-12)


def test_shillers_excess_yield_takes_trailing_ten_year_inflation() -> None:
    cpi = [100.0 * 1.003**k for k in range(120)]
    level = 100.0 * 1.003**120
    out = run(
        price=3000.0,
        price_cpi=level,
        earnings=[100.0] * 120,
        cpi=cpi,
        nominal_yield=0.045,
    )
    inflation = (level / cpi[0]) ** (12 / 120) - 1
    assert math.isclose(out.real_rate, 0.045 - inflation, rel_tol=1e-12)
    assert math.isclose(
        out.excess_cape_yield, out.cape_yield - (0.045 - inflation), rel_tol=1e-12
    )


@pytest.mark.parametrize(
    "inputs",
    [
        {"earnings": [1.0, 2.0], "cpi": [100.0], "real_yield": 0.01},
        {"earnings": [1.0], "cpi": [100.0]},
        {"earnings": [1.0], "cpi": [100.0], "real_yield": 0.01, "nominal_yield": 0.03},
        {"earnings": [1.0], "cpi": [100.0], "real_yield": 0.01, "inflation": 0.02},
    ],
    ids=["lengths", "no_rate", "two_rates", "inflation_without_nominal"],
)
def test_inconsistent_inputs_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        run_model(cape, {"price": 100.0, "price_cpi": 100.0, **inputs})


def test_runaway_inflation_has_no_real_rate() -> None:
    with pytest.raises(DomainError, match="100%"):
        run(price=100.0, price_cpi=1e6, earnings=[5.0], cpi=[1.0], nominal_yield=0.05)


def test_an_earnings_yield_beyond_its_bound_is_refused() -> None:
    with pytest.raises(DomainError, match="beyond"):
        run(price=0.01, price_cpi=1e9, earnings=[1e9], cpi=[0.01], real_yield=0.01)
