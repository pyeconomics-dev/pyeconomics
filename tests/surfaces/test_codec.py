# tests/surfaces/test_codec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The input codec: bounded, strict and typed by the model (ADR-0012 decision 10).

JSON text is refused above its size limit and its depth limit before it is parsed,
then parsed strictly; a mapping is checked for what canonical JSON cannot carry;
``field=value`` pairs are typed by the model's input schema, and a boolean never
stands in for a number (issue #75).
"""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
import toy_models as toys

from pyeconomics import registry
from pyeconomics.core import InputError
from pyeconomics.surfaces import codec
from pyeconomics.surfaces.codec import (
    MAX_INPUT_BYTES,
    MAX_INPUT_DEPTH,
    InputTooLargeError,
    decode,
    decode_json,
    decode_pairs,
)

BOND = "fixed_income.bond_pricing"


def nested(levels: int) -> str:
    """A JSON object whose value nests ``levels`` levels in all."""
    return '{"a": ' + "[" * (levels - 1) + "]" * (levels - 1) + "}"


# --- JSON text and bytes --------------------------------------------------------------


def test_json_text_bytes_and_a_bytearray_decode_alike() -> None:
    text = '{"rate": 0.05, "years": 10, "name": "café"}'
    expected = {"rate": 0.05, "years": 10, "name": "café"}
    assert decode(text) == expected
    assert decode(text.encode()) == expected
    assert decode(bytearray(text.encode())) == expected


def test_a_byte_order_mark_is_ignored() -> None:
    assert decode_json(b"\xef\xbb\xbf" + b'{"a": 1}') == {"a": 1}
    assert decode_json('﻿{"a": 1}') == {"a": 1}


def test_text_that_is_not_utf8_is_refused() -> None:
    with pytest.raises(InputError, match="not UTF-8"):
        decode_json(b'{"a": "\xff"}')


@pytest.mark.parametrize(
    "document",
    [b"x" * 11, "x" * 11, "é" * 6],
    ids=["bytes", "ascii-text", "non-ascii-text"],
)
def test_a_document_above_the_limit_is_refused_before_it_is_read(
    document: str | bytes,
) -> None:
    with pytest.raises(InputTooLargeError) as caught:
        decode_json(document, limit=10)
    assert caught.value.limit == 10
    assert caught.value.size > 10
    assert isinstance(caught.value, InputError)


def test_the_default_limit_admits_the_largest_valid_input() -> None:
    # factor_model_tests at full length with six significant digits: 2.65 MiB.
    returns = [[0.0123456] * 100] * 2520
    document = json.dumps({"returns": returns}).encode()
    assert len(document) > 2 * 1024 * 1024
    assert len(document) < MAX_INPUT_BYTES
    assert len(decode_json(document)["returns"]) == 2520  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


def test_nesting_at_the_limit_decodes_and_one_level_more_is_refused() -> None:
    assert decode_json(nested(MAX_INPUT_DEPTH))
    with pytest.raises(InputError, match=f"deeper than {MAX_INPUT_DEPTH} levels"):
        decode_json(nested(MAX_INPUT_DEPTH + 1))


def test_deep_nesting_is_refused_before_the_parser_sees_it(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def parse(*_args: object, **_kwargs: object) -> object:
        pytest.fail("the parser ran on over-deep text")

    monkeypatch.setattr(json, "loads", parse)
    with pytest.raises(InputError, match="deeper than"):
        decode_json("[" * 100_000)


def test_brackets_inside_strings_do_not_count_as_nesting() -> None:
    value = "[" * 100 + '"' + "{" * 100  # the quote is escaped in the JSON
    text = json.dumps({"a": value, "b": ["]]"]})
    assert decode_json(text) == {"a": value, "b": ["]]"]}


def test_an_unterminated_string_is_a_json_error_not_a_depth_error() -> None:
    with pytest.raises(InputError, match="not a JSON document"):
        decode_json('{"a": "' + "[" * 100)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        ('{"a": 1, "a": 2}', "repeat the key 'a'"),
        ('{"a": {"b": 1, "b": 2}}', "repeat the key 'b'"),
        ('{"a": NaN}', "NaN"),
        ('{"a": Infinity}', "Infinity"),
        ('{"a": -Infinity}', "-Infinity"),
        ('{"a": 1e999}', "not finite"),
        ('{"a": 9007199254740993}', "integer beyond"),
        ('{"a": "\\ud800"}', "lone surrogate"),
        ('{"\\udfff": 1}', "lone surrogate"),
        ("[1, 2]", "a JSON object, not list"),
        ('"text"', "a JSON object, not str"),
        ('{"a": }', "not a JSON document"),
        ("", "not a JSON document"),
    ],
)
def test_json_that_canonical_json_cannot_carry_is_refused(
    document: str, message: str
) -> None:
    with pytest.raises(InputError, match=message):
        decode_json(document)


def test_the_largest_exact_integer_is_accepted() -> None:
    assert decode_json('{"a": 9007199254740992, "b": -9007199254740992}') == {
        "a": 2**53,
        "b": -(2**53),
    }


def test_a_number_too_long_for_python_is_an_input_error() -> None:
    with pytest.raises(InputError, match="not a JSON document"):
        decode_json('{"a": ' + "9" * 5000 + "}")


# --- mappings -------------------------------------------------------------------------


def test_a_mapping_is_copied_and_other_values_pass_through() -> None:
    day = dt.date(2024, 1, 31)
    source = {"rate": 0.05, "when": day, "series": (1, 2.5)}
    decoded = decode(source)
    assert decoded == source
    assert decoded is not source


@pytest.mark.parametrize(
    ("inputs", "message"),
    [
        ({"a": float("nan")}, "not finite"),
        ({"a": [float("inf")]}, "not finite"),
        ({"a": 2**53 + 1}, "integer beyond"),
        ({"a": "\ud800"}, "lone surrogate"),
        ({1: "a"}, "an input name is text, not int"),
        ({"a": {2: "b"}}, "an input name is text, not int"),
    ],
)
def test_a_mapping_canonical_json_cannot_carry_is_refused(
    inputs: dict[Any, Any], message: str
) -> None:
    with pytest.raises(InputError, match=message):
        decode(inputs)


def test_a_booleans_and_large_floats_in_a_mapping_are_left_to_the_model() -> None:
    assert decode({"flag": True, "big": 1e300}) == {"flag": True, "big": 1e300}


def test_a_mapping_nested_too_deep_is_refused() -> None:
    value: object = []  # the mapping is level 1, so 31 lists reach the limit
    for _ in range(MAX_INPUT_DEPTH - 2):
        value = [value]
    assert decode({"a": value})
    with pytest.raises(InputError, match="deeper than"):
        decode({"a": [value]})


# --- what decode accepts --------------------------------------------------------------


def test_no_inputs_decode_to_an_empty_mapping() -> None:
    assert decode(None) == {}


def test_pairs_need_the_model() -> None:
    with pytest.raises(InputError, match="need the model"):
        decode(["rate=0.05"])


@pytest.mark.parametrize("inputs", [5, {1, 2}, object()])
def test_inputs_of_another_type_are_refused(inputs: object) -> None:
    with pytest.raises(InputError, match="not "):
        decode(inputs)


# --- field=value pairs ----------------------------------------------------------------


def test_pairs_are_typed_by_the_schema() -> None:
    model = toys.zero_coupon
    assert decode(["face_value=100", "rate=0.05", "years=10"], model) == {
        "face_value": 100,
        "rate": 0.05,
        "years": 10,
    }
    assert decode(("rate=-1.5e-2",), model) == {"rate": -0.015}


def test_a_boolean_is_refused_for_a_numeric_field() -> None:
    with pytest.raises(InputError, match="rate takes a number, not a boolean"):
        decode_pairs(toys.zero_coupon, ["rate=true"])


@pytest.mark.parametrize("text", ["five", "0x10", "NaN", "Infinity", "", "1,5"])
def test_text_that_is_not_a_json_number_is_refused_for_a_numeric_field(
    text: str,
) -> None:
    with pytest.raises(InputError, match="rate takes a number, not that text"):
        decode_pairs(toys.zero_coupon, [f"rate={text}"])


def test_a_number_that_overflows_is_refused() -> None:
    with pytest.raises(InputError, match="not finite"):
        decode_pairs(toys.zero_coupon, ["rate=1e999"])


def test_an_array_field_takes_a_json_literal() -> None:
    model = toys.mean_return
    assert decode_pairs(model, ["returns=[0.01, -0.02, 0]"]) == {
        "returns": [0.01, -0.02, 0]
    }
    with pytest.raises(InputError, match="returns takes array"):
        decode_pairs(model, ["returns=0.01,0.02"])
    with pytest.raises(InputError, match="deeper than 31 levels"):
        decode_pairs(model, ["returns=" + "[" * 32 + "]" * 32])


def test_a_family_takes_its_fields_from_the_calculation_named() -> None:
    decoded = decode_pairs(
        registry.get(BOND),
        [
            "calculation=price_from_yield",
            "settlement=2026-01-15",
            "maturity=2036-01-15",
            "coupon_rate=0.05",
            "yield_to_maturity=0.04",
            "frequency=annual",
            "end_of_month=false",
            "issue_date=null",
        ],
    )
    assert decoded == {
        "calculation": "price_from_yield",
        "settlement": "2026-01-15",
        "maturity": "2036-01-15",
        "coupon_rate": 0.05,
        "yield_to_maturity": 0.04,
        "frequency": "annual",
        "end_of_month": False,
        "issue_date": None,
    }
    assert registry.get(BOND).validate_inputs(decoded)


def test_a_family_needs_a_known_calculation() -> None:
    model = registry.get(BOND)
    with pytest.raises(InputError, match="several calculations; name one"):
        decode_pairs(model, ["coupon_rate=0.05"])
    with pytest.raises(InputError, match="no calculation of that name"):
        decode_pairs(model, ["calculation=price_to_yield"])


def test_a_boolean_field_takes_true_or_false_only() -> None:
    model = registry.get(BOND)
    with pytest.raises(InputError, match="end_of_month takes boolean"):
        decode_pairs(model, ["calculation=price_from_yield", "end_of_month=yes"])


def test_an_unknown_field_is_left_as_text_for_the_model_to_refuse() -> None:
    model = toys.zero_coupon
    decoded = decode_pairs(model, ["face_value=100", "colour=blue"])
    assert decoded == {"face_value": 100, "colour": "blue"}
    with pytest.raises(InputError):
        model.validate_inputs(decoded)


@pytest.mark.parametrize(
    ("pairs", "message"),
    [
        (["rate"], "input 1 is not written field=value"),
        (["years=1", "=0.05"], "input 2 is not written field=value"),
        (["1rate=0.05"], "input 1 is not written field=value"),
        (["rate=0.05", "rate=0.06"], "repeat the field 'rate'"),
        ([5], "input 1 is a int, not field=value text"),
        (["rate=\ud800"], "lone surrogate"),
    ],
)
def test_malformed_pairs_are_refused(pairs: list[object], message: str) -> None:
    with pytest.raises(InputError, match=message):
        decode_pairs(toys.zero_coupon, pairs)


def test_a_message_never_repeats_the_value() -> None:
    with pytest.raises(InputError) as caught:
        decode_pairs(toys.zero_coupon, ["rate=/home/someone/secret"])
    assert "someone" not in str(caught.value)


# --- the schema reader ----------------------------------------------------------------


def test_the_schema_reader_knows_type_lists_enums_and_foreign_refs() -> None:
    root: dict[str, Any] = {"$defs": {"Choice": {"enum": [1, 2.5, "x", True, None]}}}
    assert codec._kinds({"type": ["number", "null"]}, root) == {"number", "null"}  # noqa: SLF001
    assert codec._kinds({"$ref": "#/$defs/Choice"}, root) == {  # noqa: SLF001
        "integer",
        "number",
        "string",
        "boolean",
        "null",
    }
    assert codec._kinds({"const": "a"}, root) == {"string"}  # noqa: SLF001
    foreign = {"$ref": "https://example.org/schema"}
    assert codec._resolve(foreign, root) is foreign  # noqa: SLF001
    assert codec._kinds(foreign, root) == set()  # noqa: SLF001


def test_a_field_without_type_information_takes_the_text() -> None:
    assert codec._typed("x", "anything", set(), MAX_INPUT_BYTES) == "anything"  # noqa: SLF001
    assert codec._typed("x", "null", {"null", "string"}, 10) is None  # noqa: SLF001
    assert codec._typed("x", "[1]", {"array", "null"}, 10) == [1]  # noqa: SLF001
