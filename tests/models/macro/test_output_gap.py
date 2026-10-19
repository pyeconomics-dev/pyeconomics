# tests/models/macro/test_output_gap.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.output_gap``: invariants, oracles, defaults by frequency and edges.

The oracles are independent implementations: statsmodels' ``hpfilter``,
``bkfilter`` and ``cffilter`` and QuantEcon's ``hamilton_filter`` (both in the
test group). Each runs on the log of the series, as the model does, and the
model's log-form cycle must match.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest
import quantecon
from hypothesis import given, settings
from hypothesis import strategies as st
from statsmodels.tsa.filters.bk_filter import bkfilter
from statsmodels.tsa.filters.cf_filter import cffilter
from statsmodels.tsa.filters.hp_filter import hpfilter

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.macro import output_gap

FREQUENCIES = ("annual", "quarterly", "monthly")
PER_YEAR = {"annual": 1, "quarterly": 4, "monthly": 12}
LAMBDA = {"annual": 6.25, "quarterly": 1600.0, "monthly": 129_600.0}
BAND = {"annual": (2, 8, 3), "quarterly": (6, 32, 12), "monthly": (18, 96, 36)}
FILTERS = ("hp", "hamilton", "baxter_king", "christiano_fitzgerald")


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(output_gap, inputs).outputs


def walk(size: int, seed: int, level: float = 20_000.0) -> list[float]:
    """Real output: a random walk with drift in logs."""
    rng = np.random.default_rng(seed)
    logs = math.log(level) + np.cumsum(0.006 + 0.008 * rng.normal(size=size))
    return [float(v) for v in np.exp(logs)]


def needed(calculation: str, frequency: str) -> int:
    if calculation == "hamilton":
        return 4 * PER_YEAR[frequency] + 1
    if calculation == "baxter_king":
        return 2 * BAND[frequency][2] + 1
    return 3


@st.composite
def filtered(draw: st.DrawFn) -> dict[str, Any]:
    """A filter, a frequency and a series long enough for it."""
    calculation = draw(st.sampled_from(FILTERS))
    frequency = draw(st.sampled_from(FREQUENCIES))
    size = needed(calculation, frequency) + draw(st.integers(0, 60))
    series = walk(size, draw(st.integers(0, 2**32 - 1)))
    form = draw(st.sampled_from(["ratio", "log"]))
    return {
        "calculation": calculation,
        "frequency": frequency,
        "series": series,
        "form": form,
    }


# --- invariants -------------------------------------------------------------------


@pytest.mark.invariant("macro.output_gap", "trend_plus_cycle_equals_series")
@settings(deadline=None)
@given(inputs=filtered())
def test_the_trend_and_the_gap_recombine_into_the_series(
    inputs: dict[str, Any],
) -> None:
    outputs = run(**inputs)
    covered = inputs["series"][outputs.start : outputs.start + len(outputs.cycle)]
    for value, trend, gap in zip(covered, outputs.trend, outputs.cycle, strict=True):
        if inputs["form"] == "log":
            assert math.log(trend) + gap == pytest.approx(math.log(value), abs=1e-12)
        else:
            assert trend * (1.0 + gap) == pytest.approx(value, rel=1e-12)
    assert outputs.gap == outputs.cycle[-1]


@pytest.mark.invariant("macro.output_gap", "hp_cycle_zero_for_linear_series")
@given(
    level=st.floats(1.0, 1e9),
    growth=st.floats(-0.03, 0.03),
    size=st.integers(3, 200),
    frequency=st.sampled_from(FREQUENCIES),
)
def test_the_hp_filter_leaves_no_cycle_in_constant_growth(
    level: float, growth: float, size: int, frequency: str
) -> None:
    series = [level * math.exp(growth * t) for t in range(size)]
    outputs = run(calculation="hp", series=series, frequency=frequency, form="log")
    assert max(abs(c) for c in outputs.cycle) < 1e-9


@pytest.mark.invariant("macro.output_gap", "band_pass_removes_linear_trend")
@given(
    level=st.floats(1.0, 1e9),
    growth=st.floats(-0.03, 0.03),
    extra=st.integers(0, 120),
    calculation=st.sampled_from(["baxter_king", "christiano_fitzgerald"]),
    frequency=st.sampled_from(FREQUENCIES),
)
def test_the_band_pass_filters_leave_no_cycle_in_constant_growth(
    level: float, growth: float, extra: int, calculation: str, frequency: str
) -> None:
    size = needed(calculation, frequency) + extra
    series = [level * math.exp(growth * t) for t in range(size)]
    outputs = run(
        calculation=calculation, series=series, frequency=frequency, form="log"
    )
    assert max(abs(c) for c in outputs.cycle) < 1e-9


