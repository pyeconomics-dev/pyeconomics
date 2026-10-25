# tests/checks/test_client_scripts.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/clients, which ci.yml's clients job runs (Phase 4 Step 7).

``retitle_openapi.py`` must make every component title unique and change nothing
else; ``compare_runs.py`` must accept only the Python API's bytes. The generated
clients themselves run in the clients job, against a local server.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pyeconomics
from pyeconomics.server.openapi import openapi_document

if TYPE_CHECKING:
    from types import ModuleType

CLIENTS = Path(__file__).resolve().parents[2] / "scripts" / "clients"


def load(name: str) -> ModuleType:
    path = CLIENTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"clients_{name}", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


retitle_openapi = load("retitle_openapi")
python_smoke = load("python_smoke")


def test_every_component_gets_a_unique_title_and_nothing_else_changes() -> None:
    document = openapi_document()
    retitled = retitle_openapi.retitle(document)
    schemas = retitled["components"]["schemas"]
    titles = [schema["title"] for schema in schemas.values()]
    assert len(set(titles)) == len(titles) == len(schemas)
    assert schemas["fixed_income.duration.input.EffectiveInputs"]["title"] == (
        "FixedIncomeDurationInputEffectiveInputs"
    )
    for name, schema in schemas.items():
        original = dict(document["components"]["schemas"][name])
        original.pop("title", None)
        assert {k: v for k, v in schema.items() if k != "title"} == original
    assert {k: v for k, v in retitled.items() if k != "components"} == {
        k: v for k, v in document.items() if k != "components"
    }
    assert "title" not in document["components"]["schemas"]["Problem"]  # a copy


def test_the_command_writes_the_retitled_document(tmp_path: Path) -> None:
    source, target = tmp_path / "openapi.json", tmp_path / "titled.json"
    source.write_text(
        json.dumps({"components": {"schemas": {"a.b_c": {"type": "object"}}}}),
        encoding="utf-8",
    )
    assert retitle_openapi.main([str(source), str(target)]) == 0
    written = json.loads(target.read_text(encoding="utf-8"))
    assert written["components"]["schemas"]["a.b_c"] == {
        "title": "ABC",
        "type": "object",
    }
    assert retitle_openapi.main([]) == 2


def test_only_the_python_apis_bytes_compare_equal(tmp_path: Path) -> None:
    sys.path.insert(0, str(CLIENTS))  # compare_runs imports python_smoke's inputs
    try:
        compare_runs = load("compare_runs")
    finally:
        sys.path.remove(str(CLIENTS))
    expected = pyeconomics.run(compare_runs.MODEL, python_smoke.INPUTS).to_json()
    right, wrong = tmp_path / "ts-run.json", tmp_path / "py-run.json"
    right.write_bytes(expected.encode())
    wrong.write_bytes(expected.encode() + b"\n")
    assert compare_runs.main([str(right)]) == 0
    assert compare_runs.main([str(right), str(wrong)]) == 1
    assert compare_runs.differing([right, wrong], expected.encode()) == ["py-run.json"]
    assert compare_runs.main([]) == 2
