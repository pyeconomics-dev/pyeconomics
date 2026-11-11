# tests/repo/test_growth_metrics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Tests for scripts/growth_metrics.py, Gate G2's weekly ledger (Phase 5 Step 15).

The script's HTTP is replaced by a stand-in that answers from the responses
recorded under ``tests/repo/growth/``, so no socket opens. The table holds
counts and markers only; a failing source gives "unavailable" rows, never a
crash; every request goes to a declared host; no credential reaches the
table.
"""

from __future__ import annotations

import base64
import datetime as dt
import importlib.util
import io
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from email.message import Message
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "growth_metrics.py"
RECORDED = Path(__file__).resolve().parent / "growth"
NOW = dt.datetime(2026, 11, 11, 12, tzinfo=dt.UTC)
# Stand-ins for the workflow's secrets: never real, never printed.
TOKEN = "gho_" + "x" * 8
GRAFANA_TOKEN = "glc_" + "y" * 8
GRAFANA_URL = "https://prometheus-prod-56-prod-us-east-3.grafana.net/api/prom"
GRAFANA_USER = "1234567"


@pytest.fixture(scope="module")
def growth() -> ModuleType:
    """Load the script as a module, by path."""
    spec = importlib.util.spec_from_file_location("growth_metrics", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["growth_metrics"] = module
    spec.loader.exec_module(module)
    return module


def recorded(name: str) -> object:
    """A response recorded under tests/repo/growth/."""
    return json.loads((RECORDED / name).read_text(encoding="utf-8"))


def http_error(url: str, code: int) -> urllib.error.HTTPError:
    """The error urllib raises for a status ``code``."""
    return urllib.error.HTTPError(url, code, "error", Message(), io.BytesIO(b""))


class World:
    """Answers each request from the recordings, and records what was asked."""

    def __init__(self, github: object | None = None) -> None:
        self.requests: list[urllib.request.Request] = []
        self.github = recorded("github-graphql.json") if github is None else github

    def __call__(self, request: urllib.request.Request) -> object:
        self.requests.append(request)
        url = request.full_url
        parts = urllib.parse.urlsplit(url)
        if parts.hostname == "pypistats.org":
            if "pyeconomics-app" in parts.path:
                raise http_error(url, 404)
            return recorded("pypistats-pyeconomics.json")
        if parts.hostname == "api.github.com":
            return self.github
        query = urllib.parse.parse_qs(parts.query)["query"][0]
        return recorded(
            "prometheus-mcp.json"
            if 'http_route="/mcp"' in query
            else "prometheus-api.json"
        )


ENVIRON = {
    "GITHUB_TOKEN": TOKEN,
    "GITHUB_REPOSITORY": "pyeconomics-dev/pyeconomics",
    "GRAFANA_PROM_URL": GRAFANA_URL,
    "GRAFANA_PROM_USER": GRAFANA_USER,
    "GRAFANA_READ_TOKEN": GRAFANA_TOKEN,
}


def values(rows: list[object]) -> dict[tuple[str, str], object]:
    """Each row's value, by signal and measure."""
    return {(row.signal, row.measure): row.value for row in rows}  # type: ignore[attr-defined]


