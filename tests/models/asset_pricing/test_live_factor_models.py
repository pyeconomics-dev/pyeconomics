# tests/models/asset_pricing/test_live_factor_models.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Step 16 models bind the Ken French Data Library live (``pytest -m live``).

The library is library-only: none of it is committed, so these checks fetch it at
run time, inside ``cache.bypass()`` so nothing is stored, bind each profile of the
four models as of a date and run them. The weekly live run (providers-live.yml)
executes them; they need no key.
"""

from __future__ import annotations

import datetime as dt
import math
from typing import Any

import pytest

from pyeconomics.core import run_model
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.data import cache
from pyeconomics.data.bindings import bind_model
from pyeconomics.models.asset_pricing import factor_model_tests, factor_regression
from pyeconomics.models.portfolio import black_litterman, risk_based_allocation

pytestmark = pytest.mark.live

AS_OF = dt.date(2025, 12, 31)


def _bind(model: Any, **options: Any) -> Any:  # noqa: ANN401 - a Bound
    with cache.bypass():
        return bind_model(model, as_of=AS_OF, **options)


@pytest.mark.parametrize("profile", ["default", "ff5"])
@pytest.mark.parametrize("calculation", ["grs", "fama_macbeth"])
def test_the_factor_tests_bind_the_25_portfolios(
    profile: str, calculation: str
) -> None:
    bound = _bind(
        factor_model_tests, profile=profile, overrides={"calculation": calculation}
    )
    returns, factors = bound.values["returns"], bound.values["factors"]
    assert len(returns) == len(factors) == 120
    assert {len(row) for row in returns} == {25}
    assert {len(row) for row in factors} == {3 if profile == "default" else 5}
    for record in bound.sources:
        assert record.provider == "ken_french"
        assert record.observation_end <= AS_OF
        assert REVISED_DATA in record.warnings
    assert len({record.observation_end for record in bound.sources}) == 1
    outputs = run_model(factor_model_tests, bound).outputs
    if calculation == "grs":
        assert math.isfinite(outputs.statistic)
        assert 0.0 <= outputs.p_value <= 1.0
    else:
        assert all(
            s >= f
            for s, f in zip(
                outputs.shanken_standard_errors,
                outputs.premium_standard_errors,
                strict=True,
            )
        )


@pytest.mark.parametrize(
    ("profile", "calculation"),
    [
        ("default", "capm"),
        ("default", "ff3"),
        ("default", "carhart"),
        ("ff5", "ff5"),
        ("ff5", "ff6"),
    ],
)
def test_a_portfolios_returns_regress_on_the_bound_factors(
    profile: str, calculation: str
) -> None:
    # The user's returns: here, the big-growth portfolio (BIG LoBM, column 21)
    # over the same 60 months, which tracks the market closely.
    panel = _bind(factor_model_tests, overrides={"calculation": "grs"})
    tail = [row[20] for row in panel.values["returns"][-60:]]
    risk_free = panel.values["risk_free"][-60:]
    given: dict[str, Any] = {
        "calculation": calculation,
        "returns": tail,
        "periods_per_year": 12,
    }
    if calculation == "capm":
        given["market_premium"] = 0.005
    bound = _bind(factor_regression, profile=profile, overrides=given)
    assert bound.values["risk_free"] == tuple(risk_free)
    outputs = run_model(factor_regression, bound).outputs
    assert 0.5 < outputs.market_beta < 2.0
    assert outputs.r_squared is not None
    assert outputs.r_squared > 0.7
    assert outputs.observations == 60


@pytest.mark.parametrize(
    "calculation",
    ["inverse_volatility", "equal_risk_contribution", "hierarchical_risk_parity"],
)
def test_the_allocations_bind_the_industry_portfolios(calculation: str) -> None:
    bound = _bind(risk_based_allocation, overrides={"calculation": calculation})
    assert len(bound.values["returns"]) == 120
    outputs = run_model(risk_based_allocation, bound).outputs
    assert len(outputs.weights) == 12
    assert math.fsum(outputs.weights) == pytest.approx(1.0)


def test_black_litterman_binds_the_industry_covariance() -> None:
    bound = _bind(black_litterman, overrides={"market_weights": [1 / 12] * 12})
    outputs = run_model(black_litterman, bound).outputs
    assert outputs.weights == pytest.approx([1 / 12] * 12)
    assert all(math.isfinite(v) for v in outputs.equilibrium_returns)
