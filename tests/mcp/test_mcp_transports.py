# tests/mcp/test_mcp_transports.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP server over Streamable HTTP, mounted at ``/mcp`` and served alone.

``server/discover`` answers the 2026-07-28 revision, with its cache hints, and
each of the SDK's earlier handshake revisions initializes and then lists and
calls the tools, statelessly (no session id). The endpoint takes POST only,
refuses a foreign ``Origin`` (any ``Origin`` in hosted mode) and, served alone, a
host that is not loopback. Mounted in the REST server, a tool call runs through
the worker pool with the run's budget and the server's ``llm_use`` policy, and
counts against its client's rate limit by what it asks for; behind the edge it
needs the edge's credential; and a hosted result larger than the limit answers
a notice whose download the REST API answers. Nothing here is put in the GET run
cache.
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import pytest
from fastapi.testclient import TestClient
from mcp_support import LOOPBACK_ONLY, run_with
from server_support import client, problem, service_of
from starlette.datastructures import Headers

from pyeconomics import registry, run
from pyeconomics.mcp import build_server
from pyeconomics.mcp.server import _download
from pyeconomics.mcp.transport import http_app, origin_allowed
from pyeconomics.server.limits import RateLimits, route_kind
from pyeconomics.surfaces.budgets import GET_INPUTS_LIMIT
from pyeconomics.surfaces.invoke import BindRequest

if TYPE_CHECKING:
    from collections.abc import Generator

    from mcp import Client

    from pyeconomics.server.work import Outcome, Task

pytestmark = LOOPBACK_ONLY

MODERN = "2026-07-28"
HANDSHAKE = ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
ACCEPT = "application/json, text/event-stream"
TVM = dict(registry.get("foundations.time_value").spec.examples[0].inputs)


def modern(
    method: str, params: dict[str, Any] | None = None, *, name: str | None = None
) -> tuple[bytes, dict[str, str]]:
    """A 2026-07-28 request: its body and its headers."""
    meta = {
        "io.modelcontextprotocol/protocolVersion": MODERN,
        "io.modelcontextprotocol/clientInfo": {"name": "probe", "version": "1"},
        "io.modelcontextprotocol/clientCapabilities": {},
    }
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": method,
        "params": {**(params or {}), "_meta": meta},
    }
    headers = {
        "MCP-Protocol-Version": MODERN,
        "Mcp-Method": method,
        "Accept": ACCEPT,
        "Content-Type": "application/json",
    }
    if name is not None:
        headers["Mcp-Name"] = name
    return json.dumps(body).encode("utf-8"), headers


def legacy(
    method: str, params: dict[str, Any], version: str
) -> tuple[bytes, dict[str, str]]:
    """An earlier revision's request: no per-request metadata."""
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = {"Accept": ACCEPT, "Content-Type": "application/json"}
    if version >= "2025-06-18" and method != "initialize":
        headers["MCP-Protocol-Version"] = version
    return json.dumps(body).encode("utf-8"), headers


def post(api: TestClient, request: tuple[bytes, dict[str, str]], **extra: str) -> Any:  # noqa: ANN401
    content, headers = request
    return api.post("/mcp", content=content, headers={**headers, **extra})


def call_request(name: str, arguments: dict[str, Any]) -> tuple[bytes, dict[str, str]]:
    return modern("tools/call", {"name": name, "arguments": arguments}, name=name)


# --- the protocol revisions ---------------------------------------------------------


def test_server_discover_answers_the_2026_revision_in_memory() -> None:
    async def work(client: Client) -> dict[str, Any]:
        return await client.session.send_discover(MODERN)

    answer = run_with(build_server(), work)
    assert answer["supportedVersions"] == [MODERN]
    assert answer["capabilities"]["tools"] == {"listChanged": False}
    assert (answer["ttlMs"], answer["cacheScope"]) == (3_600_000, "public")


def test_server_discover_answers_over_http_with_its_cache_hints() -> None:
    with client() as api:
        response = post(api, modern("server/discover"))
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert "mcp-session-id" not in response.headers
    result = response.json()["result"]
    assert result["supportedVersions"] == [MODERN]
    assert result["resultType"] == "complete"
    assert (
        result["_meta"]["io.modelcontextprotocol/serverInfo"]["name"] == "pyeconomics"
    )


