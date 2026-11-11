# tests/server/telemetry_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""In-memory errors, metrics and spans for the hosted telemetry's tests (Step 14).

:func:`capturing` turns the telemetry on for one test with Sentry's events kept
by :class:`Captured`, metrics by an in-memory reader and spans by an in-memory
exporter: nothing reaches a vendor. ``tests/server/test_server_telemetry.py``
and ``tests/surfaces/test_problem_canary.py`` search what they keep.
"""

from __future__ import annotations

import functools
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from sentry_sdk.transport import Transport

from pyeconomics.server import observability
from pyeconomics.server.settings import DEPLOYMENT_VARIABLE, SENTRY_DSN_VARIABLE

if TYPE_CHECKING:
    import pytest

__all__ = ["Captured", "World", "capturing", "fake_dsn"]


class Captured(Transport):
    """A Sentry transport that keeps every envelope item's JSON in memory."""

    items: ClassVar[list[dict[str, Any]]] = []

    def capture_envelope(self, envelope: Any) -> None:  # noqa: ANN401 - Sentry's type
        """Keep each item's payload."""
        for item in envelope.items:
            self.items.append(item.get_event() or item.payload.json or {})

    def flush(self, timeout: float, callback: object = None) -> None:
        """Nothing is queued."""

    def kill(self) -> None:
        """Nothing runs."""


def fake_dsn() -> str:
    """A DSN on Sentry's US ingest, built at run time; it reaches no network."""
    return (
        f"https://{secrets.token_hex(16)}@o{secrets.randbelow(10**6)}"
        f".ingest.us.sentry.io/{secrets.randbelow(10**6)}"
    )


@dataclass
class World:
    """Where a test's errors, metrics and spans land."""

    reader: InMemoryMetricReader = field(default_factory=InMemoryMetricReader)
    spans: InMemorySpanExporter = field(default_factory=InMemorySpanExporter)

    @property
    def events(self) -> list[dict[str, Any]]:
        """Every Sentry event kept so far."""
        return Captured.items

    def metric_points(self) -> list[tuple[str, dict[str, Any]]]:
        """The resource's attributes, then each data point's, by metric name."""
        points: list[tuple[str, dict[str, Any]]] = []
        data = self.reader.get_metrics_data()
        for resource in data.resource_metrics if data else ():
            points.append(("resource", dict(resource.resource.attributes or {})))
            for scope in resource.scope_metrics:
                for metric in scope.metrics:
                    points.extend(
                        (metric.name, dict(point.attributes or {}))
                        for point in metric.data.data_points
                    )
        return points


def capturing(monkeypatch: pytest.MonkeyPatch) -> World:
    """Turn the hosted telemetry on for one test, every exporter in memory."""
    Captured.items = []
    found = World()
    monkeypatch.setenv(SENTRY_DSN_VARIABLE, fake_dsn())
    monkeypatch.setenv(DEPLOYMENT_VARIABLE, "test")
    monkeypatch.setattr(
        observability,
        "start",
        functools.partial(
            observability.start,
            sentry_transport=Captured,
            metric_reader=found.reader,
            span_exporter=found.spans,
        ),
    )
    return found
