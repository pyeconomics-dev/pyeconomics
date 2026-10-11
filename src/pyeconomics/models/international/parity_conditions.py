# src/pyeconomics/models/international/parity_conditions.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The international parity conditions: ``international.parity_conditions``.

An exchange rate :math:`S` is in units of the quote currency per unit of the
base currency, so a rise is the base currency appreciating. Six calculations,
discriminated on ``calculation``:

- ``covered_interest_parity``: the forward rate that leaves no riskless profit
  from borrowing one currency and lending the other with the exchange risk
  hedged, :math:`F = S\,G_q(T) / G_b(T)`, where :math:`G` is each currency's
  growth at its interest rate over :math:`T` years, and the forward premium;
- ``uncovered_interest_parity``: the spot rate expected in :math:`T` years if
  expected returns are equal unhedged, the same ratio of growths;
- ``relative_ppp``: the spot rate expected after :math:`T` years of inflation,
  :math:`S\,[(1 + \pi_q) / (1 + \pi_b)]^T`;
- ``absolute_ppp``: the exchange rate at which a basket costs the same in both
  currencies, :math:`P_q / P_b`, and how far the spot rate values the base
  currency above it;
- ``international_fisher``: each currency's real rate by the Fisher relation,
  :math:`(1 + i) = (1 + r)(1 + \pi)`, and the change in the spot rate equal
  real rates imply, :math:`(1 + i_q) / (1 + i_b) - 1`;
- ``real_exchange_rate``: the real rate :math:`S P_b / P_q` and its change over
  a period, :math:`(1 + s)(1 + \pi_b) / (1 + \pi_q) - 1`.

Rates and inflation are decimals per year. The relations are textbook formulas;
the evidence that each holds in data differs (see the limitations).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Final, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    Compounding,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Frequency,
    IndexLevel,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Rate,
    Ratio,
    Reference,
    Return,
    Years,
    accumulation_factor,
    model,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["parity_conditions"]

_FX = "units of the quote currency per unit of the base currency"
#: An exchange rate.
_FX_MIN: Final = 1e-6
_FX_MAX: Final = 1e6
#: Nominal interest rates. At -5% simple interest over ten years, growth is 0.5.
_RATE_MIN: Final = -0.05
_RATE_MAX: Final = 1.0
#: The longest horizon.
_YEARS_MAX: Final = 10.0
#: Inflation per year: deflation of 20% to inflation of 100%.
_INFLATION_MIN: Final = -0.2
_INFLATION_MAX: Final = 1.0
#: Growth ratios over ten years reach e^(1.05 x 10) = 36,316 (continuous rates)
#: and (2 / 0.8)^10 = 9,537 (inflation), so expected rates reach 3.7e10 and
#: changes 3.7e4: wider than ADR-0008's defaults for a ratio and a return.
_FX_OUT_MAX: Final = 1e11
_CHANGE_MAX: Final = 1e5
#: A basket's price in either currency, and the price indexes of a real rate.
_PRICE_MIN: Final = 0.01
_PRICE_MAX: Final = 1e7
#: A purchasing-power-parity rate is a ratio of basket prices, 1e-9 to 1e9.
_PPP_MAX: Final = 1e9
#: A real exchange rate is S P_b / P_q; its scale is set by the indexes' bases.
_REAL_MAX: Final = 1e15
#: Rate differences span twice a rate's range.
_DIFFERENCE_MAX: Final = 3.0
#: A real change: (1 + 10)(1 + 10) / (1 - 0.5) - 1 = 241 at most.
_REAL_CHANGE_MAX: Final = 250.0

_FREQUENCIES: Final[dict[str, Frequency]] = {
    "annual": Frequency.ANNUAL,
    "semiannual": Frequency.SEMIANNUAL,
    "quarterly": Frequency.QUARTERLY,
    "monthly": Frequency.MONTHLY,
}

type FrequencyName = Literal["annual", "semiannual", "quarterly", "monthly"]


def _spot() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=_FX_MIN, le=_FX_MAX, description=f"Spot exchange rate, in {_FX}")


def _rate(currency: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=_RATE_MIN,
        le=_RATE_MAX,
        description=f"Nominal interest rate of the {currency} currency per year",
    )


def _inflation(currency: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=_INFLATION_MIN,
        le=_INFLATION_MAX,
        description=f"Inflation per year in the {currency} currency's economy",
    )


