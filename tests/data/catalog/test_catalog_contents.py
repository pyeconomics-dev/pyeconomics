# tests/data/catalog/test_catalog_contents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What the shipped catalog holds, and the rules that keep it sound.

The minimum concept set of Phase 3 Step 11 is listed here id by id, so removing
one fails a test; the structural rules (every candidate's provider is registered,
every series key builds a request, derived concepts have operands and no loop,
tiers run originator to premium) run over every concept; and the released-concept
ledger rule is proven on a toy entry.
"""

from __future__ import annotations

import re

import pytest

from pyeconomics.core import UnitKind
from pyeconomics.core._released import Released
from pyeconomics.core.errors import RegistryError
from pyeconomics.core.provenance import CONCEPT_ID_PATTERN
from pyeconomics.data import (
    Mode,
    ObservationFrequency,
    SeasonalAdjustment,
    candidates_by_mode,
    catalog,
    registry,
)
from pyeconomics.data._released import CONCEPTS as RELEASED_CONCEPTS
from pyeconomics.data.catalog import checks
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Derived,
    Operand,
    Shape,
    Tier,
)
from pyeconomics.data.providers.rules import RULES, check_released_concepts

#: The minimum set of the roadmap's Step 11, one id per entry.
MINIMUM = {
    # US PCE and core PCE prices, CPI and core CPI: levels and year over year
    "us.prices.pce",
    "us.prices.pce_core",
    "us.inflation.pce.yoy",
    "us.inflation.pce_core.yoy",
    "us.prices.cpi",
    "us.prices.cpi_core",
    "us.inflation.cpi.yoy",
    "us.inflation.cpi_core.yoy",
    # the Dallas Fed trimmed-mean PCE (library-only: no originator provider)
    "us.inflation.pce_trimmed_mean.yoy",
    # labour and output
    "us.unemployment.rate",
    "us.unemployment.noncyclical_rate",
    "us.output.real_gdp",
    "us.output.potential_gdp",
    "us.output_gap.cbo",
    "us.output_gap.real_potential",
    "us.output.nominal_gdp",
    "us.output.nominal_gdp.yoy",
    # policy rates
    "us.policy_rate.effective",
    "us.policy_rate.target_upper",
    "us.policy_rate.target_lower",
    # Treasury yields, par curves and the GSW parameters
    "us.treasury.nominal_3m",
    "us.treasury.nominal_10y",
    "us.treasury.real_10y",
    "us.treasury.par_curve",
    "us.treasury.par_curve_real",
    "us.treasury.gsw_curve",
    # r*, the SEP and the SPF
    "us.neutral_rate.laubach_williams",
    "us.neutral_rate.hlw",
    "us.sep.medians",
    "us.sep.policy_rate_longer_run",
    "us.sep.core_pce_inflation",
    "us.sep.pce_inflation",
    "us.sep.unemployment",
    "us.sep.unemployment_longer_run",
    "us.spf.cpi.median_h4",
    "us.spf.core_pce.median_h4",
    "us.spf.unemployment.median_h0",
    "us.spf.cpi.median_10y",
    "us.spf.pce.median_10y",
    # fiscal
    "us.fiscal.federal_debt",
    "us.fiscal.debt_to_gdp",
    "us.fiscal.average_interest_rate",
    "us.fiscal.primary_balance",
    "us.fiscal.primary_balance_to_gdp",
    # Penn World Table by economy
    "pwt.rgdpna.us.annual",
    "pwt.rkna.gb.annual",
    "pwt.labsh.jp.annual",
    # factor and portfolio sets, monthly and daily
    "factors.ff3.us.monthly",
    "factors.ff3.us.daily",
    "factors.ff5.us.monthly",
    "factors.ff5.us.daily",
    "factors.momentum.us.monthly",
    "factors.momentum.us.daily",
    "portfolios.industry12.us.monthly",
    "portfolios.industry12.us.daily",
    "portfolios.size_bm25.us.monthly",
    "portfolios.size_bm25.us.daily",
    # Shiller's and Damodaran's market series
    "equity.shiller.us.monthly",
    "us.equity.cape",
    "us.equity.implied_erp",
    # euro area, UK and Canada: inflation, policy rates and output gaps
    "ea.inflation.hicp.yoy",
    "gb.inflation.cpi.yoy",
    "ca.inflation.cpi.yoy",
    "ea.policy_rate.headline",
    "gb.policy_rate.headline",
    "ca.policy_rate.headline",
    "ea.output_gap.oecd",
    "gb.output_gap.oecd",
    "ca.output_gap.oecd",
    "ea.neutral_rate.hlw",
    "ca.neutral_rate.hlw",
}


def test_every_concept_of_the_minimum_set_is_in_the_catalog() -> None:
    assert set(catalog.ids()) >= MINIMUM


def test_ids_are_sorted_unique_and_follow_the_grammar() -> None:
    ids = catalog.ids()
    assert list(ids) == sorted(set(ids))
    assert all(CONCEPT_ID_PATTERN.fullmatch(i) for i in ids)
    assert tuple(c.id for c in catalog.concepts()) == ids


def test_a_concept_is_found_by_id_and_a_miss_names_the_close_ones() -> None:
    assert catalog.get("us.unemployment.rate").title == "Unemployment rate"
    with pytest.raises(LookupError) as caught:
        catalog.get("us.unemployment.rat")
    assert "us.unemployment.rate" in str(caught.value)


def test_the_installed_registry_and_the_catalog_are_sound_together() -> None:
    registry.validate()
    assert checks.problems(registry.installed(), deep=True) == []


def test_every_candidate_names_a_registered_provider_that_can_fetch() -> None:
    known = set(registry.ids())
    named = {
        c.provider
        for concept in catalog.concepts()
        for c in concept.candidates
        if isinstance(c, Candidate)
    }
    assert named <= known


def test_candidates_run_originator_then_aggregator_then_premium() -> None:
    order = list(Tier)
    for concept in catalog.concepts():
        tiers = [order.index(c.tier) for c in concept.candidates]
        assert tiers == sorted(tiers), concept.id
        assert concept.candidates[0].tier is not Tier.PREMIUM or len(tiers) == 1


def test_every_non_trivial_concept_names_its_definition_in_words() -> None:
    for concept in catalog.concepts():
        assert len(concept.definition) >= 40, concept.id
        assert concept.title, concept.id
        assert concept.section != "Other", concept.id


def test_titles_are_unique_so_a_search_shows_distinct_names() -> None:
    titles = [c.title for c in catalog.concepts()]
    assert len(set(titles)) == len(titles)


def test_the_trimmed_mean_has_no_hosted_candidate_and_the_unemployment_rate_does() -> (
    None
):
    trimmed = candidates_by_mode("us.inflation.pce_trimmed_mean.yoy")
    assert [c.provider for c in trimmed[Mode.LIBRARY]] == ["fred"]
    assert trimmed[Mode.HOSTED] == ()
    unemployment = candidates_by_mode("us.unemployment.rate")
    assert [c.provider for c in unemployment[Mode.LIBRARY]] == ["bls", "fred"]
    assert [c.provider for c in unemployment[Mode.HOSTED]] == ["bls"]


def test_hosted_mode_never_lists_a_library_only_candidate_for_any_concept() -> None:
    for concept in catalog.concepts():
        for hosted in candidates_by_mode(concept)[Mode.HOSTED]:
            assert hosted.hosted_allowed
            assert hosted.licence is None or hosted.licence.hosted_allowed


def test_a_derived_concept_is_derived_from_series_concepts_only() -> None:
    derived = [
        (concept, c)
        for concept in catalog.concepts()
        for c in concept.candidates
        if isinstance(c, Derived)
    ]
    assert {concept.id for concept, _ in derived} >= {
        "us.output_gap.real_potential",
        "us.fiscal.debt_to_gdp",
        "us.fiscal.primary_balance",
        "us.fiscal.primary_balance_to_gdp",
    }
    for concept, candidate in derived:
        assert concept.shape is Shape.SERIES
        for operand in candidate.operands:
            assert catalog.get(operand.concept).shape is Shape.SERIES


def test_the_treasury_curves_need_a_window_and_say_so() -> None:
    for concept_id in (
        "us.treasury.par_curve",
        "us.treasury.par_curve_real",
        "us.treasury.nominal_3m",
        "us.treasury.nominal_10y",
        "us.treasury.real_10y",
    ):
        assert catalog.get(concept_id).needs_window


def test_the_sep_concepts_take_a_checked_meeting_parameter() -> None:
    medians = catalog.get("us.sep.medians")
    (parameter,) = medians.parameters
    assert parameter.name == "meeting"
    assert parameter.check("2026-09-16") == "2026-09-16"
    for bad in ("", "2026-9-16", "2026-09-16 ", "../x", "x" * 40):
        with pytest.raises(Exception, match="meeting"):
            parameter.check(bad)


def test_the_sep_series_concepts_read_one_median_each() -> None:
    for name in ("core_pce_inflation", "pce_inflation", "unemployment"):
        concept = catalog.get(f"us.sep.{name}")
        assert concept.shape is Shape.SERIES
        assert {p.name for p in concept.parameters} == {"meeting", "year"}
        (candidate,) = concept.candidates
        assert isinstance(candidate, Candidate)
        assert candidate.column is not None
        assert candidate.column.endswith("_median_{year}")
    longer_run = catalog.get("us.sep.unemployment_longer_run")
    assert [p.name for p in longer_run.parameters] == ["meeting"]


#: FRED's daily rate series, which ALFRED refuses a real-time request for (checked
#: live on 2026-10-18 for every FRED candidate in the catalog).
NO_ALFRED = {"DFEDTARL", "DFEDTARU", "DFII10", "DGS10", "DGS3MO", "EFFR"}


def test_the_fred_series_alfred_keeps_no_vintages_of_are_marked() -> None:
    fred = {
        c.series: c.vintages
        for concept in catalog.concepts()
        for c in concept.candidates
        if isinstance(c, Candidate) and c.provider == "fred"
    }
    assert {series for series, kept in fred.items() if not kept} == NO_ALFRED
    others = {
        c.provider
        for concept in catalog.concepts()
        for c in concept.candidates
        if isinstance(c, Candidate) and not c.vintages
    }
    assert others == {"fred"}


def test_the_target_range_records_the_2008_switch() -> None:
    for side in ("upper", "lower"):
        concept = catalog.get(f"us.policy_rate.target_{side}")
        assert "2008-12-16" in concept.definition


def test_candidate_series_keys_hold_only_declared_placeholders() -> None:
    for concept in catalog.concepts():
        declared = {p.name for p in concept.parameters}
        for candidate in concept.candidates:
            if isinstance(candidate, Candidate):
                assert candidate.placeholders == declared, concept.id
                assert not re.search(r"[\s]", candidate.series), concept.id


# --- the released-concept ledger ----------------------------------------------


def test_the_shipped_ledger_is_empty_until_the_first_release_and_validate_passes() -> (
    None
):
    assert len(RELEASED_CONCEPTS) == 0
    registry.validate()
    assert "released-concept" in RULES


def test_a_released_concept_missing_from_the_catalog_is_reported() -> None:
    ledger = {
        "us.unemployment.rate": Released("us.unemployment.rate", "1.0.0a2"),
        "us.gone.concept": Released("us.gone.concept", "1.0.0a2"),
    }
    problems = check_released_concepts(ledger, set(catalog.ids()))
    assert [str(p) for p in problems] == [
        (
            "us.gone.concept: [released-concept] no longer in the catalog; a released "
            "concept id is never deleted or renamed (ADR-0011 decision 15)"
        )
    ]
    with pytest.raises(RegistryError, match=r"\[released-concept\]"):
        registry.validate(released_concepts=ledger)


def test_a_malformed_ledger_entry_is_reported() -> None:
    renamed = {"us.old.name": Released("us.new.name", "1.0.0a2")}
    badversion = {"us.unemployment.rate": Released("us.unemployment.rate", "one")}
    badid = {"Not An Id": Released("Not An Id", "1.0.0a2")}
    for ledger in (renamed, badversion, badid):
        (problem,) = check_released_concepts(ledger, set(catalog.ids()))
        assert problem.rule == "released-concept"
        assert "malformed" in problem.detail


def test_a_ledger_that_names_only_catalog_concepts_is_sound() -> None:
    ledger = {
        concept_id: Released(concept_id, "1.0.0a2") for concept_id in catalog.ids()
    }
    assert check_released_concepts(ledger, set(catalog.ids())) == []
    registry.validate(released_concepts=ledger)


def test_the_catalog_structure_rules_each_catch_a_toy_flaw(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def toy(concept_id: str, *candidates: Candidate | Derived) -> Concept:
        return Concept(
            id=concept_id,
            title=concept_id,
            definition="A toy concept that breaks one structural rule on purpose.",
            unit_kind=UnitKind.RATE,
            frequency=ObservationFrequency.MONTHLY,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            candidates=candidates,
        )

    toys = {
        "us.toy.ghost": toy("us.toy.ghost", Candidate(provider="nobody", series="X")),
        "us.toy.loop": toy(
            "us.toy.loop",
            Derived(
                operands=(Operand("us.toy.loop"), Operand("us.toy.other")),
                transform="ratio",
            ),
        ),
        "us.toy.other": toy(
            "us.toy.other", Candidate(provider="fred", series="UNRATE")
        ),
        "us.toy.orphan": toy(
            "us.toy.orphan",
            Derived(
                operands=(Operand("us.toy.nothing"), Operand("us.toy.other")),
                transform="ratio",
            ),
        ),
        "us.toy.badkey": toy(
            "us.toy.badkey", Candidate(provider="bls", series="bad key!")
        ),
    }
    monkeypatch.setattr(checks, "CONCEPTS", toys)
    found = {(p.provider, p.rule) for p in checks.problems(registry.installed())}
    assert ("us.toy.ghost", "concept-provider") in found
    assert ("us.toy.loop", "concept-cycle") in found
    assert ("us.toy.orphan", "concept-operand") in found
    assert ("us.toy.badkey", "concept-series") in found
    assert set(checks.RULES) == {
        "concept-provider",
        "concept-series",
        "concept-operand",
        "concept-cycle",
    }
