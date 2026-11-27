# scripts/load/locustfile.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The launch load test (Phase 5 Step 20; ADR-0013 decision 19).

Locust against staging through the edge, never against an upstream source:
hosted mode reads every series from the snapshot. Requests are weighted by cost
class, as the calculators send them (a POST run of a model's first example), with
series reads beside them, and each is named by its class, so Locust's statistics
give p50 and p95 per class. The rate and the duration are fixed here, before the
run, inside the budget the readiness gate set (about ten minutes and 3,000
requests at most):

- nine minutes steady at 1 request a second (48 runs and 12 series a minute),
  under the hosted limits of one client address (60 runs and 30 series a minute)
  and the zone's rate rule (50 requests in 10 seconds);
- one minute at 3 requests a second, past the run limit on purpose, to show the
  limits answer 429 and nothing answers 5xx.

A 429 is recorded under its class's name with " (429)" added, so each class's
percentiles are of the answers the API computed.

Behind Cloudflare Access the service token comes from CF_ACCESS_CLIENT_ID and
CF_ACCESS_CLIENT_SECRET, sent as headers only, never printed.

    uv run --group load locust -f scripts/load/locustfile.py --headless \
        --host https://staging.pyeconomics.dev --csv <prefix> --only-summary
"""

from __future__ import annotations

import json
import os
import random
from typing import Any, ClassVar

from locust import HttpUser, LoadTestShape, constant_throughput, task

from pyeconomics import registry

#: Models of each cost class, all data-free (their first example needs no data).
MODELS: dict[str, tuple[str, ...]] = {
    "instant": (
        "derivatives.black_scholes_merton",
        "derivatives.forwards",
        "corporate.cost_of_capital",
    ),
    "light": (
        "foundations.time_value",
        "fixed_income.bond_pricing",
        "econometrics.ols",
    ),
    "heavy": ("econometrics.garch", "foundations.simulation", "risk.value_at_risk"),
}
#: Concepts the snapshot serves, read as the explorer reads them.
SERIES: tuple[str, ...] = (
    "us.unemployment.rate",
    "us.policy_rate.effective",
    "us.prices.cpi",
)
#: Each user's requests a second; the shape sets how many users run.
PER_USER = 0.5
STEADY_SECONDS = 540
BURST_SECONDS = 60
STEADY_USERS = 2
BURST_USERS = 6


def _headers() -> dict[str, str]:
    """Return the Access headers when the environment holds the token, else none."""
    ident = os.environ.get("CF_ACCESS_CLIENT_ID", "")
    secret = os.environ.get("CF_ACCESS_CLIENT_SECRET", "")
    if not (ident and secret):
        return {}
    return {"CF-Access-Client-Id": ident, "CF-Access-Client-Secret": secret}


def _bodies() -> dict[str, bytes]:
    """Return each model's first example as the JSON body a calculator posts."""
    bodies = {}
    for ids in MODELS.values():
        for model_id in ids:
            inputs: dict[str, Any] = dict(
                registry.get(model_id).spec.examples[0].inputs
            )
            bodies[model_id] = json.dumps(inputs).encode("utf-8")
    return bodies


class Visitor(HttpUser):
    """A visitor whose calculator runs and series reads arrive at a fixed rate."""

    wait_time = constant_throughput(PER_USER)
    bodies: ClassVar[dict[str, bytes]] = _bodies()

    def on_start(self) -> None:
        """Send the Access headers and a plain user agent with every request."""
        self.client.headers.update(
            {**_headers(), "User-Agent": "pyeconomics-load-test"}
        )

    def _run(self, cost: str) -> None:
        model_id = random.choice(MODELS[cost])  # noqa: S311 # nosec B311 - load mix, not security
        with self.client.post(
            f"/v1/models/{model_id}/run",
            data=self.bodies[model_id],
            headers={"Content-Type": "application/json"},
            name=f"run {cost}",
            catch_response=True,
        ) as response:
            if response.status_code == 429:  # noqa: PLR2004 - the limit's answer
                response.request_meta["name"] = f"run {cost} (429)"
                response.failure("429")

    @task(14)
    def instant(self) -> None:
        """Run an instant model."""
        self._run("instant")

    @task(4)
    def light(self) -> None:
        """Run a light model."""
        self._run("light")

    @task(2)
    def heavy(self) -> None:
        """Run a heavy model."""
        self._run("heavy")

    @task(5)
    def series(self) -> None:
        """Read a series the snapshot serves, ten years of it."""
        concept = random.choice(SERIES)  # noqa: S311 # nosec B311 - load mix, not security
        with self.client.get(
            f"/v1/series/{concept}?start=2016-01-01", name="series", catch_response=True
        ) as response:
            if response.status_code == 429:  # noqa: PLR2004 - the limit's answer
                response.request_meta["name"] = "series (429)"
                response.failure("429")


class SteadyThenBurst(LoadTestShape):
    """Nine minutes steady, then one minute past the run limit, then stop."""

    def tick(self) -> tuple[int, float] | None:
        """Return the users and spawn rate for the time the run has taken."""
        elapsed = self.get_run_time()
        if elapsed < STEADY_SECONDS:
            return STEADY_USERS, STEADY_USERS
        if elapsed < STEADY_SECONDS + BURST_SECONDS:
            return BURST_USERS, BURST_USERS
        return None
