# tests/data/catalog/test_transform_names.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The transform vocabulary in core and the implementations in the catalog.

Core declares the names and parameter schemas as plain data so a binding can be
checked without importing the data layer; the catalog implements each. These
tests hold the two sets equal in both directions and hold the text form to one
canonical spelling.
"""

from __future__ import annotations

import datetime as dt

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import (
    TRANSFORM_NAMES,
    TRANSFORMS,
    InputError,
    canonical_transform,
    check_transform,
    format_transform,
    parse_transform,
)
from pyeconomics.data.catalog import transforms as impl


def test_core_and_the_catalog_name_the_same_transforms_in_both_directions() -> None:
    assert set(impl.IMPLEMENTATIONS) == set(TRANSFORMS) == set(TRANSFORM_NAMES)


def test_every_declared_group_is_one_of_four() -> None:
    assert {spec.group for spec in TRANSFORMS.values()} == {
        "change",
        "combine",
        "frequency",
        "alignment",
    }


def test_the_vocabulary_cannot_be_edited() -> None:
    with pytest.raises(TypeError):
        TRANSFORMS["x"] = TRANSFORMS["yoy"]  # type: ignore[index]


@pytest.mark.parametrize(
    ("text", "canonical"),
    [
        ("yoy", "yoy"),
        (" yoy ", "yoy"),
        ("pct_change(periods=1)", "pct_change"),
        ("pct_change(periods=4)", "pct_change(periods=4)"),
        ("diff()", "diff"),
        ("ratio(excess=false)", "ratio"),
        ("ratio(excess=true)", "ratio(excess=true)"),
        ("convert(method=mean, to=quarterly)", "convert(to=quarterly,method=mean)"),
        ("asof(date=2008-12-16)", "asof(date=2008-12-16)"),
        (
            "asof(max_age_days=5,date=2008-12-16)",
            "asof(date=2008-12-16,max_age_days=5)",
        ),
        ("window(date=2020-03-31,count=4)", "window(count=4,date=2020-03-31)"),
        ("align_to(max_age_days=0)", "align_to(max_age_days=0)"),
    ],
)
def test_one_transform_has_one_canonical_text(text: str, canonical: str) -> None:
    assert canonical_transform(text) == canonical
    assert canonical_transform(canonical) == canonical
    assert check_transform(text) == text


@pytest.mark.parametrize(
    "text",
    [
        "",
        "   ",
        "unknown",
        "yoy(periods=1)",
        "pct_change(periods=0)",
        "pct_change(periods=1001)",
        "pct_change(periods=1.5)",
        "pct_change(periods=true)",
        "pct_change(periods=1,periods=2)",
        "pct_change(periods)",
        "pct_change(=1)",
        "convert(to=quarterly)",
        "convert(to=weekly,method=mean)",
        "convert(to=quarterly,method=median)",
        "asof",
        "asof(date=2008-13-01)",
        "asof(date=1500-01-01)",
        "asof(date=2008-12-16,max_age_days=-1)",
        "asof(date=2008-12-16,max_age_days=40000)",
        "ratio(excess=1)",
        "log)(",
        "yoy(",
        "YoY",
        "a://b",
        "x" * 300,
    ],
)
def test_a_malformed_transform_is_refused(text: str) -> None:
    with pytest.raises(InputError):
        parse_transform(text)


def test_a_parsed_transform_carries_its_spec_and_defaults() -> None:
    parsed = parse_transform("pct_change")
    assert parsed.name == "pct_change"
    assert parsed.arguments == {"periods": 1}
    assert parsed.spec.operands == 1
    assert parse_transform("align_to").spec.operands == 2
    assert parse_transform("ratio").arguments == {"excess": False}


def test_format_transform_writes_the_canonical_text() -> None:
    assert format_transform("yoy") == "yoy"
    assert format_transform("pct_change", periods=4) == "pct_change(periods=4)"
    assert (
        format_transform("convert", method="last", to="annual")
        == "convert(to=annual,method=last)"
    )
    assert (
        format_transform("asof", date=dt.date(2008, 12, 16)) == "asof(date=2008-12-16)"
    )
    assert format_transform("ratio", excess=True) == "ratio(excess=true)"
    with pytest.raises(InputError):
        format_transform("nope")


_DATES = st.dates(min_value=dt.date(1700, 1, 1), max_value=dt.date(2200, 12, 31))


@st.composite
def _transform_text(draw: st.DrawFn) -> str:
    name = draw(st.sampled_from(sorted(TRANSFORMS)))
    spec = TRANSFORMS[name]
    pairs: list[str] = []
    for parameter in spec.parameters:
        if not parameter.required and draw(st.booleans()):
            continue
        if parameter.kind.value == "integer":
            value = str(draw(st.integers(parameter.minimum, parameter.maximum)))
        elif parameter.kind.value == "flag":
            value = draw(st.sampled_from(["true", "false"]))
        elif parameter.kind.value == "date":
            value = draw(_DATES).isoformat()
        else:
            value = draw(st.sampled_from(parameter.choices))
        pairs.append(f"{parameter.name}={value}")
    shuffled = draw(st.permutations(pairs))
    return name + (f"({', '.join(shuffled)})" if shuffled else "")


@given(_transform_text())
def test_canonical_text_is_a_fixed_point_and_keeps_every_argument(text: str) -> None:
    parsed = parse_transform(text)
    canonical = parsed.text()
    assert canonical_transform(canonical) == canonical
    assert parse_transform(canonical).arguments == parsed.arguments
