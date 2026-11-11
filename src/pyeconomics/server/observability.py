# src/pyeconomics/server/observability.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Errors and telemetry for the hosted service (Phase 5 Step 14; ADR-0013 decision 15).

:func:`start` runs once, when a hosted server or the snapshot job starts with
its variables set (:func:`~pyeconomics.server.settings.telemetry_wanted`). A
local server never imports this module, and neither does a worker process:
workers report through the outcomes their parent records. Its libraries come
from the ``hosted`` dependency group, which only the image installs, so no
user's installation can send telemetry.

- **Errors** go to Sentry (``PYECONOMICS_SENTRY_DSN``) through a client of this
  module's own, never the SDK's global one, and with no integration, so nothing
  is captured but what :class:`Telemetry` sends: an exception that reached the
  server's last resort, a worker's problem of status 500 or more, and a snapshot
  provider's failure. The client sends no default personal data, request body,
  local variable or breadcrumb, and :func:`clean_event` rebuilds every event
  from an allowlist: each string goes through
  :func:`~pyeconomics.surfaces.problems.scrub`, and an exception's message is
  withheld, as a problem withholds an unexpected error's message.
- **Telemetry** goes to Grafana Cloud's OTLP gateway
  (``PYECONOMICS_OTLP_ENDPOINT`` and ``PYECONOMICS_OTLP_HEADERS``): a request
  histogram by route template, method, status class and route kind; a count of
  tasks by kind, model id, cost class and outcome; one span per sampled request;
  and the snapshot job's run, series and data age. No attribute holds a path, a
  query, an input, an address or a key.
- :meth:`Telemetry.close` flushes both. The app's lifespan calls it when Cloud
  Run's ``SIGTERM`` stops the server: Cloud Run throttles the CPU between
  requests, so the exporters' background threads may not run until then.

