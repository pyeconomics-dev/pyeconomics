# tests/registry/test_spec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The specification classes and the ``@model`` decorator."""

from __future__ import annotations

import dataclasses
from typing import Annotated, Any

import pytest
import toy_models as tm
from pydantic import Field

from pyeconomics import registry
from pyeconomics.core import (
    DOMAINS,
    Alias,
    Binding,
    ChangelogEntry,
    ChartKind,
    ChartSpec,
    CostClass,
    Evidence,
    Example,
    Invariant,
    Model,
    ModelInputs,
    ModelSpec,
    Reference,
    model,
)
from pyeconomics.core.spec import (
    MODEL_ID,
    SNAKE_CASE,
    union_discriminator,
    union_members,
)


def spec(**changes: Any) -> ModelSpec:  # noqa: ANN401 - forwards to dataclasses.replace
    return dataclasses.replace(tm.zero_coupon.spec, **changes)


def test_there_are_fifteen_distinct_domains() -> None:
    assert len(DOMAINS) == len(set(DOMAINS)) == 15
    assert DOMAINS[0] == "foundations"
    assert all(SNAKE_CASE.fullmatch(domain) for domain in DOMAINS)


def test_the_evidence_statuses_and_cost_classes() -> None:
    assert [e.value for e in Evidence] == [
        "standard",
        "practitioner",
        "contested",
        "rejected",
        "historical",
    ]
    assert [c.value for c in CostClass] == ["instant", "light", "heavy"]
    assert [k.value for k in ChartKind] == ["line", "bar", "scatter"]


@pytest.mark.parametrize(
    ("model_id", "valid"),
    [
        ("fixed_income.duration", True),
        ("fixed_income.duration.macaulay", True),
        ("fixed_income", False),
        ("fixed_income.a.b.c", False),
        ("Fixed.duration", False),
        ("fixed income.duration", False),
        ("fixed_income.1duration", False),
        ("fixed_income.", False),
        ("", False),
    ],
)
def test_the_id_pattern(model_id: str, valid: bool) -> None:  # noqa: FBT001
    assert bool(MODEL_ID.fullmatch(model_id)) is valid


def test_the_domain_comes_from_the_id() -> None:
    assert tm.zero_coupon.spec.domain == "fixed_income"
    assert spec(id="nodot").domain == "nodot"


def test_a_specification_is_frozen() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        tm.zero_coupon.spec.title = "Other"  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        tm.FISHER.key = "other"  # type: ignore[misc]


def test_sequences_are_held_as_tuples() -> None:
    built = spec(
        formula=["a", "b"],
        tags=["x"],
        examples=[tm.zero_coupon.spec.examples[0]],
        bindings=[],
    )
    assert built.formula == ("a", "b")
    assert built.tags == ("x",)
    assert isinstance(built.examples, tuple)
    assert built.bindings == ()


def test_bindings_are_held_as_a_tuple_of_binding_declarations() -> None:
    binding = Binding("rate", "us.unemployment.rate")
    assert spec(bindings=[binding]).bindings == (binding,)


def test_a_lone_string_is_one_item_not_a_tuple_of_characters() -> None:
    assert spec(formula="E = mc^2").formula == ("E = mc^2",)


def test_aliases_may_be_strings_or_alias_objects() -> None:
    built = spec(aliases=["fixed_income.old", Alias("fixed_income.older", "3.0.0")])
    assert built.aliases == (
        Alias("fixed_income.old", "2.0.0"),
        Alias("fixed_income.older", "3.0.0"),
    )
    assert spec(aliases="fixed_income.old").aliases == (Alias("fixed_income.old"),)


def test_an_example_keeps_a_read_only_copy_of_its_inputs() -> None:
    inputs = {"face_value": 100, "rate": 0.05, "years": 10}
    example = Example(name="copy", inputs=inputs)
    inputs["rate"] = 0.9
    assert example.inputs["rate"] == 0.05
    with pytest.raises(TypeError):
        example.inputs["rate"] = 0.9  # type: ignore[index]
    assert dataclasses.replace(example, note="n").inputs == example.inputs


def test_nothing_is_checked_when_a_specification_is_built() -> None:
    bare = ModelSpec(id="", version=0, title="", summary="", inputs=int, outputs=int)
    assert bare.evidence is None
    assert bare.cost is None
    assert bare.no_invariants_reason is None
    assert bare.bindings == ()
    assert bare.aliases == ()


def test_input_and_output_models_of_a_union() -> None:
    assert tm.zero_coupon.spec.input_models == (tm.ZeroCouponInputs,)
    assert tm.time_value.spec.input_models == (
        tm.PresentValueInputs,
        tm.FutureValueInputs,
    )
    assert tm.time_value.spec.output_models == (
        tm.PresentValueOutputs,
        tm.FutureValueOutputs,
    )


