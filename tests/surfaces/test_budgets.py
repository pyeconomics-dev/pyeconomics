# tests/surfaces/test_budgets.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The hosted budgets and size limits, as ADR-0012 decision 10 records them."""

from __future__ import annotations

import pytest

from pyeconomics.core import CostClass, PyeconomicsError
from pyeconomics.surfaces.budgets import (
    GET_INPUTS_LIMIT,
    HOSTED_BODY_LIMIT,
    HOSTED_BUDGETS,
    BudgetExceededError,
    budget_for,
)
from pyeconomics.surfaces.codec import MAX_INPUT_BYTES


def test_the_budgets_are_the_accepted_seconds_for_every_cost_class() -> None:
    assert dict(HOSTED_BUDGETS) == {
        CostClass.INSTANT: 2.0,
        CostClass.LIGHT: 10.0,
        CostClass.HEAVY: 30.0,
    }
    assert set(HOSTED_BUDGETS) == set(CostClass)
    assert budget_for(CostClass.HEAVY) == 30.0
    assert budget_for("instant") == 2.0  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]
    with pytest.raises(ValueError, match="free"):
        budget_for("free")  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


def test_the_size_limits() -> None:
    assert HOSTED_BODY_LIMIT == 1024 * 1024
    assert GET_INPUTS_LIMIT == 8 * 1024
    assert HOSTED_BODY_LIMIT < MAX_INPUT_BYTES


def test_a_budget_error_names_the_model_and_its_budget() -> None:
    error = BudgetExceededError("risk.toy", 10.0)
    assert isinstance(error, PyeconomicsError)
    assert (error.model_id, error.seconds) == ("risk.toy", 10.0)
    assert "10 s" in str(error)
    with pytest.raises(TypeError):
        HOSTED_BUDGETS[CostClass.HEAVY] = 60.0  # type: ignore[index] # ty: ignore[invalid-assignment]
