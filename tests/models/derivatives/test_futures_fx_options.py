# tests/models/derivatives/test_futures_fx_options.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``derivatives.futures_fx_options``: cross-entry invariants, QuantLib and vollib.

Black-76 is checked against QuantLib's ``blackFormula`` and vollib's Black
implied volatility; Garman-Kohlhagen against QuantLib's
``GarmanKohlagenProcess`` under ``AnalyticEuropeanEngine``. The cross-entry
tests hold both to ``derivatives.black_scholes_merton``.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
import QuantLib as ql  # type: ignore[import-untyped]  # noqa: N813 - oracle docs use ql
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from vollib.black.implied_volatility import (  # type: ignore[import-untyped]
    implied_volatility as vollib_black_implied_volatility,
)

from pyeconomics.core import run_model
from pyeconomics.models.derivatives import black_scholes_merton, futures_fx_options

KINDS = st.sampled_from(["call", "put"])
PRICES = st.floats(min_value=0.01, max_value=1e6)
YEARS = st.floats(min_value=0.001, max_value=100.0)
RATES = st.floats(min_value=-0.1, max_value=1.0)
VOLS = st.floats(min_value=0.001, max_value=5.0)
MODERATE = {
    "underlying": st.floats(min_value=0.5, max_value=500.0),
    "moneyness": st.floats(min_value=0.5, max_value=2.0),
    "years": st.floats(min_value=0.02, max_value=10.0),
    "rate": st.floats(min_value=-0.05, max_value=0.2),
}


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(futures_fx_options, inputs).outputs


def bsm(**inputs: Any) -> Any:  # noqa: ANN401 - the price outputs
    return run_model(black_scholes_merton, {"calculation": "price", **inputs}).outputs


def close(mine: float, theirs: float, scale: float) -> bool:
    return math.isclose(mine, theirs, rel_tol=1e-12, abs_tol=1e-13 * scale)


@pytest.mark.invariant(
    "derivatives.futures_fx_options", "black_76_equals_bsm_with_carry_zero"
)
@given(kind=KINDS, forward=PRICES, strike=PRICES, years=YEARS, rate=RATES, vol=VOLS)
def test_black_76_is_bsm_with_no_cost_of_carry(  # noqa: PLR0913
    *, kind: str, forward: float, strike: float, years: float, rate: float, vol: float
) -> None:
    ours = run(
        calculation="black_76",
        option_type=kind,
        futures_price=forward,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        volatility=vol,
    )
    theirs = bsm(
        option_type=kind,
        spot=forward,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        dividend_yield=rate,
        volatility=vol,
    )
    scale = (forward + strike) * math.exp(-rate * years)
    for name in ("price", "delta", "gamma", "vega", "theta"):
        assert getattr(ours, name) == getattr(theirs, name), name
    # Both rates move together: rho is the sum of BSM's two rate sensitivities.
    assert close(ours.rho, theirs.rho + theirs.dividend_rho, scale * years)


@pytest.mark.invariant(
    "derivatives.futures_fx_options", "garman_kohlhagen_equals_bsm_with_foreign_yield"
)
@given(
    kind=KINDS,
    spot=PRICES,
    strike=PRICES,
    years=YEARS,
    domestic=RATES,
    foreign=RATES,
    vol=VOLS,
)
def test_garman_kohlhagen_is_bsm_with_the_foreign_rate_as_yield(  # noqa: PLR0913
    *,
    kind: str,
    spot: float,
    strike: float,
    years: float,
    domestic: float,
    foreign: float,
    vol: float,
) -> None:
    ours = run(
        calculation="garman_kohlhagen",
        option_type=kind,
        spot=spot,
        strike=strike,
        years=years,
        domestic_rate=domestic,
        foreign_rate=foreign,
        volatility=vol,
    )
    theirs = bsm(
        option_type=kind,
        spot=spot,
        strike=strike,
        years=years,
        risk_free_rate=domestic,
        dividend_yield=foreign,
        volatility=vol,
    )
    for name in ("price", "delta", "gamma", "vega", "theta"):
        assert getattr(ours, name) == getattr(theirs, name), name
    assert ours.domestic_rho == theirs.rho
    assert ours.foreign_rho == theirs.dividend_rho


