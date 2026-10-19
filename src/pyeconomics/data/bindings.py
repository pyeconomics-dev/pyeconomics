# src/pyeconomics/data/bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bind a model's input fields to data and record where it came from (ADR-0011 16).

A model declares :class:`~pyeconomics.core.binding.Binding` values; this module
resolves one profile of them, before ``compute`` runs, so the model stays pure.
:func:`bind` is ``pyeconomics.bind``: for each bound field it resolves the
binding's catalog concept through :func:`~pyeconomics.data.resolver.resolve`,
applies the binding's transform and its as-of rule, converts to the field's unit
and returns a :class:`~pyeconomics.core.binding.Bound` of the values and one
:class:`~pyeconomics.core.provenance.DataSource` record per field. ``run`` takes
that ``Bound`` and puts the records in the result's manifest.

- **Real time by default.** With an ``as_of`` date, a binding reads the vintage
  published by that date wherever a source usable in the mode keeps vintages
  (ADR-0011 decision 6). Where none does, the binding layer reads the latest
  data, records ``revised_data`` in the field's record and the result warns.
  ``VintagePolicy.LATEST`` asks for revised data and is labelled the same way.
  Nothing passes revised data off as real-time.
- **One rule picks the value.** The as-of rule is one of the alignment transforms
  (``asof``, ``period``, ``window``) at the evaluation date, or, with no date, at
  the series' last observation; the record lists it. A binding never fills a gap
  or reads a stale value silently: a date with nothing to read raises.
- **An override replaces a bound value** and is recorded as user-supplied; the
  value itself is an input, fingerprinted with the rest.
- **One fetch per series.** The fetches share an in-process memo
  (:func:`pyeconomics.data.cache.memo`), so a series two bindings read is asked
  for once even when its terms forbid storage. Offline mode serves the cache
  only, and :class:`~pyeconomics.data.errors.OfflineError` propagates when it
  has nothing.

:func:`validate_bindings` checks every registered model's bindings against the
installed catalog, which core cannot do, and :func:`candidate_notes` describes
the sources that can fill a concept for a model's card.