@pytest.mark.invariant("macro.output_gap", "gap_zero_when_actual_equals_potential")
@given(
    levels=st.lists(st.floats(1e-3, 1e15), min_size=1, max_size=40),
    form=st.sampled_from(["ratio", "log"]),
)
def test_no_gap_when_output_is_at_potential(levels: list[float], form: str) -> None:
    outputs = run(
        calculation="from_potential", actual=levels, potential=levels, form=form
    )
    assert outputs.cycle == (0.0,) * len(levels)
    assert outputs.gap == 0.0
    assert outputs.trend == tuple(levels)


@pytest.mark.invariant("macro.output_gap", "hamilton_cycle_has_zero_mean")
@settings(deadline=None)
@given(
    seed=st.integers(0, 2**32 - 1),
    extra=st.integers(0, 80),
    frequency=st.sampled_from(FREQUENCIES),
)
def test_the_hamilton_cycle_sums_to_zero_in_logs(
    seed: int, extra: int, frequency: str
) -> None:
    series = walk(needed("hamilton", frequency) + extra, seed)
    outputs = run(
        calculation="hamilton", series=series, frequency=frequency, form="log"
    )
    assert abs(math.fsum(outputs.cycle)) < 1e-9


# --- oracles ----------------------------------------------------------------------


@pytest.mark.oracle("macro.output_gap")
@pytest.mark.parametrize("frequency", FREQUENCIES)
@pytest.mark.parametrize("size", [3, 40, 250, 2_000])
def test_statsmodels_hpfilter_agrees(frequency: str, size: int) -> None:
    series = walk(size, size)
    outputs = run(calculation="hp", series=series, frequency=frequency, form="log")
    expected, _ = hpfilter(np.log(series), lamb=LAMBDA[frequency])
    np.testing.assert_allclose(outputs.cycle, expected, rtol=0, atol=1e-9)
    assert outputs.smoothing == LAMBDA[frequency]


@pytest.mark.oracle("macro.output_gap")
@pytest.mark.parametrize("frequency", FREQUENCIES)
@pytest.mark.parametrize("extra", [0, 40, 400])
def test_statsmodels_bkfilter_agrees(frequency: str, extra: int) -> None:
    low, high, k = BAND[frequency]
    series = walk(2 * k + 1 + extra, extra + k)
    outputs = run(
        calculation="baxter_king", series=series, frequency=frequency, form="log"
    )
    expected = bkfilter(np.log(series), low=low, high=high, K=k)
    np.testing.assert_allclose(outputs.cycle, expected, rtol=0, atol=1e-12)
    assert outputs.start == k
    assert (outputs.low, outputs.high, outputs.lead_lag) == (low, high, k)


@pytest.mark.oracle("macro.output_gap")
@pytest.mark.parametrize("drift", [True, False])
@pytest.mark.parametrize("frequency", FREQUENCIES)
@pytest.mark.parametrize("size", [3, 50, 600])
def test_statsmodels_cffilter_agrees(drift: bool, frequency: str, size: int) -> None:  # noqa: FBT001
    low, high, _ = BAND[frequency]
    series = walk(size, size + 7)
    outputs = run(
        calculation="christiano_fitzgerald",
        series=series,
        frequency=frequency,
        drift=drift,
        form="log",
    )
    expected, _ = cffilter(np.log(series), low=low, high=high, drift=drift)
    np.testing.assert_allclose(outputs.cycle, expected, rtol=0, atol=1e-12)


@pytest.mark.oracle("macro.output_gap")
@pytest.mark.parametrize("frequency", FREQUENCIES)
@pytest.mark.parametrize("extra", [0, 30, 300])
def test_quantecon_hamilton_filter_agrees(frequency: str, extra: int) -> None:
    h, p = 2 * PER_YEAR[frequency], PER_YEAR[frequency]
    series = walk(2 * p + h + 1 + extra, extra + 3)
    outputs = run(
        calculation="hamilton", series=series, frequency=frequency, form="log"
    )
    cycle, trend = quantecon.hamilton_filter(np.log(series), h, p)
    np.testing.assert_allclose(outputs.cycle, cycle[p + h - 1 :], rtol=0, atol=1e-8)
    np.testing.assert_allclose(
        np.log(outputs.trend), trend[p + h - 1 :], rtol=0, atol=1e-8
    )
    assert (outputs.start, outputs.horizon, outputs.lags) == (p + h - 1, h, p)


@pytest.mark.oracle("macro.output_gap")
@given(
    seed=st.integers(0, 2**32 - 1),
    horizon=st.integers(1, 10),
    lags=st.integers(1, 6),
    extra=st.integers(0, 60),
)
@settings(deadline=None)
def test_quantecon_agrees_for_any_horizon_and_lag(
    seed: int, horizon: int, lags: int, extra: int
) -> None:
    series = walk(2 * lags + horizon + 1 + extra, seed)
    outputs = run(
        calculation="hamilton",
        series=series,
        frequency="quarterly",
        horizon=horizon,
        lags=lags,
        form="log",
    )
    cycle, _ = quantecon.hamilton_filter(np.log(series), horizon, lags)
    np.testing.assert_allclose(
        outputs.cycle, cycle[lags + horizon - 1 :], rtol=0, atol=1e-7
    )