Each exporter's host is declared, as a provider's hosts are: a DSN on Sentry's
US ingest, an endpoint on Grafana Cloud's OTLP gateway. Anything else is a
:class:`~pyeconomics.data.errors.ConfigError` naming the variable, never its
value; every secret is registered with redaction before anything can log it.
"""

from __future__ import annotations

import logging
import re
import sys
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final, Literal, cast

from pyeconomics import __version__
from pyeconomics.data import redaction
from pyeconomics.data.errors import ConfigError
from pyeconomics.server.settings import (
    DEPLOYMENT_VARIABLE,
    OTLP_ENDPOINT_VARIABLE,
    OTLP_HEADERS_VARIABLE,
    SENTRY_DSN_VARIABLE,
)
from pyeconomics.surfaces.problems import scrub

if TYPE_CHECKING:
    from collections.abc import Mapping

    from opentelemetry.metrics import Counter, Histogram
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import MetricReader
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SpanExporter
    from opentelemetry.sdk.trace.sampling import Sampler
    from opentelemetry.trace import Tracer
    from sentry_sdk import Client
    from sentry_sdk.transport import Transport
    from sentry_sdk.types import Event, Hint

    from pyeconomics.data.snapshots.writer import Report

__all__ = [
    "DEPLOYMENT_VARIABLE",
    "DURATION_BUCKETS",
    "OTLP_ENDPOINT_VARIABLE",
    "OTLP_HEADERS_VARIABLE",
    "SENTRY_DSN_VARIABLE",
    "TAGS",
    "TRACES_SAMPLE_RATE",
    "WITHHELD",
    "Component",
    "Telemetry",
    "clean_event",
    "metric_route",
    "start",
    "status_class",
]

#: The share of requests traced, by OpenTelemetry and, should anything start
#: one, by Sentry; low, because the free tiers count spans.
TRACES_SAMPLE_RATE: Final = 0.05
#: The request and task histograms' bucket bounds, in seconds; few, because each
#: bound is a series of its own in Grafana Cloud's 10,000.
DURATION_BUCKETS: Final = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0)
#: The tags an error event may carry; any other is dropped.
TAGS: Final = frozenset(
    {
        "component",
        "deployment",
        "error",
        "kind",
        "model",
        "provider",
        "route",
        "slug",
        "status",
    }
)
#: What an exception's message becomes in an error event.
WITHHELD: Final = "(withheld: pyeconomics never reports an unexpected error's message)"

#: What runs: the API service or the snapshot job.
Component = Literal["api", "snapshots"]

_SENTRY_DSN: Final = re.compile(
    r"https://(?P<key>[0-9a-f]{32})@o\d{1,12}\.ingest\.us\.sentry\.io/\d{1,20}"
)
_ESCAPE: Final = re.compile(r"%([0-9A-Fa-f]{2})")
_OTLP_ENDPOINT: Final = re.compile(
    r"https://otlp-gateway-[a-z0-9-]{1,64}\.grafana\.net/otlp"
)
_DEPLOYMENT: Final = re.compile(r"[a-z][a-z0-9-]{0,31}")
_METHODS: Final = frozenset(
    {"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"}
)
_RUN_ROUTE: Final = "/v1/models/{model_id}/run"
_EVENT_KEYS: Final = (
    "event_id",
    "timestamp",
    "start_timestamp",
    "platform",
    "level",
    "logger",
    "type",
    "transaction",
    "release",
    "environment",
)
_FRAME_TEXT: Final = ("filename", "function", "module", "context_line")
_FRAME_LINES: Final = ("pre_context", "post_context")
#: A tag's value: a route's template, a slug, a type name, a model or provider id.
#: Tags come only from this module's fixed vocabularies, so free text, a query or
#: a URL is dropped rather than scrubbed (a template looks like a path to scrub).
_TAG_VALUE: Final = re.compile(r"[A-Za-z0-9_.:/{}()<> -]{1,200}")
_INSTRUMENTATION: Final = "pyeconomics"
_LOGGER: Final = logging.getLogger("pyeconomics.server")
#: Where OpenTelemetry's exporters log a failed export.
_OTEL_LOGGER: Final = "opentelemetry"


class _ExportFailures(logging.Handler):
    """Turn an exporter's failure into one fixed line on the server's logger.

    The server drops what other libraries log (:mod:`~pyeconomics.server.logs`),
    so an expired token would stop the metrics silently. The exporter's own
    message is never repeated: it can quote a response.
    """

    def __init__(self) -> None:
        super().__init__(logging.WARNING)

    def emit(self, record: logging.LogRecord) -> None:
        """Log that an export failed, and nothing of what the exporter said."""
        _LOGGER.warning(
            "telemetry: an OpenTelemetry export failed (%s)", record.levelname
        )


def status_class(status: int) -> str:
    """Return a status's class: ``2xx``, ``4xx`` or ``5xx``.

    >>> status_class(404)
    '4xx'
    """
    return f"{status // 100}xx"


def metric_route(template: str) -> str:
    """Return a route template for a metric: a model's run routes become one.

    Each model has its own run routes, so a histogram by template would hold a
    series per model and bucket; the task count keeps the model id instead.

    >>> metric_route("/v1/models/foundations.time_value/run")
    '/v1/models/{model_id}/run'
    >>> metric_route("/v1/series/{target:path}")
    '/v1/series/{target:path}'
    """
    if template.startswith("/v1/models/") and template.endswith("/run"):
        return _RUN_ROUTE
    return template


# --- what an error event may hold --------------------------------------------------


def _text(value: object) -> str | None:
    return scrub(value) if isinstance(value, str) else None


def _frame(frame: Mapping[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {}
    for key in _FRAME_TEXT:
        text = _text(frame.get(key))
        if text is not None:
            kept[key] = text
    for key in _FRAME_LINES:
        lines = frame.get(key)
        if isinstance(lines, list):
            kept[key] = [scrub(line) for line in lines if isinstance(line, str)]
    if isinstance(frame.get("lineno"), int):
        kept["lineno"] = frame["lineno"]
    if isinstance(frame.get("in_app"), bool):
        kept["in_app"] = frame["in_app"]
    return kept


def _exception(value: Mapping[str, Any]) -> dict[str, Any]:
    kept: dict[str, Any] = {"value": WITHHELD}
    for key in ("type", "module"):
        text = _text(value.get(key))
        if text is not None:
            kept[key] = text
    mechanism = value.get("mechanism")
    if isinstance(mechanism, dict):
        kept["mechanism"] = {
            key: mechanism[key]
            for key in ("type", "handled")
            if isinstance(mechanism.get(key), str | bool)
        }
    frames = (value.get("stacktrace") or {}).get("frames")
    if isinstance(frames, list):
        kept["stacktrace"] = {
            "frames": [_frame(item) for item in frames if isinstance(item, dict)]
        }
    return kept


def _message(event: Mapping[str, Any]) -> str | None:
    message = event.get("message")
    if isinstance(message, str):
        return scrub(message)
    entry = event.get("logentry")
    if isinstance(entry, dict):
        for key in ("formatted", "message"):
            if isinstance(entry.get(key), str):
                return scrub(entry[key])
    return None


def clean_event(
    event: Mapping[str, Any], _hint: object = None
) -> dict[str, Any] | None:
    """Rebuild an error event from an allowlist, every string scrubbed.

    Sentry's ``before_send`` and ``before_send_transaction``. What survives: the
    event's id, time, platform, level, logger, release and environment; its
    message; each exception's type and module, with its message withheld, and
    each frame's file, function, line and source lines; the tags in
    :data:`TAGS` whose values are plain identifiers or route templates; the
    fingerprint and the SDK's name. A request, a user, extra
    data, contexts, breadcrumbs, local variables, modules and the server's name
    never leave.

    >>> clean_event({"level": "error", "message": "GET https://h.example/x?k=1",
    ...              "user": {"ip_address": "203.0.113.9"}, "tags": {"q": "1"}})
    {'level': 'error', 'message': 'GET <url>'}
    """
    cleaned: dict[str, Any] = {}
    for key in _EVENT_KEYS:
        value = event.get(key)
        if isinstance(value, str):
            cleaned[key] = scrub(value)
        elif isinstance(value, int | float) and not isinstance(value, bool):
            cleaned[key] = value
    message = _message(event)
    if message is not None:
        cleaned["message"] = message
    values = (event.get("exception") or {}).get("values")
    if isinstance(values, list):
        cleaned["exception"] = {
            "values": [_exception(item) for item in values if isinstance(item, dict)]
        }
    tags = event.get("tags")
    if isinstance(tags, dict):
        kept = {
            str(key): str(value)
            for key, value in tags.items()
            if key in TAGS
            and isinstance(value, str | int)
            and _TAG_VALUE.fullmatch(str(value))
            and "://" not in str(value)
        }
        if kept:
            cleaned["tags"] = kept
    fingerprint = event.get("fingerprint")
    if isinstance(fingerprint, list):
        cleaned["fingerprint"] = [scrub(str(part)) for part in fingerprint]
    sdk = event.get("sdk")
    if isinstance(sdk, dict):
        cleaned["sdk"] = {
            key: sdk[key]
            for key in ("name", "version")
            if isinstance(sdk.get(key), str)
        }
    return cleaned


# --- the configuration ---------------------------------------------------------------


def _value(environ: Mapping[str, str], name: str) -> str:
    return environ.get(name, "").strip()


def _dsn(text: str) -> str:
    """Check a DSN names Sentry's US ingest; register its key; never show it.

    One anchored pattern, never a URL parser: no server module parses a URL
    (``tests/server/test_server_layering.py``).
    """
    match = _SENTRY_DSN.fullmatch(text)
    if match is None:
        msg = (
            f"{SENTRY_DSN_VARIABLE} is not a Sentry DSN on the US ingest "
            "(https://<key>@o<org>.ingest.us.sentry.io/<project>)"
        )
        raise ConfigError(msg)
    redaction.register(text)
    redaction.register(match.group("key"))
    return text


def _percent_decoded(text: str) -> str:
    """Decode ``%XX`` escapes, as OpenTelemetry's header format writes them."""
    return _ESCAPE.sub(lambda found: chr(int(found.group(1), 16)), text)


