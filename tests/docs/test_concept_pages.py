# tests/docs/test_concept_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exercise the concept page and sources summary generators without Sphinx."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from pyeconomics import data
from pyeconomics.data import Mode

if TYPE_CHECKING:
    from types import ModuleType

    from pyeconomics.data import CandidateInfo, SourceInfo
    from pyeconomics.data.catalog import Concept


@pytest.fixture
def generator() -> ModuleType:
    path = Path(__file__).resolve().parents[2] / "docs" / "_ext" / "concept_pages.py"
    spec = importlib.util.spec_from_file_location("concept_pages_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Live:
    """The installed catalog and registry, as the Sphinx hook reads them."""

    def concepts(self) -> tuple[Concept, ...]:
        return data.catalog.concepts()

    def describe(self, concept: Concept) -> dict[str, tuple[CandidateInfo, ...]]:
        return {m.value: c for m, c in data.candidates_by_mode(concept).items()}

    def sources(self) -> tuple[SourceInfo, ...]:
        return data.sources(check_keys=False)


def test_a_page_states_the_definition_the_unit_and_the_candidates_by_mode(
    generator: ModuleType,
) -> None:
    concept = data.catalog.get("us.unemployment.rate")
    by_mode = {m.value: c for m, c in data.candidates_by_mode(concept).items()}
    page = generator.render(concept, by_mode)
    assert page.startswith("# Unemployment rate\n")
    for expected in (
        "`us.unemployment.rate`",
        "decimal (0.042 is 4.2%)",
        "monthly",
        "seasonally adjusted",
        "## Candidates in library mode",
        "## Candidates in hosted mode",
        "[bls](../providers/bls.md)",
        "`LNS14000000`",
        "[fred](../providers/fred.md)",
        "`FRED_API_KEY` (required)",
        "`BLS_API_KEY` (optional)",
        "originator",
        "aggregator",
        "falls to FRED",
        "[Data sources and keys](../../data/index.md)",
    ):
        assert expected in page, expected
    hosted = page.split("## Candidates in hosted mode")[1]
    assert "bls" in hosted
    assert "`FRED_API_KEY`" not in hosted  # FRED is refused in hosted mode


def test_a_concept_with_no_hosted_candidate_says_it_is_refused(
    generator: ModuleType,
) -> None:
    concept = data.catalog.get("us.inflation.pce_trimmed_mean.yoy")
    by_mode = {m.value: c for m, c in data.candidates_by_mode(concept).items()}
    page = generator.render(concept, by_mode)
    assert "this concept has no such source" in page
    assert "LicenceError" in page
    assert "## Notes" in page


def test_a_derived_concept_links_its_operands_and_a_parameter_is_shown(
    generator: ModuleType,
) -> None:
    gap = data.catalog.get("us.output_gap.real_potential")
    page = generator.render(
        gap, {m.value: c for m, c in data.candidates_by_mode(gap).items()}
    )
    assert "[us.output.real_gdp](us.output.real_gdp.md)" in page
    assert "[us.output.potential_gdp](us.output.potential_gdp.md)" in page
    sep = data.catalog.get("us.sep.medians")
    page = generator.render(
        sep, {m.value: c for m, c in data.candidates_by_mode(sep).items()}
    )
    assert "`meeting` (such as `2026-09-16`)" in page
    assert "`sep:{meeting}`" in page
    curve = data.catalog.get("us.treasury.par_curve")
    page = generator.render(
        curve, {m.value: c for m, c in data.candidates_by_mode(curve).items()}
    )
    assert "yes: both `start` and `end`" in page


def test_every_concept_gets_one_page_and_the_index_groups_them_by_section(
    generator: ModuleType, tmp_path: Path
) -> None:
    paths = generator.write_pages(tmp_path, Live())
    assert len(paths) == len(data.catalog.ids())
    index = (tmp_path / "index.md").read_text(encoding="utf-8")
    assert "## Treasury curves" in index
    assert "[Unemployment rate](us.unemployment.rate.md)" in index
    for concept_id in data.catalog.ids():
        assert f"\n{concept_id}\n" in index  # in the hidden toctree
        assert (tmp_path / f"{concept_id}.md").is_file()


def test_a_stale_page_is_removed_and_a_bad_id_never_escapes_the_directory(
    generator: ModuleType, tmp_path: Path
) -> None:
    stale = tmp_path / "us.gone.concept.md"
    stale.write_text("old", encoding="utf-8")
    generator.write_pages(tmp_path, Live())
    assert not stale.exists()

    class Bad(Live):
        def concepts(self) -> tuple[Any, ...]:
            good = data.catalog.get("us.unemployment.rate")

            class Tricky:
                id = "../../etc/passwd"

            return (good, Tricky())

    with pytest.raises(ValueError, match="Invalid or duplicate concept ids"):
        generator.write_pages(tmp_path / "bad", Bad())
    assert not (tmp_path / "bad").exists()


def test_the_sources_summary_lists_each_providers_class_key_and_notice(
    generator: ModuleType, tmp_path: Path
) -> None:
    path = generator.write_sources(tmp_path / "sources.md", Live())
    page = path.read_text(encoding="utf-8")
    assert page.startswith("# Sources summary\n")
    rows = [line for line in page.splitlines() if line.startswith("| [")]
    assert len(rows) == len(data.registry.ids())
    fred = next(line for line in rows if "`fred`" in line)
    assert "`library-only`" in fred
    assert "| no |" in fred  # not served in hosted mode
    assert "`FRED_API_KEY`" in fred
    treasury = next(line for line in rows if "`treasury`" in line)
    assert "| yes |" in treasury
    assert "(providers/treasury.md)" in treasury
    bls = next(line for line in rows if "`bls`" in line)
    assert "`BLS_API_KEY` (optional)" in bls
    assert "cannot vouch" in bls  # BLS's required notice


def test_a_table_cell_cannot_break_the_row(generator: ModuleType) -> None:
    assert generator.table_row("a|b", "c\nd") == "| a\\|b | c d |"
    assert generator.code_span("a`b") == "`a'b`"
    assert generator.escape_text("x *y* _z_") == "x \\*y\\* \\_z\\_"


def test_the_hosted_mark_follows_the_modes(generator: ModuleType) -> None:
    concept = data.catalog.get("us.equity.cape")
    by_mode = {m.value: c for m, c in data.candidates_by_mode(concept).items()}
    assert generator.hosted_mark(by_mode) == "no"
    assert Mode.HOSTED.value in by_mode
