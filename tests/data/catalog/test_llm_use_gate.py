# tests/data/catalog/test_llm_use_gate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``llm_use`` gate in the data layer (Phase 4 Step 8; ADR-0012 decision 14).

Under an :class:`~pyeconomics.core.provenance.LlmUsePolicy` the resolver passes
over a candidate whose source, or whose series' own terms, the policy does not
permit (the skip reason ``llm_use``) and fails over; with no candidate left it
raises :class:`~pyeconomics.data.LlmUseError`, the ``llm-use-forbidden`` problem.
A provider series is refused the same way, before the request when its
provider's terms say so. The opt-in to unclear data is configuration only.
Without a policy nothing changes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from catalog_support import HOSTED_TERMS, monthly
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse, LlmUsePolicy
from pyeconomics.data import (
    DataError,
    LicenceError,
    LlmUseError,
    Mode,
    ObservationFrequency,
    SeasonalAdjustment,
    api,
    catalog,
    resolve,
    settings,
)
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Tier,
)
from pyeconomics.data.config import configure, reset
from pyeconomics.data.resolver import REASONS
from pyeconomics.surfaces.documents import jsonable
from pyeconomics.surfaces.problems import problem_for

if TYPE_CHECKING:
    from pyeconomics.data import DataProvider

ALLOWED_ONLY = LlmUsePolicy.ALLOWED_ONLY
ALLOW_UNCLEAR = LlmUsePolicy.ALLOW_UNCLEAR
DATA = [100.0 + i for i in range(24)]


def concept(
    *candidates: Candidate | Derived, concept_id: str = "us.test.value"
) -> Concept:
    return Concept(
        id=concept_id,
        title="A test concept",
        definition="A concept made for a test of the llm_use gate.",
        unit_kind=UnitKind.INDEX_LEVEL,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=candidates,
    )


def source(
    provider: str, series: str, use: LlmUse = LlmUse.ALLOWED, **meta: Any
) -> type[DataProvider]:
    """A scripted provider of one series, its frame under its provider's terms."""
    meta.setdefault("terms", HOSTED_TERMS.with_overrides(llm_use=use))
    frame = monthly(DATA, provider=provider, series_id=series, **meta)
    return scripted(provider, {series: frame}, llm_use=use)


def test_the_policy_permits_allowed_data_and_unclear_only_by_opt_in() -> None:
    permits = {
        (policy, use): policy.permits(use) for policy in LlmUsePolicy for use in LlmUse
    }
    assert permits == {
        (ALLOWED_ONLY, LlmUse.ALLOWED): True,
        (ALLOWED_ONLY, LlmUse.UNCLEAR): False,
        (ALLOWED_ONLY, LlmUse.FORBIDDEN): False,
        (ALLOW_UNCLEAR, LlmUse.ALLOWED): True,
        (ALLOW_UNCLEAR, LlmUse.UNCLEAR): True,
        (ALLOW_UNCLEAR, LlmUse.FORBIDDEN): False,
    }
    assert "llm_use" in REASONS


def test_a_forbidden_source_is_passed_over_before_any_request() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    allowed = source("beta", "B")
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    result = resolve(
        found, registry=registry_of(forbidden, allowed), llm_use=ALLOWED_ONLY
    )
    assert result.source.provider == "beta"
    assert calls_of(forbidden) == []
    (skip,) = result.skipped
    assert (skip.provider, skip.reason, skip.llm_use) == (
        "alpha",
        "llm_use",
        LlmUse.FORBIDDEN,
    )
    assert (skip.licence, skip.terms_url) == (
        LicenceClass.HOSTED_SAFE,
        HOSTED_TERMS.terms_url,
    )
    assert "forbidden" in skip.detail
    assert "skipped_alpha_llm_use" in result.source.warnings
    assert result.source.fallback_chain == ("alpha", "beta")


@pytest.mark.parametrize(
    ("policy", "expected"), [(ALLOWED_ONLY, "beta"), (ALLOW_UNCLEAR, "alpha")]
)
def test_an_unclear_source_is_used_only_with_the_opt_in(
    policy: LlmUsePolicy, expected: str
) -> None:
    unclear = source("alpha", "A", LlmUse.UNCLEAR)
    allowed = source("beta", "B")
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    result = resolve(found, registry=registry_of(unclear, allowed), llm_use=policy)
    assert result.source.provider == expected


def test_without_a_policy_nothing_changes() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    found = concept(Candidate(provider="alpha", series="A"))
    result = resolve(found, registry=registry_of(forbidden))
    assert result.source.provider == "alpha"
    assert result.source.llm_use is LlmUse.FORBIDDEN
    assert result.skipped == ()


def test_a_series_level_marker_is_judged_after_the_fetch_and_fails_over() -> None:
    marked_terms = HOSTED_TERMS.with_overrides(llm_use=LlmUse.FORBIDDEN)
    marked = source("alpha", "A", terms=marked_terms)  # the provider is allowed
    allowed = source("beta", "B")
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    result = resolve(found, registry=registry_of(marked, allowed), llm_use=ALLOWED_ONLY)
    assert result.source.provider == "beta"
    assert len(calls_of(marked)) == 1
    (skip,) = result.skipped
    assert (skip.reason, skip.llm_use) == ("llm_use", LlmUse.FORBIDDEN)
    assert "the series' terms" in skip.detail


