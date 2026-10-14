# src/pyeconomics/models/corporate/capital_budgeting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Project appraisal of periodic signed cash flows, first at time zero.

PI is PV of all positive flows divided by minus PV of all negative flows at
the discount rate. This generalizes the usual initial-outlay PI. Payback is
the first cumulative crossing of zero, interpolated linearly within a period;
it does not promise that later outlays will keep the balance positive.
"""

from __future__ import annotations

import math
from typing import Annotated

from pydantic import Field

from pyeconomics.core import (
    ChangelogEntry,
    CostClass,
    DomainError,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Money,
    Periods,
    Rate,
    Ratio,
    Reference,
    annuity_factor,
    internal_rate_of_return,
    model,
    present_value,
    warn,
)
from pyeconomics.core.model import ARRAY_INPUT
from pyeconomics.models.corporate._common import divide, optional

__all__ = ["capital_budgeting"]

MONEY_LIMIT = 1e15

CashFlows = Annotated[
    tuple[Annotated[Money, Field(ge=-1e12, le=1e12)], ...], ARRAY_INPUT
]


class Inputs(ModelInputs):
    cash_flows: CashFlows = Field(
        min_length=2,
        max_length=1201,
        description=(
            "Signed project cash flows at t=0, 1, ...; negative means paid out"
        ),
    )
    rate: Rate = Field(ge=-0.99, le=1, description="Discount rate per period")
    finance_rate: Rate = Field(
        0,
        ge=-0.99,
        le=1,
        description="MIRR financing rate per period for negative flows",
    )
    reinvestment_rate: Rate = Field(
        0,
        ge=-0.99,
        le=1,
        description="MIRR reinvestment rate per period for positive flows",
    )


class Outputs(ModelOutputs):
    npv: Money = Field(
        ge=-1e15, le=1e15, description="NPV including the undiscounted t=0 flow"
    )
    irr: Rate | None = Field(
        ge=-0.99, le=10, description="Smallest IRR in [-0.99, 10], or null with warning"
    )
    mirr: Rate | None = Field(
        ge=-0.99, le=10, description="Modified IRR per period, or null with warning"
    )
    payback: Periods | None = Field(
        ge=0,
        le=1200,
        description=(
            "First nominal cumulative recovery time, fractional periods; "
            "null if never reached"
        ),
    )
    discounted_payback: Periods | None = Field(
        ge=0,
        le=1200,
        description="First discounted cumulative recovery time, fractional periods",
    )
    profitability_index: Ratio | None = Field(
        ge=0, le=1e6, description="PV of positive flows / absolute PV of negative flows"
    )
    equivalent_annual_annuity: Money | None = Field(
        ge=-1e15,
        le=1e15,
        description=(
            "NPV / annuity factor over the project's periods; annual only "
            "when periods are years"
        ),
    )


def _payback(flows: tuple[float, ...], name: str) -> float | None:
    if flows[0] >= 0:
        return 0.0
    balance = flows[0]
    for t, flow in enumerate(flows[1:], start=1):
        if flow >= -balance:
            return (t - 1) + (-balance / flow)
        balance += flow
    warn("never_paid_back", f"{name} never recovers the initial outlay")
    return None


def _log_sum(terms: list[float]) -> float:
    peak = max(terms)
    return peak + math.log(math.fsum(math.exp(t - peak) for t in terms))


def _mirr(inputs: Inputs) -> float | None:
    n = len(inputs.cash_flows) - 1
    positives = [
        math.log(c) + (n - t) * math.log1p(inputs.reinvestment_rate)
        for t, c in enumerate(inputs.cash_flows)
        if c > 0
    ]
    negatives = [
        math.log(-c) - t * math.log1p(inputs.finance_rate)
        for t, c in enumerate(inputs.cash_flows)
        if c < 0
    ]
    if not positives or not negatives:
        warn("mirr_missing_sign", "MIRR needs both positive and negative cash flows")
        return None
    exponent = (_log_sum(positives) - _log_sum(negatives)) / n
    # Logs of differently scaled flows lose a few ulps on subtraction.
    # Permit only that rounding error before clamping to the declared endpoints.
    log_slack = 1e-12
    if exponent < math.log(0.01) - log_slack or exponent > math.log(11) + log_slack:
        warn("unrepresentable_result", "MIRR is outside [-0.99, 10]")
        return None
    return min(10.0, max(-0.99, math.expm1(exponent)))


@model(
    id="corporate.capital_budgeting",
    version=2,
    title="Capital budgeting",
    summary=(
        "Project NPV, IRR, MIRR, fractional payback, profitability "
        "index and equivalent annual annuity."
    ),
    formula=(
        r"NPV=\sum_{t=0}^n C_t/(1+r)^t",
        r"MIRR=(FV(C^+,r_R)/[-PV(C^-,r_F)])^{1/n}-1",
        r"PI=PV(C^+)/[-PV(C^-)]",
        r"EAA=NPV/a(r,n)",
    ),
    assumptions=(
        (
            "Signed cash flows are equally spaced, first at time zero. "
            "Rates are decimals per period."
        ),
        (
            "Payback interpolates the first cumulative recovery; positive "
            "t=0 flow gives payback zero."
        ),
        ("PI discounts all inflows and all outflows, not just the initial outlay."),
    ),
    limitations=(
        (
            "NPV outside +/-1e15 raises DomainError. IRR follows core's "
            "sign-change scan and smallest-root policy, which can miss "
            "tangent or closely spaced roots."
        ),
        (
            "Undefined or unrepresentable partial outputs are null with "
            "warnings: no IRR, missing MIRR sign, no payback, zero PI "
            "denominator, or overflow. MIRR is limited to [-0.99, 10]."
        ),
        (
            "Discounted payback is not shorter for conventional cash "
            "flows at nonnegative discount rates; the MIRR interval "
            "identity assumes a single initial outlay and subsequent "
            "inflows."
        ),
    ),
    references=(
        Reference(
            key="mirr",
            citation="Microsoft. MIRR function.",
            url="https://support.microsoft.com/en-us/excel/functions/mirr-function",
            locator="Syntax and five-year example",
        ),
        Reference(
            key="kellison",
            citation=(
                "Kellison, S. G. (2009). The Theory of Interest, 3rd ed. McGraw-Hill."
            ),
            isbn="9780073382449",
            url="https://www.mheducation.com/highered/product/theory-interest-kellison.html",
            locator="Yield rates and investment appraisal",
        ),
    ),
    evidence=Evidence.STANDARD,
    cost=CostClass.LIGHT,
    invariants=(
        Invariant(
            id="npv_positive_iff_pi_above_one",
            statement=(
                "When PI exists, NPV is positive iff PI exceeds one (up to rounding)."
            ),
        ),
        Invariant(
            id="mirr_between_reinvestment_rate_and_irr",
            statement=(
                "For a single initial outlay then nonnegative inflows, MIRR "
                "lies between IRR and the reinvestment rate when both exist."
            ),
        ),
        Invariant(
            id="discounted_payback_not_shorter_than_payback",
            statement=(
                "For conventional flows and nonnegative discount rates, "
                "discounted payback is not shorter than nominal payback."
            ),
        ),
    ),
    examples=(
        Example(
            name="two_year_project",
            inputs={
                "cash_flows": [-100, 60, 60],
                "rate": 0.1,
                "finance_rate": 0.1,
                "reinvestment_rate": 0.1,
            },
        ),
    ),
    changelog=(
        ChangelogEntry(version=1, note="First version."),
        ChangelogEntry(
            version=2, note="Recognize IRR roots at inclusive bracket endpoints (#85)."
        ),
    ),
)
def capital_budgeting(inputs: Inputs) -> Outputs:
    """Appraise the project using the shared NPV and IRR numerics."""
    flows = inputs.cash_flows
    npv = present_value(inputs.rate, flows)
    if not math.isfinite(npv) or abs(npv) > MONEY_LIMIT:
        msg = "NPV is outside [-1e15, 1e15]"
        raise DomainError(msg)
    positive = present_value(inputs.rate, [max(c, 0.0) for c in flows])
    negative = -present_value(inputs.rate, [min(c, 0.0) for c in flows])
    discounted = tuple(
        present_value(inputs.rate, [c], [float(t)]) for t, c in enumerate(flows)
    )
    if all(math.isfinite(c) for c in discounted):
        discounted_payback = _payback(discounted, "discounted payback")
    else:
        warn("unrepresentable_result", "discounted cash flows overflow")
        discounted_payback = None
    eaa = npv / annuity_factor(inputs.rate, len(flows) - 1)
    return Outputs(
        npv=npv,
        irr=internal_rate_of_return(flows),
        mirr=_mirr(inputs),
        payback=_payback(flows, "payback"),
        discounted_payback=discounted_payback,
        profitability_index=divide(positive, negative, "profitability index"),
        equivalent_annual_annuity=optional(eaa, 1e15, "equivalent annual annuity"),
    )
