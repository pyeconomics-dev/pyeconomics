# src/pyeconomics/models/macro/neutral_rate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""The neutral rate of interest, r*: ``macro.neutral_rate``.

The real interest rate consistent with output at potential and stable inflation
cannot be observed; it is estimated. Four calculations, discriminated on
``calculation``, take an estimate and report it as a real and a nominal rate:

- ``laubach_williams`` and ``holston_laubach_williams``: the New York Fed's
  published one-sided estimate for an economy and quarter (Laubach and Williams
  2003; Holston, Laubach and Williams 2017), which a binding reads from the
  current file;
- ``sep_longer_run``: the FOMC's median longer-run federal funds rate less the
  inflation objective, :math:`r^* = i^{LR} - \pi^*`;
- ``constant``: a rate the caller chooses.

The nominal neutral rate is :math:`r^* + \pi^*`. Given a policy rate :math:`i` and
inflation :math:`\pi`, the real policy-rate gap is :math:`(i - \pi) - r^*`: above
zero, policy is tighter than neutral. Every rate is a decimal.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Final, Literal, Self

from pydantic import Field, model_validator

from pyeconomics.core import (
    Binding,
    ChangelogEntry,
    CostClass,
    Evidence,
    Example,
    Invariant,
    ModelInputs,
    ModelOutputs,
    Rate,
    Reference,
    model,
    warn,
)

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["neutral_rate"]

#: A real neutral rate, and the inflation objective.
_REAL_MIN: Final = -0.1
_REAL_MAX: Final = 0.1
_TARGET_MAX: Final = 0.1
#: The SEP's longer-run funds rate, a nominal rate.
_LONGER_RUN_MAX: Final = 0.2
#: A policy rate, and inflation.
_POLICY_MIN: Final = -0.1
_POLICY_MAX: Final = 1.0
_INFLATION_MIN: Final = -0.2
_INFLATION_MAX: Final = 0.5
#: The real neutral rate reaches 0.2 - 0 from the SEP and -0.1 - 0.1 below; the
#: nominal one 0.1 + 0.1; the real policy gap 1.0 + 0.2 + 0.2 at most.
_REAL_OUT_MIN: Final = -0.2
_REAL_OUT_MAX: Final = 0.2
_NOMINAL_OUT_MIN: Final = -0.1
_NOMINAL_OUT_MAX: Final = 0.2
_GAP_OUT: Final = 2.0


class _Neutral(ModelInputs):
    """What every calculation shares: the objective and an optional policy rate."""

    inflation_target: Rate = Field(
        0.02, ge=0.0, le=_TARGET_MAX, description="The inflation objective"
    )
    policy_rate: Rate | None = Field(
        None,
        ge=_POLICY_MIN,
        le=_POLICY_MAX,
        description="A nominal policy rate, to measure how far it is from neutral",
    )
    inflation: Rate | None = Field(
        None,
        ge=_INFLATION_MIN,
        le=_INFLATION_MAX,
        description="Inflation, which makes the policy rate a real rate",
    )

    @model_validator(mode="after")
    def _policy_rate_with_inflation(self) -> Self:
        if (self.policy_rate is None) != (self.inflation is None):
            msg = "give policy_rate and inflation together, or neither"
            raise ValueError(msg)
        return self


def _estimate(model_name: str) -> Any:  # noqa: ANN401 - pydantic's Field
    return Field(
        ge=_REAL_MIN,
        le=_REAL_MAX,
        description=(
            f"The New York Fed's published {model_name} estimate of r* for the "
            "economy and quarter"
        ),
    )


class LaubachWilliamsInputs(_Neutral):
    """A published Laubach-Williams (2003) estimate."""

    calculation: Literal["laubach_williams"] = Field(
        "laubach_williams", description="r* from the Laubach-Williams model"
    )
    lw_estimate: Rate = _estimate("Laubach-Williams")


class HolstonLaubachWilliamsInputs(_Neutral):
    """A published Holston-Laubach-Williams (2017) estimate."""

    calculation: Literal["holston_laubach_williams"] = Field(
        "holston_laubach_williams",
        description="r* from the Holston-Laubach-Williams model",
    )
    hlw_estimate: Rate = _estimate("Holston-Laubach-Williams")


class SepLongerRunInputs(_Neutral):
    """The FOMC's median longer-run federal funds rate."""

    calculation: Literal["sep_longer_run"] = Field(
        "sep_longer_run", description="r* implied by the SEP's longer-run rate"
    )
    longer_run_policy_rate: Rate = Field(
        ge=0.0,
        le=_LONGER_RUN_MAX,
        description="The SEP's median longer-run federal funds rate (nominal)",
    )


class ConstantInputs(_Neutral):
    """A neutral rate the caller chooses."""

    calculation: Literal["constant"] = Field(
        "constant", description="A constant real neutral rate"
    )
    real_rate: Rate = Field(
        ge=_REAL_MIN, le=_REAL_MAX, description="The real neutral rate to use"
    )


