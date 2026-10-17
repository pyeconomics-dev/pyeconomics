# tests/data/catalog/test_world_resolution.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every shipped concept resolves, offline, in library and in hosted mode.

The world (tests/data/catalog/catalog_world.py) stands in for every installed
provider with the real provider's metadata and synthetic data shaped as each
candidate's source delivers it. These tests then ask the resolver for every
concept the catalog holds and check what must hold for all of them: the
originator answers first; hosted mode resolves an originator or refuses with a
``LicenceError`` naming the classes it found; a missing key, a missing extra and
an unsatisfiable vintage each fall through to the next candidate and are
recorded; and ``strict=True`` stops at the first.
"""

from __future__ import annotations

import datetime as dt
import secrets
from typing import Any

import pytest
from catalog_world import Fail, world_registry

from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.data import (
    CredentialError,
    DataError,
    LicenceClass,
    LicenceError,
    Mode,
    ProviderNotFoundError,
    candidates_by_mode,
    catalog,
    resolve,
)
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived
from pyeconomics.data.registry import ProviderRegistry

WINDOW = {"start": dt.date(2025, 3, 1), "end": dt.date(2026, 6, 30)}
KEYED = ("fred", "bls", "bea")


def ask(concept: Concept) -> dict[str, Any]:
    """The arguments that satisfy a concept's own requirements."""
    arguments: dict[str, Any] = {}
    if concept.parameters:
        arguments["parameters"] = {p.name: p.example for p in concept.parameters}
    if concept.needs_window:
        arguments |= WINDOW
    return arguments


@pytest.fixture
def keys(isolated: object) -> None:
    for provider in KEYED:
        isolated.keyring.set_password(  # type: ignore[attr-defined]
            "pyeconomics", provider, secrets.token_hex(16)
        )


@pytest.fixture(scope="module")
def world() -> ProviderRegistry:
    """One stand-in registry for the module."""
    return world_registry()


CONCEPTS = catalog.concepts()
IDS = [c.id for c in CONCEPTS]


def _first_provider(concept: Concept) -> str:
    first = concept.candidates[0]
    if isinstance(first, Candidate):
        return first.provider
    return "derived"


@pytest.mark.parametrize("concept", CONCEPTS, ids=IDS)
def test_every_concept_resolves_in_library_mode_to_its_originator(
    concept: Concept, keys: None, world: object
) -> None:
    result = resolve(concept, registry=world, **ask(concept))  # type: ignore[arg-type]
    assert result.concept == concept.id
    assert len(result.frame.index) > 0
    assert result.skipped == ()
    record = result.source
    assert record.concept == concept.id
    if _first_provider(concept) != "derived":
        assert record.provider == _first_provider(concept)
        assert record.fallback_chain == (record.provider,)
        assert list(record.transforms) == list(
            concept.candidates[0].transforms  # type: ignore[union-attr]
        )
        # A derived concept's records keep each operand's own window.
        assert record.observation_start == result.frame.index[0]
        assert record.observation_end == result.frame.index[-1]
    assert record.licence is not None
    assert record.attribution


@pytest.mark.parametrize("concept", CONCEPTS, ids=IDS)
def test_hosted_mode_resolves_an_originator_or_refuses_naming_the_classes(
    concept: Concept, keys: None, world: object
) -> None:
    hosted = candidates_by_mode(concept, world)[Mode.HOSTED]  # type: ignore[arg-type]
    if hosted:
        result = resolve(concept, mode=Mode.HOSTED, registry=world, **ask(concept))  # type: ignore[arg-type]
        assert all(s.licence.hosted_allowed for s in result.sources)
        assert result.source.licence in {
            LicenceClass.HOSTED_SAFE,
            LicenceClass.USER_SUPPLIED,
        }
        return
    with pytest.raises(LicenceError) as caught:
        resolve(concept, mode=Mode.HOSTED, registry=world, **ask(concept))  # type: ignore[arg-type]
    named = {
        info.licence.value
        for info in candidates_by_mode(concept, world)[Mode.LIBRARY]  # type: ignore[arg-type]
        if info.licence is not None
    }
    assert named
    assert all(name in str(caught.value) for name in named)


def test_the_trimmed_mean_refuses_in_hosted_mode_and_resolves_in_library_mode(
    keys: None, world: object
) -> None:
    concept = catalog.get("us.inflation.pce_trimmed_mean.yoy")
    with pytest.raises(LicenceError, match="library-only"):
        resolve(concept, mode=Mode.HOSTED, registry=world)  # type: ignore[arg-type]
    assert resolve(concept, registry=world).source.provider == "fred"  # type: ignore[arg-type]


def test_no_key_falls_past_a_keyed_originator_and_is_recorded(world: object) -> None:
    concept = catalog.get("us.prices.pce")  # BEA first, FRED second: both keyed
    with pytest.raises(CredentialError, match="BEA_API_KEY"):
        resolve(concept, registry=world)  # type: ignore[arg-type]