def _otlp_headers(text: str) -> dict[str, str]:
    """Read ``Authorization=Basic%20<token>``; register its secret parts."""
    headers: dict[str, str] = {}
    for item in text.split(","):
        name, separator, value = item.partition("=")
        if not separator:
            headers = {}
            break
        headers[_percent_decoded(name).strip()] = _percent_decoded(value).strip()
    authorization = headers.get("Authorization", "")
    scheme, _, token = authorization.partition(" ")
    if set(headers) != {"Authorization"} or scheme != "Basic" or len(token) < 16:  # noqa: PLR2004
        msg = (
            f"{OTLP_HEADERS_VARIABLE} holds one header, as Grafana Cloud writes it: "
            "Authorization=Basic%20<token>"
        )
        raise ConfigError(msg)
    for secret in (text, authorization, token):
        redaction.register(secret)
    return headers


def _endpoint(text: str) -> str:
    if not _OTLP_ENDPOINT.fullmatch(text):
        msg = (
            f"{OTLP_ENDPOINT_VARIABLE} is not Grafana Cloud's OTLP gateway "
            "(https://otlp-gateway-<region>.grafana.net/otlp)"
        )
        raise ConfigError(msg)
    return text


def _deployment(environ: Mapping[str, str]) -> str:
    text = _value(environ, DEPLOYMENT_VARIABLE) or "hosted"
    if not _DEPLOYMENT.fullmatch(text):
        msg = f"{DEPLOYMENT_VARIABLE} is a short lower-case name, such as production"
        raise ConfigError(msg)
    return text


