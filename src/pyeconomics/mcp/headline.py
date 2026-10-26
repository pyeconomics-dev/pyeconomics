# src/pyeconomics/mcp/headline.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The headline tools: the models the MCP server offers as tools of their own.

Every model is reachable through the discovery tools (``search_models``,
``describe_model``, ``run_model``). These few, widely used across ten domains,
also get a tool each, named ``<domain>_<name>`` from the id, whose input schema
is the model's own (ADR-0012 decision 13). The tuple is data, approved by the
maintainer in Phase 4 Step 8: no other module of the server names a model, and a
model joins it only through a reviewed change here (the Generator rule).
"""

from __future__ import annotations

from typing import Final

__all__ = ["HEADLINE"]

#: The ids of the models with a tool of their own, sorted.
HEADLINE: Final[tuple[str, ...]] = (
    "corporate.capital_budgeting",
    "corporate.cost_of_capital",
    "derivatives.binomial_tree",
    "derivatives.black_scholes_merton",
    "equity.dividend_discount",
    "equity.free_cash_flow",
    "fixed_income.bond_pricing",
    "fixed_income.curve_bootstrap",
    "fixed_income.duration",
    "foundations.returns",
    "foundations.time_value",
    "international.parity_conditions",
    "macro.policy_rule",
    "performance.risk_adjusted",
    "portfolio.mean_variance",
    "risk.value_at_risk",
)
