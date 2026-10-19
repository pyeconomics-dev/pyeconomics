# src/pyeconomics/models/macro/policy_rule.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Simple monetary-policy rules: ``macro.policy_rule``.

The rules the Federal Reserve Board's Monetary Policy Report sets out, and the
papers behind them, as seven calculations discriminated on ``calculation``:

- ``taylor_1993``: :math:`r^* + \pi + 0.5(\pi - \pi^*) + 0.5\,y`;
- ``taylor_1999``: the same with a weight of 1.0 on the resource gap, the rule
  Taylor (1999) analysed and the Board calls the balanced approach;
- ``balanced_approach``: :math:`r^* + \pi + 0.5(\pi - \pi^*) + 1.0\,y`;
- ``balanced_approach_shortfalls``: the balanced approach answering only a
  shortfall, :math:`1.0 \min(y, 0)`;
- ``adjusted_taylor_1993``: :math:`\max(R^{T93} - Z, \text{ELB})`, which keeps the
  rate low after a spell at the lower bound until the shortfall :math:`Z` is
  made up;
- ``first_difference``: :math:`R_{t-1} + 0.5(\pi - \pi^*) + 0.5(y_t - y_{t-4})`;
- ``path``: one of the six over forecast horizons, each horizon's rate the next
  one's previous rate, with an optional band from low and high forecasts.

The resource gap :math:`y` is in output-gap units: an output gap, or an Okun
coefficient times the unemployment gap, :math:`k(u^* - u)`. With the Board's
coefficient of 2 the rules take the Report's unemployment form (a weight of 1
on :math:`u^* - u` for Taylor 1993, 2 for the balanced approach). Every rule
can be smoothed (the inertial form), :math:`R = \rho R_{t-1} + (1 - \rho)
R^{rule}`, and floored at an effective lower bound, which applies to the
smoothed rate. Every rate is a decimal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self, cast

from pydantic import Field, model_validator

