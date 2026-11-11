# tests/server/test_server_telemetry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The hosted service's errors and telemetry carry no personal data (Phase 5 Step 14).

ADR-0013 decision 15 and Step 14's security block:

- Sentry is initialised without ``send_default_pii`` and without a
  ``data_collection`` mapping, with no integration, local variable, request
  body or breadcrumb, and every event passes through the allowlist.
- The canary: a key, three file paths, an upstream host, a client address and
  input values are planted in requests (the query, a header, a series target,
  ``CF-Connecting-IP``, run bodies and error messages), including errors raised
  in a worker and in the app itself; none reaches a captured error event, span
  or metric. A failing assertion names the sinks, never the planted values.
- A local server, and a hosted one without the variables, never imports the
  module or the SDKs.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import secrets
import subprocess  # nosec B404: runs this interpreter with fixed arguments
import sys
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

import pytest
from leakcheck import Canary, LeakCheck, canary
from opentelemetry import metrics, trace
from server_support import ERRORS, LOOPBACK_ONLY, client, service_of, use_toys
from telemetry_support import REAL_START, Captured, World, capturing, fake_dsn

from pyeconomics import __version__
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import ConfigError, redaction
from pyeconomics.data.snapshots import codec
from pyeconomics.data.snapshots.writer import Report
from pyeconomics.server import observability, snapshot_job
from pyeconomics.server.edge import CREDENTIAL_VARIABLE, EDGE_HEADER
from pyeconomics.server.limits import RateLimits
from pyeconomics.server.settings import (
    DEPLOYMENT_VARIABLE,
    OTLP_ENDPOINT_VARIABLE,
    OTLP_HEADERS_VARIABLE,
    SENTRY_DSN_VARIABLE,
)

if TYPE_CHECKING:
    from collections.abc import Iterator

pytestmark = LOOPBACK_ONLY

#: What a span or a metric may be labelled with; anything else fails.
ATTRIBUTES = frozenset(
    {
        "http.request.method",
        "http.route",
        "pyeconomics.status_class",
        "pyeconomics.route_kind",
        "pyeconomics.task_kind",
        "pyeconomics.cost_class",
        "pyeconomics.outcome",
        "pyeconomics.model",
        "pyeconomics.deployment",
        "pyeconomics.provider",
        "pyeconomics.state",
    }
)


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[World]:
    """Turn the hosted telemetry on, with every exporter in memory."""
    yield capturing(monkeypatch)
    Captured.items = []


@dataclass(frozen=True)
class Plants:
    """A key, file paths, a host, a client address and input values to find."""

    key: Canary
    folder: str = field(default_factory=lambda: f"u{secrets.token_hex(6)}")
    host: str = field(default_factory=lambda: f"h{secrets.token_hex(6)}")
    address: str = field(
        default_factory=lambda: f"203.0.113.{secrets.randbelow(200) + 20}"
    )
    amount: str = field(
        default_factory=lambda: (
            f"{secrets.randbelow(10**6) + 10**6}.{secrets.randbelow(900) + 100}"
        )
    )

    @property
    def text(self) -> str:
        """A message holding every planted value."""
        return (
            f"reading C:\\Users\\{self.folder}\\pyeconomics.toml, "
            f"/home/{self.folder}/.config/pyeconomics.toml and "
            f"~/{self.folder}/.env through "
            f"https://api.{self.host}.example.org/v1/series?api_key={self.key.value} "
            f"for {self.address} with {self.amount} and {self.key.value}"
        )

    def needles(self) -> tuple[str, ...]:
        """Each planted value, as LeakCheck searches for it."""
        return (*self.key.needles(), self.folder, self.host, self.address, self.amount)


