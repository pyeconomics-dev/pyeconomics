# tests/models/macro/test_policy_rule.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.policy_rule``: its invariants, its input rules and its warnings.

The golden file holds the published figures (the Board's formulas, the Atlanta
and Cleveland Feds'); ``test_legacy_parity.py`` holds 0.2.x. Here each declared
invariant has its property test, and each input rule a case that breaks it.
"""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from pyeconomics.core import InputError, run_model
from pyeconomics.models.macro import policy_rule

LEVEL = (
    "taylor_1993",
    "taylor_1999",
    "balanced_approach",
    "balanced_approach_shortfalls",
    "adjusted_taylor_1993",
)
RULES = (*LEVEL, "first_difference")

INFLATION = st.floats(min_value=-0.2, max_value=0.5)
GAPS = st.floats(min_value=-0.3, max_value=0.3)
RATES = st.floats(min_value=0.0, max_value=0.3)
NEUTRAL = st.floats(min_value=-0.1, max_value=0.1)
PREVIOUS = st.floats(min_value=-0.1, max_value=1.0)
WEIGHTS = st.floats(min_value=0.0, max_value=4.0)
SMOOTHING = st.floats(min_value=0.0, max_value=1.0)
BOUNDS = st.floats(min_value=-0.1, max_value=0.1)
OKUN = st.floats(min_value=0.1, max_value=4.0)


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(policy_rule, inputs).outputs


def warnings_of(**inputs: Any) -> list[str]:  # noqa: ANN401 - field values
    return [w.code for w in run_model(policy_rule, inputs).warnings]


def rule_inputs(rule: str, **given: Any) -> dict[str, Any]:  # noqa: ANN401
    """A rule's inputs: a neutral rate for a level rule, lagged values for FD."""
    inputs: dict[str, Any] = {"calculation": rule, **given}
    if rule == "first_difference":
        inputs.setdefault("previous_rate", 0.03)
        if "output_gap" in inputs:
            inputs.setdefault("output_gap_lagged", 0.0)
        else:
            inputs.setdefault("unemployment_lagged", 0.045)
    else:
        inputs.setdefault("neutral_real_rate", 0.005)
    return inputs


@st.composite
def settings(draw: st.DrawFn) -> dict[str, Any]:
    """The weights, smoothing and bound a property holds across."""
    drawn: dict[str, Any] = {
        "inflation_target": draw(st.floats(min_value=0.0, max_value=0.1)),
        "inflation_weight": draw(WEIGHTS),
        "resource_weight": draw(WEIGHTS),
        "okun_coefficient": draw(OKUN),
        "smoothing": draw(SMOOTHING),
        "previous_rate": draw(PREVIOUS),
    }
    if draw(st.booleans()):
        drawn["lower_bound"] = draw(BOUNDS)
    return drawn


# --- invariants ---------------------------------------------------------------


@pytest.mark.invariant(
    "macro.policy_rule", "prescription_never_falls_as_inflation_rises"
)
@given(
    rule=st.sampled_from(RULES),
    low=INFLATION,
    high=INFLATION,
    gap=GAPS,
    chosen=settings(),
)
def test_more_inflation_never_lowers_the_rate(
    rule: str, low: float, high: float, gap: float, chosen: dict[str, Any]
) -> None:
    low, high = sorted((low, high))
    first = run(**rule_inputs(rule, inflation=low, output_gap=gap, **chosen))
    second = run(**rule_inputs(rule, inflation=high, output_gap=gap, **chosen))
    assert second.prescribed_rate >= first.prescribed_rate - 1e-15


@pytest.mark.invariant(
    "macro.policy_rule", "prescription_never_rises_with_unemployment"
)
@given(
    rule=st.sampled_from(RULES),
    low=RATES,
    high=RATES,
    natural=RATES,
    weak=GAPS,
    strong=GAPS,
    chosen=settings(),
)
def test_more_unemployment_never_raises_the_rate(  # noqa: PLR0913, PLR0917 - two measures
    rule: str,
    low: float,
    high: float,
    natural: float,
    weak: float,
    strong: float,
    chosen: dict[str, Any],
) -> None:
    low, high = sorted((low, high))
    common = {"inflation": 0.03, "natural_unemployment": natural, **chosen}
    tight = run(**rule_inputs(rule, unemployment=low, **common))
    slack = run(**rule_inputs(rule, unemployment=high, **common))
    assert slack.prescribed_rate <= tight.prescribed_rate + 1e-15
    weak, strong = sorted((weak, strong))
    below = run(**rule_inputs(rule, inflation=0.03, output_gap=weak, **chosen))
    above = run(**rule_inputs(rule, inflation=0.03, output_gap=strong, **chosen))
    assert below.prescribed_rate <= above.prescribed_rate + 1e-15


def _plain(rule: str, inputs: dict[str, Any]) -> float:
    """The rule's own formula, written out independently of the model."""
    gap = inputs["output_gap"]
    pi, target = inputs["inflation"], inputs.get("inflation_target", 0.02)
    alpha = inputs.get("inflation_weight", 0.5)
    beta = inputs.get(
        "resource_weight",
        0.5 if rule in {"taylor_1993", "adjusted_taylor_1993"} else 1.0,
    )
    if rule == "balanced_approach_shortfalls":
        gap = min(gap, 0.0)
    rate = inputs["neutral_real_rate"] + pi + alpha * (pi - target) + beta * gap
    return float(rate - inputs.get("cumulative_shortfall", 0.0))


@pytest.mark.invariant("macro.policy_rule", "smoothing_zero_is_the_plain_rule")
@given(
    rule=st.sampled_from(LEVEL),
    inflation=INFLATION,
    gap=GAPS,
    neutral=NEUTRAL,
    first=PREVIOUS,
    second=PREVIOUS,
    alpha=WEIGHTS,
    beta=WEIGHTS,
)
def test_no_smoothing_ignores_the_previous_rate(  # noqa: PLR0913, PLR0917 - the formula's terms
    rule: str,
    inflation: float,
    gap: float,
    neutral: float,
    first: float,
    second: float,
    alpha: float,
    beta: float,
) -> None:
    inputs: dict[str, Any] = {
        "calculation": rule,
        "inflation": inflation,
        "output_gap": gap,
        "neutral_real_rate": neutral,
        "inflation_weight": alpha,
        "resource_weight": beta,
        "lower_bound": None,
    }
    one = run(**inputs, previous_rate=first)
    two = run(**inputs, previous_rate=second)
    assert one == two
    assert math.isclose(
        one.prescribed_rate, _plain(rule, inputs), rel_tol=1e-12, abs_tol=1e-15
    )


@pytest.mark.invariant("macro.policy_rule", "elb_floors_the_prescription")
@given(
    rule=st.sampled_from(RULES),
    inflation=INFLATION,
    gap=GAPS,
    bound=BOUNDS,
    chosen=settings(),
)
def test_the_lower_bound_floors_the_prescription(
    rule: str, inflation: float, gap: float, bound: float, chosen: dict[str, Any]
) -> None:
    chosen = {**chosen, "lower_bound": bound}
    outputs = run(**rule_inputs(rule, inflation=inflation, output_gap=gap, **chosen))
    assert outputs.prescribed_rate >= bound
    if outputs.unconstrained_rate >= bound:
        assert outputs.prescribed_rate == outputs.unconstrained_rate
    else:
        assert outputs.prescribed_rate == bound


@pytest.mark.invariant(
    "macro.policy_rule", "shortfalls_rule_never_exceeds_balanced_approach"
)
@given(
    inflation=INFLATION,
    unemployment=RATES,
    natural=RATES,
    neutral=NEUTRAL,
    chosen=settings(),
)
def test_the_shortfalls_rule_never_exceeds_the_balanced_approach(
    inflation: float,
    unemployment: float,
    natural: float,
    neutral: float,
    chosen: dict[str, Any],
) -> None:
    common = {
        "inflation": inflation,
        "unemployment": unemployment,
        "natural_unemployment": natural,
        "neutral_real_rate": neutral,
        **chosen,
    }
    balanced = run(calculation="balanced_approach", **common)
    shortfalls = run(calculation="balanced_approach_shortfalls", **common)
    assert shortfalls.prescribed_rate <= balanced.prescribed_rate + 1e-15


@st.composite
def paths(draw: st.DrawFn) -> dict[str, Any]:
    """A path's inputs: equal-length forecasts and what its rule needs."""
    rule = draw(st.sampled_from(RULES))
    size = draw(st.integers(min_value=1, max_value=8))
    drawn: dict[str, Any] = {
        "calculation": "path",
        "rule": rule,
        "inflation_path": draw(st.lists(INFLATION, min_size=size, max_size=size)),
        "output_gap_path": draw(st.lists(GAPS, min_size=size, max_size=size)),
        "smoothing": draw(SMOOTHING),
        "previous_rate": draw(PREVIOUS),
        "inflation_weight": draw(WEIGHTS),
    }
    if draw(st.booleans()):
        drawn["lower_bound"] = draw(BOUNDS)
    if rule == "first_difference":
        drawn["output_gap_lagged_path"] = draw(
            st.lists(GAPS, min_size=size, max_size=size)
        )
    else:
        drawn["neutral_real_rate"] = draw(NEUTRAL)
    if rule == "adjusted_taylor_1993":
        drawn["cumulative_shortfall"] = draw(st.floats(min_value=0.0, max_value=0.05))
    return drawn


@pytest.mark.invariant("macro.policy_rule", "path_agrees_with_the_scalar_rules")
@given(inputs=paths())
def test_each_horizon_of_a_path_is_the_scalar_rule(inputs: dict[str, Any]) -> None:
    outputs = run(**inputs)
    rule = inputs["rule"]
    previous = inputs["previous_rate"]
    # A scalar rule takes a previous rate from -10% to 100%; a path may leave that
    # range (50% inflation at a weight of 2), where no scalar run can follow it.
    assume(all(-0.1 <= rate <= 1.0 for rate in outputs.prescribed_path[:-1]))
    for h, prescribed in enumerate(outputs.prescribed_path):
        scalar: dict[str, Any] = {
            "calculation": rule,
            "inflation": inputs["inflation_path"][h],
            "output_gap": inputs["output_gap_path"][h],
            "smoothing": inputs["smoothing"],
            "previous_rate": previous,
            "inflation_weight": inputs["inflation_weight"],
        }
        if "lower_bound" in inputs:
            scalar["lower_bound"] = inputs["lower_bound"]
        if rule == "first_difference":
            scalar["output_gap_lagged"] = inputs["output_gap_lagged_path"][h]
        else:
            scalar["neutral_real_rate"] = inputs["neutral_real_rate"]
        if rule == "adjusted_taylor_1993":
            scalar["cumulative_shortfall"] = inputs["cumulative_shortfall"]
        expected = run(**scalar)
        assert prescribed == expected.prescribed_rate
        assert outputs.unconstrained_path[h] == expected.unconstrained_rate
        previous = prescribed
    assert outputs.horizon == tuple(range(len(inputs["inflation_path"])))


@pytest.mark.invariant("macro.policy_rule", "band_contains_the_central_path")
@given(
    inputs=paths(),
    spreads=st.lists(
        st.tuples(
            st.floats(min_value=0.0, max_value=0.02),
            st.floats(min_value=0.0, max_value=0.02),
        ),
        min_size=8,
        max_size=8,
    ),
)
def test_the_band_holds_the_central_path(
    inputs: dict[str, Any], spreads: list[tuple[float, float]]
) -> None:
    central = inputs["inflation_path"]
    gaps = inputs["output_gap_path"]
    inputs["inflation_low_path"] = [
        max(p - s, -0.2)
        for p, (s, _) in zip(central, spreads[: len(central)], strict=True)
    ]
    inputs["inflation_high_path"] = [
        min(p + s, 0.5)
        for p, (_, s) in zip(central, spreads[: len(central)], strict=True)
    ]
    inputs["output_gap_low_path"] = [
        max(g - s, -0.3) for g, (s, _) in zip(gaps, spreads[: len(gaps)], strict=True)
    ]
    inputs["output_gap_high_path"] = [
        min(g + s, 0.3) for g, (_, s) in zip(gaps, spreads[: len(gaps)], strict=True)
    ]
    outputs = run(**inputs)
    for low, middle, high in zip(
        outputs.lower_path, outputs.prescribed_path, outputs.upper_path, strict=True
    ):
        assert low <= middle + 1e-15
        assert middle <= high + 1e-15


# --- the rules' arithmetic ------------------------------------------------------


def test_the_unemployment_form_is_the_okun_scaled_output_form() -> None:
    by_unemployment = run(
        calculation="taylor_1993",
        inflation=0.03,
        neutral_real_rate=0.01,
        unemployment=0.04,
        natural_unemployment=0.045,
        okun_coefficient=2.0,
    )
    by_output = run(
        calculation="taylor_1993",
        inflation=0.03,
        neutral_real_rate=0.01,
        output_gap=0.01,
    )
    assert math.isclose(by_unemployment.prescribed_rate, by_output.prescribed_rate)


def test_taylor_1999_and_the_balanced_approach_share_a_formula() -> None:
    common = {"inflation": 0.031, "neutral_real_rate": 0.008, "output_gap": -0.012}
    taylor = run(calculation="taylor_1999", **common)
    balanced = run(calculation="balanced_approach", **common)
    assert taylor.prescribed_rate == balanced.prescribed_rate


def test_a_nominal_neutral_rate_is_the_real_one_plus_the_target() -> None:
    common = {"inflation": 0.03, "output_gap": 0.0, "inflation_target": 0.02}
    real = run(calculation="taylor_1993", neutral_real_rate=0.011, **common)
    nominal = run(calculation="taylor_1993", neutral_nominal_rate=0.031, **common)
    assert math.isclose(real.prescribed_rate, nominal.prescribed_rate, abs_tol=1e-15)
    assert nominal.nominal_neutral_rate == 0.031


def test_the_first_difference_rule_reads_the_current_natural_rate_by_default() -> None:
    common = {
        "calculation": "first_difference",
        "inflation": 0.02,
        "previous_rate": 0.03,
        "unemployment": 0.05,
        "natural_unemployment": 0.04,
        "unemployment_lagged": 0.045,
    }
    implicit = run(**common)
    explicit = run(**common, natural_unemployment_lagged=0.04)
    assert implicit == explicit
    assert math.isclose(implicit.prescribed_rate, 0.03 - 0.005, abs_tol=1e-15)


def test_smoothing_one_holds_the_previous_rate() -> None:
    outputs = run(
        **rule_inputs(
            "taylor_1993",
            inflation=0.09,
            output_gap=0.02,
            smoothing=1.0,
            previous_rate=0.01,
        )
    )
    assert outputs.prescribed_rate == 0.01


def test_a_path_with_no_band_has_empty_edges() -> None:
    outputs = run(
        calculation="path",
        rule="balanced_approach",
        neutral_real_rate=0.005,
        inflation_path=[0.03, 0.025],
        unemployment_path=[0.04, 0.042],
        natural_unemployment_path=[0.042, 0.042],
    )
    assert outputs.lower_path == outputs.upper_path == ()
    assert len(outputs.prescribed_path) == 2


def test_a_band_on_unemployment_reads_high_unemployment_for_the_lower_edge() -> None:
    outputs = run(
        calculation="path",
        rule="taylor_1993",
        neutral_real_rate=0.005,
        inflation_path=[0.03],
        unemployment_path=[0.042],
        unemployment_low_path=[0.04],
        unemployment_high_path=[0.045],
        natural_unemployment_path=[0.042],
    )
    assert outputs.lower_path[0] < outputs.prescribed_path[0] < outputs.upper_path[0]


def test_the_adjusted_rule_floors_its_path_at_the_boards_bound() -> None:
    inputs = {
        "calculation": "path",
        "rule": "adjusted_taylor_1993",
        "neutral_real_rate": 0.005,
        "inflation_path": [0.0, 0.01],
        "output_gap_path": [-0.06, -0.04],
        "cumulative_shortfall": 0.02,
    }
    outputs = run(**inputs)
    assert outputs.prescribed_path == (0.00125, 0.00125)
    assert "elb_binding" in warnings_of(**inputs)


def test_a_first_difference_path_accumulates_its_changes() -> None:
    outputs = run(
        calculation="path",
        rule="first_difference",
        previous_rate=0.02,
        inflation_path=[0.03, 0.03, 0.03],
        output_gap_path=[0.0, 0.0, 0.0],
        output_gap_lagged_path=[0.0, 0.0, 0.0],
    )
    steps = [round(rate, 10) for rate in outputs.prescribed_path]
    assert steps == [0.025, 0.03, 0.035]


# --- warnings -------------------------------------------------------------------


def test_a_binding_lower_bound_warns() -> None:
    inputs = rule_inputs(
        "taylor_1993", inflation=-0.02, output_gap=-0.05, lower_bound=0.0
    )
    assert run(**inputs).prescribed_rate == 0.0
    assert warnings_of(**inputs) == ["elb_binding"]
    inputs = rule_inputs(
        "first_difference",
        inflation=-0.02,
        output_gap=-0.05,
        lower_bound=0.0,
        previous_rate=0.001,
    )
    assert warnings_of(**inputs) == ["elb_binding"]


def test_a_bound_that_does_not_bind_is_silent() -> None:
    inputs = rule_inputs("taylor_1993", inflation=0.03, output_gap=0.0, lower_bound=0.0)
    assert warnings_of(**inputs) == []


# --- input rules ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        (
            {"inflation": 0.02, "neutral_real_rate": 0.01},
            "give the resource gap once",
        ),
        (
            {
                "inflation": 0.02,
                "neutral_real_rate": 0.01,
                "output_gap": 0.0,
                "unemployment": 0.04,
                "natural_unemployment": 0.04,
            },
            "give the resource gap once",
        ),
        (
            {"inflation": 0.02, "neutral_real_rate": 0.01, "unemployment": 0.04},
            "together",
        ),
        (
            {
                "inflation": 0.02,
                "neutral_real_rate": 0.01,
                "gap_measure": "output",
                "unemployment": 0.04,
                "natural_unemployment": 0.04,
            },
            "gap_measure 'output'",
        ),
        (
            {
                "inflation": 0.02,
                "neutral_real_rate": 0.01,
                "gap_measure": "unemployment",
                "output_gap": 0.0,
            },
            "gap_measure 'unemployment'",
        ),
        ({"inflation": 0.02, "output_gap": 0.0}, "one of neutral_real_rate"),
        (
            {
                "inflation": 0.02,
                "output_gap": 0.0,
                "neutral_real_rate": 0.01,
                "neutral_nominal_rate": 0.03,
            },
            "one of neutral_real_rate",
        ),
        (
            {
                "inflation": 0.02,
                "output_gap": 0.0,
                "neutral_real_rate": 0.01,
                "smoothing": 0.5,
            },
            "smoothing needs previous_rate",
        ),
    ],
)
def test_a_level_rule_refuses_inputs_that_do_not_fit(
    inputs: dict[str, Any], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        run(calculation="taylor_1993", **inputs)


def test_the_explicit_gap_measures_are_accepted() -> None:
    run(
        calculation="taylor_1993",
        inflation=0.02,
        neutral_real_rate=0.0,
        gap_measure="output",
        output_gap=0.0,
    )
    run(
        calculation="taylor_1993",
        inflation=0.02,
        neutral_real_rate=0.0,
        gap_measure="unemployment",
        unemployment=0.04,
        natural_unemployment=0.04,
    )


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        ({"output_gap": 0.0}, "needs output_gap_lagged"),
        (
            {"output_gap": 0.0, "output_gap_lagged": 0.0, "unemployment_lagged": 0.04},
            "needs output_gap_lagged",
        ),
        (
            {"unemployment": 0.04, "natural_unemployment": 0.04},
            "needs unemployment_lagged",
        ),
        (
            {
                "unemployment": 0.04,
                "natural_unemployment": 0.04,
                "unemployment_lagged": 0.04,
                "output_gap_lagged": 0.0,
            },
            "needs unemployment_lagged",
        ),
    ],
)
def test_the_first_difference_rule_needs_the_gap_four_quarters_earlier(
    inputs: dict[str, Any], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        run(
            calculation="first_difference", inflation=0.02, previous_rate=0.03, **inputs
        )


PATH = {
    "calculation": "path",
    "rule": "taylor_1993",
    "neutral_real_rate": 0.005,
    "inflation_path": [0.03, 0.025],
    "output_gap_path": [0.0, 0.0],
}


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"output_gap_path": [0.0]}, "output_gap_path has 1 horizons"),
        ({"neutral_real_rate": None}, "needs one of neutral_real_rate"),
        (
            {
                "rule": "first_difference",
                "previous_rate": 0.03,
                "output_gap_lagged_path": [0.0, 0.0],
            },
            "uses no neutral rate",
        ),
        (
            {
                "rule": "first_difference",
                "neutral_real_rate": None,
                "output_gap_lagged_path": [0.0, 0.0],
            },
            "needs previous_rate",
        ),
        (
            {
                "rule": "first_difference",
                "neutral_real_rate": None,
                "previous_rate": 0.03,
            },
            "needs output_gap_lagged",
        ),
        ({"smoothing": 0.5}, "smoothing needs previous_rate"),
        ({"inflation_low_path": [0.02, 0.02]}, "together"),
        (
            {"inflation_low_path": [0.04, 0.02], "inflation_high_path": [0.05, 0.03]},
            "each horizon needs inflation_low_path",
        ),
        (
            {
                "unemployment_low_path": [0.04, 0.04],
                "unemployment_high_path": [0.05, 0.05],
            },
            "a band on the output gap",
        ),
    ],
)
def test_a_path_refuses_inputs_that_do_not_fit(
    changes: dict[str, Any], message: str
) -> None:
    inputs = {**PATH, **changes}
    inputs = {k: v for k, v in inputs.items() if v is not None}
    with pytest.raises(InputError, match=message):
        run(**inputs)


