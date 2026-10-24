# tests/surfaces/test_registry_snapshots.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Snapshots of the public schemas: an unintended change fails CI (ADR-0003).

Model ids, input and output field names, units and their JSON Schemas are public
API at 1.0.0, and the registry schema is the contract registry.json keeps. Each
model's input and output schema, the registry schema and the (id, version,
domain) index are held as JSON files under ``__snapshots__/``. A model without
snapshots, a changed schema and a snapshot no test uses all fail the suite.

After an intended change, rewrite the snapshots and review the diff:

    uv run pytest tests/surfaces --snapshot-update

and name every changed schema in CHANGELOG.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from json_snapshots import LFJSONExtension

from pyeconomics import registry
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.surfaces.registry_schema import REGISTRY_SCHEMA

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

    from pyeconomics.core.model import Model

MODELS = registry.models()
SNAPSHOTS = Path(__file__).parent / "__snapshots__" / Path(__file__).stem


@pytest.fixture
def snapshot_json(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """The snapshot fixture, one LF JSON file per assertion."""
    return snapshot.use_extension(LFJSONExtension)


@pytest.mark.parametrize("model", MODELS, ids=[m.id for m in MODELS])
def test_input_schema(model: Model[Any, Any], snapshot_json: SnapshotAssertion) -> None:
    assert input_schema(model) == snapshot_json


@pytest.mark.parametrize("model", MODELS, ids=[m.id for m in MODELS])
def test_output_schema(
    model: Model[Any, Any], snapshot_json: SnapshotAssertion
) -> None:
    assert output_schema(model) == snapshot_json


def test_registry_schema(snapshot_json: SnapshotAssertion) -> None:
    assert snapshot_json == REGISTRY_SCHEMA


def test_model_index(snapshot_json: SnapshotAssertion) -> None:
    index = [
        {"id": model.id, "version": model.version, "domain": model.spec.domain}
        for model in MODELS
    ]
    assert snapshot_json == index


def test_the_snapshot_files_are_exactly_the_models_and_the_registry() -> None:
    # Syrupy fails on a missing or unused snapshot too; this holds the set even
    # if a run passes --snapshot-warn-unused.
    expected = {
        f"test_{side}_schema[{model.id}].json"
        for model in MODELS
        for side in ("input", "output")
    } | {"test_registry_schema.json", "test_model_index.json"}
    assert {path.name for path in SNAPSHOTS.iterdir()} == expected
