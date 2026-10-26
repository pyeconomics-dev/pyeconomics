# tests/mcp/test_mcp_apps.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The MCP Apps chart (ADR-0012 decision 15; Phase 4 Step 9).

The server lists and reads one resource, ``ui://pyeconomics/chart``, with the
extension's MIME type and CSP metadata naming only the pinned script's origin;
every run tool, and no other, names it in ``_meta.ui.resourceUri``; a run of a
model with a chart for its calculation carries the figure in ``_meta`` when
Plotly is installed, and nothing else in the answer changes. The page loads one
script, pinned by version and Subresource Integrity (checked here against the
``plotly.min.js`` Plotly bundles), and holds no inline handler and no evaluation.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from mcp.shared.exceptions import MCPError
from mcp_support import LOOPBACK_ONLY, call, listed, run_with

import pyeconomics
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.plotting import figure
from pyeconomics.mcp import apps, build_server
from pyeconomics.surfaces.envelope import canonical_bytes
from pyeconomics.surfaces.invoke import invoke

if TYPE_CHECKING:
    from mcp import Client, types

pytestmark = LOOPBACK_ONLY

AMORTIZATION = {
    "calculation": "amortization",
    "principal": 10_000,
    "rate": 0.005,
    "periods": 24,
}


def test_the_chart_resource_is_listed_with_its_mime_type_and_csp() -> None:
    async def work(client: Client) -> types.ListResourcesResult:
        return await client.list_resources()

    (resource,) = run_with(build_server(), work).resources
    assert str(resource.uri) == apps.CHART_URI == "ui://pyeconomics/chart"
    assert resource.mime_type == apps.MIME_TYPE == "text/html;profile=mcp-app"
    assert resource.meta is not None
    assert resource.meta["ui"]["csp"] == {
        "connectDomains": [],
        "resourceDomains": ["https://cdn.jsdelivr.net"],
    }


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_reading_the_resource_answers_the_page_with_its_csp(mode: str) -> None:
    async def work(client: Client) -> types.ReadResourceResult:
        return await client.read_resource(apps.CHART_URI)

    (contents,) = run_with(build_server(), work, mode=mode).contents
    assert contents.mime_type == apps.MIME_TYPE
    assert getattr(contents, "text", None) == apps.CHART_HTML
    assert contents.meta is not None
    assert contents.meta["ui"]["csp"] == apps.CSP


def test_an_unknown_resource_is_a_protocol_error() -> None:
    async def work(client: Client) -> str:
        try:
            await client.read_resource("ui://pyeconomics/other")
        except MCPError as error:
            return error.error.message
        return "no error"

    message = run_with(build_server(), work, raise_exceptions=False)
    assert message == "Unknown resource: ui://pyeconomics/other"


def test_every_run_tool_and_no_other_names_the_chart() -> None:
    tools = listed(build_server())
    linked = {
        tool.name
        for tool in tools
        if tool.meta == {"ui": {"resourceUri": apps.CHART_URI}}
    }
    unlinked = {tool.name for tool in tools if tool.meta is None}
    assert linked | unlinked == {tool.name for tool in tools}
    assert "run_model" in linked
    assert unlinked == {"search_models", "describe_model", "get_series", "list_sources"}
    assert len(linked) == 17


def test_a_run_with_a_chart_attaches_its_figure_and_changes_nothing_else() -> None:
    result = call(build_server(), "foundations_time_value", AMORTIZATION)
    assert not result.is_error
    assert result.meta is not None
    built = result.meta[apps.FIGURE_KEY]
    expected = json.loads(
        figure(pyeconomics.run("foundations.time_value", AMORTIZATION)).to_json()
    )
    expected["layout"].pop("template")
    assert built == expected
    assert built["layout"]["title"]["text"] == "Loan balance after each payment"
    body = canonical_bytes(invoke("foundations.time_value", AMORTIZATION))
    assert result.structured_content == json.loads(body)
    assert result.content[0].type == "text"
    assert result.content[0].text.encode("utf-8") == body


def test_run_model_attaches_the_same_figure() -> None:
    server = build_server()
    headline = call(server, "foundations_time_value", AMORTIZATION)
    general = call(
        server,
        "run_model",
        {"model_id": "foundations.time_value", "inputs": AMORTIZATION},
    )
    assert headline.meta is not None
    assert general.meta is not None
    assert general.meta[apps.FIGURE_KEY] == headline.meta[apps.FIGURE_KEY]


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        # A family member without a chart for its calculation.
        (
            "foundations_time_value",
            {"calculation": "npv", "rate": 0.1, "cash_flows": [-100, 60, 60]},
        ),
        # A model that declares no chart.
        (
            "fixed_income_bond_pricing",
            {
                "calculation": "price_from_yield",
                "settlement": "2026-01-15",
                "maturity": "2036-01-15",
                "coupon_rate": 0.045,
                "yield_to_maturity": 0.05,
            },
        ),
    ],
)
def test_a_run_without_a_chart_has_no_figure(
    tool: str, arguments: dict[str, Any]
) -> None:
    result = call(build_server(), tool, arguments)
    assert not result.is_error
    assert apps.FIGURE_KEY not in (result.meta or {})


