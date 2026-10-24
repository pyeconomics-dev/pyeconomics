# tests/server/test_server_runs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Model runs over the API: binding, the GET form and the body's limits (Step 6).

The toy bound models and the scripted providers of
tests/data/bindings/bound_support.py are the installed registries, so a bound
run reads no network: it must answer the bytes ``invoke`` gives for the same
bind request. The GET form's ``?inputs=`` must be base64url without padding and
at most 8,192 characters; a body is refused above the mode's limit before it is
decoded, and an empty body is a run with no inputs.
"""

from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING

import pytest
from cli_support import install_world
from server_support import (
    LOOPBACK_ONLY,
    client,
    encode,
    problem,
    service_of,
)

from pyeconomics import data
from pyeconomics.core.canonical import canonical_json
from pyeconomics.surfaces.budgets import GET_INPUTS_LIMIT, HOSTED_BODY_LIMIT
from pyeconomics.surfaces.envelope import canonical_bytes
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = LOOPBACK_ONLY

UNEMPLOYMENT = "macro.toy_unemployment"
RUN = f"/v1/models/{UNEMPLOYMENT}/run"
PAST = "2024-03-20"


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> None:
    install_world(monkeypatch)


def test_a_bound_run_answers_the_bytes_of_invoke(world: None) -> None:
    del world
    expected = invoke(UNEMPLOYMENT, {"weight": 2.0}, bind=BindRequest(as_of=PAST))
    with client() as api:
        posted = api.post(RUN, params={"as_of": PAST}, content=b'{"weight": 2}')
        got = api.get(RUN, params={"as_of": PAST, "inputs": encode({"weight": 2})})
    assert posted.status_code == 200
    assert posted.content == canonical_bytes(expected) == got.content
    records = posted.json()["manifest"]["data_sources"]
    assert [record["provider"] for record in records] == ["fred"]


def test_an_empty_body_binds_every_input(world: None) -> None:
    del world
    expected = invoke(UNEMPLOYMENT, None, bind=BindRequest(as_of=PAST))
    with client() as api:
        response = api.post(RUN, params={"as_of": PAST})
    assert response.content == canonical_bytes(expected)


@pytest.mark.parametrize(
    ("params", "request_"),
    [
        ({"profile": "default"}, BindRequest()),
        ({"vintage": "latest"}, BindRequest(vintage="latest")),
        ({"profile": "uk"}, BindRequest(profile="uk")),
        (
            {"as_of": PAST, "concept": "unemployment=us.unemployment.rate"},
            BindRequest(as_of=PAST, concepts={"unemployment": "us.unemployment.rate"}),
        ),
    ],
    ids=["profile", "vintage", "uk", "concept"],
)
def test_every_bind_parameter_reaches_the_bind(
    world: None, params: dict[str, str], request_: BindRequest
) -> None:
    del world
    from pyeconomics.data import cache  # noqa: PLC0415

    with cache.bypass():
        expected = invoke(UNEMPLOYMENT, {}, bind=request_)
    with client() as api:
        response = api.post(RUN, params=params, content=b"{}")
    assert response.status_code == 200
    assert response.content == canonical_bytes(expected)


def test_parameters_and_concepts_reach_the_bind_request() -> None:
    from starlette.requests import Request  # noqa: PLC0415

    from pyeconomics.server import app  # noqa: PLC0415

    text = f"as_of={PAST}&concept=a%3Db&param=meeting%3D2024-03&param=x%3D"
    request = Request({"type": "http", "query_string": text.encode(), "headers": []})
    query = app._Query(request, app._RUN_QUERY, app._REPEATED)  # noqa: SLF001
    bound = app._bind(query)  # noqa: SLF001
    assert (
        bound
        == BindRequest(
            as_of=PAST, concepts={"a": "b"}, parameters={"meeting": "2024-03", "x": ""}
        ).to_dict()
    )


@pytest.mark.parametrize(
    "params",
    [
        {"as_of": "2024-13-40"},
        {"vintage": "sometimes"},
        {"concept": "unemployment"},
        {"param": "=x"},
        {"format": "pdf"},
        {"colour": "blue"},
    ],
    ids=["date", "vintage", "concept", "param", "format", "unknown"],
)
def test_a_bad_run_query_is_invalid_input(world: None, params: dict[str, str]) -> None:
    del world
    with client() as api:
        response = api.post(RUN, params=params, content=b"{}")
    assert response.status_code == 422
    assert problem(response)["type"].endswith("/invalid-input")


def test_a_concept_named_twice_is_refused(world: None) -> None:
    del world
    with client() as api:
        response = api.post(
            f"{RUN}?concept=unemployment=a.b.c&concept=unemployment=d.e.f", content=b""
        )
    assert response.status_code == 422
    assert "twice" in problem(response)["detail"]


def test_hosted_mode_configures_the_data_layer_once(world: None) -> None:
    del world
    with client(mode="hosted") as api:
        assert data.settings().mode == "hosted"
        response = api.post(RUN, params={"as_of": PAST}, content=b"{}")
    assert response.status_code == 200
    body = response.json()
    assert [r["provider"] for r in body["manifest"]["data_sources"]] == ["bls"]
    assert "revised_data" in {warning["code"] for warning in body["warnings"]}


# --- the GET form -------------------------------------------------------------------

TIME_VALUE = "/v1/models/foundations.time_value/run"
INPUTS = {
    "calculation": "present_value",
    "rate": 0.05,
    "periods": 10,
    "future_value": 1,
}


def test_the_get_form_takes_padding_free_base64url_only() -> None:
    text = base64.urlsafe_b64encode(canonical_json(INPUTS)).decode()
    with client() as api:
        good = api.get(TIME_VALUE, params={"inputs": text.rstrip("=")})
        padded = api.get(
            TIME_VALUE, params={"inputs": text + "=" * (4 - len(text) % 4)}
        )
        plus = api.get(TIME_VALUE, params={"inputs": "ab+c"})
        short = api.get(TIME_VALUE, params={"inputs": "abcde"})
    assert good.status_code == 200
    for refused in (padded, plus, short):
        assert refused.status_code == 422
        assert "base64url" in problem(refused)["detail"]


def test_a_long_get_form_is_too_large_and_points_to_post() -> None:
    with client() as api:
        response = api.get(TIME_VALUE, params={"inputs": "A" * (GET_INPUTS_LIMIT + 1)})
    assert response.status_code == 413
    body = problem(response)
    assert body["type"].endswith("/input-too-large")
    assert "POST" in body["detail"]


def test_a_get_form_without_inputs_runs_on_none() -> None:
    with client() as api:
        empty = api.get(TIME_VALUE, params={"inputs": ""})
        absent = api.get(TIME_VALUE)
    for response in (empty, absent):
        assert response.status_code == 422
        assert problem(response)["errors"]


def test_a_post_form_rejects_inputs_in_the_query() -> None:
    with client() as api:
        response = api.post(TIME_VALUE, params={"inputs": encode(INPUTS)}, content=b"")
    assert response.status_code == 422


# --- the body -----------------------------------------------------------------------


def _chunks(total: int) -> Iterator[bytes]:
    sent = 0
    while sent < total:
        yield b" " * 1024
        sent += 1024


def test_a_body_above_the_local_limit_is_refused_before_decoding() -> None:
    with client() as api:
        service_of(api).body_limit = 64
        declared = api.post(TIME_VALUE, content=json.dumps(INPUTS).ljust(100).encode())
        streamed = api.post(TIME_VALUE, content=_chunks(4096))
        fits = api.post(TIME_VALUE, content=b'{"calculation": "npv"}')
    for response in (declared, streamed):
        assert response.status_code == 413
        assert "Python API" in problem(response)["detail"]
    assert fits.status_code == 422  # decoded, then the model's own validation


def test_hosted_mode_refuses_a_body_above_one_mebibyte() -> None:
    with client(mode="hosted") as api:
        response = api.post(TIME_VALUE, content=b" " * (HOSTED_BODY_LIMIT + 1))
    assert response.status_code == 413
    body = problem(response)
    assert str(HOSTED_BODY_LIMIT) in body["detail"]
    assert "locally" in body["detail"]


def test_an_unknown_model_is_model_not_found_through_either_form() -> None:
    with client() as api:
        posted = api.post("/v1/models/foundations.time_valu/run", content=b"{}")
        got = api.get("/v1/models/foundations.time_valu/run")
    for response in (posted, got):
        assert response.status_code == 404
        assert "foundations.time_value" in problem(response)["detail"]