def test_the_table_holds_every_g2_count(
    growth: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = growth.collect(ENVIRON, NOW, World())
    found = values(rows)
    assert found[("PyPI downloads", "pyeconomics, last 7 days")] == 372
    assert found[("PyPI downloads", "pyeconomics, last 30 days")] == 59
    # pyeconomics-app was not on PyPI on the day recorded: unavailable, with a warning.
    assert found[("PyPI downloads", "pyeconomics-app, last 7 days")] == "unavailable"
    assert "::warning::pypistats: pyeconomics-app: HTTPError" in capsys.readouterr().err
    assert found[("GitHub", "stars")] == 11
    assert found[("GitHub", "forks")] == 2
    assert found[("Discussions", "discussions, all time")] == 0
    assert found[("REST API requests", "runs, last 7 days")] == 1234
    assert found[("REST API requests", "series, last 7 days")] == 57
    assert found[("REST API requests", "metadata, last 7 days")] == 789
    assert found[("MCP requests", "runs, last 7 days")] == 12
    # A series without a route kind (a probe) is no kind's.
    assert found[("MCP requests", "series, last 7 days")] == 0
    assert found[("Analytics", "page views, last 7 days")] == "manual"
    for event in (
        "calculator_run",
        "download",
        "pro_preview_click",
        "newsletter_submit",
        "waitlist_submit",
        "search",
    ):
        assert found[("Analytics", f"event {event}, last 7 days")] == "manual"
    assert found[("Sign-ups", "newsletter, confirmed, total")] == "manual"
    for tier in ("personal", "commercial", "team"):
        assert (
            found[("Sign-ups", f"waitlist, tier {tier}, confirmed, total")] == "manual"
        )


def test_the_event_list_is_the_sites_allowlist(growth: ModuleType) -> None:
    text = (ROOT / "web" / "src" / "lib" / "events.ts").read_text(encoding="utf-8")
    block = text.split("export const EVENTS = {", 1)[1].split("}", 1)[0]
    names = [
        line.strip().split(":", 1)[0] for line in block.splitlines() if ":" in line
    ]
    assert tuple(names) == growth.EVENTS
    assert growth.TIERS == ("personal", "commercial", "team")


def test_discussions_count_only_the_last_week(growth: ModuleType) -> None:
    nodes = [
        {"createdAt": "2026-11-10T09:00:00Z", "comments": {"totalCount": 3}},
        {"createdAt": "2026-11-04T12:00:00Z", "comments": {"totalCount": 2}},
        {"createdAt": "2026-10-01T00:00:00Z", "comments": {"totalCount": 9}},
    ]
    github = {
        "data": {
            "repository": {
                "stargazerCount": 40,
                "forkCount": 5,
                "discussions": {"totalCount": 3, "nodes": nodes},
            }
        }
    }
    found = values(growth.github_rows(TOKEN, NOW, World(github)))
    assert found[("Discussions", "discussions, all time")] == 3
    assert found[("Discussions", "discussions opened, last 7 days")] == 2
    assert found[("Discussions", "comments on discussions opened, last 7 days")] == 5


def test_requests_go_only_to_declared_hosts_with_their_own_credentials(
    growth: ModuleType,
) -> None:
    world = World()
    growth.collect(ENVIRON, NOW, world)
    hosts = {
        urllib.parse.urlsplit(request.full_url).hostname for request in world.requests
    }
    assert hosts == {
        "pypistats.org",
        "api.github.com",
        "prometheus-prod-56-prod-us-east-3.grafana.net",
    }
    for request in world.requests:
        url = request.full_url
        assert url.startswith("https://")
        authorization = request.get_header("Authorization")
        host = urllib.parse.urlsplit(url).hostname
        if host == "pypistats.org":
            assert authorization is None
        elif host == "api.github.com":
            assert authorization == f"Bearer {TOKEN}"
            assert request.get_method() == "POST"
        else:
            expected = base64.b64encode(
                f"{GRAFANA_USER}:{GRAFANA_TOKEN}".encode()
            ).decode()
            assert authorization == f"Basic {expected}"
            assert "/api/v1/query?" in url
            assert TOKEN not in url
            assert GRAFANA_TOKEN not in url


def test_the_real_fetch_refuses_an_undeclared_host(growth: ModuleType) -> None:
    for url in (
        "https://example.com/x",
        "http://pypistats.org/api/packages/x/recent",
        "https://grafana.net.example/x",
        "file:///etc/passwd",
    ):
        with pytest.raises(ValueError, match="undeclared host"):
            growth.fetch_json(urllib.request.Request(url))  # noqa: S310 - refused before any open


def test_a_failing_source_gives_unavailable_rows(
    growth: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    def down(request: urllib.request.Request) -> object:
        raise http_error(request.full_url, 503)

    rows = growth.collect(ENVIRON, NOW, down)
    automatic = [row for row in rows if row.value != "manual"]
    assert automatic
    assert {row.value for row in automatic} == {"unavailable"}
    err = capsys.readouterr().err
    assert "::warning::Grafana: MCP: HTTPError" in err
    assert TOKEN not in err
    assert GRAFANA_TOKEN not in err


def test_a_failed_query_or_a_malformed_answer_is_unavailable(
    growth: ModuleType,
) -> None:
    for answer in (
        {"status": "error", "error": "bad"},
        {"status": "success", "data": {}},
        ["no"],
        {
            "status": "success",
            "data": {
                "result": [
                    {"metric": {"pyeconomics_route_kind": "runs"}, "value": [0, "x"]}
                ]
            },
        },
    ):
        rows = growth.grafana_rows(
            GRAFANA_URL,
            GRAFANA_USER,
            GRAFANA_TOKEN,
            lambda _request, answer=answer: answer,
        )
        assert {row.value for row in rows} == {"unavailable"}, answer


def test_missing_secrets_are_not_configured(growth: ModuleType) -> None:
    rows = growth.collect({}, NOW, World())
    found = values(rows)
    assert found[("GitHub", "stars")] == "not configured"
    assert found[("REST API requests", "runs, last 7 days")] == "not configured"
    assert found[("PyPI downloads", "pyeconomics, last 7 days")] == 372


def test_a_row_holds_only_a_count_or_a_marker(growth: ModuleType) -> None:
    growth.Row("s", "m", 0, "x")
    growth.Row("s", "m", "manual", "x")
    for bad in (
        -1,
        True,
        1.5,
        "someone@example.com",
        "0f1e2d3c-4b5a-6978-8796-a5b4c3d2e1f0",
        "",
    ):
        with pytest.raises(ValueError, match="not a count"):
            growth.Row("s", "m", bad, "x")


def test_the_promql_reads_one_service_by_route_kind(growth: ModuleType) -> None:
    api = growth.request_query(mcp=False)
    mcp = growth.request_query(mcp=True)
    assert api == (
        "sum by (pyeconomics_route_kind) (increase("
        "http_server_request_duration_seconds_count"
        '{job="pyeconomics/pyeconomics-api",http_route!="/mcp"}[7d]))'
    )
    assert mcp == api.replace('http_route!="/mcp"', 'http_route="/mcp"')


def test_the_rendered_table_is_counts_and_markers(growth: ModuleType) -> None:
    table = growth.render(growth.collect(ENVIRON, NOW, World()), NOW)
    lines = table.splitlines()
    assert lines[0] == "### Week ending 2026-11-11 (UTC)"
    assert lines[2] == "| Signal | Measure | Count | Source |"
    body = [
        line
        for line in lines
        if line.startswith("| ") and not line.startswith(("| Signal", "| ---"))
    ]
    assert len(body) == len(growth.collect(ENVIRON, NOW, World()))
    for line in body:
        count = line.split(" | ")[2]
        assert (
            count in {"_manual_", "_unavailable_", "_not configured_"}
            or count.replace(",", "").isdigit()
        ), line
    assert "| REST API requests | runs, last 7 days | 1,234 | Grafana Cloud |" in lines
    for secret in (TOKEN, GRAFANA_TOKEN, GRAFANA_USER, "@"):
        assert secret not in table


def test_main_writes_the_table(
    growth: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(growth, "fetch_json", World())
    for name, value in ENVIRON.items():
        monkeypatch.setenv(name, value)
    output = tmp_path / "table.md"
    assert growth.main(["--output", str(output)]) == 0
    table = output.read_bytes().decode("utf-8")
    assert table.startswith("### Week ending ")
    assert chr(13) not in table
    assert "| GitHub | stars | 11 | GitHub GraphQL |" in table
