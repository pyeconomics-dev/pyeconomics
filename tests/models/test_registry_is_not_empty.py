# tests/models/test_registry_is_not_empty.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The installed registry holds the catalog, so the suites over it check something.

The golden harness and the contract suite parametrize over the installed
registry. If discovery found nothing (a missing entry point, a broken install),
they would collect no case and pass. This test makes an empty registry fail, and
pins the domains Phase 2 Steps 6, 8 and 9 registered.
"""

from __future__ import annotations

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
CATALOG = FOUNDATIONS | FIXED_INCOME | DERIVATIVES | INTERNATIONAL


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
