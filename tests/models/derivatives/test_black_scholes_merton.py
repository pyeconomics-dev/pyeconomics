# tests/models/derivatives/test_black_scholes_merton.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``derivatives.black_scholes_merton``: invariants, QuantLib and vollib oracles.

QuantLib's ``AnalyticEuropeanEngine`` prices the same option on flat curves and
a flat volatility, on an ACT/365 (Fixed) clock, so the time is a whole number
of days over 365; it checks the price and every Greek. vollib's
``implied_volatility`` (Jaeckel's "Let's Be Rational") checks the solver.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from vollib.black_scholes_merton.implied_volatility import (  # type: ignore[import-untyped]
    implied_volatility as vollib_implied_volatility,
)

from pyeconomics.core import InputError, run_model
from pyeconomics.models.derivatives import black_scholes_merton

SPOTS = st.floats(min_value=0.01, max_value=1e7)
YEARS = st.floats(min_value=0.001, max_value=100.0)
RATES = st.floats(min_value=-0.1, max_value=1.0)
VOLS = st.floats(min_value=0.001, max_value=5.0)
KINDS = st.sampled_from(["call", "put"])
#: Moderate inputs, where prices are far from underflow.
MODERATE = {
    "spot": st.floats(min_value=1.0, max_value=1000.0),
    "moneyness": st.floats(min_value=0.5, max_value=2.0),
    "years": st.floats(min_value=0.02, max_value=10.0),
    "rate": st.floats(min_value=-0.05, max_value=0.2),
    "dividend": st.floats(min_value=-0.05, max_value=0.2),
}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(black_scholes_merton, inputs).outputs


def price(**inputs: Any) -> Any:  # noqa: ANN401 - the price outputs
    return run(calculation="price", **inputs)


def bounds(  # noqa: PLR0913, PLR0917 - the option's inputs
    kind: str, spot: float, strike: float, years: float, rate: float, dividend: float
) -> tuple[float, float]:
    asset, cash = spot * math.exp(-dividend * years), strike * math.exp(-rate * years)
    if kind == "call":
        return max(asset - cash, 0.0), asset
    return max(cash - asset, 0.0), cash


@pytest.mark.invariant("derivatives.black_scholes_merton", "put_call_parity")
@given(spot=SPOTS, strike=SPOTS, years=YEARS, rate=RATES, dividend=RATES, vol=VOLS)
def test_a_call_less_a_put_is_the_forward_gap(  # noqa: PLR0913 - the option's inputs
    *,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend: float,
    vol: float,
) -> None:
    terms = {
        "spot": spot,
        "strike": strike,
        "years": years,
        "risk_free_rate": rate,
        "dividend_yield": dividend,
        "volatility": vol,
    }
    call = price(option_type="call", **terms)
    put = price(option_type="put", **terms)
    asset, cash = spot * math.exp(-dividend * years), strike * math.exp(-rate * years)
    scale = max(asset, cash)
    assert math.isclose(call.price - put.price, asset - cash, abs_tol=1e-12 * scale)
    assert abs(call.put_call_parity_residual) <= 1e-12 * scale
    assert call.put_call_parity_residual == put.put_call_parity_residual


@pytest.mark.invariant(
    "derivatives.black_scholes_merton", "price_within_no_arbitrage_bounds"
)
@given(
    kind=KINDS,
    spot=SPOTS,
    strike=SPOTS,
    years=YEARS,
    rate=RATES,
    dividend=RATES,
    vol=VOLS,
)
def test_the_price_is_within_the_no_arbitrage_bounds(  # noqa: PLR0913
    *,
    kind: str,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend: float,
    vol: float,
) -> None:
    result = price(
        option_type=kind,
        spot=spot,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        dividend_yield=dividend,
        volatility=vol,
    )
    low, high = bounds(kind, spot, strike, years, rate, dividend)
    slack = 1e-12 * max(high, spot, strike)
    assert low - slack <= result.price <= high + slack