def test_with_no_candidate_left_the_error_names_the_concept_and_the_terms() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    unclear = source("beta", "B", LlmUse.UNCLEAR)
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    with pytest.raises(LlmUseError) as caught:
        resolve(found, registry=registry_of(forbidden, unclear), llm_use=ALLOWED_ONLY)
    error = caught.value
    assert isinstance(error, LicenceError)
    assert error.concept == "us.test.value"
    assert (error.provider, error.llm_use, error.licence) == (
        "alpha",
        LlmUse.FORBIDDEN,
        LicenceClass.HOSTED_SAFE,
    )
    assert "us.test.value has no source" in str(error)
    assert "allowed-only" in str(error)
    problem = problem_for(error)
    assert (problem.slug, problem.status, problem.exit_code) == (
        "llm-use-forbidden",
        403,
        6,
    )
    assert problem.terms == HOSTED_TERMS.terms_url


def test_hosted_refusals_and_llm_use_refusals_together_are_an_llm_use_error() -> None:
    library = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha")},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    forbidden = source("beta", "B", LlmUse.FORBIDDEN)
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    registry = registry_of(library, forbidden)
    with pytest.raises(LlmUseError):
        resolve(found, mode=Mode.HOSTED, registry=registry, llm_use=ALLOWED_ONLY)
    # Without the policy, hosted mode's own licence refusal stays what it was.
    only_library = concept(Candidate(provider="alpha", series="A"))
    with pytest.raises(LicenceError) as caught:
        resolve(only_library, mode=Mode.HOSTED, registry=registry_of(library))
    assert not isinstance(caught.value, LlmUseError)


def test_a_refusal_mixed_with_another_failure_is_a_data_error() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    missing = scripted("beta", {})
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    with pytest.raises(DataError) as caught:
        resolve(found, registry=registry_of(forbidden, missing), llm_use=ALLOWED_ONLY)
    assert not isinstance(caught.value, LicenceError)
    assert "llm_use" in str(caught.value)


def test_a_derived_concept_passes_an_operands_refusal_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    allowed = source("beta", "B")
    left = concept(Candidate(provider="alpha", series="A"), concept_id="us.toy.left")
    right = concept(Candidate(provider="beta", series="B"), concept_id="us.toy.right")
    monkeypatch.setattr(
        catalog, "CONCEPTS", {"us.toy.left": left, "us.toy.right": right}
    )
    derived = Concept(
        id="us.toy.gap",
        title="A derived test concept",
        definition="A concept derived from two others for a test of the gate.",
        unit_kind=UnitKind.RATIO,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Derived(
                operands=(Operand("us.toy.left"), Operand("us.toy.right")),
                transform="ratio",
            ),
        ),
    )
    registry = registry_of(forbidden, allowed)
    with pytest.raises(LlmUseError) as caught:
        resolve(derived, registry=registry, llm_use=ALLOWED_ONLY)
    assert caught.value.concept == "us.toy.gap"
    assert "derived" in str(caught.value)
    assert resolve(derived, registry=registry).concept == "us.toy.gap"


def test_a_skip_reads_in_documents_and_exports_as_it_did_before_the_gate() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    allowed = source("beta", "B")
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    (skip,) = resolve(
        found, registry=registry_of(forbidden, allowed), llm_use=ALLOWED_ONLY
    ).skipped
    assert set(jsonable(skip)) == {
        "provider",
        "series",
        "reason",
        "detail",
        "licence",
        "terms_url",
    }
    assert jsonable(skip)["licence"] == "hosted-safe"


def test_a_provider_series_the_policy_refuses_is_never_requested() -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    registry = registry_of(forbidden)
    with pytest.raises(LlmUseError) as caught:
        api.get("alpha:A", registry=registry, llm_use=ALLOWED_ONLY)
    assert calls_of(forbidden) == []
    assert caught.value.llm_use is LlmUse.FORBIDDEN
    assert "alpha:A's terms" in str(caught.value)
    assert api.get("alpha:A", registry=registry).source.provider == "alpha"


def test_a_provider_series_with_its_own_marker_is_refused_after_the_fetch() -> None:
    marked = source(
        "alpha", "A", terms=HOSTED_TERMS.with_overrides(llm_use=LlmUse.UNCLEAR)
    )
    registry = registry_of(marked)
    with pytest.raises(LlmUseError):
        api.get("alpha:A", registry=registry, llm_use=ALLOWED_ONLY)
    assert len(calls_of(marked)) == 1
    found = api.get("alpha:A", registry=registry, llm_use=ALLOW_UNCLEAR)
    assert found.source.llm_use is LlmUse.UNCLEAR


def test_a_concept_target_passes_the_policy_to_the_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    forbidden = source("alpha", "A", LlmUse.FORBIDDEN)
    allowed = source("beta", "B")
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
        concept_id="us.toy.value",
    )
    monkeypatch.setattr(catalog, "CONCEPTS", {"us.toy.value": found})
    resolved = api.get(
        "us.toy.value", registry=registry_of(forbidden, allowed), llm_use="allowed-only"
    )
    assert resolved.source.provider == "beta"


# --- the opt-in is configuration only -------------------------------------------


def test_the_opt_in_is_off_by_default(isolated: object) -> None:
    assert settings().allow_unclear_llm_use is False
    assert settings().llm_use_policy is ALLOWED_ONLY


def test_the_environment_variable_opts_in(
    isolated: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_ALLOW_UNCLEAR_LLM_USE", "1")
    reset()
    assert settings().llm_use_policy is ALLOW_UNCLEAR


def test_pyeconomics_toml_opts_in(
    isolated: object, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = isolated.config_dir  # type: ignore[attr-defined]
    home.mkdir(parents=True, exist_ok=True)
    (home / "pyeconomics.toml").write_bytes(b"allow_unclear_llm_use = true\n")
    reset()
    assert settings().llm_use_policy is ALLOW_UNCLEAR


def test_configure_does_not_take_the_opt_in(isolated: object) -> None:
    with pytest.raises(TypeError):
        configure(allow_unclear_llm_use=True)  # type: ignore[call-arg] # ty: ignore[unknown-argument]
