# tests/unit/core/test_provenance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""pyeconomics.core.provenance: licence classes, real-time periods, DataSource."""

from __future__ import annotations

import datetime as dt
import importlib
import json
from dataclasses import fields, replace
from typing import Any

import pytest

import pyeconomics.core
from pyeconomics.core import (
    DataSource,
    InputError,
    LicenceClass,
    LlmUse,
    RealtimePeriod,
)
from pyeconomics.core.provenance import (
    CONCEPT_ID_PATTERN,
    DATA_DATE_BOUNDS,
    MAX_FALLBACK_CHAIN,
    MAX_TRANSFORMS,
    VINTAGE_LABEL_PATTERN,
)

TERMS = "https://www.example.org/legal/terms"
EASTERN = dt.timezone(dt.timedelta(hours=-4))


def source(**changes: Any) -> DataSource:  # noqa: ANN401 - any field
    """A record with every field set, with ``changes`` applied."""
    record = DataSource(
        provider="fred",
        series_id="PCEPILFE",
        dataset="pce_price_index",
        concept="us.inflation.pce_core.yoy",
        field="inflation",
        vintage="as_of:2008-12-16",
        realtime=RealtimePeriod(dt.date(2008, 12, 16), dt.date(2008, 12, 22)),
        observation_start=dt.date(2006, 1, 31),
        observation_end=dt.date(2008, 10, 31),
        transforms=("yoy", "mean(window=3)"),
        retrieved_at=dt.datetime(2026, 10, 14, 9, 30, tzinfo=EASTERN),
        licence=LicenceClass.LIBRARY_ONLY,
        attribution="Source: Federal Reserve Bank of St. Louis.",
        notice="This product uses an example API.",
        terms_url=TERMS,
        llm_use=LlmUse.FORBIDDEN,
        cache_hit=False,
        served_offline=False,
        fallback_chain=("bea", "fred"),
        warnings=("revised_data",),
    )
    return replace(record, **changes)


def minimal(**changes: Any) -> DataSource:  # noqa: ANN401 - any field
    """A record with only the required fields."""
    values: dict[str, Any] = {
        "provider": "treasury",
        "series_id": "par_yield_curve",
        "licence": "hosted-safe",
        "attribution": "Source: US Department of the Treasury.",
        "terms_url": TERMS,
        "llm_use": "allowed",
    }
    return DataSource(**(values | changes))


# --- licence classes and llm_use ----------------------------------------------


def test_the_five_licence_classes_are_adr_0005s() -> None:
    assert [c.value for c in LicenceClass] == [
        "hosted-safe",
        "library-only",
        "byok",
        "premium-local",
        "user-supplied",
    ]


@pytest.mark.parametrize(
    ("licence", "allowed"),
    [
        (LicenceClass.HOSTED_SAFE, True),
        (LicenceClass.USER_SUPPLIED, True),
        (LicenceClass.LIBRARY_ONLY, False),
        (LicenceClass.BYOK, False),
        (LicenceClass.PREMIUM_LOCAL, False),
    ],
)
def test_hosted_mode_allows_only_hosted_safe_and_user_supplied(
    licence: LicenceClass, *, allowed: bool
) -> None:
    assert licence.hosted_allowed is allowed


def test_llm_use_is_allowed_forbidden_or_unclear() -> None:
    assert [u.value for u in LlmUse] == ["allowed", "forbidden", "unclear"]


# --- real-time periods --------------------------------------------------------


def test_a_period_covers_both_of_its_ends() -> None:
    period = RealtimePeriod(dt.date(2008, 4, 30), dt.date(2008, 5, 28))
    assert period.covers(dt.date(2008, 4, 30))
    assert period.covers(dt.date(2008, 5, 28))
    assert not period.covers(dt.date(2008, 4, 29))
    assert not period.covers(dt.date(2008, 5, 29))
    assert not period.is_current


def test_an_open_period_is_current_and_covers_every_later_day() -> None:
    period = RealtimePeriod(dt.date(2008, 6, 26))
    assert period.is_current
    assert period.covers(DATA_DATE_BOUNDS.upper)
    assert not period.covers(dt.date(2008, 6, 25))


def test_a_one_day_period_is_allowed() -> None:
    day = dt.date(2008, 1, 30)
    assert RealtimePeriod(day, day).covers(day)


@pytest.mark.parametrize(
    ("start", "end", "message"),
    [
        (dt.date(2008, 5, 1), dt.date(2008, 4, 30), "before realtime_start"),
        ("2008-05-01", None, "must be a date"),
        (dt.datetime(2008, 5, 1, tzinfo=dt.UTC), None, "must be a date"),
        (dt.date(1699, 12, 31), None, "must lie between"),
        (dt.date(2008, 5, 1), dt.date(2201, 1, 1), "must lie between"),
    ],
)
def test_bad_periods_are_refused(start: object, end: object, message: str) -> None:
    with pytest.raises(InputError, match=message):
        RealtimePeriod(start, end)  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]


