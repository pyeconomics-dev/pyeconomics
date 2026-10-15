# tests/data/test_terms.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.data.Terms and CachePolicy: validation, overrides and freshness."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import replace
from typing import Any

import pytest
from frame_builders import TERMS

from pyeconomics.core import InputError
from pyeconomics.data import (
    TERMS_MAX_AGE_MONTHS,
    CachePolicy,
    LicenceClass,
    LlmUse,
    Terms,
)


def test_terms_round_trip_through_canonical_json() -> None:
    assert Terms.from_json(TERMS.canonical_json()) == TERMS
    assert json.loads(TERMS.canonical_json()) == {
        "attribution": TERMS.attribution,
        "cache": "allowed",
        "checked": "2026-10-14",
        "licence": "hosted-safe",
        "llm_use": "allowed",
        "notice": TERMS.notice,
        "terms_url": TERMS.terms_url,
    }


def test_terms_take_enum_values_as_well_as_members() -> None:
    values: dict[str, Any] = {
        "licence": "library-only",
        "llm_use": "unclear",
        "cache": "forbidden",
    }
    terms = replace(TERMS, **values)
    assert terms.licence is LicenceClass.LIBRARY_ONLY
    assert terms.llm_use is LlmUse.UNCLEAR
    assert terms.cache is CachePolicy.FORBIDDEN


def test_the_cache_policy_is_allowed_or_forbidden() -> None:
    assert [policy.value for policy in CachePolicy] == ["allowed", "forbidden"]


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"terms_url": "http://www.example.org/terms"}, "must use https"),
        ({"terms_url": "https://www.example.org/terms?lang=en"}, "query"),
        ({"attribution": ""}, "must not be empty"),
        ({"attribution": None}, "must be a string"),
        ({"notice": "Read https://www.example.org/notice"}, "must not contain a URL"),
        ({"checked": "2026-10-14"}, "must be a date"),
        ({"checked": dt.date(1899, 12, 31)}, "must lie between"),
        ({"licence": "hosted_safe"}, "must be one of"),
        ({"llm_use": True}, "must be one of"),
        ({"cache": "session"}, "must be one of"),
    ],
)
def test_terms_are_checked(changes: dict[str, Any], message: str) -> None:
    with pytest.raises(InputError, match=message):
        replace(TERMS, **changes)


def test_a_notice_is_optional() -> None:
    terms = replace(TERMS, notice=None)
    assert Terms.from_json(terms.canonical_json()).notice is None


# --- freshness ----------------------------------------------------------------


def test_terms_are_current_for_13_months() -> None:
    assert TERMS_MAX_AGE_MONTHS == 13
    assert TERMS.stale_after == dt.date(2027, 11, 14)
    assert not TERMS.is_stale(dt.date(2027, 11, 14))
    assert TERMS.is_stale(dt.date(2027, 11, 15))
    assert not TERMS.is_stale(TERMS.checked)


@pytest.mark.parametrize(
    ("checked", "stale_after"),
    [
        (dt.date(2026, 1, 31), dt.date(2027, 2, 28)),
        (dt.date(2027, 1, 31), dt.date(2028, 2, 29)),
        (dt.date(2026, 12, 31), dt.date(2028, 1, 31)),
        (dt.date(2200, 12, 31), dt.date(2202, 1, 31)),
    ],
)
def test_the_horizon_clamps_to_a_shorter_month(
    checked: dt.date, stale_after: dt.date
) -> None:
    assert replace(TERMS, checked=checked).stale_after == stale_after


# --- series overrides ---------------------------------------------------------


def test_a_series_overrides_only_class_llm_use_cache_and_notice() -> None:
    marked = TERMS.with_overrides(
        licence=LicenceClass.LIBRARY_ONLY,
        llm_use=LlmUse.FORBIDDEN,
        cache=CachePolicy.FORBIDDEN,
        notice="Copyright an example owner; reproduced with permission.",
    )
    assert marked.licence is LicenceClass.LIBRARY_ONLY
    assert marked.llm_use is LlmUse.FORBIDDEN
    assert marked.cache is CachePolicy.FORBIDDEN
    assert marked.notice is not None
    assert marked.notice.startswith("Copyright")
    assert (marked.terms_url, marked.checked, marked.attribution) == (
        TERMS.terms_url,
        TERMS.checked,
        TERMS.attribution,
    )


def test_no_override_leaves_the_terms_unchanged() -> None:
    assert TERMS.with_overrides() == TERMS
    assert TERMS.with_overrides(cache=CachePolicy.FORBIDDEN).licence is TERMS.licence


def test_an_override_is_checked_too() -> None:
    with pytest.raises(InputError, match="must be one of"):
        TERMS.with_overrides(licence="public")  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.pop("cache"),
        lambda d: d.update(url="https://www.example.org/"),
        lambda d: d.update(checked="14 October 2026"),
    ],
)
def test_reading_refuses_any_other_form(change: Any) -> None:  # noqa: ANN401
    data = json.loads(TERMS.canonical_json())
    change(data)
    with pytest.raises(InputError):
        Terms.from_dict(data)
