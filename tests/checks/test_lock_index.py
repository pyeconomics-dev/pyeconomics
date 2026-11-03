# tests/checks/test_lock_index.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Unit tests for scripts/checks/lock_index.py, the PyPI-only lock guard."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "checks" / "lock_index.py"
WHEEL = "https://files.pythonhosted.org/packages/aa/bb/demo-1.0-py3-none-any.whl"
PRIVATE = "https://mirror.example.invalid/acme-org/simple"
PYPI_SOURCE = '{ registry = "https://pypi.org/simple" }'


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("lock_index_check", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


lock_index = load_script()


def uv_lock(source: str, wheel: str = WHEEL) -> str:
    return (
        'version = 1\n\n[[package]]\nname = "pyeconomics"\nversion = "1.0.0.dev1"\n'
        'source = { editable = "." }\n\n[[package]]\nname = "demo"\nversion = "1.0"\n'
        f"source = {source}\n"
        f'wheels = [{{ url = "{wheel}", hash = "sha256:00" }}]\n'
    )


def pylock(index: str, wheel: str = WHEEL) -> str:
    return (
        'lock-version = "1.0"\n\n[[packages]]\nname = "pyeconomics"\n'
        'directory = { path = ".", editable = true }\n\n[[packages]]\nname = "demo"\n'
        f'version = "1.0"\nindex = "{index}"\n'
        f'wheels = [{{ url = "{wheel}", hashes = {{ sha256 = "00" }} }}]\n'
    )


def write(tmp_path: Path, uv: str, py: str) -> Path:
    (tmp_path / "uv.lock").write_text(uv, encoding="utf-8")
    (tmp_path / "pylock.toml").write_text(py, encoding="utf-8")
    return tmp_path


def test_repository_lock_files_pass(capsys: pytest.CaptureFixture[str]) -> None:
    assert lock_index.main(REPO) == 0
    assert "name only PyPI sources" in capsys.readouterr().out


def test_pypi_only_passes(tmp_path: Path) -> None:
    root = write(tmp_path, uv_lock(PYPI_SOURCE), pylock("https://pypi.org/simple"))
    assert lock_index.main(root) == 0


def test_private_index_fails_and_is_redacted(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = write(tmp_path, uv_lock(f'{{ registry = "{PRIVATE}" }}'), pylock(PRIVATE))
    assert lock_index.main(root) == 1
    err = capsys.readouterr().err
    assert "https://mirror.example.invalid/..." in err
    assert "acme-org" not in err


@pytest.mark.parametrize(
    "source",
    [
        '{ git = "https://github.com/example/demo?rev=abc#abc" }',
        '{ path = "../wheels/demo-1.0-py3-none-any.whl" }',
        '{ registry = "../local-index" }',
    ],
)
def test_non_registry_sources_fail(tmp_path: Path, source: str) -> None:
    root = write(tmp_path, uv_lock(source), pylock("https://pypi.org/simple"))
    assert lock_index.main(root) == 1


def test_file_outside_files_pythonhosted_fails(tmp_path: Path) -> None:
    wheel = "https://example.invalid/demo-1.0-py3-none-any.whl"
    root = write(
        tmp_path,
        uv_lock(PYPI_SOURCE),
        pylock("https://pypi.org/simple", wheel=wheel),
    )
    assert lock_index.main(root) == 1


def test_missing_lock_file_fails(tmp_path: Path) -> None:
    (tmp_path / "uv.lock").write_text(uv_lock(PYPI_SOURCE), encoding="utf-8")
    assert lock_index.main(tmp_path) == 1


MEMBER_PROJECT = (
    '[project]\nname = "pyeconomics"\n\n'
    '[tool.uv.workspace]\nmembers = ["packages/demo-app"]\n'
)
MEMBER_SOURCE = '{ editable = "packages/demo-app" }'


def test_a_declared_workspace_member_passes(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(MEMBER_PROJECT, encoding="utf-8")
    root = write(tmp_path, uv_lock(MEMBER_SOURCE), pylock("https://pypi.org/simple"))
    assert lock_index.main(root) == 0


def test_an_undeclared_editable_path_fails(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(MEMBER_PROJECT, encoding="utf-8")
    source = '{ editable = "packages/other" }'
    root = write(tmp_path, uv_lock(source), pylock("https://pypi.org/simple"))
    assert lock_index.main(root) == 1


def test_a_member_without_a_workspace_fails(tmp_path: Path) -> None:
    root = write(tmp_path, uv_lock(MEMBER_SOURCE), pylock("https://pypi.org/simple"))
    assert lock_index.main(root) == 1


def test_a_declared_member_passes_in_pylock(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(MEMBER_PROJECT, encoding="utf-8")
    member = (
        '\n[[packages]]\nname = "demo-app"\n'
        'directory = { path = "packages/demo-app", editable = true }\n'
    )
    py = pylock("https://pypi.org/simple") + member
    root = write(tmp_path, uv_lock(PYPI_SOURCE), py)
    assert lock_index.main(root) == 0