def test_alfreds_real_time_origin_is_inside_the_bounds() -> None:
    assert RealtimePeriod(dt.date(1776, 7, 4)).realtime_start.year == 1776


@pytest.mark.parametrize(
    "period",
    [
        RealtimePeriod(dt.date(2008, 1, 30)),
        RealtimePeriod(dt.date(2008, 1, 30), dt.date(2009, 2, 1)),
    ],
)
def test_a_period_round_trips_through_its_dict(period: RealtimePeriod) -> None:
    assert RealtimePeriod.from_dict(json.loads(json.dumps(period.to_dict()))) == period


@pytest.mark.parametrize(
    "data",
    [
        {"realtime_start": "2008-01-30"},
        {"realtime_start": "2008-01-30", "realtime_end": None, "extra": 1},
        {"realtime_start": "20080130", "realtime_end": None},
        ["2008-01-30", None],
    ],
)
def test_a_period_refuses_any_other_form(data: object) -> None:
    with pytest.raises(InputError):
        RealtimePeriod.from_dict(data)


# --- the DataSource record ----------------------------------------------------


def test_a_full_record_round_trips_through_canonical_json() -> None:
    record = source()
    text = record.canonical_json()
    assert DataSource.from_json(text) == record
    assert DataSource.from_json(text.decode()).canonical_json() == text


def test_a_minimal_record_round_trips_and_has_its_defaults() -> None:
    record = minimal()
    assert record.licence is LicenceClass.HOSTED_SAFE
    assert record.llm_use is LlmUse.ALLOWED
    assert record.transforms == record.fallback_chain == record.warnings == ()
    assert not record.cache_hit
    assert not record.served_offline
    assert DataSource.from_dict(json.loads(record.canonical_json())) == record


def test_every_key_is_written_even_when_empty() -> None:
    names = [field.name for field in fields(DataSource)]
    assert list(minimal().to_dict()) == names
    assert list(json.loads(minimal().canonical_json())) == sorted(names)


def test_the_retrieval_time_is_normalized_to_utc() -> None:
    record = source()
    assert record.retrieved_at == dt.datetime(2026, 10, 14, 13, 30, tzinfo=dt.UTC)
    assert record.retrieved_at is not None
    assert record.retrieved_at.tzinfo is dt.UTC
    assert record.to_dict()["retrieved_at"] == "2026-10-14T13:30:00+00:00"


def test_identical_records_give_identical_bytes() -> None:
    assert source().canonical_json() == source().canonical_json()
    assert source(cache_hit=True).canonical_json() != source().canonical_json()


def test_user_supplied_data_may_have_no_terms_url() -> None:
    record = minimal(licence=LicenceClass.USER_SUPPLIED, terms_url=None)
    assert record.terms_url is None
    assert DataSource.from_json(record.canonical_json()) == record


@pytest.mark.parametrize(
    "licence", [c for c in LicenceClass if c is not LicenceClass.USER_SUPPLIED]
)
def test_every_other_class_needs_its_terms_url(licence: LicenceClass) -> None:
    with pytest.raises(InputError, match="terms_url is required"):
        minimal(licence=licence, terms_url=None)


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"provider": "FRED"}, "snake_case"),
        ({"provider": "fred-api"}, "snake_case"),
        ({"provider": 3}, "must be a string"),
        ({"series_id": ""}, "must not be empty"),
        ({"series_id": "x" * 257}, "at most 256"),
        ({"series_id": "GDP\nC1"}, "control characters"),
        ({"dataset": "https://api.example.org/data"}, "must not contain a URL"),
        ({"concept": "inflation"}, "does not match"),
        ({"concept": "us.Inflation.core"}, "does not match"),
        ({"concept": "a.b.c.d.e"}, "does not match"),
        ({"field": "Inflation"}, "snake_case"),
        ({"vintage": "as_of 2008-12-16"}, "does not match"),
        ({"vintage": "revised"}, "does not match"),
        ({"realtime": (dt.date(2008, 1, 1), None)}, "must be a RealtimePeriod"),
        ({"observation_start": None}, "both set or both None"),
        ({"observation_end": dt.date(2006, 1, 1)}, "before observation_start"),
        ({"observation_start": dt.date(1600, 1, 1)}, "must lie between"),
        ({"transforms": "yoy"}, "list or tuple"),
        ({"transforms": ("x",) * (MAX_TRANSFORMS + 1)}, "at most 32"),
        ({"transforms": ("yoy", "")}, "must not be empty"),
        ({"retrieved_at": dt.datetime(2026, 10, 14, 9, 30)}, "time zone"),  # noqa: DTZ001
        ({"retrieved_at": dt.date(2026, 10, 14)}, "must be a datetime"),
        ({"licence": "public"}, "must be one of"),
        ({"licence": 1}, "must be one of"),
        ({"attribution": " "}, "must not be empty"),
        ({"attribution": "x" * 1001}, "at most 1000"),
        ({"notice": "See https://www.example.org/notice"}, "must not contain a URL"),
        ({"terms_url": "http://www.example.org/terms"}, "must use https"),
        ({"llm_use": "maybe"}, "must be one of"),
        ({"cache_hit": 1}, "true or false"),
        ({"served_offline": "no"}, "true or false"),
        ({"fallback_chain": ("bea",)}, "must end with the provider"),
        ({"fallback_chain": ("fred", "fred")}, "must not repeat"),
        ({"fallback_chain": ("x",) * (MAX_FALLBACK_CHAIN + 1)}, "at most 16"),
        ({"warnings": ("revised_data", "revised_data")}, "must not repeat"),
        ({"warnings": ("Revised data",)}, "snake_case"),
    ],
)
def test_every_field_is_checked(changes: dict[str, object], message: str) -> None:
    with pytest.raises(InputError, match=message):
        source(**changes)