def _send_planted_requests(api: Any, plants: Plants, credential: str) -> int:  # noqa: ANN401
    """Send every request the canary plants values in; return how many."""
    edge = {EDGE_HEADER: credential, "CF-Connecting-IP": plants.address}
    key = plants.key.value
    sent = 0
    for name in ERRORS:
        api.post(
            "/v1/models/foundations.toy_fail/run",
            content=canonical_json({"error": name, "message": plants.text}),
            headers=edge,
        )
        sent += 1
    for method, path, extra in (
        ("GET", "/v1/models", {"params": {"api_key": key}}),
        ("GET", "/healthz", {"headers": {**edge, "Authorization": f"Bearer {key}"}}),
        ("GET", f"/v1/series/{key}", {}),
        ("GET", f"/v1/series/nowhere:{key}", {}),
        (
            "POST",
            "/v1/models/foundations.toy_time_value/run",
            {
                "content": canonical_json(
                    {
                        "calculation": "future_value",
                        "present_value": float(plants.amount),
                        "rate": 0.05,
                        "periods": 3,
                    }
                )
            },
        ),
        (
            "POST",
            "/v1/models/foundations.toy_time_value/run",
            {"content": canonical_json({"calculation": key, "rate": plants.text})},
        ),
        ("GET", f"/no/such/{key}", {}),
    ):
        headers = {**edge, **cast("dict[str, str]", extra.pop("headers", {}))}
        api.request(method, path, headers=headers, **extra)
        sent += 1
    return sent


