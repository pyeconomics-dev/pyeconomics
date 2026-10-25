# tests/server/test_server_edge.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Edge trust (Phase 4 Step 7; ADR-0012 decision 20).

With ``PYECONOMICS_EDGE_CREDENTIAL`` set, a hosted server answers its API only
for a request whose ``X-Pyeconomics-Edge`` header matches, compared in constant
time; ``/healthz`` and ``/version`` stay open; a request without the header gets
403 with fixed text; and ``CF-Connecting-IP`` becomes the client address only
after a match, so a request sent straight to the origin cannot pick the address
its limits count. The credential is registered with redaction and reaches no
log, problem or header. Local mode never reads it.
"""

from __future__ import annotations

import hashlib
import secrets

import pytest
from leakcheck import LeakCheck
from server_support import LOOPBACK_ONLY, Plant, client, problem, service_of

from pyeconomics.data import ConfigError, redaction
from pyeconomics.server.edge import (
    CREDENTIAL_VARIABLE,
    EDGE_HEADER,
    MIN_CREDENTIAL_LENGTH,
    Edge,
    client_key,
)
from pyeconomics.server.limits import RateLimits

pytestmark = LOOPBACK_ONLY

MODELS = "/v1/models"


@pytest.fixture
def credential(monkeypatch: pytest.MonkeyPatch) -> str:
    """Configure a random edge credential for the test."""
    value = secrets.token_urlsafe(32)
    monkeypatch.setenv(CREDENTIAL_VARIABLE, value)
    return value


def test_without_the_header_the_api_is_403_and_the_probes_stay_open(
    credential: str,
) -> None:
    with client(mode="hosted") as api:
        refused = [
            api.get(path)
            for path in (MODELS, "/v1/sources", "/openapi.json", "/no/such/route")
        ]
        wrong = api.get(MODELS, headers={EDGE_HEADER: credential[:-1] + "x"})
        open_paths = [api.get("/healthz"), api.get("/version")]
        admitted = api.get(MODELS, headers={EDGE_HEADER: credential})
    for response in [*refused, wrong]:
        assert response.status_code == 403
        body = problem(response)
        assert body["type"].endswith("/edge-required")
        assert body["detail"] == (
            "this API answers only requests that come through its edge"
        )
        assert response.headers["cache-control"] == "no-store"
    assert [response.status_code for response in open_paths] == [200, 200]
    assert admitted.status_code == 200


def test_the_client_address_is_read_only_after_a_match(credential: str) -> None:
    limits = RateLimits(metadata="2/minute")
    with client(mode="hosted", rate_limits=limits) as api:

        def ask(address: str, *, through_edge: bool = True) -> int:
            headers = {"CF-Connecting-IP": address}
            if through_edge:
                headers[EDGE_HEADER] = credential
            return api.get(MODELS, headers=headers).status_code

        first = [ask("192.0.2.1"), ask("192.0.2.1"), ask("192.0.2.1")]
        other = [ask("192.0.2.2"), ask("192.0.2.2")]
        # A malformed address falls back to the connection's peer.
        peer = [ask("not-an-address"), ask("not-an-address"), ask("not-an-address")]
        direct = ask("192.0.2.3", through_edge=False)
    assert first == [200, 200, 429]
    assert other == [200, 200]
    assert peer == [200, 200, 429]
    assert direct == 403  # refused before any limit is counted


def test_without_a_credential_the_forwarded_address_is_ignored() -> None:
    limits = RateLimits(metadata="2/minute")
    with client(mode="hosted", rate_limits=limits) as api:
        answers = [
            api.get(MODELS, headers={"CF-Connecting-IP": f"192.0.2.{n}"}).status_code
            for n in range(1, 4)
        ]
    assert answers == [200, 200, 429]  # every request counted as the same peer


def test_local_mode_never_reads_the_credential(credential: str) -> None:
    with client() as api:
        assert api.get(MODELS).status_code == 200
        assert not service_of(api).edge.configured
    assert credential


@pytest.mark.parametrize(
    "value",
    [
        "short",
        "x" * (MIN_CREDENTIAL_LENGTH - 1),
        "with a space " + "x" * MIN_CREDENTIAL_LENGTH,
        "é" * MIN_CREDENTIAL_LENGTH,
    ],
    ids=["short", "one-short", "space", "non-ascii"],
)
def test_an_unusable_credential_stops_the_app_naming_the_variable_not_the_value(
    monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    from pyeconomics.server import ServerSettings, create_app  # noqa: PLC0415

    monkeypatch.setenv(CREDENTIAL_VARIABLE, value)
    with pytest.raises(ConfigError, match=CREDENTIAL_VARIABLE) as refused:
        create_app(mode="hosted", settings=ServerSettings(workers=0))
    assert value not in str(refused.value)


def test_the_credential_is_held_as_a_digest_and_registered_for_redaction(
    credential: str,
) -> None:
    edge = Edge(credential)
    assert repr(edge) == "Edge(configured=True)"
    assert credential not in repr(edge)
    assert edge._digest == hashlib.sha256(credential.encode()).digest()  # noqa: SLF001
    assert redaction.scrub_text(f"sent {credential}") == f"sent {redaction.MASK}"
    assert edge.matches(credential)
    assert not edge.matches(credential + "x")
    assert not edge.matches(credential[:-1])
    assert not edge.matches(None)
    assert not Edge(None).matches(credential)


def test_the_credential_reaches_no_log_problem_or_header(
    credential: str,
) -> None:
    check = LeakCheck(Plant(credential))
    logs = check.logs("pyeconomics.server", "pyeconomics.server.access")
    with logs, client(mode="hosted") as api:
        for headers in ({}, {EDGE_HEADER: "wrong"}, {EDGE_HEADER: credential}):
            for path in (MODELS, "/healthz", "/v1/models/no.such_model"):
                response = api.get(path, headers=headers)
                check.add(f"body:{path}", response.content)
                check.add(f"headers:{path}", repr(dict(response.headers)))
    check.assert_clean()


def test_client_keys_group_an_ipv6_subscriber_and_unmap_ipv4() -> None:
    assert client_key("2001:db8:aa:bb:1:2:3:4") == client_key("2001:db8:aa:bb::9")
    assert client_key("2001:db8:aa:bc::1") != client_key("2001:db8:aa:bb::1")
    assert client_key("::ffff:192.0.2.9") == "192.0.2.9"
    assert client_key("198.51.100.4") == "198.51.100.4"
    assert client_key("testclient") == "testclient"
