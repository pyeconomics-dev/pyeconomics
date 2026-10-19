# src/pyeconomics/core/transforms.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The names and parameter schemas of the data transforms (ADR-0011 decision 15).

A catalog concept lists the transforms that make a provider's series match its
definition, and a model's binding (Phase 3 Step 12) may name one more. Both are
written as text and recorded in a :class:`~pyeconomics.core.provenance.DataSource`
as text: ``yoy``, ``pct_change(periods=4)``,
``convert(to=quarterly,method=mean)``. This module is that vocabulary as plain
data with no implementation, so the model registry's validation (Phase 3
Step 12) can check a binding's transform without core importing the data layer.
The implementations live in :mod:`pyeconomics.data.catalog.transforms`, and a
test holds the two sets of names equal in both directions.

The text form is ``name`` or ``name(key=value, ...)``. A value is an integer, a
``true`` or ``false`` flag, an ISO date (``2008-12-16``) or a lowercase word. An
argument equal to the parameter's default is left out of the canonical form, and
the rest follow the order the schema declares, so one transform has one text:
the text goes into a manifest, whose bytes must not depend on how a caller wrote
it.

Every transform is pure, never fills a gap and never invents a date:

- *change* transforms (``pct_change``, ``yoy``, ``diff``, ``lag``, ``log``,
  ``changes_only``) turn a series into another on its own dates;
- ``convert`` changes the observation frequency by an explicit method;
- ``ratio`` and ``add`` combine two series; ``align_to`` reads one series on another's
  dates by the last observation on or before each (an explicit, bounded rule);
- ``asof``, ``period`` and ``window`` pick the observation, the period's value or
  the run of observations a binding reads at a date, and refuse when the data
  cannot supply them.

Examples
--------
>>> from pyeconomics.core.transforms import canonical_transform, parse_transform
>>> canonical_transform("convert(to=quarterly, method=mean)")
'convert(to=quarterly,method=mean)'
>>> parse_transform("pct_change(periods=4)").arguments
{'periods': 4}
>>> canonical_transform("diff(periods=1)")
'diff'
>>> sorted(TRANSFORMS)[:3]
['add', 'align_to', 'asof']
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, Final

from pyeconomics.core import _fields as f
from pyeconomics.core.provenance import DATA_DATE_BOUNDS

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "MAX_TRANSFORM_PERIODS",
    "TRANSFORMS",
    "TRANSFORM_NAMES",
    "ParsedTransform",
    "TransformParameter",
    "TransformParameterKind",
    "TransformSpec",
    "canonical_transform",
    "check_transform",
    "format_transform",
    "parse_transform",
]

#: The most observations a ``periods`` or ``count`` parameter reaches back.
MAX_TRANSFORM_PERIODS: Final = 1_000
#: The longest age, in days, an ``as-of`` rule may reach back (one century).
MAX_AGE_DAYS: Final = 36_500
_MAX_TEXT: Final = 256

_NAME: Final = re.compile(r"[a-z][a-z0-9_]*")
_CALL: Final = re.compile(r"(?P<name>[a-z][a-z0-9_]*)(?:\((?P<arguments>[^()]*)\))?")
_WORD: Final = re.compile(r"[a-z][a-z0-9_]*")
_INTEGER: Final = re.compile(r"-?\d{1,6}")
_DATE: Final = re.compile(r"\d{4}-\d{2}-\d{2}")