@pytest.mark.parametrize(
    "concept",
    [
        "us.inflation.pce_core.yoy",
        "us.unemployment.rate",
        "us.policy_rate.target_upper",
        "us.treasury.par_curve",
        "factors.ff5.us.monthly",
        "ea.inflation.hicp",
    ],
)
def test_the_concept_grammar_accepts_decision_15s_examples(concept: str) -> None:
    assert CONCEPT_ID_PATTERN.fullmatch(concept)
    assert source(concept=concept).concept == concept


@pytest.mark.parametrize(
    "label", ["latest", "first_release", "all", "as_of:2008-12-16"]
)
def test_the_vintage_labels(label: str) -> None:
    assert VINTAGE_LABEL_PATTERN.fullmatch(label)
    assert source(vintage=label).vintage == label


def test_a_record_with_no_resolver_has_no_chain() -> None:
    assert source(fallback_chain=()).fallback_chain == ()
    assert source(fallback_chain=["fred"]).fallback_chain == ("fred",)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda d: d.pop("warnings"), "missing keys"),
        (lambda d: d.update(url="https://www.example.org/"), "unknown keys"),
        (lambda d: d.update(transforms="yoy"), "JSON array"),
        (lambda d: d.update(observation_start="2006-01"), "YYYY-MM-DD"),
        (lambda d: d.update(observation_start="2006-02-30"), "not a calendar date"),
        (lambda d: d.update(retrieved_at="2026-10-14"), "ISO 8601 datetime"),
        (lambda d: d.update(retrieved_at="2026-10-14Tnoon"), "not an ISO 8601"),
        (lambda d: d.update(realtime={"realtime_start": "2008-12-16"}), "missing keys"),
    ],
)
def test_reading_a_record_refuses_any_other_form(
    change: Any,  # noqa: ANN401 - a mutator
    message: str,
) -> None:
    data = json.loads(source().canonical_json())
    change(data)
    with pytest.raises(InputError, match=message):
        DataSource.from_dict(data)


@pytest.mark.parametrize(
    ("document", "message"),
    [
        (b'{"provider": "fred", "provider": "bea"}', "repeats the key"),
        (b'{"value": NaN}', "has no NaN"),
        (b"[1, 2", "not a JSON document"),
        (b"\xff", "not a JSON document"),
        (b'"a string"', "must be a JSON object"),
        (3, "str or bytes"),
    ],
)
def test_json_is_read_strictly(document: Any, message: str) -> None:  # noqa: ANN401
    with pytest.raises(InputError, match=message):
        DataSource.from_json(document)


# --- names --------------------------------------------------------------------


def test_the_names_are_exported_from_core() -> None:
    for name in ("DataSource", "LicenceClass", "LlmUse", "RealtimePeriod"):
        assert name in pyeconomics.core.__all__


def test_the_module_is_hidden_by_the_random_provenance_function() -> None:
    # Like core.model, the name `provenance` on pyeconomics.core is a function
    # (pyeconomics.core.random.provenance); the module is reached by its path.
    assert callable(pyeconomics.core.provenance)
    module = importlib.import_module("pyeconomics.core.provenance")
    assert module.DataSource is DataSource