@pytest.mark.invariant("derivatives.futures_fx_options", "put_call_parity")
@given(
    underlying=PRICES,
    strike=PRICES,
    years=YEARS,
    domestic=RATES,
    foreign=RATES,
    vol=VOLS,
)
def test_put_call_parity_holds_for_both_models(  # noqa: PLR0913
    *,
    underlying: float,
    strike: float,
    years: float,
    domestic: float,
    foreign: float,
    vol: float,
) -> None:
    futures = {
        "calculation": "black_76",
        "futures_price": underlying,
        "strike": strike,
        "years": years,
        "risk_free_rate": domestic,
        "volatility": vol,
    }
    gap = (underlying - strike) * math.exp(-domestic * years)
    scale = (underlying + strike) * math.exp(-domestic * years)
    call = run(option_type="call", **futures).price
    put = run(option_type="put", **futures).price
    assert math.isclose(call - put, gap, abs_tol=1e-12 * scale)
    currency = {
        "calculation": "garman_kohlhagen",
        "spot": underlying,
        "strike": strike,
        "years": years,
        "domestic_rate": domestic,
        "foreign_rate": foreign,
        "volatility": vol,
    }
    asset = underlying * math.exp(-foreign * years)
    cash = strike * math.exp(-domestic * years)
    call = run(option_type="call", **currency).price
    put = run(option_type="put", **currency).price
    assert math.isclose(call - put, asset - cash, abs_tol=1e-12 * max(asset, cash))


@settings(deadline=None)
@given(kind=KINDS, vol=st.floats(min_value=0.001, max_value=5.0), **MODERATE)
def test_both_implied_volatilities_round_trip(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    underlying: float,
    moneyness: float,
    years: float,
    rate: float,
) -> None:
    strike = underlying * moneyness
    futures = {
        "option_type": kind,
        "futures_price": underlying,
        "strike": strike,
        "years": years,
        "risk_free_rate": rate,
    }
    priced = run(calculation="black_76", volatility=vol, **futures)
    assume(priced.vega > 1e-6 * underlying)
    solved = run(
        calculation="black_76_implied_volatility",
        option_price=priced.price,
        **futures,
    )
    assume(solved.lower_bound + 1e-9 * underlying < priced.price)
    assume(priced.price < solved.upper_bound - 1e-9 * underlying)
    assert solved.implied_volatility is not None
    tolerance = 1e-10 * underlying / priced.vega + 1e-11
    assert math.isclose(solved.implied_volatility, vol, rel_tol=0, abs_tol=tolerance)
    currency = {
        "option_type": kind,
        "spot": underlying,
        "strike": strike,
        "years": years,
        "domestic_rate": rate,
        "foreign_rate": rate / 2,
    }
    priced = run(calculation="garman_kohlhagen", volatility=vol, **currency)
    assume(priced.vega > 1e-6 * underlying)
    solved = run(
        calculation="garman_kohlhagen_implied_volatility",
        option_price=priced.price,
        **currency,
    )
    assume(solved.lower_bound + 1e-9 * underlying < priced.price)
    assume(priced.price < solved.upper_bound - 1e-9 * underlying)
    assert solved.implied_volatility is not None
    tolerance = 1e-10 * underlying / priced.vega + 1e-11
    assert math.isclose(solved.implied_volatility, vol, rel_tol=0, abs_tol=tolerance)


def test_a_currency_price_outside_the_bounds_has_no_implied_volatility() -> None:
    result = run_model(
        futures_fx_options,
        {
            "calculation": "garman_kohlhagen_implied_volatility",
            "option_type": "call",
            "option_price": 2.0,
            "spot": 1.08,
            "strike": 1.10,
            "years": 0.5,
            "domestic_rate": 0.045,
            "foreign_rate": 0.03,
        },
    )
    assert result.outputs.implied_volatility is None
    assert [w.code for w in result.warnings] == ["price_outside_no_arbitrage_bounds"]


# --- QuantLib and vollib as oracles ----------------------------------------------

TODAY = ql.Date(15, 1, 2026)


@pytest.mark.oracle("derivatives.futures_fx_options")
@given(kind=KINDS, vol=st.floats(min_value=0.01, max_value=2.0), **MODERATE)
def test_black_76_agrees_with_quantlibs_black_formula(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    underlying: float,
    moneyness: float,
    years: float,
    rate: float,
) -> None:
    strike = underlying * moneyness
    discount = math.exp(-rate * years)
    theirs = ql.blackFormula(
        ql.Option.Call if kind == "call" else ql.Option.Put,
        strike,
        underlying,
        vol * math.sqrt(years),
        discount,
    )
    ours = run(
        calculation="black_76",
        option_type=kind,
        futures_price=underlying,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        volatility=vol,
    )
    assert math.isclose(
        ours.price, theirs, rel_tol=1e-10, abs_tol=1e-12 * (underlying + strike)
    )


