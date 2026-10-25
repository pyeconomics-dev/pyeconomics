# src/pyeconomics/data/api.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The public data API: ``get``, ``search``, ``describe``, ``vintages``, ``sources``.

Each takes what a person would type: a catalog concept id
(``us.inflation.pce_core.yoy``), a provider series (``fred:UNRATE``, the provider
id, a colon, the provider's own series key) or, for ``describe`` and ``sources``,
a provider id. Phase 4's ``pyeconomics data search|get|vintages`` commands wrap
these functions unchanged.

- :func:`get` returns a :class:`~pyeconomics.data.resolver.Resolved`: the frame
  and its provenance records. A concept goes through the resolver (mode, keys,
  extras, vintage and series-level licence gates, fallback, transforms); a
  provider series goes straight to its provider, which applies the same gates.
  Given an ``llm_use`` policy (the MCP server's), a concept passes over the
  sources it does not permit, and a provider series it does not permit is
  refused with :class:`~pyeconomics.data.errors.LlmUseError`.
- :func:`search` finds concepts offline and, on the providers that can search,
  their series, recording the providers it could not ask and why.
- :func:`describe` explains a concept (its candidates by mode), a provider
  series (its metadata) or a provider (its terms).
- :func:`vintages` lists the dates a series changed.
- :func:`sources` lists the providers with their licence classes, notices,
  keys and capabilities, from metadata alone.

Examples
--------
>>> from pyeconomics import data
>>> info = data.sources()
>>> sorted({s.licence.value for s in info})[:2]
['hosted-safe', 'library-only']
>>> data.describe("us.unemployment.rate").concept.title
'Unemployment rate'
>>> data.search("unemployment rate", 3, providers=()).hits[0].id
'us.unemployment.rate'
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.provenance import (
    CONCEPT_ID_PATTERN,
    DATA_DATE_BOUNDS,
    LicenceClass,
    LlmUse,
    LlmUsePolicy,
)
from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived, Tier
from pyeconomics.data.credentials import has_key
from pyeconomics.data.errors import DataError, LlmUseError, ProviderNotFoundError
from pyeconomics.data.modes import Mode, current_mode, is_disabled, require_allowed
from pyeconomics.data.providers.base import (
    SERIES_ID_PATTERN,
    AuthKind,
    Capability,
    ProviderInfo,
)
from pyeconomics.data.resolver import Resolved, resolve, trim
from pyeconomics.data.vintage import Vintage

if TYPE_CHECKING:
    import datetime as dt
    from collections.abc import Iterable, Mapping, Sequence

    from pyeconomics.data.providers.base import DataProvider
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.data.terms import CachePolicy, Terms
    from pyeconomics.data.transport.base import Transport
    from pyeconomics.data.types import ObservationFrequency, SeriesMeta

__all__ = [
    "CandidateInfo",
    "ConceptInfo",
    "Hit",
    "SearchResult",
    "SourceInfo",
    "candidates_by_mode",
    "describe",
    "get",
    "search",
    "sources",
    "vintages",
]

_ADDRESS: Final = re.compile(
    rf"(?P<provider>[a-z][a-z0-9_]{{0,63}}):(?P<series>{SERIES_ID_PATTERN})"
)
_PROVIDER_ID: Final = re.compile(r"[a-z][a-z0-9_]{0,63}")
_MAX_SEARCH: Final = 100
_MIN_TOKEN: Final = 2


# --- values -----------------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceInfo:
    """A provider as ``sources()`` and ``describe()`` report it, from metadata."""

    id: str
    name: str
    homepage: str
    licence: LicenceClass
    hosted_allowed: bool
    """Whether hosted mode may serve the provider's data (its class alone; a
    series may be marked more strictly by its source)."""
    terms_url: str
    terms_checked: dt.date
    attribution: str
    notice: str | None
    llm_use: LlmUse
    cache: CachePolicy
    key_variable: str | None
    """The environment variable that holds the provider's key, if it uses one."""
    key_required: bool
    key_configured: bool | None
    """Whether a key is configured (``None`` for a provider without keys)."""
    extra: str | None
    capabilities: tuple[str, ...]
    platforms: tuple[str, ...]
    automated_collection: bool
    never_paid: bool
    disabled: bool = False
    """Whether the ``disabled_providers`` setting turns the provider off."""


@dataclass(frozen=True, slots=True, kw_only=True)
class CandidateInfo:
    """One candidate of a concept with the facts that decide when it is used."""

    provider: str
    series: str
    tier: Tier
    licence: LicenceClass | None
    """The provider's licence class; ``None`` for a derived candidate."""
    hosted_allowed: bool
    keeps_vintages: bool
    key_variable: str | None
    key_required: bool
    extra: str | None
    transforms: tuple[str, ...]
    note: str | None
    derived_from: tuple[str, ...] = ()
    """The operand concept ids of a derived candidate."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ConceptInfo:
    """A concept with its candidates described."""

    concept: Concept
    candidates: tuple[CandidateInfo, ...]

    def usable_in(self, mode: Mode) -> tuple[CandidateInfo, ...]:
        """Return the candidates a mode may use, in fallback order.

        Hosted mode keeps only hosted-safe and user-supplied candidates; a
        derived candidate is kept when its operands' originators are.
        """
        if mode is Mode.LIBRARY:
            return self.candidates
        return tuple(c for c in self.candidates if c.hosted_allowed)


@dataclass(frozen=True, slots=True, kw_only=True)
class Hit:
    """One search result: a concept or a provider series."""

    kind: str
    """``concept`` or ``series``."""
    id: str
    """A concept id, or ``provider:series`` for a series."""
    title: str
    detail: str | None = None
    provider: str | None = None
    frequency: ObservationFrequency | None = None
    unit: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    """The hits of a search and the providers it could not ask, with why."""

    hits: tuple[Hit, ...]
    skipped: tuple[tuple[str, str], ...] = ()


# --- helpers ----------------------------------------------------------------------


def _registry(registry: ProviderRegistry | None) -> ProviderRegistry:
    return registry or provider_registry.installed()


def _info(info: ProviderInfo, *, check_keys: bool = True) -> SourceInfo:
    terms = info.terms
    uses_key = info.auth.kind is AuthKind.KEY
    return SourceInfo(
        id=info.id,
        name=info.name,
        homepage=info.homepage,
        licence=terms.licence,
        hosted_allowed=terms.licence.hosted_allowed,
        terms_url=terms.terms_url,
        terms_checked=terms.checked,
        attribution=terms.attribution,
        notice=terms.notice,
        llm_use=terms.llm_use,
        cache=terms.cache,
        key_variable=info.key_variable,
        key_required=uses_key and info.auth.required,
        key_configured=has_key(info.id) if uses_key and check_keys else None,
        extra=info.extra,
        capabilities=tuple(c.value for c in info.capabilities),
        platforms=tuple(p.value for p in info.platforms),
        automated_collection=info.automated_collection,
        never_paid=info.never_paid,
        disabled=is_disabled(info.id),
    )


def _candidate_info(
    candidate: Candidate | Derived, registry: ProviderRegistry
) -> CandidateInfo:
    if isinstance(candidate, Derived):
        operands = tuple(o.concept for o in candidate.operands)
        usable = all(
            _originators_hosted(catalog.get(operand), registry) for operand in operands
        )
        return CandidateInfo(
            provider="derived",
            series=f"{candidate.transform} of {' and '.join(operands)}",
            tier=candidate.tier,
            licence=None,
            hosted_allowed=usable,
            keeps_vintages=False,
            key_variable=None,
            key_required=False,
            extra=None,
            transforms=(),
            note=candidate.note,
            derived_from=operands,
        )
    try:
        info = registry.provider_class(candidate.provider).info
    except ProviderNotFoundError:
        return CandidateInfo(
            provider=candidate.provider,
            series=candidate.series,
            tier=candidate.tier,
            licence=None,
            hosted_allowed=False,
            keeps_vintages=False,
            key_variable=None,
            key_required=False,
            extra=None,
            transforms=candidate.transforms,
            note=candidate.note,
        )
    return CandidateInfo(
        provider=candidate.provider,
        series=candidate.series,
        tier=candidate.tier,
        licence=info.terms.licence,
        hosted_allowed=info.terms.licence.hosted_allowed,
        keeps_vintages=Capability.VINTAGES in info.capabilities,
        key_variable=info.key_variable,
        key_required=info.auth.kind is AuthKind.KEY and info.auth.required,
        extra=info.extra,
        transforms=candidate.transforms,
        note=candidate.note,
    )


def _originators_hosted(concept: Concept, registry: ProviderRegistry) -> bool:
    """Whether a concept has a candidate hosted mode may use."""
    return any(_candidate_info(c, registry).hosted_allowed for c in concept.candidates)


def candidates_by_mode(
    concept: Concept | str, registry: ProviderRegistry | None = None
) -> dict[Mode, tuple[CandidateInfo, ...]]:
    """Return a concept's candidates for each mode, from metadata alone.

    It reads no key and no setting, so the documentation build can call it.

    Examples
    --------
    >>> by_mode = candidates_by_mode("us.treasury.nominal_10y")
    >>> [c.provider for c in by_mode[Mode.LIBRARY]]
    ['treasury', 'fred']
    >>> [c.provider for c in by_mode[Mode.HOSTED]]
    ['treasury']
    """
    found = catalog.get(concept) if isinstance(concept, str) else concept
    registry = _registry(registry)
    info = ConceptInfo(
        concept=found,
        candidates=tuple(_candidate_info(c, registry) for c in found.candidates),
    )
    return {mode: info.usable_in(mode) for mode in Mode}


def _split(target: str) -> tuple[str, str | None]:
    """Classify a target as a concept, a provider series or a bare provider id."""
    text = f.text(target, "a concept id or provider:series", max_length=256)
    if CONCEPT_ID_PATTERN.fullmatch(text):
        return "concept", None
    match = _ADDRESS.fullmatch(text)
    if match is not None:
        return match["provider"], match["series"]
    if _PROVIDER_ID.fullmatch(text):
        return "provider", text
    msg = (
        f"{text!r} is neither a concept id (such as us.unemployment.rate) nor a "
        "provider series (such as fred:UNRATE)"
    )
    raise f.fail(msg)


def _require_llm_use(
    terms: Terms, policy: LlmUsePolicy | None, target: str, *, provider: str
) -> None:
    """Refuse a provider series whose terms the ``llm_use`` policy does not permit."""
    if policy is None or policy.permits(terms.llm_use):
        return
    msg = (
        f"{target}'s terms make its data {terms.llm_use.value} for language "
        f"models, which the {policy.value} policy does not permit"
    )
    raise LlmUseError(
        msg,
        provider=provider,
        licence=terms.licence,
        llm_use=terms.llm_use,
        terms_url=terms.terms_url,
    )


def _vintage(as_of: dt.date | None, vintage: Vintage | str | None) -> Vintage:
    if as_of is not None and vintage is not None:
        msg = "ask for as_of or for a vintage, not both"
        raise f.fail(msg)
    if as_of is not None:
        return Vintage.as_of(f.day(as_of, "as_of", DATA_DATE_BOUNDS))
    if vintage is None:
        return Vintage.latest()
    return vintage if isinstance(vintage, Vintage) else Vintage.parse(vintage)


# --- the five functions -----------------------------------------------------------


def get(  # noqa: PLR0913 - the public contract's independent options
    target: str,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    as_of: dt.date | None = None,
    vintage: Vintage | str | None = None,
    provider: str | None = None,
    mode: Mode | None = None,
    strict: bool = False,
    parameters: Mapping[str, object] | None = None,
    max_observations: int | None = None,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
    llm_use: LlmUsePolicy | str | None = None,
) -> Resolved:
    """Get the data a concept or a provider series names.

    Parameters
    ----------
    target
        A concept id, or ``provider:series`` (``fred:UNRATE``).
    start, end
        The observation window.
    as_of, vintage
        Read the data as published on a date, or select a vintage; a source that
        keeps no vintages cannot honour one and a concept skips it.
    provider
        For a concept, use only this provider's candidates; for a provider
        series, it must equal the address's provider.
    mode
        ``library`` or ``hosted``; the configured mode by default. A provider
        series is refused up front in a mode its class does not allow.
    strict
        For a concept, try its first candidate only.
    parameters
        The concept's parameters, such as an SEP ``meeting``.
    max_observations
        At most this many (the most recent) observations per fetch.
    transport, registry
        Seams for tests: a replay transport and an isolated provider registry.
    llm_use
        The surface's :class:`~pyeconomics.core.provenance.LlmUsePolicy`, or its
        value, for data about to reach a language model: a concept passes over the
        sources it does not permit, and a provider series it does not permit is
        refused, before the request when its provider's terms say so and after it
        when the series' own terms do. ``None`` looks at no ``llm_use`` class.

    Returns
    -------
    Resolved
        The frame, one ``DataSource`` record per source read, and the candidates
        passed over.

    Raises
    ------
    ConceptNotFoundError, ProviderNotFoundError
        For an unknown concept or provider.
    LlmUseError
        If the ``llm_use`` policy leaves no source.
    LicenceError, CredentialError, OfflineError, DataError
        As the resolver or the provider raises them.
    """
    policy = None if llm_use is None else f.choice(LlmUsePolicy, llm_use, "llm_use")
    kind, series = _split(target)
    if kind == "provider":
        msg = f"{target!r} is a provider; name a series as {target}:<series>"
        raise f.fail(msg)
    if series is None:
        return resolve(
            target,
            start=start,
            end=end,
            as_of=as_of,
            vintage=vintage,
            mode=mode,
            strict=strict,
            provider=provider,
            parameters=parameters,
            max_observations=max_observations,
            transport=transport,
            registry=registry,
            llm_use=policy,
        )
    if provider is not None and provider != kind:
        msg = f"{target!r} names {kind}, not {provider}"
        raise f.fail(msg)
    if parameters:
        msg = "a provider series takes no concept parameters"
        raise f.fail(msg)
    chosen = _registry(registry).get(kind)
    require_allowed(chosen.info.terms, provider=kind, mode=mode)
    _require_llm_use(chosen.info.terms, policy, target, provider=kind)
    fields: dict[str, object] = {
        "series": (series,),
        "start": start,
        "end": end,
        "vintage": _vintage(as_of, vintage).label,
    }
    if max_observations is not None:
        fields["max_observations"] = max_observations
    fetched = chosen.fetch_with_origin(
        chosen.query_type.model_validate(fields), transport=transport
    )
    _require_llm_use(fetched.frame.meta.terms, policy, target, provider=kind)
    frame = trim(fetched.frame, start, end)
    record = fetched.source()
    if frame.index:
        record = replace(
            record, observation_start=frame.index[0], observation_end=frame.index[-1]
        )
    return Resolved(frame, (record,), None, ())


def sources(
    *, check_keys: bool = True, registry: ProviderRegistry | None = None
) -> tuple[SourceInfo, ...]:
    """List every provider with its licence class, notice, key and capabilities.

    Metadata only: it makes no request. With ``check_keys`` (the default),
    ``key_configured`` says whether the key chain finds a key, without reading
    its value; without it the field is ``None``, so a documentation build looks
    at no key at all.
    """
    return tuple(
        _info(info, check_keys=check_keys) for info in _registry(registry).infos()
    )


def describe(
    target: str,
    *,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
) -> ConceptInfo | SeriesMeta | SourceInfo:
    """Describe a concept, a provider series or a provider.

    A concept id gives its :class:`ConceptInfo` (offline). ``provider:series``
    asks the provider to describe the series (a request; offline mode refuses).
    A provider id gives its :class:`SourceInfo` (offline).
    """
    kind, series = _split(target)
    registry = _registry(registry)
    if kind == "concept":
        found = catalog.get(target)
        return ConceptInfo(
            concept=found,
            candidates=tuple(_candidate_info(c, registry) for c in found.candidates),
        )
    if series is None:  # pragma: no cover - _split names a concept or gives a series
        msg = f"{target!r} is not a concept or provider"
        raise f.fail(msg)
    if kind == "provider":
        return _info(registry.provider_class(series).info)
    return registry.get(kind).describe(series, transport=transport)


def _needs_key(info: ProviderInfo) -> bool:
    """Say whether a provider needs a key and the chain has none."""
    return (
        info.auth.kind is AuthKind.KEY and info.auth.required and not has_key(info.id)
    )


def _vintage_provider(
    concept: Concept, mode: Mode, registry: ProviderRegistry
) -> tuple[DataProvider, str]:
    """Pick the first candidate of a concept that keeps vintages and mode allows."""
    for candidate in concept.candidates:
        if not isinstance(candidate, Candidate) or candidate.placeholders:
            continue
        try:
            chosen = registry.get(candidate.provider)
        except ProviderNotFoundError:
            continue
        info = chosen.info
        if Capability.VINTAGES not in info.capabilities or is_disabled(info.id):
            continue
        if mode is Mode.HOSTED and not info.terms.licence.hosted_allowed:
            continue
        if (
            info.auth.kind is AuthKind.KEY
            and info.auth.required
            and not has_key(info.id)
        ):
            continue
        return chosen, candidate.series
    msg = f"{concept.id} has no candidate that keeps vintages and this mode may use"
    raise DataError(msg)


def vintages(
    target: str,
    *,
    mode: Mode | None = None,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
) -> tuple[dt.date, ...]:
    """List the dates a series changed, oldest first.

    For a concept, the first candidate that keeps vintages, is allowed in the
    mode and has its key is asked; a concept whose series name a parameter
    (the SEP) is not supported. For ``provider:series``, that provider.

    Raises
    ------
    DataError
        If no candidate of a concept keeps vintages, or the provider keeps none.
    """
    kind, series = _split(target)
    registry = _registry(registry)
    if kind == "concept":
        chosen, key = _vintage_provider(
            catalog.get(target), mode or current_mode(), registry
        )
        return chosen.vintages(key, transport=transport)
    if series is None or kind == "provider":
        msg = f"{target!r} names a provider; name a series as provider:series"
        raise f.fail(msg)
    return registry.get(kind).vintages(series, transport=transport)


# --- search -----------------------------------------------------------------------


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= _MIN_TOKEN]


def _score(concept: Concept, tokens: Sequence[str]) -> int:
    """Score a concept against search tokens: topic words count most."""
    name = concept.id.lower().replace("_", " ")
    topic = concept.id.lower().split(".")[1].split("_")
    title = concept.title.lower()
    total = 0
    for token in tokens:
        if token in name or token in title:
            total += 3
        if token in topic:
            total += 2
        if title.startswith(token):
            total += 2
        if token in concept.definition.lower():
            total += 1
        if token in concept.section.lower():
            total += 1
    return total


def _concept_hits(text: str) -> list[Hit]:
    tokens = _tokens(text)
    if not tokens:
        return []
    scored = [(_score(c, tokens), c) for c in catalog.concepts()]
    ranked = sorted(
        (s for s in scored if s[0] > 0), key=lambda s: (-s[0], len(s[1].id), s[1].id)
    )
    return [
        Hit(
            kind="concept",
            id=c.id,
            title=c.title,
            detail=c.definition,
            frequency=c.frequency,
            unit=c.unit_text,
        )
        for _, c in ranked
    ]


def search(  # noqa: PLR0913 - the public contract's independent options
    text: str,
    limit: int = 20,
    *,
    providers: Iterable[str] | None = None,
    mode: Mode | None = None,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
) -> SearchResult:
    """Search concepts, then the series of the providers that can search.

    Concepts are matched offline on their id, title, section and definition and
    ranked. Each provider that declares ``search`` and that this mode, platform,
    key and offline setting allow is then asked for its series; one that cannot
    be asked is listed in ``skipped`` with the reason, and never stops the
    others.

    Parameters
    ----------
    text
        What to look for.
    limit
        At most this many hits in all (1 to 100).
    providers
        Which providers to ask; every searchable one by default, none for a
        concepts-only search (``providers=()``).
    mode, transport, registry
        As for :func:`get`.
    """
    f.text(text, "search text", max_length=256)
    if isinstance(limit, bool) or not 1 <= limit <= _MAX_SEARCH:
        msg = f"limit must be between 1 and {_MAX_SEARCH}"
        raise f.fail(msg)
    hits = _concept_hits(text)[:limit]
    skipped: list[tuple[str, str]] = []
    registry = _registry(registry)
    wanted = registry.ids() if providers is None else tuple(providers)
    active = mode or current_mode()
    for provider_id in wanted:
        if len(hits) >= limit:
            break
        found = _ask(registry, provider_id, text, limit - len(hits), active, transport)
        if isinstance(found, str):
            skipped.append((provider_id, found))
        else:
            hits.extend(found)
    return SearchResult(tuple(hits[:limit]), tuple(skipped))


def _search_refusal(info: ProviderInfo, mode: Mode) -> str | None:
    """Say why a provider is not asked to search, or ``None`` when it is."""
    if Capability.SEARCH not in info.capabilities:
        return "does not search"
    if is_disabled(info.id):
        return "disabled by the disabled_providers setting"
    if mode is Mode.HOSTED and not info.terms.licence.hosted_allowed:
        return f"{info.terms.licence.value}: hosted mode refuses it"
    if _needs_key(info):
        return f"no key: set {info.key_variable}"
    return None


def _ask(  # noqa: PLR0913, PLR0917 - one provider's search with its gates
    registry: ProviderRegistry,
    provider_id: str,
    text: str,
    room: int,
    mode: Mode,
    transport: Transport | None,
) -> list[Hit] | str:
    """Ask one provider to search; return its hits, or the reason it was passed over."""
    try:
        chosen = registry.get(provider_id)
    except ProviderNotFoundError:
        return "not registered"
    refusal = _search_refusal(chosen.info, mode)
    if refusal is not None:
        return refusal
    try:
        found = chosen.search(text, limit=room, transport=transport)
    except (DataError, MissingOptionalDependencyError) as error:
        lines = str(error).strip().splitlines()
        return lines[0][:200] if lines else type(error).__name__
    return [
        Hit(
            kind="series",
            id=f"{provider_id}:{hit.series_id}",
            title=hit.title,
            detail=hit.dataset,
            provider=provider_id,
            frequency=hit.frequency,
            unit=hit.unit,
        )
        for hit in found
    ]
