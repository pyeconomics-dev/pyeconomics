# tests/data/catalog/test_public_api.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics.data.get``, ``search``, ``describe``, ``vintages`` and ``sources``.

Phase 4's ``data`` commands wrap these unchanged, so the contract is pinned here:
what each accepts (a concept id, ``provider:series`` or a provider id), what it
returns, and what it refuses.
"""

from __future__ import annotations

import datetime as dt
import secrets

import pytest
from catalog_support import LIBRARY_TERMS, monthly
from catalog_world import world_registry
from scripted import calls_of, registry_of, scripted

from pyeconomics import data
from pyeconomics.core import InputError, UnitKind
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import (
    Capability,
    ConceptInfo,
    ConceptNotFoundError,
    DataError,
    LicenceError,
    Mode,
    ObservationFrequency,
    OfflineError,
    ProviderNotFoundError,
    SearchHit,
    SeasonalAdjustment,
    catalog,
)
from pyeconomics.data.catalog.definitions import Candidate, Concept

SERIES = monthly([float(i) for i in range(40)], provider="alpha", series_id="A")


def concept_info(target: str) -> ConceptInfo:
    """Describe a concept id and narrow the answer for a typed test."""
    found = data.describe(target)
    assert isinstance(found, ConceptInfo)
    return found


# --- get ----------------------------------------------------------------------


def test_get_reads_a_provider_series_by_its_address() -> None:
    alpha = scripted("alpha", {"A": SERIES})
    result = data.get(
        "alpha:A",
        start=dt.date(2025, 1, 1),
        end=dt.date(2025, 6, 30),
        registry=registry_of(alpha),
    )
    assert result.concept is None
    assert result.skipped == ()
    assert result.frame.index[0] >= dt.date(2025, 1, 1)
    assert result.source.provider == "alpha"
    assert result.source.series_id == "A"
    assert result.source.concept is None
    assert result.source.vintage == "latest"


def test_a_series_key_may_hold_a_colon() -> None:
    frame = monthly([1.0, 2.0], provider="alpha", series_id="h15:RIFSPFF_N.B")
    alpha = scripted("alpha", {"h15:RIFSPFF_N.B": frame})
    result = data.get("alpha:h15:RIFSPFF_N.B", registry=registry_of(alpha))
    assert result.source.series_id == "h15:RIFSPFF_N.B"


def test_get_refuses_a_provider_that_disagrees_and_parameters_it_cannot_take() -> None:
    alpha = scripted("alpha", {"A": SERIES})
    registry = registry_of(alpha)
    with pytest.raises(InputError, match="not beta"):
        data.get("alpha:A", provider="beta", registry=registry)
    assert (
        data.get("alpha:A", provider="alpha", registry=registry).source.provider
        == "alpha"
    )
    with pytest.raises(InputError, match="no concept parameters"):
        data.get("alpha:A", parameters={"meeting": "2026-09-16"}, registry=registry)


def test_get_refuses_a_bare_provider_a_bad_address_and_an_unknown_provider() -> None:
    alpha = scripted("alpha", {"A": SERIES})
    registry = registry_of(alpha)
    with pytest.raises(InputError, match="is a provider"):
        data.get("alpha", registry=registry)
    for bad in ("", "UPPER:A", "alpha:", "has space", "x" * 300, "a://b"):
        with pytest.raises(InputError):
            data.get(bad, registry=registry)
    with pytest.raises(ProviderNotFoundError, match="did you mean"):
        data.get("alphx:A", registry=registry)


def test_a_provider_series_in_hosted_mode_is_refused_by_class_before_a_request() -> (
    None
):
    closed = scripted(
        "alpha",
        {"A": monthly([1.0], provider="alpha", terms=LIBRARY_TERMS)},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    registry = registry_of(closed)
    with pytest.raises(LicenceError, match="library-only"):
        data.get("alpha:A", mode=Mode.HOSTED, registry=registry)
    assert calls_of(closed) == []
    assert (
        data.get("alpha:A", registry=registry).source.licence
        is LicenceClass.LIBRARY_ONLY
    )


def test_a_vintage_of_a_provider_series_that_keeps_none_is_an_error() -> None:
    alpha = scripted("alpha", {"A": SERIES})
    with pytest.raises(DataError, match="keeps no vintages"):
        data.get("alpha:A", as_of=dt.date(2020, 1, 1), registry=registry_of(alpha))
    with pytest.raises(InputError, match="not both"):
        data.get(
            "alpha:A",
            as_of=dt.date(2020, 1, 1),
            vintage="latest",
            registry=registry_of(alpha),
        )


def test_get_resolves_a_concept_through_the_catalog(isolated: object) -> None:
    for provider in ("fred", "bls", "bea"):
        isolated.keyring.set_password(  # type: ignore[attr-defined]
            "pyeconomics", provider, secrets.token_hex(16)
        )
    world = world_registry()
    result = data.get("us.unemployment.rate", registry=world)
    assert result.concept == "us.unemployment.rate"
    assert result.source.provider == "bls"
    by_provider = data.get("us.unemployment.rate", provider="fred", registry=world)
    assert by_provider.source.provider == "fred"
    with pytest.raises(ConceptNotFoundError):
        data.get("us.unemployment.rat", registry=world)


def test_get_passes_a_concepts_parameters_and_window_through() -> None:
    world = world_registry()
    result = data.get(
        "us.sep.policy_rate_longer_run",
        parameters={"meeting": "2026-09-16"},
        registry=world,
    )
    assert result.source.series_id.startswith("sep:2026-09-16")
    treasury = data.get(
        "us.treasury.nominal_10y",
        start=dt.date(2025, 3, 1),
        end=dt.date(2026, 6, 30),
        registry=world,
    )
    assert treasury.source.provider == "treasury"


# --- sources and describe -----------------------------------------------------


def test_sources_lists_every_provider_with_class_notice_and_key() -> None:
    listed = data.sources()
    assert [s.id for s in listed] == sorted(data.registry.ids())
    by_id = {s.id: s for s in listed}
    fred = by_id["fred"]
    assert fred.licence is LicenceClass.LIBRARY_ONLY
    assert not fred.hosted_allowed
    assert fred.key_variable == "FRED_API_KEY"
    assert fred.key_required
    assert fred.key_configured is False  # the test's isolated chain holds none
    assert fred.notice
    treasury = by_id["treasury"]
    assert treasury.hosted_allowed
    assert treasury.key_variable is None
    assert treasury.key_configured is None
    assert by_id["bls"].key_required is False  # the key only raises BLS's limits
    assert all(s.attribution and s.terms_url.startswith("https://") for s in listed)
    assert all("fetch" in s.capabilities or "records" in s.capabilities for s in listed)


def test_sources_reports_a_configured_key_without_its_value(isolated: object) -> None:
    key = secrets.token_hex(16)
    isolated.keyring.set_password("pyeconomics", "fred", key)  # type: ignore[attr-defined]
    fred = next(s for s in data.sources() if s.id == "fred")
    assert fred.key_configured is True
    assert key not in repr(fred)


def test_describe_a_concept_lists_its_candidates() -> None:
    info = concept_info("us.unemployment.noncyclical_rate")
    assert info.concept.id == "us.unemployment.noncyclical_rate"
    assert [(c.provider, c.keeps_vintages) for c in info.candidates] == [
        ("cbo", True),
        ("fred", True),
    ]
    assert [c.provider for c in info.usable_in(Mode.HOSTED)] == ["cbo"]
    derived = concept_info("us.fiscal.debt_to_gdp")
    assert derived.candidates[0].provider == "derived"
    assert derived.candidates[0].derived_from == (
        "us.fiscal.federal_debt",
        "us.output.nominal_gdp",
    )
    assert derived.candidates[0].hosted_allowed


def test_describe_a_provider_gives_its_terms_and_a_series_asks_the_provider() -> None:
    assert data.describe("fred").licence is LicenceClass.LIBRARY_ONLY  # type: ignore[union-attr]
    alpha = scripted(
        "alpha",
        {"A": SERIES},
        capabilities=(Capability.FETCH, Capability.DESCRIBE),
        described=SERIES.meta,
    )
    described = data.describe("alpha:A", registry=registry_of(alpha))
    assert described.series_id == "A"  # type: ignore[union-attr]
    assert described.provider == "alpha"  # type: ignore[union-attr]
    with pytest.raises(ConceptNotFoundError):
        data.describe("us.nothing.here")
    with pytest.raises(InputError):
        data.describe("not a target")


# --- vintages -----------------------------------------------------------------


def test_vintages_lists_the_dates_a_series_changed() -> None:
    dates = (dt.date(2020, 1, 30), dt.date(2020, 2, 27))
    alpha = scripted(
        "alpha",
        {"A": SERIES},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        changed=dates,
    )
    assert data.vintages("alpha:A", registry=registry_of(alpha)) == dates
    with pytest.raises(InputError, match="names a provider"):
        data.vintages("alpha", registry=registry_of(alpha))


def test_vintages_of_a_concept_asks_the_first_candidate_that_keeps_them(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dates = (dt.date(2024, 2, 7), dt.date(2024, 6, 18))
    plain = scripted("plain", {"P": SERIES})
    vintaged = scripted(
        "vintaged",
        {"V": SERIES},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        changed=dates,
    )
    toy = Concept(
        id="us.toy.value",
        title="Toy",
        definition="A toy concept for the vintages test of the public API.",
        unit_kind=UnitKind.INDEX_LEVEL,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(provider="plain", series="P"),
            Candidate(provider="vintaged", series="V"),
        ),
    )
    monkeypatch.setattr(catalog, "CONCEPTS", {toy.id: toy})
    assert data.vintages(toy.id, registry=registry_of(plain, vintaged)) == dates
    with pytest.raises(DataError, match="no candidate that keeps vintages"):
        data.vintages(toy.id, registry=registry_of(plain))


def test_vintages_in_offline_mode_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    alpha = scripted(
        "alpha", {"A": SERIES}, capabilities=(Capability.FETCH, Capability.VINTAGES)
    )
    data.configure(offline=True)
    with pytest.raises(OfflineError):
        data.vintages("alpha:A", registry=registry_of(alpha))


# --- search -------------------------------------------------------------------


def test_search_finds_concepts_offline_and_ranks_the_topic_first() -> None:
    result = data.search("unemployment rate", providers=())
    assert result.skipped == ()
    first = result.hits[0]
    assert (first.kind, first.id) == ("concept", "us.unemployment.rate")
    assert first.provider is None
    assert first.frequency is ObservationFrequency.MONTHLY
    assert all(hit.kind == "concept" for hit in result.hits)


def test_search_honours_the_limit_and_finds_nothing_for_nonsense() -> None:
    assert len(data.search("inflation", 3, providers=()).hits) == 3
    assert data.search("zzzzqqqq", providers=()).hits == ()
    assert data.search("a", providers=()).hits == ()  # a one-letter token is ignored
    for bad in (0, 101, True):
        with pytest.raises(InputError):
            data.search("inflation", bad, providers=())
    with pytest.raises(InputError):
        data.search("", providers=())


def test_search_asks_the_providers_that_can_and_says_why_it_skipped_the_rest(
    isolated: object,
) -> None:
    found = (
        SearchHit(
            series_id="A1", title="Alpha one", frequency=ObservationFrequency.MONTHLY
        ),
    )
    searchable = scripted(
        "alpha",
        {"A": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        hits=found,
    )
    keyed = scripted(
        "keyed",
        {"K": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        keyed=True,
    )
    closed = scripted(
        "closed",
        {"C": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        licence=LicenceClass.LIBRARY_ONLY,
    )
    broken = scripted(
        "broken",
        {"B": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        hits=DataError("the source is down", provider="broken"),
    )
    mute = scripted("mute", {"M": SERIES})
    registry = registry_of(searchable, keyed, closed, broken, mute)
    result = data.search("zzqq nothing", 10, registry=registry)
    series = [h for h in result.hits if h.kind == "series"]
    assert [(h.id, h.provider) for h in series] == [("alpha:A1", "alpha")]
    reasons = dict(result.skipped)
    assert "ALPHA" not in reasons
    assert "no key: set KEYED_API_KEY" in reasons["keyed"]
    assert reasons["mute"] == "does not search"
    assert "source is down" in reasons["broken"]
    hosted = data.search("zzqq nothing", 10, mode=Mode.HOSTED, registry=registry)
    assert "library-only: hosted mode refuses it" in dict(hosted.skipped)["closed"]
    assert data.search(
        "zzqq nothing", 10, providers=("ghost",), registry=registry
    ).skipped == (("ghost", "not registered"),)


def test_a_search_stops_asking_providers_once_the_limit_is_met() -> None:
    first = scripted(
        "alpha",
        {"A": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        hits=(
            SearchHit(series_id="A1", title="One"),
            SearchHit(series_id="A2", title="Two"),
        ),
    )
    second = scripted(
        "beta",
        {"B": SERIES},
        capabilities=(Capability.FETCH, Capability.SEARCH),
        hits=(SearchHit(series_id="B1", title="Three"),),
    )
    result = data.search("zzqq nothing", 2, registry=registry_of(first, second))
    assert [h.id for h in result.hits] == ["alpha:A1", "alpha:A2"]
    assert result.skipped == ()


# --- the package surface ------------------------------------------------------


def test_the_data_package_exports_the_five_functions_and_their_values() -> None:
    for name in (
        "get",
        "search",
        "describe",
        "vintages",
        "sources",
        "resolve",
        "Resolved",
        "Skip",
        "SourceInfo",
        "ConceptInfo",
        "CandidateInfo",
        "SearchResult",
        "Hit",
        "ConceptNotFoundError",
        "candidates_by_mode",
        "catalog",
    ):
        assert name in data.__all__
        assert hasattr(data, name)


def test_a_resolved_exposes_its_first_source_and_its_providers() -> None:
    alpha = scripted("alpha", {"A": SERIES})
    result = data.get("alpha:A", registry=registry_of(alpha))
    assert result.source is result.sources[0]
    assert result.providers == ("alpha",)