@pytest.mark.oracle("derivatives.futures_fx_options")
@settings(deadline=None)
@given(
    kind=KINDS,
    days=st.integers(min_value=1, max_value=3650),
    domestic=st.floats(min_value=-0.05, max_value=0.2),
    foreign=st.floats(min_value=-0.05, max_value=0.2),
    vol=st.floats(min_value=0.01, max_value=2.0),
    spot=st.floats(min_value=0.001, max_value=1000.0),
    moneyness=st.floats(min_value=0.5, max_value=2.0),
)
def test_garman_kohlhagen_agrees_with_quantlib(  # noqa: PLR0913
    *,
    kind: str,
    days: int,
    domestic: float,
    foreign: float,
    vol: float,
    spot: float,
    moneyness: float,
) -> None:
    ql.Settings.instance().evaluationDate = TODAY
    day_count = ql.Actual365Fixed()
    strike = spot * moneyness
    process = ql.GarmanKohlagenProcess(
        ql.QuoteHandle(ql.SimpleQuote(spot)),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, foreign, day_count)),
        ql.YieldTermStructureHandle(ql.FlatForward(TODAY, domestic, day_count)),
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
    ours = run(
        calculation="garman_kohlhagen",
        option_type=kind,
        spot=spot,
        strike=strike,
        years=days / 365,
        domestic_rate=domestic,
        foreign_rate=foreign,
        volatility=vol,
    )
    scale = spot + strike
    pairs = {
        "price": (ours.price, option.NPV()),
        "delta": (ours.delta, option.delta()),
        "gamma": (ours.gamma, option.gamma()),
        "vega": (ours.vega, option.vega()),
        "theta": (ours.theta, option.theta()),
        "domestic_rho": (ours.domestic_rho, option.rho()),
        "foreign_rho": (ours.foreign_rho, option.dividendRho()),
    }
    for name, (mine, theirs) in pairs.items():
        tolerance = 1e-11 * scale / spot if name == "gamma" else 1e-11 * scale
        assert math.isclose(mine, theirs, rel_tol=1e-9, abs_tol=tolerance), name


@pytest.mark.oracle("derivatives.futures_fx_options")
@settings(deadline=None)
@given(kind=KINDS, vol=st.floats(min_value=0.02, max_value=2.0), **MODERATE)
def test_black_76_implied_volatility_agrees_with_vollib(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    underlying: float,
    moneyness: float,
    years: float,
    rate: float,
) -> None:
    strike = underlying * moneyness
    terms = {
        "option_type": kind,
        "futures_price": underlying,
        "strike": strike,
        "years": years,
        "risk_free_rate": rate,
    }
    priced = run(calculation="black_76", volatility=vol, **terms)
    solved = run(
        calculation="black_76_implied_volatility", option_price=priced.price, **terms
    )
    assume(priced.vega > 1e-4 * underlying)
    assume(solved.lower_bound + 1e-7 * underlying < priced.price)
    assume(priced.price < solved.upper_bound - 1e-7 * underlying)
    theirs = vollib_black_implied_volatility(
        priced.price, underlying, strike, rate, years, kind[0]
    )
    assert solved.implied_volatility is not None
    assert math.isclose(solved.implied_volatility, theirs, rel_tol=0, abs_tol=1e-7)


@pytest.mark.oracle("derivatives.futures_fx_options")
@given(kind=KINDS, vol=st.floats(min_value=0.05, max_value=1.5), **MODERATE)
def test_black_76_greeks_agree_with_quantlib_differences(  # noqa: PLR0913
    *,
    kind: str,
    vol: float,
    underlying: float,
    moneyness: float,
    years: float,
    rate: float,
) -> None:
    strike = underlying * moneyness
    option = ql.Option.Call if kind == "call" else ql.Option.Put

    def black(forward: float, sigma: float, tau: float, r: float) -> float:
        value: float = ql.blackFormula(
            option, strike, forward, sigma * math.sqrt(tau), math.exp(-r * tau)
        )
        return value

    ours = run(
        calculation="black_76",
        option_type=kind,
        futures_price=underlying,
        strike=strike,
        years=years,
        risk_free_rate=rate,
        volatility=vol,
    )
    f_step, v_step, t_step, r_step = 1e-4 * underlying, 1e-5, 1e-6, 1e-6
    differences = {
        "delta": (
            black(underlying + f_step, vol, years, rate)
            - black(underlying - f_step, vol, years, rate)
        )
        / (2 * f_step),
        "gamma": (
            black(underlying + f_step, vol, years, rate)
            - 2 * black(underlying, vol, years, rate)
            + black(underlying - f_step, vol, years, rate)
        )
        / f_step**2,
        "vega": (
            black(underlying, vol + v_step, years, rate)
            - black(underlying, vol - v_step, years, rate)
        )
        / (2 * v_step),
        # Theta is the change as calendar time passes: minus the change in T.
        "theta": -(
            black(underlying, vol, years + t_step, rate)
            - black(underlying, vol, years - t_step, rate)
        )
        / (2 * t_step),
        "rho": (
            black(underlying, vol, years, rate + r_step)
            - black(underlying, vol, years, rate - r_step)
        )
        / (2 * r_step),
    }
    scale = underlying + strike
    for name, difference in differences.items():
        mine = getattr(ours, name)
        tolerance = (1e-4 / underlying if name == "gamma" else 1e-6) * scale
        assert math.isclose(mine, difference, rel_tol=1e-4, abs_tol=tolerance), name
