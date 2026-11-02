# tests/web/test_mcp_snippet.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/web/mcp_snippet.py, which runs the calculators' MCP snippets."""

from __future__ import annotations

import importlib.util
import io
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from server_support import LOOPBACK_ONLY

import pyeconomics

if TYPE_CHECKING:
    from types import ModuleType

    import pytest

pytestmark = LOOPBACK_ONLY

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "web" / "mcp_snippet.py"
INPUTS = {
    "calculation": "macaulay_modified",
    "settlement": "2026-01-15",
    "maturity": "2036-01-15",
    "coupon_rate": 0.045,
    "yield_to_maturity": 0.045,
}


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("mcp_snippet", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


snippet = load_script()


def test_each_call_answers_its_text_block_and_an_error_its_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = [
        {
            "name": "run_model",
            "arguments": {"model_id": "fixed_income.duration", "inputs": INPUTS},
        },
        {"name": "run_model", "arguments": {"model_id": "no.such_model", "inputs": {}}},
    ]
    written = io.BytesIO()
    monkeypatch.setattr(
        sys, "stdin", io.TextIOWrapper(io.BytesIO(json.dumps(calls).encode()))
    )
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(written, encoding="utf-8"))
    assert snippet.main() == 0
    first, second = json.loads(written.getvalue())
    assert first == pyeconomics.run("fixed_income.duration", INPUTS).to_json()
    assert json.loads(second["error"])["type"].endswith("/model-not-found")
