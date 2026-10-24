# tests/server/test_openapi_snapshot.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The REST API's OpenAPI 3.1 document: its snapshot and its shape (Step 6).

The paths, operations, parameters and shared schemas are public API at 1.0.0
(ADR-0003), and FastAPI builds part of them, so the document is held to a syrupy
snapshot (through tests/json_snapshots.py's ``LFJSONExtension``): a FastAPI
release that changes it fails here until the snapshot is updated in its pull
request (``uv run pytest tests/server --snapshot-update``, then review the
diff). Each model's own schemas, which tests/surfaces/__snapshots__ already
holds readably, are recorded by their SHA-256, and ``info.version`` as a
placeholder, so a release changes neither.

Beside the snapshot: every reference resolves; each model has one POST and one
GET operation, named from its id, whose request body and result are its own
input and output schemas (moved into ``components`` with their ``$defs``, and
nothing else changed); the document is canonical, the same in both modes, and
holds no host or server; and ``pyeconomics registry export`` writes it.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any

import pytest
from cli_support import cli
from json_snapshots import LFJSONExtension
from server_support import LOOPBACK_ONLY

from pyeconomics import __version__, registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.server import ServerSettings, create_app
from pyeconomics.server.openapi import (
    PROBLEM_MEDIA_TYPE,
    REF,
    openapi_document,
    write_openapi,
)

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from syrupy.assertion import SnapshotAssertion

pytestmark = LOOPBACK_ONLY

METHODS = ("get", "post")


@pytest.fixture(scope="module")
def document() -> dict[str, Any]:
    return openapi_document()


def _model_component(name: str) -> bool:
    return any(name.startswith(f"{model_id}.") for model_id in registry.ids())


def test_the_document_matches_its_snapshot(
    document: dict[str, Any], snapshot: SnapshotAssertion
) -> None:
    assert document["info"]["version"] == __version__
    recorded = {**document, "info": {**document["info"], "version": "<version>"}}
    schemas = dict(document["components"]["schemas"])
    for name, schema in schemas.items():
        if _model_component(name):
            schemas[name] = (
                "sha256:" + hashlib.sha256(canonical_json(schema)).hexdigest()
            )
    recorded["components"] = {**document["components"], "schemas": schemas}
    assert snapshot.use_extension(LFJSONExtension) == recorded


def _references(value: object) -> Iterator[str]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "$ref" and isinstance(item, str):
                yield item
            elif key == "mapping" and isinstance(item, dict):
                yield from (
                    target for target in item.values() if isinstance(target, str)
                )
            else:
                yield from _references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _references(item)


def test_every_reference_resolves(document: dict[str, Any]) -> None:
    schemas = document["components"]["schemas"]
    references = set(_references(document))
    assert references
    assert all(reference.startswith(REF) for reference in references)
    assert {reference.removeprefix(REF) for reference in references} <= set(schemas)
    assert not any("$defs" in reference for reference in references)
    assert "HTTPValidationError" not in schemas


def test_it_is_openapi_3_1_with_no_server_or_host(document: dict[str, Any]) -> None:
    assert document["openapi"] == "3.1.0"
    assert "servers" not in document
    text = canonical_json(document).decode()
    assert "127.0.0.1" not in text
    assert "localhost" not in text
    assert "testserver" not in text


def test_each_model_has_its_own_post_and_get_operations(
    document: dict[str, Any],
) -> None:
    operations = [
        operation["operationId"]
        for item in document["paths"].values()
        for operation in item.values()
    ]
    assert len(operations) == len(set(operations))
    for model in registry.models():
        item = document["paths"][f"/v1/models/{model.id}/run"]
        assert sorted(item) == list(METHODS)
        stem = "run_" + model.id.replace(".", "_")
        assert item["post"]["operationId"] == stem
        assert item["get"]["operationId"] == f"{stem}_get"
        for method in METHODS:
            operation = item[method]
            assert operation["tags"] == [model.spec.domain]
            content = operation["responses"]["200"]["content"]
            assert content["application/json"]["schema"] == {
                "$ref": f"{REF}{model.id}.result"
            }
        body = item["post"]["requestBody"]["content"]["application/json"]["schema"]
        assert body == {"$ref": f"{REF}{model.id}.input"}
        names = [parameter["name"] for parameter in item["get"]["parameters"]]
        assert names[0] == "inputs"


def _restore(value: Any, prefix: str) -> Any:  # noqa: ANN401 - JSON values
    """Point references back into ``$defs``: the inverse of the document's move."""
    if isinstance(value, list):
        return [_restore(item, prefix) for item in value]
    if not isinstance(value, dict):
        if isinstance(value, str) and value.startswith(REF + prefix):
            return "#/$defs/" + value.removeprefix(REF + prefix)
        return value
    restored: dict[str, Any] = {}
    for key, item in value.items():
        if key == "mapping" and isinstance(item, dict):
            restored[key] = {
                tag: _restore(target, prefix) for tag, target in item.items()
            }
        else:
            restored[key] = _restore(item, prefix)
    return restored


@pytest.mark.parametrize("model_id", registry.ids())
def test_a_models_components_are_its_own_schemas(
    model_id: str, document: dict[str, Any]
) -> None:
    schemas = document["components"]["schemas"]
    model = registry.get(model_id)
    for side, built in (
        ("input", input_schema(model)),
        ("output", output_schema(model)),
    ):
        name = f"{model_id}.{side}"
        expected = {k: v for k, v in built.items() if k not in {"$schema", "$id"}}
        moved = {
            key.removeprefix(f"{name}."): _restore(schema, f"{name}.")
            for key, schema in schemas.items()
            if key.startswith(f"{name}.")
        }
        restored = _restore(schemas[name], f"{name}.")
        if moved:
            restored["$defs"] = moved
        assert restored == expected
    result = schemas[f"{model_id}.result"]
    assert result["properties"]["model_id"] == {"const": model_id}
    assert result["properties"]["inputs"] == {"$ref": f"{REF}{model_id}.input"}


def test_every_operation_answers_problems(document: dict[str, Any]) -> None:
    for item in document["paths"].values():
        for operation in item.values():
            for status in ("4XX", "5XX"):
                content = operation["responses"][status]["content"]
                assert content[PROBLEM_MEDIA_TYPE]["schema"] == {
                    "$ref": f"{REF}Problem"
                }


def test_the_document_is_the_same_in_both_modes(document: dict[str, Any]) -> None:
    hosted = create_app(mode="hosted", settings=ServerSettings(workers=0)).openapi()
    assert canonical_json(hosted) == canonical_json(document)


def test_write_openapi_writes_canonical_bytes(
    document: dict[str, Any], tmp_path: Path
) -> None:
    path = tmp_path / "openapi.json"
    write_openapi(path)
    assert path.read_bytes() == canonical_json(document)


def _empty_registry(path: Path, *, figures: bool) -> None:
    del figures
    path.write_bytes(b"{}")


def test_registry_export_writes_openapi_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    from pyeconomics.surfaces import registry_export  # noqa: PLC0415

    monkeypatch.setattr(registry_export, "write_registry", _empty_registry)
    outcome = cli("registry", "export", "--out", str(tmp_path))
    assert (outcome.code, outcome.stderr) == (0, "")
    assert (
        outcome.text == f"{tmp_path / 'registry.json'}\n{tmp_path / 'openapi.json'}\n"
    )
    assert (tmp_path / "openapi.json").read_bytes() == canonical_json(
        openapi_document()
    )


def test_registry_export_skips_openapi_json_without_the_server_extra(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    import sys  # noqa: PLC0415

    from pyeconomics.surfaces import registry_export  # noqa: PLC0415

    monkeypatch.setattr(registry_export, "write_registry", _empty_registry)
    monkeypatch.setitem(sys.modules, "fastapi", None)
    outcome = cli("registry", "export", "--out", str(tmp_path))
    assert outcome.code == 0
    assert outcome.text == f"{tmp_path / 'registry.json'}\n"
    assert outcome.stderr.startswith("openapi.json skipped: ")
    assert "pyeconomics[server]" in outcome.stderr
    assert not (tmp_path / "openapi.json").exists()
