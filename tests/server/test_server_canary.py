# tests/server/test_server_canary.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No key, path, host or upstream URL reaches a problem or a server log line.

Phase 4 Step 6's security block. Every error the table maps is raised in a run
with a planted key, file paths in Windows, POSIX and home forms, and an upstream
URL and host in its message; the planted key is also sent in the query, in a
header and in a series target. Every response body and every log record the
server writes (problems, request lines, and anything else on the root,
``pyeconomics`` and ``urllib3`` loggers) is searched for each of them. A failing
assertion names the sinks, never the planted values (tests/data/leakcheck.py).
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from leakcheck import Canary, LeakCheck, canary
from server_support import ERRORS, LOOPBACK_ONLY, client, use_toys

from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    import pytest

pytestmark = LOOPBACK_ONLY


@dataclass(frozen=True)
class Plants:
    """A key, three file paths and an upstream URL, each with a random part."""

    key: Canary
    folder: str = field(default_factory=lambda: f"u{secrets.token_hex(6)}")
    host: str = field(default_factory=lambda: f"h{secrets.token_hex(6)}")

    @property
    def text(self) -> str:
        """A message holding every planted value."""
        return (
            f"reading C:\\Users\\{self.folder}\\pyeconomics.toml, "
            f"/home/{self.folder}/.config/pyeconomics.toml and "
            f"~/{self.folder}/.env through "
            f"https://api.{self.host}.example.org/v1/series?api_key={self.key.value} "
            f"(HTTPSConnectionPool(host='api.{self.host}.example.org', port=443)) "
            f"with {self.key.value}"
        )

    def needles(self) -> tuple[str, ...]:
        """The key's forms and the random parts of the paths and the host."""
        return (*self.key.needles(), self.folder, self.host)


def test_no_planted_value_reaches_a_response_or_a_log_line(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_toys(monkeypatch)
    # The test client logs its own request lines: they are not the server's.
    monkeypatch.setattr(logging.getLogger("httpx2"), "disabled", True)
    plants = Plants(key=canary())
    check = LeakCheck(plants)
    with check.logs("pyeconomics.server", "uvicorn"), client() as api:
        for name in ERRORS:
            inputs = {"error": name, "message": plants.text}
            response = api.post(
                "/v1/models/foundations.toy_fail/run", content=canonical_json(inputs)
            )
            check.add(f"body:{name}", response.content)
        key = plants.key.value
        requests = {
            "query": api.get("/v1/models", params={"api_key": key}),
            "header": api.get("/healthz", headers={"Authorization": f"Bearer {key}"}),
            "target": api.get(f"/v1/series/{key}"),
            "provider": api.get(f"/v1/series/nowhere:{key}"),
            "inputs": api.post(
                "/v1/models/foundations.toy_time_value/run",
                content=canonical_json({"calculation": key, "rate": plants.text}),
            ),
        }
        for sink, response in requests.items():
            check.add(f"body:{sink}", response.content)
            check.add(f"headers:{sink}", repr(dict(response.headers)))
    assert any(sink.startswith("log:pyeconomics.server") for sink in check.sinks)
    assert len([s for s in check.sinks if s.startswith("body:")]) == len(ERRORS) + 5
    check.assert_clean()


def test_the_harness_sees_each_planted_value() -> None:
    plants = Plants(key=canary())
    for needle in plants.needles():
        probe = LeakCheck(plants)
        probe.add("probe", f"around {needle} here")
        assert probe.leaks() == ["probe"]