def test_no_planted_value_reaches_an_error_event_a_span_or_a_metric(
    monkeypatch: pytest.MonkeyPatch, world: World
) -> None:
    use_toys(monkeypatch)
    credential = secrets.token_urlsafe(32)
    monkeypatch.setenv(CREDENTIAL_VARIABLE, credential)
    plants = Plants(key=canary())
    check = LeakCheck(plants)

    def unexpected(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError(plants.text)

    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        sent = _send_planted_requests(api, plants, credential)
        # An error the app itself raises, outside every handler: the last resort.
        monkeypatch.setattr("pyeconomics.server.app.listing.list_models", unexpected)
        crashed = api.get(
            "/v1/models",
            headers={EDGE_HEADER: credential, "CF-Connecting-IP": plants.address},
        )
        points = world.metric_points()
        assert service_of(api).telemetry is not None
    assert crashed.status_code == 500
    # The process's global providers stay OpenTelemetry's no-op proxies, so the
    # spans FastAPI and the MCP SDK make through the API go nowhere.
    assert type(trace.get_tracer_provider()).__name__ == "ProxyTracerProvider"
    assert type(metrics.get_meter_provider()).__name__ == "_ProxyMeterProvider"
    for index, event in enumerate(world.events):
        check.add(f"event:{index}", json.dumps(event, default=str))
    for index, span in enumerate(world.spans.get_finished_spans()):
        check.add(f"span:{index}", span.to_json())
    for index, (name, attributes) in enumerate(points):
        check.add(f"metric:{index}:{name}", json.dumps(attributes, default=str))
    # The canary is not vacuous: every channel recorded something.
    assert len(world.spans.get_finished_spans()) == sent + 1
    assert {name for name, _ in points} >= {
        "http.server.request.duration",
        "pyeconomics.tasks",
        "pyeconomics.task.duration",
    }
    assert any("exception" in event for event in world.events)
    assert any(
        event.get("tags", {}).get("slug") == "internal-error" for event in world.events
    )
    check.assert_clean()


def test_events_spans_and_metrics_hold_only_the_allowed_fields(
    monkeypatch: pytest.MonkeyPatch, world: World
) -> None:
    use_toys(monkeypatch)
    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        api.post(
            "/v1/models/foundations.toy_fail/run",
            content=canonical_json({"error": "RuntimeError", "message": "x"}),
        )
        api.get(
            "/v1/models/foundations.toy_time_value/run",
            params={"inputs": "eyJjYWxjdWxhdGlvbiI6ImZ1dHVyZV92YWx1ZSJ9"},
        )
        monkeypatch.setattr(
            "pyeconomics.server.app.listing.list_models",
            lambda *_a, **_k: (_ for _ in ()).throw(KeyError("value")),
        )
        api.get("/v1/models")
        points = world.metric_points()
    for _name, attributes in points[1:]:
        assert set(attributes) <= ATTRIBUTES
    routes = {
        a.get("http.route") for n, a in points if n == "http.server.request.duration"
    }
    assert "/v1/models/{model_id}/run" in routes
    assert not any("toy_time_value" in str(route) for route in routes)
    resource = points[0][1]
    assert resource["service.name"] == "pyeconomics-api"
    assert resource["deployment.environment.name"] == "test"
    for span in world.spans.get_finished_spans():
        assert set(span.attributes or {}) <= ATTRIBUTES
    for event in world.events:
        assert set(event) <= {
            "event_id",
            "timestamp",
            "platform",
            "level",
            "release",
            "environment",
            "message",
            "exception",
            "tags",
            "fingerprint",
            "sdk",
            "type",
        }
        assert set(event.get("tags", {})) <= observability.TAGS
        for value in event.get("exception", {}).get("values", []):
            assert value["value"] == observability.WITHHELD
            for frame in value["stacktrace"]["frames"]:
                assert "vars" not in frame
                assert "abs_path" not in frame
    crash = next(event for event in world.events if "exception" in event)
    assert crash["tags"]["route"] == "/v1/models"
    assert crash["exception"]["values"][-1]["type"] == "KeyError"


@pytest.mark.usefixtures("world")
def test_sentry_is_initialised_without_personal_data() -> None:
    telemetry = observability.start(component="api", git_sha="abc1234")
    try:
        assert telemetry.sentry is not None
        options = telemetry.sentry.options
        assert not options["send_default_pii"]
        # No mapping was passed: the SDK's own record says so, and user details
        # (the address among them) stay off. No integration reads the rest.
        assert options["data_collection"]["provided_by_user"] is False
        assert options["data_collection"]["user_info"] is False
        assert options["default_integrations"] is False
        assert options["auto_enabling_integrations"] is False
        assert dict(telemetry.sentry.integrations) == {}
        assert options["include_local_variables"] is False
        assert options["max_request_body_size"] == "never"
        assert options["max_breadcrumbs"] == 0
        assert options["traces_sample_rate"] == observability.TRACES_SAMPLE_RATE
        assert options["release"] == f"pyeconomics@{__version__}+abc1234"
        assert options["environment"] == "test"
        assert options["before_send"] is options["before_send_transaction"]
    finally:
        telemetry.close()


def test_clean_event_rebuilds_an_event_from_its_allowlist() -> None:
    address = "198.51.100.7"
    event = {
        "level": "error",
        "logentry": {"message": "%s failed", "params": [address], "formatted": "x"},
        "request": {"url": "https://pyeconomics.dev/v1/models?inputs=abc"},
        "user": {"ip_address": address},
        "extra": {"inputs": address},
        "contexts": {"trace": {"trace_id": "0" * 32}},
        "breadcrumbs": {"values": [{"message": address}]},
        "server_name": "instance-1",
        "modules": {"pyeconomics": "1"},
        "tags": {
            "route": "/v1/models",
            "client": address,
            "status": 500,
            "slug": "see https://h.example/x?k=1",
        },
        "fingerprint": ["problem", "internal-error"],
        "exception": {
            "values": [
                {
                    "type": "ValueError",
                    "value": f"bad {address}",
                    "module": None,
                    "mechanism": {"type": "pyeconomics", "handled": True, "data": {}},
                    "stacktrace": {
                        "frames": [
                            {
                                "filename": "pyeconomics/server/app.py",
                                "abs_path": "/usr/local/lib/python3.14/x.py",
                                "function": "_run",
                                "lineno": 3,
                                "vars": {"inputs": address},
                                "pre_context": ["see https://h.example/x"],
                                "in_app": True,
                            }
                        ]
                    },
                }
            ]
        },
    }
    cleaned = observability.clean_event(event)
    assert cleaned is not None
    assert address not in json.dumps(cleaned)
    assert cleaned["message"] == "x"
    assert cleaned["tags"] == {"route": "/v1/models", "status": "500"}
    frame = cleaned["exception"]["values"][0]["stacktrace"]["frames"][0]
    assert frame == {
        "filename": "pyeconomics/server/app.py",
        "function": "_run",
        "pre_context": ["see <url>"],
        "lineno": 3,
        "in_app": True,
    }
    assert cleaned["exception"]["values"][0]["mechanism"] == {
        "type": "pyeconomics",
        "handled": True,
    }
    assert set(cleaned) == {"level", "message", "tags", "fingerprint", "exception"}


@pytest.mark.parametrize(
    ("variable", "value"),
    [
        (SENTRY_DSN_VARIABLE, "https://{key}@o1.ingest.de.sentry.io/1"),
        (SENTRY_DSN_VARIABLE, "http://{key}@o1.ingest.us.sentry.io/1"),
        (SENTRY_DSN_VARIABLE, "https://{key}@o1.ingest.us.sentry.io:8443/1"),
        (SENTRY_DSN_VARIABLE, "https://{key}:x@o1.ingest.us.sentry.io/1"),
        (SENTRY_DSN_VARIABLE, "https://{key}@o1.ingest.us.sentry.io/1?x=1"),
        (SENTRY_DSN_VARIABLE, "https://[::1"),
        (OTLP_ENDPOINT_VARIABLE, "https://{key}.example.org/otlp"),
        (OTLP_HEADERS_VARIABLE, "Authorization=Bearer%20{key}"),
        (OTLP_HEADERS_VARIABLE, "Authorization=Basic%20{key},X-Key={key}"),
        (OTLP_HEADERS_VARIABLE, "{key}"),
        (DEPLOYMENT_VARIABLE, "Production {key}"),
    ],
)
def test_a_bad_setting_names_its_variable_never_its_value(
    variable: str, value: str
) -> None:
    key = secrets.token_hex(16)
    environ = {
        OTLP_ENDPOINT_VARIABLE: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp",
        OTLP_HEADERS_VARIABLE: f"Authorization=Basic%20{secrets.token_hex(16)}",
        variable: value.format(key=key),
    }
    with pytest.raises(ConfigError, match=variable) as caught:
        observability.start(component="api", git_sha="unknown", environ=environ)
    assert key not in str(caught.value)


def test_the_otlp_endpoint_and_headers_come_together() -> None:
    environ = {
        OTLP_ENDPOINT_VARIABLE: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp"
    }
    with pytest.raises(ConfigError, match=OTLP_HEADERS_VARIABLE):
        observability.start(component="api", git_sha="unknown", environ=environ)


def test_the_otlp_secret_is_registered_with_redaction_and_exporters_built() -> None:
    token = secrets.token_hex(24)
    environ = {
        OTLP_ENDPOINT_VARIABLE: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp",
        OTLP_HEADERS_VARIABLE: f"Authorization=Basic%20{token}",
    }
    telemetry = observability.start(
        component="snapshots", git_sha="unknown", environ=environ
    )
    try:
        assert redaction.scrub_text(f"sent {token}") == f"sent {redaction.MASK}"
        assert telemetry.sentry is None
        assert telemetry.meters is not None
        assert telemetry.tracers is None  # the job records no span
        assert telemetry.identity.release == f"pyeconomics@{__version__}"
    finally:
        # The periodic reader would try the network on shutdown: drop it unflushed.
        telemetry.meters = None
        telemetry.close()


def test_the_api_builds_otlp_span_and_metric_exporters() -> None:
    environ = {
        OTLP_ENDPOINT_VARIABLE: "https://otlp-gateway-prod-us-east-0.grafana.net/otlp",
        OTLP_HEADERS_VARIABLE: f"Authorization=Basic%20{secrets.token_hex(16)}",
    }
    telemetry = observability.start(component="api", git_sha="unknown", environ=environ)
    assert telemetry.tracers is not None
    assert telemetry.tracer is not None
    assert telemetry.failures is not None
    telemetry.meters = None
    telemetry.tracers = None
    telemetry.close()
    assert telemetry.failures not in logging.getLogger("opentelemetry").handlers


@pytest.mark.usefixtures("world")
def test_a_failed_export_logs_one_fixed_line() -> None:
    telemetry = observability.start(component="api", git_sha="unknown")
    records: list[logging.LogRecord] = []

    class Keep(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(record)

    handler = Keep()
    logging.getLogger("pyeconomics.server").addHandler(handler)
    try:
        logging.getLogger("opentelemetry.exporter.otlp").warning(
            "Failed to export batch: 401 %s", "a response body"
        )
    finally:
        logging.getLogger("pyeconomics.server").removeHandler(handler)
        telemetry.close()
    messages = [record.getMessage() for record in records]
    assert "telemetry: an OpenTelemetry export failed (WARNING)" in messages
    assert not any("response body" in message for message in messages)


@pytest.mark.usefixtures("world")
def test_close_flushes_once_and_never_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    telemetry = observability.start(component="api", git_sha="unknown")

    def broken(**_kwargs: object) -> None:
        raise RuntimeError

    assert telemetry.meters is not None
    monkeypatch.setattr(telemetry.meters, "shutdown", broken)
    telemetry.close()
    telemetry.close()


@pytest.mark.usefixtures("world")
def test_telemetry_never_breaks_a_request(monkeypatch: pytest.MonkeyPatch) -> None:
    telemetry = observability.start(component="api", git_sha="unknown")
    telemetry.instruments = None
    monkeypatch.setattr(telemetry, "tracer", "not a tracer")
    telemetry.request(
        method="BREW", route="/x", status=200, kind="probe", started=2, ended=1
    )
    monkeypatch.setattr(telemetry.sentry, "capture_event", None)
    telemetry.problem("internal-error", 500, "RuntimeError", route="/x")
    telemetry.exception(RuntimeError("x"), route="/x")
    telemetry.tracer = None
    telemetry.close()


def test_a_test_event_is_sent_and_returns_its_id(world: World) -> None:
    telemetry = observability.start(component="snapshots", git_sha="unknown")
    try:
        assert telemetry.test_event()
    finally:
        telemetry.close()
    assert world.events[-1]["message"] == "test event from pyeconomics-snapshots"
    assert world.events[-1]["tags"]["component"] == "snapshots"


def test_a_problem_below_500_is_not_sent(world: World) -> None:
    telemetry = observability.start(component="api", git_sha="unknown")
    telemetry.problem("invalid-input", 422, "InputError", route="/x")
    telemetry.close()
    assert world.events == []


def test_without_sentry_nothing_is_sent() -> None:
    identity = observability._Identity(  # noqa: SLF001
        component="api", deployment="x", version="1", git_sha="unknown"
    )
    telemetry = observability.Telemetry(identity=identity)
    telemetry.exception(RuntimeError("x"), route="/x")
    telemetry.problem("internal-error", 500, "RuntimeError", route="/x")
    telemetry.task(kind="run", model=None, cost="light", outcome="ok", seconds=1.0)
    assert telemetry.test_event() is None
    telemetry.close()


def _report(*, ok: bool) -> Report:
    today = dt.date(2026, 11, 10)
    good = codec.ProviderStatus(
        object=None,
        series={
            "a": codec.SeriesStatus(last_observation=today - dt.timedelta(days=3)),
            "b": codec.SeriesStatus(failure="upstream-unavailable"),
        },
    )
    bad = codec.ProviderStatus(
        object=None,
        failure="upstream-rate-limited",
        series={"c": codec.SeriesStatus(failure="upstream-rate-limited")},
    )
    manifest = codec.Manifest(
        run="20261110T233000Z-0a1b2c3d",
        completed_at=dt.datetime(2026, 11, 10, 23, 40, tzinfo=dt.UTC),
        providers={"treasury": good, "fed": bad},
    )
    return Report(
        run=manifest.run,
        manifest=manifest,
        succeeded=("treasury",) if ok else (),
        failed=("fed",) if ok else ("fed", "treasury"),
        series_written=1,
        series_failed=2,
        seconds=12.5,
        pruned=(),
        heartbeat="sent",
    )


def test_a_snapshot_run_records_its_series_age_and_failures(world: World) -> None:
    telemetry = observability.start(component="snapshots", git_sha="unknown")
    telemetry.snapshot(_report(ok=True))
    points = world.metric_points()
    telemetry.close()
    series = {
        (a["pyeconomics.provider"], a["pyeconomics.state"])
        for n, a in points
        if n == "pyeconomics.snapshot.series"
    }
    assert series == {
        ("treasury", "written"),
        ("treasury", "failed"),
        ("fed", "written"),
        ("fed", "failed"),
    }
    names = {n for n, _ in points}
    assert {"pyeconomics.snapshot.ok", "pyeconomics.snapshot.duration"} <= names
    assert "pyeconomics.snapshot.data_age" in names
    messages = [event["message"] for event in world.events]
    assert messages == ["snapshot provider fed failed: upstream-rate-limited"]
    # Error level: Sentry alerts on new high-priority issues, which a warning is not.
    assert world.events[0]["level"] == "error"


def test_a_snapshot_run_with_no_success_is_an_error(world: World) -> None:
    telemetry = observability.start(component="snapshots", git_sha="unknown")
    telemetry.snapshot(_report(ok=False))
    telemetry.close()
    assert world.events[-1]["message"] == "snapshot run failed: no provider succeeded"
    assert world.events[-1]["level"] == "error"


def test_the_snapshot_job_runs_the_writer_observed(
    monkeypatch: pytest.MonkeyPatch, world: World
) -> None:
    from pyeconomics.data.snapshots import __main__ as command  # noqa: PLC0415

    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    seen: list[object] = []

    def run(argv: list[str], *, observe: Any = None) -> int:  # noqa: ANN401
        seen.append(argv)
        observe(_report(ok=True))
        return 0

    monkeypatch.setattr(command, "main", run)
    assert snapshot_job.main(["write"]) == 0
    assert seen == [["write"]]
    assert world.events[0]["tags"]["component"] == "snapshots"


def test_the_snapshot_job_reports_a_crash_and_raises_it(
    monkeypatch: pytest.MonkeyPatch, world: World
) -> None:
    from pyeconomics.data.snapshots import __main__ as command  # noqa: PLC0415

    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")

    def crash(_argv: list[str], **_kwargs: object) -> int:
        msg = "x"
        raise RuntimeError(msg)

    monkeypatch.setattr(command, "main", crash)
    with pytest.raises(RuntimeError):
        snapshot_job.main(["write"])
    assert world.events[-1]["exception"]["values"][-1]["type"] == "RuntimeError"


def test_the_snapshot_job_without_telemetry_is_the_writer_alone(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from pyeconomics.data.snapshots import __main__ as command  # noqa: PLC0415

    calls: list[tuple[list[str], dict[str, object]]] = []

    def run(argv: list[str], **kwargs: object) -> int:
        calls.append((argv, kwargs))
        return 1

    monkeypatch.setattr(command, "main", run)
    assert snapshot_job.main(["write"]) == 1
    assert calls == [(["write"], {})]
    assert snapshot_job.main(["read"]) == 2


def test_the_snapshot_job_refuses_a_bad_setting(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    key = secrets.token_hex(16)
    monkeypatch.setenv("PYECONOMICS_MODE", "hosted")
    monkeypatch.setenv(SENTRY_DSN_VARIABLE, f"https://{key}@example.org/1")
    assert snapshot_job.main(["write"]) == 2
    error = capsys.readouterr().err
    assert SENTRY_DSN_VARIABLE in error
    assert key not in error


@pytest.mark.usefixtures("world")
def test_the_test_event_command(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    assert observability._main(["x"]) == 2  # noqa: SLF001
    assert observability._main(["test-event"]) == 0  # noqa: SLF001
    assert capsys.readouterr().out.startswith("test event: sent ")
    # Without the DSN there is nothing to send to: the unpatched start, all off.
    monkeypatch.delenv(SENTRY_DSN_VARIABLE)
    monkeypatch.setattr(observability, "start", REAL_START)
    assert observability._main(["test-event"]) == 1  # noqa: SLF001
    assert capsys.readouterr().out == "test event: not configured\n"


def test_local_mode_never_imports_the_telemetry(tmp_path: Any) -> None:  # noqa: ANN401
    script = (
        "import os, sys\n"
        f"os.environ[{SENTRY_DSN_VARIABLE!r}] = {fake_dsn()!r}\n"
        f"os.environ[{OTLP_ENDPOINT_VARIABLE!r}] = 'https://otlp-gateway-prod-us-east-0.grafana.net/otlp'\n"
        "from fastapi.testclient import TestClient\n"
        "from pyeconomics.server import create_app, ServerSettings\n"
        "app = create_app(mode='local', settings=ServerSettings(workers=0))\n"
        "with TestClient(app, base_url='http://127.0.0.1') as api:\n"
        "    print(api.get('/healthz').status_code)\n"
        "for name in ("
        + repr(SENTRY_DSN_VARIABLE)
        + ", "
        + repr(OTLP_ENDPOINT_VARIABLE)
        + "):\n"
        "    del os.environ[name]\n"
        "app = create_app(mode='hosted', settings=ServerSettings(workers=0))\n"
        "with TestClient(app, base_url='http://127.0.0.1') as api:\n"
        "    print(api.get('/healthz').status_code)\n"
        # FastAPI, Starlette and MCP import OpenTelemetry's API, a no-op without
        # a provider; the SDK, the exporters and Sentry must not load.
        "loaded = sorted(m for m in sys.modules if m.startswith(('sentry_sdk',"
        " 'opentelemetry.sdk', 'opentelemetry.exporter'))"
        " or m == 'pyeconomics.server.observability')\n"
        "from opentelemetry import metrics, trace\n"
        "print(type(trace.get_tracer_provider()).__name__,"
        " type(metrics.get_meter_provider()).__name__)\n"
        "print(loaded)\n"
    )
    result = subprocess.run(  # noqa: S603 # nosec B603: fixed arguments, no shell
        [sys.executable, "-I", "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        timeout=120,
    )
    assert result.stdout.splitlines() == [
        "200",
        "200",
        "ProxyTracerProvider _ProxyMeterProvider",
        "[]",
    ]
