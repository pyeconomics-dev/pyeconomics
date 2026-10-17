# tests/data/catalog/test_concept_shapes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The catalog's data classes refuse what would make a concept ambiguous.

A concept is permanent public vocabulary once released, so its shape is checked at
import: the id grammar, the tier order, the placeholders of a parameterised
series key, the transforms, and the columns of a table. Each refusal is shown
here on the smallest example.
"""

from __future__ import annotations

import datetime as dt

import pytest

from pyeconomics.core import InputError, UnitKind
from pyeconomics.core.transforms import (
    TransformParameter,
    TransformParameterKind,
    TransformSpec,
)
from pyeconomics.data import ObservationFrequency, SeasonalAdjustment, catalog
from pyeconomics.data.catalog import definitions as shapes
from pyeconomics.data.catalog.definitions import (
    MAX_CANDIDATES,
    Candidate,
    Concept,
    Derived,
    Operand,
    Parameter,
    Shape,
    Tier,
)


def concept(*candidates: Candidate | Derived, **fields: object) -> Concept:
    base: dict[str, object] = {
        "id": "us.toy.value",
        "title": "A toy",
        "definition": "A toy concept written to test the catalog's data classes.",
        "unit_kind": UnitKind.RATE,
        "frequency": ObservationFrequency.MONTHLY,
        "seasonal_adjustment": SeasonalAdjustment.NOT_APPLICABLE,
        "candidates": candidates or (Candidate(provider="alpha", series="A"),),
    }
    base.update(fields)
    return Concept(**base)  # type: ignore[arg-type]


def test_a_plain_concept_is_valid_and_exposes_its_originators() -> None:
    plain = concept(
        Candidate(provider="alpha", series="A"),
        Candidate(provider="beta", series="B", tier=Tier.AGGREGATOR),
    )
    assert [c.provider for c in plain.originators] == ["alpha"]  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "us",
        "us.toy",
        "Us.toy.value",
        "us.toy.value.a.b",
        "us.toy..value",
        "us.to y.v",
    ],
)
def test_a_concept_id_must_follow_the_grammar(bad: str) -> None:
    with pytest.raises(InputError, match="not a concept id"):
        concept(id=bad)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("title", "", "title"),
        ("definition", "x" * 1_001, "definition"),
        ("unit_text", "", "unit_text"),
        ("year_ends_in", 13, "year_ends_in"),
        ("year_ends_in", 0, "year_ends_in"),
        ("needs_window", "yes", "needs_window"),
        ("notes", ("",), "note"),
        ("shape", "tablet", "shape"),
        ("frequency", "hourly", "frequency"),
        ("seasonal_adjustment", "sometimes", "seasonal_adjustment"),
        ("unit_kind", "kilos", "unit_kind"),
    ],
)
def test_a_concepts_fields_are_checked(field: str, value: object, message: str) -> None:
    with pytest.raises(InputError, match=message):
        concept(**{field: value})


def test_only_a_table_may_leave_the_unit_kind_out() -> None:
    with pytest.raises(InputError, match="only a table concept"):
        concept(unit_kind=None)
    table = concept(
        Candidate(provider="alpha", series="A"), unit_kind=None, shape=Shape.TABLE
    )
    assert table.unit_kind is None


def test_candidates_are_counted_ordered_and_matched_to_parameters() -> None:
    with pytest.raises(InputError, match="lists 1 to"):
        concept(
            *[
                Candidate(provider="a", series=f"S{i}")
                for i in range(MAX_CANDIDATES + 1)
            ]
        )
    with pytest.raises(InputError, match="lists 1 to"):
        Concept(
            id="us.toy.value",
            title="t",
            definition="A concept with no candidate at all, which is refused.",
            unit_kind=UnitKind.RATE,
            frequency=ObservationFrequency.MONTHLY,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            candidates=(),
        )
    with pytest.raises(InputError, match="out of order"):
        concept(
            Candidate(provider="a", series="A", tier=Tier.AGGREGATOR),
            Candidate(provider="b", series="B", tier=Tier.ORIGINATOR),
        )
    with pytest.raises(InputError, match="a Candidate or a Derived"):
        concept("not a candidate")  # type: ignore[arg-type]
    meeting = Parameter(name="meeting", pattern=r"\d+", summary="n", example="1")
    with pytest.raises(InputError, match="differ"):
        concept(Candidate(provider="a", series="S{meeting}"))
    with pytest.raises(InputError, match="differ"):
        concept(Candidate(provider="a", series="S"), parameters=(meeting,))
    with pytest.raises(InputError, match="repeats a parameter"):
        concept(
            Candidate(provider="a", series="S{meeting}"), parameters=(meeting, meeting)
        )


def test_table_concepts_take_columns_and_never_a_derived_candidate() -> None:
    with pytest.raises(InputError, match="takes columns, not a column"):
        concept(
            Candidate(provider="a", series="T", column="x"),
            shape=Shape.TABLE,
            unit_kind=None,
        )
    derived = Derived(
        operands=(Operand("us.a.b"), Operand("us.c.d")), transform="ratio"
    )
    with pytest.raises(InputError, match="answers a series concept"):
        concept(derived, shape=Shape.TABLE, unit_kind=None)


@pytest.mark.parametrize(
    "fields",
    [
        {"provider": "Alpha", "series": "A"},
        {"provider": "a", "series": "http://x/y"},
        {"provider": "a", "series": "A", "column": "x", "keep": "y"},
        {"provider": "a", "series": "A", "column": "x", "columns": (("a", "b"),)},
        {"provider": "a", "series": "A", "keep": "("},
        {"provider": "a", "series": "A", "columns": ((" ", "b"),)},
        {"provider": "a", "series": "A", "columns": (("a", ""),)},
        {"provider": "a", "series": "A", "tier": "gold"},
        {"provider": "a", "series": "A", "delivers": "hourly"},
        {"provider": "a", "series": "A", "options": (("Bad", "x"),)},
        {"provider": "a", "series": "A", "options": (("good", 1.5),)},
        {"provider": "a", "series": "A", "transforms": ("nonsense",)},
        {"provider": "a", "series": "A", "transforms": ("ratio",)},
        {"provider": "a", "series": "A", "note": ""},
    ],
)
def test_a_candidate_is_checked(fields: dict[str, object]) -> None:
    with pytest.raises(InputError):
        Candidate(**fields)  # type: ignore[arg-type]


def test_a_candidate_canonicalises_its_transforms_and_names_its_placeholders() -> None:
    candidate = Candidate(
        provider="a",
        series="S:{meeting}:{year}",
        transforms=("convert(method=mean, to=quarterly)", "pct_change(periods=1)"),
        options=(("dataset", "x"), ("flag", True), ("count", 3)),
    )
    assert candidate.transforms == ("convert(to=quarterly,method=mean)", "pct_change")
    assert candidate.placeholders == {"meeting", "year"}


def test_a_derived_candidate_combines_exactly_two_concepts() -> None:
    ok = Derived(
        operands=(Operand("us.a.b", ("yoy",)), Operand("us.c.d")),
        transform="ratio( excess = true )".replace(" ", ""),
    )
    assert ok.transform == "ratio(excess=true)"
    assert ok.operands[0].transforms == ("yoy",)
    with pytest.raises(InputError, match="exactly two"):
        Derived(operands=(Operand("us.a.b"),), transform="ratio")
    with pytest.raises(InputError, match="does not combine two"):
        Derived(operands=(Operand("us.a.b"), Operand("us.c.d")), transform="yoy")
    with pytest.raises(InputError, match="not a concept id"):
        Operand("nope")
    with pytest.raises(InputError):
        Derived(
            operands=(Operand("us.a.b"), "us.c.d"),  # type: ignore[arg-type]
            transform="ratio",
        )


def test_a_parameter_checks_its_pattern_its_example_and_every_value() -> None:
    meeting = Parameter(
        name="meeting", pattern=r"\d{4}", summary="year", example="2026"
    )
    assert meeting.check("2026") == "2026"
    for bad in ("26", 2026, None, "2026 ", "2026\n"):
        with pytest.raises(InputError, match="must match"):
            meeting.check(bad)
    with pytest.raises(InputError, match="bad pattern"):
        Parameter(name="p", pattern="(", summary="s", example="x")
    with pytest.raises(InputError, match="does not match"):
        Parameter(name="p", pattern=r"\d", summary="s", example="x")
    with pytest.raises(InputError):
        Parameter(name="P", pattern=r".", summary="s", example="x")


def test_a_parameter_value_can_never_carry_a_brace_into_a_series_key() -> None:
    wide = Parameter(name="p", pattern=r".+", summary="anything", example="x")
    for bad in ("{x}", "a{b", "a}", "{}"):
        with pytest.raises(InputError, match="brace"):
            wide.check(bad)


def test_the_catalog_refuses_a_duplicate_concept_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Module:
        CONCEPTS = (concept(), concept())

    monkeypatch.setattr(catalog, "_MODULES", (Module,))
    with pytest.raises(ValueError, match="twice"):
        catalog._collect()  # noqa: SLF001 - the import-time collector


def test_the_shape_module_is_what_the_package_re_exports() -> None:
    assert catalog.Concept is shapes.Concept
    assert catalog.Candidate is shapes.Candidate
    assert catalog.Derived is shapes.Derived
    assert catalog.Tier is Tier


def test_transform_schemas_check_themselves() -> None:
    integer = TransformParameterKind.INTEGER
    choice = TransformParameterKind.CHOICE
    with pytest.raises(InputError, match="only a choice lists choices"):
        TransformParameter(name="p", kind=integer, summary="s", choices=("a",))
    with pytest.raises(InputError, match="only a choice lists choices"):
        TransformParameter(name="p", kind=choice, summary="s")
    with pytest.raises(InputError, match="no default"):
        TransformParameter(
            name="p", kind=integer, summary="s", required=True, default=1
        )
    with pytest.raises(InputError):
        TransformParameter(name="p", kind=integer, summary="s", default=0)
    with pytest.raises(InputError):
        TransformParameter(name="p", kind="decimal", summary="s")  # type: ignore[arg-type]
    with pytest.raises(InputError, match="snake_case"):
        TransformSpec(name="Bad", summary="s")
    parameter = TransformParameter(name="p", kind=integer, summary="s")
    with pytest.raises(InputError, match="repeats a parameter"):
        TransformSpec(name="ok", summary="s", parameters=(parameter, parameter))
    with pytest.raises(InputError, match="one or two series"):
        TransformSpec(name="ok", summary="s", operands=3)
    spec = TransformSpec(name="ok", summary="s")
    with pytest.raises(InputError, match="no parameter"):
        spec.parameter("missing")


def test_each_parameter_kind_checks_its_values() -> None:
    flag = TransformParameter(
        name="f", kind=TransformParameterKind.FLAG, summary="s", default=False
    )
    assert flag.check(value=True) is True
    for bad in (1, "true", None):
        with pytest.raises(InputError, match="true or false"):
            flag.check(bad)
    date = TransformParameter(name="d", kind=TransformParameterKind.DATE, summary="s")
    assert date.check(dt.date(2008, 12, 16)) == "2008-12-16"
    for bad in ("2008-12-1", 5, "1500-01-01"):
        with pytest.raises(InputError):
            date.check(bad)
    pick = TransformParameter(
        name="c", kind=TransformParameterKind.CHOICE, summary="s", choices=("a", "b")
    )
    assert pick.check("a") == "a"
    with pytest.raises(InputError, match="one of a, b"):
        pick.check("z")
    number = TransformParameter(
        name="n", kind=TransformParameterKind.INTEGER, summary="s", minimum=2, maximum=5
    )
    wrong: tuple[object, ...] = (1, 6, True, 2.5, "3")
    for value in wrong:
        with pytest.raises(InputError, match="whole number from 2 to 5"):
            number.check(value)
