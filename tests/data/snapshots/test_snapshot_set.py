# tests/data/snapshots/test_snapshot_set.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot set: computed from the catalog and the registry (Phase 5 Step 8).

It holds every hosted-safe originator candidate of every bound model's default
profile, and nothing from FRED, an aggregator, a library-only source or a
storage-forbidden series (ADR-0013 decision 6; ROADMAP §5 "Data licensing
policy" rules 3 and 4).
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from snapshot_support import forbidding

from pyeconomics import registry as model_registry
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.cache.policy import may_store
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived, Tier
from pyeconomics.data.providers.base import Capability
from pyeconomics.data.registry import ProviderRegistry
from pyeconomics.data.snapshots.set import (
    HISTORY_STARTS,
    SEP_MEETINGS,
    bound_concepts,
    snapshot_set,
)

if TYPE_CHECKING:
    import pytest

#: The set's size today; a catalog change that moves it updates this pin.
SET_SIZE = 92
PROVIDERS = (
    "bea",
    "bis",
    "bls",
    "cbo",
    "damodaran",
    "ecb",
    "eurostat",
    "fed_board",
    "nyfed",
    "oecd",
    "penn_world_table",
    "treasury",
)


def _with_operands(concept_id: str, seen: set[str]) -> list[Concept]:
    """A concept and, for a derived candidate, its operands, recursively."""
    if concept_id in seen:
        return []
    seen.add(concept_id)
    concept = catalog.get(concept_id)
    found = [concept]
    for candidate in concept.candidates:
        if isinstance(candidate, Derived):
            for operand in candidate.operands:
                found += _with_operands(operand.concept, seen)
    return found


def _hosted_candidates(concept: Concept) -> list[tuple[str, str]]:
    installed = provider_registry.installed()
    wanted = []
    for candidate in concept.candidates:
        if (
            not isinstance(candidate, Candidate)
            or candidate.tier is not Tier.ORIGINATOR
        ):
            continue
        info = installed.provider_class(candidate.provider).info
        if info.terms.licence is not LicenceClass.HOSTED_SAFE:
            continue
        keys = (
            [candidate.series.replace("{meeting}", m) for m in SEP_MEETINGS]
            if "{meeting}" in candidate.series
            else [candidate.series]
        )
        wanted += [(candidate.provider, key) for key in keys]
    return wanted


def test_the_set_has_its_pinned_size_and_providers() -> None:
    chosen = snapshot_set()
    assert len(chosen) == SET_SIZE
    assert chosen.providers() == PROVIDERS
    assert chosen.excluded == ()


def test_it_holds_every_hosted_safe_candidate_of_every_default_profile() -> None:
    chosen = snapshot_set()
    held = {(e.provider, e.series) for e in chosen.entries}
    seen: set[str] = set()
    wanted: set[tuple[str, str]] = set()
    bound = 0
    for model_id in model_registry.ids():
        model = model_registry.get(model_id)
        defaults = [b for b in model.spec.bindings if b.profile == "default"]
        bound += bool(defaults)
        for binding in defaults:
            for concept in _with_operands(binding.concept, seen):
                wanted |= set(_hosted_candidates(concept))
    assert bound >= 18
    assert wanted
    assert sorted(wanted - held) == []


def test_it_holds_every_concept_any_profile_binds() -> None:
    models = [model_registry.get(i) for i in model_registry.ids()]
    named = bound_concepts(models)
    assert "us.treasury.par_curve" in named
    assert named <= {concept.id for concept in catalog.concepts()}


def test_nothing_from_fred_an_aggregator_or_a_library_only_source() -> None:
    installed = provider_registry.installed()
    for entry in snapshot_set().entries:
        info = installed.provider_class(entry.provider).info
        assert entry.provider not in {"fred", "dbnomics"}
        assert info.terms.licence is LicenceClass.HOSTED_SAFE, entry.target
        assert may_store(info.terms), entry.target
        tiers = {
            candidate.tier
            for concept_id in entry.concepts
            for candidate in catalog.get(concept_id).candidates
            if isinstance(candidate, Candidate) and candidate.provider == entry.provider
        }
        assert tiers == {Tier.ORIGINATOR}, entry.target


def test_a_storage_forbidden_source_is_left_out_and_listed() -> None:
    installed = provider_registry.installed()
    providers = [installed.provider_class(i) for i in installed.ids()]
    without = [p for p in providers if p.info.id != "treasury"]
    registry = ProviderRegistry.from_providers(*without, forbidding("treasury", {}))
    chosen = snapshot_set(registry=registry)
    assert not chosen.of("treasury")
    reasons = {(x.provider, x.reason) for x in chosen.excluded}
    assert reasons == {("treasury", "storage_forbidden")}
    assert {x.series for x in chosen.excluded} >= {"par_nominal", "debt"}


def test_a_window_concept_without_a_declared_start_is_left_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    toy = replace(
        catalog.get("us.treasury.par_curve"),
        id="us.toy.par_curve",
        candidates=(Candidate(provider="treasury", series="toy"),),
    )
    concepts, get = catalog.concepts, catalog.get
    monkeypatch.setattr(catalog, "concepts", lambda: (*concepts(), toy))
    monkeypatch.setattr(
        catalog,
        "get",
        lambda concept_id: toy if concept_id == toy.id else get(concept_id),
    )
    chosen = snapshot_set(models=())
    assert chosen.get("treasury", "toy") is None
    assert [(x.series, x.reason) for x in chosen.excluded] == [
        ("toy", "undeclared_window")
    ]


def test_parameterized_concepts_expand_over_the_declared_meetings() -> None:
    chosen = snapshot_set()
    sep = {e.series for e in chosen.of("fed_board") if e.series.startswith("sep:")}
    assert sep == {f"sep:{meeting}" for meeting in SEP_MEETINGS}
    assert tuple(sorted(set(SEP_MEETINGS))) == SEP_MEETINGS


def test_series_served_by_window_carry_their_declared_start() -> None:
    chosen = snapshot_set()
    starts = {(e.provider, e.series): e.start for e in chosen.entries if e.start}
    assert starts == dict(HISTORY_STARTS)
    for entry in chosen.entries:
        if any(catalog.get(c).needs_window for c in entry.concepts):
            assert entry.start is not None, entry.target


def test_a_source_that_keeps_vintages_is_kept_at_every_vintage() -> None:
    installed = provider_registry.installed()
    for entry in snapshot_set().entries:
        keeps = (
            Capability.VINTAGES
            in installed.provider_class(entry.provider).info.capabilities
        )
        assert entry.vintage == ("all" if keeps else "latest"), entry.target
    assert {e.vintage for e in snapshot_set().of("cbo")} == {"all"}