def test_the_tool_list_over_http_is_sorted_and_cacheable() -> None:
    with client() as api:
        result = post(api, modern("tools/list")).json()["result"]
    names = [tool["name"] for tool in result["tools"]]
    assert names == sorted(names)
    assert (result["ttlMs"], result["cacheScope"]) == (3_600_000, "public")


@pytest.mark.parametrize("version", HANDSHAKE)
def test_an_earlier_revisions_client_initializes_lists_and_calls(version: str) -> None:
    init = {
        "protocolVersion": version,
        "capabilities": {},
        "clientInfo": {"name": "older", "version": "1"},
    }
    call = {"name": "foundations_time_value", "arguments": TVM}
    with client() as api:
        started = post(api, legacy("initialize", init, version))
        listed = post(api, legacy("tools/list", {}, version))
        called = post(api, legacy("tools/call", call, version))
    assert started.json()["result"]["protocolVersion"] == version
    assert "mcp-session-id" not in started.headers
    names = [tool["name"] for tool in listed.json()["result"]["tools"]]
    assert "foundations_time_value" in names
    content = called.json()["result"]["content"]
    assert content[0]["text"] == run("foundations.time_value", TVM).to_json()


def test_a_header_that_differs_from_the_body_is_refused() -> None:
    with client() as api:
        response = post(
            api,
            call_request("foundations_time_value", TVM),
            **{"Mcp-Name": "run_model"},
        )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == -32020


# --- what the endpoint refuses ---------------------------------------------------


@pytest.mark.parametrize("method", ["GET", "DELETE", "PUT"])
def test_only_post_is_taken(method: str) -> None:
    with client() as api:
        response = api.request(method, "/mcp", headers={"Accept": ACCEPT})
    assert response.status_code == 405
    assert response.headers["allow"] == "POST"


@pytest.mark.parametrize(
    ("origin", "status"),
    [
        ("http://localhost:6274", 200),
        ("http://127.0.0.1:6274", 200),
        ("https://evil.example", 403),
        ("null", 403),
    ],
)
def test_a_local_server_admits_only_this_machines_origins(
    origin: str, status: int
) -> None:
    with client() as api:
        response = post(api, modern("server/discover"), Origin=origin)
    assert response.status_code == status


def test_origin_rules_by_mode() -> None:
    assert origin_allowed(None, "local")
    assert origin_allowed(None, "hosted")
    assert origin_allowed("https://localhost", "local")
    assert not origin_allowed("http://localhost:6274", "hosted")
    assert not origin_allowed("ftp://127.0.0.1", "local")
    assert not origin_allowed("http://[::1", "local")


@contextmanager
def alone(
    *, check_host: bool = True, base_url: str = "http://127.0.0.1"
) -> Generator[TestClient]:
    with TestClient(
        http_app(build_server(), check_host=check_host), base_url=base_url
    ) as api:
        yield api


def test_served_alone_it_answers_only_a_loopback_host() -> None:
    with alone() as api:
        assert post(api, modern("server/discover")).status_code == 200
    with alone(base_url="http://example.org") as api:
        assert post(api, modern("server/discover")).status_code == 421
    with alone(check_host=False, base_url="http://example.org") as api:
        assert post(api, modern("server/discover")).status_code == 200


def test_outside_its_lifespan_the_endpoint_is_not_running() -> None:
    api = TestClient(http_app(build_server()), base_url="http://127.0.0.1")
    assert post(api, modern("server/discover")).status_code == 503


# --- mounted in the REST server -------------------------------------------------------


def _recording(api: TestClient) -> list[Task]:
    """Record every task the app's service hands its pool."""
    service = service_of(api)
    tasks: list[Task] = []
    real = service.outcome

    async def outcome(task: Task) -> Outcome:
        tasks.append(task)
        answer: Outcome = await real(task)
        return answer

    service.outcome = outcome
    return tasks


def test_a_tool_call_runs_in_the_pool_with_the_policy_and_the_budget() -> None:
    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        tasks = _recording(api)
        response = post(api, call_request("foundations_time_value", TVM))
        cached = len(service_of(api).cache)
    result = response.json()["result"]
    assert result["content"][0]["text"] == run("foundations.time_value", TVM).to_json()
    (task,) = tasks
    assert (task.kind, task.target, task.llm_use) == (
        "run",
        "foundations.time_value",
        "allowed-only",
    )
    assert task.budget == 10.0  # time_value is a light model: the hosted budget
    assert cached == 0


