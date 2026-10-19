# tests/data/bindings/test_validate_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``validate_bindings``: the checks that need the catalog, which core cannot make.

``registry.validate()`` holds a binding to its structural rules without reading
the catalog; this holds every registered model's bindings to the installed
catalog's concepts (ADR-0011 decision 16).
"""

from __future__ import annotations

from typing import Any

import bound_support as bs
import pytest
import toy_models as tm

from pyeconomics import data
from pyeconomics.core import AsOf, Binding, Registry, RegistryError


def registry_of_bound(*bindings: Binding, base: Any = tm.zero_coupon) -> Registry:  # noqa: ANN401
    return tm.toy_registry(tm.variant(base, bindings=bindings))


def failures(registry: Registry) -> list[str]:
    with pytest.raises(RegistryError) as caught:
        data.validate_bindings(registry)
    return list(caught.value.problems)


def test_the_installed_models_bindings_all_name_catalog_concepts() -> None:
    data.validate_bindings()


def test_the_toy_bound_models_pass() -> None:
    data.validate_bindings(bs.model_registry())


def test_a_concept_missing_from_the_catalog_is_named_with_the_closest() -> None:
    (problem,) = failures(registry_of_bound(Binding("rate", "us.unemployment.rat")))
    assert problem.startswith("fixed_income.toy_zero_coupon: [bindings] ")
    assert "binding 'rate' (profile 'default')" in problem
    assert "the catalog has no concept 'us.unemployment.rat'" in problem
    assert "did you mean 'us.unemployment.rate'?" in problem


def test_a_far_off_concept_gets_no_suggestion() -> None:
    (problem,) = failures(registry_of_bound(Binding("rate", "zz.qq.xx")))
    assert "no concept 'zz.qq.xx'" in problem
    assert "did you mean" not in problem


def test_a_table_concept_cannot_be_bound() -> None:
    (problem,) = failures(registry_of_bound(Binding("rate", "us.treasury.par_curve")))
    assert "us.treasury.par_curve is a table; a binding reads a series" in problem


def test_the_period_rule_needs_a_regular_concept() -> None:
    (problem,) = failures(
        registry_of_bound(
            Binding("rate", "us.policy_rate.target_upper", as_of=AsOf.PERIOD)
        )
    )
    assert "irregular and has no periods" in problem
    # The same concept is fine under the rule that reads the last observation.
    data.validate_bindings(
        registry_of_bound(Binding("rate", "us.policy_rate.target_upper"))
    )


def test_a_field_of_another_unit_kind_than_the_concept_is_refused() -> None:
    (problem,) = failures(registry_of_bound(Binding("years", "us.unemployment.rate")))
    assert "us.unemployment.rate is rate, but the field is years" in problem


def test_a_rate_concept_may_fill_a_ratio_field_and_a_transform_defers_the_check() -> (
    None
):
    # Rates and ratios are one dimensionless decimal; and after a transform the
    # unit kind is the transform's to say, so the check is made at bind time.
    data.validate_bindings(
        registry_of_bound(Binding("years", "us.unemployment.rate", transform="diff"))
    )


def test_every_bad_binding_of_every_model_is_listed_at_once() -> None:
    registry = tm.toy_registry(
        tm.variant(
            tm.zero_coupon,
            bindings=(Binding("rate", "no.such.concept"), Binding("years", "zz.qq.xx")),
        ),
        tm.variant(
            tm.mean_return,
            bindings=(Binding("returns", "also.not.there"),),
        ),
    )
    problems = failures(registry)
    assert len(problems) == 3
    assert {p.split(":")[0] for p in problems} == {
        "fixed_income.toy_zero_coupon",
        "foundations.toy_mean_return",
    }
    with pytest.raises(RegistryError, match=r"have 3 problems:\n"):
        data.validate_bindings(registry)


def test_a_single_problem_reads_in_the_singular() -> None:
    with pytest.raises(RegistryError, match=r"have 1 problem:\n"):
        data.validate_bindings(registry_of_bound(Binding("rate", "no.such.concept")))
