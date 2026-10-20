# src/pyeconomics/core/_rules.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The rules ``registry.validate()`` holds every model to.

Each rule has a slug, and each problem a rule reports names the model and the
slug, so a failure says what to fix. The rules encode ROADMAP section 5's
"Model quality and governance" table (identity, citations, units and bounds,
examples, invariants), ADR-0003 (permanent ids) and ADR-0008 (units, bounds and
lengths on every field).

A field is checked by walking its type annotation, not the JSON Schema, so dates
and nested models are held to the same rules as numbers. Everything here is
private; the public surface is ``pyeconomics.registry.validate``.
"""

from __future__ import annotations

import datetime as dt
import math
import re
import types
from collections.abc import Mapping, Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Final,
    Literal,
    TypeAliasType,
    Union,
    cast,
    get_args,
    get_origin,
)

from annotated_types import Ge, Gt, Le, Lt
from pydantic import (
    AllowInfNan,
    BaseModel,
    InstanceOf,
    PlainValidator,
    SkipValidation,
    WrapValidator,
)

from pyeconomics.core._annotations import flatten, max_length
from pyeconomics.core.binding import (
    DEFAULT_PROFILE,
    AsOf,
    Binding,
    FieldShape,
    VintagePolicy,
    field_shapes,
)
from pyeconomics.core.context import collect_warnings
from pyeconomics.core.errors import InputError, MissingOptionalDependencyError
from pyeconomics.core.model import ModelInputs, ModelOutputs
from pyeconomics.core.provenance import CONCEPT_ID_PATTERN
from pyeconomics.core.spec import (
    CALCULATION_FIELD,
    DOMAINS,
    MAX_SUMMARY_LENGTH,
    MAX_TEXT_LENGTH,
    MAX_TITLE_LENGTH,
    MODEL_ID,
    SNAKE_CASE,
    ChartKind,
    CostClass,
    Evidence,
    union_discriminator,
)
from pyeconomics.core.transforms import MAX_TRANSFORM_PERIODS, parse_transform
from pyeconomics.core.units import Unit, UnitKind

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable

    from pyeconomics.core._released import Released
    from pyeconomics.core.model import Model
    from pyeconomics.core.registry import Provider
    from pyeconomics.core.spec import Example, ModelSpec

__all__ = ["RULES", "Problem", "check_model", "check_released"]

#: Every rule slug ``validate()`` can report. Tests hold each to a toy spec.
RULES: Final = (
    "id-format",
    "domain",
    "no-cfa",
    "version",
    "changelog",
    "title",
    "summary",
    "tags",
    "formula",
    "assumptions",
    "limitations",
    "references",
    "reference",
    "extra",
    "evidence",
    "cost",
    "io-types",
    "calculation",
    "field-type",
    "field-unit",
    "field-bounds",
    "field-description",
    "field-length",
    "examples",
    "example-calculations",
    "invariants",
    "charts",
    "aliases",
    "bindings",
    "released",
    "duplicate-id",
    "spec",
)

_DOI = re.compile(r"10\.\d{4,9}/\S+")
_URL = re.compile(r"https?://[^\s/]+\S*")
_ISBN = re.compile(r"(?:\d{9}[\dXx]|\d{13})")
_TAG = re.compile(r"[a-z0-9][a-z0-9 -]*")
_ALIAS_REMOVAL = re.compile(r"(?:[2-9]|[1-9]\d+)\.0\.0")
_VERSION = re.compile(r"\d+(?:\.\d+)*(?:(?:a|b|rc)\d+)?")
_MAX_TAG_LENGTH = 40
_MAX_TAGS = 10
_UNIONS: Final = (Union, types.UnionType)
#: Pydantic metadata that replaces or skips a field's own validation.
_BYPASS: Final = cast(
    "tuple[type, ...]", (PlainValidator, SkipValidation, WrapValidator, InstanceOf)
)


@dataclass(frozen=True, slots=True)
class Problem:
    """One thing wrong with a model, naming the model and the rule."""

    model: str
    rule: str
    detail: str

    def __str__(self) -> str:
        """Render as ``<model>: [<rule>] <detail>``."""
        return f"{self.model}: [{self.rule}] {self.detail}"


class _Report:
    """The problems found for one model."""

    def __init__(self, model_id: str) -> None:
        self.model_id = model_id
        self.problems: list[Problem] = []

    def add(self, rule: str, detail: str) -> None:
        self.problems.append(Problem(self.model_id, rule, detail))


# --- walking a field's type ------------------------------------------------


def _bounds(metadata: Sequence[object]) -> tuple[Any, Any]:
    """Return the tightest lower and upper bound in the metadata, or ``None``."""
    lows: list[Any] = [m.ge for m in metadata if isinstance(m, Ge)]
    lows += [m.gt for m in metadata if isinstance(m, Gt)]
    highs: list[Any] = [m.le for m in metadata if isinstance(m, Le)]
    highs += [m.lt for m in metadata if isinstance(m, Lt)]
    return (max(lows) if lows else None, min(highs) if highs else None)


def _finite_number(value: object) -> bool:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _is_str(value: object) -> bool:
    return isinstance(value, str)


def _is_a(value: object, kind: type) -> bool:
    """Say whether a value is of a class, for a declaration nothing has checked."""
    return isinstance(value, kind)


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_model_class(tp: object) -> bool:
    return isinstance(tp, type) and issubclass(tp, BaseModel)


@dataclass(frozen=True, slots=True)
class _Site:
    """Where a type sits: the report, the path and the models already entered."""

    report: _Report
    path: str
    seen: frozenset[type] = frozenset()

    def under(self, suffix: str) -> _Site:
        return _Site(self.report, f"{self.path}{suffix}", self.seen)


def _check_bounds(metadata: Sequence[object], site: _Site, *, dates: bool) -> None:
    low, high = _bounds(metadata)
    if dates:
        valid = isinstance(low, dt.date) and isinstance(high, dt.date)
    else:
        valid = _finite_number(low) and _finite_number(high)
    if not valid:
        what = "date" if dates else "finite numeric"
        site.report.add("field-bounds", f"{site.path} needs {what} lower/upper bounds")
    elif low >= high:
        site.report.add(
            "field-bounds", f"{site.path}: the lower bound {low} is not below {high}"
        )


def _check_numeric(tp: object, metadata: Sequence[object], site: _Site) -> None:
    if get_origin(tp) is Literal:
        tp = int if all(type(value) is int for value in get_args(tp)) else float
    units = [m for m in metadata if isinstance(m, Unit)]
    if not units:
        site.report.add(
            "field-unit", f"{site.path} has no unit marker (ADR-0008 decision 2)"
        )
    else:
        kind = units[-1].kind
        whole = kind in {UnitKind.DAYS, UnitKind.COUNT}
        if kind is UnitKind.DATE or whole != (tp is int):
            expected = "an int" if whole else "a float"
            site.report.add(
                "field-unit", f"{site.path}: unit '{kind.value}' needs {expected}"
            )
    finite = [m for m in metadata if isinstance(m, AllowInfNan)]
    if finite and finite[-1].allow_inf_nan:
        site.report.add("field-bounds", f"{site.path} allows NaN and infinity")
    _check_bounds(metadata, site, dates=False)


def _check_date(tp: object, metadata: Sequence[object], site: _Site) -> None:
    if tp is dt.datetime:
        site.report.add("field-type", f"{site.path}: use a date, not a datetime")
        return
    units = [m for m in metadata if isinstance(m, Unit)]
    if not units or units[-1].kind is not UnitKind.DATE:
        site.report.add("field-unit", f"{site.path} has no 'date' unit marker")
    _check_bounds(metadata, site, dates=True)


def _check_string(_tp: object, metadata: Sequence[object], site: _Site) -> None:
    if max_length(metadata) is None:
        site.report.add(
            "field-length", f"{site.path} is a string with no maximum length"
        )


def _check_tuple(tp: object, metadata: Sequence[object], site: _Site) -> None:
    args = get_args(tp)
    if not args:
        site.report.add("field-type", f"{site.path} is a tuple with no item type")
    elif len(args) == 2 and args[1] is Ellipsis:  # noqa: PLR2004 - tuple[X, ...]
        if max_length(metadata) is None:
            site.report.add(
                "field-length", f"{site.path} is an array with no maximum length"
            )
        _walk(args[0], [], site.under("[]"))
    else:
        for position, item in enumerate(args):
            _walk(item, [], site.under(f"[{position}]"))


def _check_mapping(tp: object, metadata: Sequence[object], site: _Site) -> None:
    args = get_args(tp)
    if len(args) != 2:  # noqa: PLR2004 - key and value
        site.report.add("field-type", f"{site.path} is an unconstrained dict")
        return
    if max_length(metadata) is None:
        site.report.add("field-length", f"{site.path} is a dict with no maximum length")
    _walk(args[0], [], site.under("{key}"))
    _walk(args[1], [], site.under("{value}"))


def _check_mutable(tp: object, _metadata: Sequence[object], site: _Site) -> None:
    site.report.add(
        "field-type", f"{site.path}: use a tuple, which is immutable, not {tp}"
    )


def _check_loose(tp: object, _metadata: Sequence[object], site: _Site) -> None:
    site.report.add(
        "field-type", f"{site.path} is typed {tp}; use a concrete, bounded type"
    )


def _check_nested(tp: object, _metadata: Sequence[object], site: _Site) -> None:
    cls: Any = tp
    if not issubclass(cls, ModelInputs | ModelOutputs):
        site.report.add(
            "field-type",
            f"{site.path}: nested model {cls.__name__} must derive from "
            "ModelInputs or ModelOutputs",
        )
    elif cls in site.seen:
        site.report.add(
            "field-type", f"{site.path}: model {cls.__name__} contains itself"
        )
    else:
        _check_fields(cls, _Site(site.report, site.path, site.seen | {cls}))


def _check_unsupported(tp: object, _metadata: Sequence[object], site: _Site) -> None:
    site.report.add("field-type", f"{site.path} has the unsupported type {tp}")


def _classify(tp: object, origin: object) -> str:
    """Name the kind of type ``tp`` is, for dispatch."""
    if origin is Literal and all(type(value) in {int, float} for value in get_args(tp)):
        return "numeric"
    for kind, hit in (
        ("loose", tp is Any or tp is object),
        ("scalar", tp is bool or origin is Literal),
        ("scalar", isinstance(tp, type) and issubclass(tp, Enum)),
        ("numeric", tp is int or tp is float),
        ("string", tp is str),
        ("date", tp is dt.date or tp is dt.datetime),
        ("tuple", tp is tuple or origin is tuple),
        ("mapping", tp is dict or origin in {dict, Mapping}),
        (
            "mutable",
            tp in (list, set, frozenset)
            or origin in {list, set, frozenset, Sequence, AbstractSet},
        ),
        ("nested", _is_model_class(tp)),
    ):
        if hit:
            return kind
    return "unsupported"


_DISPATCH: Final[Mapping[str, Callable[[object, Sequence[object], _Site], None]]] = {
    "loose": _check_loose,
    "scalar": lambda *_: None,
    "numeric": _check_numeric,
    "string": _check_string,
    "date": _check_date,
    "tuple": _check_tuple,
    "mapping": _check_mapping,
    "mutable": _check_mutable,
    "nested": _check_nested,
    "unsupported": _check_unsupported,
}


def _report_bypass(items: Iterable[object], site: _Site) -> None:
    """Report metadata that could skip the field's bounds."""
    for item in items:
        if isinstance(item, _BYPASS) or item is SkipValidation:
            name = getattr(item, "__name__", type(item).__name__)
            site.report.add(
                "field-type", f"{site.path} uses {name}, which can skip its bounds"
            )


