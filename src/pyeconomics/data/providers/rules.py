# src/pyeconomics/data/providers/rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The rules ``pyeconomics.data.registry.validate()`` holds every provider to.

Each rule has a slug, and each problem a rule reports names the provider and the
slug (``<id>: [<rule>] <detail>``), so a failure says what to fix. The rules
encode ADR-0005 (a licence class, terms and attribution are required, and a
vendor's data is closed by default), ADR-0011 decisions 7 to 10 (terms, the
provider contract, exact HTTPS hosts and published limits) and ADR-0003 (a
released id is permanent).

``ProviderInfo`` accepts what it is given, so a flaw is reported here, once and
by name, instead of failing at construction. For that reason every rule reads a
field as an ``object`` and checks its type: a hand-built or corrupted
``ProviderInfo`` is the case a rule exists for. A rule never reads the clock: the
13-month freshness of a provider's terms is a test
(``tests/providers/test_provider_terms.py``), not a rule.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.providers.base import (
    Access,
    Authentication,
    AuthKind,
    Capability,
    DataProvider,
    KeyPlacement,
    Platform,
    ProviderInfo,
    RateLimit,
)
from pyeconomics.data.redaction import is_credential_header, is_credential_parameter
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import HOST_PATTERN

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core._released import Released
    from pyeconomics.core.registry import Provider

__all__ = ["RULES", "Problem", "check_provider", "check_released"]

#: Every rule slug ``validate()`` can report. Tests hold each to a toy violation.
RULES: Final = (
    "provider-id",
    "terms",
    "attribution",
    "notice",
    "llm-use",
    "cache-policy",
    "hosts",
    "rate-limit",
    "capabilities",
    "auth",
    "extra",
    "platforms",
    "size-cap",
    "released",
    "duplicate-id",
    "spec",
)

