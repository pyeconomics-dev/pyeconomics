# tests/checks/test_coverage_floors.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/coverage_floors.py, the per-package coverage floors."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "checks" / "coverage_floors.py"
CORE = "src/pyeconomics/core/units.py"
MODELS = "src/pyeconomics/models/foundations/npv.py"
DATA = "src/pyeconomics/data/types.py"
SURFACES = "src/pyeconomics/surfaces/codec.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("coverage_floors_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


floors = load_script()


def entry(
    statements: int, covered: int, branches: int = 0, covered_branches: int = 0
) -> dict[str, Any]:
    return {
        "summary": {
            "num_statements": statements,
            "covered_lines": covered,
            "num_branches": branches,
            "covered_branches": covered_branches,
        }
    }


def write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "coverage.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def run(
    tmp_path: Path, data: object, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str, str]:
    code = floors.main(["coverage_floors.py", str(write(tmp_path, data))])
    captured = capsys.readouterr()
    return code, captured.out, captured.err


# --- the floors ---------------------------------------------------------------


def test_the_floors_are_95_on_core_90_on_models_and_95_on_data_and_surfaces() -> None:
    assert {name: floor for name, _, floor in floors.FLOORS} == {
        "core": 95.0,
        "models": 90.0,
        "data": 95.0,
        "surfaces": 95.0,
    }


def test_full_coverage_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {
        "files": {
            CORE: entry(100, 100, 20, 20),
            MODELS: entry(50, 50, 10, 10),
            DATA: entry(30, 30, 10, 10),
            SURFACES: entry(20, 20, 4, 4),
        }
    }
    code, out, err = run(tmp_path, data, capsys)
    assert code == 0
    assert "core: 100.00% of 120 (floor 95%) ok" in out
    assert "models: 100.00% of 60 (floor 90%) ok" in out
    assert "data: 100.00% of 40 (floor 95%) ok" in out
    assert "surfaces: 100.00% of 24 (floor 95%) ok" in out
    assert err == ""


def test_surfaces_below_95_fails_though_the_rest_is_fine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {
        CORE: entry(10, 10),
        MODELS: entry(10, 10),
        DATA: entry(10, 10),
        SURFACES: entry(100, 94),
    }
    code, out, err = run(tmp_path, {"files": files}, capsys)
    assert code == 1
    assert "surfaces coverage is 94.00%, below its 95% floor" in err
    assert "surfaces: 94.00% of 100 (floor 95%) BELOW THE FLOOR" in out


def test_surfaces_with_no_files_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {CORE: entry(10, 10), MODELS: entry(10, 10), DATA: entry(10, 10)}
    code, out, err = run(tmp_path, {"files": files}, capsys)
    assert code == 1
    assert "surfaces: no measured statements (0 file(s))" in out
    assert "surfaces has no measured statements" in err


def test_core_below_95_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {
        "files": {
            CORE: entry(100, 94, 0, 0),
            MODELS: entry(50, 50),
            DATA: entry(1, 1),
            SURFACES: entry(1, 1),
        }
    }
    code, out, err = run(tmp_path, data, capsys)
    assert code == 1
    assert "core coverage is 94.00%, below its 95% floor" in err
    assert "BELOW THE FLOOR" in out
    assert "models" not in err


def test_models_below_90_fails_though_core_is_fine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {
        "files": {
            CORE: entry(100, 100),
            MODELS: entry(100, 89),
            DATA: entry(1, 1),
            SURFACES: entry(1, 1),
        }
    }
    code, _, err = run(tmp_path, data, capsys)
    assert code == 1
    assert "models coverage is 89.00%, below its 90% floor" in err
    assert "core" not in err


def test_both_below_their_floors_reports_both(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {"files": {CORE: entry(100, 10), MODELS: entry(100, 10)}}
    code, _, err = run(tmp_path, data, capsys)
    assert code == 1
    assert "core coverage" in err
    assert "models coverage" in err


@pytest.mark.parametrize(
    ("covered", "expected"), [(95, 0), (94, 1)], ids=["at-the-floor", "just-under"]
)
def test_the_floor_itself_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], covered: int, expected: int
) -> None:
    data = {
        "files": {
            CORE: entry(100, covered),
            MODELS: entry(10, 10),
            DATA: entry(1, 1),
            SURFACES: entry(1, 1),
        }
    }
    code, _, _ = run(tmp_path, data, capsys)
    assert code == expected