def test_no_figure_without_the_plot_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    from pyeconomics.core import plotting  # noqa: PLC0415

    def missing(name: str, *, extra: str) -> Any:  # noqa: ANN401 - as import_optional
        raise MissingOptionalDependencyError(name, extra=extra)

    monkeypatch.setattr(plotting, "import_optional", missing)
    result = call(build_server(), "foundations_time_value", AMORTIZATION)
    assert not result.is_error
    assert apps.FIGURE_KEY not in (result.meta or {})
    body = canonical_bytes(invoke("foundations.time_value", AMORTIZATION))
    assert result.structured_content == json.loads(body)


def test_a_failed_run_has_no_figure() -> None:
    result = call(
        build_server(), "foundations_time_value", {"calculation": "amortization"}
    )
    assert result.is_error
    assert apps.FIGURE_KEY not in (result.meta or {})


# --- the page ------------------------------------------------------------------------


def test_the_page_loads_one_pinned_script_from_the_declared_origin() -> None:
    html = apps.CHART_HTML
    sources = re.findall(r"<script\b[^>]*\bsrc=\"([^\"]+)\"", html)
    assert sources == [apps.PLOTLY_JS_URL]
    assert apps.PLOTLY_JS_URL.startswith(apps.PLOTLY_JS_ORIGIN + "/")
    assert f"@{apps.PLOTLY_JS_VERSION}/" in apps.PLOTLY_JS_URL
    tag = re.search(r"<script\b[^>]*\bsrc=[^>]*>", html)
    assert tag is not None
    assert f'integrity="{apps.PLOTLY_JS_INTEGRITY}"' in tag.group(0)
    assert 'crossorigin="anonymous"' in tag.group(0)
    # Every URL in the page is the script's; no stylesheet, image or frame.
    assert set(re.findall(r"https?://[^\s\"'<>)]+", html)) == {apps.PLOTLY_JS_URL}
    assert not re.search(r"<(link|img|iframe|object|embed|base)\b", html, re.IGNORECASE)
    assert apps.CSP["resourceDomains"] == [apps.PLOTLY_JS_ORIGIN]
    assert apps.CSP["connectDomains"] == []


def test_the_integrity_hash_is_the_bundled_plotly_js() -> None:
    import plotly  # noqa: PLC0415
    from plotly.offline import get_plotlyjs_version  # noqa: PLC0415

    assert get_plotlyjs_version() == apps.PLOTLY_JS_VERSION, (
        "Plotly now bundles another Plotly.js: move PLOTLY_JS_VERSION and "
        "PLOTLY_JS_INTEGRITY in src/pyeconomics/mcp/apps.py to it, after checking "
        "the CDN's file is byte for byte the bundled one"
    )
    bundled = Path(plotly.__file__).parent / "package_data" / "plotly.min.js"
    digest = hashlib.sha384(bundled.read_bytes()).digest()
    expected = "sha384-" + base64.b64encode(digest).decode()
    assert expected == apps.PLOTLY_JS_INTEGRITY


def test_the_page_has_no_inline_handler_and_evaluates_nothing() -> None:
    html = apps.CHART_HTML
    assert not re.search(r"<[^>]+\son[a-z]+\s*=", html, re.IGNORECASE)
    for pattern in (
        r"\beval\s*\(",
        r"\bnew\s+Function\b",
        r"\bFunction\s*\(",
        r"\.innerHTML\b",
        r"\.outerHTML\b",
        r"insertAdjacentHTML",
        r"document\.write",
        r"set(Timeout|Interval)\s*\(\s*[\"'`]",
        r"javascript:",
        r"\bfetch\s*\(",
        r"XMLHttpRequest",
        r"WebSocket",
    ):
        assert not re.search(pattern, html), pattern
    # The figure is read from the result's _meta, by its key.
    assert f'meta["{apps.FIGURE_KEY}"]' in html
    assert "ui/initialize" in html
    assert "ui/notifications/initialized" in html
    assert "ui/notifications/tool-result" in html


def test_the_page_is_plain_ascii() -> None:
    apps.CHART_HTML.encode("ascii")
