# src/pyeconomics/models/accounting/scoring_models.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Original Altman, eight-variable Beneish and nine-signal Piotroski scores.

Ratios and normalized signals are supplied, avoiding hidden accounting
normalizations. Components are returned individually. Zone names label the
historical Altman bands; they are not credit or investment recommendations.
"""

from __future__ import annotations

import math
from typing import Annotated, Literal

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Ratio,
    Reference,
    model,
)

__all__ = ["scoring_models"]

DISTRESS_CUTOFF = 1.81
SAFE_CUTOFF = 2.99


class AltmanInputs(ModelInputs):
    calculation: Literal["altman_z"] = Field(
        "altman_z", description="Original public manufacturing Z-score"
    )
    working_capital_to_assets: Ratio = Field(
        ge=-100, le=100, description="Working capital / total assets, decimal ratio"
    )
    retained_earnings_to_assets: Ratio = Field(
        ge=-100, le=100, description="Retained earnings / total assets, decimal ratio"
    )
    ebit_to_assets: Ratio = Field(
        ge=-100, le=100, description="EBIT / total assets, decimal ratio"
    )
    market_equity_to_liabilities: Ratio = Field(
        ge=0,
        le=100,
        description="Market common and preferred equity / book total liabilities",
    )
    sales_to_assets: Ratio = Field(
        ge=0, le=100, description="Sales / total assets, unscaled turnover"
    )


class BeneishInputs(ModelInputs):
    calculation: Literal["beneish_m"] = Field(
        "beneish_m", description="Eight-variable M-score"
    )
    dsri: Ratio = Field(
        ge=0, le=100, description="(Receivables/sales)t / (receivables/sales)t-1"
    )
    gmi: Ratio = Field(ge=0, le=100, description="Gross margin t-1 / gross margin t")
    aqi: Ratio = Field(
        ge=0, le=100, description="[1-(current assets+PPE)/assets]t / same t-1"
    )
    sgi: Ratio = Field(ge=0, le=100, description="Sales t / sales t-1")
    depi: Ratio = Field(
        ge=0, le=100, description="[Depreciation/(depreciation+PPE)]t-1 / same t"
    )
    sgai: Ratio = Field(ge=0, le=100, description="(SG&A/sales)t / (SG&A/sales)t-1")
    tata: Ratio = Field(
        ge=-100,
        le=100,
        description=(
            "(Change in current assets - change in cash - change in current "
            "liabilities + change in current maturities of long-term debt "
            "+ change in income-tax payable - depreciation and amortization) "
            "/ total assets"
        ),
    )
    lvgi: Ratio = Field(
        ge=0,
        le=100,
        description="[(Current liabilities+long-term debt)/assets]t / same t-1",
    )


class PiotroskiInputs(ModelInputs):
    calculation: Literal["piotroski_f"] = Field(
        "piotroski_f", description="Nine original binary signals"
    )
    positive_roa: bool = Field(
        description="Net income before extraordinary items / beginning assets > 0"
    )
    positive_cfo: bool = Field(description="Operating cash flow / beginning assets > 0")
    improving_roa: bool = Field(
        description=(
            "Current ROA exceeds prior ROA; each scaled by its beginning assets"
        )
    )
    cash_exceeds_income: bool = Field(
        description="CFO / beginning assets exceeds ROA, strictly"
    )
    decreasing_leverage: bool = Field(
        description=(
            "Long-term debt including its current portion / average assets "
            "decreased, strictly"
        )
    )
    improving_liquidity: bool = Field(
        description="Current assets / current liabilities increased, strictly"
    )
    no_equity_issuance: bool = Field(
        description="No common equity issued during the preceding year"
    )
    improving_margin: bool = Field(description="Gross margin increased, strictly")
    improving_turnover: bool = Field(
        description="Sales / beginning assets increased, strictly"
    )


Inputs = Annotated[
    AltmanInputs | BeneishInputs | PiotroskiInputs, Field(discriminator="calculation")
]


class AltmanOutputs(ModelOutputs):
    calculation: Literal["altman_z"] = Field(
        "altman_z", description="Original public manufacturing Z-score"
    )
    z_score: Ratio = Field(
        ge=-1000,
        le=1000,
        description="Original discriminant score, using .999 sales coefficient",
    )
    zone: Literal["distress", "grey", "safe"] = Field(
        description="Historical bands: below 1.81, 1.81 through 2.99, above 2.99"
    )
    working_capital_component: Ratio = Field(
        ge=-120, le=120, description="1.2 * working capital/assets"
    )
    retained_earnings_component: Ratio = Field(
        ge=-140, le=140, description="1.4 * retained earnings/assets"
    )
    ebit_component: Ratio = Field(ge=-330, le=330, description="3.3 * EBIT/assets")
    equity_component: Ratio = Field(
        ge=0, le=60, description="0.6 * market equity/book liabilities"
    )
    sales_component: Ratio = Field(ge=0, le=100, description="0.999 * sales/assets")


class BeneishOutputs(ModelOutputs):
    calculation: Literal["beneish_m"] = Field(
        "beneish_m", description="Eight-variable M-score"
    )
    m_score: Ratio = Field(
        ge=-1000,
        le=1000,
        description=(
            "-4.84 plus the eight weighted components; no probability or "
            "classification implied"
        ),
    )
    dsri_component: Ratio = Field(ge=0, le=100, description="0.920 * DSRI")
    gmi_component: Ratio = Field(ge=0, le=100, description="0.528 * GMI")
    aqi_component: Ratio = Field(ge=0, le=100, description="0.404 * AQI")
    sgi_component: Ratio = Field(ge=0, le=100, description="0.892 * SGI")
    depi_component: Ratio = Field(ge=0, le=100, description="0.115 * DEPI")
    sgai_component: Ratio = Field(ge=-100, le=0, description="-0.172 * SGAI")
    tata_component: Ratio = Field(ge=-500, le=500, description="4.679 * TATA")
    lvgi_component: Ratio = Field(ge=-100, le=0, description="-0.327 * LVGI")


class PiotroskiOutputs(ModelOutputs):
    calculation: Literal["piotroski_f"] = Field(
        "piotroski_f", description="Nine original binary signals"
    )
    f_score: Count = Field(ge=0, le=9, description="Sum of the nine binary signals")
    positive_roa: Count = Field(ge=0, le=1, description="Positive ROA signal")
    positive_cfo: Count = Field(ge=0, le=1, description="Positive CFO signal")
    improving_roa: Count = Field(ge=0, le=1, description="Increasing ROA signal")
    cash_exceeds_income: Count = Field(
        ge=0, le=1, description="CFO greater than ROA signal"
    )
    decreasing_leverage: Count = Field(
        ge=0, le=1, description="Decreasing leverage signal"
    )
    improving_liquidity: Count = Field(
        ge=0, le=1, description="Increasing current ratio signal"
    )
    no_equity_issuance: Count = Field(
        ge=0, le=1, description="No common equity issuance signal"
    )
    improving_margin: Count = Field(
        ge=0, le=1, description="Increasing gross margin signal"
    )
    improving_turnover: Count = Field(
        ge=0, le=1, description="Increasing asset turnover signal"
    )


Outputs = Annotated[
    AltmanOutputs | BeneishOutputs | PiotroskiOutputs,
    Field(discriminator="calculation"),
]


@model(
    id="accounting.scoring_models",
    version=1,
    title="Accounting scoring models",
    summary=(
        "Original Altman Z with historical bands, eight-variable "
        "Beneish M, and Piotroski F with components."
    ),
    formula=(
        r"Z=1.2X_1+1.4X_2+3.3X_3+0.6X_4+0.999X_5",
        r"M=-4.84+.920DSRI+.528GMI+.404AQI+.892SGI+.115DEPI-.172SGAI+4.679TATA-.327LVGI",
        r"F=\sum_{j=1}^9 I_j",
    ),
    assumptions=(
        (
            "Altman ratios are decimals: the original .012/.014/.033/.006 "
            "coefficients on percentage inputs become 1.2/1.4/3.3/.6; "
            "sales turnover retains .999."
        ),
        (
            "Beneish inputs are the eight precomputed variables defined "
            "in the schema, with original Table 3 coefficients. TATA uses "
            "the original balance-sheet accrual definition."
        ),
        (
            "Piotroski accepts nine precomputed binary signals; each "
            "strict comparison and denominator convention is stated in "
            "its input description."
        ),
    ),
    limitations=(
        (
            "Altman was estimated on 66 US manufacturing firms, 33 "
            "bankrupt in 1946-1965 with matched nonbankrupt firms; it is "
            "not the private/nonmanufacturing variant. Bands are "
            "historical labels, not credit recommendations."
        ),
        (
            "Beneish's estimation sample covers identified US earnings "
            "manipulators in 1982-1992, excluding financial firms; "
            "coefficients are not a calibrated probability. Negative or "
            "undefined input indices must be resolved upstream."
        ),
        (
            "Piotroski studied high book-to-market US firms in 1976-1996; "
            "supplied binary signals must use comparable financial "
            "statements. None of the scores or bands is a buy, sell or "
            "credit recommendation."
        ),
    ),
    references=(
        Reference(
            key="altman1968",
            citation=(
                "Altman, E. I. (1968). Financial Ratios, Discriminant "
                "Analysis and the Prediction of Corporate Bankruptcy. Journal "
                "of Finance 23, 589-609."
            ),
            doi="10.1111/j.1540-6261.1968.tb00843.x",
            locator="Equation (1), p. 594; zones, p. 606",
        ),
        Reference(
            key="beneish1999",
            citation=(
                "Beneish, M. D. (1999). The Detection of Earnings "
                "Manipulation. Financial Analysts Journal 55(5), 24-36."
            ),
            doi="10.2469/faj.v55.n5.2296",
            locator="Variable definitions and Table 3",
        ),
        Reference(
            key="piotroski2000",
            citation=(
                "Piotroski, J. D. (2000). Value Investing: The Use of "
                "Historical Financial Statement Information to Separate "
                "Winners from Losers. Journal of Accounting Research 38, "
                "1-41."
            ),
            doi="10.2307/2672906",
            locator="Sections 2.3.1-2.3.3; equation (1)",
        ),
    ),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="z_score_linear_in_ratios",
            statement="Altman Z is linear in its five ratio inputs.",
        ),
        Invariant(
            id="f_score_between_zero_and_nine",
            statement="Piotroski F is an integer from zero through nine.",
        ),
        Invariant(
            id="m_score_matches_coefficients",
            statement=(
                "Beneish M equals its intercept plus the eight original "
                "weighted variables."
            ),
        ),
    ),
    examples=(
        Example(
            name="formula_altman_z",
            inputs={
                "calculation": "altman_z",
                "working_capital_to_assets": 0,
                "retained_earnings_to_assets": 0,
                "ebit_to_assets": 0,
                "market_equity_to_liabilities": 0,
                "sales_to_assets": 0,
            },
        ),
        Example(
            name="formula_beneish_m",
            inputs={
                "calculation": "beneish_m",
                "dsri": 1,
                "gmi": 1,
                "aqi": 1,
                "sgi": 1,
                "depi": 1,
                "sgai": 1,
                "tata": 0,
                "lvgi": 1,
            },
        ),
        Example(
            name="formula_piotroski_f",
            inputs={
                "calculation": "piotroski_f",
                "positive_roa": True,
                "positive_cfo": True,
                "improving_roa": True,
                "cash_exceeds_income": True,
                "decreasing_leverage": True,
                "improving_liquidity": True,
                "no_equity_issuance": True,
                "improving_margin": True,
                "improving_turnover": True,
            },
        ),
        Example(
            name="unit_altman_ratios",
            inputs={
                "calculation": "altman_z",
                "working_capital_to_assets": 1,
                "retained_earnings_to_assets": 1,
                "ebit_to_assets": 1,
                "market_equity_to_liabilities": 1,
                "sales_to_assets": 1,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def scoring_models(inputs: Inputs) -> Outputs:
    """Return the selected historical score and every component."""
    if isinstance(inputs, AltmanInputs):
        parts = {
            "working_capital_component": 1.2 * inputs.working_capital_to_assets,
            "retained_earnings_component": 1.4 * inputs.retained_earnings_to_assets,
            "ebit_component": 3.3 * inputs.ebit_to_assets,
            "equity_component": 0.6 * inputs.market_equity_to_liabilities,
            "sales_component": 0.999 * inputs.sales_to_assets,
        }
        score = math.fsum(parts.values())
        zone: Literal["distress", "grey", "safe"] = (
            "distress"
            if score < DISTRESS_CUTOFF
            else "safe"
            if score > SAFE_CUTOFF
            else "grey"
        )
        return AltmanOutputs(calculation="altman_z", z_score=score, zone=zone, **parts)
    if isinstance(inputs, BeneishInputs):
        parts = {
            "dsri_component": 0.920 * inputs.dsri,
            "gmi_component": 0.528 * inputs.gmi,
            "aqi_component": 0.404 * inputs.aqi,
            "sgi_component": 0.892 * inputs.sgi,
            "depi_component": 0.115 * inputs.depi,
            "sgai_component": -0.172 * inputs.sgai,
            "tata_component": 4.679 * inputs.tata,
            "lvgi_component": -0.327 * inputs.lvgi,
        }
        return BeneishOutputs(
            calculation="beneish_m",
            m_score=math.fsum([-4.84, *parts.values()]),
            **parts,
        )
    signals = {
        name: int(value)
        for name, value in inputs.model_dump(exclude={"calculation"}).items()
    }
    return PiotroskiOutputs(
        calculation="piotroski_f", f_score=sum(signals.values()), **signals
    )