@pytest.mark.invariant("derivatives.black_scholes_merton", "gamma_and_vega_nonnegative")
@given(
    kind=KINDS,
    spot=SPOTS,
    strike=SPOTS,
    years=YEARS,
    rate=RATES,
    dividend=RATES,
    vol=VOLS,
)
def test_gamma_and_vega_are_never_negative(  # noqa: PLR0913
    *,
    kind: str,
    spot: float,
    strike: float,
    years: float,
    rate: float,
    dividend: float,
    vol: float,
) -> None:
    result = price(
        option_type=kind,
        spot=spot,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        dividend_yield=dividend,
        volatility=vol,
    )
    assert result.gamma >= 0.0
    assert result.vega >= 0.0


@pytest.mark.invariant("derivatives.black_scholes_merton", "call_increases_with_spot")
@given(
    low=SPOTS,
    high=SPOTS,
    strike=SPOTS,
    years=YEARS,
    rate=RATES,
    dividend=RATES,
    vol=VOLS,
)
def test_a_call_does_not_fall_as_the_spot_rises(  # noqa: PLR0913
    *,
    low: float,
    high: float,
    strike: float,
    years: float,
    rate: float,
    dividend: float,
    vol: float,
) -> None:
    low, high = sorted((low, high))
    terms = {
        "option_type": "call",
        "strike": strike,
        "years": years,
        "risk_free_rate": rate,
        "dividend_yield": dividend,
        "volatility": vol,
    }
    below = price(spot=low, **terms).price
    above = price(spot=high, **terms).price
    assert above >= below - 1e-12 * max(above, strike)


@pytest.mark.invariant(
    "derivatives.black_scholes_merton", "implied_volatility_round_trip"
)
@settings(deadline=None)  # the first solve imports SciPy
@given(kind=KINDS, vol=VOLS, **MODERATE)
def test_the_implied_volatility_of_a_price_is_its_volatility(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    spot: float,
    moneyness: float,
    years: float,
    rate: float,
    dividend: float,
) -> None:
    terms = {
        "option_type": kind,
        "spot": spot,
        "strike": spot * moneyness,
        "years": years,
        "risk_free_rate": rate,
        "dividend_yield": dividend,
    }
    priced = price(volatility=vol, **terms)
    low, high = bounds(kind, spot, spot * moneyness, years, rate, dividend)
    # Where the price barely moves with volatility, or sits on a bound in
    # floating point, no solver can recover the volatility.
    assume(priced.vega > 1e-6 * spot)
    assume(low + 1e-9 * spot < priced.price < high - 1e-9 * spot)
    solved = run(calculation="implied_volatility", option_price=priced.price, **terms)
    assert solved.implied_volatility is not None
    tolerance = 1e-10 * spot / priced.vega + 1e-11
    assert math.isclose(solved.implied_volatility, vol, rel_tol=0, abs_tol=tolerance)


def test_a_price_outside_the_bounds_has_no_implied_volatility() -> None:
    result = run_model(
        black_scholes_merton,
        {
            "calculation": "implied_volatility",
            "option_type": "put",
            "option_price": 0.0,
            "spot": 100,
            "strike": 100,
            "years": 1,
            "risk_free_rate": 0.05,
        },
    )
    assert result.outputs.implied_volatility is None
    assert [w.code for w in result.warnings] == ["price_outside_no_arbitrage_bounds"]


@pytest.mark.parametrize(
    ("option_price", "strike", "side"),
    [
        # Within a cent of the upper bound of 100: a volatility far above 5.
        (99.99, 100.0, "above"),
        # A tenth of a cent for an at-the-money-forward call: about 2.5e-5.
        (0.001, 100 * math.exp(0.05), "below"),
    ],
)
def test_a_volatility_outside_the_range_is_none(
    option_price: float, strike: float, side: str
) -> None:
    result = run_model(
        black_scholes_merton,
        {
            "calculation": "implied_volatility",
            "option_price": option_price,
            "spot": 100,
            "strike": strike,
            "years": 1,
            "risk_free_rate": 0.05,
        },
    )
    assert result.outputs.implied_volatility is None
    assert [w.code for w in result.warnings] == ["implied_volatility_out_of_range"]
    assert side in result.warnings[0].message


def test_a_volatility_above_the_range_is_refused() -> None:
    with pytest.raises(InputError, match="volatility"):
        price(spot=100, strike=100, years=1, risk_free_rate=0.05, volatility=5.5)


# --- QuantLib and vollib as oracles ----------------------------------------------

TODAY = ql.Date(15, 1, 2026)


