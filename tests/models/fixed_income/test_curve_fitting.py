# tests/models/fixed_income/test_curve_fitting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``fixed_income.curve_fitting``: its invariants, two oracles, refusals.

The oracles are an independent NumPy evaluation, written from the textbook
formulas with none of the model's numerics (no ``expm1``, discount factors
summed coupon by coupon), and QuantLib's Svensson curve: a
``FittedBondDiscountCurve`` built with given parameters evaluates the discount
function itself, and fitted to zero-coupon bonds it is the fit the model must
match or beat on yields, since the model minimizes the yield errors directly.
"""

from __future__ import annotations

import importlib
import math
from typing import Any

import numpy as np
import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import given, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, InputError, run_model
from pyeconomics.models.fixed_income import curve_fitting

# The package exports the model under its module's name: reach the module by path.
module = importlib.import_module("pyeconomics.models.fixed_income.curve_fitting")

MATURITIES = (0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0, 20.0, 30.0)
PERIODS = {"annual": 1, "semiannual": 2, "quarterly": 4, "monthly": 12}
BETA = st.floats(min_value=-0.08, max_value=0.08)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(curve_fitting, inputs).outputs


@st.composite
def identifiable(draw: st.DrawFn, *, svensson: bool = True) -> dict[str, float]:
    """Curves whose humps ten maturities to 30 years can tell apart.

    Each hump is at least one percentage point and the second decays within the
    maturities (tau2 at most 12 years): a hump near zero, or one so slow it is
    nearly a straight line out to 30 years, leaves its decay unidentified, and
    a fit can then stop a little short of the best (the limitations say so).
    """
    tau1 = draw(st.floats(min_value=0.3, max_value=4.0))

    def hump() -> float:
        size = draw(st.floats(min_value=0.01, max_value=0.05))
        return size if draw(st.booleans()) else -size

    found = {
        "beta0": draw(st.floats(min_value=0.0, max_value=0.08)),
        "beta1": draw(st.floats(min_value=-0.05, max_value=0.05)),
        "beta2": hump(),
        "tau1": tau1,
    }
    if svensson:
        found["beta3"] = hump()
        found["tau2"] = draw(st.floats(min_value=2.5 * tau1, max_value=12.0))
    return found


@st.composite
def parameters(draw: st.DrawFn, *, svensson: bool = True) -> dict[str, float]:
    """Curves of the shapes central banks publish: a level, a slope, two humps."""
    tau1 = draw(st.floats(min_value=0.3, max_value=4.0))
    found = {
        "beta0": draw(st.floats(min_value=0.0, max_value=0.08)),
        "beta1": draw(st.floats(min_value=-0.05, max_value=0.05)),
        "beta2": draw(st.floats(min_value=-0.05, max_value=0.05)),
        "tau1": tau1,
    }
    if svensson:
        found["beta3"] = draw(st.floats(min_value=-0.05, max_value=0.05))
        found["tau2"] = draw(st.floats(min_value=2.5 * tau1, max_value=25.0))
    return found


def _textbook(params: dict[str, float], n: float) -> tuple[float, float]:
    """Return the zero yield and the forward from the published formulas."""
    b0, b1, b2 = params["beta0"], params["beta1"], params["beta2"]
    b3, t1 = params.get("beta3", 0.0), params["tau1"]
    t2 = params.get("tau2") or t1
    a, b = n / t1, n / t2
    zero = (
        b0
        + b1 * (1 - math.exp(-a)) / a
        + b2 * ((1 - math.exp(-a)) / a - math.exp(-a))
        + b3 * ((1 - math.exp(-b)) / b - math.exp(-b))
    )
    forward = b0 + b1 * math.exp(-a) + b2 * a * math.exp(-a) + b3 * b * math.exp(-b)
    return zero, forward


def _textbook_par(params: dict[str, float], n: float, m: int) -> float:
    """A par yield coupon by coupon: whole periods back from maturity, then a stub."""
    whole = math.floor(n * m + 1e-9)
    stub = n - whole / m
    if stub > 1e-9:
        times = [stub + j / m for j in range(whole + 1)]
        accruals = [stub] + [1 / m] * whole
    else:
        times = [j / m for j in range(1, whole + 1)]
        accruals = [1 / m] * whole
    times[-1] = n
    factors = [math.exp(-_textbook(params, s)[0] * s) for s in times]
    return (1 - factors[-1]) / sum(
        a * d for a, d in zip(accruals, factors, strict=True)
    )


# --- invariants ----------------------------------------------------------------


@pytest.mark.invariant("fixed_income.curve_fitting", "long_end_tends_to_beta0")
@given(params=parameters())
def test_the_long_end_tends_to_beta0(params: dict[str, float]) -> None:
    n = 100.0
    out = run(calculation="evaluate", maturities=[n], **params)
    # |L(x)| <= 1/x and |L(x) - e^-x| <= 2/x bound the zero yield's distance;
    # x e^-x for x >= 20 (decays of at most five years) bounds the forward's.
    bound = (abs(params["beta1"]) + 2 * abs(params["beta2"])) * params["tau1"] / n
    bound += 2 * abs(params["beta3"]) * params["tau2"] / n
    assert abs(out.zero_yields[0] - params["beta0"]) <= bound + 1e-15
    x1, x2 = n / params["tau1"], n / params["tau2"]
    reach = (
        abs(params["beta1"]) * math.exp(-x1)
        + abs(params["beta2"]) * x1 * math.exp(-x1)
        + abs(params["beta3"]) * x2 * math.exp(-x2)
    )
    assert abs(out.forward_rates[0] - params["beta0"]) <= reach + 1e-15


@pytest.mark.invariant(
    "fixed_income.curve_fitting", "short_end_tends_to_beta0_plus_beta1"
)
@given(params=parameters())
def test_the_short_end_tends_to_beta0_plus_beta1(params: dict[str, float]) -> None:
    n = 1e-6
    out = run(calculation="evaluate", maturities=[n], **params)
    short = params["beta0"] + params["beta1"]
    # Each loading moves from its limit by at most its argument, n / tau.
    slack = sum(abs(params[k]) for k in ("beta1", "beta2")) * n / params["tau1"]
    slack += abs(params["beta3"]) * n / params["tau2"]
    assert abs(out.zero_yields[0] - short) <= slack + 1e-15
    assert abs(out.forward_rates[0] - short) <= 2 * slack + 1e-15


@pytest.mark.invariant(
    "fixed_income.curve_fitting", "svensson_with_zero_beta3_is_nelson_siegel"
)
@given(params=parameters(svensson=False), tau2=st.floats(min_value=0.1, max_value=50))
def test_a_zero_beta3_gives_nelson_siegel(
    params: dict[str, float], tau2: float
) -> None:
    nelson_siegel = run(calculation="evaluate", maturities=MATURITIES, **params)
    svensson = run(
        calculation="evaluate", maturities=MATURITIES, beta3=0.0, tau2=tau2, **params
    )
    assert svensson.zero_yields == nelson_siegel.zero_yields
    assert svensson.forward_rates == nelson_siegel.forward_rates
    assert svensson.par_yields == nelson_siegel.par_yields


@pytest.mark.invariant("fixed_income.curve_fitting", "fit_recovers_noise_free_curve")
@settings(deadline=None)
@given(
    data=st.data(),
    form=st.sampled_from(["nelson_siegel", "svensson"]),
    yield_type=st.sampled_from(["zero", "par"]),
)
def test_a_fit_recovers_a_noise_free_curve(
    data: st.DataObject, form: str, yield_type: str
) -> None:
    params = data.draw(identifiable(svensson=form == "svensson"))
    curve = run(calculation="evaluate", maturities=MATURITIES, **params)
    observed = curve.zero_yields if yield_type == "zero" else curve.par_yields
    fit = run(
        calculation="fit",
        maturities=MATURITIES,
        yields=observed,
        yield_type=yield_type,
        form=form,
    )
    # Compared on yields: the parameters need not be unique.
    for fitted, given_yield in zip(fit.fitted_yields, observed, strict=True):
        assert abs(fitted - given_yield) <= 1e-7
    assert fit.rmse <= 1e-7


# --- oracles -------------------------------------------------------------------


@pytest.mark.oracle("fixed_income.curve_fitting")
@given(
    params=parameters(),
    frequency=st.sampled_from(list(PERIODS)),
    maturities=st.lists(
        st.floats(min_value=0.05, max_value=40.0), min_size=1, max_size=8, unique=True
    ),
)
def test_evaluation_agrees_with_the_textbook_formulas(
    params: dict[str, float], frequency: str, maturities: list[float]
) -> None:
    out = run(
        calculation="evaluate",
        maturities=maturities,
        coupon_frequency=frequency,
        **params,
    )
    for k, n in enumerate(maturities):
        zero, forward = _textbook(params, n)
        assert math.isclose(out.zero_yields[k], zero, rel_tol=1e-12, abs_tol=1e-14)
        assert math.isclose(out.forward_rates[k], forward, rel_tol=1e-12, abs_tol=1e-14)
        par = _textbook_par(params, n, PERIODS[frequency])
        assert math.isclose(out.par_yields[k], par, rel_tol=1e-10, abs_tol=1e-13)
        assert math.isclose(out.discount_factors[k], math.exp(-zero * n), rel_tol=1e-12)


def _quantlib_svensson(params: dict[str, float]) -> Any:  # noqa: ANN401 - a QuantLib curve
    today = ql.Date(15, 6, 2026)
    vector = ql.Array(
        [
            params["beta0"],
            params["beta1"],
            params["beta2"],
            params["beta3"],
            1 / params["tau1"],
            1 / params["tau2"],
        ]
    )
    return ql.FittedBondDiscountCurve(
        today,
        ql.SvenssonFitting(),
        vector,
        today + ql.Period(60, ql.Years),
        ql.Actual365Fixed(),
    )


@pytest.mark.oracle("fixed_income.curve_fitting")
@given(params=parameters())
def test_evaluation_agrees_with_quantlib_svensson(params: dict[str, float]) -> None:
    curve = _quantlib_svensson(params)
    out = run(calculation="evaluate", maturities=MATURITIES, **params)
    for n, factor in zip(MATURITIES, out.discount_factors, strict=True):
        # QuantLib adds machine epsilon to the decay and the time it divides by.
        assert math.isclose(curve.discount(n), factor, rel_tol=1e-12)


def _quantlib_fit(
    maturities: tuple[float, ...], yields: list[float]
) -> tuple[list[float], list[float]]:
    """Fit QuantLib's Svensson curve to zero-coupon bonds; return its zero yields."""
    today = ql.Date(15, 6, 2026)
    ql.Settings.instance().evaluationDate = today
    counter = ql.Actual365Fixed()
    helpers, times = [], []
    for n, y in zip(maturities, yields, strict=True):
        maturity = today + round(n * 365)
        t = counter.yearFraction(today, maturity)
        bond = ql.ZeroCouponBond(
            0, ql.NullCalendar(), 100.0, maturity, ql.Unadjusted, 100.0, today
        )
        quote = ql.QuoteHandle(ql.SimpleQuote(100.0 * math.exp(-y * t)))
        helpers.append(ql.BondHelper(quote, bond))
        times.append(t)
    curve = ql.FittedBondDiscountCurve(
        today, helpers, counter, ql.SvenssonFitting(), 1e-12, 50_000
    )
    return [-math.log(curve.discount(t)) / t for t in times], times