def _walk(tp: object, metadata: Sequence[object], site: _Site) -> None:
    """Check one type annotation, with the metadata that applies to it."""
    while get_origin(tp) is Annotated or isinstance(tp, TypeAliasType):
        if isinstance(tp, TypeAliasType):  # type X = Annotated[...]
            tp = tp.__value__
            continue
        args = get_args(tp)
        tp = args[0]
        added = flatten(args[1:])
        _report_bypass(added, site)
        metadata = [*metadata, *added]
    origin = get_origin(tp)
    if origin in _UNIONS:
        for member in get_args(tp):
            if member is not type(None):
                _walk(member, metadata, site)
        return
    _DISPATCH[_classify(tp, origin)](tp, metadata, site)


def _check_fields(cls: type[BaseModel], site: _Site) -> None:
    """Check every field of one input or output model."""
    _check_config(cls, site)
    for name, info in cls.model_fields.items():
        field_site = site.under(f".{name}" if site.path else name)
        if not (info.description and info.description.strip()):
            site.report.add(
                "field-description", f"{field_site.path} has no description"
            )
        metadata = flatten(info.metadata)
        _report_bypass(metadata, field_site)
        _walk(info.annotation, metadata, field_site)


_CONFIG_PINS: Final = {
    "frozen": True,
    "extra": "forbid",
    "revalidate_instances": "always",
    "allow_inf_nan": False,
}