@dataclass(frozen=True, slots=True, kw_only=True)
class _Identity:
    component: Component
    deployment: str
    version: str
    git_sha: str

    @property
    def release(self) -> str:
        sha = "" if self.git_sha == "unknown" else f"+{self.git_sha}"
        return f"pyeconomics@{self.version}{sha}"

    @property
    def service(self) -> str:
        return f"pyeconomics-{self.component}"


def _before_send(event: Event, _hint: Hint) -> Event | None:
    """Sentry's hook: :func:`clean_event`."""
    return cast("Event", clean_event(event))


def _sentry(dsn: str, identity: _Identity, transport: type[Transport] | None) -> Client:
    import sentry_sdk  # noqa: PLC0415 - the hosted group

    # Neither send_default_pii nor data_collection is passed: the latter would
    # switch to defaults that collect addresses and bodies (ADR-0013 decision 15).
    return sentry_sdk.Client(
        dsn=dsn,
        release=identity.release,
        environment=identity.deployment,
        server_name=identity.service,
        default_integrations=False,
        auto_enabling_integrations=False,
        integrations=[],
        include_local_variables=False,
        max_request_body_size="never",
        max_breadcrumbs=0,
        attach_stacktrace=False,
        auto_session_tracking=False,
        send_client_reports=False,
        enable_metrics=False,
        enable_logs=False,
        propagate_traces=False,
        trace_propagation_targets=[],
        traces_sample_rate=TRACES_SAMPLE_RATE,
        before_send=_before_send,
        before_send_transaction=_before_send,
        before_breadcrumb=lambda _crumb, _hint: None,
        transport=transport,
        shutdown_timeout=2,
    )


# --- the telemetry -----------------------------------------------------------------


@dataclass(slots=True, kw_only=True)
class _Instruments:
    requests: Histogram
    tasks: Counter
    task_seconds: Histogram
    # The API's synchronous gauge has no public type name yet (_Gauge in 1.45).
    snapshot_ok: Any
    snapshot_seconds: Any
    snapshot_series: Any
    snapshot_age: Any