class TransformParameterKind(StrEnum):
    """The four kinds of value a transform parameter takes."""

    INTEGER = "integer"
    """A whole number between the parameter's bounds."""
    FLAG = "flag"
    """``true`` or ``false``."""
    DATE = "date"
    """An ISO calendar date inside the data layer's date bounds."""
    CHOICE = "choice"
    """One of a closed set of lowercase words."""


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformParameter:
    """One parameter of a transform: its name, kind, bounds and default.

    A parameter is required unless it has a default. ``None`` is a default only
    for an optional parameter, which is then left out when not given.
    """

    name: str
    kind: TransformParameterKind
    summary: str
    required: bool = False
    default: int | bool | str | None = None
    choices: tuple[str, ...] = ()
    minimum: int = 1
    maximum: int = MAX_TRANSFORM_PERIODS

    def __post_init__(self) -> None:
        """Check the schema itself, so a typo here fails at import."""
        f.identifier(self.name, "parameter name")
        f.text(self.summary, "parameter summary")
        kind = f.choice(TransformParameterKind, self.kind, "parameter kind")
        object.__setattr__(self, "kind", kind)
        if (kind is TransformParameterKind.CHOICE) != bool(self.choices):
            msg = f"parameter {self.name!r}: only a choice lists choices, and it must"
            raise f.fail(msg)
        if self.required and self.default is not None:
            msg = f"parameter {self.name!r} is required, so it has no default"
            raise f.fail(msg)
        if self.default is not None:
            self.check(self.default)

    def check(self, value: object) -> int | bool | str:
        """Return ``value`` if it suits the parameter, else raise ``InputError``."""
        what = f"transform parameter {self.name!r}"
        match self.kind:
            case TransformParameterKind.INTEGER:
                if (
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or not self.minimum <= value <= self.maximum
                ):
                    msg = (
                        f"{what} is a whole number from {self.minimum} to "
                        f"{self.maximum}, not {value!r}"
                    )
                    raise f.fail(msg)
                return value
            case TransformParameterKind.FLAG:
                if not isinstance(value, bool):
                    msg = f"{what} is true or false, not {value!r}"
                    raise f.fail(msg)
                return value
            case TransformParameterKind.DATE:
                text = value.isoformat() if isinstance(value, dt.date) else value
                if not isinstance(text, str) or not _DATE.fullmatch(text):
                    msg = f"{what} is an ISO date such as 2008-12-16, not {value!r}"
                    raise f.fail(msg)
                f.day(f.parse_day(text, what), what, DATA_DATE_BOUNDS)
                return text
            case TransformParameterKind.CHOICE:
                if value not in self.choices:
                    msg = f"{what} is one of {', '.join(self.choices)}, not {value!r}"
                    raise f.fail(msg)
                return str(value)


@dataclass(frozen=True, slots=True, kw_only=True)
class TransformSpec:
    """A transform's name, what it does and the parameters it takes."""

    name: str
    summary: str
    parameters: tuple[TransformParameter, ...] = ()
    operands: int = 1
    """How many series it reads: 1, or 2 for ``ratio`` and ``align_to``."""
    group: str = "change"
    """``change``, ``frequency``, ``combine`` or ``alignment``."""

    def __post_init__(self) -> None:
        """Check the schema itself."""
        if not _NAME.fullmatch(self.name):
            msg = f"a transform name is lowercase snake_case, not {self.name!r}"
            raise f.fail(msg)
        f.text(self.summary, "transform summary")
        names = [parameter.name for parameter in self.parameters]
        if len(set(names)) != len(names):
            msg = f"transform {self.name!r} repeats a parameter"
            raise f.fail(msg)
        if self.operands not in {1, 2}:
            msg = f"transform {self.name!r} reads one or two series"
            raise f.fail(msg)

    def parameter(self, name: str) -> TransformParameter:
        """Return the named parameter.

        Raises
        ------
        InputError
            If the transform has no parameter of that name.
        """
        for parameter in self.parameters:
            if parameter.name == name:
                return parameter
        msg = f"transform {self.name!r} has no parameter {name!r}"
        raise f.fail(msg)


@dataclass(frozen=True, slots=True)
class ParsedTransform:
    """A checked transform: its spec and its arguments, defaults filled in."""

    spec: TransformSpec
    arguments: dict[str, int | bool | str]

    @property
    def name(self) -> str:
        """The transform's name."""
        return self.spec.name

    def text(self) -> str:
        """Return the canonical text (defaults left out, schema order)."""
        shown = [
            f"{parameter.name}={_show(self.arguments[parameter.name])}"
            for parameter in self.spec.parameters
            if parameter.name in self.arguments
            and self.arguments[parameter.name] != parameter.default
        ]
        return self.spec.name + (f"({','.join(shown)})" if shown else "")