def test_a_series_call_goes_to_the_pool_with_its_limit() -> None:
    with client(mcp_series_limit=7) as api:
        tasks = _recording(api)
        post(api, call_request("get_series", {"target": "us.unemployment.rate"}))
    (task,) = tasks
    assert (task.kind, task.target, task.max_observations, task.llm_use) == (
        "series",
        "us.unemployment.rate",
        7,
        "allowed-only",
    )


def test_a_worker_problem_reaches_the_client_as_a_tool_error() -> None:
    with client() as api:
        response = post(
            api, call_request("run_model", {"model_id": "macro.no_such_model"})
        )
    result = response.json()["result"]
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["type"].endswith("/model-not-found")


def test_a_large_hosted_result_answers_a_notice_the_rest_api_downloads() -> None:
    with client(
        mode="hosted", rate_limits=RateLimits.off(), mcp_result_limit=200
    ) as api:
        response = post(api, call_request("foundations_time_value", TVM))
        notice = response.json()["result"]["structuredContent"]
        download = api.get(notice["download"]["path"])
    expected = run("foundations.time_value", TVM)
    assert notice["result_sha256"] == expected.manifest.result_sha256
    assert notice["result_bytes"] == len(expected.to_json().encode("utf-8"))
    assert notice["summary"].startswith("Time value of money")
    assert download.status_code == 200
    assert download.content == expected.to_json().encode("utf-8")


def test_a_local_server_returns_a_large_result_whole() -> None:
    with client(mcp_result_limit=200) as api:
        response = post(api, call_request("foundations_time_value", TVM))
    structured = response.json()["result"]["structuredContent"]
    assert (
        structured["outputs"]
        == json.loads(run("foundations.time_value", TVM).to_json())["outputs"]
    )


def test_a_download_names_the_bind_and_none_when_the_inputs_are_too_long() -> None:
    model = registry.get("macro.policy_rule")
    bind = BindRequest(
        as_of="2019-06-28", concepts={"inflation": "us.inflation.cpi.yoy"}
    )
    path = _download(model, b'{"calculation":"taylor_1993"}', bind)
    assert path is not None
    assert path.startswith("/v1/models/macro.policy_rule/run?inputs=")
    encoded = path.split("inputs=")[1].split("&")[0]
    decoded = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    assert decoded == b'{"calculation":"taylor_1993"}'
    assert "as_of=2019-06-28" in path
    assert "concept=inflation%3Dus.inflation.cpi.yoy" in path
    spaced = _download(model, b"{}", BindRequest(parameters={"meeting": "2019 06"}))
    assert (
        spaced
        == "/v1/models/macro.policy_rule/run?profile=default&param=meeting%3D2019+06"
    )
    assert _download(model, b"{}", None) == "/v1/models/macro.policy_rule/run"
    long = b'{"x":"' + b"a" * GET_INPUTS_LIMIT + b'"}'
    assert _download(model, long, None) is None