NeutralRateInputs = Annotated[
    LaubachWilliamsInputs
    | HolstonLaubachWilliamsInputs
    | SepLongerRunInputs
    | ConstantInputs,
    Field(discriminator="calculation"),
]


class _NeutralOutputs(ModelOutputs):
    real_neutral_rate: Rate = Field(
        ge=_REAL_OUT_MIN, le=_REAL_OUT_MAX, description="The real neutral rate, r*"
    )
    nominal_neutral_rate: Rate = Field(
        ge=_NOMINAL_OUT_MIN,
        le=_NOMINAL_OUT_MAX,
        description="The real neutral rate plus the inflation objective",
    )
    real_policy_gap: Rate | None = Field(
        ge=-_GAP_OUT,
        le=_GAP_OUT,
        description=(
            "The real policy rate (policy rate less inflation) less r*; None "
            "without a policy rate"
        ),
    )


class LaubachWilliamsOutputs(_NeutralOutputs):
    calculation: Literal["laubach_williams"] = Field(
        "laubach_williams", description="r* from the Laubach-Williams model"
    )


class HolstonLaubachWilliamsOutputs(_NeutralOutputs):
    calculation: Literal["holston_laubach_williams"] = Field(
        "holston_laubach_williams",
        description="r* from the Holston-Laubach-Williams model",
    )


class SepLongerRunOutputs(_NeutralOutputs):
    calculation: Literal["sep_longer_run"] = Field(
        "sep_longer_run", description="r* implied by the SEP's longer-run rate"
    )


class ConstantOutputs(_NeutralOutputs):
    calculation: Literal["constant"] = Field(
        "constant", description="A constant real neutral rate"
    )


NeutralRateOutputs = Annotated[
    LaubachWilliamsOutputs
    | HolstonLaubachWilliamsOutputs
    | SepLongerRunOutputs
    | ConstantOutputs,
    Field(discriminator="calculation"),
]


def _report(
    inputs: _Neutral, real: float, nominal: float | None = None
) -> dict[str, float | None]:
    """Return the rates: real, nominal and, with a policy rate, the real gap."""
    gap = None
    if inputs.policy_rate is None or inputs.inflation is None:
        warn(
            "no_policy_gap",
            "the real policy-rate gap needs a policy rate and inflation",
        )
    else:
        gap = inputs.policy_rate - inputs.inflation - real
    return {
        "real_neutral_rate": real,
        "nominal_neutral_rate": real + inputs.inflation_target
        if nominal is None
        else nominal,
        "real_policy_gap": gap,
    }


def _laubach_williams(inputs: LaubachWilliamsInputs) -> LaubachWilliamsOutputs:
    return LaubachWilliamsOutputs.model_validate(_report(inputs, inputs.lw_estimate))


def _holston(
    inputs: HolstonLaubachWilliamsInputs,
) -> HolstonLaubachWilliamsOutputs:
    return HolstonLaubachWilliamsOutputs.model_validate(
        _report(inputs, inputs.hlw_estimate)
    )


def _sep(inputs: SepLongerRunInputs) -> SepLongerRunOutputs:
    real = inputs.longer_run_policy_rate - inputs.inflation_target
    return SepLongerRunOutputs.model_validate(
        _report(inputs, real, inputs.longer_run_policy_rate)
    )


def _constant(inputs: ConstantInputs) -> ConstantOutputs:
    return ConstantOutputs.model_validate(_report(inputs, inputs.real_rate))


_LW = Reference(
    key="laubach2003",
    citation=(
        "Laubach, T. and Williams, J. C. (2003). Measuring the Natural Rate of "
        "Interest. Review of Economics and Statistics, 85(4), 1063-1070."
    ),
    doi="10.1162/003465303772815934",
    locator="The state-space model of r*, trend growth and the output gap",
)
_HLW = Reference(
    key="holston2017",
    citation=(
        "Holston, K., Laubach, T. and Williams, J. C. (2017). Measuring the "
        "Natural Rate of Interest: International Trends and Determinants. Journal "
        "of International Economics, 108, S59-S75."
    ),
    doi="10.1016/j.jinteco.2017.01.004",
    locator="The model estimated for the United States, Canada and the euro area",
)
_NYFED = Reference(
    key="nyfed_rstar",
    citation=(
        "Federal Reserve Bank of New York. Measuring the Natural Rate of Interest: "
        "the Laubach-Williams and Holston-Laubach-Williams current estimates."
    ),
    url="https://www.newyorkfed.org/research/policy/rstar",
    locator="The current-estimates files, one-sided r* by quarter",
)
_SEP = Reference(
    key="fomc_sep",
    citation=(
        "Board of Governors of the Federal Reserve System. Summary of Economic "
        "Projections, released after each FOMC meeting with projections."
    ),
    url="https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
    locator="Table 1: the median federal funds rate in the longer run",
)