def _check_config(cls: type[BaseModel], site: _Site) -> None:
    """Hold a model to the closed, finite, re-validated configuration."""
    if any(cls.model_config.get(key) != value for key, value in _CONFIG_PINS.items()):
        site.report.add(
            "io-types",
            f"{cls.__name__} must be frozen, forbid extra fields, re-validate "
            "instances and reject NaN and infinity",
        )
    for name in cls.model_computed_fields:
        site.report.add(
            "field-type",
            f"{site.path or cls.__name__}.{name} is a computed field, which is not "
            "validated; compute the value in compute and declare it as a field",
        )
    decorators = cls.__pydantic_decorators__
    for validator in decorators.field_validators.values():
        if validator.info.mode in {"plain", "wrap"}:
            site.report.add(
                "field-type",
                f"{cls.__name__}.{validator.cls_var_name} is a {validator.info.mode} "
                "validator, which can skip a field's bounds",
            )
    for model_validator in decorators.model_validators.values():
        if model_validator.info.mode == "wrap":
            site.report.add(
                "field-type",
                f"{cls.__name__}.{model_validator.cls_var_name} is a wrap "
                "validator, which can skip the bounds",
            )


# --- the rules ---------------------------------------------------------------


class _Checker:
    """Run every static rule against one model's specification."""

    def __init__(self, spec: ModelSpec, provider: Provider | None) -> None:
        self.spec = spec
        self.provider = provider
        self.report = _Report(spec.id)
        self.types_ok = True
        """False when the input or output types are not model classes at all."""

    def run(self) -> list[Problem]:
        self.identity()
        self.changelog()
        self.prose()
        self.references()
        self.extra()
        self.io_types()
        self.invariants()
        self.charts()
        self.aliases()
        self.bindings()
        return self.report.problems

    def text(self, value: object, rule: str, what: str, limit: int) -> None:
        if not isinstance(value, str) or not value.strip():
            self.report.add(rule, f"{what} is empty")
        elif len(value) > limit:
            self.report.add(rule, f"{what} is {len(value)} characters; limit {limit}")

    def texts(self, items: Sequence[object], rule: str, what: str) -> None:
        if not items:
            self.report.add(rule, f"declares no {what}")
        for position, item in enumerate(items, start=1):
            self.text(item, rule, f"{what} {position}", MAX_TEXT_LENGTH)

    def identity(self) -> None:
        spec = self.spec
        if not _is_str(spec.id) or not MODEL_ID.fullmatch(spec.id):
            self.report.add(
                "id-format",
                f"id {spec.id!r} is not <domain>.<name> in snake_case "
                "(at most three segments)",
            )
        elif spec.domain not in DOMAINS:
            self.report.add(
                "domain",
                f"domain {spec.domain!r} is not one of the fifteen domains "
                f"({', '.join(DOMAINS)})",
            )
        if "cfa" in str(spec.id).lower():
            self.report.add("no-cfa", f"id {spec.id!r} contains 'cfa' (ADR-0009)")
        if not _is_int(spec.version):
            self.report.add("version", f"version {spec.version!r} is not an integer")
        elif spec.version < 1:
            self.report.add("version", f"version {spec.version} is below 1")

    def changelog(self) -> None:
        spec = self.spec
        versions = [entry.version for entry in spec.changelog]
        if _is_int(spec.version) and spec.version not in versions:
            self.report.add(
                "changelog", f"the changelog has no entry for version {spec.version}"
            )
        if len(set(versions)) != len(versions):
            self.report.add("changelog", "the changelog repeats a version")
        for entry in spec.changelog:
            if not _is_int(entry.version) or entry.version < 1:
                self.report.add(
                    "changelog", f"entry version {entry.version!r} is below 1"
                )
            self.text(
                entry.note,
                "changelog",
                f"the note for version {entry.version}",
                MAX_TEXT_LENGTH,
            )

    def prose(self) -> None:
        spec = self.spec
        self.text(spec.title, "title", "the title", MAX_TITLE_LENGTH)
        self.text(spec.summary, "summary", "the summary", MAX_SUMMARY_LENGTH)
        self.texts(spec.formula, "formula", "formula")
        self.texts(spec.assumptions, "assumptions", "assumption")
        self.texts(spec.limitations, "limitations", "limitation")
        if len(spec.tags) > _MAX_TAGS or len(set(spec.tags)) != len(spec.tags):
            self.report.add("tags", f"at most {_MAX_TAGS} distinct tags are allowed")
        for tag in spec.tags:
            if (
                not _is_str(tag)
                or len(tag) > _MAX_TAG_LENGTH
                or not _TAG.fullmatch(tag)
            ):
                self.report.add(
                    "tags",
                    f"tag {tag!r} is not lowercase words of at most "
                    f"{_MAX_TAG_LENGTH} characters",
                )

    def references(self) -> None:
        if not self.spec.references:
            self.report.add("references", "declares no reference")
        keys: set[str] = set()
        for reference in self.spec.references:
            label = f"reference {reference.key!r}"
            if not _is_str(reference.key) or not reference.key or reference.key in keys:
                self.report.add("reference", f"{label}: the key is empty or repeated")
            keys.add(str(reference.key))
            self.text(
                reference.citation,
                "reference",
                f"{label}: the citation",
                MAX_TEXT_LENGTH,
            )
            self.reference_target(reference.doi, reference.url, label)
            locator = reference.locator
            if not _is_str(locator) or not str(locator).strip():
                self.report.add(
                    "reference", f"{label} has no locator (page, table, section, ...)"
                )
            self.reference_isbn(reference.isbn, label)

    def reference_isbn(self, isbn: object, label: str) -> None:
        if isbn is not None and (
            not _is_str(isbn)
            or not _ISBN.fullmatch(str(isbn).replace("-", "").replace(" ", ""))
        ):
            self.report.add("reference", f"{label}: isbn {isbn!r} is invalid")

    def reference_target(self, doi: object, url: object, label: str) -> None:
        if not doi and not url:
            self.report.add("reference", f"{label} has neither a doi nor a url")
        if doi and not (_is_str(doi) and _DOI.fullmatch(str(doi))):
            self.report.add("reference", f"{label}: doi {doi!r} is not a DOI")
        if url and not (_is_str(url) and _URL.fullmatch(str(url))):
            self.report.add("reference", f"{label}: url {url!r} is not an http(s) URL")

    def extra(self) -> None:
        spec = self.spec
        if spec.extra is not None and (
            self.provider is None or not self.provider.declares(spec.extra)
        ):
            owner = self.provider.name if self.provider else "its distribution"
            self.report.add(
                "extra",
                f"extra {spec.extra!r} is not declared by {owner} (Provides-Extra)",
            )
        if not isinstance(spec.evidence, Evidence):
            self.report.add("evidence", "no evidence status is set")
        if not isinstance(spec.cost, CostClass):
            self.report.add("cost", "no cost class is set")

    def io_types(self) -> None:
        spec = self.spec
        sides: tuple[tuple[str, Sequence[Any], type[BaseModel]], ...] = (
            ("inputs", spec.input_models, ModelInputs),
            ("outputs", spec.output_models, ModelOutputs),
        )
        wrong = False
        for side, members, base in sides:
            for member in members:
                if not (isinstance(member, type) and issubclass(member, base)):
                    wrong = True
                    self.report.add(
                        "io-types", f"{side} {member!r} is not a {base.__name__}"
                    )
        if wrong:
            self.types_ok = False
            return
        self.calculations()
        for side, members, _ in sides:
            for member in cast("Sequence[type[BaseModel]]", members):
                scoped = _Report(spec.id)
                _check_fields(member, _Site(scoped, "", frozenset({member})))
                for problem in scoped.problems:
                    self.report.add(problem.rule, f"{side}: {problem.detail}")

    def calculations(self) -> None:
        """Hold a union of calculations to the ``calculation`` rules."""
        spec = self.spec
        unions = (len(spec.input_models) > 1, len(spec.output_models) > 1)
        if unions[0] != unions[1]:
            self.report.add(
                "calculation",
                "inputs and outputs must both be one model or both a union "
                f"discriminated on '{CALCULATION_FIELD}'",
            )
            return
        if not unions[0]:
            return
        for side, annotation in (("inputs", spec.inputs), ("outputs", spec.outputs)):
            if union_discriminator(annotation) != CALCULATION_FIELD:
                self.report.add(
                    "calculation",
                    f"{side} are a union not discriminated on "
                    f"'{CALCULATION_FIELD}' (use Field(discriminator=...))",
                )
        in_calcs = _member_calculations(spec.input_models, "inputs", self.report)
        out_calcs = _member_calculations(spec.output_models, "outputs", self.report)
        if (
            in_calcs is not None
            and out_calcs is not None
            and set(in_calcs) != set(out_calcs)
        ):
            self.report.add(
                "calculation",
                f"input calculations {sorted(in_calcs)} differ from "
                f"output calculations {sorted(out_calcs)}",
            )

    def invariants(self) -> None:
        spec = self.spec
        ids = [invariant.id for invariant in spec.invariants]
        if len(set(ids)) != len(ids):
            self.report.add("invariants", "invariant ids are not unique")
        for invariant in spec.invariants:
            if not SNAKE_CASE.fullmatch(str(invariant.id)):
                self.report.add(
                    "invariants", f"invariant id {invariant.id!r} is not snake_case"
                )
            self.text(
                invariant.statement,
                "invariants",
                f"the statement of {invariant.id!r}",
                MAX_TEXT_LENGTH,
            )
        reason = spec.no_invariants_reason
        if not spec.invariants and not (reason and reason.strip()):
            self.report.add(
                "invariants", "declares no invariant and records no reason why not"
            )

    def charts(self) -> None:
        spec = self.spec
        ids = [chart.id for chart in spec.charts]
        if len(set(ids)) != len(ids):
            self.report.add("charts", "chart ids are not unique")
        outputs: list[Any] = [m for m in spec.output_models if _is_model_class(m)]
        for chart in spec.charts:
            if not SNAKE_CASE.fullmatch(str(chart.id)):
                self.report.add("charts", f"chart id {chart.id!r} is not snake_case")
            members: list[Any] = [
                m
                for m in outputs
                if chart.calculation is None or _calculation_of(m) == chart.calculation
            ]
            if not chart.y or not members:
                self.report.add(
                    "charts",
                    f"chart {chart.id!r} needs y fields and a known calculation",
                )
            if chart.kind is ChartKind.BAND and len(chart.y) < 2:  # noqa: PLR2004
                self.report.add(
                    "charts",
                    f"chart {chart.id!r} is a band: its first two y fields are the "
                    "lower and upper edges",
                )
            for name in dict.fromkeys((chart.x, *chart.y)):
                if not all(_is_array_field(m, name) for m in members):
                    self.report.add(
                        "charts", f"chart {chart.id!r}: {name!r} is not an array output"
                    )

    def aliases(self) -> None:
        spec = self.spec
        for alias in spec.aliases:
            if not MODEL_ID.fullmatch(str(alias.id)):
                self.report.add(
                    "aliases", f"alias {alias.id!r} is not a valid model id"
                )
            if "cfa" in str(alias.id).lower():
                self.report.add(
                    "no-cfa", f"alias {alias.id!r} contains 'cfa' (ADR-0009)"
                )
            if alias.id == spec.id:
                self.report.add("aliases", f"alias {alias.id!r} is the model's own id")
            if not _ALIAS_REMOVAL.fullmatch(str(alias.removed_in)):
                self.report.add(
                    "aliases",
                    f"alias {alias.id!r} is removed in {alias.removed_in!r}, which "
                    "is not a major release after 1.0 (ADR-0003)",
                )

    def bindings(self) -> None:
        """Hold the data bindings to their structural rules (ADR-0011 decision 16).

        Whether a concept exists in the installed catalog is the data layer's to
        check (``pyeconomics.data.validate_bindings``): core never imports it.
        """
        spec = self.spec
        if not spec.bindings:
            return
        shapes = field_shapes(spec.inputs) if self.types_ok else None
        bound: set[tuple[object, object]] = set()
        profiles: set[object] = set()
        declared: tuple[object, ...] = spec.bindings  # nothing checked it yet
        for position, binding in enumerate(declared, start=1):
            if not isinstance(binding, Binding):
                self.report.add("bindings", f"binding {position} is not a Binding")
                continue
            profiles.add(binding.profile)
            where = f"binding {binding.field!r} (profile {binding.profile!r})"
            filled = [binding.field]
            if isinstance(binding.tenors, str):
                filled.append(binding.tenors)
            for name in filled:
                if (binding.profile, name) in bound:
                    self.report.add(
                        "bindings",
                        f"binding {name!r} (profile {binding.profile!r}) binds the "
                        "field twice",
                    )
                bound.add((binding.profile, name))
            self.binding(binding, where, shapes)
        if DEFAULT_PROFILE not in profiles:
            self.report.add(
                "bindings", f"declares bindings but no '{DEFAULT_PROFILE}' profile"
            )

    def binding(
        self,
        binding: Binding,
        where: str,
        shapes: dict[str, tuple[FieldShape, ...]] | None,
    ) -> None:
        add = self.report.add
        if not _is_str(binding.field) or not SNAKE_CASE.fullmatch(binding.field):
            add("bindings", f"{where}: the field name is not snake_case")
        if not _is_str(binding.profile) or not SNAKE_CASE.fullmatch(binding.profile):
            add("bindings", f"{where}: the profile name is not snake_case")
        if not _is_str(binding.concept) or not CONCEPT_ID_PATTERN.fullmatch(
            binding.concept
        ):
            add(
                "bindings",
                f"{where}: concept {binding.concept!r} is not a concept id "
                "(dotted snake_case of three or four parts, ADR-0011 decision 15)",
            )
        self.binding_transform(binding, where)
        rule_ok = _is_a(binding.as_of, AsOf)
        if not rule_ok:
            add("bindings", f"{where}: as_of {binding.as_of!r} is not an AsOf rule")
        if not _is_a(binding.vintage, VintagePolicy):
            add(
                "bindings",
                f"{where}: vintage {binding.vintage!r} is not a VintagePolicy",
            )
        window = binding.window
        window_ok = (
            isinstance(window, int)
            and not isinstance(window, bool)
            and 1 <= window <= MAX_TRANSFORM_PERIODS
        )
        if rule_ok and (binding.as_of is AsOf.WINDOW) != (window is not None):
            add(
                "bindings",
                f"{where}: a window goes with the '{AsOf.WINDOW.value}' rule, and only "
                "with that rule",
            )
        elif window is not None and not window_ok:
            add(
                "bindings",
                f"{where}: window {window!r} is not a whole number from 1 to "
                f"{MAX_TRANSFORM_PERIODS}",
            )
        self.binding_curve(binding, where, rule_ok=rule_ok)
        if shapes is not None and _is_str(binding.field):
            self.binding_field(binding, where, shapes, window if window_ok else None)

    def binding_curve(self, binding: Binding, where: str, *, rule_ok: bool) -> None:
        """Hold a curve's binding (one with ``tenors``) to its rules."""
        tenors = binding.tenors
        if tenors is None:
            return
        add = self.report.add
        if not _is_str(tenors) or not SNAKE_CASE.fullmatch(tenors):
            add("bindings", f"{where}: the tenors field name is not snake_case")
        elif tenors == binding.field:
            add("bindings", f"{where}: the tenors go to another field than the values")
        if rule_ok and binding.as_of is not AsOf.LAST_ON_OR_BEFORE:
            add(
                "bindings",
                f"{where}: a curve is read at its last observation on or before the "
                f"date (the '{AsOf.LAST_ON_OR_BEFORE.value}' rule)",
            )
        if binding.transform is not None:
            add("bindings", f"{where}: a curve's binding takes no transform")

    def binding_transform(self, binding: Binding, where: str) -> None:
        if binding.transform is None:
            return
        try:
            parsed = parse_transform(binding.transform)
        except InputError as error:
            self.report.add("bindings", f"{where}: {_first_line(error)}")
            return
        if parsed.spec.operands != 1:
            self.report.add(
                "bindings",
                f"{where}: transform '{parsed.name}' reads two series; a binding's "
                "transform reads the one series its concept resolves to",
            )
        elif parsed.spec.group == "alignment":
            self.report.add(
                "bindings",
                f"{where}: transform '{parsed.name}' picks observations at a date; "
                "choose that with as_of and window",
            )

    def binding_field(
        self,
        binding: Binding,
        where: str,
        shapes: dict[str, tuple[FieldShape, ...]],
        window: int | None,
    ) -> None:
        found = shapes.get(binding.field)
        if not found:
            known = ", ".join(sorted(shapes))
            self.report.add(
                "bindings", f"{where}: not an input field (the fields are {known})"
            )
            return
        if {shape.array for shape in found} == {True, False}:
            self.report.add(
                "bindings",
                f"{where}: the field is an array in one calculation and a scalar "
                "in another",
            )
            return
        shape = found[0]
        if shape.kind is None or shape.kind is UnitKind.DATE:
            self.report.add(
                "bindings", f"{where}: only a numeric field can be bound to data"
            )
        if binding.tenors is not None:
            self.binding_tenors(binding, where, shapes, array=shape.array)
        elif shape.array and binding.as_of is not AsOf.WINDOW:
            self.report.add(
                "bindings",
                f"{where}: an array field needs the '{AsOf.WINDOW.value}' rule and "
                "a window, or a curve's tenors",
            )
        elif not shape.array and binding.as_of is AsOf.WINDOW:
            self.report.add("bindings", f"{where}: a scalar field cannot take a window")
        longest = min(
            (s.max_length for s in found if s.max_length is not None), default=None
        )
        if window is not None and longest is not None and window > longest:
            self.report.add(
                "bindings",
                f"{where}: the window of {window} exceeds the field's maximum "
                f"length of {longest}",
            )

    def binding_tenors(
        self,
        binding: Binding,
        where: str,
        shapes: dict[str, tuple[FieldShape, ...]],
        *,
        array: bool,
    ) -> None:
        """Hold a curve to its two array fields: the values and their tenors."""
        if not array:
            self.report.add(
                "bindings", f"{where}: a curve's values go to an array field"
            )
        tenors = binding.tenors
        if not isinstance(tenors, str):
            return
        found = shapes.get(tenors)
        if not found:
            self.report.add(
                "bindings",
                f"{where}: the tenors field {binding.tenors!r} is not an input field",
            )
            return
        if not all(s.array and s.kind is UnitKind.YEARS for s in found):
            self.report.add(
                "bindings",
                f"{where}: the tenors field {binding.tenors!r} must be an array of "
                "years",
            )


