# tests/data/catalog/test_live_concepts.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every catalog concept against the real sources (``uv run pytest -m live``).

The weekly live run (providers-live.yml) executes this beside the providers' own
contract cases. For each concept it asks every candidate in turn, one provider
at a time and strictly, so a wrong series key, a changed source or a definition
that drifted fails here and names the candidate. The same concepts are proven
offline against synthetic stand-ins (test_world_resolution.py) and, where an
originator has a recording, through the real parser (test_recorded_concepts.py).

A generated family is sampled rather than repeated: the Penn World Table for
the United States in every variable and for every economy in real GDP, and the
SPF at the survey quarter and four quarters ahead for every variable. A
candidate whose key is not configured on the machine is skipped; the weekly run
configures the four keys (FRED, BLS, BEA, Census).
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

from pyeconomics import data
from pyeconomics.data import Mode, ObservationFrequency, catalog
from pyeconomics.data.catalog.definitions import Candidate, Concept
from pyeconomics.data.credentials import has_key

pytestmark = pytest.mark.live

_SPAN = {
    ObservationFrequency.DAILY: 60,
    ObservationFrequency.BUSINESS_DAILY: 60,
    ObservationFrequency.WEEKLY: 120,
    ObservationFrequency.MONTHLY: 3 * 366,
    ObservationFrequency.QUARTERLY: 5 * 366,
    ObservationFrequency.SEMIANNUAL: 8 * 366,
    ObservationFrequency.ANNUAL: 15 * 366,
    ObservationFrequency.IRREGULAR: 3 * 366,
}
_SAMPLED_PWT = {"us"}
_SAMPLED_HORIZONS = {"median_h0", "median_h4", "median_10y"}


def sampled(concept: Concept) -> bool:
    """Whether the live run asks this concept (a family is sampled)."""
    parts = concept.id.split(".")
    if parts[0] == "pwt":
        return parts[2] in _SAMPLED_PWT or parts[1] == "rgdpna"
    if parts[:2] == ["us", "spf"]:
        return parts[3] in _SAMPLED_HORIZONS
    return True


def window(concept: Concept) -> dict[str, Any]:
    """Return a recent window sized to the concept's frequency."""
    today = dt.datetime.now(dt.UTC).date()
    arguments: dict[str, Any] = {
        "start": today - dt.timedelta(days=_SPAN[concept.frequency])
    }
    if concept.needs_window:
        arguments["end"] = today
    if concept.parameters:
        arguments["parameters"] = {p.name: p.example for p in concept.parameters}
    return arguments


def pairs() -> list[tuple[str, str]]:
    """Every sampled (concept id, provider id) over the catalog's candidates."""
    found: list[tuple[str, str]] = []
    for concept in catalog.concepts():
        if sampled(concept):
            found.extend(
                (concept.id, provider)
                for provider in dict.fromkeys(
                    c.provider for c in concept.candidates if isinstance(c, Candidate)
                )
            )
    return found


def _skip_without_key(provider: str) -> None:
    info = data.registry.installed().provider_class(provider).info
    if info.auth.kind.value == "key" and info.auth.required and not has_key(provider):
        pytest.skip(f"no {info.key_variable} configured on this machine")


@pytest.mark.parametrize(("concept_id", "provider"), pairs())
def test_live_each_candidate_answers_its_concept(
    concept_id: str, provider: str
) -> None:
    _skip_without_key(provider)
    concept = catalog.get(concept_id)
    result = data.get(concept_id, provider=provider, strict=True, **window(concept))
    assert len(result.frame.index) > 0
    assert result.source.provider == provider
    assert result.source.concept == concept_id
    assert result.skipped == ()


DERIVED = [
    c.id
    for c in catalog.concepts()
    if isinstance(c.candidates[0], data.catalog.Derived)
]


@pytest.mark.parametrize("concept_id", DERIVED)
def test_live_a_derived_concept_resolves_from_its_operands(concept_id: str) -> None:
    concept = catalog.get(concept_id)
    result = data.get(concept_id, mode=Mode.HOSTED, **window(concept))
    assert len(result.frame.index) > 0
    assert len(result.sources) == 2
    assert {s.concept for s in result.sources} == {concept_id}


def test_live_hosted_mode_serves_an_originator_and_refuses_the_trimmed_mean() -> None:
    served = data.get(
        "us.policy_rate.effective",
        mode=Mode.HOSTED,
        **window(catalog.get("us.policy_rate.effective")),
    )
    assert served.source.licence.hosted_allowed
    with pytest.raises(data.LicenceError, match="library-only"):
        data.get("us.inflation.pce_trimmed_mean.yoy", mode=Mode.HOSTED)


def test_live_an_as_of_request_reads_the_alfred_vintage_in_force() -> None:
    _skip_without_key("fred")
    as_of = dt.date(2020, 6, 30)
    result = data.get(
        "us.output.real_gdp", as_of=as_of, start=dt.date(2018, 1, 1), end=as_of
    )
    assert result.source.provider == "fred"  # BEA's API keeps no vintages
    assert result.source.vintage == "as_of:2020-06-30"
    assert result.source.realtime is not None
    assert result.source.realtime.covers(as_of)
    (skip,) = result.skipped  # BEA was passed over: no vintages, or no key
    assert skip.provider == "bea"
    assert skip.reason in {"vintage_unsupported", "key_missing"}