def _years() -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(gt=0.0, le=_YEARS_MAX, description="Horizon in years")


def _change(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-1.0, le=_CHANGE_MAX, description=description)


# --- inputs ------------------------------------------------------------------


class _InterestParity(ModelInputs):
    spot: Ratio = _spot()
    quote_rate: Rate = _rate("quote")
    base_rate: Rate = _rate("base")
    years: Years = _years()
    compounding: Literal["simple", "periodic", "continuous"] = Field(
        "periodic", description="How both rates compound over the horizon"
    )
    frequency: FrequencyName = Field(
        "annual", description="Compounding frequency of periodic rates"
    )


class CoveredInputs(_InterestParity):
    """A spot rate and each currency's interest rate."""

    calculation: Literal["covered_interest_parity"] = Field(
        "covered_interest_parity", description="Forward rate by covered parity"
    )


class UncoveredInputs(_InterestParity):
    """A spot rate and each currency's interest rate."""

    calculation: Literal["uncovered_interest_parity"] = Field(
        "uncovered_interest_parity", description="Expected spot by uncovered parity"
    )


class RelativePppInputs(ModelInputs):
    """A spot rate and each economy's expected inflation."""

    calculation: Literal["relative_ppp"] = Field(
        "relative_ppp", description="Expected spot by relative purchasing power"
    )
    spot: Ratio = _spot()
    quote_inflation: Rate = _inflation("quote")
    base_inflation: Rate = _inflation("base")
    years: Years = _years()


class AbsolutePppInputs(ModelInputs):
    """A basket's price in each currency, and the spot rate."""

    calculation: Literal["absolute_ppp"] = Field(
        "absolute_ppp", description="Exchange rate by absolute purchasing power"
    )
    quote_price: Money = Field(
        ge=_PRICE_MIN, le=_PRICE_MAX, description="Basket's price in the quote currency"
    )
    base_price: Money = Field(
        ge=_PRICE_MIN, le=_PRICE_MAX, description="Basket's price in the base currency"
    )
    spot: Ratio = _spot()


class InternationalFisherInputs(ModelInputs):
    """Each currency's nominal rate and expected inflation."""

    calculation: Literal["international_fisher"] = Field(
        "international_fisher", description="Real rates and the expected change"
    )
    quote_rate: Rate = _rate("quote")
    base_rate: Rate = _rate("base")
    quote_inflation: Rate = _inflation("quote")
    base_inflation: Rate = _inflation("base")


class RealExchangeRateInputs(ModelInputs):
    """A spot rate, each economy's price level, and a period's changes."""

    calculation: Literal["real_exchange_rate"] = Field(
        "real_exchange_rate", description="Real exchange rate and its change"
    )
    spot: Ratio = _spot()
    quote_price_level: IndexLevel = Field(
        ge=_PRICE_MIN, le=_PRICE_MAX, description="Price index of the quote economy"
    )
    base_price_level: IndexLevel = Field(
        ge=_PRICE_MIN, le=_PRICE_MAX, description="Price index of the base economy"
    )
    spot_change: Return = Field(
        0.0, ge=-0.9, le=10.0, description="Change in the spot rate over the period"
    )
    quote_inflation: Return = Field(
        0.0, ge=-0.5, le=10.0, description="Inflation in the quote economy over it"
    )
    base_inflation: Return = Field(
        0.0, ge=-0.5, le=10.0, description="Inflation in the base economy over it"
    )


ParityConditionsInputs = Annotated[
    CoveredInputs
    | UncoveredInputs
    | RelativePppInputs
    | AbsolutePppInputs
    | InternationalFisherInputs
    | RealExchangeRateInputs,
    Field(discriminator="calculation"),
]


# --- outputs -----------------------------------------------------------------


