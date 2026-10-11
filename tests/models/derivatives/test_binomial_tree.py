# tests/models/derivatives/test_binomial_tree.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``derivatives.binomial_tree``: invariants, QuantLib's CRR engine as an oracle.

QuantLib's ``BinomialCRRVanillaEngine`` builds the same lattice (``u = e^(sigma
sqrt(dt))``, ``d = 1/u``, discounting at ``r`` each step) but takes the
up-probability to first order, ``1/2 + (r - q - sigma^2/2) dt / (2 sigma
sqrt(dt))``, where Cox, Ross and Rubinstein's is exact, ``(e^((r - q) dt) - d) /
(u - d)``. QuantLib reads ``q`` nowhere else, so the oracle gives it the yield
that makes its probability the exact one; the trees are then the same, node for
node, and the price, early exercise, delta and gamma must agree. A second test
bounds the gap to QuantLib's own probability, which shrinks as ``1/n``.

QuantLib 1.43's binomial engine prices some American options below its own
European on the same tree (a put at a zero rate at 0.1173 against 0.1226 on
23 steps), which no exercise policy allows, so the exact comparison covers
European options. American options are compared, converged, with QuantLib's
finite-difference engine (``FdBlackScholesVanillaEngine``): 2,000 tree steps
against an 800 by 800 grid agree to 1e-3 of the spot plus the strike.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import given, reject, settings
from hypothesis import strategies as st

from pyeconomics.core import DomainError, run_model
from pyeconomics.models.derivatives import binomial_tree, black_scholes_merton

KINDS = st.sampled_from(["call", "put"])
MODERATE = {
    "spot": st.floats(min_value=1.0, max_value=1000.0),
    "moneyness": st.floats(min_value=0.5, max_value=2.0),
    "years": st.floats(min_value=0.05, max_value=10.0),
    "rate": st.floats(min_value=-0.05, max_value=0.2),
    "dividend": st.floats(min_value=-0.05, max_value=0.2),
    "vol": st.floats(min_value=0.1, max_value=1.5),
}
STEPS = st.integers(min_value=2, max_value=200)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the tree's outputs
    return run_model(binomial_tree, inputs).outputs


def tree(**inputs: Any) -> Any:  # noqa: ANN401 - the tree's outputs
    """Run the tree, discarding a draw whose drift outruns its volatility."""
    try:
        return run(**inputs)
    except DomainError:
        reject()  # the up-probability is outside (0, 1); tested below


def terms(  # noqa: PLR0913, PLR0917 - the option's inputs
    spot: float,
    moneyness: float,
    years: float,
    rate: float,
    dividend: float,
    vol: float,
) -> dict[str, float]:
    return {
        "spot": spot,
        "strike": spot * moneyness,
        "years": years,
        "risk_free_rate": rate,
        "dividend_yield": dividend,
        "volatility": vol,
    }


@pytest.mark.invariant("derivatives.binomial_tree", "american_put_at_least_european")
@settings(deadline=None)
@given(steps=STEPS, **MODERATE)
def test_an_american_put_is_worth_at_least_the_european(
    steps: int, **option: float
) -> None:
    common = {"option_type": "put", "steps": steps, **terms(**option)}
    american = tree(exercise="american", **common).price
    european = tree(exercise="european", **common).price
    assert american >= european - 1e-12 * option["spot"]


@pytest.mark.invariant(
    "derivatives.binomial_tree", "american_call_equals_european_without_dividends"
)
@settings(deadline=None)
@given(
    steps=STEPS,
    rate=st.floats(min_value=0.0, max_value=0.2),
    **{k: v for k, v in MODERATE.items() if k not in {"rate", "dividend"}},
)
def test_an_american_call_without_dividends_is_european(
    steps: int, rate: float, **option: float
) -> None:
    common = {
        "option_type": "call",
        "steps": steps,
        **terms(rate=rate, dividend=0.0, **option),
    }
    american = tree(exercise="american", **common).price
    european = tree(exercise="european", **common).price
    assert math.isclose(american, european, rel_tol=1e-12, abs_tol=1e-12)


