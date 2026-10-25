# tests/server/test_server_ssrf.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""No route fetches what a caller names (Phase 4 Step 7; threat 3, SSRF).

The test enumerates every operation and every parameter in ``openapi.json`` and
sends each URL-shaped value (the cloud metadata address, loopback addresses in
both families, a file URL and an outside host) to each parameter in turn, and to
each concept parameter a run can bind (``param=NAME=VALUE``, the one text that
reaches a provider's series key), with
the other parameters left out (a key-less source may answer 503; nothing answers
500). Every data request the server makes goes through
the real HTTPS transport into a recording pool, which answers 404: each URL it
recorded must name a host on some provider's allowlist, and none may name an
address or a host a caller sent. Both modes are driven; hosted mode serves only
hosted-safe sources, local mode every source.
"""

from __future__ import annotations

import ipaddress
from typing import TYPE_CHECKING, Any
from urllib.parse import quote, urlsplit

import pytest
from server_support import LOOPBACK_ONLY, client, openapi_of, use_recording_transport

from pyeconomics.data import catalog
from pyeconomics.data import registry as provider_registry
from pyeconomics.server.limits import RateLimits

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pyeconomics.server.settings import ServerMode

pytestmark = LOOPBACK_ONLY

#: URL-shaped values: link-local metadata, loopback v4 and v6, a file, outside.
URLS = (
    "http://169.254.169.254/latest/meta-data/",
    "http://127.0.0.1:8000/v1/models",
    "http://[::1]/",
    "file:///etc/passwd",
    "https://attacker.example.net/x?y=1",
)
#: A valid value for each path parameter, used while another parameter is probed.
PATH_DEFAULTS = {"target": "us.unemployment.rate"}
CALLER_HOSTS = frozenset(
    {"169.254.169.254", "127.0.0.1", "::1", "attacker.example.net", "localhost"}
)


def _operations(
    document: dict[str, Any],
) -> list[tuple[str, str, list[dict[str, Any]]]]:
    found = []
    for path, item in document["paths"].items():
        for method, operation in item.items():
            found.append((path, method.upper(), operation.get("parameters", [])))
    return found


def _concept_parameters(path: str) -> list[dict[str, Any]]:
    """A run's concept parameters (``param=NAME=VALUE``) as probes of their own.

    A concept parameter fills a placeholder in a series key, the one place a
    caller's text reaches a provider's request; each is probed by name.
    """
    if not path.endswith("/run"):
        return []
    names = sorted(
        {p.name for concept in catalog.concepts() for p in concept.parameters}
    )
    return [{"in": "param", "name": name} for name in names]


def _send(
    api: TestClient,
    path: str,
    method: str,
    parameter: dict[str, Any],
    value: str,
) -> int:
    where = parameter["in"]
    name = parameter["name"]
    filled = path
    for key, default in PATH_DEFAULTS.items():
        if where == "path" and key == name:
            continue
        filled = filled.replace(f"{{{key}}}", default)
    if where == "path":
        filled = filled.replace(f"{{{name}}}", quote(value, safe=""))
        response = api.request(method, filled)
    elif where == "query":
        response = api.request(method, filled, params={name: value})
    elif where == "param":
        response = api.request(method, filled, params={"param": f"{name}={value}"})
    else:
        response = api.request(method, filled, headers={name: value})
    return response.status_code


@pytest.mark.parametrize("mode", ["local", "hosted"])
def test_no_parameter_sends_a_request_to_a_host_a_caller_names(
    mode: ServerMode, monkeypatch: pytest.MonkeyPatch
) -> None:
    pool = use_recording_transport(monkeypatch)
    allowed = {
        host for info in provider_registry.installed().infos() for host in info.hosts
    }
    probes = 0
    statuses: set[int] = set()
    # Limits off: a probe must reach its route, not stop at the limiter.
    with client(mode=mode, rate_limits=RateLimits.off()) as api:
        for path, method, parameters in _operations(openapi_of(api)):
            for parameter in [*parameters, *_concept_parameters(path)]:
                for value in URLS:
                    statuses.add(_send(api, path, method, parameter, value))
                    probes += 1
        # The recorder is the transport in use: a real series reaches it.
        before = len(pool.urls)
        api.get("/v1/series/us.unemployment.rate")
        assert len(pool.urls) > before
    assert probes > 1_000  # every run operation of every model, both forms
    # A source without a key may answer 503; nothing may fail unexpectedly.
    assert 500 not in statuses, statuses
    assert 429 not in statuses
    hosts = {urlsplit(url).hostname or "" for url in pool.urls}
    assert hosts <= allowed, sorted(hosts - allowed)
    assert not hosts & CALLER_HOSTS
    for host in hosts:
        try:
            ipaddress.ip_address(host)
        except ValueError:
            continue
        pytest.fail(f"a request named the address {host}")
    for url in pool.urls:
        assert urlsplit(url).scheme == "https"


def test_a_url_as_a_series_target_is_refused_before_any_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pool = use_recording_transport(monkeypatch)
    with client() as api:
        for value in URLS:
            response = api.get(f"/v1/series/{quote(value, safe='')}")
            assert response.status_code == 422
            assert response.json()["type"].endswith("/invalid-input")
    assert pool.urls == []