def test_branches_count_with_statements(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    # All 90 statements run, but only 4 of 10 branches: (90 + 4) / 100 = 94%.
    data = {
        "files": {
            CORE: entry(90, 90, 10, 4),
            MODELS: entry(10, 10),
            DATA: entry(1, 1),
            SURFACES: entry(1, 1),
        }
    }
    code, out, _ = run(tmp_path, data, capsys)
    assert code == 1
    assert "core: 94.00% of 100" in out


def test_files_of_a_package_are_pooled(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {
        "files": {
            "src/pyeconomics/core/a.py": entry(900, 900),
            "src/pyeconomics/core/b.py": entry(100, 50),
            MODELS: entry(10, 10),
            DATA: entry(10, 10),
            SURFACES: entry(10, 10),
        }
    }
    code, out, _ = run(tmp_path, data, capsys)
    assert code == 0
    assert "core: 95.00% of 1000" in out


def test_data_below_95_fails_though_core_and_models_are_fine(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {
        "files": {
            CORE: entry(100, 100),
            MODELS: entry(100, 100),
            DATA: entry(100, 94),
            SURFACES: entry(1, 1),
        }
    }
    code, out, err = run(tmp_path, data, capsys)
    assert code == 1
    assert "data coverage is 94.00%, below its 95% floor" in err
    assert "data: 94.00% of 100 (floor 95%) BELOW THE FLOOR" in out
    assert "core coverage" not in err
    assert "models coverage" not in err


# --- a package with nothing measured ------------------------------------------


def test_data_with_no_files_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {CORE: entry(10, 10), MODELS: entry(10, 10), SURFACES: entry(1, 1)}
    code, out, err = run(tmp_path, {"files": files}, capsys)
    assert code == 1
    assert "data: no measured statements (0 file(s))" in out
    assert "data has no measured statements" in err


def test_models_with_no_files_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {CORE: entry(10, 10), DATA: entry(10, 10), SURFACES: entry(10, 10)}
    code, out, err = run(tmp_path, {"files": files}, capsys)
    assert code == 1
    assert "models: no measured statements (0 file(s))" in out
    assert "models has no measured statements" in err
    assert "core" not in err


def test_models_with_only_a_docstring_module_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    init = "src/pyeconomics/models/__init__.py"
    data = {"files": {CORE: entry(10, 10, 0, 0), init: entry(0, 0, 0, 0)}}
    code, out, _ = run(tmp_path, data, capsys)
    assert code == 1
    assert "models: no measured statements (1 file(s))" in out


@pytest.mark.parametrize(
    "files",
    [{}, {"src/pyeconomics/core/x.py": entry(0, 0, 0, 0)}, {MODELS: entry(10, 10)}],
    ids=["empty-report", "no-statements", "paths-point-elsewhere"],
)
def test_core_with_nothing_measured_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, Any]
) -> None:
    code, out, err = run(tmp_path, {"files": files}, capsys)
    assert code == 1
    assert "core: no measured statements" in out
    assert "core has no measured statements" in err
    assert "source_pkgs" in err


# --- paths --------------------------------------------------------------------


@pytest.mark.parametrize(
    "name",
    [
        "src\\pyeconomics\\core\\units.py",
        "E:\\Code\\Python\\pyeconomics\\src\\pyeconomics\\core\\units.py",
        "/home/runner/work/pyeconomics/src/pyeconomics/core/units.py",
        "pyeconomics/core/units.py",
    ],
)
def test_windows_absolute_and_relative_paths_all_count(name: str) -> None:
    found = floors.totals({"files": {name: entry(10, 5)}}, "/pyeconomics/core/")
    assert found == (1, 5, 10)


@pytest.mark.parametrize(
    "name",
    [
        "src/pyeconomics/corex/units.py",
        "src/pyeconomics/models/core/x.py",
        "tests/core/test_units.py",
        "src/other/pyeconomics_core/units.py",
    ],
)
def test_other_paths_do_not_count(name: str) -> None:
    found = floors.totals({"files": {name: entry(10, 5)}}, "/pyeconomics/core/")
    assert found == (0, 0, 0)


# --- a report that cannot be trusted ------------------------------------------


def test_a_report_without_branch_data_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    data = {"files": {CORE: {"summary": {"num_statements": 10, "covered_lines": 10}}}}
    code, _, err = run(tmp_path, data, capsys)
    assert code == 2
    assert "no branch data" in err


def test_a_missing_report_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = floors.main(["coverage_floors.py", str(tmp_path / "absent.json")])
    assert code == 2
    assert "cannot read" in capsys.readouterr().err


def test_a_report_that_is_not_json_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "coverage.json"
    path.write_text("<coverage/>", encoding="utf-8")
    assert floors.main(["coverage_floors.py", str(path)]) == 2
    assert "not a JSON report" in capsys.readouterr().err


@pytest.mark.parametrize("data", [[], {"meta": {}}, {"files": []}])
def test_a_json_file_that_is_not_a_coverage_report_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], data: object
) -> None:
    code, _, err = run(tmp_path, data, capsys)
    assert code == 2
    assert "not a `coverage json` report" in err


def test_the_default_report_is_coverage_json_in_the_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    write(
        tmp_path,
        {
            "files": {
                CORE: entry(10, 10),
                MODELS: entry(10, 10),
                DATA: entry(10, 10),
                SURFACES: entry(10, 10),
            }
        },
    )
    monkeypatch.chdir(tmp_path)
    assert floors.main(["coverage_floors.py"]) == 0
    assert "core: 100.00%" in capsys.readouterr().out
