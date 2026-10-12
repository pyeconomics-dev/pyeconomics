# tests/checks/test_python_floor.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Offline checks using PyPI info fields recorded on 2026-10-12."""

from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.error import URLError

import pytest
from packaging.version import Version

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
RECORDED = {
    "numpy": {"info": {"version": "2.5.4", "requires_python": ">=3.12"}},
    "scipy": {"info": {"version": "1.18.1", "requires_python": ">=3.12"}},
}


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "python_floor_check", REPO / "scripts/checks/python_floor.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check = load_script()


@pytest.fixture
def recorded(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    seen: list[str] = []

    def open_recording(url: str, *, timeout: int) -> io.BytesIO:
        assert timeout == 30
        package = url.split("/")[-2]
        assert url == f"https://pypi.org/pypi/{package}/json"
        seen.append(package)
        return io.BytesIO(json.dumps(RECORDED[package]).encode())

    monkeypatch.setattr(check, "urlopen", open_recording)
    return seen


def project(tmp_path: Path, expression: str) -> Path:
    (tmp_path / "pyproject.toml").write_bytes(
        f'[project]\nrequires-python = "{expression}"\n'.encode()
    )
    return tmp_path


def test_recorded_live_responses(
    recorded: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert check.main(REPO) == 0
    assert recorded == ["numpy", "scipy"]
    output = capsys.readouterr().out
    assert "numpy 2.5.4: >=3.12" in output
    assert "scipy 1.18.1: >=3.12" in output
    assert "PASS" in output


@pytest.mark.parametrize("package", ["numpy", "scipy"])
def test_either_dependency_can_raise_floor(
    package: str,
    recorded: list[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setitem(
        RECORDED, package, {"info": {"version": "3.0.0", "requires_python": ">=3.13"}}
    )
    assert check.main(project(tmp_path, ">=3.12")) == 1
    assert recorded == ["numpy", "scipy"]
    error = capsys.readouterr().err
    assert "raise requires-python from >=3.12 to >=3.13" in error
    assert "CI matrix, Python classifiers and phase verification" in error


def test_higher_project_floor_passes(recorded: list[str], tmp_path: Path) -> None:
    assert check.main(project(tmp_path, ">=3.13")) == 0
    assert len(recorded) == 2


@pytest.mark.parametrize("expression", [">=3.12", ">=3.10,>=3.12,<4", "~=3.12"])
def test_inclusive_floor(expression: str) -> None:
    assert check.floor(expression) == Version("3.12")


@pytest.mark.parametrize(
    "expression",
    [
        "",
        "<4",
        ">3.12",
        "==3.12.*",
        ">=3.12,!=3.12.*",
        ">=3.12,<3.11",
        ">=3.13rc1",
        "bad",
    ],
)
def test_ambiguous_floor_fails(expression: str) -> None:
    with pytest.raises(ValueError, match=r"floor|bound|Invalid specifier"):
        check.floor(expression)


@pytest.mark.parametrize(
    "info",
    [
        {},
        {"version": "2.5.4", "requires_python": None},
        {"version": "3.0rc1", "requires_python": ">=3.13"},
    ],
)
def test_malformed_metadata_fails(
    info: dict[str, str | None], recorded: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(RECORDED, "numpy", {"info": info})
    assert check.main(REPO) == 1
    assert recorded == ["numpy"]


def test_timeout_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    def unavailable(_url: str, *, timeout: int) -> io.BytesIO:
        assert timeout > 0
        message = "timed out"
        raise URLError(message)

    monkeypatch.setattr(check, "urlopen", unavailable)
    assert check.main(REPO) == 1


def test_missing_project_fails(tmp_path: Path) -> None:
    assert check.main(tmp_path) == 1


def test_only_fixed_packages_are_fetchable() -> None:
    with pytest.raises(ValueError, match="unsupported floor dependency"):
        check.latest("https://example.invalid")
