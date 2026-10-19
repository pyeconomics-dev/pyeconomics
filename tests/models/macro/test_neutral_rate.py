# tests/models/macro/test_neutral_rate.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.neutral_rate``: its identities, its input rule and its warning."""

from __future__ import annotations

import math
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import InputError, run_model
from pyeconomics.models.macro import neutral_rate

REAL = st.floats(min_value=-0.1, max_value=0.1)
TARGETS = st.floats(min_value=0.0, max_value=0.1)
POLICY = st.floats(min_value=-0.1, max_value=1.0)
INFLATION = st.floats(min_value=-0.2, max_value=0.5)


@st.composite
def estimates(draw: st.DrawFn) -> dict[str, Any]:
    """One calculation's inputs and the real rate it should report."""
    calculation = draw(
        st.sampled_from(
            [
                "laubach_williams",
                "holston_laubach_williams",
                "sep_longer_run",
                "constant",
            ]
        )
    )
    target = draw(TARGETS)
    inputs: dict[str, Any] = {"calculation": calculation, "inflation_target": target}
    if calculation == "sep_longer_run":
        inputs["longer_run_policy_rate"] = draw(st.floats(min_value=0.0, max_value=0.2))
    elif calculation == "constant":
        inputs["real_rate"] = draw(REAL)
    else:
        prefix = "lw" if calculation == "laubach_williams" else "hlw"
        inputs[f"{prefix}_estimate"] = draw(REAL)
    return inputs


def run(**inputs: Any) -> Any:  # noqa: ANN401 - the calculation's outputs
    return run_model(neutral_rate, inputs).outputs


@pytest.mark.invariant("macro.neutral_rate", "nominal_is_real_plus_target")
@given(inputs=estimates())
def test_the_nominal_rate_is_the_real_rate_plus_the_target(
    inputs: dict[str, Any],
) -> None:
    outputs = run(**inputs)
    assert math.isclose(
        outputs.nominal_neutral_rate,
        outputs.real_neutral_rate + inputs["inflation_target"],
        rel_tol=1e-12,
        abs_tol=1e-15,
    )
    if inputs["calculation"] == "sep_longer_run":
        assert outputs.nominal_neutral_rate == inputs["longer_run_policy_rate"]


@pytest.mark.invariant("macro.neutral_rate", "policy_gap_is_the_real_rate_less_neutral")
@given(inputs=estimates(), policy=POLICY, inflation=INFLATION)
def test_the_policy_gap_is_the_real_policy_rate_less_neutral(
    inputs: dict[str, Any], policy: float, inflation: float
) -> None:
    outputs = run(**inputs, policy_rate=policy, inflation=inflation)
    expected = policy - inflation - outputs.real_neutral_rate
    assert math.isclose(outputs.real_policy_gap, expected, rel_tol=1e-12, abs_tol=1e-15)


def test_without_a_policy_rate_the_gap_is_undefined_and_says_so() -> None:
    result = run_model(neutral_rate, {"calculation": "constant", "real_rate": 0.005})
    assert result.outputs.real_policy_gap is None
    assert [w.code for w in result.warnings] == ["no_policy_gap"]


@pytest.mark.parametrize("given_", [{"policy_rate": 0.03}, {"inflation": 0.02}])
def test_a_policy_rate_needs_inflation_and_inflation_a_policy_rate(
    given_: dict[str, float],
) -> None:
    with pytest.raises(InputError, match="together"):
        run(calculation="holston_laubach_williams", hlw_estimate=0.01, **given_)


def test_the_sep_rate_less_the_target_is_r_star() -> None:
    outputs = run(
        calculation="sep_longer_run",
        longer_run_policy_rate=0.031,
        inflation_target=0.02,
    )
    assert math.isclose(outputs.real_neutral_rate, 0.011)
    assert outputs.nominal_neutral_rate == 0.031