def test_behind_the_edge_mcp_needs_its_credential(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential = secrets.token_urlsafe(32)
    monkeypatch.setenv("PYECONOMICS_EDGE_CREDENTIAL", credential)
    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        refused = post(api, modern("server/discover"))
        admitted = post(
            api, modern("server/discover"), **{"X-Pyeconomics-Edge": credential}
        )
    assert refused.status_code == 403
    assert problem(refused)["type"].endswith("/edge-required")
    assert admitted.status_code == 200


def test_hosted_mcp_refuses_any_origin() -> None:
    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        response = post(api, modern("server/discover"), Origin="http://localhost:6274")
    assert response.status_code == 403


def _kind(headers: dict[str, str]) -> str | None:
    return route_kind("/mcp", Headers(headers))


def test_an_mcp_request_counts_by_what_its_checked_headers_ask_for() -> None:
    call = {"mcp-protocol-version": MODERN, "mcp-method": "tools/call"}
    assert _kind({**call, "mcp-name": "get_series"}) == "series"
    assert _kind({**call, "mcp-name": "search_models"}) == "metadata"
    assert _kind({**call, "mcp-name": "list_sources"}) == "metadata"
    assert _kind({**call, "mcp-name": "run_model"}) == "runs"
    assert _kind({**call, "mcp-name": "fixed_income_duration"}) == "runs"
    assert (
        _kind({"mcp-protocol-version": MODERN, "mcp-method": "tools/list"})
        == "metadata"
    )
    # An earlier revision's headers are unchecked: it counts as a run.
    assert _kind({"mcp-method": "tools/list"}) == "runs"
    assert (
        _kind({"mcp-protocol-version": "2025-11-25", "mcp-method": "tools/list"})
        == "runs"
    )
    assert route_kind("/mcp/", None) == "runs"
    assert route_kind("/v1/models", None) == "metadata"


def test_hosted_runs_over_mcp_count_against_the_run_limit() -> None:
    limits = RateLimits(runs="1/minute", series=None, metadata=None)
    with client(mode="hosted", rate_limits=limits) as api:
        first = post(api, call_request("foundations_time_value", TVM))
        second = post(api, call_request("foundations_time_value", TVM))
        listing = post(api, modern("tools/list"))
    assert first.status_code == 200
    assert second.status_code == 429
    assert problem(second)["type"].endswith("/too-many-requests")
    assert listing.status_code == 200


def test_the_access_line_names_the_endpoint(caplog: pytest.LogCaptureFixture) -> None:
    with (
        caplog.at_level(logging.INFO, logger="pyeconomics.server.access"),
        client() as api,
    ):
        post(api, modern("server/discover"))
    lines = [
        r.getMessage() for r in caplog.records if r.name == "pyeconomics.server.access"
    ]
    assert any(line.startswith("POST /mcp 200 ") for line in lines), lines


def test_the_server_classes_every_discovery_tool_and_mounts_one_path() -> None:
    from pyeconomics.mcp import transport  # noqa: PLC0415
    from pyeconomics.mcp.tools import DISCOVERY_TOOLS  # noqa: PLC0415
    from pyeconomics.server import limits  # noqa: PLC0415

    call = {"mcp-protocol-version": MODERN, "mcp-method": "tools/call"}
    kinds = {name: _kind({**call, "mcp-name": name}) for name in DISCOVERY_TOOLS}
    assert kinds == {
        "search_models": "metadata",
        "describe_model": "metadata",
        "run_model": "runs",
        "get_series": "series",
        "list_sources": "metadata",
    }
    assert limits.MCP_PATH == transport.MCP_PATH


@pytest.mark.parametrize(
    "settings",
    [
        {"mode": "remote"},
        {"result_limit": 0},
        {"series_limit": True},
        {"result_limit": 1.5},
    ],
)
def test_build_server_refuses_a_bad_mode_or_limit(settings: dict[str, Any]) -> None:
    from pyeconomics.core import InputError  # noqa: PLC0415

    with pytest.raises(InputError):
        build_server(**settings)


def test_a_worker_applies_the_policy_to_a_series_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from mcp_support import stub_world  # noqa: PLC0415

    from pyeconomics.server.work import Task, execute  # noqa: PLC0415

    stub_world(monkeypatch)
    allowed = execute(
        Task(
            kind="series",
            target="us.unemployment.rate",
            llm_use="allowed-only",
            max_observations=3,
        )
    )
    assert allowed.problem is None
    document = json.loads(allowed.body)
    assert len(document["frame"]["index"]) == 3
    assert {record["llm_use"] for record in document["sources"]} == {"allowed"}
    refused = execute(Task(kind="series", target="fred:UNRATE", llm_use="allowed-only"))
    assert refused.problem is not None
    assert refused.problem.slug == "llm-use-forbidden"


def test_without_the_extra_the_app_mounts_no_mcp(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import importlib.util  # noqa: PLC0415

    real = importlib.util.find_spec

    def find_spec(name: str, *args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
        return None if name == "mcp" else real(name, *args, **kwargs)

    monkeypatch.setattr(importlib.util, "find_spec", find_spec)
    with client() as api:
        routes = api.app.routes  # type: ignore[attr-defined] # ty: ignore[unresolved-attribute]
        paths = [getattr(route, "path", None) for route in routes]
        response = post(api, modern("server/discover"))
    assert "/mcp" not in paths
    assert response.status_code == 404
