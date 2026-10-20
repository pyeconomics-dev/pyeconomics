# tests/results/test_bound_cards.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The card's "Data" section and ``describe()``'s ``bindings`` key (Step 12)."""

from __future__ import annotations

import json
import re
from typing import Any

import bound_support as bs
import pytest
import toy_models as tm

from pyeconomics import registry
from pyeconomics.core import (
    LicenceClass,
    ModelCard,
    canonical_json,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.binding import CandidateNote
from pyeconomics.core.cards import BOUND_SECTION_TITLES, SECTION_TITLES
from pyeconomics.core.describe import DESCRIPTION_KEYS, describe
from pyeconomics.data.bindings import candidate_notes


def headings(markdown: str) -> list[str]:
    return re.findall(r"^## (.+)$", markdown, flags=re.MULTILINE)


@pytest.fixture
def installed(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        core_registry._CACHE,  # noqa: SLF001
        "registry",
        bs.model_registry(),
    )


# --- the card -----------------------------------------------------------------


def test_a_bound_card_has_a_data_section_after_the_variables() -> None:
    markdown = ModelCard.from_model(bs.unemployment).to_markdown()
    assert headings(markdown) == list(BOUND_SECTION_TITLES)
    assert BOUND_SECTION_TITLES.index("Data") == SECTION_TITLES.index("Variables") + 1


def test_a_card_without_bindings_has_no_data_section() -> None:
    assert headings(ModelCard.from_model(bs.plain).to_markdown()) == list(
        SECTION_TITLES
    )
    assert headings(ModelCard.from_model(tm.zero_coupon).to_markdown()) == list(
        SECTION_TITLES
    )


def test_the_data_section_lists_each_binding_by_profile() -> None:
    markdown = ModelCard.from_model(bs.unemployment).to_markdown()
    section = markdown.split("## Data\n", 1)[1].split("\n## ", 1)[0]
    assert "### Profile `default`" in section
    assert "### Profile `revised`" in section
    assert "### Profile `uk`" in section
    assert (
        "| `unemployment` | `us.unemployment.rate` | none | "
        "last observation on or before the date | real time: as published by the date |"
    ) in section
    assert "latest: revised data" in section
    assert 'pyeconomics.bind("macro.toy_unemployment")' in section
    assert "`revised_data`" in section


def test_the_data_section_words_a_window_a_period_and_a_transform() -> None:
    window = ModelCard.from_model(bs.unemployment_window).to_markdown()
    assert "the last 4 observations on or before the date" in window
    period = ModelCard.from_model(bs.output).to_markdown()
    assert "the observation of the period containing the date" in period
    change = ModelCard.from_model(bs.unemployment_change).to_markdown()
    assert "| `diff` |" in change


def test_candidates_add_the_classes_and_notices_of_the_sources() -> None:
    notes = {
        "us.unemployment.rate": (
            CandidateNote(
                provider="bls",
                licence=LicenceClass.HOSTED_SAFE,
                attribution="Source: BLS.",
                notice="Not endorsed by the BLS.",
            ),
            CandidateNote(provider="fred", licence=LicenceClass.LIBRARY_ONLY),
            CandidateNote(provider="derived", licence=None),
        )
    }
    markdown = ModelCard.from_model(bs.unemployment_window, notes).to_markdown()
    assert "### Sources" in markdown
    assert "Concept `us.unemployment.rate`:" in markdown
    assert "- **bls** (hosted-safe) Source: BLS. Not endorsed by the BLS." in markdown
    assert "- **fred** (library-only)" in markdown
    assert "- **derived** (derived)" in markdown


def test_a_card_renders_the_same_text_every_time() -> None:
    first = ModelCard.from_model(bs.unemployment).to_markdown()
    assert first == ModelCard.from_model(bs.unemployment).to_markdown()
    assert "\r" not in first
    assert first.endswith("\n")


# --- describe -----------------------------------------------------------------


def test_describe_carries_the_bindings_in_a_fixed_position() -> None:
    description = describe(bs.unemployment)
    assert tuple(description) == DESCRIPTION_KEYS
    keys = list(description)
    assert keys.index("aliases") < keys.index("bindings") < keys.index("extra")
    first = description["bindings"][0]
    assert first == {
        "field": "unemployment",
        "concept": "us.unemployment.rate",
        "transform": None,
        "as_of": "last_on_or_before",
        "window": None,
        "vintage": "real_time",
        "profile": "default",
        "tenors": None,
    }
    assert [b["profile"] for b in description["bindings"]] == [
        "default",
        "revised",
        "uk",
    ]


def test_describe_is_json_ready_for_a_bound_model() -> None:
    description = describe(bs.unemployment_window)
    assert json.loads(json.dumps(description)) == description
    canonical_json(description)
    assert description["bindings"][0]["as_of"] == "window"
    assert description["bindings"][0]["window"] == 4


def test_a_model_without_bindings_describes_an_empty_list() -> None:
    assert describe(bs.plain)["bindings"] == []


def test_describe_passes_the_candidates_to_the_card() -> None:
    notes: dict[str, Any] = candidate_notes(bs.unemployment, bs.world())
    assert set(notes) == {"us.unemployment.rate", "gb.inflation.cpi.yoy"}
    description = describe(bs.unemployment, notes)
    assert "### Sources" in description["card"]


def test_candidate_notes_come_from_metadata_in_fallback_order() -> None:
    notes = candidate_notes(bs.unemployment, bs.world())
    rate = notes["us.unemployment.rate"]
    assert [(n.provider, n.licence) for n in rate] == [
        ("bls", LicenceClass.HOSTED_SAFE),
        ("fred", LicenceClass.LIBRARY_ONLY),
    ]
    assert rate[0].attribution
    assert candidate_notes(bs.plain, bs.world()) == {}


def test_the_registry_facade_lists_the_sources_of_a_bound_model(
    installed: None,  # noqa: ARG001 - the fixture installs the toy models
) -> None:
    description = registry.describe("macro.toy_unemployment")
    card = description["card"]
    assert "### Sources" in card
    assert "- **bls** (hosted-safe)" in card
    assert "- **fred** (library-only)" in card
    assert registry.describe("macro.toy_plain")["bindings"] == []