def _member_calculations(
    members: Sequence[Any], side: str, report: _Report
) -> dict[str, type] | None:
    """Map each member's ``calculation`` literal to it; ``None`` if any is bad."""
    calculations: dict[str, type] = {}
    clean = True
    for member in members:
        value = _calculation_of(member)
        if value is None:
            clean = False
            report.add(
                "calculation",
                f"{side} member {member.__name__} needs a '{CALCULATION_FIELD}' "
                "field typed Literal['<snake_case>']",
            )
        elif value in calculations:
            clean = False
            report.add("calculation", f"{side} repeat the calculation {value!r}")
        else:
            calculations[value] = member
    return calculations if clean else None


def _calculation_of(member: type[BaseModel]) -> str | None:
    """Return a union member's ``calculation`` literal, if it is well formed."""
    info = member.model_fields.get(CALCULATION_FIELD)
    if info is None or get_origin(info.annotation) is not Literal:
        return None
    values = get_args(info.annotation)
    if (
        len(values) == 1
        and isinstance(values[0], str)
        and SNAKE_CASE.fullmatch(values[0])
    ):
        return values[0]
    return None


def _strip(annotation: object) -> object:
    """Remove ``Annotated`` wrappers."""
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]
    return annotation


def _is_array_field(member: type[BaseModel], name: str) -> bool:
    info = member.model_fields.get(name)
    if info is None:
        return False
    annotation = _strip(info.annotation)
    candidates = (
        get_args(annotation) if get_origin(annotation) in _UNIONS else (annotation,)
    )
    return any(get_origin(_strip(c)) is tuple for c in candidates)


