# tests/docs/test_in_browser.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The in-browser examples: what they run and everything they may fetch.

A browser proves each page in ci.yml's docs job (web/tests/wasm/). These tests
hold what that run cannot: that the notebooks stay data-free, that the lockfile
pins every file to a hash on the two hosts allowed, and that it stays in step with
the Pyodide the pyodide job proves, the wheel's floors and marimo.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

from pyeconomics import registry

if TYPE_CHECKING:
    from types import ModuleType

ROOT: Final = Path(__file__).resolve().parents[2]
WASM: Final = ROOT / "docs" / "wasm"
NOTEBOOKS: Final = sorted(WASM.glob("*.py"))
LOCKFILE: Final = WASM / "pyodide-lock.json"
SPEC: Final = ROOT / "web" / "tests" / "wasm" / "in-browser.spec.ts"
_MODEL: Final = re.compile(r'"((?:\w+\.)+\w+)",\s*(?:calculation|\*\*)')
#: The only imports a notebook needs, so nothing here can reach a network.
_ALLOWED_IMPORTS: Final = {"datetime", "json", "marimo", "pyeconomics"}


def _script(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        f"docs_{name}", ROOT / "scripts" / "docs" / f"{name}.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def export_wasm() -> ModuleType:
    return _script("export_wasm")


@pytest.fixture(scope="module")
def pyodide_version() -> str:
    return str(_script("pin_wasm").PYODIDE)


@pytest.fixture(scope="module")
def lock() -> dict[str, Any]:
    parsed: dict[str, Any] = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    return parsed


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _locked_version(name: str) -> str:
    uv_lock = tomllib.loads(_text(ROOT / "uv.lock"))
    versions: dict[str, str] = {
        package["name"]: package.get("version", "") for package in uv_lock["package"]
    }
    return versions[name]


def test_the_three_examples_are_the_ones_the_step_names() -> None:
    assert [path.stem for path in NOTEBOOKS] == [
        "bond_price_duration",
        "mean_variance_frontier",
        "time_value",
    ]


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_notebook_keeps_the_file_header_then_its_own(notebook: Path) -> None:
    lines = _text(notebook).splitlines()
    assert lines[0] == f"# {notebook.relative_to(ROOT).as_posix()}"
    assert lines[1].startswith("# Copyright ")
    assert lines[2] == "# SPDX-License-Identifier: Apache-2.0"
    assert lines[3] == "# /// script"


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_page_says_it_runs_in_the_browser_with_no_install(notebook: Path) -> None:
    text = " ".join(_text(notebook).split())
    assert "runs entirely in your browser and needs no install" in text
    assert "not investment advice" in text


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_notebook_pins_the_wheel_the_lockfile_holds(
    notebook: Path, lock: dict[str, Any]
) -> None:
    version = lock["packages"]["pyeconomics"]["version"]
    assert f'# dependencies = ["pyeconomics=={version}"]\n' in _text(notebook)


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_notebook_was_written_for_the_locked_marimo(notebook: Path) -> None:
    version = _locked_version("marimo")
    assert f'__generated_with = "{version}"\n' in _text(notebook)


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_notebook_imports_nothing_that_reaches_a_network(notebook: Path) -> None:
    imported = set()
    for node in ast.walk(ast.parse(_text(notebook))):
        if isinstance(node, ast.Import):
            imported |= {alias.name.split(".")[0] for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").split(".")[0])
    assert imported <= _ALLOWED_IMPORTS


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_a_notebook_runs_only_models_that_need_no_data(notebook: Path) -> None:
    text = _text(notebook)
    models = _MODEL.findall(text)
    assert models
    assert not any(registry.get(model).spec.bindings for model in models)
    assert "pyeconomics.data" not in text
    assert "pyeconomics.bind" not in text
    assert re.search(r"api_key|token|password", text, re.IGNORECASE) is None


def test_every_file_is_pinned_by_hash_on_the_two_allowed_hosts(
    lock: dict[str, Any], pyodide_version: str
) -> None:
    allowed = (
        f"https://cdn.jsdelivr.net/pyodide/v{pyodide_version}/full/",
        "https://files.pythonhosted.org/packages/",
    )
    assert lock["packages"]
    for name, entry in lock["packages"].items():
        assert entry["file_name"].startswith(allowed), name
        assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"]), name


def test_the_pinned_wheel_is_in_the_lockfile_so_no_index_is_asked(
    lock: dict[str, Any],
) -> None:
    entry = lock["packages"]["pyeconomics"]
    assert f"pyeconomics-{entry['version']}-py3-none-any.whl" in entry["file_name"]


def test_every_dependency_of_a_locked_package_is_locked_too(
    lock: dict[str, Any],
) -> None:
    packages = lock["packages"]
    for name, entry in packages.items():
        depends = {canonicalize_name(depend) for depend in entry["depends"]}
        assert depends <= set(packages), name


def test_the_pin_script_refuses_a_lockfile_below_the_wheels_floors() -> None:
    # marimo's Pyodide 314.0.0 bundles SciPy 1.17, which the wheel's floor refuses,
    # and Pyodide would load it unchecked.
    floor = [Requirement("scipy>=1.18")]
    unmet = _script("pin_wasm").unmet
    assert unmet(floor, {"scipy": {"version": "1.17.1"}}) == ["scipy>=1.18"]
    assert unmet(floor, {"scipy": {"version": "1.18.0"}}) == []


def test_the_lockfile_holds_the_scipy_the_wheel_needs(lock: dict[str, Any]) -> None:
    assert (
        _script("pin_wasm").unmet([Requirement("scipy>=1.18")], lock["packages"]) == []
    )


def test_dependabot_leaves_marimo_alone() -> None:
    # A bump moves the notebooks and the lockfile with it, so it is done by hand.
    config = _text(ROOT / ".github" / "dependabot.yml")
    assert "dependency-name: marimo" in config


def test_the_runtime_is_the_one_the_pyodide_job_proves(
    lock: dict[str, Any], pyodide_version: str
) -> None:
    workflow = _text(ROOT / ".github" / "workflows" / "ci.yml")
    assert f'PYODIDE_VERSION: "{pyodide_version}"' in workflow
    assert lock["info"]["abi_version"] == "2026_0"


def test_the_locked_marimo_is_the_one_that_exports_the_pages(
    lock: dict[str, Any],
) -> None:
    assert lock["packages"]["marimo-base"]["version"] == _locked_version("marimo")


def test_the_export_points_a_page_at_the_lockfile(export_wasm: ModuleType) -> None:
    page = '<body><marimo-wasm hidden=""></marimo-wasm></body>'
    assert 'data-pyodide-lockfile-url="./pyodide-lock.json"' in export_wasm.pin(page)


def test_the_export_refuses_a_page_it_does_not_recognise(
    export_wasm: ModuleType,
) -> None:
    # A page left alone would ask wasm.marimo.app for its packages again.
    with pytest.raises(SystemExit, match="marimo-wasm"):
        export_wasm.pin("<body><marimo-wasm></marimo-wasm></body>")


@pytest.mark.parametrize("notebook", NOTEBOOKS, ids=lambda path: path.stem)
def test_each_page_is_listed_and_driven_by_the_browser_check(
    notebook: Path, export_wasm: ModuleType
) -> None:
    page = export_wasm.page_name(notebook)
    assert f'href="{page}"' in _text(WASM / "index.md")
    assert f'page: "{page}"' in _text(SPEC)


def test_a_page_is_one_file_so_a_reader_does_not_trip_the_hosts_rate_limit() -> None:
    # About 310 requests a page otherwise: Read the Docs answers 429, and a reader
    # sees an error page in place of the example.
    assert '"--single-file"' in _text(ROOT / "scripts" / "docs" / "export_wasm.py")
    assert "MOST_FROM_OWN_HOST" in _text(SPEC)


def test_the_docs_job_drives_the_examples_in_a_browser() -> None:
    workflow = _text(ROOT / ".github" / "workflows" / "ci.yml")
    assert "npm run e2e:wasm" in workflow


def test_the_new_tools_are_in_the_docs_group_only() -> None:
    project = tomllib.loads(_text(ROOT / "pyproject.toml"))
    groups = project["dependency-groups"]
    assert {"marimo", "sphinx-gallery"} <= {
        Requirement(line).name for line in groups["docs"]
    }
    runtime = [
        *project["project"]["dependencies"],
        *(
            line
            for extra in project["project"]["optional-dependencies"].values()
            for line in extra
        ),
        *(line for name, lines in groups.items() if name != "docs" for line in lines),
    ]
    named = {Requirement(line).name for line in runtime if isinstance(line, str)}
    assert not {"marimo", "sphinx-gallery"} & named