def quantlib_option(  # noqa: PLR0913, PLR0917 - the option's inputs
    kind: str,
    spot: float,
    strike: float,
    days: int,
    rate: float,
    dividend: float,
    vol: float,
) -> Any:  # noqa: ANN401 - a QuantLib VanillaOption
    ql.Settings.instance().evaluationDate = TODAY
    day_count = ql.Actual365Fixed()
    process = ql.BlackScholesMertonProcess(
        ql.QuoteHandle(ql.SimpleQuote(spot)),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, dividend, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, rate, day_count)),
        ql.BlackVolTermStructureHandle(
            ql.BlackConstantVol(TODAY, ql.NullCalendar(), vol, day_count)
        ),
    )
    option = ql.VanillaOption(
        ql.PlainVanillaPayoff(
            ql.Option.Call if kind == "call" else ql.Option.Put, strike
        ),
        ql.EuropeanExercise(TODAY + days),
    )
    option.setPricingEngine(ql.AnalyticEuropeanEngine(process))
    return option


@pytest.mark.oracle("derivatives.black_scholes_merton")
@settings(deadline=None)
@given(
    kind=KINDS,
    days=st.integers(min_value=1, max_value=3650),
    vol=st.floats(min_value=0.01, max_value=2.0),
    **MODERATE,
)
def test_prices_and_greeks_agree_with_quantlib(  # noqa: PLR0913
    *,
    kind: str,
    days: int,
    vol: float,
    spot: float,
    moneyness: float,
    years: float,
    rate: float,
    dividend: float,
) -> None:
    del years  # QuantLib's clock counts whole days
    strike = spot * moneyness
    option = quantlib_option(kind, spot, strike, days, rate, dividend, vol)
    ours = price(
        option_type=kind,
        spot=spot,
        strike=strike,
        years=days / 365,
        risk_free_rate=rate,
        dividend_yield=dividend,
        volatility=vol,
    )
    scale = spot + strike
    pairs = {
        "price": (ours.price, option.NPV()),
        "delta": (ours.delta, option.delta()),
        "gamma": (ours.gamma, option.gamma()),
        "vega": (ours.vega, option.vega()),
        "theta": (ours.theta, option.theta()),
        "rho": (ours.rho, option.rho()),
        "dividend_rho": (ours.dividend_rho, option.dividendRho()),
    }
    for name, (mine, theirs) in pairs.items():
        assert math.isclose(mine, theirs, rel_tol=1e-9, abs_tol=1e-11 * scale), name


@pytest.mark.oracle("derivatives.black_scholes_merton")
@settings(deadline=None)
@given(kind=KINDS, vol=st.floats(min_value=0.02, max_value=2.0), **MODERATE)
def test_implied_volatility_agrees_with_vollib(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    spot: float,
    moneyness: float,
    years: float,
    rate: float,
    dividend: float,
) -> None:
    strike = spot * moneyness
    terms = {
        "option_type": kind,
        "spot": spot,
        "strike": strike,
        "years": years,
        "risk_free_rate": rate,
        "dividend_yield": dividend,
    }
    priced = price(volatility=vol, **terms)
    low, high = bounds(kind, spot, strike, years, rate, dividend)
    assume(priced.vega > 1e-4 * spot)
    assume(low + 1e-7 * spot < priced.price < high - 1e-7 * spot)
    ours = run(calculation="implied_volatility", option_price=priced.price, **terms)
    theirs = vollib_implied_volatility(
        priced.price, spot, strike, years, rate, dividend, kind[0]
    )
    assert ours.implied_volatility is not None
    assert math.isclose(ours.implied_volatility, theirs, rel_tol=0, abs_tol=1e-7)


@pytest.mark.parametrize(("end", "offset"), [(5.0, 1e-12), (0.001, -1e-12)])
def test_a_price_within_rounding_of_an_end_gives_that_end(
    end: float, offset: float
) -> None:
    terms = {
        "option_type": "call",
        "spot": 100.0,
        "strike": 100.0,
        "years": 0.01,
        "risk_free_rate": 0.0,
    }
    at_end = price(volatility=end, **terms).price
    solved = run(
        calculation="implied_volatility", option_price=at_end + offset, **terms
    )
    assert solved.implied_volatility == end