# --- examples ----------------------------------------------------------------


def _first_line(error: Exception) -> str:
    """Return an error's first line: what is wrong, without the rest."""
    return (str(error).splitlines() or [type(error).__name__])[0]


def _first_error(error: InputError) -> str:
    """Summarise the first of pydantic's errors: where, and what."""
    first = error.errors[0]
    where = ".".join(str(part) for part in first["loc"]) or "inputs"
    return f"{where}: {first['msg']}"


def _missing_extra_problem(
    error: MissingOptionalDependencyError, extra: str | None, *, extra_missing: bool
) -> str | None:
    """Judge a ``MissingOptionalDependencyError`` an example raised."""
    if not extra_missing:
        return f"needs a package that is not installed: {error}"
    if error.extra != extra:
        return f"raised an error naming extra {error.extra!r}, not {extra!r}"
    return None


def _run_example(
    model: Model[Any, Any], inputs: object, *, extra_missing: bool
) -> str | None:
    """Run one validated example; return what is wrong, or ``None``."""
    extra = model.spec.extra
    try:
        with collect_warnings():
            outputs = model.validate_outputs(model.compute(inputs))
    except MissingOptionalDependencyError as error:
        return _missing_extra_problem(error, extra, extra_missing=extra_missing)
    except Exception as error:  # noqa: BLE001 - any failure of compute is a finding
        return f"failed to run: {type(error).__name__}: {error}"
    if extra_missing:
        return (
            f"ran although the extra {extra!r} is not installed; it must raise "
            "MissingOptionalDependencyError naming the extra"
        )
    if getattr(inputs, CALCULATION_FIELD, None) != getattr(
        outputs, CALCULATION_FIELD, None
    ):
        return "the output calculation differs from the input calculation"
    return None


