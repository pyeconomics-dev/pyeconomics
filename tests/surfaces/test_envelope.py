# tests/surfaces/test_envelope.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The envelope's bytes, entity tag and summary (ADR-0012 decisions 3 and 12)."""

from __future__ import annotations

import datetime as dt

import bound_support as bs
import pytest
import toy_models as toys

from pyeconomics.core import run_model
from pyeconomics.data import bind_model
from pyeconomics.surfaces import envelope
from pyeconomics.surfaces.envelope import canonical_bytes, etag, summary


def test_the_bytes_are_the_canonical_json_in_utf8() -> None:
    result = run_model(toys.zero_coupon, {"face_value": 100, "rate": 0.05, "years": 10})
    assert canonical_bytes(result) == result.to_json().encode("utf-8")


def test_the_entity_tag_is_weak_and_names_the_result_hash() -> None:
    result = run_model(toys.zero_coupon, {"face_value": 100, "rate": 0.05, "years": 10})
    assert etag(result) == f'W/"{result.manifest.result_sha256}"'


def test_a_summary_names_the_model_its_outputs_and_its_warnings() -> None:
    result = run_model(toys.mean_return, {"returns": [0.0, 0.0]})
    assert summary(result) == (
        "Toy arithmetic mean return (foundations.toy_mean_return, version 1): "
        "mean = 0, count = 2. Warnings: all_zero."
    )


def test_a_summary_names_the_providers_but_not_a_supplied_value() -> None:
    bound = bind_model(
        bs.unemployment_change, as_of=dt.date(2024, 9, 30), registry=bs.world()
    )
    assert summary(run_model(bs.unemployment_change, bound)).endswith(
        " Data from fred."
    )
    supplied = bind_model(
        bs.unemployment, overrides={"unemployment": 0.04}, registry=bs.world()
    )
    assert "Data from" not in summary(run_model(bs.unemployment, supplied))


def test_a_summary_counts_the_outputs_past_its_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(envelope, "MAX_SUMMARY_OUTPUTS", 1)
    result = run_model(toys.mean_return, {"returns": [0.01, 0.03]})
    assert summary(result).endswith(": mean = 0.02, and 1 more.")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, "undefined"),
        ([], "0 values"),
        ([1.0, 2.0], "2 values"),
        ([[1.0], [2.0], [3.0]], "3 rows"),
        ({"a": 1}, "1 entries"),
        ("street", "street"),
        (True, "true"),
        (1e-7, "1e-7"),
    ],
)
def test_an_output_is_described_in_a_few_words(value: object, expected: str) -> None:
    assert envelope._value(value) == expected  # noqa: SLF001