@dataclass(slots=True, kw_only=True)
class Telemetry:
    """What a hosted process reports: errors, metrics and sampled spans.

    Every method swallows its own failure: telemetry never breaks a request.
    """

    identity: _Identity
    sentry: Client | None = None
    meters: MeterProvider | None = None
    tracers: TracerProvider | None = None
    instruments: _Instruments | None = None
    tracer: Tracer | None = None
    failures: logging.Handler | None = None
    _closed: bool = field(default=False, init=False)

    # The API's requests and tasks.

    def request(  # noqa: PLR0913 - one request's facts
        self,
        *,
        method: str,
        route: str,
        status: int,
        kind: str,
        started: int,
        ended: int,
        details: Mapping[str, str] | None = None,
    ) -> None:
        """Record a request: its duration by route, and a span when sampled.

        ``started`` and ``ended`` are ``time.time_ns()`` values; ``details``
        holds the task's model id, cost class and outcome, when it ran one.
        """
        try:
            verb = method if method in _METHODS else "_OTHER"
            attributes = {
                "http.request.method": verb,
                "http.route": metric_route(route),
                "pyeconomics.status_class": status_class(status),
                "pyeconomics.route_kind": kind,
            }
            if self.instruments is not None:
                self.instruments.requests.record(
                    max(ended - started, 0) / 1e9, attributes
                )
            if self.tracer is not None:
                self._span(
                    verb,
                    route,
                    status,
                    attributes,
                    started=started,
                    ended=ended,
                    details=details,
                )
        except Exception:  # noqa: BLE001 - telemetry never breaks a request
            _LOGGER.warning("telemetry could not record a request")

    def _span(  # noqa: PLR0913 - one span's facts
        self,
        verb: str,
        route: str,
        status: int,
        attributes: Mapping[str, str],
        *,
        started: int,
        ended: int,
        details: Mapping[str, str] | None,
    ) -> None:
        from opentelemetry.trace import SpanKind, Status, StatusCode  # noqa: PLC0415

        tracer = self.tracer
        if tracer is None:  # pragma: no cover - checked by the caller
            return
        span = tracer.start_span(
            f"{verb} {route}",
            kind=SpanKind.SERVER,
            start_time=started,
            attributes={**attributes, "http.route": route},
        )
        for key, value in (details or {}).items():
            span.set_attribute(f"pyeconomics.{key}", value)
        if status >= 500:  # noqa: PLR2004 - a server error
            span.set_status(Status(StatusCode.ERROR))
        span.end(end_time=max(ended, started))

    def task(
        self, *, kind: str, model: str | None, cost: str, outcome: str, seconds: float
    ) -> None:
        """Count a worker task by kind, model id, cost class and outcome."""
        try:
            if self.instruments is None:
                return
            attributes = {
                "pyeconomics.task_kind": kind,
                "pyeconomics.cost_class": cost,
                "pyeconomics.outcome": outcome,
            }
            counted = dict(attributes)
            if model is not None:
                counted["pyeconomics.model"] = model
            self.instruments.tasks.add(1, counted)
            self.instruments.task_seconds.record(
                max(seconds, 0.0),
                {
                    **attributes,
                    "pyeconomics.outcome": "ok" if outcome == "ok" else "problem",
                },
            )
        except Exception:  # noqa: BLE001 - telemetry never breaks a request
            _LOGGER.warning("telemetry could not record a task")

    # Errors.

    def exception(self, error: BaseException, *, route: str) -> None:
        """Send an exception that reached the last resort: its type and frames."""
        if self.sentry is None:
            return
        try:
            from sentry_sdk.utils import event_from_exception  # noqa: PLC0415

            event, hint = event_from_exception(
                (type(error), error, error.__traceback__),
                client_options=self.sentry.options,
                mechanism={"type": "pyeconomics", "handled": True},
            )
            event["tags"] = self._tags(route=route)
            self._capture(event, hint)
        except Exception:  # noqa: BLE001 - telemetry never breaks a request
            _LOGGER.warning("telemetry could not send an error")

    def problem(self, slug: str, status: int, error: str, *, route: str) -> None:
        """Send a server's problem (status 500 or more) as one grouped issue."""
        if self.sentry is None or status < 500:  # noqa: PLR2004 - server errors only
            return
        event = {
            "level": "error",
            "message": f"{slug} ({status}, {error})",
            "tags": self._tags(route=route, slug=slug, status=str(status), error=error),
            "fingerprint": ["problem", slug, error],
        }
        self._capture(event)

    def _tags(self, **tags: str) -> dict[str, str]:
        return {
            "component": self.identity.component,
            "deployment": self.identity.deployment,
            **tags,
        }

    def _capture(self, event: Mapping[str, Any], hint: Hint | None = None) -> None:
        if self.sentry is None:
            return
        try:
            import sentry_sdk  # noqa: PLC0415 - the hosted group

            # A fresh scope: nothing global reaches the event.
            self.sentry.capture_event(
                cast("Event", dict(event)), hint=hint, scope=sentry_sdk.Scope()
            )
        except Exception:  # noqa: BLE001 - telemetry never breaks a request
            _LOGGER.warning("telemetry could not send an error")

    # The snapshot job.

    def snapshot(self, report: Report) -> None:
        """Record a snapshot run: whether it worked, its time, series and data age.

        A provider that failed becomes a warning grouped by provider and problem
        slug; a run in which none succeeded becomes an error.
        """
        manifest = report.manifest
        today = manifest.completed_at.date()
        try:
            if self.instruments is not None:
                run = {"pyeconomics.deployment": self.identity.deployment}
                self.instruments.snapshot_ok.set(1 if report.ok else 0, run)
                self.instruments.snapshot_seconds.set(report.seconds, run)
                for provider, status in sorted(manifest.providers.items()):
                    labels = {**run, "pyeconomics.provider": provider}
                    states = [series.failure for series in status.series.values()]
                    for state, count in (
                        ("written", sum(1 for s in states if s is None)),
                        ("failed", sum(1 for s in states if s is not None)),
                    ):
                        self.instruments.snapshot_series.set(
                            count, {**labels, "pyeconomics.state": state}
                        )
                    dates = [
                        s.last_observation
                        for s in status.series.values()
                        if s.last_observation is not None
                    ]
                    if dates:
                        self.instruments.snapshot_age.set(
                            (today - max(dates)).days, labels
                        )
        except Exception:  # noqa: BLE001 - telemetry never stops the job
            _LOGGER.warning("telemetry could not record the snapshot run")
        for provider in report.failed:
            slug = manifest.providers[provider].failure or "internal-error"
            self._capture(
                {
                    "level": "warning",
                    "message": f"snapshot provider {provider} failed: {slug}",
                    "tags": self._tags(provider=provider, slug=slug, route="snapshot"),
                    "fingerprint": ["snapshot", provider, slug],
                }
            )
        if not report.ok:
            self._capture(
                {
                    "level": "error",
                    "message": "snapshot run failed: no provider succeeded",
                    "tags": self._tags(route="snapshot"),
                    "fingerprint": ["snapshot", "run-failed"],
                }
            )

    def test_event(self) -> str | None:
        """Send one test event; return its id (the alarm proof's, Step 14)."""
        if self.sentry is None:
            return None
        import sentry_sdk  # noqa: PLC0415 - the hosted group

        event = {
            "level": "error",
            "message": f"test event from {self.identity.service}",
            "tags": self._tags(route="test"),
            "fingerprint": ["test-event", self.identity.component],
        }
        return self.sentry.capture_event(cast("Event", event), scope=sentry_sdk.Scope())

    def close(self) -> None:
        """Flush and stop every exporter, within Cloud Run's ten-second grace."""
        if self._closed:
            return
        self._closed = True
        started = time.monotonic()
        for name, stop in (
            ("errors", self._close_errors),
            ("traces", self._close_traces),
            ("metrics", self._close_metrics),
        ):
            try:
                stop()
            except Exception:  # noqa: BLE001 - shutting down never raises
                _LOGGER.warning("telemetry could not flush its %s", name)
        if self.failures is not None:
            logging.getLogger(_OTEL_LOGGER).removeHandler(self.failures)
        _LOGGER.info("telemetry flushed in %.1f s", time.monotonic() - started)

    def _close_errors(self) -> None:
        if self.sentry is not None:
            self.sentry.close(timeout=2)

    def _close_traces(self) -> None:
        if self.tracers is not None:
            self.tracers.shutdown()

    def _close_metrics(self) -> None:
        if self.meters is not None:
            self.meters.shutdown(timeout_millis=4000)