def _check_example(
    model: Model[Any, Any], example: Example, report: _Report, *, extra_missing: bool
) -> None:
    """Hold one example to its rules: a name, valid inputs, a clean run."""
    label = f"example {example.name!r}"
    if not SNAKE_CASE.fullmatch(str(example.name)):
        report.add("examples", f"{label}: the name is not snake_case")
    try:
        inputs = model.validate_inputs(example.inputs)
    except InputError as error:
        report.add("examples", f"{label} does not validate: {_first_error(error)}")
        return
    problem = _run_example(model, inputs, extra_missing=extra_missing)
    if problem is not None:
        report.add("examples", f"{label} {problem}")


def _check_examples(
    model: Model[Any, Any], provider: Provider | None, report: _Report
) -> None:
    """Run every example: it must validate and run, with outputs in bounds."""
    spec = model.spec
    if not spec.examples:
        report.add("examples", "declares no example")
        return
    try:
        _ = model.input_adapter, model.output_adapter
    except Exception as error:  # noqa: BLE001 - pydantic raises several types here
        reason = (str(error).splitlines() or [""])[0]
        report.add(
            "io-types", f"cannot build a validator: {type(error).__name__}: {reason}"
        )
        return
    names = [example.name for example in spec.examples]
    if len(set(names)) != len(names):
        report.add("examples", "example names are not unique")
    extra_missing = (
        spec.extra is not None
        and provider is not None
        and not provider.installed(spec.extra)
    )
    for example in spec.examples:
        _check_example(model, example, report, extra_missing=extra_missing)
    if len(spec.input_models) > 1:
        known = _member_calculations(spec.input_models, "inputs", _Report(spec.id))
        covered = {
            c
            for example in spec.examples
            if _is_str(c := example.inputs.get(CALCULATION_FIELD))
        }
        for name in sorted(set(known or {}) - covered):
            report.add(
                "example-calculations", f"no example runs the calculation {name!r}"
            )


