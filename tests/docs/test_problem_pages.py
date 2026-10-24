# tests/docs/test_problem_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exercise the problem types page generator without importing Sphinx."""

from __future__ import annotations

import importlib.util
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from pyeconomics.surfaces.problems import ROWS

if TYPE_CHECKING:
    from types import ModuleType


@pytest.fixture
def generator() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "docs" / "_ext" / "problem_pages.py"
    spec = importlib.util.spec_from_file_location("problem_pages_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_page_lists_every_row_under_an_anchor_named_by_its_slug(
    generator: ModuleType,
) -> None:
    page = generator.render(ROWS)
    assert page.startswith("# Problem types\n")
    for row in ROWS:
        assert f"\n## {row.slug}\n" in page
        assert (
            f"| `{row.slug}` | {row.title} | {row.status} | {row.exit_code} |" in page
        )
        assert f"Type: `https://pyeconomics.dev/problems/{row.slug}`" in page
    assert "raised as `pyeconomics.core.errors.InputError`" in page
    assert "raised as any other exception" in page
    assert "- `7`: data unavailable" in page


def test_the_page_is_written_as_utf8_with_lf(
    generator: ModuleType, tmp_path: Path
) -> None:
    path = generator.write_page(tmp_path / "docs" / "problems.md", ROWS)
    data = path.read_bytes()
    assert b"\r\n" not in data
    assert data.decode("utf-8") == generator.render(ROWS)


@pytest.mark.parametrize("slug", ["Invalid", "a b", "x" * 65, "invalid-input"])
def test_a_bad_or_repeated_slug_writes_nothing(
    generator: ModuleType, tmp_path: Path, slug: str
) -> None:
    rows = (*ROWS, replace(ROWS[0], slug=slug))
    with pytest.raises(ValueError, match="Invalid or duplicate"):
        generator.write_page(tmp_path / "problems.md", rows)
    assert not (tmp_path / "problems.md").exists()
