# tests/models/performance/test_risk_adjusted.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``performance.risk_adjusted``: invariants, undefined ratios and oracles.

empyrical-reloaded is not used: 0.5.12, its latest release, imports ``pytz``
without declaring it (pandas 3 no longer installs it), pins ``peewee<3.17.4``,
and its capture functions reject the ``annualization`` argument. The ratios are
instead recomputed here with NumPy from their stated definitions, and beta and
Jensen's alpha come from ``scipy.stats.linregress``, an independent least-squares
fit. Both libraries are imported at the top, so a missing one fails the suite.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import scipy.stats
from hypothesis import assume, given
from hypothesis import strategies as st

from pyeconomics.core import InputError, run_model
from pyeconomics.models.performance import risk_adjusted

MODERATE = st.floats(-0.2, 0.2)


def result(**inputs: Any) -> Any:  # noqa: ANN401 - a Result
    return run_model(risk_adjusted, inputs)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the outputs
    return result(**inputs).outputs


@st.composite
def series(draw: st.DrawFn, size: int | None = None) -> list[float]:
    n = size if size is not None else draw(st.integers(3, 40))
    values = draw(st.lists(MODERATE, min_size=n, max_size=n))
    assume(float(np.ptp(values)) > 1e-4)
    return values


@st.composite
def paired(draw: st.DrawFn) -> tuple[list[float], list[float]]:
    portfolio = draw(series())
    benchmark = draw(series(len(portfolio)))
    assume(float(np.ptp(np.array(portfolio) - np.array(benchmark))) > 1e-4)
    return portfolio, benchmark


@pytest.mark.invariant(
    "performance.risk_adjusted", "sharpe_invariant_to_positive_scaling"
)
@given(returns=series(), scale=st.floats(0.01, 4.0))
def test_scaling_returns_keeps_the_sharpe_ratio(
    returns: list[float], scale: float
) -> None:
    benchmark = [0.0] * len(returns)
    base = run(returns=returns, benchmark_returns=benchmark, periods_per_year=12)
    scaled = run(
        returns=[r * scale for r in returns],
        benchmark_returns=benchmark,
        periods_per_year=12,
    )
    assert math.isclose(
        scaled.sharpe_ratio, base.sharpe_ratio, rel_tol=1e-9, abs_tol=1e-12
    )


@pytest.mark.invariant(
    "performance.risk_adjusted", "tracking_error_zero_for_identical_series"
)
@pytest.mark.invariant(
    "performance.risk_adjusted", "capture_ratios_one_for_identical_series"
)
@pytest.mark.invariant(
    "performance.risk_adjusted", "beta_one_alpha_zero_for_identical_series"
)
@given(returns=series(), rate=st.floats(0.0, 0.01))
def test_a_portfolio_identical_to_its_benchmark(
    returns: list[float], rate: float
) -> None:
    found = result(
        returns=returns,
        benchmark_returns=returns,
        risk_free_returns=[rate] * len(returns),
        periods_per_year=252,
    )
    out = found.outputs
    assert out.tracking_error == 0.0
    assert out.information_ratio is None
    assert "zero_volatility" in [w.code for w in found.warnings]
    if any(b > 0 for b in returns):
        assert out.up_capture == 1.0
    if any(b < 0 for b in returns):
        assert out.down_capture == 1.0
    assert math.isclose(out.beta, 1.0, rel_tol=1e-12)
    assert math.isclose(out.jensen_alpha, 0.0, abs_tol=1e-12)


@pytest.mark.oracle("performance.risk_adjusted")
@given(pair=paired(), rate=st.floats(-0.001, 0.005))
def test_beta_and_alpha_match_scipy_linregress(
    pair: tuple[list[float], list[float]], rate: float
) -> None:
    portfolio, benchmark = pair
    out = run(
        returns=portfolio,
        benchmark_returns=benchmark,
        risk_free_returns=[rate] * len(portfolio),
        periods_per_year=12,
    )
    fit = scipy.stats.linregress(np.array(benchmark) - rate, np.array(portfolio) - rate)
    assert math.isclose(out.beta, fit.slope, rel_tol=1e-9, abs_tol=1e-12)
    assert math.isclose(
        out.jensen_alpha, 12 * fit.intercept, rel_tol=1e-8, abs_tol=1e-12
    )