def test_a_key_for_the_aggregator_alone_lets_the_resolver_fall_to_it(
    isolated: object, world: object
) -> None:
    isolated.keyring.set_password(  # type: ignore[attr-defined]
        "pyeconomics", "fred", secrets.token_hex(16)
    )
    result = resolve(catalog.get("us.prices.pce"), registry=world)  # type: ignore[arg-type]
    assert result.source.provider == "fred"
    assert result.source.fallback_chain == ("bea", "fred")
    assert "skipped_bea_key_missing" in result.source.warnings
    assert [s.reason for s in result.skipped] == ["key_missing"]


def test_strict_stops_at_the_first_candidate(isolated: object, world: object) -> None:
    isolated.keyring.set_password(  # type: ignore[attr-defined]
        "pyeconomics", "fred", secrets.token_hex(16)
    )
    with pytest.raises(CredentialError):
        resolve(catalog.get("us.prices.pce"), strict=True, registry=world)  # type: ignore[arg-type]


def test_a_missing_extra_falls_to_the_next_candidate_and_is_recorded() -> None:
    fail = Fail()
    fail.errors["eurostat"] = MissingOptionalDependencyError(
        "the sdmx extra is not installed"
    )
    world = world_registry(fail)
    result = resolve(catalog.get("ea.inflation.hicp.yoy"), registry=world)
    assert result.source.provider == "ecb"
    assert result.source.fallback_chain == ("eurostat", "ecb")
    assert [s.reason for s in result.skipped] == ["extra_missing"]
    assert "skipped_eurostat_extra_missing" in result.source.warnings
    with pytest.raises(DataError, match="extra_missing"):
        resolve(catalog.get("ea.inflation.hicp.yoy"), strict=True, registry=world)


def test_an_unsatisfiable_vintage_falls_to_a_candidate_that_keeps_vintages(
    keys: None, world: object
) -> None:
    concept = catalog.get("us.unemployment.noncyclical_rate")  # cbo, then fred
    result = resolve(concept, as_of=dt.date(2025, 6, 30), registry=world)  # type: ignore[arg-type]
    assert result.source.provider == "cbo"
    assert result.source.vintage == "as_of:2025-06-30"
    assert result.source.realtime is not None
    unemployment = catalog.get("us.unemployment.rate")  # bls keeps no vintages
    again = resolve(unemployment, as_of=dt.date(2025, 6, 30), registry=world)  # type: ignore[arg-type]
    assert again.source.provider == "fred"
    assert again.source.fallback_chain == ("bls", "fred")
    assert [s.reason for s in again.skipped] == ["vintage_unsupported"]
    with pytest.raises(DataError, match="vintage_unsupported"):
        resolve(
            unemployment,
            as_of=dt.date(2025, 6, 30),
            strict=True,
            registry=world,  # type: ignore[arg-type]
        )


def test_a_concept_no_candidate_of_which_keeps_vintages_cannot_be_read_as_of_a_date(
    keys: None, world: object
) -> None:
    with pytest.raises(DataError, match="vintage_unsupported"):
        resolve(
            catalog.get("us.prices.cpi"),
            vintage="first_release",
            provider="bls",
            registry=world,  # type: ignore[arg-type]
        )


def test_the_fallback_to_fred_records_both_providers_in_the_chain(
    keys: None,
) -> None:
    fail = Fail()
    fail.errors["bea"] = DataError("BEA is down", provider="bea")
    result = resolve(catalog.get("us.output.real_gdp"), registry=world_registry(fail))
    assert result.source.provider == "fred"
    assert result.source.fallback_chain == ("bea", "fred")


def test_an_unknown_provider_in_the_registry_is_passed_over() -> None:
    empty = ProviderRegistry.from_providers()
    with pytest.raises(DataError, match="provider_unavailable"):
        resolve(catalog.get("us.unemployment.rate"), registry=empty)
    assert issubclass(ProviderNotFoundError, LookupError)


def test_derived_concepts_record_one_source_per_operand(
    keys: None, world: object
) -> None:
    for concept_id, count in (
        ("us.output_gap.real_potential", 2),
        ("us.fiscal.debt_to_gdp", 2),
        ("us.fiscal.primary_balance", 2),
    ):
        concept = catalog.get(concept_id)
        assert isinstance(concept.candidates[0], Derived)
        result = resolve(concept, registry=world)  # type: ignore[arg-type]
        assert len(result.sources) == count
        assert {s.concept for s in result.sources} == {concept_id}
        assert result.sources[0].transforms[-1] == concept.candidates[0].transform


def test_debt_to_gdp_is_a_ratio_of_debt_at_quarter_end_to_annual_gdp(
    keys: None, world: object
) -> None:
    result = resolve(catalog.get("us.fiscal.debt_to_gdp"), registry=world)  # type: ignore[arg-type]
    assert result.sources[0].transforms == (
        "convert(to=quarterly,method=last)",
        "ratio",
    )
    assert result.frame.meta.frequency.value == "quarterly"
