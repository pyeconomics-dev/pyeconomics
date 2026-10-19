# tests/results/test_manifest_sources.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Manifest schema 2: the data records a bound run carries, and what stays out.

Schema 1 promised a manifest with no clock at all. Schema 2 narrows that to the
invariant it protected: no clock *of the run*, no host, user, path or environment
value, and no request URL or key. A record's retrieval time is a fact about the
data, recorded where the data was fetched (ADR-0011 decision 16).
"""

from __future__ import annotations

import datetime as dt
import getpass
import os
import platform
import socket
import sys
from pathlib import Path
from typing import Any

import bound_support as bs
import pytest

from pyeconomics.core import Manifest, run_model
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import DataSource, LicenceClass, LlmUse
from pyeconomics.data import bind_model

MIN_VALUE = 6
FORBIDDEN_KEYS = {
    "time",
    "timestamp",
    "created",
    "host",
    "hostname",
    "user",
    "username",
    "path",
    "cwd",
    "env",
    "environment",
    "token",
    "key",
    "api_key",
    "password",
    "url",
    "uri",
    "headers",
    "query",
}
RECORD_KEYS = [
    "provider",
    "series_id",
    "dataset",
    "concept",
    "field",
    "vintage",
    "realtime",
    "observation_start",
    "observation_end",
    "transforms",
    "retrieved_at",
    "licence",
    "attribution",
    "notice",
    "terms_url",
    "llm_use",
    "cache_hit",
    "served_offline",
    "fallback_chain",
    "warnings",
]


def record(field: str, series_id: str = "X") -> DataSource:
    return DataSource(
        provider="demo",
        series_id=series_id,
        field=field,
        licence=LicenceClass.HOSTED_SAFE,
        attribution="Source: demo.",
        terms_url="https://www.example.org/terms",
        llm_use=LlmUse.ALLOWED,
    )


def walk(value: object) -> Any:  # noqa: ANN401 - yields every key and string value
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from walk(item)
    elif isinstance(value, list | tuple):
        for item in value:
            yield from walk(item)
    else:
        yield value


def bound_manifest() -> dict[str, Any]:
    bound = bind_model(bs.unemployment, as_of=dt.date(2024, 3, 20), registry=bs.world())
    return run_model(bs.unemployment, bound).manifest.to_dict()


def test_a_manifest_holds_the_records_it_is_given_sorted_by_field() -> None:
    first, second, third = record("b", "S1"), record("a", "S2"), record("a", "S1")
    manifest = Manifest(
        model_id="a.b",
        model_version=1,
        package_version="1",
        data_sources=[first, second, third],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        inputs_sha256="0" * 64,
        result_sha256="1" * 64,
    )
    # Sorted by field; a field's own records keep their order (a ratio's
    # numerator comes before its denominator).
    assert manifest.data_sources == (second, third, first)
    assert isinstance(manifest.data_sources, tuple)


def test_a_manifest_refuses_anything_but_a_record() -> None:
    with pytest.raises(TypeError, match="DataSource"):
        Manifest(
            model_id="a.b",
            model_version=1,
            package_version="1",
            data_sources=({"provider": "fred"},),  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
            inputs_sha256="0" * 64,
            result_sha256="1" * 64,
        )


def test_create_takes_the_records_and_the_hashes_do_not_cover_them() -> None:
    kwargs: dict[str, Any] = {
        "model_id": "a.b",
        "model_version": 1,
        "inputs": {"x": 1},
        "body": {"outputs": {"y": 2}},
    }
    bare = Manifest.create(**kwargs)
    read = Manifest.create(**kwargs, data_sources=[record("x")])
    assert bare.data_sources == ()
    assert read.data_sources == (record("x"),)
    assert (bare.inputs_sha256, bare.result_sha256) == (
        read.inputs_sha256,
        read.result_sha256,
    )


def test_the_dict_form_lists_every_record_key_and_the_schema_is_two() -> None:
    manifest = bound_manifest()
    assert manifest["schema_version"] == 2
    (source,) = manifest["data_sources"]
    assert list(source) == RECORD_KEYS
    assert list(manifest) == [
        "schema_version",
        "model_id",
        "model_version",
        "package_version",
        "dependencies",
        "seed",
        "bit_generator",
        "data_sources",
        "inputs_sha256",
        "result_sha256",
    ]


def test_a_bound_manifest_has_no_clock_of_the_run_host_user_path_or_environment() -> (
    None
):
    manifest = bound_manifest()
    keys = {k.lower() for k in walk(manifest) if isinstance(k, str)}
    assert not FORBIDDEN_KEYS & keys
    values = [str(v) for v in walk(manifest)]
    volatile = {
        socket.gethostname(),
        getpass.getuser(),
        os.getcwd(),  # noqa: PTH109
        str(Path.home()),
        sys.executable,
        platform.node(),
    }
    joined = "\n".join(values)
    assert not [name for name in volatile if len(name) >= MIN_VALUE and name in joined]
    leaked = [
        name
        for name, value in os.environ.items()
        if len(value) >= MIN_VALUE and value in joined
    ]
    assert not leaked  # names only: a value is never printed


def test_the_only_time_in_a_bound_manifest_is_the_datas_own() -> None:
    manifest = bound_manifest()
    (source,) = manifest["data_sources"]
    assert source["retrieved_at"] == bs.FETCHED.isoformat()
    others = [
        v
        for v in walk({**manifest, "data_sources": []})
        if isinstance(v, str) and (":" in v and v[:4].isdigit())
    ]
    assert others == []


def test_a_record_names_the_data_never_the_request() -> None:
    (source,) = bound_manifest()["data_sources"]
    for key, value in source.items():
        text = str(value)
        if key == "terms_url":
            assert text.startswith("https://")
            assert not any(mark in text for mark in "?#@")
        else:
            assert "://" not in text, key
    assert source["terms_url"] == "https://www.example.org/legal/library"


def test_two_runs_on_the_same_inputs_and_records_have_the_same_bytes() -> None:
    bound = bind_model(bs.unemployment, as_of=dt.date(2024, 3, 20), registry=bs.world())
    one = run_model(bs.unemployment, bound).manifest
    two = run_model(bs.unemployment, bound).manifest
    assert canonical_json(one.to_dict()) == canonical_json(two.to_dict())