@pytest.mark.oracle("fixed_income.curve_fitting")
@pytest.mark.parametrize(
    "shift",
    [
        (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0),
        (2e-4, -1e-4, 3e-4, 0.0, -2e-4, 1e-4, 0.0, -1e-4, 2e-4, -3e-4),
    ],
    ids=["noise_free", "noisy"],
)
def test_the_fit_matches_or_beats_quantlib_on_yields(
    shift: tuple[float, ...],
) -> None:
    truth = {
        "beta0": 0.045,
        "beta1": -0.012,
        "beta2": -0.02,
        "beta3": 0.015,
        "tau1": 1.5,
        "tau2": 9.0,
    }
    zero = run(calculation="evaluate", maturities=MATURITIES, **truth).zero_yields
    observed = [y + s for y, s in zip(zero, shift, strict=True)]
    quantlib, times = _quantlib_fit(MATURITIES, observed)
    ours = run(
        calculation="fit",
        maturities=times,
        yields=observed,
        yield_type="zero",
        form="svensson",
    )
    theirs = math.sqrt(
        math.fsum((q - o) ** 2 for q, o in zip(quantlib, observed, strict=True))
        / len(observed)
    )
    assert ours.rmse <= theirs + 1e-10


# --- details and refusals ------------------------------------------------------


