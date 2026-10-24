# tests/surfaces/test_listing.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Listing and searching the models, as every surface shows them (Phase 4 Step 4)."""

from __future__ import annotations

import pytest
import toy_models as toys

from pyeconomics import registry
from pyeconomics.core import InputError
from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.listing import (
    MAX_SEARCH_RESULTS,
    list_models,
    model_entry,
    search_models,
)


def test_an_entry_holds_what_a_person_chooses_by() -> None:
    model = registry.get("macro.policy_rule")
    entry = model_entry(model)
    assert entry == {
        "id": "macro.policy_rule",
        "version": model.spec.version,
        "domain": "macro",
        "title": model.spec.title,
        "summary": model.spec.summary,
        "tags": list(model.spec.tags),
        "cost": model.spec.cost.value if model.spec.cost else None,
        "extra": None,
        "bound": True,
    }
    canonical_json(entry)


def test_the_list_follows_the_registry() -> None:
    assert [entry["id"] for entry in list_models()] == list(registry.ids())
    assert [entry["id"] for entry in list_models("macro")] == [
        model.id for model in registry.models("macro")
    ]
    with pytest.raises(InputError, match="unknown domain"):
        list_models("nowhere")


def test_a_search_ranks_ids_and_titles_first() -> None:
    found = [entry["id"] for entry in search_models("bond duration", 3)]
    assert found[0] == "fixed_income.duration"
    assert len(found) <= 3
    assert search_models("zzzz qqqq") == []
    assert search_models("a") == []


def test_tags_domains_and_summaries_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(core_registry._CACHE, "registry", toys.toy_registry())  # noqa: SLF001
    ids = {entry["id"] for entry in search_models("fixed income", MAX_SEARCH_RESULTS)}
    assert "fixed_income.toy_zero_coupon" in ids


@pytest.mark.parametrize("limit", [0, MAX_SEARCH_RESULTS + 1, True])
def test_a_search_limit_is_bounded(limit: int) -> None:
    with pytest.raises(InputError, match="limit must be between 1 and 100"):
        search_models("bond", limit)


def test_a_search_needs_text() -> None:
    with pytest.raises(InputError):
        search_models("")
