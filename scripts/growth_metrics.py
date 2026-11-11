# scripts/growth_metrics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Gate G2's weekly counts, as one Markdown table (Phase 5 Step 15).

``growth-metrics.yml`` runs this every week, and its report job posts the
table on the pinned "Gate G3 ledger" issue (ROADMAP §5 "Monetization strategy
& validation gates"; ADR-0013 decision 19). It runs in the workflow, never in
the package, and imports the standard library only.

It writes counts only, never an address, an identifier or an input:

- PyPI downloads of ``pyeconomics`` and ``pyeconomics-app`` over the last
  week and month, from pypistats.org (no key);
- GitHub stars, forks and Discussions activity (``GITHUB_TOKEN``);
- API and MCP requests by route kind over the last seven days, from Grafana
  Cloud's Prometheus endpoint with a ``metrics:read`` token
  (``GRAFANA_PROM_URL``, ``GRAFANA_PROM_USER``, ``GRAFANA_READ_TOKEN``);
- the analytics totals and events, and sign-ups by list and tier, as
  "manual" rows: Umami's free plan has no API, and the email processor's only
  key that reads sign-up counts can also read every address, so none is kept
  in CI (the maintainer's decision, 2026-11-11). The maintainer adds those
  figures to the comment.

A source that fails gives "unavailable" rows and a warning, never a crash, so
one outage does not cost the week's other counts. Every request goes to one
of three declared hosts over HTTPS.

Usage: ``python scripts/growth_metrics.py [--output table.md]``.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

USER_AGENT = "pyeconomics-growth-metrics/1.0"
TIMEOUT = 30
PACKAGES = ("pyeconomics", "pyeconomics-app")
REPOSITORY = "pyeconomics-dev/pyeconomics"
GRAFANA_HOST = re.compile(r"^prometheus-[a-z0-9-]+\.grafana\.net$")
HOSTS = ("pypistats.org", "api.github.com")
ROUTE_KINDS = ("runs", "series", "metadata")
MCP_ROUTE = "/mcp"
# Grafana Cloud names an OTLP series' job <service.namespace>/<service.name>.
SERVICE = 'job="pyeconomics/pyeconomics-api"'
WINDOW = "7d"
MANUAL = "manual"
UNAVAILABLE = "unavailable"
NOT_CONFIGURED = "not configured"
MARKERS = frozenset({MANUAL, UNAVAILABLE, NOT_CONFIGURED})
UMAMI = "Umami Cloud dashboard"
BUTTONDOWN = "Buttondown dashboard"
FAILURES = (urllib.error.URLError, OSError, ValueError, KeyError, TypeError)

# The allowlisted analytics events (web/src/lib/events.ts EVENTS).
EVENTS = (
    "calculator_run",
    "download",
    "pro_preview_click",
    "newsletter_submit",
    "waitlist_submit",
    "search",
)
TIERS = ("personal", "commercial", "team")

Fetch = Callable[[urllib.request.Request], object]


@dataclass(frozen=True)
class Row:
    """One count: what it measures, its value and where it came from."""

    signal: str
    measure: str
    value: int | str
    source: str

    def __post_init__(self) -> None:
        """Hold every value to a non-negative count or a marker."""
        value = self.value
        if isinstance(value, bool) or not (
            (isinstance(value, int) and value >= 0) or value in MARKERS
        ):
            msg = f"{self.signal} / {self.measure}: not a count"
            raise ValueError(msg)


def _allowed(url: str) -> bool:
    parts = urllib.parse.urlsplit(url)
    host = parts.hostname or ""
    return parts.scheme == "https" and (host in HOSTS or bool(GRAFANA_HOST.match(host)))


def fetch_json(request: urllib.request.Request) -> object:
    """Send ``request`` to a declared host and parse its JSON answer."""
    if not _allowed(request.full_url):
        msg = "a request to an undeclared host"
        raise ValueError(msg)
    request.add_header("User-Agent", USER_AGENT)
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=TIMEOUT) as response:  # noqa: S310 # nosec B310 - https to a declared host only
        return json.loads(response.read())


def _warn(message: str) -> None:
    sys.stderr.write(f"::warning::{message}\n")


def _count(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = "not a number"
        raise TypeError(msg)
    return max(round(value), 0)


def pypi_rows(fetch: Fetch = fetch_json) -> list[Row]:
    """Count each package's downloads over the last week and month."""
    rows: list[Row] = []
    for package in PACKAGES:
        url = f"https://pypistats.org/api/packages/{package}/recent"
        try:
            document = fetch(urllib.request.Request(url))
            data = document["data"]  # type: ignore[index]
            week, month = _count(data["last_week"]), _count(data["last_month"])
        except FAILURES as error:
            _warn(f"pypistats: {package}: {type(error).__name__}")
            week = month = UNAVAILABLE  # type: ignore[assignment]
        rows.append(
            Row("PyPI downloads", f"{package}, last 7 days", week, "pypistats.org")
        )
        rows.append(
            Row("PyPI downloads", f"{package}, last 30 days", month, "pypistats.org")
        )
    return rows


GITHUB_QUERY = """
query($owner: String!, $name: String!) {
  repository(owner: $owner, name: $name) {
    stargazerCount
    forkCount
    discussions(first: 100, orderBy: {field: CREATED_AT, direction: DESC}) {
      totalCount
      nodes { createdAt comments { totalCount } }
    }
  }
}
"""


def github_rows(
    token: str | None,
    now: dt.datetime,
    fetch: Fetch = fetch_json,
    repository: str = REPOSITORY,
) -> list[Row]:
    """Count stars, forks and Discussions activity (the workflow's token)."""
    measures = (
        ("GitHub", "stars"),
        ("GitHub", "forks"),
        ("Discussions", "discussions, all time"),
        ("Discussions", "discussions opened, last 7 days"),
        ("Discussions", "comments on discussions opened, last 7 days"),
    )
    if not token:
        return [
            Row(signal, measure, NOT_CONFIGURED, "GitHub GraphQL")
            for signal, measure in measures
        ]
    owner, name = repository.split("/", 1)
    body = json.dumps(
        {"query": GITHUB_QUERY, "variables": {"owner": owner, "name": name}}
    ).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=body, method="POST"
    )
    request.add_header("Authorization", f"Bearer {token}")
    request.add_header("Content-Type", "application/json")
    try:
        document = fetch(request)
        repo = document["data"]["repository"]  # type: ignore[index]
        since = now - dt.timedelta(days=7)
        recent = [
            node
            for node in repo["discussions"]["nodes"]
            if dt.datetime.fromisoformat(node["createdAt"]) >= since
        ]
        values: list[int | str] = [
            _count(repo["stargazerCount"]),
            _count(repo["forkCount"]),
            _count(repo["discussions"]["totalCount"]),
            len(recent),
            sum(_count(node["comments"]["totalCount"]) for node in recent),
        ]
    except FAILURES as error:
        _warn(f"GitHub: {type(error).__name__}")
        values = [UNAVAILABLE] * len(measures)
    return [
        Row(signal, measure, value, "GitHub GraphQL")
        for (signal, measure), value in zip(measures, values, strict=True)
    ]


def request_query(*, mcp: bool) -> str:
    """Return the PromQL for the last week's requests by route kind, API or MCP."""
    route = f'http_route="{MCP_ROUTE}"' if mcp else f'http_route!="{MCP_ROUTE}"'
    return (
        "sum by (pyeconomics_route_kind) (increase("
        f"http_server_request_duration_seconds_count{{{SERVICE},{route}}}[{WINDOW}]))"
    )


def _by_route_kind(document: object) -> dict[str, int]:
    """Sum a Prometheus vector's values by route kind."""
    if not isinstance(document, dict) or document.get("status") != "success":
        msg = "the query failed"
        raise ValueError(msg)
    found: dict[str, int] = {}
    for result in document["data"]["result"]:
        kind = result["metric"].get("pyeconomics_route_kind", "")
        if kind in ROUTE_KINDS:
            found[kind] = found.get(kind, 0) + _count(float(result["value"][1]))
    return found


def grafana_rows(
    url: str | None,
    user: str | None,
    token: str | None,
    fetch: Fetch = fetch_json,
) -> list[Row]:
    """Count API and MCP requests by route kind over the last week (Grafana)."""
    surfaces = (("REST API", False), ("MCP", True))
    if not (url and user and token):
        return [
            Row(
                f"{surface} requests",
                f"{kind}, last 7 days",
                NOT_CONFIGURED,
                "Grafana Cloud",
            )
            for surface, _ in surfaces
            for kind in ROUTE_KINDS
        ]
    credential = base64.b64encode(f"{user}:{token}".encode()).decode()
    rows: list[Row] = []
    for surface, mcp in surfaces:
        query = urllib.parse.urlencode({"query": request_query(mcp=mcp)})
        # fetch_json refuses any host but Grafana Cloud's Prometheus, over https.
        request = urllib.request.Request(f"{url.rstrip('/')}/api/v1/query?{query}")  # noqa: S310
        request.add_header("Authorization", f"Basic {credential}")
        try:
            found = _by_route_kind(fetch(request))
            values: dict[str, int | str] = {k: found.get(k, 0) for k in ROUTE_KINDS}
        except FAILURES as error:
            _warn(f"Grafana: {surface}: {type(error).__name__}")
            values = dict.fromkeys(ROUTE_KINDS, UNAVAILABLE)
        rows.extend(
            Row(
                f"{surface} requests",
                f"{kind}, last 7 days",
                values[kind],
                "Grafana Cloud",
            )
            for kind in ROUTE_KINDS
        )
    return rows


def manual_rows() -> list[Row]:
    """List the rows CI has no safe API for: the maintainer adds them."""
    rows = [
        Row("Analytics", "page views, last 7 days", MANUAL, UMAMI),
        Row("Analytics", "visitors, last 7 days", MANUAL, UMAMI),
    ]
    rows.extend(
        Row("Analytics", f"event {event}, last 7 days", MANUAL, UMAMI)
        for event in EVENTS
    )
    rows.append(Row("Sign-ups", "newsletter, confirmed, total", MANUAL, BUTTONDOWN))
    rows.extend(
        Row("Sign-ups", f"waitlist, tier {tier}, confirmed, total", MANUAL, BUTTONDOWN)
        for tier in TIERS
    )
    return rows


def collect(
    environ: Mapping[str, str],
    now: dt.datetime,
    fetch: Fetch = fetch_json,
) -> list[Row]:
    """Return every row of the week's table, in order."""
    return [
        *pypi_rows(fetch),
        *github_rows(
            environ.get("GITHUB_TOKEN"),
            now,
            fetch,
            environ.get("GITHUB_REPOSITORY", REPOSITORY),
        ),
        *grafana_rows(
            environ.get("GRAFANA_PROM_URL"),
            environ.get("GRAFANA_PROM_USER"),
            environ.get("GRAFANA_READ_TOKEN"),
            fetch,
        ),
        *manual_rows(),
    ]


def render(rows: list[Row], now: dt.datetime) -> str:
    """Write the comment: a heading, the table and how to fill the manual rows."""
    lines = [
        f"### Week ending {now.date().isoformat()} (UTC)",
        "",
        "| Signal | Measure | Count | Source |",
        "| --- | --- | ---: | --- |",
    ]
    for row in rows:
        value = f"{row.value:,}" if isinstance(row.value, int) else f"_{row.value}_"
        lines.append(f"| {row.signal} | {row.measure} | {value} | {row.source} |")
    lines += [
        "",
        (
            "Counts only: no address, identifier or input. Rows marked _manual_ "
            "come from dashboards CI has no safe access to; the maintainer edits "
            "this comment to add them (docs/operations/production.md, section 12)."
        ),
    ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Collect the week's counts and write the table."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--output", type=Path, help="write the table to this file")
    args = parser.parse_args(argv)
    now = dt.datetime.now(dt.UTC)
    table = render(collect(os.environ, now, fetch_json), now)
    if args.output is None:
        sys.stdout.write(table)
    else:
        args.output.write_bytes(table.encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