def test_the_board_publishes_the_par_yield_the_model_computes() -> None:
    # Integer maturities: semiannual coupons i/2, no stub (GSW's equation 7).
    params = {"beta0": 0.05, "beta1": -0.02, "beta2": 0.01, "beta3": 0.0, "tau1": 2.0}
    out = run(calculation="evaluate", maturities=[10.0], **params)
    factors = [math.exp(-_textbook(params, i / 2)[0] * i / 2) for i in range(1, 21)]
    assert math.isclose(
        out.par_yields[0], 2 * (1 - factors[-1]) / sum(factors), rel_tol=1e-12
    )


def test_a_broken_maturity_has_a_short_first_period() -> None:
    # Written out by hand, independently of any schedule code: 1.25 years of
    # semiannual coupons pay at 0.25 (a quarter-year stub), 0.75 and 1.25.
    y = 0.05
    out = run(
        calculation="evaluate",
        maturities=[1.25],
        beta0=y,
        beta1=0.0,
        beta2=0.0,
        tau1=1.0,
    )
    d = [math.exp(-y * t) for t in (0.25, 0.75, 1.25)]
    expected = (1 - d[2]) / (0.25 * d[0] + 0.5 * d[1] + 0.5 * d[2])
    assert math.isclose(out.par_yields[0], expected, rel_tol=1e-14)


