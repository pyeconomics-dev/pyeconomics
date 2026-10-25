# tests/server/test_server_problems.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every error reaches the caller as a problem from the error table (Step 6).

Each row of the table is driven through the API by a toy model that raises its
error in a run, and the serving errors also by the request that causes them: an
unknown route, an unknown method (with ``Allow``), a host a local server does
not answer for, a full queue (with ``Retry-After``). FastAPI's own validation
error, from a route that declares a typed parameter, is the invalid-input
problem; an unexpected exception in a route answers 500 with fixed text and is
not raised further. Each problem is logged once, and each request as one line
naming its route's template.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from fastapi.testclient import TestClient
from server_support import (
    LOCAL,
    LOOPBACK_ONLY,
    client,
    problem,
    service_of,
    use_toys,
)

from pyeconomics.core.canonical import canonical_json
from pyeconomics.server import ServerSettings, create_app
from pyeconomics.surfaces.problems import ROWS, Row
from pyeconomics.surfaces.service import ServerBusyError

if TYPE_CHECKING:
    from pyeconomics.server.work import Outcome, Task

pytestmark = LOOPBACK_ONLY

FAIL = "/v1/models/foundations.toy_fail/run"


@pytest.mark.parametrize("row", ROWS, ids=lambda row: row.slug)
def test_every_row_reaches_a_run_as_its_problem(
    row: Row, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_toys(monkeypatch)
    inputs = {"error": row.error_name, "message": "a planted failure"}
    with client() as api:
        response = api.post(FAIL, content=canonical_json(inputs))
    assert response.status_code == row.status
    body = problem(response)
    assert (body["type"], body["title"]) == (row.type_uri, row.title)
    if row.slug == "upstream-rate-limited":
        assert response.headers["retry-after"] == "3"
    if row.slug == "server-busy":
        assert response.headers["retry-after"] == "1"
    if row.slug == "too-many-requests":
        assert response.headers["retry-after"] == "1"
        assert body["retry_after"] == 0.4
    if row.slug == "limits-unavailable":
        assert response.headers["retry-after"] == "5"
    assert response.headers["cache-control"] == "no-store"
    if row.slug == "internal-error":
        assert body["detail"] == "An unexpected error stopped the request."


def test_an_unknown_route_is_route_not_found() -> None:
    with client() as api:
        response = api.get("/v2/models")
    assert response.status_code == 404
    assert problem(response)["type"].endswith("/route-not-found")


def test_an_unknown_method_is_method_not_allowed_with_allow() -> None:
    with client() as api:
        on_health = api.delete("/healthz")
        on_run = api.put("/v1/models/foundations.time_value/run")
    assert on_health.status_code == 405
    assert problem(on_health)["type"].endswith("/method-not-allowed")
    assert on_health.headers["allow"] == "GET"
    assert on_run.headers["allow"] == "GET, POST"
    assert "GET, POST" in problem(on_run)["detail"]


@pytest.mark.parametrize(
    "base_url", ["http://evil.example", "http://192.168.1.20:8000", "http://0.0.0.0"]
)
def test_a_local_server_answers_only_for_loopback_names(base_url: str) -> None:
    with client(base_url=base_url) as api:
        response = api.get("/healthz")
    assert response.status_code == 400
    assert problem(response)["type"].endswith("/host-not-allowed")


@pytest.mark.parametrize(
    "base_url", ["http://127.0.0.1:8000", "http://localhost", "http://[::1]:8000"]
)
def test_loopback_names_are_answered(base_url: str) -> None:
    with client(base_url=base_url) as api:
        assert api.get("/healthz").status_code == 200


def test_allow_remote_and_hosted_mode_answer_any_host() -> None:
    with client(base_url="http://evil.example", allow_remote=True) as api:
        assert api.get("/healthz").status_code == 200
    with client(mode="hosted", base_url="http://api.example.org") as api:
        assert api.get("/healthz").status_code == 200


class _BusyPool:
    def start(self) -> None:
        """Nothing to start."""

    async def submit(self, task: Task) -> Outcome:
        del task
        raise ServerBusyError(4)

    def close(self) -> None:
        """Nothing to stop."""


def test_a_full_queue_is_server_busy_with_retry_after() -> None:
    with client() as api:
        service_of(api).pool = _BusyPool()
        response = api.post("/v1/models/foundations.time_value/run", content=b"{}")
        service_of(api).pool = None
    assert response.status_code == 503
    assert problem(response)["type"].endswith("/server-busy")
    assert response.headers["retry-after"] == "1"


def test_fastapis_own_validation_is_the_invalid_input_problem() -> None:
    app = create_app(settings=ServerSettings(workers=0))

    async def typed(count: int) -> dict[str, int]:
        return {"count": count}

    app.add_api_route("/typed", typed, methods=["GET"])
    with TestClient(app, base_url=LOCAL) as api:
        response = api.get("/typed", params={"count": "many"})
        fine = api.get("/typed", params={"count": "3"})
    assert response.status_code == 422
    body = problem(response)
    assert body["type"].endswith("/invalid-input")
    assert "query.count" in body["detail"]
    assert "many" not in body["detail"]
    assert fine.json() == {"count": 3}


def test_an_unexpected_exception_answers_fixed_text_and_is_not_raised(
    caplog: pytest.LogCaptureFixture,
) -> None:
    app = create_app(settings=ServerSettings(workers=0))

    async def broken() -> None:
        msg = "C:/Users/someone/secret.toml could not be read"
        raise RuntimeError(msg)

    app.add_api_route("/broken", broken, methods=["GET"])
    with (
        caplog.at_level(logging.INFO, "pyeconomics.server"),
        TestClient(app, base_url=LOCAL) as api,
    ):
        response = api.get("/broken")
    assert response.status_code == 500
    assert problem(response)["detail"] == "An unexpected error stopped the request."
    logged = [record.getMessage() for record in caplog.records]
    assert any(line.startswith("internal-error (500, RuntimeError)") for line in logged)
    assert not any("someone" in line for line in logged)
    assert all(record.exc_info is None for record in caplog.records)


def test_each_problem_and_request_is_logged_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.INFO, "pyeconomics.server"), client() as api:
        api.get("/v1/models/foundations.time_valu")
        api.get("/v1/series/fred:UNRATE?api_key=planted")
    problems = [r for r in caplog.records if r.name == "pyeconomics.server"]
    access = [
        r.getMessage() for r in caplog.records if r.name == "pyeconomics.server.access"
    ]
    assert [r.getMessage().split(" ")[0] for r in problems] == [
        "model-not-found",
        "invalid-input",
    ]
    assert access[0].startswith("GET /v1/models/{model_id} 404 ")
    assert access[1].startswith("GET /v1/series/{target} 422 ")
    assert not any("planted" in line or "UNRATE" in line for line in access)


def test_a_run_without_the_lifespan_is_an_internal_error() -> None:
    app = create_app(settings=ServerSettings(workers=0))
    api = TestClient(app, base_url=LOCAL)  # no lifespan: the pool never started
    response = api.post("/v1/models/foundations.time_value/run", content=b"{}")
    assert response.status_code == 500
    assert problem(response)["detail"] == "An unexpected error stopped the request."
