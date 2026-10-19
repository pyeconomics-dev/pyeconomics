# src/pyeconomics/data/catalog/fiscal.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""United States federal fiscal concepts: debt, its cost and the primary balance."""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Tier,
)
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_SECTION: Final = "Fiscal"
_QUARTERLY: Final = ObservationFrequency.QUARTERLY
_BEA_NOTE: Final = (
    "BEA's API serves current estimates only, so a run on it records revised_data."
)
_SAAR: Final = SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE

CONCEPTS: Final = (
    Concept(
        id="us.fiscal.federal_debt",
        title="Total public debt outstanding",
        definition=(
            "The face amount of the debt the US Treasury has issued and not "
            "repaid (the debt to the penny), in dollars, each business day."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="US dollars",
        frequency=ObservationFrequency.BUSINESS_DAILY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="treasury",
                series="debt",
                column="tot_pub_debt_out_amt",
                delivers=ObservationFrequency.IRREGULAR,
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.debt_to_gdp",
        title="Federal debt to GDP",
        definition=(
            "Total public debt outstanding at the end of each quarter over "
            "nominal GDP at that quarter's annual rate, as a ratio (1.2 is 120% "
            "of GDP), quarterly."
        ),
        unit_kind=UnitKind.RATIO,
        unit_text="ratio of debt to annual GDP (1.2 is 120%)",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Derived(
                operands=(
                    Operand(
                        "us.fiscal.federal_debt",
                        ("convert(to=quarterly,method=last)",),
                    ),
                    Operand("us.output.nominal_gdp"),
                ),
                transform="ratio",
                note=(
                    "The Treasury's debt to the penny over BEA's nominal GDP: "
                    "both originators, so hosted mode can compute it."
                ),
            ),
            Candidate(provider="fred", series="GFDEGDQ188S", tier=Tier.AGGREGATOR),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.average_interest_rate",
        title="Average interest rate on federal debt",
        definition=(
            "The average interest rate on total interest-bearing US Treasury "
            "debt at each month end, as a decimal per year, from the "
            "Treasury's monthly table of average interest rates."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.033 is 3.3%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="treasury",
                series="average_interest",
                column="Total Interest-bearing Debt:avg_interest_rate_amt",
                delivers=ObservationFrequency.IRREGULAR,
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.net_lending",
        title="Federal net lending or borrowing",
        definition=(
            "The federal government's net lending (positive) or net borrowing "
            "(negative) in the national income and product accounts, quarterly "
            "at an annual rate, in dollars."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="current US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=_SAAR,
        candidates=(
            Candidate(provider="bea", series="NIPA/T30200/Q/49", note=_BEA_NOTE),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.interest_payments",
        title="Federal interest payments",
        definition=(
            "Interest the federal government pays, in the national income and "
            "product accounts, quarterly at an annual rate, in dollars."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="current US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=_SAAR,
        candidates=(
            Candidate(provider="bea", series="NIPA/T30200/Q/33", note=_BEA_NOTE),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.primary_balance",
        title="Federal primary balance",
        definition=(
            "Federal net lending or borrowing before interest: net lending plus "
            "interest payments, quarterly at an annual rate, in dollars. A "
            "deficit is negative."
        ),
        unit_kind=UnitKind.MONEY,
        unit_text="current US dollars per year",
        frequency=_QUARTERLY,
        seasonal_adjustment=_SAAR,
        candidates=(
            Derived(
                operands=(
                    Operand("us.fiscal.net_lending"),
                    Operand("us.fiscal.interest_payments"),
                ),
                transform="add",
            ),
        ),
        section=_SECTION,
    ),
    Concept(
        id="us.fiscal.primary_balance_to_gdp",
        title="Federal primary balance to GDP",
        definition=(
            "The federal primary balance over nominal GDP, both quarterly at an "
            "annual rate, as a ratio (-0.03 is a primary deficit of 3% of GDP), "
            "quarterly: the primary balance the debt-dynamics identity reads."
        ),
        unit_kind=UnitKind.RATIO,
        unit_text="ratio of the primary balance to annual GDP (-0.03 is -3%)",
        frequency=_QUARTERLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Derived(
                operands=(
                    Operand("us.fiscal.primary_balance"),
                    Operand("us.output.nominal_gdp"),
                ),
                transform="ratio",
                note=(
                    "BEA's primary balance over BEA's nominal GDP, both at annual "
                    "rates: originators, so hosted mode can compute it."
                ),
            ),
        ),
        section=_SECTION,
    ),
)