def _instruments(meters: MeterProvider) -> _Instruments:
    meter = meters.get_meter(_INSTRUMENTATION, __version__)
    return _Instruments(
        requests=meter.create_histogram(
            "http.server.request.duration", unit="s", description="Request duration"
        ),
        tasks=meter.create_counter(
            "pyeconomics.tasks", unit="{task}", description="Worker tasks by outcome"
        ),
        task_seconds=meter.create_histogram(
            "pyeconomics.task.duration", unit="s", description="Worker task duration"
        ),
        snapshot_ok=meter.create_gauge(
            "pyeconomics.snapshot.ok",
            unit="1",
            description="1 if any provider succeeded",
        ),
        snapshot_seconds=meter.create_gauge(
            "pyeconomics.snapshot.duration", unit="s", description="Snapshot run time"
        ),
        snapshot_series=meter.create_gauge(
            "pyeconomics.snapshot.series",
            unit="{series}",
            description="Series by state",
        ),
        snapshot_age=meter.create_gauge(
            "pyeconomics.snapshot.data_age",
            unit="d",
            description="Days since the newest observation",
        ),
    )


def _meters(
    identity: _Identity,
    endpoint: str | None,
    headers: dict[str, str] | None,
    reader: MetricReader | None,
) -> MeterProvider | None:
    from opentelemetry.sdk.metrics import MeterProvider  # noqa: PLC0415
    from opentelemetry.sdk.metrics.view import (  # noqa: PLC0415
        ExplicitBucketHistogramAggregation,
        View,
    )

    if reader is None:
        if endpoint is None or headers is None:
            return None
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (  # noqa: PLC0415
            OTLPMetricExporter,
        )
        from opentelemetry.sdk.metrics.export import (  # noqa: PLC0415
            PeriodicExportingMetricReader,
        )

        reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(
                endpoint=f"{endpoint}/v1/metrics", headers=headers, timeout=5
            ),
            export_interval_millis=60_000,
            export_timeout_millis=5_000,
        )
    buckets = ExplicitBucketHistogramAggregation(DURATION_BUCKETS)
    return MeterProvider(
        metric_readers=[reader],
        resource=_resource(identity),
        shutdown_on_exit=False,
        views=[
            View(instrument_name="http.server.request.duration", aggregation=buckets),
            View(instrument_name="pyeconomics.task.duration", aggregation=buckets),
        ],
    )