@pytest.mark.oracle("performance.risk_adjusted")
@given(pair=paired(), mar=st.floats(-0.01, 0.01), m=st.sampled_from([4, 12, 52, 252]))
def test_ratios_match_a_numpy_recomputation(
    pair: tuple[list[float], list[float]], mar: float, m: int
) -> None:
    r, b = np.array(pair[0]), np.array(pair[1])
    out = run(
        returns=pair[0],
        benchmark_returns=pair[1],
        periods_per_year=m,
        minimum_acceptable_return=mar,
    )
    root = math.sqrt(m)
    close = {"rel_tol": 1e-9, "abs_tol": 1e-12}
    assert math.isclose(out.sharpe_ratio, r.mean() / r.std(ddof=1) * root, **close)
    assert math.isclose(out.annualized_volatility, r.std(ddof=1) * root, **close)
    downside = math.sqrt(float(np.mean(np.minimum(r - mar, 0) ** 2)))
    assert math.isclose(out.downside_deviation, downside * root, **close)
    sortino = (r.mean() - mar) / downside * root if downside > 0 else math.inf
    if abs(sortino) <= 1e6:
        assert math.isclose(out.sortino_ratio, sortino, **close)
    else:
        assert out.sortino_ratio is None
    active = r - b
    assert math.isclose(out.tracking_error, active.std(ddof=1) * root, **close)
    assert math.isclose(
        out.information_ratio, active.mean() / active.std(ddof=1) * root, **close
    )
    assert math.isclose(
        out.m_squared, r.mean() / r.std(ddof=1) * b.std(ddof=1) * m, **close
    )
    wealth = np.concatenate(([1.0], np.cumprod(1 + r)))
    drawdown = float(np.max(1 - wealth / np.maximum.accumulate(wealth)))
    assert math.isclose(out.max_drawdown, drawdown, rel_tol=1e-9, abs_tol=1e-15)
    growth = wealth[-1] ** (m / r.size) - 1
    if growth > 1e6:
        assert out.annualized_return is None
    else:
        assert math.isclose(out.annualized_return, growth, rel_tol=1e-9, abs_tol=1e-12)
        if drawdown > 1e-12 and abs(growth / drawdown) <= 1e6:
            assert math.isclose(out.calmar_ratio, growth / drawdown, rel_tol=1e-8)
    up = b > 0
    if up.any():
        # log1p and expm1 keep a tiny benchmark return that 1 + b would drop.
        mean_p = float(np.expm1(np.mean(np.log1p(r[up]))))
        mean_b = float(np.expm1(np.mean(np.log1p(b[up]))))
        if abs(mean_p / mean_b) <= 1e6:
            assert math.isclose(
                out.up_capture, mean_p / mean_b, rel_tol=1e-8, abs_tol=1e-10
            )
        else:
            assert out.up_capture is None


# --- undefined ratios and errors ---------------------------------------------------


def test_a_flat_benchmark_has_no_beta() -> None:
    found = result(
        returns=[0.01, 0.02, -0.01], benchmark_returns=[0.0] * 3, periods_per_year=12
    )
    out = found.outputs
    assert out.beta is out.treynor_ratio is out.jensen_alpha is None
    assert out.up_capture is out.down_capture is None
    codes = [w.code for w in found.warnings]
    assert "zero_volatility" in codes
    assert codes.count("no_periods") == 2


def test_no_downside_has_no_sortino_ratio() -> None:
    found = result(
        returns=[0.01, 0.02, 0.03],
        benchmark_returns=[0.01, -0.01, 0.02],
        periods_per_year=12,
    )
    assert found.outputs.sortino_ratio is None
    assert found.outputs.calmar_ratio is None
    assert "zero_denominator" in [w.code for w in found.warnings]


def test_a_total_loss_is_a_full_drawdown() -> None:
    out = run(
        returns=[0.1, -1.0, 0.0],
        benchmark_returns=[0.01, -0.02, 0.01],
        periods_per_year=12,
    )
    assert out.max_drawdown == 1.0
    assert out.annualized_return == -1.0
    assert out.calmar_ratio == -1.0


def test_a_huge_annualized_return_is_null() -> None:
    found = result(
        returns=[1.0, 2.0], benchmark_returns=[0.1, 0.2], periods_per_year=100_000
    )
    assert found.outputs.annualized_return is None
    assert found.outputs.calmar_ratio is None
    assert "unrepresentable_result" in [w.code for w in found.warnings]


def test_a_zero_beta_has_no_treynor_ratio() -> None:
    # The portfolio's excess returns are uncorrelated with the benchmark's.
    found = result(
        returns=[0.01, -0.01, -0.01, 0.01],
        benchmark_returns=[0.02, 0.02, -0.02, -0.02],
        periods_per_year=12,
    )
    assert found.outputs.beta == 0.0
    assert found.outputs.treynor_ratio is None


def test_the_series_must_cover_the_same_periods() -> None:
    with pytest.raises(InputError, match="same periods"):
        run(
            returns=[0.01, 0.02],
            benchmark_returns=[0.01, 0.02, 0.03],
            periods_per_year=12,
        )
    with pytest.raises(InputError, match="same periods"):
        run(
            returns=[0.01, 0.02],
            benchmark_returns=[0.01, 0.02],
            risk_free_returns=[0.0],
            periods_per_year=12,
        )


def test_an_overflowing_compound_return_is_null_not_an_error() -> None:
    # Review regression: the compound return overflowed to inf and the
    # annualization refused it with an undocumented InputError.
    found = result(
        returns=[1.0] * 1025,
        benchmark_returns=[0.01, 0.02] * 512 + [0.0],
        periods_per_year=252,
    )
    assert found.outputs.annualized_return is None
    assert "unrepresentable_result" in [w.code for w in found.warnings]


def test_a_long_run_of_losses_annualizes_to_its_true_rate() -> None:
    # Review regression: 600 monthly losses of 6.5% compound to a value that
    # rounds to -1, which used to annualize to -1 rather than 0.935^12 - 1.
    out = run(
        returns=[-0.065] * 600,
        benchmark_returns=[0.01, -0.01] * 300,
        periods_per_year=12,
    )
    assert math.isclose(out.annualized_return, 0.935**12 - 1, rel_tol=1e-12)
    assert math.isclose(
        out.calmar_ratio, (0.935**12 - 1) / out.max_drawdown, rel_tol=1e-12
    )
