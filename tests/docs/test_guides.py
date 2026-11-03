# tests/docs/test_guides.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The tutorials and how-to guides: their order, their examples and their rules.

docs/conftest.py runs each page's examples. These tests hold what running them
cannot: that the track is the one ROADMAP section 4 5.6 asks for, that Sybil
collects every example, that a page's lists equal the code's, and the step's
security rules: no example shows a key, data examples name their source's licence
class and attribution, and no example sends FRED data to an assistant or a hosted
service.
"""

from __future__ import annotations

import importlib.util
import itertools
import json
import re
import tomllib
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from pyeconomics.mcp.headline import HEADLINE
from pyeconomics.surfaces.problems import ROWS

if TYPE_CHECKING:
    from types import ModuleType

ROOT: Final = Path(__file__).resolve().parents[2]
DOCS: Final = ROOT / "docs"
TRACK: Final = (
    "install",
    "first-model",
    "data-and-keys",
    "command-line",
    "rest-api",
    "mcp",
)
HOW_TO: Final = ("pandas", "r", "excel", "xlwings-lite", "series", "local-app")
#: The pages Sybil runs (a notebook runs in the documentation build instead).
GUIDES: Final = (
    *(DOCS / "tutorials" / f"{name}.md" for name in TRACK if name != "first-model"),
    *(DOCS / "how-to" / f"{name}.md" for name in HOW_TO),
    DOCS / "migration.md",
)
_FENCE: Final = re.compile(r"^```(\S+)\n(.*?)^```", re.MULTILINE | re.DOTALL)
_RUNNABLE: Final = re.compile(r"^ *```(python|console|shell)$", re.MULTILINE)


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _fences(path: Path, *languages: str) -> list[str]:
    return [
        body for language, body in _FENCE.findall(_text(path)) if language in languages
    ]


def _toctree(path: Path) -> list[str]:
    block = re.search(r"```\{toctree\}\n(.*?)```", _text(path), re.DOTALL)
    assert block is not None
    return [line for line in block[1].splitlines() if line and not line.startswith(":")]


@pytest.fixture(scope="module")
def conftest() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "docs_conftest_guides", DOCS / "conftest.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_tutorials_are_the_six_part_track_in_order() -> None:
    assert tuple(_toctree(DOCS / "tutorials" / "index.md")) == TRACK
    assert {path.stem for path in (DOCS / "tutorials").glob("*.md")} == {
        *TRACK,
        "index",
    }


def test_each_tutorial_leads_to_the_next() -> None:
    for name, following in itertools.pairwise(TRACK):
        assert f"{{doc}}`{following}`" in _text(DOCS / "tutorials" / f"{name}.md"), name


def test_the_how_to_guides_are_all_listed() -> None:
    assert tuple(_toctree(DOCS / "how-to" / "index.md")) == HOW_TO
    assert {path.stem for path in (DOCS / "how-to").glob("*.md")} == {*HOW_TO, "index"}


def test_the_index_reaches_every_section() -> None:
    index = _text(DOCS / "index.md")
    for entry in ("tutorials/index", "how-to/index", "study-paths/index", "migration"):
        assert re.search(rf"^{entry}$", index, re.MULTILINE), entry


def test_sybil_collects_every_example_of_every_guide(conftest: ModuleType) -> None:
    for page in GUIDES:
        assert conftest.GUIDES.should_parse(page), page
        lines = {example.line for example in conftest.GUIDES.parse(page).examples()}
        source = _text(page)
        for match in _RUNNABLE.finditer(source):
            first = source.count("\n", 0, match.start()) + 1
            last = first + source.count(
                "\n", match.start(), source.index("```", match.end())
            )
            assert any(first <= line <= last for line in lines), (page, first)


def test_every_guide_has_examples_that_run() -> None:
    for page in GUIDES:
        assert _fences(page, "python", "console", "shell"), page


def test_no_guide_hides_python_in_a_fence_that_does_not_run() -> None:
    for page in GUIDES:
        for body in _fences(page, "text"):
            if body.startswith(">>>"):
                assert page.name == "migration.md", page
                assert "pyeconomics.run" not in body


def test_the_extras_table_is_pyprojects() -> None:
    project = tomllib.loads(_text(ROOT / "pyproject.toml"))["project"]
    listed = re.findall(
        r"^\| `(\w+)` \|", _text(DOCS / "tutorials" / "install.md"), re.MULTILINE
    )
    assert sorted(listed) == sorted(project["optional-dependencies"])


def test_the_exit_code_table_lists_every_code() -> None:
    text = _text(DOCS / "tutorials" / "command-line.md")
    listed = {int(code) for code in re.findall(r"^\| (\d) \|", text, re.MULTILINE)}
    assert listed == {row.exit_code for row in ROWS} | {0, 2}


def test_the_mcp_client_configuration_is_the_guides() -> None:
    (tutorial,) = _fences(DOCS / "tutorials" / "mcp.md", "json")
    assert json.loads(tutorial) == json.loads(_fences(DOCS / "mcp.md", "json")[0])


def test_the_mcp_tutorial_counts_the_headline_tools() -> None:
    assert len(HEADLINE) == 16
    assert "Sixteen widely used models" in _text(DOCS / "tutorials" / "mcp.md")


def test_the_hosted_endpoint_is_never_run() -> None:
    page = DOCS / "tutorials" / "mcp.md"
    assert "https://pyeconomics.dev/mcp" in _text(page)
    assert not any(
        "pyeconomics.dev/mcp" in body for body in _fences(page, "python", "console")
    )


@pytest.mark.parametrize("page", GUIDES, ids=lambda page: page.stem)
def test_no_example_shows_or_stores_a_key(page: Path) -> None:
    text = _text(page)
    assert re.search(r"[A-Z]+_API_KEY\s*=", text) is None
    assert re.search(r"(api_key|token|password)\s*=", text, re.IGNORECASE) is None


def test_a_key_is_set_only_through_the_hidden_prompt() -> None:
    text = _text(DOCS / "tutorials" / "data-and-keys.md")
    assert "pyeconomics keys set fred\n" in text
    assert "hidden prompt" in text
    assert "$ pyeconomics keys list\n" in text
    assert "--stdin" not in text


@pytest.mark.parametrize("page", GUIDES, ids=lambda page: page.stem)
def test_an_example_that_reads_data_names_its_licence_and_attribution(
    page: Path,
) -> None:
    runnable = "".join(_fences(page, "python", "console", "shell"))
    if re.search(r"data\.get\(|data get |/v1/series/", runnable):
        text = _text(page)
        assert "hosted-safe" in text, page
        assert "attribution" in text.casefold(), page


def test_no_example_sends_fred_data_to_an_assistant_or_a_hosted_service() -> None:
    for name in ("mcp", "rest-api"):
        page = DOCS / "tutorials" / f"{name}.md"
        assert "fred:" not in "".join(_fences(page, "python", "console", "shell"))
    refused = "".join(_fences(DOCS / "tutorials" / "data-and-keys.md", "python"))
    assert re.findall(r'data\.get\("fred:\w+"[^)]*\)', refused) == [
        'data.get("fred:UNRATE", mode=data.Mode.HOSTED)'
    ]


def test_no_new_page_path_carries_a_mark() -> None:
    for page in (
        *GUIDES,
        DOCS / "tutorials" / "index.md",
        DOCS / "how-to" / "index.md",
    ):
        assert "cfa" not in page.relative_to(DOCS).as_posix().lower()


def test_the_xlwings_guide_keeps_its_plain_statement() -> None:
    text = " ".join(_text(DOCS / "how-to" / "xlwings-lite.md").split())
    assert "Live data needs a local install" in text
    assert "/issues/114" in text
    assert "/issues/116" in text
    # A bare `pyeconomics` resolves to 0.2.6, which micropip cannot install.
    assert "   pyeconomics>=1.0.0b1,<2\n" in _text(DOCS / "how-to" / "xlwings-lite.md")
