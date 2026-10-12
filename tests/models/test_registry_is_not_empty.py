# tests/models/test_registry_is_not_empty.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The installed registry holds the catalog, so the suites over it check something.

The golden harness and the contract suite parametrize over the installed
registry. If discovery found nothing (a missing entry point, a broken install),
they would collect no case and pass. This test makes an empty registry fail,
pins the domains Phase 2 Steps 6 and 8 to 12 registered, and holds the registry
to exactly the 32 ids of the Phase 2 roadmap's launch-catalog table (a later
phase replaces "exactly" with "at least").
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from pyeconomics import registry
from pyeconomics.core import ENTRY_POINT_GROUP
from pyeconomics.core.registry import installed

FOUNDATIONS = {
    "foundations.hypothesis_tests",
    "foundations.returns",
    "foundations.risk_statistics",
    "foundations.simulation",
    "foundations.time_value",
}
FIXED_INCOME = {
    "fixed_income.bond_pricing",
    "fixed_income.convexity",
    "fixed_income.credit_spread",
    "fixed_income.curve_bootstrap",
    "fixed_income.duration",
    "fixed_income.money_market",
}
DERIVATIVES = {
    "derivatives.binomial_tree",
    "derivatives.black_scholes_merton",
    "derivatives.forwards",
    "derivatives.futures_fx_options",
    "derivatives.interest_rate_swap",
}
INTERNATIONAL = {"international.parity_conditions"}
EQUITY = {"equity.dividend_discount", "equity.free_cash_flow"}
CORPORATE = {
    "corporate.cost_of_capital",
    "corporate.capital_budgeting",
    "corporate.leverage",
}
ACCOUNTING = {"accounting.financial_ratios", "accounting.scoring_models"}
PORTFOLIO = {"portfolio.mean_variance", "portfolio.utility"}
PERFORMANCE = {
    "performance.brinson_attribution",
    "performance.return_measurement",
    "performance.risk_adjusted",
}
RISK = {"risk.value_at_risk", "risk.var_backtest"}
ECONOMETRICS = {"econometrics.ols"}
CATALOG = (
    FOUNDATIONS
    | FIXED_INCOME
    | DERIVATIVES
    | INTERNATIONAL
    | EQUITY
    | CORPORATE
    | ACCOUNTING
    | PORTFOLIO
    | PERFORMANCE
    | RISK
    | ECONOMETRICS
)

ROADMAP = (
    Path(__file__).resolve().parents[2] / "docs" / "roadmap" / "phase02-roadmap.md"
)
#: A row of the launch-catalog table: | 30 | `risk.value_at_risk` | ... |
CATALOG_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`([a-z_]+\.[a-z_]+)`\s*\|", re.MULTILINE)


def launch_catalog() -> set[str]:
    """Read the ids from the Phase 2 roadmap's launch-catalog table."""
    return set(CATALOG_ROW.findall(ROADMAP.read_text(encoding="utf-8")))


def test_the_registry_is_not_empty() -> None:
    assert registry.models(), (
        f"no model is registered; is the package installed with its "
        f"{ENTRY_POINT_GROUP!r} entry points?"
    )


def test_the_foundations_entry_point_registers_its_five_models() -> None:
    assert {m.id for m in registry.models("foundations")} == FOUNDATIONS
    assert "foundations" in registry.domains()


def test_the_fixed_income_entry_point_registers_its_six_models() -> None:
    assert {m.id for m in registry.models("fixed_income")} == FIXED_INCOME
    assert "fixed_income" in registry.domains()


def test_the_derivatives_entry_point_registers_its_five_models() -> None:
    assert {m.id for m in registry.models("derivatives")} == DERIVATIVES
    assert "derivatives" in registry.domains()


def test_the_international_entry_point_registers_its_model() -> None:
    assert {m.id for m in registry.models("international")} == INTERNATIONAL
    assert "international" in registry.domains()


def test_each_catalog_model_comes_from_this_distribution() -> None:
    for registration in installed().registrations:
        if registration.model.id in CATALOG:
            assert registration.provider.name == "pyeconomics"


@pytest.mark.parametrize(
    ("domain", "expected"),
    [("equity", EQUITY), ("corporate", CORPORATE), ("accounting", ACCOUNTING)],
)
def test_step10_domains_are_installed(domain: str, expected: set[str]) -> None:
    assert {m.id for m in registry.models(domain)} == expected


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ("portfolio", PORTFOLIO),
        ("performance", PERFORMANCE),
        ("risk", RISK),
        ("econometrics", ECONOMETRICS),
    ],
)
def test_step11_and_step12_domains_are_installed(
    domain: str, expected: set[str]
) -> None:
    assert {m.id for m in registry.models(domain)} == expected


def test_the_roadmap_table_lists_32_entries() -> None:
    assert len(launch_catalog()) == 32
    assert launch_catalog() == CATALOG


def test_the_registry_holds_exactly_the_launch_catalog() -> None:
    assert {m.id for m in registry.models()} == launch_catalog()
