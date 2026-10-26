# src/pyeconomics/mcp/apps.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""MCP Apps: a run's chart, drawn inside a client (ADR-0012 decision 15).

A client that supports the MCP Apps extension (``io.modelcontextprotocol/ui``,
revision 2026-01-26) renders the resource :data:`CHART_URI` beside a run tool's
answer: every run tool names it in its ``_meta.ui.resourceUri``
(:data:`TOOL_META`). The page, :data:`CHART_HTML`, is a string constant here,
because the wheel admits only ``.py`` files. It speaks the extension's messages
in plain JavaScript (no SDK), draws the Plotly figure a run attaches under
``_meta["pyeconomics/figure"]`` (:func:`figure_meta`), and loads one script:
Plotly.js from :data:`PLOTLY_JS_URL`, pinned by version and Subresource
Integrity, whose origin is the only one its CSP metadata (:data:`CSP`) names.

A run attaches a figure only when the ``plot`` extra is installed and the model
declares a chart for the result's calculation (the first one, when several
apply); the result's structured content and text are the same either way, so a
client without the extension, or a run without a chart, gets the plain result.

What the page does with the figure: it hands the figure's ``data`` and
``layout``, which are JSON values, to ``Plotly.newPlot`` and nothing else. It
writes text only through ``textContent``, has no inline event handler, never
evaluates text and opens no connection: the extension's default policy, which
the host enforces, refuses one.

Examples
--------
>>> from pyeconomics.mcp.apps import CHART_URI, MIME_TYPE
>>> CHART_URI, MIME_TYPE
('ui://pyeconomics/chart', 'text/html;profile=mcp-app')
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, Final

from mcp import types

from pyeconomics.core.errors import MissingOptionalDependencyError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core.model import Model

__all__ = [
    "CHART_HTML",
    "CHART_URI",
    "CSP",
    "EXTENSION",
    "FIGURE_KEY",
    "MIME_TYPE",
    "PLOTLY_JS_INTEGRITY",
    "PLOTLY_JS_ORIGIN",
    "PLOTLY_JS_URL",
    "PLOTLY_JS_VERSION",
    "TOOL_META",
    "chart_contents",
    "chart_resource",
    "figure_meta",
]

#: The extension's identifier.
EXTENSION: Final = "io.modelcontextprotocol/ui"
#: The chart's resource URI.
CHART_URI: Final = "ui://pyeconomics/chart"
#: The extension's MIME type for an HTML page.
MIME_TYPE: Final = "text/html;profile=mcp-app"
#: The ``_meta`` key of a run's figure.
FIGURE_KEY: Final = "pyeconomics/figure"
#: The Plotly.js release the page loads: the one the ``plot`` extra's Plotly
#: bundles, so the page draws what Plotly builds (a test holds the two equal).
PLOTLY_JS_VERSION: Final = "4.1.1"
#: The one origin the page loads from.
PLOTLY_JS_ORIGIN: Final = "https://cdn.jsdelivr.net"
#: The script, at an immutable npm version.
PLOTLY_JS_URL: Final = (
    f"{PLOTLY_JS_ORIGIN}/npm/plotly.js-dist-min@{PLOTLY_JS_VERSION}/plotly.min.js"
)
#: The script's SHA-384, byte for byte the ``plotly.min.js`` Plotly bundles (a
#: test checks it against that file).
PLOTLY_JS_INTEGRITY: Final = (
    "sha384-AFNp2MtSm5/oZbEs/J19F/Ah57MEiVsoed8nE3fq2Wnccdl1u/EkyJ9XKKU8rt7+"
)
#: The page's CSP metadata: the script's origin, and no connection.
CSP: Final[dict[str, list[str]]] = {
    "connectDomains": [],
    "resourceDomains": [PLOTLY_JS_ORIGIN],
}
#: What a run tool carries in its ``_meta``.
TOOL_META: Final[dict[str, Any]] = {"ui": {"resourceUri": CHART_URI}}

