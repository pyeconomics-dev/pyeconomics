# src/pyeconomics/data/resolver.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Resolve a concept to a series, by mode, keys, extras and vintage (ADR-0011).

:func:`resolve` walks a concept's candidates in fallback order and returns the
first that can answer, with the chain it tried. A candidate is skipped, with the
reason recorded, when

- the ``disabled_providers`` setting turns its provider off (``disabled``),
  checked here before any request and again in the provider,
- hosted mode refuses its licence class (``licence_refused``), checked here
  before any request and again in the provider and on the series' own terms,
- an ``llm_use`` policy does not permit its source's terms or the series' own
  (``llm_use``): the MCP server and the AI narrative pass one, so data whose
  terms forbid language models, or leave them unclear without the user's
  opt-in, is passed over (ADR-0012 decision 14),
- the provider is not registered or does not run on this platform,
- its key is absent (``key_missing``) or its extra is not installed
  (``extra_missing``),
- it cannot honour the requested vintage (``vintage_unsupported``),
- the request fails: a series not found, a refused key, a rate limit, an
  unreachable source, a malformed answer, or offline mode with nothing cached,
- or its answer does not match the concept's definition
  (``definition_mismatch``): the resolver fails over only between identical
  definitions.

``strict=True`` tries the first candidate only. When none answers the error says
why: :class:`~pyeconomics.data.errors.LicenceError` naming the classes found
(and the first candidate's terms page) when hosted mode refused every candidate,
``CredentialError`` when keys were all that was missing, ``OfflineError`` when
offline mode had nothing cached, ``SourceDisabledError`` when every candidate's
provider is disabled, and :class:`~pyeconomics.data.errors.LlmUseError` when the
``llm_use`` policy (with hosted mode's licence refusals) left none.

Every :class:`~pyeconomics.core.provenance.DataSource` the result carries names
the concept, the transforms applied (as canonical text), the vintage, the window
read, and the providers tried in order; its warning codes add
``skipped_<provider>_<reason>`` for each candidate passed over. A library-mode
request for a vintage prefers a candidate that keeps vintages simply because the
others cannot honour it.

The resolver reads no clock and does no I/O of its own: providers fetch, and the
only settings it consults are the mode, the disabled providers and the key chain.
Without an ``llm_use`` policy it never looks at a source's ``llm_use`` class.

Examples
--------
>>> from pyeconomics.data import resolver
>>> sorted(resolver.REASONS)[:3]
['bad_response', 'credential_refused', 'data_error']
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Final, overload

from pydantic import ValidationError

from pyeconomics.core import UnitKind
from pyeconomics.core import _fields as f
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.provenance import (
    DATA_DATE_BOUNDS,
    MAX_FALLBACK_CHAIN,
    MAX_WARNINGS,
    DataSource,
    LicenceClass,
    LlmUse,
    LlmUsePolicy,
    RealtimePeriod,
)
from pyeconomics.core.transforms import parse_transform
from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.catalog import transforms as tf
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived, Shape
from pyeconomics.data.credentials import has_key
from pyeconomics.data.errors import (
    CredentialError,
    DataError,
    LicenceError,
    LlmUseError,
    OfflineError,
    ProviderNotFoundError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    SourceDisabledError,
    TransportError,
)
from pyeconomics.data.modes import Mode, current_mode, is_disabled, require_allowed
from pyeconomics.data.providers.base import AuthKind, Capability, current_platform
from pyeconomics.data.types import (
    DECIMAL_KINDS,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    Table,
)
from pyeconomics.data.vintage import Vintage, VintageKind

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

    from pyeconomics.data.cache.policy import Fetched
    from pyeconomics.data.providers.base import DataProvider, Query
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.data.terms import Terms
    from pyeconomics.data.transport.base import Transport

__all__ = ["REASONS", "Resolved", "Skip", "resolve", "trim"]

#: Every reason a candidate may be passed over, with what it means.
REASONS: Final = {
    "disabled": "the disabled_providers setting turns the provider off",
    "licence_refused": "hosted mode refuses the candidate's licence class",
    "llm_use": "the llm_use policy does not permit the source's terms",
    "provider_unavailable": "the provider is not registered",
    "platform_unsupported": "the provider does not run on this platform",
    "key_missing": "the provider needs an API key and none is configured",
    "extra_missing": "the provider's optional dependency is not installed",
    "vintage_unsupported": "the source keeps no vintages, so it cannot honour one",
    "credential_refused": "the source refused the key",
    "series_not_found": "the source has no such series",
    "rate_limited": "the source's rate limit held",
    "unavailable": "the source could not be reached",
    "offline": "offline mode had no cached answer",
    "bad_response": "the source's answer was malformed",
    "definition_mismatch": "the answer does not match the concept's definition",
    "transform_failed": "a transform could not be applied to the answer",
    "no_observations": "the answer holds no observation in the window",
    "operand_failed": "a concept this one is derived from could not be resolved",
    "data_error": "the provider refused the request",
}

_SKIPPED_PREFIX: Final = "skipped_"
_ONE_YEAR: Final = dt.timedelta(days=366)
_LOOKBACK_YEARS: Final = {"yoy": 2, "convert": 2}
_PERIOD_DAYS: Final = 400
#: Unit kinds that are one dimensionless decimal, interchangeable in a definition.
_DIMENSIONLESS: Final = frozenset({UnitKind.RATE, UnitKind.RATIO})
_DERIVED: Final = "derived"


@dataclass(frozen=True, slots=True, kw_only=True)
class Skip:
    """A candidate the resolver passed over, and why."""

    provider: str
    """The provider id, or ``derived`` for a derived candidate."""
    series: str
    reason: str
    """One of :data:`REASONS`."""
    detail: str
    licence: LicenceClass | None = None
    """The candidate's licence class, when the reason concerns it."""
    terms_url: str | None = None
    """The candidate's terms page, when the reason concerns its licence."""
    llm_use: LlmUse | None = None
    """The source's ``llm_use`` class, when the reason is ``llm_use``."""

    def __post_init__(self) -> None:
        """Check the reason and the texts."""
        if self.reason not in REASONS:
            msg = f"{self.reason!r} is not a skip reason"
            raise f.fail(msg)
        f.text(self.provider, "provider")
        f.text(self.series, "series")
        f.text(self.detail, "detail", max_length=f.MAX_TEXT_LENGTH)

    def to_dict(self) -> dict[str, object]:
        """Return the skip as JSON-ready values, as documents and exports carry it.

        ``llm_use`` stays out: the reason and the detail already say it, so a
        resolution without a policy reads exactly as it did before there was one.
        """
        return {
            "provider": self.provider,
            "series": self.series,
            "reason": self.reason,
            "detail": self.detail,
            "licence": None if self.licence is None else self.licence.value,
            "terms_url": self.terms_url,
        }

    @property
    def code(self) -> str:
        """The warning code a ``DataSource`` records for this skip."""
        return f"{_SKIPPED_PREFIX}{self.provider}_{self.reason}"[:64]


@dataclass(frozen=True, slots=True)
class Resolved:
    """What a resolution returns: the data, its records and what was passed over.

    ``sources`` holds one :class:`~pyeconomics.core.provenance.DataSource` for a
    provider series and one per operand for a derived concept. A derived
    concept's records all name the derived concept and end their transforms with
    the combining transform, numerator or first operand first.
    """

    frame: Series | Table
    sources: tuple[DataSource, ...]
    concept: str | None = None
    skipped: tuple[Skip, ...] = ()

    @property
    def source(self) -> DataSource:
        """The record of the first (or only) source read."""
        return self.sources[0]

    @property
    def providers(self) -> tuple[str, ...]:
        """The provider ids read, in order."""
        return tuple(dict.fromkeys(source.provider for source in self.sources))


@dataclass(frozen=True, slots=True, kw_only=True)
class _Ask:
    """What one resolution was asked for, shared by every candidate."""

    start: dt.date | None
    end: dt.date | None
    selector: Vintage
    mode: Mode
    strict: bool
    max_observations: int | None
    parameters: Mapping[str, str]
    transport: Transport | None
    registry: ProviderRegistry
    min_observations: int | None = None
    llm_use: LlmUsePolicy | None = None


def _selector(as_of: dt.date | None, vintage: Vintage | str | None) -> Vintage:
    """Turn ``as_of`` or ``vintage`` into one selector; both at once is a mistake."""
    if as_of is not None and vintage is not None:
        msg = "ask for as_of or for a vintage, not both"
        raise f.fail(msg)
    if as_of is not None:
        return Vintage.as_of(f.day(as_of, "as_of", DATA_DATE_BOUNDS))
    if vintage is None:
        return Vintage.latest()
    return vintage if isinstance(vintage, Vintage) else Vintage.parse(vintage)


def _parameters(concept: Concept, given: Mapping[str, object] | None) -> dict[str, str]:
    """Check the caller's parameters against the concept's declared ones."""
    supplied = dict(given or {})
    declared = {parameter.name: parameter for parameter in concept.parameters}
    unknown = sorted(set(supplied) - set(declared))
    if unknown:
        known = ", ".join(declared) or "none"
        msg = f"{concept.id} takes no parameter {unknown[0]!r}; its parameters: {known}"
        raise f.fail(msg)
    missing = sorted(set(declared) - set(supplied))
    if missing:
        example = declared[missing[0]].example
        msg = f"{concept.id} needs the parameter {missing[0]!r}, such as {example!r}"
        raise f.fail(msg)
    return {name: declared[name].check(value) for name, value in supplied.items()}


def _lookback(transforms: Sequence[str]) -> dt.timedelta | None:
    """Return how much history before ``start`` the transforms need.

    ``None`` means all of it (``changes_only`` needs the state before the window).
    """
    widest = dt.timedelta(0)
    for text in transforms:
        parsed = parse_transform(text)
        if parsed.name == "changes_only":
            return None
        years = _LOOKBACK_YEARS.get(parsed.name)
        if years is not None:
            widest = max(widest, _ONE_YEAR * years)
        periods = parsed.arguments.get("periods")
        if isinstance(periods, int) and not isinstance(periods, bool):
            widest = max(widest, dt.timedelta(days=_PERIOD_DAYS * (periods + 1)))
    return widest


def _widened(start: dt.date | None, transforms: Sequence[str]) -> dt.date | None:
    """Return the first date to request so the transforms see enough history."""
    if start is None:
        return None
    back = _lookback(transforms)
    if back is None:
        return None
    return max(start - back, DATA_DATE_BOUNDS.lower)


@overload
def trim(frame: Series, start: dt.date | None, end: dt.date | None) -> Series: ...
@overload
def trim(frame: Table, start: dt.date | None, end: dt.date | None) -> Table: ...
@overload
def trim(
    frame: Series | Table, start: dt.date | None, end: dt.date | None
) -> Series | Table: ...
def trim(
    frame: Series | Table, start: dt.date | None, end: dt.date | None
) -> Series | Table:
    """Keep the rows dated from ``start`` to ``end`` inclusive.

    Examples
    --------
    >>> import datetime as dt
    >>> from pyeconomics.data import (
    ...     CachePolicy, DateConvention, LicenceClass, LlmUse, ObservationFrequency,
    ...     SeasonalAdjustment, Series, SeriesMeta, Terms, UnitRecord,
    ... )
    >>> terms = Terms(licence=LicenceClass.HOSTED_SAFE, terms_url="https://x.example",
    ...     checked=dt.date(2026, 10, 15), attribution="Source: X.",
    ...     llm_use=LlmUse.ALLOWED, cache=CachePolicy.ALLOWED)
    >>> meta = SeriesMeta(provider="demo", series_id="X", title="X",
    ...     unit=UnitRecord(text="Index"), frequency=ObservationFrequency.ANNUAL,
    ...     seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
    ...     source_dating=DateConvention.PERIOD_END, terms=terms)
    >>> days = (dt.date(2022, 12, 31), dt.date(2023, 12, 31), dt.date(2024, 12, 31))
    >>> trim(Series(days, (1.0, 2.0, 3.0), meta), dt.date(2023, 1, 1), None).values
    (2.0, 3.0)
    """
    rows = [
        row
        for row, day in enumerate(frame.index)
        if (start is None or day >= start) and (end is None or day <= end)
    ]
    if len(rows) == len(frame.index):
        return frame
    index = tuple(frame.index[row] for row in rows)
    realtime = (
        None if frame.realtime is None else tuple(frame.realtime[row] for row in rows)
    )
    if isinstance(frame, Series):
        values = tuple(frame.values[row] for row in rows)
        return replace(frame, index=index, values=values, realtime=realtime)
    data = tuple(tuple(column[row] for row in rows) for column in frame.data)
    return replace(frame, index=index, data=data, realtime=realtime)


# --- shaping and checking a fetched frame -----------------------------------------


def _select_columns(table: Table, candidate: Candidate, concept: Concept) -> Table:
    """Keep and rename a table's columns as the candidate says."""
    names: dict[int, str]
    if candidate.keep is not None:
        pattern = re.compile(candidate.keep)
        names = {
            i: column.name
            for i, column in enumerate(table.columns)
            if pattern.search(column.name)
        }
        if not names:
            msg = f"no column of {table.meta.table_id} matches {candidate.keep!r}"
            raise DataError(msg, provider=table.meta.provider)
    elif candidate.columns:
        position = {column.name: i for i, column in enumerate(table.columns)}
        names = {}
        for wanted, source in candidate.columns:
            if source not in position:
                msg = (
                    f"{table.meta.table_id} has no column {source!r} for "
                    f"{concept.id} column {wanted!r}"
                )
                raise DataError(msg, provider=table.meta.provider)
            names[position[source]] = wanted
    else:
        return table
    return replace(
        table,
        columns=tuple(
            replace(table.columns[i], name=name) for i, name in names.items()
        ),
        data=tuple(table.data[i] for i in names),
    )


def _shape(
    frame: Series | Table, candidate: Candidate, concept: Concept
) -> tuple[Series | Table, str]:
    """Turn the fetched frame into the concept's shape; return it with its id."""
    if isinstance(frame, Series):
        if concept.shape is Shape.TABLE:
            msg = f"{frame.meta.series_id} is a series, but {concept.id} is a table"
            raise DataError(msg, provider=frame.meta.provider)
        return frame, frame.meta.series_id
    identifier = frame.meta.table_id
    if concept.shape is Shape.TABLE:
        return _select_columns(frame, candidate, concept), identifier
    if candidate.column is None:
        msg = f"{identifier} is a table; {concept.id} needs a column of it"
        raise DataError(msg, provider=frame.meta.provider)
    if candidate.column not in frame.column_names:
        msg = f"{identifier} has no column {candidate.column!r}"
        raise DataError(msg, provider=frame.meta.provider)
    return frame.column(candidate.column), f"{identifier}:{candidate.column}"


def _cadence(frequency: ObservationFrequency) -> str:
    if frequency in {ObservationFrequency.DAILY, ObservationFrequency.BUSINESS_DAILY}:
        return "daily"
    return frequency.value


def _kind_ok(wanted: UnitKind | None, found: UnitKind | None) -> bool:
    """Say whether a unit kind satisfies the concept's.

    A decimal kind must be known exactly (a rate in the wrong scale is the error
    the boundary exists to stop); a dimensionless decimal may be a rate or a
    ratio; any other kind may be unlabelled by a source that has no vocabulary
    for it (an index level).
    """
    if wanted is None or wanted == found:
        return True
    if wanted in _DIMENSIONLESS and found in _DIMENSIONLESS:
        return True
    return found is None and wanted not in DECIMAL_KINDS


def _season_class(value: SeasonalAdjustment) -> str | None:
    if value is SeasonalAdjustment.NOT_APPLICABLE:
        return None
    return "nsa" if value is SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED else "sa"


def _season_ok(wanted: SeasonalAdjustment, found: SeasonalAdjustment) -> bool:
    first, second = _season_class(wanted), _season_class(found)
    return first is None or second is None or first == second


def _series_problem(concept: Concept, series: Series) -> str | None:
    meta = series.meta
    if not _kind_ok(concept.unit_kind, meta.unit.kind):
        return f"unit kind is {meta.unit.kind}, but {concept.id} is {concept.unit_kind}"
    if not _season_ok(concept.seasonal_adjustment, meta.seasonal_adjustment):
        return (
            f"seasonal adjustment is {meta.seasonal_adjustment.value}, but "
            f"{concept.id} is {concept.seasonal_adjustment.value}"
        )
    return None


def _table_problem(concept: Concept, table: Table) -> str | None:
    for column in table.columns:
        if not _kind_ok(concept.unit_kind, column.unit.kind):
            return (
                f"column {column.name!r} has unit kind {column.unit.kind}, but "
                f"{concept.id} is {concept.unit_kind}"
            )
    return None


def _mismatch(
    concept: Concept, candidate: Candidate | None, frame: Series | Table
) -> str | None:
    """Return why a frame is not the concept, or ``None`` when it is."""
    meta = frame.meta
    allowed = {_cadence(concept.frequency)}
    if candidate is not None and candidate.delivers is not None:
        allowed.add(_cadence(candidate.delivers))
    if _cadence(meta.frequency) not in allowed:
        return (
            f"frequency is {meta.frequency.value}, but {concept.id} is "
            f"{concept.frequency.value}"
        )
    if (
        concept.shape is Shape.SERIES
        and meta.frequency.needs_year_end
        and meta.year_ends_in != concept.year_ends_in
    ):
        return f"the year ends in month {meta.year_ends_in}, not {concept.year_ends_in}"
    if isinstance(frame, Series):
        return _series_problem(concept, frame)
    return _table_problem(concept, frame)


# --- the candidates -------------------------------------------------------------


_URL: Final = re.compile(r"https?://\S+")


def _first_line(error: Exception) -> str:
    """Return an error's first line without any URL: a detail names no address."""
    lines = str(error).strip().splitlines()
    text = _URL.sub("[page]", lines[0] if lines else type(error).__name__)
    return text.replace("://", ":")[: f.MAX_TEXT_LENGTH]


def _skip_for(
    error: Exception, provider: str, series: str, licence: LicenceClass | None = None
) -> Skip:
    """Map an error from a candidate to the reason it is passed over."""
    reasons: tuple[tuple[type[Exception], str], ...] = (
        (SourceDisabledError, "disabled"),
        (LlmUseError, "llm_use"),
        (LicenceError, "licence_refused"),
        (MissingOptionalDependencyError, "extra_missing"),
        (CredentialError, "credential_refused"),
        (SeriesNotFoundError, "series_not_found"),
        (RateLimitError, "rate_limited"),
        (OfflineError, "offline"),
        (TransportError, "unavailable"),
        (ResponseError, "bad_response"),
        (ProviderNotFoundError, "provider_unavailable"),
    )
    reason = next((r for kind, r in reasons if isinstance(error, kind)), "data_error")
    terms_url = None
    if isinstance(error, LicenceError):
        licence, terms_url = error.licence, error.terms_url
    return Skip(
        provider=provider,
        series=series,
        reason=reason,
        detail=_first_line(error),
        licence=licence,
        terms_url=terms_url,
        llm_use=error.llm_use if isinstance(error, LlmUseError) else None,
    )


def _llm_skip(
    provider: str, series: str, terms: Terms, policy: LlmUsePolicy, whose: str
) -> Skip:
    """Return the skip of a candidate whose terms the ``llm_use`` policy refuses."""
    return Skip(
        provider=provider,
        series=series,
        reason="llm_use",
        detail=(
            f"{whose} terms make its data {terms.llm_use.value} for language "
            f"models, which the {policy.value} policy does not permit"
        ),
        licence=terms.licence,
        terms_url=terms.terms_url,
        llm_use=terms.llm_use,
    )


def _refusal(  # noqa: PLR0911 - one return per refusal, in the order checked
    provider: DataProvider, series: str, ask: _Ask, *, keeps_vintages: bool = True
) -> Skip | None:
    """Return the skip a candidate earns before any request, or ``None``.

    A vintage the source can never serve is refused before its key is asked for,
    so a missing key is not blamed for it.
    """
    info = provider.info

    def skip(reason: str, detail: str, *, licensed: bool = False) -> Skip:
        return Skip(
            provider=info.id,
            series=series,
            reason=reason,
            detail=detail,
            licence=info.terms.licence if licensed else None,
            terms_url=info.terms.terms_url if licensed else None,
        )

    if is_disabled(info.id):
        return skip("disabled", f"{info.id} is named in disabled_providers")
    platform = current_platform()
    if platform is None or not info.supports(platform):
        return skip("platform_unsupported", f"{info.id} does not run on this platform")
    if ask.mode is Mode.HOSTED and not info.terms.licence.hosted_allowed:
        return skip(
            "licence_refused",
            f"{info.id} is {info.terms.licence.value}; hosted mode serves only "
            "hosted-safe and user-supplied data",
            licensed=True,
        )
    if ask.llm_use is not None and not ask.llm_use.permits(info.terms.llm_use):
        return _llm_skip(info.id, series, info.terms, ask.llm_use, f"{info.id}'s")
    keeps_none = Capability.VINTAGES not in info.capabilities
    if ask.selector.kind is not VintageKind.LATEST and (
        keeps_none or not keeps_vintages
    ):
        whose = "" if keeps_none else f" of {series}"
        return skip(
            "vintage_unsupported",
            f"{info.id} keeps no vintages{whose}, so {ask.selector.label} "
            "cannot be read",
        )
    if info.auth.kind is AuthKind.KEY and info.auth.required and not has_key(info.id):
        return skip("key_missing", f"set {info.key_variable}")
    return None


def _query(
    provider: DataProvider, candidate: Candidate, series: str, ask: _Ask
) -> Query:
    """Build the provider's query; widen the window for the candidate's transforms."""
    fields: dict[str, object] = {
        "series": (series,),
        "start": _widened(ask.start, candidate.transforms),
        "end": ask.end,
        "vintage": ask.selector.label,
        **dict(candidate.options),
    }
    if ask.max_observations is not None:
        fields["max_observations"] = ask.max_observations
    return provider.query_type.model_validate(fields)


def _record(  # noqa: PLR0913 - the record joins the fetch, the shape and the chain
    fetched: Fetched,
    frame: Series | Table,
    *,
    identifier: str,
    concept: Concept,
    transforms: tuple[str, ...],
    skipped: Sequence[Skip],
) -> DataSource:
    """Build the provenance record of a resolved candidate."""
    base = fetched.source()
    last = None if frame.realtime is None else frame.realtime[-1]
    codes = tuple(dict.fromkeys((*base.warnings, *(s.code for s in skipped))))
    chain = _chain(skipped, base.provider)
    return replace(
        base,
        series_id=identifier,
        concept=concept.id,
        realtime=last if isinstance(last, RealtimePeriod) else None,
        observation_start=frame.index[0],
        observation_end=frame.index[-1],
        transforms=transforms,
        fallback_chain=chain[-MAX_FALLBACK_CHAIN:],
        warnings=codes[:MAX_WARNINGS],
    )


def _chain(skipped: Sequence[Skip], chosen: str) -> tuple[str, ...]:
    """List the providers tried, in order, ending with the one chosen."""
    tried = [s.provider for s in skipped if s.provider not in {_DERIVED, chosen}]
    return (*dict.fromkeys(tried), chosen)


def _fetch(candidate: Candidate, series: str, ask: _Ask) -> Fetched | Skip:
    """Fetch a candidate's series, or say why it was passed over."""
    try:
        provider = ask.registry.get(candidate.provider)
    except ProviderNotFoundError as error:
        return _skip_for(error, candidate.provider, series)
    refusal = _refusal(provider, series, ask, keeps_vintages=candidate.vintages)
    if refusal is not None:
        return refusal
    try:
        query = _query(provider, candidate, series, ask)
        fetched = provider.fetch_with_origin(query, transport=ask.transport)
        # The provider judges a series' own terms by the configured mode; judge
        # them again by the mode this resolution was asked for.
        terms = fetched.frame.meta.terms
        require_allowed(terms, provider=candidate.provider, mode=ask.mode)
    except ValidationError as error:
        return Skip(
            provider=candidate.provider,
            series=series,
            reason="data_error",
            detail=(
                f"the provider rejected the catalog's query "
                f"({error.error_count()} errors)"
            ),
        )
    except (DataError, MissingOptionalDependencyError) as error:
        return _skip_for(error, candidate.provider, series, provider.info.terms.licence)
    # A series' own terms can be stricter than its provider's (an SDMX series).
    if ask.llm_use is not None and not ask.llm_use.permits(terms.llm_use):
        return _llm_skip(candidate.provider, series, terms, ask.llm_use, "the series'")
    return fetched


def _transformed(
    fetched: Fetched, candidate: Candidate, concept: Concept, series: str
) -> tuple[Series | Table, str] | Skip:
    """Shape the fetched frame and apply the candidate's transforms."""
    try:
        frame, identifier = _shape(fetched.frame, candidate, concept)
        if isinstance(frame, Series):
            for text in candidate.transforms:
                frame = tf.apply(text, frame)
    except DataError as error:
        reason = "transform_failed" if candidate.transforms else "definition_mismatch"
        return Skip(
            provider=candidate.provider,
            series=series,
            reason=reason,
            detail=_first_line(error),
        )
    return frame, identifier


def _try_provider(
    concept: Concept, candidate: Candidate, ask: _Ask, skipped: Sequence[Skip]
) -> Resolved | Skip:
    series = candidate.series.format_map(ask.parameters)
    fetched = _fetch(candidate, series, ask)
    if isinstance(fetched, Skip):
        return fetched
    if candidate.column is not None:
        candidate = replace(
            candidate, column=candidate.column.format_map(ask.parameters)
        )
    shaped = _transformed(fetched, candidate, concept, series)
    if isinstance(shaped, Skip):
        return shaped
    frame, identifier = shaped
    frame = trim(frame, ask.start, ask.end)
    short = _too_short(frame, ask)
    problem = short or (
        "the answer holds no observation in the window"
        if not frame.index
        else _mismatch(concept, candidate, frame)
    )
    if problem is not None:
        reason = (
            "no_observations" if short or not frame.index else "definition_mismatch"
        )
        return Skip(
            provider=candidate.provider, series=series, reason=reason, detail=problem
        )
    record = _record(
        fetched,
        frame,
        identifier=identifier,
        concept=concept,
        transforms=candidate.transforms,
        skipped=skipped,
    )
    return Resolved(frame, (record,), concept.id, tuple(skipped))


def _operand(candidate: Derived, ask: _Ask, position: int) -> Resolved:
    """Resolve one operand of a derived candidate, widening for its transforms."""
    operand = candidate.operands[position]
    return resolve(
        operand.concept,
        start=_widened(ask.start, operand.transforms),
        end=ask.end,
        vintage=ask.selector,
        mode=ask.mode,
        strict=ask.strict,
        max_observations=ask.max_observations,
        transport=ask.transport,
        registry=ask.registry,
        min_observations=ask.min_observations,
        llm_use=ask.llm_use,
    )


def _too_short(frame: Series | Table, ask: _Ask) -> str | None:
    """Say why an answer with fewer observations than asked for is passed over."""
    count = len(frame.index)
    if ask.min_observations is None or not count or count >= ask.min_observations:
        return None
    return (
        f"the answer holds {count} observations in the window, fewer than the "
        f"{ask.min_observations} asked for"
    )


def _combine(candidate: Derived, parts: Sequence[Resolved]) -> Series:
    """Apply each operand's transforms, then the combining transform."""
    frames: list[Series] = []
    for operand, part in zip(candidate.operands, parts, strict=True):
        frame = part.frame
        if not isinstance(frame, Series):
            msg = f"{operand.concept} is not a series"
            raise DataError(msg)
        for text in operand.transforms:
            frame = tf.apply(text, frame)
        frames.append(frame)
    return tf.apply(candidate.transform, frames[0], frames[1])


def _try_derived(
    concept: Concept, candidate: Derived, ask: _Ask, skipped: Sequence[Skip]
) -> Resolved | Skip:
    where = " and ".join(operand.concept for operand in candidate.operands)

    def skip(reason: str, detail: str) -> Skip:
        return Skip(provider=_DERIVED, series=where, reason=reason, detail=detail)

    try:
        parts = [_operand(candidate, ask, i) for i in range(len(candidate.operands))]
    except (DataError, MissingOptionalDependencyError) as error:
        failure = _skip_for(error, _DERIVED, where)
        if failure.reason in {"licence_refused", "llm_use"}:
            return failure
        return replace(failure, reason="operand_failed")
    try:
        combined = trim(_combine(candidate, parts), ask.start, ask.end)
    except DataError as error:
        return skip("transform_failed", _first_line(error))
    short = _too_short(combined, ask)
    if short is not None or not combined.index:
        detail = short or "the operands share no observation in the window"
        return skip("no_observations", detail)
    problem = _mismatch(concept, None, combined)
    if problem is not None:
        return skip("definition_mismatch", problem)
    records = tuple(
        replace(
            record,
            concept=concept.id,
            transforms=(*record.transforms, *operand.transforms, candidate.transform),
        )
        for operand, part in zip(candidate.operands, parts, strict=True)
        for record in part.sources
    )
    return Resolved(combined, records, concept.id, tuple(skipped))


def _exhausted(
    concept: Concept,
    skipped: Sequence[Skip],
    mode: Mode,
    *,
    strict: bool,
    policy: LlmUsePolicy | None = None,
) -> DataError:
    """Build the error for a concept no candidate could answer."""
    reasons = {s.reason for s in skipped}
    listing = "; ".join(
        f"{s.provider} {s.series}: {s.reason} ({s.detail})" for s in skipped
    )
    prefix = f"{concept.id} cannot be resolved{' strictly' if strict else ''}: "
    # A source that cannot read the vintage asked for is not why nothing answered:
    # the key or the cache of the one that could is.
    blocking = reasons - {"vintage_unsupported"}
    refused = [s for s in skipped if s.reason == "llm_use"]
    if policy is not None and refused and blocking <= {"llm_use", "licence_refused"}:
        first = refused[0]
        return LlmUseError(
            f"{concept.id} has no source whose terms let its data reach a language "
            f"model under the {policy.value} policy: {listing}",
            provider=first.provider,
            licence=first.licence or LicenceClass.LIBRARY_ONLY,
            llm_use=first.llm_use or LlmUse.FORBIDDEN,
            terms_url=first.terms_url,
            concept=concept.id,
        )
    if reasons == {"licence_refused"} and mode is Mode.HOSTED:
        classes = sorted({s.licence.value for s in skipped if s.licence is not None})
        providers = ", ".join(sorted({s.provider for s in skipped}))
        return LicenceError(
            f"{concept.id} has no source hosted mode may serve; classes found: "
            f"{', '.join(classes)} ({providers})",
            provider=skipped[0].provider,
            licence=skipped[0].licence or LicenceClass.LIBRARY_ONLY,
            terms_url=skipped[0].terms_url,
        )
    if blocking == {"disabled"}:
        disabled = sorted({s.provider for s in skipped if s.reason == "disabled"})
        return SourceDisabledError(*disabled, concept=concept.id)
    if blocking == {"key_missing"}:
        return CredentialError(prefix + listing)
    if blocking == {"offline"}:
        return OfflineError(prefix + listing)
    return DataError(prefix + listing)


def resolve(  # noqa: PLR0913 - the public resolution contract has independent options
    concept: str | Concept,
    *,
    start: dt.date | None = None,
    end: dt.date | None = None,
    as_of: dt.date | None = None,
    vintage: Vintage | str | None = None,
    mode: Mode | None = None,
    strict: bool = False,
    provider: str | None = None,
    parameters: Mapping[str, object] | None = None,
    max_observations: int | None = None,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
    min_observations: int | None = None,
    llm_use: LlmUsePolicy | str | None = None,
) -> Resolved:
    """Resolve a concept to data, trying its candidates in fallback order.

    Parameters
    ----------
    concept
        A concept id or a :class:`~pyeconomics.data.catalog.Concept`.
    start, end
        The first and last observation dates wanted; the sources are asked for
        enough earlier history that the concept's transforms (a year-over-year
        change needs a year before ``start``) have it, and the result is cut to
        the window.
    as_of
        Read the data as published on this date: ``vintage=Vintage.as_of(...)``.
    vintage
        A :class:`~pyeconomics.data.vintage.Vintage` or its label. A source that
        keeps no vintages cannot honour anything but ``latest`` and is skipped.
    mode
        ``library`` or ``hosted``; the configured mode by default.
    strict
        Try the first candidate only: no fallback.
    provider
        Restrict the candidates to one provider's.
    parameters
        The values of the concept's parameters, such as an SEP ``meeting``.
    max_observations
        At most this many (the most recent) observations per fetch.
    min_observations
        Pass over a candidate whose answer holds fewer observations than this
        in the window (a binding that reads a run of them), so the next one,
        with a longer history, answers.
    transport
        The transport providers send through (a test passes a replay).
    registry
        The provider registry; the installed one by default.
    llm_use
        An :class:`~pyeconomics.core.provenance.LlmUsePolicy`, or its value: pass
        over every source whose terms, or whose series' own terms, it does not
        permit (ADR-0012 decision 14). ``None``, the default, looks at no
        ``llm_use`` class.

    Returns
    -------
    Resolved
        The frame, its ``DataSource`` records and the candidates passed over.

    Raises
    ------
    ConceptNotFoundError
        If the id is not in the catalog.
    InputError
        For a missing parameter or window, ``as_of`` with ``vintage``, or an
        ``llm_use`` that is not a policy.
    LicenceError
        If hosted mode refuses every candidate; it names the classes found.
    LlmUseError
        If the ``llm_use`` policy (with any hosted refusals) leaves no candidate.
    DataError
        If no candidate answers; the message lists why each was passed over.
    """
    found = catalog.get(concept) if isinstance(concept, str) else concept
    if found.needs_window and (start is None or end is None):
        msg = f"{found.id} needs both start and end dates"
        raise f.fail(msg)
    if start is not None and end is not None and start > end:
        msg = f"start {start} is after end {end}"
        raise f.fail(msg)
    ask = _Ask(
        start=start,
        end=end,
        selector=_selector(as_of, vintage),
        mode=mode or current_mode(),
        strict=strict,
        max_observations=max_observations,
        parameters=_parameters(found, parameters),
        transport=transport,
        registry=registry or provider_registry.installed(),
        min_observations=min_observations,
        llm_use=None if llm_use is None else f.choice(LlmUsePolicy, llm_use, "llm_use"),
    )
    candidates = [
        c
        for c in found.candidates
        if provider is None or (isinstance(c, Candidate) and c.provider == provider)
    ]
    if not candidates:
        msg = f"{found.id} has no candidate from provider {provider!r}"
        raise f.fail(msg)
    if strict:
        candidates = candidates[:1]
    skipped: list[Skip] = []
    for candidate in candidates:
        outcome = (
            _try_provider(found, candidate, ask, skipped)
            if isinstance(candidate, Candidate)
            else _try_derived(found, candidate, ask, skipped)
        )
        if isinstance(outcome, Resolved):
            return outcome
        skipped.append(outcome)
    raise _exhausted(found, skipped, ask.mode, strict=strict, policy=ask.llm_use)
