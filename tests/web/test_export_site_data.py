# tests/web/test_export_site_data.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/web/export_site_data.py, the data the web app builds from."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pyeconomics import registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import MissingOptionalDependencyError, RegistryError
from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.mcp.headline import HEADLINE
from pyeconomics.surfaces.budgets import local_command
from pyeconomics.surfaces.problem_guide import EXIT_CODES, GUIDES
from pyeconomics.surfaces.problems import ROWS

if TYPE_CHECKING:
    from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "web" / "export_site_data.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("export_site_data", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


export = load_script()


def read(path: Path) -> dict[str, Any]:
    document: dict[str, Any] = json.loads(path.read_bytes())
    return document


def test_the_default_output_is_the_web_apps_generated_directory() -> None:
    assert export.DEFAULT_OUT == export.ROOT / "web" / "src" / "data" / "generated"


def test_problems_hold_every_row_in_table_order() -> None:
    document = export.problems_document()
    assert document["format"] == export.SITE_DATA_FORMAT
    assert [p["slug"] for p in document["problems"]] == [row.slug for row in ROWS]
    first = document["problems"][0]
    assert first == {
        "slug": "invalid-input",
        "title": ROWS[0].title,
        "status": 422,
        "exit_code": 3,
        "type": "https://pyeconomics.dev/problems/invalid-input",
        "error": "InputError",
        "meaning": GUIDES["invalid-input"].meaning,
        "action": GUIDES["invalid-input"].action,
        "local_command": None,
    }
    budget = next(p for p in document["problems"] if p["slug"] == "budget-exceeded")
    assert budget["local_command"] == local_command("<model-id>")
    assert document["exit_codes"] == {str(k): v for k, v in EXIT_CODES.items()}


def test_sources_come_from_metadata_without_a_key_or_a_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_DISABLED_PROVIDERS", "fred")
    document = export.sources_document()
    ids = [source["id"] for source in document["sources"]]
    infos = provider_registry.installed().infos()
    assert ids == sorted(info.id for info in infos)
    fred = next(s for s in document["sources"] if s["id"] == "fred")
    assert fred["licence"] == "library-only"
    assert fred["hosted"] is False
    assert fred["terms_url"].startswith("https://")
    assert fred["notice"]
    assert fred["key_variable"] == "FRED_API_KEY"
    for source in document["sources"]:
        assert set(source) == {
            "id",
            "name",
            "licence",
            "hosted",
            "terms_url",
            "terms_checked",
            "attribution",
            "notice",
            "llm_use",
            "storage",
            "key_variable",
            "key_required",
            "extra",
        }


def test_concepts_carry_candidates_and_hosted_availability() -> None:
    document = export.concepts_document()
    concepts = document["concepts"]
    assert [c["id"] for c in concepts] == sorted(c.id for c in catalog.concepts())
    treasury = next(c for c in concepts if c["id"] == "us.treasury.nominal_10y")
    assert [c["provider"] for c in treasury["candidates"]] == ["treasury", "fred"]
    assert treasury["hosted"] is True
    for concept in concepts:
        assert concept["hosted"] is any(c["hosted"] for c in concept["candidates"])


def test_surfaces_name_each_models_route_tool_and_command() -> None:
    openapi: dict[str, Any] = {
        "paths": {
            f"/v1/models/{i}/run": {"get": {}, "post": {}} for i in registry.ids()
        }
    }
    document = export.surfaces_document(openapi)
    models = {entry["id"]: entry for entry in document["models"]}
    assert list(models) == sorted(registry.ids())
    assert models["fixed_income.duration"] == {
        "id": "fixed_income.duration",
        "rest": "/v1/models/fixed_income.duration/run",
        "methods": ["GET", "POST"],
        "mcp_tool": "fixed_income_duration",
        "cli": "pyeconomics models run fixed_income.duration",
    }
    assert {i for i, m in models.items() if m["mcp_tool"]} == set(HEADLINE)


def test_surfaces_refuse_a_model_with_no_run_route() -> None:
    with pytest.raises(RegistryError, match="has no run route"):
        export.surfaces_document({"paths": {}})


def test_documents_are_deterministic() -> None:
    for build in (
        export.problems_document,
        export.sources_document,
        export.concepts_document,
    ):
        assert canonical_json(build()) == canonical_json(build())


def test_write_site_data_writes_canonical_files_and_removes_stale_ones(
    tmp_path: Path,
) -> None:
    (tmp_path / "stale.json").write_text("{}")
    (tmp_path / "keep.txt").write_text("not ours")
    written = export.write_site_data(tmp_path, figures=False)
    assert [path.name for path in written] == list(export.FILES)
    assert not (tmp_path / "stale.json").exists()
    assert (tmp_path / "keep.txt").exists()
    for path in written:
        body = path.read_bytes()
        # A large whole-number double reads back as an int (core/canonical.py).
        assert body == canonical_json(json.loads(body, parse_int=float))
    document = read(tmp_path / "registry.json")
    assert [m["id"] for m in document["models"]] == [m.id for m in registry.models()]
    assert all(m["example_figure"] is None for m in document["models"])
    assert read(tmp_path / "openapi.json")["openapi"].startswith("3.1")
    surfaces = read(tmp_path / "surfaces.json")["models"]
    assert [m["id"] for m in surfaces] == [m.id for m in registry.models()]
    first = {path.name: path.read_bytes() for path in written}
    export.write_site_data(tmp_path, figures=False)
    assert {path.name: path.read_bytes() for path in written} == first


def test_main_names_the_missing_server_extra(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def missing(_out: Path) -> tuple[Path, ...]:
        package = "fastapi"
        raise MissingOptionalDependencyError(package, extra="server")

    monkeypatch.setattr(export, "write_site_data", missing)
    assert export.main(["--out", str(tmp_path)]) == 1
    assert "--all-extras" in capsys.readouterr().err


def test_main_prints_the_files_it_wrote(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        export, "write_site_data", lambda out: tuple(out / n for n in export.FILES)
    )
    assert export.main(["--out", str(tmp_path)]) == 0
    assert capsys.readouterr().out.splitlines() == [
        str(tmp_path / name) for name in export.FILES
    ]