# --- the calculations' own rules -----------------------------------------------


def test_the_ratio_gap_is_actual_over_potential_less_one() -> None:
    outputs = run(
        calculation="from_potential", actual=[105.0, 98.0], potential=[100.0, 100.0]
    )
    assert outputs.cycle == pytest.approx((0.05, -0.02), abs=1e-15)
    logs = run(
        calculation="from_potential",
        actual=[105.0, 98.0],
        potential=[100.0, 100.0],
        form="log",
    )
    assert logs.cycle == pytest.approx((math.log(1.05), math.log(0.98)), abs=1e-15)
    assert logs.gap == logs.cycle[-1]


def test_the_ratio_gap_of_a_filter_is_the_log_gap_exponentiated() -> None:
    series = walk(60, 11)
    ratio = run(calculation="hp", series=series, frequency="quarterly")
    logs = run(calculation="hp", series=series, frequency="quarterly", form="log")
    assert ratio.cycle == pytest.approx(tuple(math.expm1(c) for c in logs.cycle))
    assert ratio.trend == logs.trend


def test_overridden_settings_are_used_and_reported() -> None:
    series = walk(80, 5)
    hp = run(calculation="hp", series=series, frequency="quarterly", smoothing=100.0)
    expected, _ = hpfilter(np.log(series), lamb=100.0)
    assert hp.smoothing == 100.0
    np.testing.assert_allclose(
        [math.log1p(c) for c in hp.cycle], expected, rtol=0, atol=1e-12
    )
    bk = run(
        calculation="baxter_king",
        series=series,
        frequency="quarterly",
        low=4,
        high=20,
        lead_lag=8,
    )
    assert (bk.low, bk.high, bk.lead_lag, bk.start, len(bk.cycle)) == (4, 20, 8, 8, 64)


def test_baxter_king_warns_that_it_loses_the_ends() -> None:
    result = run_model(
        output_gap,
        {"calculation": "baxter_king", "series": walk(30, 1), "frequency": "quarterly"},
    )
    assert [w.code for w in result.warnings] == ["end_points_lost"]


def test_a_series_of_minimum_length_filters() -> None:
    minimal = run(calculation="hp", series=[100.0, 103.0, 101.0], frequency="annual")
    assert len(minimal.cycle) == 3
    bk = run(calculation="baxter_king", series=walk(25, 2), frequency="quarterly")
    assert len(bk.cycle) == 1
    hamilton = run(calculation="hamilton", series=walk(17, 3), frequency="quarterly")
    assert len(hamilton.cycle) == 6


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        (
            {"calculation": "from_potential", "actual": [1.0, 2.0], "potential": [1.0]},
            "one value of each",
        ),
        (
            {"calculation": "hamilton", "series": [1.0] * 16, "frequency": "quarterly"},
            "at least 17",
        ),
        (
            {
                "calculation": "baxter_king",
                "series": [1.0] * 24,
                "frequency": "quarterly",
            },
            "at least 25",
        ),
        (
            {
                "calculation": "christiano_fitzgerald",
                "series": [1.0, 2.0, 3.0],
                "frequency": "quarterly",
                "low": 40,
            },
            "low below high",
        ),
        ({"calculation": "hp", "series": [1.0, 2.0, 3.0]}, "frequency"),
        (
            {"calculation": "hp", "series": [1.0, 0.0, 3.0], "frequency": "annual"},
            "greater than 0",
        ),
    ],
)
def test_bad_inputs_are_refused(inputs: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        run(**inputs)


def test_a_log_linear_series_has_no_hamilton_regression() -> None:
    series = [100.0 * math.exp(0.01 * t) for t in range(40)]
    with pytest.raises(DomainError, match="collinear"):
        run(calculation="hamilton", series=series, frequency="quarterly")


def test_a_ratio_gap_that_rounds_past_its_bound_is_refused() -> None:
    # The log form passes its check; the quotient itself is 1,000,000.000000002.
    with pytest.raises(DomainError, match="actual over potential"):
        run(
            calculation="from_potential",
            actual=[893317935874679.4],
            potential=[893317042.5576351],
        )


def test_a_series_that_moves_by_absurd_factors_is_refused() -> None:
    with pytest.raises(DomainError, match="moves by factors"):
        run(
            calculation="from_potential",
            actual=[1e15, 1.0],
            potential=[1e-6, 1.0],
        )
    with pytest.raises(DomainError, match="moves by factors"):
        run(
            calculation="from_potential",
            actual=[1e-300, 1.0],
            potential=[1e15, 1.0],
            form="log",
        )