def _tracers(
    identity: _Identity,
    endpoint: str | None,
    headers: dict[str, str] | None,
    exporter: SpanExporter | None,
) -> TracerProvider | None:
    from opentelemetry.sdk.trace import TracerProvider  # noqa: PLC0415
    from opentelemetry.sdk.trace.export import (  # noqa: PLC0415
        BatchSpanProcessor,
        SimpleSpanProcessor,
    )
    from opentelemetry.sdk.trace.sampling import TraceIdRatioBased  # noqa: PLC0415

    if exporter is None:
        if endpoint is None or headers is None:
            return None
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: PLC0415
            OTLPSpanExporter,
        )

        processor: Any = BatchSpanProcessor(
            OTLPSpanExporter(
                endpoint=f"{endpoint}/v1/traces", headers=headers, timeout=5
            )
        )
        sampler: Sampler = TraceIdRatioBased(TRACES_SAMPLE_RATE)
    else:
        from opentelemetry.sdk.trace.sampling import ALWAYS_ON  # noqa: PLC0415

        processor, sampler = SimpleSpanProcessor(exporter), ALWAYS_ON
    tracers = TracerProvider(
        resource=_resource(identity), sampler=sampler, shutdown_on_exit=False
    )
    tracers.add_span_processor(processor)
    return tracers