Examples
--------
>>> from pyeconomics.data.bindings import lookback_days
>>> from pyeconomics.data import ObservationFrequency
>>> lookback_days(ObservationFrequency.QUARTERLY, 4)
767
"""

from __future__ import annotations

import datetime as dt
import difflib
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
from pyeconomics.core import _fields as f
from pyeconomics.core.binding import (
    DEFAULT_PROFILE,
    REVISED_DATA,
    AsOf,
    Binding,
    Bound,
    CandidateNote,
    FieldShape,
    VintagePolicy,
    field_shapes,
    user_supplied,
)
from pyeconomics.core.errors import RegistryError
from pyeconomics.core.provenance import (
    DATA_DATE_BOUNDS,
    MAX_WARNINGS,
    DataSource,
)
from pyeconomics.core.transforms import canonical_transform, format_transform
from pyeconomics.data import cache, catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.data.catalog import transforms as tf
from pyeconomics.data.catalog.definitions import Candidate, Concept, Derived, Shape
from pyeconomics.data.errors import DataError, ProviderNotFoundError
from pyeconomics.data.modes import Mode, current_mode
from pyeconomics.data.providers.base import Capability
from pyeconomics.data.resolver import Resolved, resolve
from pyeconomics.data.types import (
    DECIMAL_KINDS,
    ObservationFrequency,
    Series,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core.model import Model
    from pyeconomics.core.registry import Registry
    from pyeconomics.data.registry import ProviderRegistry
    from pyeconomics.data.transport.base import Transport

__all__ = [
    "bind",
    "bind_model",
    "candidate_notes",
    "lookback_days",
    "validate_bindings",
]

#: Calendar days one observation spans, for sizing the window a source is asked.
_SPAN_DAYS: Final = {
    ObservationFrequency.DAILY: 1,
    ObservationFrequency.BUSINESS_DAILY: 1,
    ObservationFrequency.WEEKLY: 7,
    ObservationFrequency.BIWEEKLY: 14,
    ObservationFrequency.MONTHLY: 31,
    ObservationFrequency.QUARTERLY: 92,
    ObservationFrequency.SEMIANNUAL: 184,
    ObservationFrequency.ANNUAL: 366,
    ObservationFrequency.IRREGULAR: 31,
}
#: Holidays and weekends mean a business-daily window spans about 1.4 times as
#: many days; double it, and add a month, so a window never comes up short.
_MARGIN_DAYS: Final = 31
#: Unit kinds that are one dimensionless decimal, interchangeable for a field.
_DIMENSIONLESS: Final = frozenset({UnitKind.RATE, UnitKind.RATIO})
_WHOLE: Final = frozenset({UnitKind.DAYS, UnitKind.COUNT})
_MAX_DEPTH: Final = 4


def lookback_days(frequency: ObservationFrequency, count: int = 1) -> int:
    """Return how many calendar days back to ask a source for ``count`` observations.

    Only a concept whose source answers for a window of dates (the Treasury
    curves) is asked for one; any other is asked for its whole history, so a
    binding never reads a value from a window it cut short.

    Examples
    --------
    >>> lookback_days(ObservationFrequency.BUSINESS_DAILY)
    33
    >>> lookback_days(ObservationFrequency.QUARTERLY, 4)
    767
    """
    return 2 * count * _SPAN_DAYS[frequency] + _MARGIN_DAYS


# --- the public entry points --------------------------------------------------------


def bind(  # noqa: PLR0913 - the public contract's independent options
    model_id: str,
    /,
    *,
    as_of: dt.date | None = None,
    vintage: VintagePolicy | str | None = None,
    mode: Mode | None = None,
    profile: str = DEFAULT_PROFILE,
    concepts: Mapping[str, str] | None = None,
    parameters: Mapping[str, object] | None = None,
    **overrides: object,
) -> Bound:
    """Bind a registered model's data as of a date; ``pyeconomics.bind``.

    Resolves the bindings of one profile through the catalog, applies each
    binding's transform and as-of rule, converts to the field's unit and returns
    the values with one record per bound field. ``pyeconomics.run(model_id,
    bound)`` runs them and records every series, vintage and retrieval time in
    the result's manifest.

    Parameters
    ----------
    model_id
        A model id or alias; the result is bound for the canonical model.
    as_of
        The evaluation date: each binding reads what was published by then. Left
        out, it reads the latest data at each series' last observation.
    vintage
        A :class:`~pyeconomics.core.binding.VintagePolicy` for every binding in
        place of their own; ``latest`` reads revised data and is labelled so.
    mode
        ``library`` or ``hosted``; the configured mode by default.
    profile
        The named set of bindings to resolve (``default``).
    concepts
        ``{field: concept}`` rebinds a field to another catalog concept of the
        same unit kind and frequency; any other is refused.
    parameters
        Values of concept parameters (an SEP ``meeting``), passed to each bound
        concept that declares them.
    **overrides
        Values the caller supplies. A bound field's value is replaced, not
        read, and recorded as user-supplied; any other field is carried as an
        ordinary input. (A field named ``parameters`` cannot be supplied this
        way; use :func:`bind_model`.)

    Returns
    -------
    Bound
        The values by field and the records of the data behind them.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    InputError
        For a model with no such profile, an unknown input field, a concept of
        another unit kind or frequency, a table concept, or a field the series'
        unit kind does not suit.
    ConceptNotFoundError, LicenceError, CredentialError, OfflineError, DataError
        As the catalog and the resolver raise them, and for a date the data
        cannot answer (nothing on or before it, a missing period, a short
        window); each names the concept.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - as run() does

    model = installed().resolve(model_id, stacklevel=3)
    return bind_model(
        model,
        as_of=as_of,
        vintage=vintage,
        mode=mode,
        profile=profile,
        concepts=concepts,
        parameters=parameters,
        overrides=overrides,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class _Ask:
    """What one bind was asked for, shared by every binding."""

    day: dt.date | None
    policy: VintagePolicy | None
    mode: Mode
    concepts: Mapping[str, str]
    parameters: Mapping[str, object]
    shapes: Mapping[str, tuple[FieldShape, ...]]
    transport: Transport | None
    registry: ProviderRegistry


def bind_model(  # noqa: PLR0913 - the public contract's independent options
    model: Model[Any, Any],
    /,
    *,
    as_of: dt.date | None = None,
    vintage: VintagePolicy | str | None = None,
    mode: Mode | None = None,
    profile: str = DEFAULT_PROFILE,
    concepts: Mapping[str, str] | None = None,
    parameters: Mapping[str, object] | None = None,
    overrides: Mapping[str, object] | None = None,
    transport: Transport | None = None,
    registry: ProviderRegistry | None = None,
) -> Bound:
    """Bind a model object's data; see :func:`bind`.

    ``overrides`` is a mapping here, so a field may have any name, and
    ``transport`` and ``registry`` are the seams a test uses: a replay transport
    and an isolated provider registry.
    """
    day = f.optional_day(as_of, "as_of", DATA_DATE_BOUNDS)
    policy = None if vintage is None else f.choice(VintagePolicy, vintage, "vintage")
    chosen = _profile(model, profile)
    shapes = field_shapes(model.spec.inputs)
    given = dict(overrides or {})
    unknown = sorted(set(given) - set(shapes))
    if unknown:
        known = ", ".join(sorted(shapes))
        msg = f"{model.id} has no input field {unknown[0]!r}; its fields: {known}"
        raise f.fail(msg)
    missing = sorted({b.field for b in chosen} - set(shapes))
    if missing:
        msg = f"{model.id} binds {missing[0]!r}, which is not one of its input fields"
        raise f.fail(msg)
    rebound = dict(concepts or {})
    unbound = sorted(set(rebound) - {binding.field for binding in chosen})
    if unbound:
        msg = f"{model.id} binds no field {unbound[0]!r} in the profile {profile!r}"
        raise f.fail(msg)
    ask = _Ask(
        day=day,
        policy=policy,
        mode=mode or current_mode(),
        concepts=rebound,
        parameters=dict(parameters or {}),
        shapes=shapes,
        transport=transport,
        registry=registry or provider_registry.installed(),
    )
    values: dict[str, object] = dict(given)
    records: list[DataSource] = []
    with cache.memo():
        for binding in chosen:
            if binding.field in given:
                records.append(user_supplied(binding.field, concept=binding.concept))
                continue
            read = _read(binding, ask)
            values[binding.field] = read.value
            records.extend(read.records)
    return Bound(
        model_id=model.id,
        profile=profile,
        values=values,
        sources=tuple(records),
        as_of=day,
    )


def _profile(model: Model[Any, Any], profile: str) -> list[Binding]:
    """Return the bindings of one profile, or say what the model offers."""
    chosen = [b for b in model.spec.bindings if b.profile == profile]
    if chosen:
        return chosen
    offered = sorted({b.profile for b in model.spec.bindings})
    if not offered:
        msg = f"{model.id} declares no data bindings"
    else:
        msg = (
            f"{model.id} has no profile {profile!r}; its profiles: {', '.join(offered)}"
        )
    raise f.fail(msg)


# --- reading one binding ------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _Read:
    """The value one binding read and the records behind it."""

    value: float | int | tuple[float | int, ...]
    records: tuple[DataSource, ...]


def _read(binding: Binding, ask: _Ask) -> _Read:
    """Resolve one binding to its value and its records."""
    concept = _concept(binding, ask)
    shape = ask.shapes[binding.field][0]
    policy = ask.policy or binding.vintage
    resolved, revised = _resolve(concept, binding, policy, ask)
    frame = resolved.frame
    if not isinstance(frame, Series):  # pragma: no cover - _concept refuses tables
        msg = f"{concept.id} is not a series"
        raise DataError(msg)
    where = f"{concept.id} for the field {binding.field!r}"
    try:
        series = frame
        if binding.transform is not None:
            series = tf.apply(binding.transform, frame)
        _check_unit(series, shape, where)
        rule = _rule(binding, series, ask.day)
        picked = tf.apply(rule, series)
    except DataError as error:
        msg = f"{where}: {error}"
        raise DataError(msg, provider=error.provider) from error
    own = () if binding.transform is None else (canonical_transform(binding.transform),)
    tail = (*own, canonical_transform(rule))
    records = tuple(
        _record(r, binding, concept.id, picked, tail, revised=revised)
        for r in resolved.sources
    )
    return _Read(_values(picked, shape), records)


def _concept(binding: Binding, ask: _Ask) -> Concept:
    """Look the concept up; a rebound one must match the declared one."""
    declared = catalog.get(binding.concept)
    chosen = ask.concepts.get(binding.field)
    concept = declared if chosen is None else catalog.get(chosen)
    if concept.shape is not Shape.SERIES:
        msg = f"{concept.id} is a table; a binding reads a series"
        raise f.fail(msg)
    if chosen is not None and (
        concept.unit_kind != declared.unit_kind
        or concept.frequency != declared.frequency
    ):
        msg = (
            f"{concept.id} cannot replace {declared.id} for {binding.field!r}: "
            f"it is {concept.unit_kind} at {concept.frequency.value} frequency, "
            f"not {declared.unit_kind} at {declared.frequency.value}"
        )
        raise f.fail(msg)
    return concept


def _resolve(
    concept: Concept, binding: Binding, policy: VintagePolicy, ask: _Ask
) -> tuple[Resolved, bool]:
    """Resolve a concept as the policy asks; say whether the data is revised."""
    day = ask.day
    start: dt.date | None = None
    if concept.needs_window:
        if day is None:
            msg = f"{concept.id} needs an as_of date: its sources answer for a window"
            raise f.fail(msg)
        count = binding.window if binding.as_of is AsOf.WINDOW else 1
        back = lookback_days(concept.frequency, count or 1)
        start = max(day - dt.timedelta(days=back), DATA_DATE_BOUNDS.lower)
    declared = {parameter.name for parameter in concept.parameters}
    # An observation is dated by its period's last day, so the period containing
    # the date is dated after it: that rule reads past the date (a vintage as of
    # the date still holds back what was not yet published).
    reads_ahead = binding.as_of is AsOf.PERIOD and not concept.needs_window
    common: dict[str, Any] = {
        "start": start,
        "end": None if reads_ahead else day,
        "mode": ask.mode,
        "parameters": {k: v for k, v in ask.parameters.items() if k in declared},
        "transport": ask.transport,
        "registry": ask.registry,
    }
    real_time = (
        policy is VintagePolicy.REAL_TIME
        and day is not None
        and _serves_vintages(concept, ask.mode, ask.registry)
    )
    if real_time:
        return resolve(concept, as_of=day, **common), False
    # Revised data: the latest values, because the policy asks for them or no
    # source usable in this mode keeps vintages. With no date there is nothing
    # to be revised against, so a real-time bind of today's data is not.
    revised = policy is VintagePolicy.LATEST or day is not None
    return resolve(concept, vintage="latest", **common), revised


def _serves_vintages(
    concept: Concept, mode: Mode, registry: ProviderRegistry, depth: int = 0
) -> bool:
    """Say whether some candidate usable in the mode can read a past vintage.

    From metadata alone: a registered provider that declares the ``vintages``
    capability and that the mode allows, or a derived candidate whose operands
    all can.
    """
    if depth > _MAX_DEPTH:  # pragma: no cover - the catalog checks forbid loops
        return False
    for candidate in concept.candidates:
        if isinstance(candidate, Derived):
            if all(
                _serves_vintages(catalog.get(o.concept), mode, registry, depth + 1)
                for o in candidate.operands
            ):
                return True
            continue
        try:
            info = registry.provider_class(candidate.provider).info
        except ProviderNotFoundError:
            continue
        if Capability.VINTAGES in info.capabilities and (
            mode is Mode.LIBRARY or info.terms.licence.hosted_allowed
        ):
            return True
    return False


def _rule(binding: Binding, series: Series, day: dt.date | None) -> str:
    """Write the as-of rule as the transform that applies it at the date.

    With no evaluation date the rule is read at the series' last observation.
    """
    if day is None:
        if not series.index:
            msg = "holds no observation"
            raise DataError(msg)
        day = series.index[-1]
    match binding.as_of:
        case AsOf.PERIOD:
            return format_transform("period", date=day)
        case AsOf.WINDOW:
            return format_transform("window", count=binding.window or 1, date=day)
        case _:
            return format_transform("asof", date=day)


def _check_unit(series: Series, shape: FieldShape, where: str) -> None:
    """Refuse a series whose unit kind the field cannot take."""
    wanted, found = shape.kind, series.meta.unit.kind
    if wanted is None or found == wanted:
        return
    if found in _DIMENSIONLESS and wanted in _DIMENSIONLESS:
        return
    if found is None and wanted not in DECIMAL_KINDS:
        return
    msg = f"{where}: the series is {found}, but the field is {wanted}"
    raise f.fail(msg)


def _values(picked: Series, shape: FieldShape) -> float | int | tuple[float | int, ...]:
    """Convert the picked observations to the field's unit and type."""
    scale = picked.meta.unit.scale
    numbers = [_number(v, scale, shape) for v in picked.values]
    return tuple(numbers) if shape.array else numbers[0]


def _number(value: float | None, scale: float, shape: FieldShape) -> float | int:
    """Scale one observation and, for a whole-number field, make it an ``int``."""
    if value is None:  # pragma: no cover - the as-of transforms refuse a gap
        msg = "an observation is missing"
        raise DataError(msg)
    scaled = value * scale
    if shape.kind in _WHOLE and float(scaled).is_integer():
        return int(scaled)
    return scaled


def _record(  # noqa: PLR0913 - the record joins the binding, the pick and the tail
    record: DataSource,
    binding: Binding,
    concept: str,
    picked: Series,
    tail: tuple[str, ...],
    *,
    revised: bool,
) -> DataSource:
    """Complete a resolver's record: the field, the picked window, the rule."""
    warnings = record.warnings
    if revised and REVISED_DATA not in warnings:
        warnings = (*warnings, REVISED_DATA)
    return replace(
        record,
        field=binding.field,
        concept=concept,
        realtime=picked.realtime[-1] if picked.realtime else None,
        observation_start=picked.index[0],
        observation_end=picked.index[-1],
        transforms=(*record.transforms, *tail),
        warnings=warnings[:MAX_WARNINGS],
    )


# --- describing and checking bindings ----------------------------------------------


def candidate_notes(
    model: Model[Any, Any], registry: ProviderRegistry | None = None
) -> dict[str, tuple[CandidateNote, ...]]:
    """Describe the sources that can fill each concept a model binds.

    From metadata alone (no key, no request): for each concept, its candidates in
    fallback order with their licence class, attribution and required notice. A
    model's card lists them in its "Data" section.
    """
    found = registry or provider_registry.installed()
    notes: dict[str, tuple[CandidateNote, ...]] = {}
    for binding in model.spec.bindings:
        if binding.concept in notes or binding.concept not in catalog.CONCEPTS:
            continue
        notes[binding.concept] = tuple(
            _note(candidate, found)
            for candidate in catalog.get(binding.concept).candidates
        )
    return notes


def _note(candidate: Candidate | Derived, registry: ProviderRegistry) -> CandidateNote:
    if isinstance(candidate, Derived):
        return CandidateNote(provider="derived", licence=None)
    try:
        terms = registry.provider_class(candidate.provider).info.terms
    except ProviderNotFoundError:
        return CandidateNote(provider=candidate.provider, licence=None)
    return CandidateNote(
        provider=candidate.provider,
        licence=terms.licence,
        attribution=terms.attribution,
        notice=terms.notice,
    )


def validate_bindings(registry: Registry | None = None) -> None:
    """Check every model's bindings against the installed catalog.

    ``registry.validate()`` holds a binding to its structural rules; whether the
    concept exists, is a series, suits the field's unit kind and the as-of rule is
    the catalog's to say, and core never imports it. Each problem is reported as
    ``<model>: [bindings] <detail>``.

    Parameters
    ----------
    registry
        The model registry to check; the installed one by default.

    Raises
    ------
    RegistryError
        Listing every problem.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - loads the models

    lines: list[str] = []
    for model in (registry or installed()).models():
        shapes = field_shapes(model.spec.inputs)
        lines += [
            f"{model.id}: [bindings] {detail}"
            for binding in model.spec.bindings
            for detail in _problems(binding, shapes)
        ]
    if lines:
        noun = "problem" if len(lines) == 1 else "problems"
        detail = "\n".join(f"  {line}" for line in lines)
        msg = f"the model bindings have {len(lines)} {noun}:\n{detail}"
        raise RegistryError(msg, problems=lines)


def _problems(
    binding: Binding, shapes: Mapping[str, tuple[FieldShape, ...]]
) -> list[str]:
    """Return what is wrong with one binding, judged against the catalog."""
    where = f"binding {binding.field!r} (profile {binding.profile!r})"
    if binding.concept not in catalog.CONCEPTS:
        close = _closest(binding.concept)
        hint = f"; did you mean {close!r}?" if close else ""
        return [f"{where}: the catalog has no concept {binding.concept!r}{hint}"]
    concept = catalog.get(binding.concept)
    problems: list[str] = []
    if concept.shape is not Shape.SERIES:
        problems.append(f"{where}: {concept.id} is a table; a binding reads a series")
    if (
        binding.as_of is AsOf.PERIOD
        and concept.frequency is ObservationFrequency.IRREGULAR
    ):
        problems.append(f"{where}: {concept.id} is irregular and has no periods")
    found = shapes.get(binding.field)
    if found and binding.transform is None:
        kind = found[0].kind
        if not _kinds_fit(concept.unit_kind, kind):
            problems.append(
                f"{where}: {concept.id} is {concept.unit_kind}, but the field is {kind}"
            )
    return problems


def _kinds_fit(concept_kind: UnitKind | None, field_kind: UnitKind | None) -> bool:
    if concept_kind is None or field_kind is None or concept_kind == field_kind:
        return True
    return concept_kind in _DIMENSIONLESS and field_kind in _DIMENSIONLESS


def _closest(concept_id: str) -> str | None:
    """Return the closest catalog concept id, if one is near."""
    matches = difflib.get_close_matches(concept_id, catalog.ids(), n=1)
    return matches[0] if matches else None
