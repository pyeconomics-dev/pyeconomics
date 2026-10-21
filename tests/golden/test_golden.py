# tests/golden/test_golden.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The golden harness over the installed registry (ROADMAP section 5).

From Phase 2 Step 6 on, a model cannot merge unless it has a golden file that
follows the rules in ``_loader.py`` (tests/golden/README.md) and every case in it
runs through ``pyeconomics.run`` within tolerance. ``test_harness.py`` holds the
rules themselves to account with toy models; this module applies them to the real
catalog.

``tests/models/test_registry_is_not_empty.py`` fails if discovery finds no model,
so this module can never pass by collecting nothing.
"""

from __future__ import annotations

import pytest
from _loader import Case, GoldenFile, audit, run_case
from extra_gaps import excluded_gap

import pyeconomics
from pyeconomics.core.registry import installed

REGISTRY = installed()
AUDIT = audit(REGISTRY)

CASES = [
    pytest.param(golden, case, id=f"{golden.model}::{case.id}")
    for golden in AUDIT.files
    for case in golden.cases
]


def test_every_golden_file_and_registered_model_follows_the_rules() -> None:
    assert not AUDIT.problems, "\n".join(AUDIT.problems)


@pytest.mark.parametrize(("golden", "case"), CASES)
def test_golden_case(golden: GoldenFile, case: Case) -> None:
    model = REGISTRY.get(golden.model)
    # Where the model's extra leaves its library out of this Python (the Wheel
    # rule), the case asserts the gap the model names instead.
    gap = excluded_gap(model)
    if gap is not None:
        assert gap.extra == model.spec.extra
        return
    mismatches = run_case(model, case, lambda m, inputs: pyeconomics.run(m.id, inputs))
    assert not mismatches, "\n".join(mismatches)