def _show(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _spec(
    name: str,
    summary: str,
    *parameters: TransformParameter,
    operands: int = 1,
    group: str = "change",
) -> tuple[str, TransformSpec]:
    return name, TransformSpec(
        name=name,
        summary=summary,
        parameters=tuple(parameters),
        operands=operands,
        group=group,
    )


_PERIODS = TransformParameter(
    name="periods",
    kind=TransformParameterKind.INTEGER,
    summary="How many observations back the comparison reaches.",
    default=1,
)
_DATE_PARAM = TransformParameter(
    name="date",
    kind=TransformParameterKind.DATE,
    summary="The date the rule is read at.",
    required=True,
)
_MAX_AGE = TransformParameter(
    name="max_age_days",
    kind=TransformParameterKind.INTEGER,
    summary=(
        "The oldest an observation may be, in days before the date, to count; "
        "any age when absent."
    ),
    minimum=0,
    maximum=MAX_AGE_DAYS,
)

#: Every transform, by name: the vocabulary a binding is checked against.
TRANSFORMS: Final[Mapping[str, TransformSpec]] = MappingProxyType(
    dict(
        sorted(
            (
                _spec(
                    "pct_change",
                    "The fractional change from the observation `periods` back, "
                    "as a decimal (0.02, not 2). A date with no observation that "
                    "far back, or a missing one, is missing.",
                    _PERIODS,
                ),
                _spec(
                    "yoy",
                    "The fractional change from the same period one year earlier "
                    "(month-based frequencies only), as a decimal.",
                ),
                _spec(
                    "diff",
                    "The difference from the observation `periods` back, in the "
                    "series' own unit.",
                    _PERIODS,
                ),
                _spec(
                    "lag",
                    "The value of the observation `periods` back, on each date: "
                    "`lag(periods=12)` of a monthly series is its value a year "
                    "earlier. A date with no observation that far back is "
                    "missing.",
                    _PERIODS,
                ),
                _spec(
                    "log",
                    "The natural logarithm; a value that is not positive is "
                    "refused, never replaced.",
                ),
                _spec(
                    "changes_only",
                    "The dates on which the value differs from the previous "
                    "observation, plus the first: a daily step series becomes "
                    "its change dates.",
                ),
                _spec(
                    "ratio",
                    "The first series over the second on the dates they "
                    "share (their frequency must match); `excess` subtracts "
                    "one, so a ratio of actual to potential becomes a gap.",
                    TransformParameter(
                        name="excess",
                        kind=TransformParameterKind.FLAG,
                        summary="Subtract one from the ratio.",
                        default=False,
                    ),
                    operands=2,
                    group="combine",
                ),
                _spec(
                    "add",
                    "The first series plus the second on the dates they share "
                    "(their frequency and unit kind must match), in the first "
                    "series' unit.",
                    operands=2,
                    group="combine",
                ),
                _spec(
                    "convert",
                    "Change the observation frequency by an explicit method. "
                    "Aggregating needs every period complete and never fills; "
                    "going to a higher frequency with `period_end` puts each "
                    "value on its period's last day and leaves the other "
                    "periods missing.",
                    TransformParameter(
                        name="to",
                        kind=TransformParameterKind.CHOICE,
                        summary="The frequency to convert to.",
                        required=True,
                        choices=("monthly", "quarterly", "semiannual", "annual"),
                    ),
                    TransformParameter(
                        name="method",
                        kind=TransformParameterKind.CHOICE,
                        summary="How the observations of one period combine.",
                        required=True,
                        choices=("mean", "sum", "first", "last", "period_end"),
                    ),
                    group="frequency",
                ),
                _spec(
                    "align_to",
                    "Read the first series on the second's dates: at each, the "
                    "last observation on or before it, no older than "
                    "`max_age_days`. A date with none is refused.",
                    _MAX_AGE,
                    operands=2,
                    group="alignment",
                ),
                _spec(
                    "asof",
                    "The last observation on or before `date`, no older than "
                    "`max_age_days`; refused when there is none.",
                    _DATE_PARAM,
                    _MAX_AGE,
                    group="alignment",
                ),
                _spec(
                    "period",
                    "The observation of the period that contains `date`; "
                    "refused when it is absent or missing.",
                    _DATE_PARAM,
                    group="alignment",
                ),
                _spec(
                    "window",
                    "The last `count` observations on or before `date`; "
                    "refused when fewer exist or one is missing.",
                    TransformParameter(
                        name="count",
                        kind=TransformParameterKind.INTEGER,
                        summary="How many observations to read.",
                        required=True,
                    ),
                    _DATE_PARAM,
                    group="alignment",
                ),
            ),
            key=lambda item: item[0],
        )
    )
)

#: The names of :data:`TRANSFORMS`.
TRANSFORM_NAMES: Final = frozenset(TRANSFORMS)


def _argument(parameter: TransformParameter, word: str) -> int | bool | str:
    """Read one argument as its parameter's kind."""
    kind = parameter.kind
    if kind is TransformParameterKind.INTEGER and _INTEGER.fullmatch(word):
        return parameter.check(int(word))
    if kind is TransformParameterKind.FLAG and word in {"true", "false"}:
        return word == "true"
    if kind is TransformParameterKind.DATE and _DATE.fullmatch(word):
        return parameter.check(word)
    if kind is TransformParameterKind.CHOICE and _WORD.fullmatch(word):
        return parameter.check(word)
    msg = f"transform parameter {parameter.name!r} cannot read {word!r}"
    raise f.fail(msg)


def _given(spec: TransformSpec, source: str, raw: str | None) -> dict[str, object]:
    """Read the ``key=value`` pairs of a call, refusing repeats and unknown keys."""
    given: dict[str, object] = {}
    if raw is None or not raw.strip():
        return given
    for pair in raw.split(","):
        key, separator, word = (part.strip() for part in pair.partition("="))
        if not separator or not key or not word:
            msg = f"{source!r}: each argument is key=value"
            raise f.fail(msg)
        if key in given:
            msg = f"{source!r} repeats the parameter {key!r}"
            raise f.fail(msg)
        given[key] = _argument(spec.parameter(key), word)
    return given


def parse_transform(text: str) -> ParsedTransform:
    """Read and check a transform written as ``name`` or ``name(key=value,...)``.

    Parameters
    ----------
    text
        The transform's text.

    Returns
    -------
    ParsedTransform
        The spec and the arguments, every default filled in.

    Raises
    ------
    InputError
        For an unknown name, an unknown or repeated parameter, a value of the
        wrong kind or outside its bounds, or a required parameter left out.

    Examples
    --------
    >>> parse_transform("asof(date=2008-12-16)").arguments
    {'date': '2008-12-16'}
    >>> parse_transform("ratio(excess=true)").arguments
    {'excess': True}
    """
    source = f.text(text, "a transform", max_length=_MAX_TEXT).strip()
    match = _CALL.fullmatch(source)
    if match is None:
        msg = f"{source!r} is not a transform: write name or name(key=value, ...)"
        raise f.fail(msg)
    name = match["name"]
    spec = TRANSFORMS.get(name)
    if spec is None:
        known = ", ".join(sorted(TRANSFORMS))
        msg = f"unknown transform {name!r}; the transforms are {known}"
        raise f.fail(msg)
    given = _given(spec, source, match["arguments"])
    arguments: dict[str, int | bool | str] = {}
    for parameter in spec.parameters:
        if parameter.name in given:
            arguments[parameter.name] = parameter.check(given[parameter.name])
        elif parameter.required:
            msg = f"transform {name!r} needs the parameter {parameter.name!r}"
            raise f.fail(msg)
        elif parameter.default is not None:
            arguments[parameter.name] = parameter.default
    return ParsedTransform(spec, arguments)


def canonical_transform(text: str) -> str:
    """Return the one canonical text of a transform, after checking it.

    Examples
    --------
    >>> canonical_transform("pct_change(periods=1)")
    'pct_change'
    >>> canonical_transform("window(date=2020-03-31, count=4)")
    'window(count=4,date=2020-03-31)'
    """
    return parse_transform(text).text()


def check_transform(text: str) -> str:
    """Check a transform and return it unchanged; see :func:`parse_transform`."""
    parse_transform(text)
    return text


def format_transform(name: str, **arguments: int | bool | str | dt.date) -> str:
    """Write a transform's canonical text from its name and arguments.

    Examples
    --------
    >>> format_transform("convert", to="quarterly", method="mean")
    'convert(to=quarterly,method=mean)'
    >>> format_transform("asof", date=dt.date(2008, 12, 16))
    'asof(date=2008-12-16)'
    """
    spec = TRANSFORMS.get(name)
    if spec is None:
        msg = f"unknown transform {name!r}"
        raise f.fail(msg)
    shown = ",".join(
        f"{key}={_show(value.isoformat() if isinstance(value, dt.date) else value)}"
        for key, value in arguments.items()
    )
    return canonical_transform(f"{name}({shown})" if shown else name)