# --- entry points ------------------------------------------------------------


def check_model(model: Model[Any, Any], provider: Provider | None) -> list[Problem]:
    """Return every problem with one model, in a fixed order."""
    checker = _Checker(model.spec, provider)
    try:
        checker.run()
        if checker.types_ok:
            _check_examples(model, provider, checker.report)
    except Exception as error:  # noqa: BLE001 - a malformed spec must not hide the rest
        checker.report.add(
            "spec",
            f"cannot be checked, a value has the wrong type: {type(error).__name__}: "
            f"{error}",
        )
    return checker.report.problems


def check_released(
    released: Mapping[str, Released],
    canonical_ids: AbstractSet[str],
    aliases: Mapping[str, str],
) -> list[Problem]:
    """Check the released-id ledger against the registry (ADR-0003).

    Parameters
    ----------
    released
        The ledger: released id to the canonical id it named and the first
        version that shipped it.
    canonical_ids
        Every canonical id in the registry.
    aliases
        Every alias in the registry, mapped to its canonical id.
    """
    problems: list[Problem] = []

    def resolves(model_id: str) -> bool:
        return model_id in canonical_ids or model_id in aliases

    for released_id in sorted(released):
        entry = released[released_id]
        detail: str | None = None
        if not MODEL_ID.fullmatch(entry.canonical_id) or not _VERSION.fullmatch(
            entry.first_version
        ):
            detail = "the ledger entry is malformed"
        elif not resolves(released_id):
            detail = "no longer resolves; a released id is never deleted (ADR-0003)"
        elif entry.canonical_id != released_id and released_id in canonical_ids:
            detail = (
                f"shipped as an alias of {entry.canonical_id!r} and is now a model "
                "id; a released id is never reused (ADR-0003)"
            )
        elif not resolves(entry.canonical_id):
            detail = f"the model it named, {entry.canonical_id!r}, no longer resolves"
        elif aliases.get(released_id, released_id) != aliases.get(
            entry.canonical_id, entry.canonical_id
        ):
            detail = (
                f"now resolves to {aliases.get(released_id, released_id)!r}, but it "
                f"named {entry.canonical_id!r}, which is now "
                f"{aliases.get(entry.canonical_id, entry.canonical_id)!r} "
                "(an alias was retargeted; ADR-0003)"
            )
        if detail is not None:
            problems.append(Problem(released_id, "released", detail))
    return problems
