# tests/cli/test_cli_every_model.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``models run`` over every registered model's first example (Phase 4 Step 4).

Each example's inputs go in as a file, and the command line must print the bytes
``pyeconomics.run`` gives for them, plus one newline. A model whose extra leaves
its package out of this Python (arch on CPython 3.15) must exit 8 naming that
extra, never pass silently (tests/extra_gaps.py).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from cli_support import cli
from extra_gaps import excluded_gap

import pyeconomics
from pyeconomics import registry
from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.parametrize("model_id", registry.ids())
def test_models_run_prints_the_first_examples_result(
    model_id: str, tmp_path: Path
) -> None:
    model = registry.get(model_id)
    inputs = model.spec.examples[0].inputs
    path = tmp_path / "inputs.json"
    path.write_bytes(canonical_json(inputs))
    outcome = cli("models", "run", model_id, "--inputs", str(path))
    gap = excluded_gap(model)
    if gap is not None:
        assert outcome.code == 8
        assert outcome.stderr.startswith("missing-extra: ")
        assert f"pyeconomics[{model.spec.extra}]" in outcome.stderr
        return
    assert (outcome.code, outcome.stderr) == (0, "")
    assert (
        outcome.stdout
        == pyeconomics.run(model_id, inputs).to_json().encode("utf-8") + b"\n"
    )