@pytest.mark.invariant("derivatives.binomial_tree", "european_parity_holds")
@settings(deadline=None)
@given(steps=STEPS, **MODERATE)
def test_european_parity_holds_on_the_tree(steps: int, **option: float) -> None:
    common = {"exercise": "european", "steps": steps, **terms(**option)}
    call = tree(option_type="call", **common).price
    put = tree(option_type="put", **common).price
    asset = option["spot"] * math.exp(-option["dividend"] * option["years"])
    strike = option["spot"] * option["moneyness"]
    cash = strike * math.exp(-option["rate"] * option["years"])
    assert math.isclose(call - put, asset - cash, abs_tol=1e-10 * max(asset, cash))


@pytest.mark.invariant("derivatives.binomial_tree", "converges_to_black_scholes")
@settings(deadline=None, max_examples=30)
@given(kind=KINDS, **MODERATE)
def test_a_european_price_converges_to_black_scholes(
    kind: str, **option: float
) -> None:
    common = {"option_type": kind, **terms(**option)}
    exact: float = run_model(
        black_scholes_merton, {"calculation": "price", **common}
    ).outputs.price

    def error(steps: int) -> float:
        priced: float = tree(exercise="european", steps=steps, **common).price
        return abs(priced - exact)

    coarse = max(error(10), error(11))
    fine = error(1000)
    # The error falls roughly as 1/n, with an oscillation that never makes up a
    # hundredfold increase in steps.
    assert fine <= coarse / 5 or fine <= 1e-9 * option["spot"]


def test_the_five_step_american_put_matches_the_textbook_tree() -> None:
    result = run(
        option_type="put",
        spot=50,
        strike=50,
        years=5 / 12,
        risk_free_rate=0.10,
        volatility=0.40,
        steps=5,
    )
    assert math.isclose(result.up_factor, 1.1224, abs_tol=5e-5)
    assert math.isclose(result.up_probability, 0.5073, abs_tol=5e-5)


def test_two_steps_read_delta_and_gamma_from_expiry() -> None:
    result = run(
        option_type="call",
        exercise="european",
        spot=100,
        strike=95,
        years=1,
        risk_free_rate=0.05,
        volatility=0.3,
        steps=2,
    )
    u = math.exp(0.3 * math.sqrt(0.5))
    up, middle, down = 100 * u * u - 95, 100 - 95, 0.0
    delta_up = (up - middle) / (100 * u * u - 100)
    delta_down = (middle - down) / (100 - 100 / u / u)
    gamma = (delta_up - delta_down) / (0.5 * (100 * u * u - 100 / u / u))
    assert math.isclose(result.gamma, gamma, rel_tol=1e-12)


def test_a_drift_that_outruns_the_volatility_is_refused() -> None:
    with pytest.raises(DomainError, match="up-probability"):
        run(
            spot=100,
            strike=100,
            years=100,
            risk_free_rate=1.0,
            volatility=0.01,
            steps=2,
        )


def test_a_tree_whose_top_node_overflows_is_refused() -> None:
    with pytest.raises(DomainError, match="overflows"):
        run(
            spot=1e7,
            strike=100,
            years=100,
            risk_free_rate=0.0,
            volatility=5.0,
            steps=5000,
        )


# --- QuantLib as an oracle -------------------------------------------------------

TODAY = ql.Date(15, 1, 2026)