_SCRIPT: Final = """
(function () {
  "use strict";
  var status = document.getElementById("status");
  var chart = document.getElementById("chart");
  var nextId = 1;
  var initializeId = null;

  function send(message) {
    message.jsonrpc = "2.0";
    window.parent.postMessage(message, "*");
  }

  function say(text) {
    status.textContent = text;
    status.hidden = text === "";
  }

  function resize() {
    send({
      method: "ui/notifications/size-changed",
      params: { height: Math.ceil(document.documentElement.scrollHeight) }
    });
  }

  function applyContext(context) {
    if (!context) {
      return;
    }
    if (context.theme === "dark" || context.theme === "light") {
      document.documentElement.setAttribute("data-theme", context.theme);
    }
    var variables = context.styles && context.styles.variables;
    if (variables) {
      Object.keys(variables).forEach(function (name) {
        var value = variables[name];
        if (name.indexOf("--") === 0 && typeof value === "string") {
          document.documentElement.style.setProperty(name, value);
        }
      });
    }
    if (chart.data && window.Plotly) {
      window.Plotly.relayout(chart, colours());
    }
  }

  function colours() {
    var style = window.getComputedStyle(document.body);
    var text = style.getPropertyValue("--chart-text").trim();
    var grid = style.getPropertyValue("--chart-grid").trim();
    return {
      "paper_bgcolor": "rgba(0,0,0,0)",
      "plot_bgcolor": "rgba(0,0,0,0)",
      "font.color": text,
      "xaxis.gridcolor": grid,
      "yaxis.gridcolor": grid
    };
  }

  function render(result) {
    var meta = (result && result._meta) || {};
    var figure = meta["pyeconomics/figure"];
    if (result && result.isError) {
      say("The run failed: there is no chart.");
    } else if (!figure || !Array.isArray(figure.data)) {
      say("This result has no chart.");
    } else if (!window.Plotly) {
      say("The chart library did not load.");
    } else {
      var layout = figure.layout || {};
      layout.autosize = true;
      layout.margin = { l: 64, r: 24, t: 48, b: 56 };
      window.Plotly.newPlot(chart, figure.data, layout, {
        displaylogo: false,
        responsive: true
      }).then(function () {
        window.Plotly.relayout(chart, colours());
        say("");
        resize();
      });
      return;
    }
    resize();
  }

  window.addEventListener("message", function (event) {
    var message = event.data;
    if (event.source !== window.parent || !message || message.jsonrpc !== "2.0") {
      return;
    }
    if (message.id !== undefined && message.id === initializeId) {
      initializeId = null;
      applyContext(message.result && message.result.hostContext);
      send({ method: "ui/notifications/initialized", params: {} });
      return;
    }
    if (message.method === "ui/notifications/tool-result") {
      render(message.params);
    } else if (message.method === "ui/notifications/host-context-changed") {
      applyContext(message.params);
    } else if (message.method === "ui/resource-teardown") {
      send({ id: message.id, result: {} });
    } else if (message.method !== undefined && message.id !== undefined) {
      send({
        id: message.id,
        error: { code: -32601, message: "Method not found" }
      });
    }
  });

  initializeId = nextId;
  nextId += 1;
  send({
    id: initializeId,
    method: "ui/initialize",
    params: {
      protocolVersion: "2026-01-26",
      appInfo: { name: "pyeconomics-chart", version: "1" },
      appCapabilities: {}
    }
  });
})();
"""

_STYLE: Final = """
:root {
  color-scheme: light dark;
  --chart-text: #1f2328;
  --chart-grid: #d8dee4;
  --chart-muted: #59636e;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --chart-text: #e6edf3;
    --chart-grid: #30363d;
    --chart-muted: #9198a1;
  }
}
:root[data-theme="dark"] {
  --chart-text: #e6edf3;
  --chart-grid: #30363d;
  --chart-muted: #9198a1;
}
html, body {
  margin: 0;
  background: transparent;
  color: var(--chart-text);
  font-family: var(--font-sans, system-ui, sans-serif);
}
#chart {
  width: 100%;
  height: 360px;
}
#status {
  margin: 0;
  padding: 12px 16px;
  color: var(--chart-muted);
  font-size: 14px;
}
"""

#: The chart page: HTML, its style, the pinned Plotly.js and the page's script.
CHART_HTML: Final = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>pyeconomics chart</title>
<style>{_STYLE}</style>
<script src="{PLOTLY_JS_URL}"
  integrity="{PLOTLY_JS_INTEGRITY}"
  crossorigin="anonymous"></script>
</head>
<body>
<div id="chart"></div>
<p id="status">Waiting for the result.</p>
<script>{_SCRIPT}</script>
</body>
</html>
"""

_RESOURCE_META: Final[dict[str, Any]] = {"ui": {"csp": CSP, "prefersBorder": False}}


def chart_resource() -> types.Resource:
    """Return the chart's entry in the resource list, with its CSP metadata."""
    return types.Resource(
        uri=CHART_URI,
        name="chart",
        title="pyeconomics chart",
        description=(
            "Draws the Plotly chart a model run attaches to its result, in a client "
            "that supports MCP Apps."
        ),
        mime_type=MIME_TYPE,
        meta=_RESOURCE_META,
    )


def chart_contents() -> types.TextResourceContents:
    """Return the chart page, with its CSP metadata, as ``resources/read`` gives it."""
    return types.TextResourceContents(
        uri=CHART_URI, mime_type=MIME_TYPE, text=CHART_HTML, meta=_RESOURCE_META
    )


def figure_meta(
    model: Model[Any, Any], document: Mapping[str, Any]
) -> dict[str, Any] | None:
    """Return a run's ``_meta`` with its figure, ``None`` when it has none.

    The figure is the first of the model's charts for the result's calculation,
    built from the result's JSON document; there is none without the ``plot``
    extra or such a chart. Its layout's template is left out: Plotly.js draws
    its own default, and the figure stays a few kilobytes.
    """
    from pyeconomics.core import plotting  # noqa: PLC0415 - Plotly loads on use

    charts = plotting.charts_for(model, document["inputs"].get("calculation"))
    if not charts:
        return None
    try:
        figure = plotting.figure_of(model, document, charts[0].id)
    except MissingOptionalDependencyError:
        return None
    built: dict[str, Any] = json.loads(figure.to_json())
    built.get("layout", {}).pop("template", None)
    return {FIGURE_KEY: built}
