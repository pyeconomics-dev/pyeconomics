# src/pyeconomics/models/corporate/leverage.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Operating and financial leverage of a single-product firm.

DOL = contribution/EBIT; DFL = EBIT/(EBIT-interest); DTL = DOL*DFL.
At zero EBIT the factorization leaves DOL and DTL undefined; other measures
remain available. Breakeven quantities are continuous, before rounding up to
whole saleable units, so their unit marker is ratio rather than integer count.
"""

from __future__ import annotations

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
    Money,
    Ratio,
    Reference,
    model,
    warn,
)
from pyeconomics.models.corporate._common import divide

__all__ = ["leverage"]


class Inputs(ModelInputs):
    price: Money = Field(ge=0, le=1e6, description="Selling price per unit")
    variable_cost: Money = Field(ge=0, le=1e6, description="Variable cost per unit")
    fixed_costs: Money = Field(
        ge=0, le=1e12, description="Fixed operating costs per period"
    )
    interest: Money = Field(ge=0, le=1e12, description="Interest expense per period")
    quantity: Count = Field(ge=0, le=1e8, description="Units sold per period")


class Outputs(ModelOutputs):
    operating_income: Money = Field(ge=-1e15, le=1e15, description="EBIT = Q(P-v)-F")
    dol: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Degree of operating leverage"
    )
    dfl: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Degree of financial leverage"
    )
    dtl: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Degree of total leverage, DOL times DFL"
    )
    operating_breakeven: Ratio | None = Field(
        ge=-1e6, le=1e6, description="Continuous units for zero EBIT, F/(P-v)"
    )
    total_breakeven: Ratio | None = Field(
        ge=-1e6,
        le=1e6,
        description="Continuous units for zero pretax income, (F+I)/(P-v)",
    )


@model(
    id="corporate.leverage",
    version=1,
    title="Operating and financial leverage",
    summary=(
        "DOL, DFL, DTL and operating and total breakeven quantities for one product."
    ),
    formula=(
        r"EBIT=Q(P-v)-F",
        r"DOL=Q(P-v)/EBIT,\quad DFL=EBIT/(EBIT-I)",
        r"DTL=DOL\,DFL",
        r"Q_O=F/(P-v),\quad Q_T=(F+I)/(P-v)",
    ),
    assumptions=(
        (
            "Constant price, unit variable cost, fixed costs and "
            "interest, in one currency and period."
        ),
        (
            "Breakeven quantities are continuous algebraic solutions; "
            "negative solutions need not be feasible sales volumes."
        ),
    ),
    limitations=(
        (
            "DOL and DTL are null at zero EBIT; DFL and DTL are null at "
            "zero pretax income. Zero unit contribution makes breakeven "
            "quantities null, with warnings."
        ),
        (
            "A ratio outside +/-1e6 is null with a warning. Above-one DOL "
            "requires positive EBIT and nonnegative fixed costs; it is "
            "strictly above one only for positive fixed costs."
        ),
    ),
    references=(
        Reference(
            key="damodaran",
            citation=(
                "Damodaran, A. (2014). Applied Corporate Finance, 4th ed. Wiley."
            ),
            isbn="9781118808931",
            url="https://www.stern.nyu.edu/~adamodar/pdfiles/acf4E/acf4Ebook.pdf",
            locator="Operating and financial leverage",
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.INSTANT,
    invariants=(
        Invariant(
            id="dtl_equals_dol_times_dfl",
            statement="When defined, DTL equals DOL times DFL.",
        ),
        Invariant(
            id="dol_above_one_with_fixed_costs",
            statement=(
                "DOL is at least one for positive EBIT and nonnegative fixed "
                "costs, strictly above one for positive fixed costs in exact "
                "arithmetic."
            ),
        ),
    ),
    examples=(
        Example(
            name="profitable_product",
            inputs={
                "price": 20,
                "variable_cost": 10,
                "fixed_costs": 100,
                "interest": 20,
                "quantity": 30,
            },
        ),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def leverage(inputs: Inputs) -> Outputs:
    """Return each defined measure, collecting warnings for the others."""
    margin = inputs.price - inputs.variable_cost
    contribution = inputs.quantity * margin
    ebit = contribution - inputs.fixed_costs
    dol = divide(contribution, ebit, "DOL")
    dfl = divide(ebit, ebit - inputs.interest, "DFL")
    if ebit == 0:
        warn("zero_operating_income", "DTL's DOL factor is undefined at zero EBIT")
        dtl = None
    else:
        dtl = divide(contribution, ebit - inputs.interest, "DTL")
    return Outputs(
        operating_income=ebit,
        dol=dol,
        dfl=dfl,
        dtl=dtl,
        operating_breakeven=divide(inputs.fixed_costs, margin, "operating breakeven"),
        total_breakeven=divide(
            inputs.fixed_costs + inputs.interest, margin, "total breakeven"
        ),
    )
