# tests/server/test_server_every_model.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every registered model's first example through POST and GET (Phase 4 Step 6).

Each run must answer exactly the bytes of ``pyeconomics.run(...).to_json()``,
through the POST form (the inputs as the body) and the GET form (``?inputs=``,
base64url), and the body must validate against the model's own result schema in
the OpenAPI document. A model whose extra leaves its package out of this Python
(arch on CPython 3.15) must answer the ``missing-extra`` problem naming the extra
(tests/extra_gaps.py), never pass silently.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from extra_gaps import excluded_gap
from jsonschema import Draft202012Validator
from server_support import LOOPBACK_ONLY, client, encode, problem

import pyeconomics
from pyeconomics import registry
from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from collections.abc import Iterator

    from fastapi.testclient import TestClient

pytestmark = LOOPBACK_ONLY


@pytest.fixture(scope="module")
def api() -> Iterator[TestClient]:
    with client() as test_client:
        yield test_client


@pytest.fixture(scope="module")
def document(api: TestClient) -> dict[str, Any]:
    body: dict[str, Any] = api.get("/openapi.json").json()
    return body


@pytest.mark.parametrize("model_id", registry.ids())
def test_post_and_get_answer_the_bytes_of_run(
    model_id: str, api: TestClient, document: dict[str, Any]
) -> None:
    model = registry.get(model_id)
    inputs = model.spec.examples[0].inputs
    path = f"/v1/models/{model_id}/run"
    posted = api.post(path, content=canonical_json(inputs))
    got = api.get(path, params={"inputs": encode(inputs)})
    gap = excluded_gap(model)
    if gap is not None:
        for response in (posted, got):
            assert response.status_code == 501
            body = problem(response)
            assert body["type"].endswith("/missing-extra")
            assert f"pyeconomics[{model.spec.extra}]" in body["detail"]
        return
    expected = pyeconomics.run(model_id, inputs).to_json().encode("utf-8")
    assert (posted.status_code, got.status_code) == (200, 200)
    assert posted.headers["content-type"] == "application/json"
    assert posted.content == expected
    assert got.content == expected
    schema = {"$ref": f"#/components/schemas/{model_id}.result", **document}
    Draft202012Validator(schema).validate(posted.json())
