# tests/web/test_legal_pages.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The legal pages' data is held to the service it describes (Phase 5 Step 16).

The privacy policy is generated from ``web/src/content/legal/data-flows.json``.
``web/tests/unit/legal.test.ts`` holds that file complete against the Content
Security Policy; this holds it against the rest:

- every row of ADR-0013's "Personal data" table, which the file must match line
  by line, has a flow with that row's processor and decision;
- every host the service sends to holds a flow: Sentry's ingest
  (``server/observability.py``), Grafana Cloud's OTLP gateway, Better Stack's
  heartbeat host (``data/snapshots/writer.py``) and the rate limits' Redis;
- the logs the service keeps: its own records in Cloud Logging for 30 days,
  with Cloud Run's request logs excluded by the exclusion production.md names.

It also holds the hosted rate limits the terms of use state (``legal.ts
RATE_LIMITS``) to ``server/limits.py``, and the build tools the licence page
lists (``licences.ts BUILD_OUTPUT``) to ``scripts/checks/web_licences.py``.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import re
from pathlib import Path
from typing import Any, Final

import pytest

ROOT: Final = Path(__file__).resolve().parents[2]
FLOWS: Final = ROOT / "web" / "src" / "content" / "legal" / "data-flows.json"
ADR: Final = ROOT / "docs" / "adr" / "0013-web-app-and-launch.md"
LEGAL_TS: Final = ROOT / "web" / "src" / "lib" / "legal.ts"
LICENCES_TS: Final = ROOT / "web" / "src" / "lib" / "licences.ts"
PRODUCTION: Final = ROOT / "docs" / "operations" / "production.md"


def _flows() -> dict[str, Any]:
    document: dict[str, Any] = json.loads(FLOWS.read_text(encoding="utf-8"))
    return document


def _processor_names() -> dict[str, str]:
    return {p["id"]: p["name"] for p in _flows()["processors"]}


def _hosts() -> list[str]:
    return [host for flow in _flows()["flows"] for host in flow["hosts"]]


def _fill(text: str, value: str) -> str:
    """Replace a pattern's ``<name>`` placeholders with a sample value."""
    return re.sub(r"<[a-z]+>", value, text)


def _adr_rows() -> list[list[str]]:
    text = ADR.read_text(encoding="utf-8")
    section = text.split("### Personal data", 1)[1].split("\n### ", 1)[0]
    rows = [
        [cell.strip() for cell in line.strip().strip("|").split("|")]
        for line in section.splitlines()
        if line.startswith("|") and not re.fullmatch(r"\|[-| ]+\|", line.strip())
    ]
    return rows[1:]


def test_every_row_of_adr_0013s_personal_data_table_has_a_flow() -> None:
    names = _processor_names()
    flows = _flows()["flows"]
    rows = _adr_rows()
    assert len(rows) >= 11
    for row in rows:
        who = re.sub(r"\s*\[S\d+\]", "", row[2])
        decision = int(re.findall(r"\d+", row[-1])[0])
        vendor = re.split(r" \(|,", who, maxsplit=1)[0].removesuffix(" Zero Trust")
        vendor = {"Functional Software": "Sentry", "Umami Software": "Umami"}.get(
            vendor, vendor
        )
        matching = [
            f
            for f in flows
            if f["processor"] is not None
            and vendor in names[f["processor"]]
            and f["decision"] == decision
        ]
        assert matching, f"ADR-0013 row {row[0]!r} ({vendor}, decision {decision})"


def test_every_host_the_service_sends_to_has_a_flow() -> None:
    from pyeconomics.data.snapshots.writer import HEARTBEAT_HOST  # noqa: PLC0415

    hosts = _hosts()
    assert HEARTBEAT_HOST in hosts
    assert any(host.endswith(".upstash.io") for host in hosts)

    pytest.importorskip("fastapi")
    from pyeconomics.server import observability  # noqa: PLC0415

    dsn = observability._SENTRY_DSN  # noqa: SLF001 - the declared pattern itself
    otlp = observability._OTLP_ENDPOINT  # noqa: SLF001 - the declared pattern itself
    assert any(
        dsn.fullmatch(f"https://{'0' * 32}@{_fill(host, '1234567')}/42")
        for host in hosts
    ), "no flow names Sentry's ingest host"
    assert any(
        otlp.fullmatch(f"https://{_fill(host, 'prod-us-east-0')}/otlp")
        for host in hosts
    ), "no flow names Grafana Cloud's OTLP gateway"


def test_the_logs_the_service_keeps_are_described() -> None:
    flows = {flow["id"]: flow for flow in _flows()["flows"]}
    records = flows["api-records"]
    assert records["processor"] == "google-cloud"
    assert records["retention"] == "30 days."
    assert "request logs" in records["collected"]
    assert "excluded" in records["collected"]
    # The exclusion is configured by hand and recorded with its name.
    production = PRODUCTION.read_text(encoding="utf-8")
    assert "Log exclusion `cloud-run-request-logs` on the `_Default` sink" in production
    inputs = flows["run-inputs"]
    assert "POST" in inputs["collected"]
    assert "never uploaded" in inputs["collected"]


def _ts_object(path: Path, name: str) -> dict[str, str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(rf"export const {name} = (\{{[^}}]*\}}) as const;", source)
    assert match is not None, f"{path.name} has no {name}"
    body = re.sub(r"(\w+):", r'"\1":', match[1])
    parsed: dict[str, str] = ast.literal_eval(body)
    return parsed


def test_the_terms_state_the_servers_rate_limits() -> None:
    pytest.importorskip("fastapi")
    from pyeconomics.server.limits import HOSTED_LIMITS  # noqa: PLC0415

    stated = _ts_object(LEGAL_TS, "RATE_LIMITS")
    assert stated == {
        "runs": HOSTED_LIMITS.runs,
        "series": HOSTED_LIMITS.series,
        "metadata": HOSTED_LIMITS.metadata,
    }


def test_the_licence_page_lists_the_build_tools_the_licence_check_does() -> None:
    path = ROOT / "scripts" / "checks" / "web_licences.py"
    spec = importlib.util.spec_from_file_location("web_licences_for_test", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = LICENCES_TS.read_text(encoding="utf-8")
    match = re.search(r"export const BUILD_OUTPUT = (\[[^\]]*\]) as const;", source)
    assert match is not None
    assert tuple(ast.literal_eval(match[1])) == tuple(module.BUILD_OUTPUT)
