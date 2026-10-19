# tests/results/test_manifest.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The manifest: what it records, what it hashes, and what it must never hold."""

from __future__ import annotations

import getpass
import os
import platform
import re
import socket
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pydantic
import scipy
import toy_models as tm
import toy_results_models as rm

import pyeconomics
from pyeconomics.core import Manifest, run_model
from pyeconomics.core.canonical import canonical_json, canonical_sha256
from pyeconomics.core.manifest import (
    DEPENDENCIES,
    MANIFEST_SCHEMA_VERSION,
    inputs_sha256,
    result_sha256,
)

ZERO = {"face_value": 100, "rate": 0.05, "years": 10}


def zero() -> Any:  # noqa: ANN401 - a Result
    return run_model(tm.zero_coupon, **ZERO)


#: Shorter values would match by chance; the test never prints a value.
MIN_VALUE = 6


def leaked_names(text: str) -> list[str]:
    """Return the names (never the values) of environment variables found in text."""
    return [
        name
        for name, value in os.environ.items()
        if len(value) >= MIN_VALUE and value in text
    ]


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


def test_the_manifest_records_the_environment_it_ran_in() -> None:
    manifest = zero().manifest
    assert manifest.schema_version == MANIFEST_SCHEMA_VERSION == 2
    assert (manifest.model_id, manifest.model_version) == (
        "fixed_income.toy_zero_coupon",
        1,
    )
    assert manifest.package_version == pyeconomics.__version__
    assert dict(manifest.dependencies) == {
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "pydantic": pydantic.VERSION,
        "scipy": scipy.__version__,
    }
    assert tuple(manifest.dependencies) == DEPENDENCIES  # sorted by name
    assert manifest.data_sources == ()
    assert (manifest.seed, manifest.bit_generator) == (None, None)


def test_the_manifest_dict_has_these_keys() -> None:
    assert list(zero().manifest.to_dict()) == [
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
    assert zero().manifest.to_dict()["data_sources"] == []


def test_the_inputs_hash_covers_the_model_its_version_and_the_inputs() -> None:
    result = zero()
    inputs = result.inputs.model_dump(mode="json")
    expected = canonical_sha256(
        {"inputs": inputs, "model_id": result.model_id, "model_version": 1}
    )
    assert result.manifest.inputs_sha256 == expected
    assert inputs_sha256(result.model_id, 1, inputs) == expected
    assert inputs_sha256(result.model_id, 2, inputs) != expected
    assert inputs_sha256("fixed_income.other", 1, inputs) != expected
    assert inputs_sha256(result.model_id, 1, {**inputs, "rate": 0.06}) != expected


def test_the_result_hash_covers_everything_but_the_manifest() -> None:
    result = run_model(rm.dated, start="2026-01-31", days=0)
    body = {
        "model_id": result.model_id,
        "model_version": result.model_version,
        "inputs": result.inputs.model_dump(mode="json"),
        "outputs": result.outputs.model_dump(mode="json"),
        "warnings": [{"code": "zero_days", "message": result.warnings[0].message}],
    }
    assert result.manifest.result_sha256 == canonical_sha256(body)
    assert result_sha256(body) == canonical_sha256(body)
    for key in body:
        changed = {**body, key: "changed"}
        assert result_sha256(changed) != result_sha256(body), key
    assert "manifest" not in body


def test_the_hashes_are_lowercase_sha256_hex() -> None:
    manifest = zero().manifest
    for digest in (manifest.inputs_sha256, manifest.result_sha256):
        assert re.fullmatch(r"[0-9a-f]{64}", digest)


def test_the_manifest_is_deterministic_and_equal_across_runs() -> None:
    a, b = zero().manifest, zero().manifest
    assert a == b
    assert canonical_json(a.to_dict()) == canonical_json(b.to_dict())


def test_dependency_versions_are_read_once() -> None:
    from pyeconomics.core import manifest as module  # noqa: PLC0415

    zero()
    before = module._versions.cache_info().hits  # noqa: SLF001
    zero()
    assert module._versions.cache_info().hits > before  # noqa: SLF001


def test_a_hand_built_manifest_freezes_what_it_is_given() -> None:
    manifest = Manifest(
        model_id="a.b",
        model_version=1,
        package_version="1",
        dependencies={"scipy": "1", "numpy": "2"},
        data_sources=[],  # type: ignore[arg-type]  # ty: ignore[invalid-argument-type]
        inputs_sha256="0" * 64,
        result_sha256="1" * 64,
    )
    assert list(manifest.dependencies) == ["numpy", "scipy"]
    assert manifest.data_sources == ()


def test_the_manifest_of_a_run_without_data_holds_no_volatile_or_sensitive_value() -> (
    None
):
    """Keys and values: no clock, host, user, path or environment value.

    Schema 2 lets a data source record its retrieval time, a fact about the data;
    a run that read no data has no such record, so its manifest is as before.
    """
    manifest = zero().manifest.to_dict()
    keys = [k for k in walk(manifest) if isinstance(k, str)]
    values = [str(v) for v in walk(manifest)]
    forbidden_keys = {
        "time",
        "timestamp",
        "created",
        "date",
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
    }
    assert not forbidden_keys & {key.lower() for key in keys}
    volatile = {
        socket.gethostname(),
        getpass.getuser(),
        os.getcwd(),  # noqa: PTH109
        str(Path.home()),
        sys.executable,
        platform.node(),
    }
    joined = "\n".join(values)
    assert not [f for f in volatile if len(f) >= MIN_VALUE and f in joined]
    assert not leaked_names(joined)  # names only: a value is never printed
    # Every value is a version, a hash, an id, a number, or null.
    pattern = re.compile(r"[A-Za-z0-9_.+-]+|None")
    for value in values:
        assert pattern.fullmatch(value) or value in {"[]", "{}"}, value


def test_a_whole_result_carries_no_environment_value() -> None:
    result = zero()
    joined = result.to_json()
    assert not leaked_names(joined)
    assert str(Path.home()) not in joined
