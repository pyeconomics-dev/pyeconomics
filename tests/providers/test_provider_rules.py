# tests/providers/test_provider_rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``registry.validate()`` reports each rule's toy violation under its slug.

Each toy is a valid provider with exactly one flaw. The suite fails for a rule
slug without a toy, so a new rule cannot be added unproved.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest
from stubs import STUB_TERMS, Stub, stub_info
from toys import ToyJson, ToyVintage

from pyeconomics.core._released import Released
from pyeconomics.core.errors import RegistryError
from pyeconomics.data import (
    Access,
    Authentication,
    Capability,
    DataProvider,
    KeyPlacement,
    LicenceClass,
    LlmUse,
    Platform,
    RateLimit,
    Terms,
)
from pyeconomics.data.providers.rules import RULES
from pyeconomics.data.registry import ProviderRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyeconomics.data import ProviderInfo


def variant(base: type[DataProvider], **changes: Any) -> type[DataProvider]:
    """Return a subclass of ``base`` whose info has ``changes`` applied."""
    return type("Variant", (base,), {"info": replace(base.info, **changes)})


def corrupted(**fields: object) -> Terms:
    """Return stub terms with fields set past the constructor's checks."""
    terms = replace(STUB_TERMS)
    for name, value in fields.items():
        object.__setattr__(terms, name, value)
    return terms


class WithBadHook(Stub):
    """Overrides a search hook without declaring search."""

    info = stub_info(capabilities=(Capability.FETCH,))


def _undeclared_hook() -> type[DataProvider]:
    return type(
        "Undeclared",
        (Stub,),
        {"info": stub_info(capabilities=(Capability.FETCH,))},
    )


#: One broken provider per rule slug: (builder, the registry's extras).
VIOLATIONS: dict[str, Callable[[], type[DataProvider]]] = {
    "provider-id": lambda: variant(Stub, id="Bad-Id"),
    "terms": lambda: variant(Stub, terms=None),
    "attribution": lambda: variant(Stub, terms=corrupted(attribution="TBD")),
    "notice": lambda: variant(Stub, terms=corrupted(notice=STUB_TERMS.attribution)),
    "llm-use": lambda: variant(
        Stub,
        terms=replace(
            STUB_TERMS, licence=LicenceClass.PREMIUM_LOCAL, llm_use=LlmUse.ALLOWED
        ),
    ),
    "cache-policy": lambda: variant(Stub, terms=corrupted(cache="sometimes")),
    "hosts": lambda: variant(Stub, hosts=("https://api.example.org",)),
    "rate-limit": lambda: variant(Stub, rate_limits=()),
    "capabilities": lambda: variant(
        Stub, capabilities=(Capability.FETCH, Capability.SEARCH)
    ),
    "auth": lambda: variant(Stub, auth=Authentication.key("k", KeyPlacement.QUERY)),
    "extra": lambda: variant(Stub, extra="nonexistent"),
    "platforms": lambda: variant(Stub, platforms=()),
    "size-cap": lambda: variant(Stub, max_response_bytes=10),
}


def problems(*providers: type[DataProvider], **kwargs: Any) -> list[str]:
    registry = ProviderRegistry.from_providers(*providers, extras={"real": ()})
    kwargs.setdefault("released", {})  # toys have no release history
    return [str(p) for p in registry.problems(**kwargs)]


def test_both_toy_providers_pass() -> None:
    ProviderRegistry.from_providers(ToyJson, ToyVintage).validate(released={})


def test_every_rule_slug_has_a_toy_violation() -> None:
    provided = set(VIOLATIONS) | {
        "released",
        "released-concept",
        "duplicate-id",
        "spec",
    }
    assert provided == set(RULES)


@pytest.mark.parametrize("slug", sorted(VIOLATIONS))
def test_a_violation_is_reported_under_its_slug(slug: str) -> None:
    found = problems(VIOLATIONS[slug]())
    assert found, f"{slug}: the toy passed"
    assert all(f"[{slug}]" in line for line in found), found


def test_a_problem_names_the_provider_and_the_rule() -> None:
    (line,) = problems(variant(Stub, rate_limits=()))
    assert line.startswith("stub: [rate-limit] ")


