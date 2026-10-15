# tests/unit/core/test_fields.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.core._fields: the checks behind the provenance and data types."""

from __future__ import annotations

import datetime as dt
import secrets
from enum import StrEnum

import pytest

from pyeconomics.core import InputError
from pyeconomics.core import _fields as f
from pyeconomics.core.units import DateBounds


class Colour(StrEnum):
    RED = "red"


BOUNDS = DateBounds(dt.date(2000, 1, 1), dt.date(2000, 12, 31))
#: User information with a password, generated at run time, never a literal.
USERINFO = f"user:{secrets.token_hex(8)}"


@pytest.mark.parametrize(
    "url",
    [
        "https://fred.stlouisfed.org/docs/api/terms_of_use.html",
        "https://www.bls.gov/developers/termsOfService.htm",
        "https://home.treasury.gov/",
        "https://data.bis.org/help/legal",
    ],
)
def test_public_https_terms_pages_are_accepted(url: str) -> None:
    assert f.terms_url(url) == url


@pytest.mark.parametrize(
    ("url", "message"),
    [
        (None, "must be a string"),
        ("http://www.example.org/terms", "must use https"),
        ("ftp://www.example.org/terms", "must use https"),
        ("www.example.org/terms", "must use https"),
        (f"https://{USERINFO}@www.example.org/terms", "user information or a port"),
        ("https://user@www.example.org/terms", "user information or a port"),
        ("https://www.example.org:8443/terms", "user information or a port"),
        ("https://www.example.org:99999/terms", "not a valid URL"),
        ("https://www.example.org/terms?key=value", "query or a fragment"),
        ("https://www.example.org/terms?", "query or a fragment"),
        ("https://www.example.org/terms#use", "query or a fragment"),
        ("https://localhost/terms", "lowercase host"),
        ("https://WWW.EXAMPLE.ORG/terms", "lowercase host"),
        ("https://192.168.0.1/terms", "lowercase host"),
        ("https://www.example.org/a terms", "single URL"),
        ("https://www.example.org/\nterms", "single URL"),
        ("https://www.example.org/" + "t" * 512, "single URL"),
        ("https://[::1/terms", "not a valid URL"),
    ],
)
def test_a_terms_url_that_could_carry_more_is_refused(
    url: object, message: str
) -> None:
    with pytest.raises(InputError, match=message):
        f.terms_url(url)


def test_text_refuses_what_could_hide_a_request() -> None:
    with pytest.raises(InputError, match="URL"):
        f.text("see ftp://files.example.org", "title")
    with pytest.raises(InputError, match="control"):
        f.text("tab\there", "title")
    assert f.optional_text(None, "title") is None


def test_identifiers_are_snake_case_and_bounded() -> None:
    assert f.identifier("fred_v2", "provider") == "fred_v2"
    for bad in ("2fred", "_fred", "fred.v2"):
        with pytest.raises(InputError, match="snake_case"):
            f.identifier(bad, "provider")
    with pytest.raises(InputError, match="at most 64"):
        f.identifier("a" * 65, "provider")
    assert f.identifiers(["a", "a"], "codes", max_items=2, unique=False) == ("a", "a")


@pytest.mark.parametrize("value", ["abc", b"abc", {"a": 1}, 3])
def test_a_sequence_is_a_list_or_tuple(value: object) -> None:
    with pytest.raises(InputError, match="list or tuple"):
        f.sequence(value, "items", max_items=3)


def test_choices_take_members_or_their_values() -> None:
    assert f.choice(Colour, "red", "colour") is Colour.RED
    assert f.choice(Colour, Colour.RED, "colour") is Colour.RED
    with pytest.raises(InputError, match="one of red"):
        f.choice(Colour, "blue", "colour")


def test_instances_are_checked_by_class() -> None:
    assert f.instance(3, int, "count") == 3
    with pytest.raises(InputError, match="must be a int"):
        f.instance("3", int, "count")


def test_flags_are_booleans_only() -> None:
    assert f.flag(value=True, what="hit") is True
    with pytest.raises(InputError):
        f.flag(1, "hit")


def test_days_are_dates_within_bounds() -> None:
    assert f.day(dt.date(2000, 6, 1), "day", BOUNDS) == dt.date(2000, 6, 1)
    assert f.optional_day(None, "day", BOUNDS) is None
    with pytest.raises(InputError, match="must lie between"):
        f.day(dt.date(2001, 1, 1), "day", BOUNDS)
    with pytest.raises(InputError, match="must be a date"):
        f.day(True, "day", BOUNDS)  # noqa: FBT003 - a flag is not a date


def test_instants_are_aware_and_become_utc() -> None:
    tokyo = dt.timezone(dt.timedelta(hours=9))
    moment = dt.datetime(2026, 10, 14, 9, 0, tzinfo=tokyo)
    assert f.instant(moment, "at") == dt.datetime(2026, 10, 14, 0, 0, tzinfo=dt.UTC)
    assert f.optional_instant(None, "at") is None


def test_json_nested_as_deep_as_the_writer_allows_is_read() -> None:
    # 100 nested arrays put the innermost value at depth 100, the writer's limit.
    assert f.load_json("[" * 100 + "1" + "]" * 100) is not None
    assert f.load_json('{"a":' * 100 + "1" + "}" * 100) is not None


@pytest.mark.parametrize(
    "document",
    ["[" * 101 + "1" + "]" * 101, '{"a":' * 101 + "1" + "}" * 101],
    ids=["arrays", "objects"],
)
def test_json_nested_deeper_than_the_writer_allows_is_refused(document: str) -> None:
    with pytest.raises(InputError, match="nests deeper than 100 levels"):
        f.load_json(document)


def test_json_too_deep_for_any_parser_is_refused() -> None:
    # Python 3.12 and 3.13's parser raise RecursionError; 3.14's parses it and
    # the depth check refuses it. Either way the caller sees an InputError.
    with pytest.raises(InputError):
        f.load_json("[" * 100_000 + "]" * 100_000)


def test_parsing_reads_only_iso_forms() -> None:
    assert f.parse_day("2026-10-14", "day") == dt.date(2026, 10, 14)
    assert f.parse_optional_day(None, "day") is None
    assert f.parse_instant(None, "at") is None
    with pytest.raises(InputError, match="YYYY-MM-DD"):
        f.parse_day(20261014, "day")
    with pytest.raises(InputError, match="ISO 8601 datetime"):
        f.parse_instant(1, "at")
