# tests/docs/test_finance_tutorials.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Python-for-finance tutorials: their order, sources and the marks rule.

They are MyST-NB notebooks, so the documentation build runs them and each one's
assertions. These tests hold what running them cannot: each method's originators
stay cited, each page keeps its disclaimer and sockets stay off, and none of them
names a curriculum (ROADMAP section 5, "CFA Institute marks and content").
"""

from __future__ import annotations

import itertools
import re
from pathlib import Path
from typing import Final

import pytest

ROOT: Final = Path(__file__).resolve().parents[2]
DOCS: Final = ROOT / "docs"
FINANCE: Final = DOCS / "tutorials" / "finance"
TRACK: Final = (
    "pandas-results",
    "return-statistics",
    "monte-carlo",
    "portfolio-mathematics",
)
PAGES: Final = tuple(FINANCE / f"{name}.md" for name in TRACK)
#: Each method's originators, as the page's references must name them.
ORIGINATORS: Final = {
    "pandas-results": ("McKinney", "Macaulay"),
    "return-statistics": (
        "Bacon",
        "Fisher",
        "Hardy",
        "Joanes",
        "Osborne",
        "Sortino",
    ),
    "monte-carlo": (
        "Boyle",
        "Efron",
        "Glasserman",
        "Hammersley",
        "Metropolis",
        "Osborne",
    ),
    "portfolio-mathematics": (
        "Jensen",
        "Markowitz",
        "Merton",
        "Modigliani",
        "Pratt",
        "Sharpe",
        "Sortino",
        "Tobin",
        "Treynor",
    ),
}


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _references(page: Path) -> str:
    return _text(page).split("\n## References\n")[1]


def test_the_track_is_the_four_tutorials_in_order() -> None:
    block = re.search(
        r"```\{toctree\}\n(.*?)```", _text(FINANCE / "index.md"), re.DOTALL
    )
    assert block is not None
    listed = [
        line for line in block[1].splitlines() if line and not line.startswith(":")
    ]
    assert tuple(listed) == TRACK
    assert {path.stem for path in FINANCE.glob("*.md")} == {*TRACK, "index"}


@pytest.mark.parametrize("page", PAGES, ids=lambda path: path.stem)
def test_a_tutorial_is_a_notebook_the_build_runs_with_sockets_off(page: Path) -> None:
    text = _text(page)
    assert text.startswith("---\nfile_format: mystnb\n")
    assert "disable_socket()" in text
    assert "```{code-cell} ipython3" in text


def test_each_tutorial_leads_to_the_next() -> None:
    for name, following in itertools.pairwise(TRACK):
        assert f"{{doc}}`{following}`" in _text(FINANCE / f"{name}.md")


@pytest.mark.parametrize("name", TRACK)
def test_a_tutorial_cites_its_methods_originators(name: str) -> None:
    references = _references(FINANCE / f"{name}.md")
    missing = [person for person in ORIGINATORS[name] if person not in references]
    assert not missing


@pytest.mark.parametrize("page", PAGES, ids=lambda path: path.stem)
def test_a_tutorial_says_what_its_numbers_are(page: Path) -> None:
    text = " ".join(_text(page).split())
    assert "invented" in text
    assert "not investment advice" in text or "investment advice or" in text


@pytest.mark.parametrize("page", [*PAGES, FINANCE / "index.md"], ids=lambda p: p.stem)
def test_a_tutorial_names_no_curriculum(page: Path) -> None:
    text = _text(page).casefold()
    assert "cfa" not in text
    assert "curriculum" not in text
    assert "practical skills" not in text
    assert "learning outcome" not in text
    assert "cfa" not in page.relative_to(DOCS).as_posix().casefold()


@pytest.mark.parametrize("page", PAGES, ids=lambda path: path.stem)
def test_a_tutorial_reads_no_data(page: Path) -> None:
    text = _text(page)
    assert "data.get(" not in text
    assert "pyeconomics.bind" not in text


def test_the_front_page_links_the_gallery_the_examples_and_the_tutorials() -> None:
    text = _text(DOCS / "index.md")
    for page in ("gallery/index", "wasm/index", "tutorials/finance/index"):
        assert f"<{page}>`" in text
        assert f"\n{page}\n" in text
