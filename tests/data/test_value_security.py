# tests/data/test_value_security.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No value type can carry a URL, a host, a path or a credential (Step 2's gate).

Each type's fields, and every key of its canonical JSON with every optional
field set, are checked against the words a request, a location or a secret
would be named by. The one exception is ``terms_url``: a source's public
terms page, which must be https with no user information, port, query or
fragment, so it carries neither a credential nor a request.
"""

from __future__ import annotations

import datetime as dt
import json
import secrets
from dataclasses import fields, is_dataclass, replace
from typing import Any

import pytest
from frame_builders import TERMS, history, series_meta, two_column_table

from pyeconomics.core import InputError
from pyeconomics.core.provenance import (
    DataSource,
    LicenceClass,
    LlmUse,
    RealtimePeriod,
)
from pyeconomics.data import (
    ColumnMeta,
    Series,
    SeriesMeta,
    Table,
    TableMeta,
    Terms,
    UnitRecord,
    Vintage,
)

#: Words that name a request, a location or a secret, matched against each
#: underscore-separated part of a field name.
FORBIDDEN = frozenset(
    {
        "auth",
        "authorization",
        "contact",
        "cookie",
        "credential",
        "credentials",
        "email",
        "endpoint",
        "file",
        "header",
        "headers",
        "host",
        "hostname",
        "key",
        "params",
        "passwd",
        "password",
        "path",
        "query",
        "secret",
        "token",
        "uri",
        "url",
        "user",
        "username",
    }
)
ALLOWED = frozenset({"terms_url"})
#: User information with a password, generated at run time, never a literal.
USERINFO = f"someone:{secrets.token_hex(8)}"

TYPES = (
    DataSource,
    RealtimePeriod,
    Terms,
    UnitRecord,
    SeriesMeta,
    ColumnMeta,
    TableMeta,
    Series,
    Table,
    Vintage,
)


def full_source() -> DataSource:
    return DataSource(
        provider="fred",
        series_id="GDPC1",
        dataset="gdp",
        concept="us.output.real_gdp",
        field="output",
        vintage="first_release",
        realtime=RealtimePeriod(dt.date(2008, 1, 30), dt.date(2008, 2, 28)),
        observation_start=dt.date(2000, 3, 31),
        observation_end=dt.date(2007, 12, 31),
        transforms=("yoy",),
        retrieved_at=dt.datetime(2026, 10, 14, tzinfo=dt.UTC),
        licence=LicenceClass.LIBRARY_ONLY,
        attribution="Source: an example.",
        notice="An example notice.",
        terms_url=TERMS.terms_url,
        llm_use=LlmUse.UNCLEAR,
        cache_hit=True,
        served_offline=True,
        fallback_chain=("fred",),
        warnings=("served_offline",),
    )


def _bad(name: str) -> bool:
    return name not in ALLOWED and bool(set(name.lower().split("_")) & FORBIDDEN)


def _keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in _keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in _keys(item)}
    return set()


@pytest.mark.parametrize("cls", TYPES, ids=lambda cls: cls.__name__)
def test_no_field_is_named_for_a_url_host_path_or_credential(cls: type) -> None:
    assert is_dataclass(cls)
    assert [field.name for field in fields(cls) if _bad(field.name)] == []


@pytest.mark.parametrize(
    "document",
    [
        lambda: full_source().canonical_json(),
        TERMS.canonical_json,
        lambda: history().canonical_json(),
        lambda: two_column_table().canonical_json(),
    ],
    ids=["DataSource", "Terms", "Series", "Table"],
)
def test_no_canonical_json_key_is_named_for_one(document: Any) -> None:  # noqa: ANN401
    keys = _keys(json.loads(document()))
    assert keys
    assert sorted(key for key in keys if _bad(key)) == []


def test_the_word_list_catches_what_it_should() -> None:
    assert [
        name
        for name in ("api_key", "request_url", "host", "cache_path", "terms_url")
        if _bad(name)
    ] == [
        "api_key",
        "request_url",
        "host",
        "cache_path",
    ]


@pytest.mark.parametrize(
    "url",
    [
        f"https://{USERINFO}@www.example.org/terms",
        "https://www.example.org/terms?key=value",
        "https://www.example.org:8080/terms",
        "http://www.example.org/terms",
    ],
)
def test_the_terms_url_cannot_carry_a_credential_or_a_request(url: str) -> None:
    with pytest.raises(InputError):
        replace(TERMS, terms_url=url)
    with pytest.raises(InputError):
        replace(full_source(), terms_url=url)


TEXT_FIELDS = {
    "source.series_id": lambda value: replace(full_source(), series_id=value),
    "source.dataset": lambda value: replace(full_source(), dataset=value),
    "source.attribution": lambda value: replace(full_source(), attribution=value),
    "source.notice": lambda value: replace(full_source(), notice=value),
    "source.transforms": lambda value: replace(full_source(), transforms=(value,)),
    "terms.attribution": lambda value: replace(TERMS, attribution=value),
    "terms.notice": lambda value: replace(TERMS, notice=value),
    "meta.title": lambda value: series_meta(title=value),
    "meta.series_id": lambda value: series_meta(series_id=value),
    "meta.dataset": lambda value: series_meta(dataset=value),
    "unit.text": lambda value: UnitRecord(text=value),
}


@pytest.mark.parametrize("build", TEXT_FIELDS.values(), ids=list(TEXT_FIELDS))
def test_no_text_field_takes_a_url(build: Any) -> None:  # noqa: ANN401 - a builder
    with pytest.raises(InputError, match="must not contain a URL"):
        build("https://api.example.org/v1/series?id=1")
