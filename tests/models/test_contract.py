# tests/models/test_contract.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every registered model keeps the contract in ``tests/contract.py``.

For inputs generated from each model's fields, a run stays within its output
bounds, returns finite numbers or a documented ``None``, raises only the
documented errors, repeats itself exactly and survives a round trip through its
canonical JSON. The inputs per model are bounded by its cost class.

``test_contract_rules.py`` holds the checks themselves to account with toy
models, and ``test_registry_is_not_empty.py`` fails if discovery finds nothing
to parametrize over.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import contract
import pytest
from extra_gaps import excluded_gap

from pyeconomics.core.registry import installed

if TYPE_CHECKING:
    from pyeconomics.core import Model

MODELS = installed().models()


@pytest.mark.parametrize("model", [pytest.param(m, id=m.id) for m in MODELS])
def test_the_model_keeps_the_contract(model: Model[Any, Any]) -> None:
    # A model whose extra leaves its library out of this Python names the gap
    # (the Wheel rule); excluded_gap asserts that, and there is nothing to fuzz.
    if excluded_gap(model) is None:
        contract.check_model(model)