def quantlib_tree(  # noqa: PLR0913 - the option's inputs and the tree's
    kind: str,
    exercise: str,
    days: int,
    steps: int,
    option: dict[str, float],
    *,
    exact: bool,
) -> Any:  # noqa: ANN401 - a QuantLib VanillaOption
    ql.Settings.instance().evaluationDate = TODAY
    day_count = ql.Actual365Fixed()
    years = days / 365
    rate, vol = option["risk_free_rate"], option["volatility"]
    dividend = option["dividend_yield"]
    if exact:
        dt = years / steps
        jump = vol * math.sqrt(dt)
        p = (math.expm1((rate - dividend) * dt) - math.expm1(-jump)) / (
            math.expm1(jump) - math.expm1(-jump)
        )
        # QuantLib's p = 1/2 + (r - q' - sigma^2/2) dt / (2 jump): solve for q'.
        dividend = rate - vol * vol / 2 - (2 * p - 1) * jump / dt
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(option["spot"])),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, dividend, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, rate, day_count)),
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(TODAY, ql.NullCalendar(), vol, day_count)
        ),
    )
    expiry = TODAY + days
    instrument = ql.VanillaOption(
        ql.PlainVanillaPayoff(
            ql.Option.Call if kind == "call" else ql.Option.Put, option["strike"]
        ),
        ql.AmericanExercise(TODAY, expiry)
        if exercise == "american"
        else ql.EuropeanExercise(expiry),
    )
    instrument.setPricingEngine(ql.BinomialCRRVanillaEngine(process, steps))
    return instrument


@pytest.mark.oracle("derivatives.binomial_tree")
@settings(deadline=None)
@given(
    kind=KINDS,
    days=st.integers(min_value=20, max_value=3650),
    steps=st.integers(min_value=3, max_value=300),
    **{k: v for k, v in MODERATE.items() if k != "years"},
)
def test_a_european_tree_agrees_with_quantlibs_crr_engine(
    kind: str,
    days: int,
    steps: int,
    **option: float,
) -> None:
    common = terms(years=days / 365, **option)
    ours = tree(option_type=kind, exercise="european", steps=steps, **common)
    theirs = quantlib_tree(kind, "european", days, steps, common, exact=True)
    scale = common["spot"] + common["strike"]
    assert math.isclose(ours.price, theirs.NPV(), rel_tol=1e-9, abs_tol=1e-11 * scale)
    assert math.isclose(ours.delta, theirs.delta(), rel_tol=1e-8, abs_tol=1e-10)
    assert math.isclose(
        ours.gamma, theirs.gamma(), rel_tol=1e-7, abs_tol=1e-9 / common["spot"]
    )


@pytest.mark.oracle("derivatives.binomial_tree")
@settings(deadline=None, max_examples=30)
@given(
    kind=KINDS,
    days=st.integers(min_value=20, max_value=3650),
    **{k: v for k, v in MODERATE.items() if k != "years"},
)
def test_an_american_tree_agrees_with_quantlibs_finite_differences(
    kind: str, days: int, **option: float
) -> None:
    common = terms(years=days / 365, **option)
    ours = tree(option_type=kind, exercise="american", steps=2000, **common)
    ql.Settings.instance().evaluationDate = TODAY
    day_count = ql.Actual365Fixed()
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(common["spot"])),
        ql.YieldTermStructureHandle(
            ql.FlatForward(TODAY, common["dividend_yield"], day_count)
        ),
        ql.YieldTermStructureHandle(
            ql.FlatForward(TODAY, common["risk_free_rate"], day_count)
        ),
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(
                TODAY, ql.NullCalendar(), common["volatility"], day_count
            )
        ),
    )
    theirs = ql.VanillaOption(
        ql.PlainVanillaPayoff(
            ql.Option.Call if kind == "call" else ql.Option.Put, common["strike"]
        ),
        ql.AmericanExercise(TODAY, TODAY + days),
    )
    theirs.setPricingEngine(ql.FdBlackScholesVanillaEngine(process, 800, 800))
    scale = common["spot"] + common["strike"]
    assert math.isclose(ours.price, theirs.NPV(), rel_tol=0, abs_tol=1e-3 * scale)


def test_quantlibs_first_order_probability_differs_by_order_one_over_n() -> None:
    option = terms(
        spot=50, moneyness=1.0, years=152 / 365, rate=0.1, dividend=0.0, vol=0.4
    )
    gaps = []
    for steps in (50, 500):
        theirs = quantlib_tree("put", "european", 152, steps, option, exact=False)
        ours = run(option_type="put", exercise="european", steps=steps, **option)
        gaps.append(abs(ours.price - theirs.NPV()))
    assert gaps[1] < gaps[0] / 5
    assert gaps[1] < 1e-4