from pyeconomics.core import (
    ARRAY_INPUT,
    AsOf,
    Binding,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    Count,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    Ratio,
    Reference,
    model,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

__all__ = ["policy_rule"]

#: Inflation, current or forecast: deflation of 20% to inflation of 50%.
_INFLATION_MIN: Final = -0.2
_INFLATION_MAX: Final = 0.5
_TARGET_MAX: Final = 0.1
#: The real neutral rate, and the nominal one (the real rate plus the target).
_NEUTRAL_MIN: Final = -0.1
_NEUTRAL_MAX: Final = 0.1
_NOMINAL_MAX: Final = 0.2
#: An output gap of 30% either way; unemployment and its natural rate to 30%.
_GAP_MAX: Final = 0.3
_UNEMPLOYMENT_MAX: Final = 0.3
_OKUN_MIN: Final = 0.1
_OKUN_MAX: Final = 4.0
_WEIGHT_MAX: Final = 4.0
#: A policy rate before the rule's date, and the lower bound.
_RATE_MIN: Final = -0.1
_RATE_MAX: Final = 1.0
_BOUND_MAX: Final = 0.1
_SHORTFALL_MAX: Final = 1.0
#: The Board's effective lower bound for the adjusted rule: 12.5 basis points.
_ELB: Final = 0.00125
#: A level rule's prescription stays within 0.2 + 5 x 0.5 + 4 x 1.2 = 7.5 of
#: zero, and a first-difference one within 1 + 2 + 4 x 2.4 = 12.6; the terms are
#: smaller. A path of 40 first-difference steps moves at most 40 x 11.6.
_OUT: Final = 20.0
_PATH_OUT: Final = 500.0
#: The longest forecast path: ten years of quarters, CBO's horizon.
_HORIZONS: Final = 40

type RuleName = Literal[
    "taylor_1993",
    "taylor_1999",
    "balanced_approach",
    "balanced_approach_shortfalls",
    "adjusted_taylor_1993",
    "first_difference",
]
type GapMeasure = Literal["unemployment", "output"]

#: Each rule's published weight on the resource gap, in output-gap units.
RESOURCE_WEIGHTS: Final[dict[str, float]] = {
    "taylor_1993": 0.5,
    "taylor_1999": 1.0,
    "balanced_approach": 1.0,
    "balanced_approach_shortfalls": 1.0,
    "adjusted_taylor_1993": 0.5,
    "first_difference": 0.5,
}


def _inflation(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=_INFLATION_MIN, le=_INFLATION_MAX, description=description)


def _optional(low: float, high: float, description: str) -> Any:  # noqa: ANN401
    return Field(None, ge=low, le=high, description=description)


# --- inputs ------------------------------------------------------------------


class _Common(ModelInputs):
    """What every rule reads: inflation, its target, the gap and the settings."""

    inflation: Rate = _inflation(
        "Inflation the rule answers: over the past four quarters, or a forecast"
    )
    inflation_target: Rate = Field(
        0.02, ge=0.0, le=_TARGET_MAX, description="The inflation objective"
    )
    gap_measure: GapMeasure | None = Field(
        None,
        description=(
            "How the resource gap is measured; left out, it follows the fields given"
        ),
    )
    output_gap: Rate | None = _optional(
        -_GAP_MAX, _GAP_MAX, "Output gap: real GDP over potential, less one"
    )
    unemployment: Rate | None = _optional(
        0.0, _UNEMPLOYMENT_MAX, "The unemployment rate"
    )
    natural_unemployment: Rate | None = _optional(
        0.0, _UNEMPLOYMENT_MAX, "The natural (longer-run) rate of unemployment"
    )
    okun_coefficient: Ratio = Field(
        2.0,
        ge=_OKUN_MIN,
        le=_OKUN_MAX,
        description="Output-gap points per point of unemployment gap (Okun's law)",
    )
    inflation_weight: Ratio = Field(
        0.5, ge=0.0, le=_WEIGHT_MAX, description="Weight on the inflation gap"
    )
    smoothing: Ratio = Field(
        0.0,
        ge=0.0,
        le=1.0,
        description="Weight on the previous rate (the inertial form); 0 is none",
    )
    lower_bound: Rate | None = _optional(
        _RATE_MIN, _BOUND_MAX, "An effective lower bound that floors the prescription"
    )

    @model_validator(mode="after")
    def _one_resource_gap(self) -> Self:
        _measure(
            self.gap_measure,
            self.output_gap,
            self.unemployment,
            self.natural_unemployment,
        )
        return self


def _weight(default: float, description: str = "Weight on the resource gap") -> Any:  # noqa: ANN401
    return Field(default, ge=0.0, le=_WEIGHT_MAX, description=description)


class _Level(_Common):
    """A rule on the level of the neutral rate."""

    resource_weight: Ratio = _weight(0.5)
    neutral_real_rate: Rate | None = _optional(
        _NEUTRAL_MIN, _NEUTRAL_MAX, "The real neutral rate, r*"
    )
    neutral_nominal_rate: Rate | None = _optional(
        _NEUTRAL_MIN,
        _NOMINAL_MAX,
        "The nominal neutral rate, r* plus the target (the SEP's longer-run rate)",
    )
    previous_rate: Rate | None = _optional(
        _RATE_MIN, _RATE_MAX, "The policy rate before the rule's date, for smoothing"
    )

    @model_validator(mode="after")
    def _one_neutral_rate_and_a_previous_rate(self) -> Self:
        if (self.neutral_real_rate is None) == (self.neutral_nominal_rate is None):
            msg = "give one of neutral_real_rate and neutral_nominal_rate"
            raise ValueError(msg)
        if self.smoothing > 0 and self.previous_rate is None:
            msg = "smoothing needs previous_rate, the policy rate it smooths from"
            raise ValueError(msg)
        return self


class Taylor1993Inputs(_Level):
    """Taylor (1993): a weight of 0.5 on the inflation gap and on the output gap."""

    calculation: Literal["taylor_1993"] = Field(
        "taylor_1993", description="The Taylor (1993) rule"
    )


class Taylor1999Inputs(_Level):
    """Taylor (1999): a weight of 1.0 on the output gap."""

    calculation: Literal["taylor_1999"] = Field(
        "taylor_1999", description="The Taylor (1999) rule"
    )
    resource_weight: Ratio = _weight(1.0)


class BalancedApproachInputs(_Level):
    """The balanced approach: twice the Taylor (1993) weight on the gap."""

    calculation: Literal["balanced_approach"] = Field(
        "balanced_approach", description="The balanced-approach rule"
    )
    resource_weight: Ratio = _weight(1.0)


class ShortfallsInputs(_Level):
    """The balanced approach answering only a shortfall of activity."""

    calculation: Literal["balanced_approach_shortfalls"] = Field(
        "balanced_approach_shortfalls",
        description="The balanced-approach (shortfalls) rule",
    )
    resource_weight: Ratio = _weight(1.0, "Weight on a negative resource gap")


class AdjustedTaylor1993Inputs(_Level):
    """Taylor (1993) less the shortfall left by the lower bound, floored at it."""

    calculation: Literal["adjusted_taylor_1993"] = Field(
        "adjusted_taylor_1993", description="The adjusted Taylor (1993) rule"
    )
    cumulative_shortfall: Rate = Field(
        0.0,
        ge=0.0,
        le=_SHORTFALL_MAX,
        description=(
            "Z: the sum of the rate's past excesses over Taylor (1993) prescriptions "
            "below the lower bound, still to be made up"
        ),
    )
    lower_bound: Rate = Field(
        _ELB,
        ge=_RATE_MIN,
        le=_BOUND_MAX,
        description=(
            "The effective lower bound the rule is floored at; the Board's is 12.5 "
            "basis points"
        ),
    )


class FirstDifferenceInputs(_Common):
    """The first-difference rule: the previous rate plus the change it prescribes."""

    calculation: Literal["first_difference"] = Field(
        "first_difference", description="The first-difference rule"
    )
    resource_weight: Ratio = _weight(0.5, "Weight on the change in the resource gap")
    previous_rate: Rate = Field(
        ge=_RATE_MIN, le=_RATE_MAX, description="The policy rate a quarter earlier"
    )
    output_gap_lagged: Rate | None = _optional(
        -_GAP_MAX, _GAP_MAX, "The output gap four quarters earlier"
    )
    unemployment_lagged: Rate | None = _optional(
        0.0, _UNEMPLOYMENT_MAX, "The unemployment rate four quarters earlier"
    )
    natural_unemployment_lagged: Rate | None = _optional(
        0.0,
        _UNEMPLOYMENT_MAX,
        "The natural rate four quarters earlier; the current one when left out",
    )

    @model_validator(mode="after")
    def _the_gap_four_quarters_earlier(self) -> Self:
        measure = _measure(
            self.gap_measure,
            self.output_gap,
            self.unemployment,
            self.natural_unemployment,
        )
        _lagged(
            measure,
            self.output_gap_lagged,
            self.unemployment_lagged,
            self.natural_unemployment_lagged,
        )
        return self


# --- the path ------------------------------------------------------------------

_Inflations = Annotated[
    tuple[Annotated[Rate, Field(ge=_INFLATION_MIN, le=_INFLATION_MAX)], ...],
    ARRAY_INPUT,
]
_Gaps = Annotated[
    tuple[Annotated[Rate, Field(ge=-_GAP_MAX, le=_GAP_MAX)], ...], ARRAY_INPUT
]
_Unemployments = Annotated[
    tuple[Annotated[Rate, Field(ge=0.0, le=_UNEMPLOYMENT_MAX)], ...], ARRAY_INPUT
]


def _path(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(None, min_length=1, max_length=_HORIZONS, description=description)


class PathInputs(ModelInputs):
    """One rule over forecast horizons: a path of inflation and of the gap."""

    calculation: Literal["path"] = Field("path", description="A rule over a forecast")
    rule: RuleName = Field(description="The rule to apply at each horizon")
    inflation_path: _Inflations = Field(
        min_length=1, max_length=_HORIZONS, description="Inflation at each horizon"
    )
    inflation_target: Rate = Field(
        0.02, ge=0.0, le=_TARGET_MAX, description="The inflation objective"
    )
    gap_measure: GapMeasure | None = Field(
        None,
        description=(
            "How the resource gap is measured; left out, it follows the paths given"
        ),
    )
    output_gap_path: _Gaps | None = _path("Output gap at each horizon")
    unemployment_path: _Unemployments | None = _path("Unemployment at each horizon")
    natural_unemployment_path: _Unemployments | None = _path(
        "The natural rate of unemployment at each horizon"
    )
    output_gap_lagged_path: _Gaps | None = _path(
        "For the first-difference rule: each horizon's output gap four quarters back"
    )
    unemployment_lagged_path: _Unemployments | None = _path(
        "For the first-difference rule: each horizon's unemployment four quarters back"
    )
    natural_unemployment_lagged_path: _Unemployments | None = _path(
        "For the first-difference rule: the natural rate four quarters back; the "
        "horizon's own when left out"
    )
    inflation_low_path: _Inflations | None = _path(
        "A low inflation forecast (a 25th percentile) for the band's lower edge"
    )
    inflation_high_path: _Inflations | None = _path(
        "A high inflation forecast (a 75th percentile) for the band's upper edge"
    )
    output_gap_low_path: _Gaps | None = _path("A low output-gap forecast, for the band")
    output_gap_high_path: _Gaps | None = _path(
        "A high output-gap forecast, for the band"
    )
    unemployment_low_path: _Unemployments | None = _path(
        "A low unemployment forecast, for the band's upper edge"
    )
    unemployment_high_path: _Unemployments | None = _path(
        "A high unemployment forecast, for the band's lower edge"
    )
    neutral_real_rate: Rate | None = _optional(
        _NEUTRAL_MIN, _NEUTRAL_MAX, "The real neutral rate, r*, for a level rule"
    )
    neutral_nominal_rate: Rate | None = _optional(
        _NEUTRAL_MIN, _NOMINAL_MAX, "The nominal neutral rate, for a level rule"
    )
    okun_coefficient: Ratio = Field(
        2.0,
        ge=_OKUN_MIN,
        le=_OKUN_MAX,
        description="Output-gap points per point of unemployment gap (Okun's law)",
    )
    inflation_weight: Ratio = Field(
        0.5, ge=0.0, le=_WEIGHT_MAX, description="Weight on the inflation gap"
    )
    resource_weight: Ratio | None = _optional(
        0.0, _WEIGHT_MAX, "Weight on the resource gap; the rule's own when left out"
    )
    smoothing: Ratio = Field(
        0.0, ge=0.0, le=1.0, description="Weight on the previous rate at each horizon"
    )
    previous_rate: Rate | None = _optional(
        _RATE_MIN, _RATE_MAX, "The policy rate before the first horizon"
    )
    lower_bound: Rate | None = _optional(
        _RATE_MIN,
        _BOUND_MAX,
        "An effective lower bound; for the adjusted rule, 12.5 basis points when "
        "left out",
    )
    cumulative_shortfall: Rate = Field(
        0.0,
        ge=0.0,
        le=_SHORTFALL_MAX,
        description="For the adjusted rule: the shortfall Z, held over the path",
    )

    @model_validator(mode="after")
    def _paths_that_fit(self) -> Self:
        size = len(self.inflation_path)
        measure = _measure(
            self.gap_measure,
            self.output_gap_path,
            self.unemployment_path,
            self.natural_unemployment_path,
        )
        for name in (
            "output_gap_path",
            "unemployment_path",
            "natural_unemployment_path",
            "output_gap_lagged_path",
            "unemployment_lagged_path",
            "natural_unemployment_lagged_path",
            "inflation_low_path",
            "inflation_high_path",
            "output_gap_low_path",
            "output_gap_high_path",
            "unemployment_low_path",
            "unemployment_high_path",
        ):
            value = getattr(self, name)
            if value is not None and len(value) != size:
                msg = f"{name} has {len(value)} horizons; inflation_path has {size}"
                raise ValueError(msg)
        _band(self, measure)
        _used_by_the_rule(self)
        level = self.rule != "first_difference"
        given = (self.neutral_real_rate is not None) + (
            self.neutral_nominal_rate is not None
        )
        if level and given != 1:
            msg = f"{self.rule} needs one of neutral_real_rate and neutral_nominal_rate"
            raise ValueError(msg)
        if not level:
            if given:
                msg = "the first-difference rule uses no neutral rate"
                raise ValueError(msg)
            if self.previous_rate is None:
                msg = "the first-difference rule needs previous_rate"
                raise ValueError(msg)
            _lagged(
                measure,
                self.output_gap_lagged_path,
                self.unemployment_lagged_path,
                self.natural_unemployment_lagged_path,
            )
        if self.smoothing > 0 and self.previous_rate is None:
            msg = "smoothing needs previous_rate, the policy rate it smooths from"
            raise ValueError(msg)
        return self


def _used_by_the_rule(inputs: PathInputs) -> None:
    """Refuse a path input the chosen rule would ignore."""
    if inputs.rule != "adjusted_taylor_1993" and inputs.cumulative_shortfall > 0:
        msg = f"cumulative_shortfall is the adjusted rule's; {inputs.rule} takes none"
        raise ValueError(msg)
    lagged = (
        "output_gap_lagged_path",
        "unemployment_lagged_path",
        "natural_unemployment_lagged_path",
    )
    given = [name for name in lagged if getattr(inputs, name) is not None]
    if inputs.rule != "first_difference" and given:
        msg = f"{given[0]} is the first-difference rule's; {inputs.rule} takes none"
        raise ValueError(msg)


def _measure(
    named: GapMeasure | None, output: object, unemployment: object, natural: object
) -> GapMeasure:
    """Say how the gap is measured, refusing a gap given twice or not at all."""
    if (unemployment is None) != (natural is None):
        msg = "give unemployment and natural_unemployment together"
        raise ValueError(msg)
    has_output, has_unemployment = output is not None, unemployment is not None
    if named is None:
        if has_output == has_unemployment:
            msg = (
                "give the resource gap once: an output gap, or unemployment and its "
                "natural rate"
            )
            raise ValueError(msg)
        return "output" if has_output else "unemployment"
    if named == "output" and (not has_output or has_unemployment):
        msg = "gap_measure 'output' takes the output gap, and no unemployment"
        raise ValueError(msg)
    if named == "unemployment" and (not has_unemployment or has_output):
        msg = "gap_measure 'unemployment' takes unemployment and its natural rate only"
        raise ValueError(msg)
    return named


def _lagged(
    measure: GapMeasure, output: object, unemployment: object, natural: object
) -> None:
    """Hold the gap four quarters earlier to the measure of the current one."""
    if measure == "output":
        if output is None or unemployment is not None or natural is not None:
            msg = "the first-difference rule on the output gap needs output_gap_lagged"
            raise ValueError(msg)
    elif unemployment is None or output is not None:
        msg = "the first-difference rule on unemployment needs unemployment_lagged"
        raise ValueError(msg)


def _band(inputs: PathInputs, measure: GapMeasure) -> None:
    """Hold a band's forecasts to the measure and to low <= central <= high."""
    pairs: list[tuple[str, str, str]] = [
        ("inflation_low_path", "inflation_path", "inflation_high_path")
    ]
    pairs.append(
        ("output_gap_low_path", "output_gap_path", "output_gap_high_path")
        if measure == "output"
        else ("unemployment_low_path", "unemployment_path", "unemployment_high_path")
    )
    other = (
        ("unemployment_low_path", "unemployment_high_path")
        if measure == "output"
        else ("output_gap_low_path", "output_gap_high_path")
    )
    if any(getattr(inputs, name) is not None for name in other):
        msg = f"a band on the {measure} gap takes no {other[0]} or {other[1]}"
        raise ValueError(msg)
    for low_name, middle_name, high_name in pairs:
        low, middle, high = (
            getattr(inputs, n) for n in (low_name, middle_name, high_name)
        )
        if (low is None) != (high is None):
            msg = f"give {low_name} and {high_name} together"
            raise ValueError(msg)
        if low is not None and not all(
            a <= b <= c for a, b, c in zip(low, middle, high, strict=True)
        ):
            msg = f"each horizon needs {low_name} <= {middle_name} <= {high_name}"
            raise ValueError(msg)


PolicyRuleInputs = Annotated[
    Taylor1993Inputs
    | Taylor1999Inputs
    | BalancedApproachInputs
    | ShortfallsInputs
    | AdjustedTaylor1993Inputs
    | FirstDifferenceInputs
    | PathInputs,
    Field(discriminator="calculation"),
]


# --- outputs -------------------------------------------------------------------


def _out(description: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(ge=-_OUT, le=_OUT, description=description)


class _Prescribed(ModelOutputs):
    prescribed_rate: Rate = _out("The policy rate the rule prescribes")
    unconstrained_rate: Rate = _out(
        "The prescription before the lower bound: the rule, smoothed"
    )
    inflation_gap_term: Rate = _out("The weight on inflation times its gap")
    resource_gap_term: Rate = _out("The weight on the resource gap times the gap")


class _LevelOutputs(_Prescribed):
    nominal_neutral_rate: Rate = Field(
        ge=_NEUTRAL_MIN,
        le=_NOMINAL_MAX,
        description="The real neutral rate plus the target: the rate at no gaps",
    )


class Taylor1993Outputs(_LevelOutputs):
    calculation: Literal["taylor_1993"] = Field(
        "taylor_1993", description="The Taylor (1993) rule"
    )


class Taylor1999Outputs(_LevelOutputs):
    calculation: Literal["taylor_1999"] = Field(
        "taylor_1999", description="The Taylor (1999) rule"
    )


class BalancedApproachOutputs(_LevelOutputs):
    calculation: Literal["balanced_approach"] = Field(
        "balanced_approach", description="The balanced-approach rule"
    )


class ShortfallsOutputs(_LevelOutputs):
    calculation: Literal["balanced_approach_shortfalls"] = Field(
        "balanced_approach_shortfalls",
        description="The balanced-approach (shortfalls) rule",
    )


class AdjustedTaylor1993Outputs(_LevelOutputs):
    calculation: Literal["adjusted_taylor_1993"] = Field(
        "adjusted_taylor_1993", description="The adjusted Taylor (1993) rule"
    )


class FirstDifferenceOutputs(_Prescribed):
    calculation: Literal["first_difference"] = Field(
        "first_difference", description="The first-difference rule"
    )


_PathRates = Annotated[
    tuple[Annotated[Rate, Field(ge=-_PATH_OUT, le=_PATH_OUT)], ...], ARRAY_INPUT
]
_Horizons = Annotated[
    tuple[Annotated[Count, Field(ge=0, le=_HORIZONS)], ...], ARRAY_INPUT
]


class PathOutputs(ModelOutputs):
    calculation: Literal["path"] = Field("path", description="A rule over a forecast")
    rule: RuleName = Field(description="The rule applied at each horizon")
    horizon: _Horizons = Field(
        max_length=_HORIZONS, description="Horizons after the first: 0, 1, 2, ..."
    )
    prescribed_path: _PathRates = Field(
        max_length=_HORIZONS, description="The prescribed rate at each horizon"
    )
    unconstrained_path: _PathRates = Field(
        max_length=_HORIZONS, description="Each prescription before the lower bound"
    )
    lower_path: _PathRates = Field(
        max_length=_HORIZONS,
        description="The band's lower edge (low inflation, weak activity); empty "
        "with no band",
    )
    upper_path: _PathRates = Field(
        max_length=_HORIZONS,
        description="The band's upper edge (high inflation, strong activity); empty "
        "with no band",
    )


PolicyRuleOutputs = Annotated[
    Taylor1993Outputs
    | Taylor1999Outputs
    | BalancedApproachOutputs
    | ShortfallsOutputs
    | AdjustedTaylor1993Outputs
    | FirstDifferenceOutputs
    | PathOutputs,
    Field(discriminator="calculation"),
]


# --- the arithmetic ------------------------------------------------------------


@dataclass(frozen=True, slots=True, kw_only=True)
class _Step:
    """What one rule reads at one date, in output-gap units."""

    rule: str
    inflation: float
    target: float
    gap: float
    gap_lagged: float = 0.0
    neutral_real: float = 0.0
    previous: float | None = None
    inflation_weight: float
    resource_weight: float
    smoothing: float
    lower_bound: float | None
    shortfall: float = 0.0


@dataclass(frozen=True, slots=True)
class _Prescription:
    prescribed: float
    unconstrained: float
    inflation_term: float
    resource_term: float

    @property
    def binds(self) -> bool:
        return self.prescribed != self.unconstrained


def _prescribe(step: _Step) -> _Prescription:
    """Apply one rule: its terms, the smoothing, then the lower bound."""
    inflation_term = step.inflation_weight * (step.inflation - step.target)
    if step.rule == "first_difference":
        resource_term = step.resource_weight * (step.gap - step.gap_lagged)
        notional = (step.previous or 0.0) + inflation_term + resource_term
    else:
        gap = (
            min(step.gap, 0.0)
            if step.rule == "balanced_approach_shortfalls"
            else step.gap
        )
        resource_term = step.resource_weight * gap
        notional = step.neutral_real + step.inflation + inflation_term + resource_term
        if step.rule == "adjusted_taylor_1993":
            notional -= step.shortfall
    smoothed = notional
    if step.smoothing > 0:
        previous = step.previous or 0.0
        smoothed = step.smoothing * previous + (1.0 - step.smoothing) * notional
    prescribed = smoothed
    if step.lower_bound is not None and smoothed < step.lower_bound:
        prescribed = step.lower_bound
    return _Prescription(prescribed, smoothed, inflation_term, resource_term)


def _unemployment_gap(okun: float, natural: float, unemployment: float) -> float:
    return okun * (natural - unemployment)


def _gap_of(inputs: _Common) -> float:
    if inputs.output_gap is not None:
        return inputs.output_gap
    return _unemployment_gap(
        inputs.okun_coefficient,
        inputs.natural_unemployment or 0.0,
        inputs.unemployment or 0.0,
    )


def _neutral_real(
    neutral_real: float | None, neutral_nominal: float | None, target: float
) -> float:
    if neutral_real is not None:
        return neutral_real
    return (neutral_nominal or 0.0) - target


def _warn_bound(bound: float | None) -> None:
    warn(
        "elb_binding",
        f"the rule prescribes a rate below the lower bound {bound:g}; the "
        "prescription is the bound",
    )


#: Each level rule's inputs, with its name and its outputs.
_LEVELS: Final[dict[type[_Level], tuple[str, type[_LevelOutputs]]]] = {
    Taylor1993Inputs: ("taylor_1993", Taylor1993Outputs),
    Taylor1999Inputs: ("taylor_1999", Taylor1999Outputs),
    BalancedApproachInputs: ("balanced_approach", BalancedApproachOutputs),
    ShortfallsInputs: ("balanced_approach_shortfalls", ShortfallsOutputs),
    AdjustedTaylor1993Inputs: ("adjusted_taylor_1993", AdjustedTaylor1993Outputs),
}


def _level(inputs: _Level) -> PolicyRuleOutputs:
    rule, outputs = _LEVELS[type(inputs)]
    shortfall = (
        inputs.cumulative_shortfall
        if isinstance(inputs, AdjustedTaylor1993Inputs)
        else 0.0
    )
    neutral = _neutral_real(
        inputs.neutral_real_rate, inputs.neutral_nominal_rate, inputs.inflation_target
    )
    result = _prescribe(
        _Step(
            rule=rule,
            inflation=inputs.inflation,
            target=inputs.inflation_target,
            gap=_gap_of(inputs),
            neutral_real=neutral,
            previous=inputs.previous_rate,
            inflation_weight=inputs.inflation_weight,
            resource_weight=inputs.resource_weight,
            smoothing=inputs.smoothing,
            lower_bound=inputs.lower_bound,
            shortfall=shortfall,
        )
    )
    if result.binds:
        _warn_bound(inputs.lower_bound)
    nominal = (
        inputs.neutral_nominal_rate
        if inputs.neutral_nominal_rate is not None
        else neutral + inputs.inflation_target
    )
    built = outputs(
        prescribed_rate=result.prescribed,
        unconstrained_rate=result.unconstrained,
        inflation_gap_term=result.inflation_term,
        resource_gap_term=result.resource_term,
        nominal_neutral_rate=nominal,
    )
    return cast("PolicyRuleOutputs", built)


def _first_difference(inputs: FirstDifferenceInputs) -> FirstDifferenceOutputs:
    if inputs.output_gap_lagged is not None:
        lagged = inputs.output_gap_lagged
    else:
        natural = inputs.natural_unemployment_lagged
        if natural is None:
            natural = inputs.natural_unemployment or 0.0
        lagged = _unemployment_gap(
            inputs.okun_coefficient, natural, inputs.unemployment_lagged or 0.0
        )
    result = _prescribe(
        _Step(
            rule="first_difference",
            inflation=inputs.inflation,
            target=inputs.inflation_target,
            gap=_gap_of(inputs),
            gap_lagged=lagged,
            previous=inputs.previous_rate,
            inflation_weight=inputs.inflation_weight,
            resource_weight=inputs.resource_weight,
            smoothing=inputs.smoothing,
            lower_bound=inputs.lower_bound,
        )
    )
    if result.binds:
        _warn_bound(inputs.lower_bound)
    return FirstDifferenceOutputs(
        prescribed_rate=result.prescribed,
        unconstrained_rate=result.unconstrained,
        inflation_gap_term=result.inflation_term,
        resource_gap_term=result.resource_term,
    )


def _gaps(
    inputs: PathInputs,
    output: Sequence[float] | None,
    unemployment: Sequence[float] | None,
    natural: Sequence[float] | None,
) -> list[float]:
    """Each horizon's gap in output-gap units, from whichever measure is given."""
    if output is not None:
        return list(output)
    rates = unemployment or ()
    naturals = (
        natural if natural is not None else inputs.natural_unemployment_path or ()
    )
    return [
        _unemployment_gap(inputs.okun_coefficient, n, u)
        for n, u in zip(naturals, rates, strict=True)
    ]


def _walk(
    inputs: PathInputs, inflation: Sequence[float], gaps: Sequence[float]
) -> tuple[list[_Prescription], bool]:
    """Run the rule along the path; each horizon's rate is the next one's previous."""
    rule = inputs.rule
    lagged = (
        _gaps(
            inputs,
            inputs.output_gap_lagged_path,
            inputs.unemployment_lagged_path,
            inputs.natural_unemployment_lagged_path,
        )
        if rule == "first_difference"
        else [0.0] * len(inflation)
    )
    bound = inputs.lower_bound
    if bound is None and rule == "adjusted_taylor_1993":
        bound = _ELB
    neutral = _neutral_real(
        inputs.neutral_real_rate, inputs.neutral_nominal_rate, inputs.inflation_target
    )
    weight = (
        RESOURCE_WEIGHTS[rule]
        if inputs.resource_weight is None
        else inputs.resource_weight
    )
    previous = inputs.previous_rate
    steps: list[_Prescription] = []
    for pi, gap, lag in zip(inflation, gaps, lagged, strict=True):
        result = _prescribe(
            _Step(
                rule=rule,
                inflation=pi,
                target=inputs.inflation_target,
                gap=gap,
                gap_lagged=lag,
                neutral_real=neutral,
                previous=previous,
                inflation_weight=inputs.inflation_weight,
                resource_weight=weight,
                smoothing=inputs.smoothing,
                lower_bound=bound,
                shortfall=inputs.cumulative_shortfall,
            )
        )
        steps.append(result)
        previous = result.prescribed
    return steps, any(step.binds for step in steps)


def _path_of(inputs: PathInputs) -> PathOutputs:
    central = _gaps(inputs, inputs.output_gap_path, inputs.unemployment_path, None)
    steps, binds = _walk(inputs, inputs.inflation_path, central)
    lower: list[float] = []
    upper: list[float] = []
    banded = any(
        getattr(inputs, name) is not None
        for name in (
            "inflation_low_path",
            "output_gap_low_path",
            "unemployment_low_path",
        )
    )
    if banded:
        weak = _gaps(
            inputs,
            inputs.output_gap_low_path or inputs.output_gap_path,
            inputs.unemployment_high_path or inputs.unemployment_path,
            None,
        )
        strong = _gaps(
            inputs,
            inputs.output_gap_high_path or inputs.output_gap_path,
            inputs.unemployment_low_path or inputs.unemployment_path,
            None,
        )
        low_steps, low_binds = _walk(
            inputs, inputs.inflation_low_path or inputs.inflation_path, weak
        )
        high_steps, high_binds = _walk(
            inputs, inputs.inflation_high_path or inputs.inflation_path, strong
        )
        lower = [step.prescribed for step in low_steps]
        upper = [step.prescribed for step in high_steps]
        binds = binds or low_binds or high_binds
    if binds:
        _warn_bound(inputs.lower_bound if inputs.lower_bound is not None else _ELB)
    return PathOutputs(
        rule=inputs.rule,
        horizon=tuple(range(len(steps))),
        prescribed_path=tuple(step.prescribed for step in steps),
        unconstrained_path=tuple(step.unconstrained for step in steps),
        lower_path=tuple(lower),
        upper_path=tuple(upper),
    )


# --- the model -----------------------------------------------------------------

_TAYLOR_1993 = Reference(
    key="taylor1993",
    citation=(
        "Taylor, J. B. (1993). Discretion versus Policy Rules in Practice. "
        "Carnegie-Rochester Conference Series on Public Policy, 39, 195-214."
    ),
    doi="10.1016/0167-2231(93)90009-L",
    locator="The rule and its weights of one half, p. 202",
)
_TAYLOR_1999 = Reference(
    key="taylor1999",
    citation=(
        "Taylor, J. B. (1999). A Historical Analysis of Monetary Policy Rules. In "
        "J. B. Taylor (ed.), Monetary Policy Rules, pp. 319-341. University of "
        "Chicago Press."
    ),
    doi="10.7208/chicago/9780226791265.001.0001",
    locator="Chapter 7: the rule with a weight of 1.0 on the output gap",
)
_REIFSCHNEIDER = Reference(
    key="reifschneider2000",
    citation=(
        "Reifschneider, D. and Williams, J. C. (2000). Three Lessons for Monetary "
        "Policy in a Low-Inflation Era. Journal of Money, Credit and Banking, "
        "32(4), 936-966."
    ),
    doi="10.2307/2601151",
    locator="The rule that makes up past shortfalls at the zero bound",
)
_ORPHANIDES = Reference(
    key="orph2003",
    citation=(
        "Orphanides, A. (2003). Historical Monetary Policy Analysis and the Taylor "
        "Rule. Journal of Monetary Economics, 50(5), 983-1022."
    ),
    doi="10.1016/S0304-3932(03)00065-5",
    locator="The rule in first differences",
)
_MPR_2026 = Reference(
    key="mpr2026",
    citation=(
        "Board of Governors of the Federal Reserve System (2026). Monetary Policy "
        "Report, July 2026. Box 4, Monetary Policy Rules in the Current "
        "Environment."
    ),
    url="https://www.federalreserve.gov/monetarypolicy/files/20260710_mprfullreport.pdf",
    locator="Box 4, table A and its notes, pp. 42-43",
)
_MPR_2023 = Reference(
    key="mpr2023",
    citation=(
        "Board of Governors of the Federal Reserve System (2023). Monetary Policy "
        "Report, June 2023. Box, Monetary Policy Rules in the Current Environment."
    ),
    url="https://www.federalreserve.gov/monetarypolicy/files/20230616_mprfullreport.pdf",
    locator="Table A, p. 44: the balanced-approach (shortfalls) rule",
)

_RULE_BINDINGS: Final = (
    # Realized US data, the gap as Okun-scaled unemployment (the Report's form).
    Binding("inflation", "us.inflation.pce_core.yoy"),
    Binding("unemployment", "us.unemployment.rate"),
    Binding(
        "natural_unemployment", "us.unemployment.noncyclical_rate", as_of=AsOf.PERIOD
    ),
    Binding("neutral_real_rate", "us.neutral_rate.hlw"),
    Binding("previous_rate", "us.policy_rate.effective"),
    Binding("unemployment_lagged", "us.unemployment.rate", transform="lag(periods=12)"),
    Binding(
        "natural_unemployment_lagged",
        "us.unemployment.noncyclical_rate",
        transform="lag(periods=4)",
        as_of=AsOf.PERIOD,
    ),
    # Realized US data, the gap as real GDP over CBO's potential GDP, in the last
    # quarter published by the date (GDP for the quarter itself comes later).
    Binding("inflation", "us.inflation.pce_core.yoy", profile="us_output_gap"),
    Binding("output_gap", "us.output_gap.real_potential", profile="us_output_gap"),
    Binding(
        "output_gap_lagged",
        "us.output_gap.real_potential",
        transform="lag(periods=4)",
        profile="us_output_gap",
    ),
    Binding("neutral_real_rate", "us.neutral_rate.hlw", profile="us_output_gap"),
    Binding("previous_rate", "us.policy_rate.effective", profile="us_output_gap"),
    # The FOMC's Summary of Economic Projections, for a meeting and a year.
    Binding("inflation", "us.sep.core_pce_inflation", profile="us_sep"),
    Binding("unemployment", "us.sep.unemployment", profile="us_sep"),
    Binding("natural_unemployment", "us.sep.unemployment_longer_run", profile="us_sep"),
    Binding("neutral_nominal_rate", "us.sep.policy_rate_longer_run", profile="us_sep"),
    Binding("previous_rate", "us.policy_rate.effective", profile="us_sep"),
    # The Survey of Professional Forecasters, for the survey quarter.
    Binding(
        "inflation", "us.spf.core_pce.median_h0", as_of=AsOf.PERIOD, profile="us_spf"
    ),
    Binding(
        "unemployment",
        "us.spf.unemployment.median_h0",
        as_of=AsOf.PERIOD,
        profile="us_spf",
    ),
    Binding(
        "natural_unemployment",
        "us.unemployment.noncyclical_rate",
        as_of=AsOf.PERIOD,
        profile="us_spf",
    ),
    Binding("neutral_real_rate", "us.neutral_rate.hlw", profile="us_spf"),
    Binding("previous_rate", "us.policy_rate.effective", profile="us_spf"),
    # The euro area, the United Kingdom and Canada: the OECD's output gaps.
    Binding("inflation", "ea.inflation.hicp.yoy", profile="ea"),
    Binding("output_gap", "ea.output_gap.oecd", as_of=AsOf.PERIOD, profile="ea"),
    Binding("neutral_real_rate", "ea.neutral_rate.hlw", profile="ea"),
    Binding("previous_rate", "ea.policy_rate.headline", profile="ea"),
    Binding("inflation", "gb.inflation.cpi.yoy", profile="gb"),
    Binding("output_gap", "gb.output_gap.oecd", as_of=AsOf.PERIOD, profile="gb"),
    Binding("previous_rate", "gb.policy_rate.headline", profile="gb"),
    Binding("inflation", "ca.inflation.cpi.yoy", profile="ca"),
    Binding("output_gap", "ca.output_gap.oecd", as_of=AsOf.PERIOD, profile="ca"),
    Binding("neutral_real_rate", "ca.neutral_rate.hlw", profile="ca"),
    Binding("previous_rate", "ca.policy_rate.headline", profile="ca"),
)


@model(
    id="macro.policy_rule",
    version=1,
    title="Monetary-policy rules",
    summary=(
        "Taylor (1993 and 1999), balanced-approach, shortfalls, adjusted and "
        "first-difference rules, smoothed and floored, on a gap measured in output "
        "or unemployment, and over forecast paths."
    ),
    formula=(
        (
            r"R^{T93} = r^* + \pi + 0.5(\pi - \pi^*) + 0.5\,y, \quad "
            r"y = k(u^* - u) \text{ or the output gap}"
        ),
        (
            r"R^{T99} = R^{BA} = r^* + \pi + 0.5(\pi - \pi^*) + 1.0\,y, \quad "
            r"R^{BAS} = r^* + \pi + 0.5(\pi - \pi^*) + 1.0 \min(y, 0)"
        ),
        (
            r"R^{T93adj} = \max(R^{T93} - Z, \text{ELB}), \quad "
            r"R^{FD} = R_{t-1} + 0.5(\pi - \pi^*) + 0.5(y_t - y_{t-4})"
        ),
        r"R = \max\{\rho R_{t-1} + (1 - \rho) R^{rule},\ \text{ELB}\}",
    ),
    assumptions=(
        (
            "Rates, inflation and gaps are decimals. The resource gap is in "
            "output-gap units: an Okun coefficient k (2 by default, the Board's "
            "conversion) times the unemployment gap, or an output gap."
        ),
        (
            "Each rule's weights default to its published values (0.5 on the "
            "inflation gap; 0.5 or 1.0 on the resource gap) and may be overridden."
        ),
        (
            "Smoothing blends the previous rate with the rule's prescription; the "
            "lower bound, when given, floors the smoothed rate. The adjusted rule "
            "is floored at 12.5 basis points unless told otherwise."
        ),
        (
            "Profiles: default binds core PCE inflation, the unemployment rate, "
            "CBO's noncyclical rate, the HLW r* and the effective funds rate (and, "
            "for the first-difference rule, unemployment and the natural rate four "
            "quarters back); us_output_gap swaps in real GDP over CBO's potential "
            "GDP; us_sep reads the SEP medians for a meeting and year; us_spf the "
            "SPF's survey-quarter "
            "medians; ea, gb and ca each economy's inflation, OECD output gap, "
            "policy rate and, for ea and ca, the HLW r*."
        ),
    ),
    limitations=(
        (
            "A prescription is the rule's arithmetic, not a forecast of policy or "
            "advice: the rules leave out most of what a central bank weighs, and "
            "the neutral rate and natural unemployment are estimated with wide "
            "uncertainty."
        ),
        (
            "Taylor (1999) and the balanced approach share one formula; they are "
            "kept apart because the literature and the Board name them apart."
        ),
        (
            "A path holds the adjusted rule's shortfall fixed, and a "
            "first-difference path accumulates its changes, so it can drift far "
            "from any level a central bank would set."
        ),
        (
            "Only the default and us_output_gap profiles bind the first-difference "
            "rule's gap four quarters back; with any other, supply it."
        ),
        (
            "The gb profile binds no neutral rate, because the New York Fed "
            "publishes none for the United Kingdom: supply neutral_real_rate. The "
            "New York Fed's r* files keep no dated vintages, so an as-of bind reads "
            "them as revised data and says so."
        ),
    ),
    references=(
        _TAYLOR_1993,
        _TAYLOR_1999,
        _REIFSCHNEIDER,
        _ORPHANIDES,
        _MPR_2026,
        _MPR_2023,
    ),
    evidence=Evidence.PRACTITIONER,
    cost=CostClass.INSTANT,
    tags=(
        "taylor rule",
        "monetary policy",
        "policy rules",
        "federal funds rate",
        "effective lower bound",
    ),
    invariants=(
        Invariant(
            id="prescription_never_falls_as_inflation_rises",
            statement="With all else fixed, more inflation never lowers the rate.",
        ),
        Invariant(
            id="prescription_never_rises_with_unemployment",
            statement=(
                "With all else fixed, more unemployment (or a lower output gap) "
                "never raises the rate."
            ),
        ),
        Invariant(
            id="smoothing_zero_is_the_plain_rule",
            statement=(
                "With no smoothing the previous rate is ignored and the rule is "
                "its plain formula."
            ),
        ),
        Invariant(
            id="elb_floors_the_prescription",
            statement=(
                "With a lower bound the prescription is never below it, and equals "
                "the unconstrained rate whenever that is at or above it."
            ),
        ),
        Invariant(
            id="shortfalls_rule_never_exceeds_balanced_approach",
            statement=(
                "On the same inputs the shortfalls rule prescribes no more than "
                "the balanced approach."
            ),
        ),
        Invariant(
            id="path_agrees_with_the_scalar_rules",
            statement=(
                "Each horizon of a path is the scalar rule on that horizon's "
                "inputs, with the previous horizon's rate as the previous rate."
            ),
        ),
        Invariant(
            id="band_contains_the_central_path",
            statement=(
                "With forecasts ordered low, central, high, the band's edges hold "
                "the central path between them."
            ),
        ),
    ),
    examples=(
        Example(
            name="taylor_1993_on_unemployment",
            inputs={
                "calculation": "taylor_1993",
                "inflation": 0.03,
                "neutral_real_rate": 0.01,
                "unemployment": 0.043,
                "natural_unemployment": 0.042,
            },
            note="The Report's form: a weight of 1 on the unemployment gap.",
        ),
        Example(
            name="taylor_1999_on_the_output_gap",
            inputs={
                "calculation": "taylor_1999",
                "inflation": 0.025,
                "neutral_real_rate": 0.005,
                "output_gap": 0.01,
            },
        ),
        Example(
            name="balanced_approach_on_the_sep",
            inputs={
                "calculation": "balanced_approach",
                "inflation": 0.026,
                "neutral_nominal_rate": 0.03,
                "unemployment": 0.044,
                "natural_unemployment": 0.042,
            },
            note="A nominal neutral rate, as the SEP's longer-run funds rate gives.",
        ),
        Example(
            name="shortfalls_ignore_a_tight_labour_market",
            inputs={
                "calculation": "balanced_approach_shortfalls",
                "inflation": 0.02,
                "neutral_real_rate": 0.005,
                "unemployment": 0.035,
                "natural_unemployment": 0.042,
            },
        ),
        Example(
            name="adjusted_rule_after_the_lower_bound",
            inputs={
                "calculation": "adjusted_taylor_1993",
                "inflation": 0.02,
                "neutral_real_rate": 0.005,
                "unemployment": 0.05,
                "natural_unemployment": 0.042,
                "cumulative_shortfall": 0.01,
            },
        ),
        Example(
            name="first_difference",
            inputs={
                "calculation": "first_difference",
                "inflation": 0.03,
                "previous_rate": 0.0425,
                "unemployment": 0.042,
                "natural_unemployment": 0.042,
                "unemployment_lagged": 0.04,
            },
        ),
        Example(
            name="inertial_taylor_1999",
            inputs={
                "calculation": "taylor_1999",
                "inflation": 0.03,
                "neutral_real_rate": 0.01,
                "output_gap": 0.005,
                "smoothing": 0.85,
                "previous_rate": 0.0375,
                "lower_bound": 0.00125,
            },
        ),
        Example(
            name="fan_chart_over_a_forecast",
            inputs={
                "calculation": "path",
                "rule": "taylor_1993",
                "neutral_real_rate": 0.01,
                "inflation_path": [0.03, 0.028, 0.026, 0.024, 0.022],
                "inflation_low_path": [0.027, 0.024, 0.022, 0.02, 0.019],
                "inflation_high_path": [0.033, 0.032, 0.03, 0.028, 0.026],
                "output_gap_path": [0.01, 0.008, 0.006, 0.004, 0.002],
                "output_gap_low_path": [0.005, 0.002, 0.0, -0.002, -0.003],
                "output_gap_high_path": [0.015, 0.013, 0.011, 0.009, 0.007],
            },
            note="A central forecast with its interquartile range: the fan chart.",
        ),
    ),
    charts=(
        ChartSpec(
            id="fan_chart",
            title="Prescribed policy rate over the forecast",
            kind=ChartKind.BAND,
            x="horizon",
            y=("lower_path", "upper_path", "prescribed_path"),
            x_label="Quarters ahead",
            y_label="Policy rate (decimal)",
            calculation="path",
        ),
    ),
    bindings=_RULE_BINDINGS,
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def policy_rule(inputs: PolicyRuleInputs) -> PolicyRuleOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], PolicyRuleOutputs]]] = {
    **dict.fromkeys(_LEVELS, _level),
    FirstDifferenceInputs: _first_difference,
    PathInputs: _path_of,
}