def _expected(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(gt=0.0, le=_FX_OUT_MAX, description=f"{description}, in {_FX}")


class CoveredOutputs(ModelOutputs):
    calculation: Literal["covered_interest_parity"] = Field(
        "covered_interest_parity", description="Forward rate by covered parity"
    )
    forward_rate: Ratio = _expected("Forward exchange rate for the horizon")
    forward_points: Ratio = Field(
        ge=-_FX_OUT_MAX,
        le=_FX_OUT_MAX,
        description="Forward less spot, in units of the quote currency",
    )
    forward_premium: Return = _change(
        "Forward over spot, less one: the base currency's forward premium"
    )


class UncoveredOutputs(ModelOutputs):
    calculation: Literal["uncovered_interest_parity"] = Field(
        "uncovered_interest_parity", description="Expected spot by uncovered parity"
    )
    expected_spot: Ratio = _expected("Spot rate expected at the horizon")
    expected_change: Return = _change("Expected change in the spot rate")


class RelativePppOutputs(ModelOutputs):
    calculation: Literal["relative_ppp"] = Field(
        "relative_ppp", description="Expected spot by relative purchasing power"
    )
    expected_spot: Ratio = _expected("Spot rate expected at the horizon")
    expected_change: Return = _change("Expected change in the spot rate")
    inflation_differential: Rate = Field(
        ge=-_DIFFERENCE_MAX,
        le=_DIFFERENCE_MAX,
        description="Quote inflation less base inflation: the change per year, approx.",
    )


class AbsolutePppOutputs(ModelOutputs):
    calculation: Literal["absolute_ppp"] = Field(
        "absolute_ppp", description="Exchange rate by absolute purchasing power"
    )
    ppp_rate: Ratio = Field(
        gt=0.0,
        le=_PPP_MAX,
        description=f"Exchange rate equating the basket's prices, in {_FX}",
    )
    base_currency_valuation: Return = Field(
        ge=-1.0,
        le=100.0,
        description="Spot over the PPP rate, less one: above zero, the base is dear",
    )


class InternationalFisherOutputs(ModelOutputs):
    calculation: Literal["international_fisher"] = Field(
        "international_fisher", description="Real rates and the expected change"
    )
    quote_real_rate: Rate = Field(
        ge=-0.99, le=10.0, description="(1 + quote rate) / (1 + quote inflation) - 1"
    )
    base_real_rate: Rate = Field(
        ge=-0.99, le=10.0, description="(1 + base rate) / (1 + base inflation) - 1"
    )
    real_rate_differential: Rate = Field(
        ge=-_DIFFERENCE_MAX,
        le=_DIFFERENCE_MAX,
        description="Quote real rate less base real rate",
    )
    expected_change: Return = Field(
        ge=-1.0,
        le=100.0,
        description=(
            "Expected change in the spot rate over a year: (1 + i_q) / (1 + i_b) - 1"
        ),
    )
    approximate_change: Rate = Field(
        ge=-_DIFFERENCE_MAX,
        le=_DIFFERENCE_MAX,
        description="Quote rate less base rate: the change's linear approximation",
    )


class RealExchangeRateOutputs(ModelOutputs):
    calculation: Literal["real_exchange_rate"] = Field(
        "real_exchange_rate", description="Real exchange rate and its change"
    )
    real_exchange_rate: Ratio = Field(
        gt=0.0,
        le=_REAL_MAX,
        description="Spot times the base price level over the quote price level",
    )
    real_change: Return = Field(
        ge=-1.0,
        le=_REAL_CHANGE_MAX,
        description="(1 + spot change)(1 + base inflation)/(1 + quote inflation) - 1",
    )


ParityConditionsOutputs = Annotated[
    CoveredOutputs
    | UncoveredOutputs
    | RelativePppOutputs
    | AbsolutePppOutputs
    | InternationalFisherOutputs
    | RealExchangeRateOutputs,
    Field(discriminator="calculation"),
]


# --- calculations ------------------------------------------------------------


def _growth_ratio(inputs: _InterestParity) -> float:
    """Return the quote currency's growth over the base currency's."""
    compounding = Compounding(inputs.compounding)
    frequency = (
        _FREQUENCIES[inputs.frequency] if compounding is Compounding.PERIODIC else None
    )
    quote = accumulation_factor(inputs.quote_rate, inputs.years, compounding, frequency)
    base = accumulation_factor(inputs.base_rate, inputs.years, compounding, frequency)
    return quote / base


def _covered(inputs: CoveredInputs) -> CoveredOutputs:
    ratio = _growth_ratio(inputs)
    forward = inputs.spot * ratio
    return CoveredOutputs(
        forward_rate=forward,
        forward_points=forward - inputs.spot,
        forward_premium=ratio - 1.0,
    )


def _uncovered(inputs: UncoveredInputs) -> UncoveredOutputs:
    ratio = _growth_ratio(inputs)
    return UncoveredOutputs(
        expected_spot=inputs.spot * ratio, expected_change=ratio - 1.0
    )


def _relative_ppp(inputs: RelativePppInputs) -> RelativePppOutputs:
    ratio = ((1.0 + inputs.quote_inflation) / (1.0 + inputs.base_inflation)) ** (
        inputs.years
    )
    return RelativePppOutputs(
        expected_spot=inputs.spot * ratio,
        expected_change=ratio - 1.0,
        inflation_differential=inputs.quote_inflation - inputs.base_inflation,
    )


def _absolute_ppp(inputs: AbsolutePppInputs) -> AbsolutePppOutputs:
    ppp = inputs.quote_price / inputs.base_price
    valuation = inputs.spot / ppp - 1.0
    if valuation > 100.0:  # noqa: PLR2004 - the return's upper bound
        msg = (
            f"the spot rate is {valuation + 1.0:g} times the PPP rate {ppp:g}; a "
            "valuation above 100 (10,000%) is outside the output's bounds"
        )
        raise DomainError(msg)
    return AbsolutePppOutputs(ppp_rate=ppp, base_currency_valuation=valuation)


def _real_rate(nominal: float, inflation: float) -> float:
    return (nominal - inflation) / (1.0 + inflation)


def _international_fisher(
    inputs: InternationalFisherInputs,
) -> InternationalFisherOutputs:
    quote_real = _real_rate(inputs.quote_rate, inputs.quote_inflation)
    base_real = _real_rate(inputs.base_rate, inputs.base_inflation)
    return InternationalFisherOutputs(
        quote_real_rate=quote_real,
        base_real_rate=base_real,
        real_rate_differential=quote_real - base_real,
        expected_change=(inputs.quote_rate - inputs.base_rate)
        / (1.0 + inputs.base_rate),
        approximate_change=inputs.quote_rate - inputs.base_rate,
    )


def _real_exchange_rate(inputs: RealExchangeRateInputs) -> RealExchangeRateOutputs:
    return RealExchangeRateOutputs(
        real_exchange_rate=inputs.spot
        * inputs.base_price_level
        / inputs.quote_price_level,
        real_change=(1.0 + inputs.spot_change)
        * (1.0 + inputs.base_inflation)
        / (1.0 + inputs.quote_inflation)
        - 1.0,
    )


# --- the model ---------------------------------------------------------------

_BIS = Reference(
    key="borio2016",
    citation=(
        "Borio, C., McCauley, R. N., McGuire, P. and Sushko, V. (2016). Covered "
        "interest parity lost: understanding the cross-currency basis. BIS "
        "Quarterly Review, September 2016."
    ),
    url="https://www.bis.org/publ/qtrpdf/r_qt1609e.htm",
    locator='Section "A framework" and Box A (the covered parity condition)',
)
_ROGOFF = Reference(
    key="rogoff1996",
    citation=(
        "Rogoff, K. (1996). The Purchasing Power Parity Puzzle. Journal of "
        "Economic Literature, 34(2), 647-668."
    ),
    url="https://ideas.repec.org/a/aea/jeclit/v34y1996i2p647-668.html",
    locator="The definitions of absolute and relative PPP, and the evidence on them",
)
_FISHER = Reference(
    key="fisher1930",
    citation="Fisher, I. (1930). The Theory of Interest. Macmillan.",
    url="https://www.econlib.org/library/YPDBooks/Fisher/fshToI.html",
    locator="The relation between money interest and real interest",
)
_FAMA = Reference(
    key="fama1984",
    citation=(
        "Fama, E. F. (1984). Forward and Spot Exchange Rates. Journal of "
        "Monetary Economics, 14(3), 319-338."
    ),
    doi="10.1016/0304-3932(84)90046-1",
    locator="The regressions of spot changes on the forward premium",
)


@model(
    id="international.parity_conditions",
    version=1,
    title="International parity conditions",
    summary=(
        "Covered and uncovered interest parity, relative and absolute purchasing "
        "power parity, the international Fisher effect and real exchange rates."
    ),
    formula=(
        (
            r"F = S\,\frac{G_q(T)}{G_b(T)}, \quad "
            r"G(T) \in \{1 + iT,\ (1 + i/m)^{mT},\ e^{iT}\}"
        ),
        r"E[S_T] = S\,\frac{G_q(T)}{G_b(T)}",
        (
            r"E[S_T] = S \left(\frac{1 + \pi_q}{1 + \pi_b}\right)^T, \quad "
            r"S_{PPP} = \frac{P_q}{P_b}"
        ),
        (
            r"1 + i = (1 + r)(1 + \pi), \quad "
            r"\frac{E[S_1]}{S_0} - 1 = \frac{1 + i_q}{1 + i_b} - 1"
        ),
        (
            r"q = S\,\frac{P_b}{P_q}, \quad "
            r"\Delta q = \frac{(1 + s)(1 + \pi_b)}{1 + \pi_q} - 1"
        ),
    ),
    assumptions=(
        (
            "Exchange rates are in units of the quote currency per unit of the "
            "base currency."
        ),
        (
            "Interest parity compares money-market investments of equal risk, with "
            "both rates compounded the same way over the horizon."
        ),
        (
            "Relative PPP and the international Fisher effect compound annually; "
            "the Fisher effect is over one year."
        ),
    ),
    limitations=(
        (
            "Results are the formulas' outputs for the inputs given, not "
            "forecasts or trading advice."
        ),
        (
            "Covered interest parity holds up to transaction costs and credit; "
            "since 2008 a persistent cross-currency basis has opened gaps the "
            "formula does not show."
        ),
        (
            "Uncovered interest parity and purchasing power parity fail "
            "empirically over short horizons: high-rate currencies tend not to "
            "depreciate as uncovered parity predicts, and real exchange rates "
            "deviate from PPP for years. Read their outputs as benchmarks."
        ),
        (
            "Absolute PPP needs the same basket in both economies; a spot rate "
            "more than 101 times the PPP rate raises DomainError."
        ),
    ),
    references=(_BIS, _ROGOFF, _FISHER, _FAMA),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    tags=(
        "exchange rates",
        "interest rate parity",
        "purchasing power parity",
        "fisher effect",
        "real exchange rate",
    ),
    invariants=(
        Invariant(
            id="parity_forward_matches_derivatives_forwards",
            statement=(
                "With simple interest, the covered-parity forward equals the "
                "fx_forward of derivatives.forwards on the same horizon and "
                "day count."
            ),
        ),
        Invariant(
            id="real_rate_identity",
            statement=(
                "Each currency's real rate r and inflation pi give its nominal rate: "
                "(1 + r)(1 + pi) = 1 + i."
            ),
        ),
    ),
    examples=(
        Example(
            name="two_year_forward",
            inputs={
                "calculation": "covered_interest_parity",
                "spot": 0.75,
                "quote_rate": 0.01,
                "base_rate": 0.03,
                "years": 2,
                "compounding": "continuous",
            },
        ),
        Example(
            name="expected_spot_by_uncovered_parity",
            inputs={
                "calculation": "uncovered_interest_parity",
                "spot": 150.0,
                "quote_rate": 0.005,
                "base_rate": 0.045,
                "years": 1,
            },
        ),
        Example(
            name="five_years_of_inflation",
            inputs={
                "calculation": "relative_ppp",
                "spot": 1.25,
                "quote_inflation": 0.02,
                "base_inflation": 0.035,
                "years": 5,
            },
        ),
        Example(
            name="basket_prices",
            inputs={
                "calculation": "absolute_ppp",
                "quote_price": 5.69,
                "base_price": 4.95,
                "spot": 1.10,
            },
        ),
        Example(
            name="real_rates",
            inputs={
                "calculation": "international_fisher",
                "quote_rate": 0.05,
                "base_rate": 0.02,
                "quote_inflation": 0.03,
                "base_inflation": 0.01,
            },
        ),
        Example(
            name="real_appreciation",
            inputs={
                "calculation": "real_exchange_rate",
                "spot": 1.10,
                "quote_price_level": 120.0,
                "base_price_level": 115.0,
                "spot_change": 0.05,
                "quote_inflation": 0.03,
                "base_inflation": 0.02,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def parity_conditions(inputs: ParityConditionsInputs) -> ParityConditionsOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[
    dict[type[ModelInputs], Callable[[Any], ParityConditionsOutputs]]
] = {
    CoveredInputs: _covered,
    UncoveredInputs: _uncovered,
    RelativePppInputs: _relative_ppp,
    AbsolutePppInputs: _absolute_ppp,
    InternationalFisherInputs: _international_fisher,
    RealExchangeRateInputs: _real_exchange_rate,
}