def test_a_short_maturity_has_one_stub_period() -> None:
    out = run(
        calculation="evaluate",
        maturities=[0.25],
        beta0=0.04,
        beta1=0.0,
        beta2=0.0,
        tau1=1.0,
    )
    # A flat 4% continuous curve: the simple rate over a quarter.
    assert math.isclose(out.par_yields[0], (math.exp(0.01) - 1) / 0.25, rel_tol=1e-12)


def test_a_nelson_siegel_fit_repeats_tau1_and_zeroes_beta3() -> None:
    curve = run(
        calculation="evaluate",
        maturities=MATURITIES,
        beta0=0.05,
        beta1=-0.01,
        beta2=0.02,
        tau1=1.2,
    )
    fit = run(
        calculation="fit",
        maturities=MATURITIES,
        yields=curve.zero_yields,
        yield_type="zero",
        form="nelson_siegel",
    )
    assert fit.beta3 == 0.0
    assert fit.tau2 == fit.tau1
    again = run(
        calculation="evaluate",
        maturities=MATURITIES,
        **{
            k: getattr(fit, k)
            for k in ("beta0", "beta1", "beta2", "beta3", "tau1", "tau2")
        },
    )
    assert np.allclose(again.zero_yields, curve.zero_yields, atol=1e-9)


def test_a_fit_that_runs_out_of_evaluations_warns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(module, "_EVALUATIONS_PER_START", 2)
    result = run_model(
        curve_fitting,
        {
            "calculation": "fit",
            "maturities": MATURITIES,
            "yields": [
                0.04,
                0.041,
                0.042,
                0.043,
                0.044,
                0.046,
                0.047,
                0.048,
                0.05,
                0.051,
            ],
            "form": "svensson",
        },
    )
    assert [w.code for w in result.warnings] == ["fit_not_converged"]


@pytest.mark.parametrize(
    "inputs",
    [
        {
            "calculation": "evaluate",
            "beta0": 0.04,
            "beta1": 0.0,
            "beta2": 0.0,
            "beta3": 0.01,
            "tau1": 1.0,
        },
        {
            "calculation": "fit",
            "maturities": [1, 2, 3, 4],
            "yields": [0.01, 0.02, 0.03],
        },
        {
            "calculation": "fit",
            "maturities": [1, 3, 2, 4],
            "yields": [0.01, 0.02, 0.03, 0.04],
        },
        {
            "calculation": "fit",
            "maturities": [1, 2, 3, 4, 5],
            "yields": [0.01, 0.02, 0.03, 0.04, 0.05],
            "form": "svensson",
        },
    ],
    ids=[
        "beta3_without_tau2",
        "lengths_differ",
        "not_increasing",
        "too_few_for_svensson",
    ],
)
def test_inconsistent_inputs_are_refused(inputs: dict[str, Any]) -> None:
    with pytest.raises(InputError):
        run_model(curve_fitting, inputs)


def test_a_curve_that_discounts_past_the_smallest_float_is_refused() -> None:
    # A 10% yield for 100 years discounts by e^-1000: no float holds it.
    with pytest.raises(DomainError, match="smallest representable factor"):
        run(
            calculation="evaluate",
            maturities=[0.5, 1.0, 100.0],
            beta0=10.0,
            beta1=-10.0,
            beta2=0.0,
            tau1=1.0,
            coupon_frequency="monthly",
        )


def test_a_curve_beyond_the_rate_bounds_is_refused() -> None:
    with pytest.raises(DomainError, match="outside"):
        run(
            calculation="evaluate",
            maturities=[100.0],
            beta0=-0.99,
            beta1=-0.99,
            beta2=-0.99,
            tau1=100.0,
        )