def test_a_path_on_unemployment_refuses_a_band_on_the_output_gap() -> None:
    with pytest.raises(InputError, match="a band on the unemployment gap"):
        run(
            calculation="path",
            rule="taylor_1993",
            neutral_real_rate=0.005,
            inflation_path=[0.03],
            unemployment_path=[0.04],
            natural_unemployment_path=[0.042],
            output_gap_low_path=[0.0],
            output_gap_high_path=[0.01],
        )


def test_every_rule_reads_its_published_weight_by_default() -> None:
    from pyeconomics.models.macro.policy_rule import RESOURCE_WEIGHTS  # noqa: PLC0415

    for rule, weight in RESOURCE_WEIGHTS.items():
        inputs = rule_inputs(rule, inflation=0.02, output_gap=-0.01)
        outputs = run(**inputs)
        assert math.isclose(outputs.resource_gap_term, weight * -0.01)
        path = {
            "calculation": "path",
            "rule": rule,
            "inflation_path": [0.02],
            "output_gap_path": [-0.01],
            "previous_rate": 0.03,
        }
        if rule == "first_difference":
            path["output_gap_lagged_path"] = [0.0]
        else:
            path["neutral_real_rate"] = 0.005
        assert run(**path).prescribed_path[0] == outputs.prescribed_rate


def test_the_fan_chart_draws_the_band_and_the_central_path() -> None:
    example = next(
        e for e in policy_rule.spec.examples if e.name == "fan_chart_over_a_forecast"
    )
    figure = run_model(policy_rule, dict(example.inputs)).plot("fan_chart")
    lower, upper, central = figure.data
    assert upper.fill == "tonexty"
    assert list(central.x) == [0, 1, 2, 3, 4]
    assert all(a <= b <= c for a, b, c in zip(lower.y, central.y, upper.y, strict=True))