def test_validate_raises_one_error_listing_every_problem() -> None:
    broken = variant(Stub, rate_limits=(), platforms=())
    with pytest.raises(RegistryError) as caught:
        ProviderRegistry.from_providers(broken).validate(released={})
    assert "has 2 problems" in str(caught.value)
    assert len(caught.value.problems) == 2
    with pytest.raises(RegistryError, match="has 1 problem:"):
        ProviderRegistry.from_providers(variant(Stub, platforms=())).validate(
            released={}
        )


def test_the_extra_must_be_declared_by_the_registering_distribution() -> None:
    declared = variant(Stub, extra="real")
    assert problems(declared) == []
    registry = ProviderRegistry.from_providers(declared)  # no extras declared
    assert [p.rule for p in registry.problems(released={})] == ["extra"]
    assert [
        p.rule
        for p in ProviderRegistry.from_providers(variant(Stub, extra=" ")).problems(
            released={}
        )
    ] == ["extra"]


def test_a_released_provider_must_stay_registered() -> None:
    ledger = {"gone": Released("gone", "1.0.0a2")}
    assert problems(Stub, released=ledger) == [
        (
            "gone: [released] no longer registered; a released provider id is "
            "never deleted or renamed (ADR-0003)"
        )
    ]
    assert problems(Stub, released={"stub": Released("stub", "1.0.0a2")}) == []


@pytest.mark.parametrize(
    "entry",
    [
        Released("other", "1.0.0a2"),
        Released("stub", "not a version"),
        Released("Stub", "1.0.0"),
    ],
)
def test_a_malformed_ledger_entry_is_reported(entry: Released) -> None:
    found = problems(Stub, released={entry.canonical_id.lower(): entry, "stub": entry})
    assert any("[released]" in line and "malformed" in line for line in found)


def test_a_duplicate_id_is_reported_with_both_distributions() -> None:
    first = ProviderRegistry.from_providers(Stub, distribution="one")
    twice = ProviderRegistry(
        [
            *first.registrations,
            *ProviderRegistry.from_providers(Stub, distribution="two").registrations,
        ]
    )
    (line,) = (str(p) for p in twice.problems(released={}))
    assert "[duplicate-id]" in line
    assert "'one'" in line
    assert "'two'" in line
    assert twice.ids() == ("stub",)


def test_a_class_without_info_is_reported_as_a_spec_problem() -> None:
    class NoInfo(DataProvider):
        pass

    (line,) = problems(NoInfo)
    assert line.startswith("NoInfo: [spec]")


def test_the_capability_rule_checks_hooks_both_ways() -> None:
    undeclared = _undeclared_hook()
    found = problems(undeclared)
    assert any(
        "overrides build_search, parse_search but does not declare search" in p
        for p in found
    )
    missing = problems(
        variant(
            ToyVintage,
            capabilities=(Capability.FETCH, Capability.SEARCH, Capability.VINTAGES),
        )
    )
    assert any("declares search but does not override" in p for p in missing)


@pytest.mark.parametrize(
    "capabilities",
    [(), ("fetch", "fetch"), (Capability.BULK,), (Capability.VINTAGES,), ("nonsense",)],
)
def test_odd_capability_declarations_are_reported(
    capabilities: tuple[Any, ...],
) -> None:
    assert any(
        "[capabilities]" in p
        for p in problems(variant(Stub, capabilities=capabilities))
    )


@pytest.mark.parametrize(
    "hosts",
    [
        (),
        ("api.example.org", "api.example.org"),
        ("API.example.org",),
        ("api.example.org:8443",),
        ("*.example.org",),
        ("example",),
        ("10.0.0.1",),
        tuple(f"h{n}.example.org" for n in range(17)),
        "api.example.org",
    ],
)
def test_the_hosts_rule_wants_exact_distinct_lowercase_names(hosts: Any) -> None:
    assert any("[hosts]" in p for p in problems(variant(Stub, hosts=hosts)))


def test_a_session_provider_declares_no_host_and_an_https_one_declares_some() -> None:
    session = variant(Stub, access=Access.SESSION, hosts=(), rate_limits=())
    assert problems(session) == []
    assert any(
        "[hosts]" in p for p in problems(variant(session, hosts=("api.example.org",)))
    )
    assert any("[hosts]" in p for p in problems(variant(Stub, access="ftp")))