def _resource(identity: _Identity) -> Any:  # noqa: ANN401 - the SDK's Resource
    from opentelemetry.sdk.resources import Resource  # noqa: PLC0415

    return Resource.create(
        {
            "service.name": identity.service,
            "service.namespace": "pyeconomics",
            "service.version": identity.version,
            "deployment.environment.name": identity.deployment,
            "vcs.ref.head.revision": identity.git_sha,
        }
    )


def start(  # noqa: PLR0913 - the configuration and the tests' seams
    *,
    component: Component,
    git_sha: str,
    environ: Mapping[str, str] | None = None,
    sentry_transport: type[Transport] | None = None,
    metric_reader: MetricReader | None = None,
    span_exporter: SpanExporter | None = None,
) -> Telemetry:
    """Start what the environment configures and return it.

    Parameters
    ----------
    component
        ``api`` (the service) or ``snapshots`` (the job), which records no span.
    git_sha
        The commit the image was built from.
    environ
        The variables; the process's environment by default.
    sentry_transport, metric_reader, span_exporter
        Seams for tests: where events, metrics and spans go instead of the
        vendors. A reader or an exporter stands in for the OTLP endpoint.

    Raises
    ------
    ConfigError
        If a variable is set to something it cannot be; the message names the
        variable, never its value.
    """
    import os  # noqa: PLC0415

    env = os.environ if environ is None else environ
    identity = _Identity(
        component=component,
        deployment=_deployment(env),
        version=__version__,
        git_sha=git_sha,
    )
    dsn_text = _value(env, SENTRY_DSN_VARIABLE)
    endpoint_text = _value(env, OTLP_ENDPOINT_VARIABLE)
    headers_text = _value(env, OTLP_HEADERS_VARIABLE)
    if bool(endpoint_text) != bool(headers_text):
        msg = f"set {OTLP_ENDPOINT_VARIABLE} and {OTLP_HEADERS_VARIABLE} together"
        raise ConfigError(msg)
    endpoint = _endpoint(endpoint_text) if endpoint_text else None
    headers = _otlp_headers(headers_text) if headers_text else None
    sentry = _sentry(_dsn(dsn_text), identity, sentry_transport) if dsn_text else None
    meters = _meters(identity, endpoint, headers, metric_reader)
    tracers = (
        _tracers(identity, endpoint, headers, span_exporter)
        if component == "api"
        else None
    )
    telemetry = Telemetry(
        identity=identity,
        sentry=sentry,
        meters=meters,
        tracers=tracers,
        instruments=None if meters is None else _instruments(meters),
        tracer=None
        if tracers is None
        else tracers.get_tracer(_INSTRUMENTATION, __version__),
    )
    if meters is not None or tracers is not None:
        telemetry.failures = _ExportFailures()
        logging.getLogger(_OTEL_LOGGER).addHandler(telemetry.failures)
    _LOGGER.info(
        "telemetry started: errors=%s metrics=%s traces=%s",
        "on" if sentry else "off",
        "on" if meters else "off",
        "on" if tracers else "off",
    )
    return telemetry


def _main(argv: list[str]) -> int:
    """``python -m pyeconomics.server.observability test-event``: one test event."""
    if argv != ["test-event"]:
        sys.stderr.write(
            "usage: python -m pyeconomics.server.observability test-event\n"
        )
        return 2
    from pyeconomics.server import logs  # noqa: PLC0415
    from pyeconomics.server.settings import ServerSettings, git_sha  # noqa: PLC0415

    handler = logs.configure(sys.stderr)
    try:
        telemetry = start(component="snapshots", git_sha=git_sha(ServerSettings()))
        sent = telemetry.test_event()
        telemetry.close()
    finally:
        logs.release(handler)
    sys.stdout.write(f"test event: {'sent ' + sent if sent else 'not configured'}\n")
    return 0 if sent else 1


if __name__ == "__main__":  # pragma: no cover - the alarm proof's command
    raise SystemExit(_main(sys.argv[1:]))