_ID: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
_RESERVED_IDS: Final = frozenset({"index"})
_VERSION: Final = re.compile(r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?")
_PLACEHOLDERS: Final = frozenset(
    {
        "fixme",
        "n/a",
        "na",
        "none",
        "placeholder",
        "tbc",
        "tbd",
        "todo",
        "unknown",
        "xxx",
    }
)
_TOKEN: Final = re.compile(r"[A-Za-z][A-Za-z0-9_.$\[\]-]{0,63}")
_SCHEME: Final = re.compile(r"[A-Za-z][A-Za-z0-9-]{0,31}")
_WINDOWS: Final = ("second", "minute", "day")
_MAX_HOSTS: Final = 16
_MAX_LIMITS: Final = 4
_MAX_REQUESTS_PER_WINDOW: Final = 1_000_000
_MIN_SIZE_CAP: Final = 1_024
_MAX_SIZE_CAP: Final = 1_073_741_824
_VENDOR_CLASSES: Final = frozenset({LicenceClass.BYOK, LicenceClass.PREMIUM_LOCAL})

#: Each capability and the hook pairs a provider overrides to implement it.
_HOOKS: Final = {
    Capability.FETCH: ("build_requests", "parse"),
    Capability.SEARCH: ("build_search", "parse_search"),
    Capability.DESCRIBE: ("build_describe", "parse_describe"),
    Capability.VINTAGES: ("build_vintages", "parse_vintages"),
}


@dataclass(frozen=True, slots=True)
class Problem:
    """One thing wrong with a provider, naming the provider and the rule."""

    provider: str
    rule: str
    detail: str

    def __str__(self) -> str:
        """Render as ``<provider>: [<rule>] <detail>``."""
        return f"{self.provider}: [{self.rule}] {self.detail}"


class _Report:
    def __init__(self, provider_id: str) -> None:
        self.provider_id = provider_id
        self.problems: list[Problem] = []

    def add(self, rule: str, detail: str) -> None:
        self.problems.append(Problem(self.provider_id, rule, detail))


def _get(obj: object, name: str) -> object:
    """Read a field as an ``object``, so a rule may check its type."""
    return getattr(obj, name, None)


def _is_placeholder(text: str) -> bool:
    return text.strip(" .:;-").casefold() in _PLACEHOLDERS


def _is_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _whole(value: object, low: int, high: int) -> bool:
    return (
        isinstance(value, int) and not isinstance(value, bool) and low <= value <= high
    )


# --- the rules -------------------------------------------------------------------


def _check_id(info: ProviderInfo, report: _Report) -> None:
    provider_id = _get(info, "id")
    if not isinstance(provider_id, str) or not _ID.fullmatch(provider_id):
        report.add(
            "provider-id",
            f"the id {provider_id!r} must be snake_case: a letter, then letters, "
            "digits and underscores, at most 64 characters",
        )
    elif provider_id in _RESERVED_IDS:
        report.add("provider-id", f"{provider_id!r} is reserved (it names a docs page)")
    if not _is_text(_get(info, "name")):
        report.add("provider-id", "the provider needs a name")
    try:
        f.terms_url(_get(info, "homepage"), "homepage")
    except InputError as error:
        report.add("provider-id", f"the homepage is not a public https page: {error}")


def _check_terms(info: ProviderInfo, report: _Report) -> Terms | None:
    terms = _get(info, "terms")
    if not isinstance(terms, Terms):
        report.add(
            "terms",
            "the provider has no complete Terms: a licence class, the terms page, "
            "the date it was read, attribution, llm_use and a cache policy "
            "(ADR-0005 rule 1)",
        )
        return None
    licence = _get(terms, "licence")
    if not isinstance(licence, LicenceClass):
        report.add("terms", f"the licence class {licence!r} is not a LicenceClass")
    try:
        f.terms_url(_get(terms, "terms_url"))
    except InputError as error:
        report.add("terms", f"the terms page is not a public https page: {error}")
    checked = _get(terms, "checked")
    if not isinstance(checked, dt.date) or isinstance(checked, dt.datetime):
        report.add("terms", "the date the terms were read must be a date")
    return terms


def _check_terms_fields(terms: Terms, report: _Report) -> None:
    attribution = _get(terms, "attribution")
    if not isinstance(attribution, str) or not _is_text(attribution):
        report.add("attribution", "the attribution is required: whom to credit")
    elif _is_placeholder(attribution):
        report.add(
            "attribution",
            "the attribution travels with the data and must say whom to credit, "
            "not be a placeholder",
        )
    notice = _get(terms, "notice")
    if notice is not None:
        if (
            not isinstance(notice, str)
            or not _is_text(notice)
            or _is_placeholder(notice)
        ):
            report.add("notice", "a required notice must be the source's own text")
        elif notice == attribution:
            report.add(
                "notice",
                "the notice repeats the attribution; leave it out or give the "
                "source's required wording",
            )
    llm_use, licence = _get(terms, "llm_use"), _get(terms, "licence")
    if not isinstance(llm_use, LlmUse):
        report.add("llm-use", f"llm_use {llm_use!r} is not an LlmUse")
    elif licence in _VENDOR_CLASSES and llm_use is LlmUse.ALLOWED:
        report.add(
            "llm-use",
            f"a {licence} source is closed to language models by default: declare "
            "forbidden or unclear, and allowed only after the vendor's written "
            "permission and an ADR",
        )
    cache = _get(terms, "cache")
    if not isinstance(cache, CachePolicy):
        report.add("cache-policy", f"the cache policy {cache!r} is not a CachePolicy")


def _check_hosts(info: ProviderInfo, report: _Report) -> None:
    hosts, access = _get(info, "hosts"), _get(info, "access")
    if not isinstance(hosts, tuple) or not all(isinstance(host, str) for host in hosts):
        report.add("hosts", "hosts must be a tuple of host names")
        return
    if access is Access.SESSION:
        if hosts:
            report.add(
                "hosts",
                "a session provider contacts no host through the transport, so it "
                "declares none",
            )
        return
    if access is not Access.HTTPS:
        report.add("hosts", f"access {access!r} is not https or session")
        return
    if not hosts:
        report.add("hosts", "an HTTPS provider declares the exact hosts it may contact")
    if len(hosts) > _MAX_HOSTS or len(set(hosts)) != len(hosts):
        report.add("hosts", f"declare at most {_MAX_HOSTS} distinct hosts")
    for host in hosts:
        if not HOST_PATTERN.fullmatch(host):
            report.add(
                "hosts",
                f"{host!r} is not an exact lower-case host name (no scheme, port, "
                "path or wildcard; every request is HTTPS)",
            )


def _limit_problem(limit: object) -> str | None:
    if not isinstance(limit, RateLimit):
        return f"{limit!r} is not a RateLimit"
    requests, per = _get(limit, "requests"), _get(limit, "per")
    if not _whole(requests, 1, _MAX_REQUESTS_PER_WINDOW):
        return (
            f"{requests!r} requests is not a whole number from 1 to "
            f"{_MAX_REQUESTS_PER_WINDOW}"
        )
    if per not in _WINDOWS:
        return f"per {per!r} is not second, minute or day"
    return None


def _check_rate_limits(info: ProviderInfo, report: _Report) -> None:
    limits, access = _get(info, "rate_limits"), _get(info, "access")
    if not isinstance(limits, tuple):
        report.add("rate-limit", "rate limits must be a tuple of RateLimit")
        return
    if access is Access.HTTPS and not limits:
        report.add(
            "rate-limit",
            "an HTTPS provider declares the source's published limits, which the "
            "transport holds it to",
        )
    windows: list[object] = []
    for limit in limits:
        problem = _limit_problem(limit)
        if problem is not None:
            report.add("rate-limit", problem)
        else:
            windows.append(_get(limit, "per"))
    if len(limits) > _MAX_LIMITS or len(set(windows)) != len(windows):
        report.add(
            "rate-limit",
            f"declare at most {_MAX_LIMITS} limits, one per second, minute or day",
        )


def _hooks_overridden(
    provider: type[DataProvider], hooks: tuple[str, ...]
) -> list[str]:
    return [
        name
        for name in hooks
        if getattr(provider, name) is not getattr(DataProvider, name)
    ]


def _check_capabilities(
    provider: type[DataProvider], info: ProviderInfo, report: _Report
) -> None:
    caps = _get(info, "capabilities")
    if (
        not isinstance(caps, tuple)
        or not caps
        or not all(isinstance(cap, Capability) for cap in caps)
    ):
        report.add("capabilities", "declare at least one Capability")
        return
    if len(set(caps)) != len(caps):
        report.add("capabilities", "a capability is declared once")
    if Capability.BULK in caps and Capability.FETCH not in caps:
        report.add("capabilities", "bulk is a way of fetching, so it requires fetch")
    if Capability.VINTAGES in caps and Capability.FETCH not in caps:
        report.add("capabilities", "vintages requires fetch")
    for capability, hooks in _HOOKS.items():
        present = _hooks_overridden(provider, hooks)
        if capability in caps and len(present) != len(hooks):
            missing = ", ".join(sorted(set(hooks) - set(present)))
            report.add(
                "capabilities",
                f"declares {capability.value} but does not override {missing}",
            )
        elif capability not in caps and present:
            report.add(
                "capabilities",
                f"overrides {', '.join(present)} but does not declare "
                f"{capability.value}",
            )


def _check_key_auth(auth: Authentication, report: _Report) -> None:
    placement, name, scheme = (
        _get(auth, field) for field in ("placement", "name", "scheme")
    )
    if not isinstance(placement, KeyPlacement) or not isinstance(name, str):
        report.add(
            "auth", "a key declares where it goes (query, body or header) and its name"
        )
        return
    if not _TOKEN.fullmatch(name):
        report.add("auth", f"{name!r} is not a plain parameter or header name")
        return
    scrubbable = (
        is_credential_header(name)
        if placement is KeyPlacement.HEADER
        else is_credential_parameter(name)
    )
    if not scrubbable:
        report.add(
            "auth",
            f"{name!r} is not a name the redaction layer recognises as a "
            "credential, so a URL or a cassette could keep the key; add it to "
            "pyeconomics.data.redaction first",
        )
    if scheme is not None and (
        placement is not KeyPlacement.HEADER
        or not isinstance(scheme, str)
        or not _SCHEME.fullmatch(scheme)
    ):
        report.add("auth", "a scheme such as Bearer belongs to a header only")


def _check_auth(info: ProviderInfo, report: _Report) -> None:
    auth = _get(info, "auth")
    kind = _get(auth, "kind")
    if not isinstance(auth, Authentication) or not isinstance(kind, AuthKind):
        report.add("auth", "authentication must be an Authentication of a known kind")
        return
    required = _get(auth, "required")
    if not isinstance(required, bool):
        report.add("auth", "required is true or false")
    if kind is AuthKind.KEY:
        _check_key_auth(auth, report)
    elif (
        any(_get(auth, field) is not None for field in ("placement", "name", "scheme"))
        or required is False
    ):
        report.add(
            "auth", f"a {kind.value} source declares no key placement, name or scheme"
        )
    terms = _get(info, "terms")
    if (
        isinstance(terms, Terms)
        and _get(terms, "licence") is LicenceClass.BYOK
        and not (kind is AuthKind.KEY and required is True)
    ):
        report.add("auth", "a byok source is on the user's own key: it requires one")


def _check_extra(info: ProviderInfo, distribution: Provider, report: _Report) -> None:
    extra = _get(info, "extra")
    if extra is None:
        return
    if not isinstance(extra, str) or not _is_text(extra):
        report.add("extra", "extra must be the name of an extra, a string literal")
    elif not distribution.declares(extra):
        report.add(
            "extra",
            f"extra {extra!r} is not declared by {distribution.name!r} "
            "(Provides-Extra)",
        )


def _check_platforms_and_size(info: ProviderInfo, report: _Report) -> None:
    platforms = _get(info, "platforms")
    if (
        not isinstance(platforms, tuple)
        or not platforms
        or not all(isinstance(item, Platform) for item in platforms)
        or len(set(platforms)) != len(platforms)
    ):
        report.add("platforms", "declare the distinct Platform values it runs on")
    if not isinstance(_get(info, "automated_collection"), bool):
        report.add("platforms", "automated_collection is true or false")
    if not _whole(_get(info, "max_response_bytes"), _MIN_SIZE_CAP, _MAX_SIZE_CAP):
        report.add(
            "size-cap",
            f"max_response_bytes must be between {_MIN_SIZE_CAP} and {_MAX_SIZE_CAP}",
        )


def check_provider(
    provider: type[DataProvider], distribution: Provider
) -> list[Problem]:
    """Check one provider class against every rule except the ledger's.

    Parameters
    ----------
    provider
        A :class:`~pyeconomics.data.providers.base.DataProvider` subclass.
    distribution
        The distribution that registered it, which must declare its extra.
    """
    info = getattr(provider, "info", None)
    if not isinstance(info, ProviderInfo):
        report = _Report(provider.__name__)
        report.add(
            "spec", "a provider sets `info` to a ProviderInfo as a class attribute"
        )
        return report.problems
    provider_id = _get(info, "id")
    report = _Report(provider_id if isinstance(provider_id, str) else provider.__name__)
    _check_id(info, report)
    terms = _check_terms(info, report)
    if terms is not None:
        _check_terms_fields(terms, report)
    _check_hosts(info, report)
    _check_rate_limits(info, report)
    _check_capabilities(provider, info, report)
    _check_auth(info, report)
    _check_extra(info, distribution, report)
    _check_platforms_and_size(info, report)
    return report.problems


def check_released(
    released: Mapping[str, Released], provider_ids: set[str]
) -> list[Problem]:
    """Check the released-provider ledger against the registry (ADR-0003).

    A released id never disappears and is never renamed: providers have no
    aliases, so each entry's canonical id is the id itself.
    """
    problems: list[Problem] = []
    for released_id in sorted(released):
        entry = released[released_id]
        detail: str | None = None
        if (
            not _ID.fullmatch(entry.canonical_id)
            or not _VERSION.fullmatch(entry.first_version)
            or entry.canonical_id != released_id
        ):
            detail = "the ledger entry is malformed: a provider id names itself"
        elif released_id not in provider_ids:
            detail = (
                "no longer registered; a released provider id is never deleted or "
                "renamed (ADR-0003)"
            )
        if detail is not None:
            problems.append(Problem(released_id, "released", detail))
    return problems
