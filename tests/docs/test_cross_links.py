# tests/docs/test_cross_links.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Each documentation model page links its web page, and each web page links back.

The documentation's links are read from the pages ``docs/_ext/model_pages.py``
writes. The site's come from the rules in its TypeScript source, read here and
held to what they say (the idiom of tests/web/test_explorer_constants.py), so a
change to either side fails until the other follows. The site's build proves
each page renders its link (web/tests/site/site.test.ts).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from typing import TYPE_CHECKING, Final

import pytest

from pyeconomics import registry

if TYPE_CHECKING:
    from types import ModuleType

ROOT: Final = Path(__file__).resolve().parents[2]
LIB: Final = ROOT / "web" / "src" / "lib"
LINK: Final = re.compile(r"on \[its web page\]\((https://[^)]+)\)")


def _constant(path: Path, name: str) -> str:
    match = re.search(rf'export const {name} = "([^"]+)";', path.read_text("utf-8"))
    assert match is not None, f"{path.name} has no {name}"
    return match[1]


ORIGIN: Final = _constant(LIB / "paths.ts", "ORIGIN")
DOCUMENTATION: Final = _constant(LIB / "links.ts", "DOCUMENTATION")


def site_page(model_id: str) -> str:
    """The page the site builds for a model (paths.ts ``modelPath``)."""
    domain, name = model_id.split(".")
    return f"{ORIGIN}/models/{domain.replace('_', '-')}/{name.replace('_', '-')}/"


def site_docs_link(model_id: str) -> str:
    """The documentation link a site page carries (models.ts ``docsUrl``)."""
    domain, name = model_id.split(".")
    return f"{DOCUMENTATION}reference/models/{domain}/{name}.html"


@pytest.fixture
def generator() -> ModuleType:
    path = ROOT / "docs" / "_ext" / "model_pages.py"
    spec = importlib.util.spec_from_file_location("model_pages_cross_links", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_sites_rules_are_the_ones_this_test_reads() -> None:
    paths = (LIB / "paths.ts").read_text("utf-8")
    models = (LIB / "models.ts").read_text("utf-8")
    assert (
        '`/models/${domainSegment(match[1] ?? "")}/'
        '${(match[2] ?? "").replaceAll("_", "-")}/`' in paths
    )
    assert 'return domain.replaceAll("_", "-");' in paths
    assert "`${DOCUMENTATION}reference/models/${domain}/${name}.html`" in models


def test_the_two_sets_of_links_are_equal(generator: ModuleType, tmp_path: Path) -> None:
    written = generator.write_pages(tmp_path, registry)
    by_page = {
        path.relative_to(tmp_path).with_suffix("").as_posix(): path for path in written
    }
    docs_pages = {f"{DOCUMENTATION}reference/models/{page}.html" for page in by_page}
    web_links = set()
    for path in written:
        found = LINK.findall(path.read_text("utf-8"))
        assert len(found) == 1, path
        web_links.add(found[0])
    assert web_links == {site_page(model_id) for model_id in registry.ids()}
    assert docs_pages == {site_docs_link(model_id) for model_id in registry.ids()}


def test_a_page_links_its_own_model(generator: ModuleType, tmp_path: Path) -> None:
    generator.write_pages(tmp_path, registry)
    for model_id in registry.ids():
        domain, name = model_id.split(".")
        page = (tmp_path / domain / f"{name}.md").read_text("utf-8")
        assert LINK.findall(page) == [site_page(model_id)], model_id
    assert generator.web_url("fixed_income.bond_pricing") == (
        "https://pyeconomics.dev/models/fixed-income/bond-pricing/"
    )


def test_the_link_sits_before_the_first_section(
    generator: ModuleType, tmp_path: Path
) -> None:
    generator.write_pages(tmp_path, registry)
    page = (tmp_path / "foundations" / "time_value.md").read_text("utf-8")
    assert page.index("its web page") < page.index("\n## ")