def test_union_helpers() -> None:
    discriminated = Annotated[int | str, Field(discriminator="kind")]
    assert union_members(discriminated) == (int, str)
    assert union_members(int) == (int,)
    assert union_discriminator(discriminated) == "kind"
    assert union_discriminator(Annotated[int, "note"]) is None
    assert union_discriminator(int | str) is None


def test_chart_and_reference_defaults() -> None:
    chart = ChartSpec(id="c", title="T", kind=ChartKind.LINE, x="a", y=("b",))
    assert chart.x_label is None
    assert chart.calculation is None
    reference = Reference(key="k", citation="c")
    assert (reference.doi, reference.url) == (None, None)
    assert (reference.locator, reference.isbn) == (None, None)
    assert ChangelogEntry(version=1, note="n").version == 1
    assert Invariant(id="i", statement="s").id == "i"


# --- the decorator -----------------------------------------------------------

COMMON: dict[str, Any] = {
    "id": "foundations.toy_decorated",
    "version": 1,
    "title": "Decorated",
    "summary": "A decorated function.",
    "formula": ["x"],
    "assumptions": ["a"],
    "limitations": ["l"],
    "references": [tm.FISHER],
    "evidence": Evidence.STANDARD,
    "cost": CostClass.INSTANT,
    "examples": [],
    "changelog": [ChangelogEntry(version=1, note="First.")],
}


def test_the_decorator_builds_the_spec_from_its_arguments_and_the_hints() -> None:
    @model(**COMMON, tags=["toy"], aliases=["foundations.old_name"], extra="toy")
    def decorated(inputs: tm.ZeroCouponInputs) -> tm.ZeroCouponOutputs:
        return tm.ZeroCouponOutputs(price=inputs.face_value)

    assert isinstance(decorated, Model)
    built = decorated.spec
    assert built.id == "foundations.toy_decorated"
    assert built.inputs is tm.ZeroCouponInputs
    assert built.outputs is tm.ZeroCouponOutputs
    assert built.tags == ("toy",)
    assert built.aliases == (Alias("foundations.old_name"),)
    assert built.extra == "toy"
    assert built.formula == ("x",)
    assert decorated(face_value=5, rate=0.1, years=1).price == 5


def test_decorating_has_no_global_side_effect() -> None:
    before = registry.ids()

    @model(**COMMON)
    def decorated(inputs: tm.ZeroCouponInputs) -> tm.ZeroCouponOutputs:
        return tm.ZeroCouponOutputs(price=inputs.face_value)

    assert decorated.id not in registry.ids()
    assert registry.ids() == before


def test_the_union_annotation_is_kept_whole() -> None:
    assert tm.time_value.spec.inputs == tm.TimeValueInputs
    assert union_discriminator(tm.time_value.spec.outputs) == "calculation"


def test_the_decorator_needs_one_positional_parameter() -> None:
    with pytest.raises(TypeError, match="exactly one positional parameter"):

        @model(**COMMON)  # type: ignore[arg-type]
        def two(a: tm.ZeroCouponInputs, b: int) -> tm.ZeroCouponOutputs:
            raise NotImplementedError

    with pytest.raises(TypeError, match="exactly one positional parameter"):

        @model(**COMMON)  # type: ignore[arg-type]
        def keyword_only(*, a: tm.ZeroCouponInputs) -> tm.ZeroCouponOutputs:
            raise NotImplementedError


def test_the_decorator_needs_type_hints() -> None:
    with pytest.raises(TypeError, match="needs type hints"):

        @model(**COMMON)
        def unhinted(inputs):  # type: ignore[no-untyped-def]  # noqa: ANN001, ANN202
            raise NotImplementedError

    with pytest.raises(TypeError, match="needs type hints"):

        @model(**COMMON)
        def no_return(inputs: tm.ZeroCouponInputs):  # type: ignore[no-untyped-def]  # noqa: ANN202
            raise NotImplementedError


def test_the_decorator_reports_a_hint_it_cannot_resolve() -> None:
    with pytest.raises(TypeError, match="cannot resolve the type hints"):

        @model(**COMMON)
        def forward(inputs: NotDefinedAnywhere) -> tm.ZeroCouponOutputs:  # type: ignore[name-defined]  # noqa: F821
            raise NotImplementedError


def test_a_model_without_a_valid_spec_still_builds_and_runs() -> None:
    class Open(ModelInputs):
        x: int = 0

    built: Model[Any, Any] = Model(
        spec(inputs=Open), lambda _inputs: tm.ZeroCouponOutputs(price=1.0)
    )
    assert built(x=1).price == 1.0
