# tests/docs/test_examples_gallery.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The example gallery: one script or more per domain, each offline and runnable.

The documentation build runs the scripts with the docs job's environment. Running
them here as well finds a break on every cell of the test matrix, and under
pytest's rules: no socket, and every warning an error.
"""

from __future__ import annotations

import ast
import re
import runpy
from pathlib import Path
from typing import Final

import pytest

from pyeconomics import registry

ROOT: Final = Path(__file__).resolve().parents[2]
DOCS: Final = ROOT / "docs"
SCRIPTS: Final = sorted((DOCS / "examples").glob("*.py"))
_RUN: Final = re.compile(r'pyeconomics\.run\(\s*"(\w+)\.(\w+)"')


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _models(script: Path) -> set[str]:
    return {f"{domain}.{name}" for domain, name in _RUN.findall(_text(script))}


def test_every_populated_domain_has_a_script() -> None:
    covered = {model.split(".")[0] for script in SCRIPTS for model in _models(script)}
    assert covered == set(registry.domains())


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_a_script_has_the_file_header_a_title_and_an_explanation(script: Path) -> None:
    lines = _text(script).splitlines()
    assert lines[0] == f"# {script.relative_to(ROOT).as_posix()}"
    assert lines[1].startswith("# Copyright ")
    assert lines[2] == "# SPDX-License-Identifier: Apache-2.0"
    docstring = ast.get_docstring(ast.parse(_text(script)))
    assert docstring is not None
    title, underline, _, *explanation = docstring.splitlines()
    assert underline == "=" * len(title)
    assert " ".join(explanation)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_a_script_links_the_page_of_a_model_it_runs(script: Path) -> None:
    models = _models(script)
    assert models
    assert any(
        f"/reference/models/{model.replace('.', '/')}" in _text(script)
        for model in models
    )


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_a_script_draws_the_chart_of_a_model_that_has_one(script: Path) -> None:
    charted = [model for model in _models(script) if registry.get(model).spec.charts]
    assert (".plot()" in _text(script)) == bool(charted)


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_a_script_reads_no_data(script: Path) -> None:
    text = _text(script)
    assert "pyeconomics.data" not in text
    assert "pyeconomics.bind" not in text


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.stem)
def test_a_script_runs_offline(script: Path) -> None:
    runpy.run_path(str(script), run_name="__main__")


def test_the_generated_gallery_is_ignored_everywhere() -> None:
    assert "docs/gallery/\n" in _text(ROOT / ".gitignore")
    assert "docs/gallery/\n" in _text(ROOT / ".dockerignore")


def test_a_failing_script_fails_the_build() -> None:
    assert '"abort_on_example_error": True' in _text(DOCS / "conf.py")


def test_a_figure_loads_nothing_from_another_origin() -> None:
    renderer = _text(DOCS / "_ext" / "gallery_figures.py")
    assert "include_plotlyjs=_PLOTLY_JS" in renderer
    assert "include_mathjax=False" in renderer
    assert "plotly.min.js" in _text(DOCS / "conf.py")