@model(
    id="macro.neutral_rate",
    version=1,
    title="Neutral rate of interest",
    summary=(
        "r* from the New York Fed's Laubach-Williams and Holston-Laubach-Williams "
        "estimates, the SEP's longer-run rate or a constant, as real and nominal "
        "rates, with the real policy-rate gap."
    ),
    formula=(
        (
            r"r^* = \hat r^*_{LW} \text{ or } \hat r^*_{HLW}, \quad "
            r"r^* = i^{LR}_{SEP} - \pi^*"
        ),
        r"i^* = r^* + \pi^*, \quad \text{gap} = (i - \pi) - r^*",
    ),
    assumptions=(
        (
            "Estimates are the New York Fed's one-sided ones, as it publishes them "
            "for a quarter; the SEP's longer-run inflation is the 2 percent "
            "objective, so its implied r* is the longer-run rate less the target."
        ),
        (
            "The real policy rate is the simple difference of the policy rate and "
            "inflation, as the policy-rule literature uses it."
        ),
        (
            "Profiles: default binds the LW and HLW estimates for the United "
            "States (each calculation reads its own), the effective funds rate and "
            "core PCE inflation; us_sep the SEP's longer-run rate for a meeting; ea "
            "and ca the HLW estimate, policy rate and inflation of the euro area "
            "and Canada (the New York Fed publishes LW for the United States only)."
        ),
    ),
    limitations=(
        (
            "r* is not observed. Its estimates are uncertain, revised as data "
            "arrive, and differ by model by a percentage point or more; read the "
            "estimate as one view."
        ),
        (
            "The New York Fed's files keep no dated vintages, so a bind as of a "
            "past date reads the current estimates and labels them revised data."
        ),
        "Without a policy rate and inflation the real policy gap is None, and says so.",
    ),
    references=(_LW, _HLW, _NYFED, _SEP),
    evidence=Evidence.CONTESTED,
    cost=CostClass.INSTANT,
    tags=("r-star", "neutral rate", "natural rate of interest", "monetary policy"),
    invariants=(
        Invariant(
            id="nominal_is_real_plus_target",
            statement="The nominal neutral rate is the real one plus the objective.",
        ),
        Invariant(
            id="policy_gap_is_the_real_rate_less_neutral",
            statement=(
                "Given a policy rate and inflation, the gap is the policy rate "
                "less inflation less r*."
            ),
        ),
    ),
    examples=(
        Example(
            name="holston_laubach_williams",
            inputs={
                "calculation": "holston_laubach_williams",
                "hlw_estimate": 0.0101,
                "policy_rate": 0.0364,
                "inflation": 0.03,
            },
        ),
        Example(
            name="laubach_williams",
            inputs={"calculation": "laubach_williams", "lw_estimate": 0.0165},
        ),
        Example(
            name="sep_longer_run",
            inputs={"calculation": "sep_longer_run", "longer_run_policy_rate": 0.031},
        ),
        Example(
            name="constant", inputs={"calculation": "constant", "real_rate": 0.005}
        ),
    ),
    bindings=(
        # Each published estimate has its own field, so a calculation reads its
        # own model's r*: the default profile binds both US estimates.
        Binding("hlw_estimate", "us.neutral_rate.hlw"),
        Binding("lw_estimate", "us.neutral_rate.laubach_williams"),
        Binding("policy_rate", "us.policy_rate.effective"),
        Binding("inflation", "us.inflation.pce_core.yoy"),
        Binding(
            "longer_run_policy_rate", "us.sep.policy_rate_longer_run", profile="us_sep"
        ),
        Binding("policy_rate", "us.policy_rate.effective", profile="us_sep"),
        Binding("inflation", "us.inflation.pce_core.yoy", profile="us_sep"),
        Binding("hlw_estimate", "ea.neutral_rate.hlw", profile="ea"),
        Binding("policy_rate", "ea.policy_rate.headline", profile="ea"),
        Binding("inflation", "ea.inflation.hicp.yoy", profile="ea"),
        Binding("hlw_estimate", "ca.neutral_rate.hlw", profile="ca"),
        Binding("policy_rate", "ca.policy_rate.headline", profile="ca"),
        Binding("inflation", "ca.inflation.cpi.yoy", profile="ca"),
    ),
    changelog=(ChangelogEntry(version=1, note="First version."),),
)
def neutral_rate(inputs: NeutralRateInputs) -> NeutralRateOutputs:
    """Run the calculation the inputs select."""
    return _CALCULATIONS[type(inputs)](inputs)


_CALCULATIONS: Final[dict[type[ModelInputs], Callable[[Any], NeutralRateOutputs]]] = {
    LaubachWilliamsInputs: _laubach_williams,
    HolstonLaubachWilliamsInputs: _holston,
    SepLongerRunInputs: _sep,
    ConstantInputs: _constant,
}
