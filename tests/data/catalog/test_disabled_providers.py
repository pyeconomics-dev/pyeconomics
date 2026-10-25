# tests/data/catalog/test_disabled_providers.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``disabled_providers`` switch (issue #162; Phase 4 Step 7).

An operator turns a failing source off with ``PYECONOMICS_DISABLED_PROVIDERS``,
``pyeconomics.toml`` or ``configure``. A disabled provider is refused before any
cache read or request, by every public operation, whatever its own
``check_configuration`` does; a concept fails over to its next candidate, and
fails with ``SourceDisabledError`` when every candidate is disabled; ``sources()``
and the command line say so. The same change keeps the hosted server's own
secret out of the settings' credential-name refusal, and gives a concept's hosted
refusal its first candidate's terms page.
"""

from __future__ import annotations

import datetime as dt
import secrets
from typing import TYPE_CHECKING

import pytest
from catalog_support import as_series, monthly
from cli_support import cli
from scripted import calls_of, registry_of, scripted

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import (
    Capability,
    ConfigError,
    DataError,
    DataProvider,
    LicenceError,
    Mode,
    ObservationFrequency,
    SeasonalAdjustment,
    SourceDisabledError,
    api,
    cache,
    configure,
    resolve,
    settings,
)
from pyeconomics.data.catalog.definitions import Candidate, Concept, Tier
from pyeconomics.data.config import reset
from pyeconomics.data.modes import is_disabled, require_enabled
from pyeconomics.data.resolver import REASONS

if TYPE_CHECKING:
    from config_isolation import Home

DATA = [100.0 + i for i in range(24)]


def concept(*candidates: Candidate, concept_id: str = "us.test.value") -> Concept:
    return Concept(
        id=concept_id,
        title="A test concept",
        definition="A concept made for a test of the disabled_providers switch.",
        unit_kind=UnitKind.INDEX_LEVEL,
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=candidates,
    )


def two_sources() -> tuple[type[DataProvider], type[DataProvider], Concept]:
    first = scripted("alpha", {"A": monthly(DATA, provider="alpha", series_id="A")})
    second = scripted("beta", {"B": monthly(DATA, provider="beta", series_id="B")})
    found = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    return first, second, found


# --- the setting ----------------------------------------------------------------


@pytest.mark.usefixtures("home")
def test_the_variable_takes_ids_separated_by_commas_or_spaces(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_DISABLED_PROVIDERS", " fred, bls  bea,fred ")
    assert settings().disabled_providers == ("bea", "bls", "fred")
    assert is_disabled("bls")
    assert not is_disabled("treasury")


def test_the_files_and_configure_set_it_too(
    home: Home, monkeypatch: pytest.MonkeyPatch
) -> None:
    home.write_config('disabled_providers = ["oecd", "imf"]\n')
    assert settings().disabled_providers == ("imf", "oecd")
    monkeypatch.setenv("PYECONOMICS_DISABLED_PROVIDERS", "bis")
    reset()  # the variables are read once per process: read them again
    assert settings().disabled_providers == ("bis",)  # the environment overrides
    assert configure(disabled_providers=["ecb", "ecb"]).disabled_providers == ("ecb",)
    assert configure(disabled_providers=()).disabled_providers == ()


@pytest.mark.parametrize(
    ("text", "problem"),
    [
        ('disabled_providers = "fred"\n', "must be a list of provider ids"),
        ("disabled_providers = [1]\n", "must be a list of provider ids"),
        ('disabled_providers = ["Fred!"]\n', "snake_case"),
    ],
)
def test_a_bad_list_is_a_configuration_error(
    home: Home, text: str, problem: str
) -> None:
    home.write_config(text)
    with pytest.raises(ConfigError, match=problem):
        settings()


@pytest.mark.usefixtures("home")
def test_the_hosted_servers_own_secret_is_not_refused_but_other_names_are(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYECONOMICS_EDGE_CREDENTIAL", secrets.token_urlsafe(32))
    assert settings().mode == "library"
    monkeypatch.setenv("PYECONOMICS_API_TOKEN", secrets.token_urlsafe(32))
    reset()  # the variables are read once per process: read them again
    with pytest.raises(ConfigError, match="PYECONOMICS_API_TOKEN is named like"):
        settings()


# --- the provider gate ------------------------------------------------------------


def test_every_operation_refuses_a_disabled_provider_before_the_cache_or_a_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha", series_id="A")},
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
    )()
    configure(disabled_providers=["alpha"])

    def no_cache(*_args: object, **_kwargs: object) -> None:
        msg = "a disabled provider must not reach the cache"
        raise AssertionError(msg)

    monkeypatch.setattr(cache, "lookup", no_cache)
    for call in (
        lambda: provider.fetch({"series": ("A",)}),
        lambda: provider.search("anything"),
        lambda: provider.describe("A"),
    ):
        with pytest.raises(SourceDisabledError, match="alpha is disabled"):
            call()
    assert calls_of(type(provider)) == []
    with pytest.raises(SourceDisabledError):
        require_enabled(provider="alpha")


def test_an_own_configuration_check_cannot_bypass_the_switch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    permissive = scripted("alpha", {"A": monthly(DATA, provider="alpha")})

    def accept_everything(self: DataProvider) -> None:
        """Accept everything, as a careless provider might."""

    monkeypatch.setattr(permissive, "check_configuration", accept_everything)
    configure(disabled_providers=["alpha"])
    with pytest.raises(SourceDisabledError):
        permissive().fetch({"series": ("A",)})


def test_an_enabled_provider_still_answers() -> None:
    provider = scripted("alpha", {"A": monthly(DATA, provider="alpha", series_id="A")})
    configure(disabled_providers=["beta"])
    assert as_series(provider().fetch({"series": ("A",)})).values[0] == DATA[0]


# --- the resolver -----------------------------------------------------------------


def test_the_resolver_fails_over_from_a_disabled_candidate() -> None:
    first, second, found = two_sources()
    configure(disabled_providers=["alpha"])
    result = resolve(found, registry=registry_of(first, second))
    assert result.source.provider == "beta"
    (skip,) = result.skipped
    assert (skip.provider, skip.reason) == ("alpha", "disabled")
    assert skip.reason in REASONS
    assert "skipped_alpha_disabled" in result.source.warnings
    assert result.source.fallback_chain == ("alpha", "beta")
    assert calls_of(first) == []


def test_every_candidate_disabled_is_a_source_disabled_error() -> None:
    first, second, found = two_sources()
    configure(disabled_providers=["alpha", "beta"])
    with pytest.raises(SourceDisabledError) as refused:
        resolve(found, registry=registry_of(first, second))
    assert str(refused.value).startswith(
        "us.test.value cannot be resolved: alpha, beta are disabled"
    )
    assert refused.value.providers == ("alpha", "beta")
    assert calls_of(first) == calls_of(second) == []


def test_a_provider_series_is_refused_when_its_provider_is_disabled() -> None:
    first, second, _ = two_sources()
    configure(disabled_providers=["beta"])
    with pytest.raises(SourceDisabledError):
        api.get("beta:B", registry=registry_of(first, second))
    assert as_series(api.get("alpha:A", registry=registry_of(first, second)).frame)


# --- what reports it --------------------------------------------------------------


def test_sources_reports_the_switch() -> None:
    first, second, _ = two_sources()
    configure(disabled_providers=["beta"])
    infos = {
        info.id: info.disabled
        for info in api.sources(check_keys=False, registry=registry_of(first, second))
    }
    assert infos == {"alpha": False, "beta": True}


def test_search_and_vintages_pass_over_a_disabled_provider() -> None:
    searcher = scripted("alpha", {}, capabilities=(Capability.FETCH, Capability.SEARCH))
    configure(disabled_providers=["alpha"])
    found = api.search("qqqzzzx", mode=Mode.LIBRARY, registry=registry_of(searcher))
    assert dict(found.skipped)["alpha"] == "disabled by the disabled_providers setting"
    keeper = scripted(
        "beta",
        {},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        changed=(dt.date(2024, 1, 31),),
    )
    configure(disabled_providers=["beta"])
    with pytest.raises(SourceDisabledError):
        api.vintages("beta:B", registry=registry_of(keeper))
    with pytest.raises(DataError, match="no candidate that keeps vintages"):
        api._vintage_provider(  # noqa: SLF001 - the concept path's own choice
            concept(Candidate(provider="beta", series="B")),
            Mode.LIBRARY,
            registry_of(keeper),
        )


def test_the_command_line_marks_a_disabled_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain = cli("data", "sources")
    assert plain.code == 0
    assert "Disabled" not in plain.text
    monkeypatch.setenv("PYECONOMICS_DISABLED_PROVIDERS", "bls")
    reset()
    marked = cli("data", "sources")
    assert marked.code == 0
    assert "Disabled" in marked.text
    rows = [line for line in marked.text.splitlines() if " bls " in f" {line} "]
    assert rows
    assert rows[0].rstrip(" │|").endswith("yes")


# --- a concept's hosted refusal names a terms page ----------------------------------


def test_a_concepts_hosted_refusal_carries_its_first_candidates_terms_page() -> None:
    library = scripted(
        "alpha",
        {"A": monthly(DATA, provider="alpha", series_id="A")},
        licence=LicenceClass.LIBRARY_ONLY,
    )
    found = concept(Candidate(provider="alpha", series="A"))
    with pytest.raises(LicenceError) as refused:
        resolve(found, mode=Mode.HOSTED, registry=registry_of(library))
    assert refused.value.licence is LicenceClass.LIBRARY_ONLY
    assert refused.value.terms_url == library.info.terms.terms_url
    assert calls_of(library) == []
