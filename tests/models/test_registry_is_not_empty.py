# tests/models/test_registry_is_not_empty.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The installed registry holds the catalog, so the suites over it check something.

The golden harness and the contract suite parametrize over the installed
registry. If discovery found nothing (a missing entry point, a broken install),
they would collect no case and pass. This test makes an empty registry fail,
pins the domains Phase 2 Steps 6 and 8 to 12 registered, and holds the registry
to at least the 32 ids of the Phase 2 roadmap's launch-catalog table plus every
id of the Phase 3 table whose step has landed (its Status reads Complete), and
to no id outside the two tables (Phase 3 Step 13 narrowed "exactly the 32").
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

MACRO = {"macro.neutral_rate", "macro.policy_rule"}
ASSET_PRICING = {
    "asset_pricing.factor_model_tests",
    "asset_pricing.factor_regression",
}

ROADMAPS = Path(__file__).resolve().parents[2] / "docs" / "roadmap"
ROADMAP = ROADMAPS / "phase02-roadmap.md"
PHASE03 = ROADMAPS / "phase03-roadmap.md"
#: A row of the launch-catalog table: | 30 | `risk.value_at_risk` | ... |
CATALOG_ROW = re.compile(r"^\|\s*\d+\s*\|\s*`([a-z_]+\.[a-z_]+)`\s*\|", re.MULTILINE)
#: A row of Phase 3's table, ending in the step that lands it: | 33 | `id` | ... | 13 |
PHASE03_ROW = re.compile(
    r"^\|\s*\d+\s*\|\s*`([a-z_]+\.[a-z_]+)`\s*\|.*\|\s*(\d+)\s*\|\s*$", re.MULTILINE
)
#: A step heading and the Status line under it.
STEP_STATUS = re.compile(r"^## Step (\d+) — .*\n\n\*\*Status:\*\* (\S+)", re.MULTILINE)


def launch_catalog() -> set[str]:
    """Read the ids from the Phase 2 roadmap's launch-catalog table."""
    return set(CATALOG_ROW.findall(ROADMAP.read_text(encoding="utf-8")))


def phase03_catalog() -> dict[str, int]:
    """Read the Phase 3 table's ids, each with the step that lands it."""
    text = PHASE03.read_text(encoding="utf-8")
    return {model_id: int(step) for model_id, step in PHASE03_ROW.findall(text)}


def landed() -> set[str]:
    """The Phase 3 ids whose step reads Complete on this tree's roadmap."""
    text = PHASE03.read_text(encoding="utf-8")
    complete = {
        int(step) for step, status in STEP_STATUS.findall(text) if status == "Complete"
    }
    return {
        model_id for model_id, step in phase03_catalog().items() if step in complete
    }


def test_the_registry_is_not_empty() -> None:
    assert registry.models(), (
        f"no model is registered; is the package installed with its "
        f"{ENTRY_POINT_GROUP!r} entry points?"
    )


def test_the_foundations_entry_point_registers_its_five_models() -> None:
    assert {m.id for m in registry.models("foundations")} == FOUNDATIONS
    assert "foundations" in registry.domains()


def test_the_fixed_income_entry_point_registers_phase_2s_six_models() -> None:
    # At least: Phase 3 Step 15 adds two (the table below lists them).
    assert {m.id for m in registry.models("fixed_income")} >= FIXED_INCOME
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
    # At least: Phase 3 Step 15 adds two equity models (the table below lists them).
    assert {m.id for m in registry.models(domain)} >= expected


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
    found = {m.id for m in registry.models(domain)}
    # At least: Phase 3 Step 16 adds two portfolio models (the table below lists
    # them).
    assert found >= expected if domain == "portfolio" else found == expected


def test_the_asset_pricing_entry_point_registers_its_two_models() -> None:
    assert {m.id for m in registry.models("asset_pricing")} == ASSET_PRICING
    assert "asset_pricing" in registry.domains()


def test_the_macro_entry_point_registers_the_policy_suite() -> None:
    assert {m.id for m in registry.models("macro")} >= MACRO
    assert "macro" in registry.domains()


def test_the_roadmap_table_lists_32_entries() -> None:
    assert len(launch_catalog()) == 32
    assert launch_catalog() == CATALOG


def test_the_phase03_table_lists_18_new_entries() -> None:
    table = phase03_catalog()
    assert len(table) == 18
    assert not set(table) & launch_catalog()
    assert {model_id for model_id, step in table.items() if step == 13} == MACRO


def test_the_registry_holds_at_least_the_launch_catalog_and_what_has_landed() -> None:
    ids = {m.id for m in registry.models()}
    assert ids >= launch_catalog() | landed()
    assert ids <= launch_catalog() | set(phase03_catalog())