@pytest.mark.parametrize(
    "limits",
    [
        (RateLimit(requests=0, per="second"),),
        (RateLimit(requests=2_000_000, per="second"),),
        (RateLimit(requests=1, per="week"),),  # type: ignore[arg-type]
        (RateLimit(requests=1, per="second"), RateLimit(requests=2, per="second")),
        ("ten per second",),
        "ten per second",
    ],
)
def test_the_rate_limit_rule_wants_sane_distinct_windows(limits: Any) -> None:
    assert any("[rate-limit]" in p for p in problems(variant(Stub, rate_limits=limits)))


@pytest.mark.parametrize(
    "auth",
    [
        Authentication.key("api_key", None),  # type: ignore[arg-type]
        Authentication.key("not a name", KeyPlacement.QUERY),
        Authentication.key("api_key", KeyPlacement.QUERY, scheme="Bearer"),
        Authentication(kind="magic"),  # type: ignore[arg-type]
        replace(Authentication(), name="api_key"),
        replace(Authentication(), required="yes"),  # type: ignore[arg-type]
        replace(Authentication.contact(), required=False),
        "a key",
    ],
)
def test_the_auth_rule_wants_a_coherent_scrubbable_spec(auth: Any) -> None:
    assert any("[auth]" in p for p in problems(variant(Stub, auth=auth)))


def test_a_header_key_and_a_bearer_scheme_are_fine_and_a_byok_source_needs_a_key() -> (
    None
):
    good = Authentication.key("Authorization", KeyPlacement.HEADER, scheme="Bearer")
    assert problems(variant(Stub, auth=good)) == []
    assert (
        problems(
            variant(Stub, auth=Authentication.key("x-api-key", KeyPlacement.HEADER))
        )
        == []
    )
    assert (
        problems(
            variant(Stub, auth=Authentication.key("registrationkey", KeyPlacement.BODY))
        )
        == []
    )
    byok = replace(STUB_TERMS, licence=LicenceClass.BYOK, llm_use=LlmUse.FORBIDDEN)
    assert any("byok" in p for p in problems(variant(Stub, terms=byok)))
    assert problems(variant(Stub, terms=byok, auth=good)) == []
    optional = Authentication.key("api_key", KeyPlacement.QUERY, required=False)
    assert any("byok" in p for p in problems(variant(Stub, terms=byok, auth=optional)))


@pytest.mark.parametrize("llm", [LlmUse.FORBIDDEN, LlmUse.UNCLEAR])
def test_a_vendor_source_may_declare_forbidden_or_unclear(llm: LlmUse) -> None:
    terms = replace(STUB_TERMS, licence=LicenceClass.PREMIUM_LOCAL, llm_use=llm)
    assert problems(variant(Stub, terms=terms)) == []


@pytest.mark.parametrize(
    "terms",
    [
        corrupted(licence="hosted-safe"),
        corrupted(terms_url="http://insecure.example.org/terms"),
        corrupted(checked=dt.datetime(2026, 1, 1, tzinfo=dt.UTC)),
        corrupted(llm_use="sometimes"),
        corrupted(attribution="   "),
        corrupted(notice="n/a"),
        corrupted(attribution=7),
    ],
)
def test_corrupted_terms_are_reported(terms: Terms) -> None:
    assert problems(variant(Stub, terms=terms))


def test_homepage_and_name_are_required() -> None:
    assert any(
        "[provider-id]" in p
        for p in problems(variant(Stub, homepage="http://insecure.example.org"))
    )
    assert any("[provider-id]" in p for p in problems(variant(Stub, name="")))
    assert any("[provider-id]" in p for p in problems(variant(Stub, id="index")))


@pytest.mark.parametrize(
    "changes",
    [
        {"platforms": (Platform.LINUX, Platform.LINUX)},
        {"platforms": ("amiga",)},
        {"automated_collection": "yes"},
        {"max_response_bytes": True},
        {"max_response_bytes": 2**40},
        {"ttl_seconds": -1},
        {"ttl_seconds": True},
        {"ttl_seconds": 1.5},
        {"ttl_seconds": 10**12},
    ],
)
def test_platforms_the_size_cap_and_the_time_to_live_are_checked(
    changes: dict[str, Any],
) -> None:
    assert problems(variant(Stub, **changes))


def test_info_is_hashable_once_built() -> None:
    info: ProviderInfo = stub_info()
    assert isinstance(hash(info.hosts), int)
