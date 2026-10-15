# tests/providers/test_canary_transport.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A request with a canary key leaves no trace in any sink (ADR-0011 decision 13).

The transport is the one place a key is revealed, so it is the sink most worth
proving. A random canary key goes through every placement (query, header, body),
every failure and a replay; the logs of every logger (urllib3's own lines
included), the warnings, the exceptions with their tracebacks, the returned
series, a cassette recorded from the exchange and the transport's own ``repr`` are
searched for it. A failing assertion names the sinks, never the key.
"""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

import pytest
import urllib3
from fakes import FIXED_NOW, FakeClock, FakePool, FakeRaw
from leakcheck import LeakCheck, canary, log_urllib3_request
from stubs import HOST, stub_info
from toys import JSON_HOST, ToyJson

from pyeconomics.data import (
    Authentication,
    CredentialError,
    KeyPlacement,
    Query,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
    TransportError,
)
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.http import HttpTransport

SERIES = json.dumps(
    {
        "title": "Toy policy rate",
        "units": "Percent",
        "frequency": "monthly",
        "seasonal_adjustment": "NSA",
        "observations": [{"date": "2025-01-01", "value": "4.50"}],
    }
).encode()


class LoggingPool(FakePool):
    """A pool that writes the lines urllib3 would, with the URL it was given."""

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        log_urllib3_request(url[len("https://") + len(JSON_HOST) :], host=JSON_HOST)
        return super().request(method, url, **kwargs)


def transport(pool: FakePool) -> HttpTransport:
    clock = FakeClock()
    return HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
    )


def fetch(provider: ToyJson, wire: HttpTransport, key: str) -> Any:
    return provider.fetch(Query(series=("TOYRATE",)), key=key, transport=wire)


def ok() -> FakeRaw:
    return FakeRaw(200, SERIES, {"Content-Type": "application/json"})


def test_a_key_in_the_query_string_reaches_no_sink() -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    pool = LoggingPool(ok(), ok())
    wire = transport(pool)
    series = check.run(lambda: fetch(ToyJson(), wire, held.value))
    assert series is not None
    # The wire request did carry the key (that is the transport's job) ...
    assert held.value in pool.calls[0].url
    # ... and nothing else did, including a cassette recorded from the exchange.
    request = Request(
        host=JSON_HOST, path="/v1/observations", params=(("series_id", "TOYRATE"),)
    )
    reply = wire.send(ToyJson.info, request, key=held.value)
    cassette = Cassette.from_exchanges(
        "toy_json", FIXED_NOW, [(request, reply)], synthetic=False
    )
    check.add("cassette", cassette.document())
    check.add("transport", repr(wire) + repr(ToyJson.info) + repr(ToyJson()))
    check.assert_clean()
    assert len(check.sinks) >= 4


def test_a_key_in_a_header_reaches_no_sink() -> None:
    held = canary("toy_json")
    info = replace(
        ToyJson.info,
        auth=Authentication.key("Authorization", KeyPlacement.HEADER, scheme="Bearer"),
    )
    provider = type("Header", (ToyJson,), {"info": info})()
    pool = LoggingPool(ok())
    check = LeakCheck(held)
    assert check.run(lambda: fetch(provider, transport(pool), held.value)) is not None
    assert held.value in pool.calls[0].headers["Authorization"]
    assert held.value not in pool.calls[0].url
    check.assert_clean()


def test_a_key_in_a_body_reaches_no_sink() -> None:
    held = canary("toy_json")
    info = replace(
        ToyJson.info, auth=Authentication.key("registrationkey", KeyPlacement.BODY)
    )
    wire = transport(LoggingPool(ok()))
    request = Request(
        host=JSON_HOST, path="/v2/timeseries", method="POST", body={"seriesid": ["A"]}
    )
    check = LeakCheck(held)
    response = check.run(lambda: wire.send(info, request, key=held.value))
    assert response is not None
    check.add("response", repr(response) + repr(response.headers))
    cassette = Cassette.from_exchanges(
        "toy_json", FIXED_NOW, [(request, response)], synthetic=False
    )
    check.add("cassette", cassette.document())
    check.assert_clean()


@pytest.mark.parametrize(
    "failure",
    [
        lambda key: OSError(
            f"GET https://{JSON_HOST}/v1/observations?api_key={key}&x=1 reset"
        ),
        lambda key: urllib3.exceptions.ProtocolError(f"aborted (api_key={key})"),
        lambda key: ValueError(f"bad url /v1/observations?api_key={key}"),
    ],
    ids=["oserror", "protocol-error", "value-error"],
)
def test_a_connection_failure_reaches_no_sink(failure: Any) -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    pool = LoggingPool(*[failure(held.value)] * 5)
    check.run(lambda: fetch(ToyJson(), transport(pool), held.value))
    error_sinks = [name for name in check.sinks if name.startswith("exception:")]
    assert error_sinks, "the failure was not collected"
    check.assert_clean()


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (401, CredentialError),
        (403, CredentialError),
        (404, SeriesNotFoundError),
        (429, RateLimitError),
        (503, TransportError),
        (400, ResponseError),
    ],
)
def test_a_failure_status_reaches_no_sink(status: int, error: type[Exception]) -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    body = f'{{"error_message":"bad key {held.value}"}}'.encode()
    pool = LoggingPool(*[FakeRaw(status, body)] * 5)
    check.run(lambda: fetch(ToyJson(), transport(pool), held.value))
    assert any(name == f"exception:{error.__name__}" for name in check.sinks)
    check.assert_clean()


def test_a_response_that_echoes_the_key_is_scrubbed_from_the_cassette() -> None:
    held = canary("toy_json")
    echoing = json.dumps(
        {"echo": held.value, "next": f"/v1/x?api_key={held.value}"}
    ).encode()
    wire = transport(
        LoggingPool(FakeRaw(200, echoing, {"Content-Type": "application/json"}))
    )
    request = Request(
        host=JSON_HOST, path="/v1/observations", params=(("series_id", "TOYRATE"),)
    )
    response = wire.send(ToyJson.info, request, key=held.value)
    cassette = Cassette.from_exchanges(
        "toy_json", FIXED_NOW, [(request, response)], synthetic=False
    )
    check = LeakCheck(held)
    check.add("cassette", cassette.document())
    check.assert_clean()


def test_a_missing_key_error_names_the_variable_not_a_value() -> None:
    held = canary("toy_json")
    check = LeakCheck(held)
    check.run(lambda: fetch(ToyJson(), transport(FakePool()), ""))
    check.assert_clean()


def test_a_contact_canary_reaches_no_sink(monkeypatch: pytest.MonkeyPatch) -> None:
    from leakcheck import contact_canary  # noqa: PLC0415

    from pyeconomics.data import config  # noqa: PLC0415

    contact = contact_canary()
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", contact.value)
    config.reset()
    info = stub_info(id="needs_contact", auth=Authentication.contact())
    wire = transport(
        FakePool(OSError(f"cannot reach {contact.value}"), *[OSError("x")] * 4)
    )
    check = LeakCheck(contact)
    check.run(lambda: wire.send(info, Request(host=HOST, path="/v1/x")))
    check.assert_clean()
