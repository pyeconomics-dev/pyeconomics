# tests/providers/test_http_transport.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``HttpTransport``: hosts, HTTPS, keys, redirects, retries, caps and scrubbed errors.

Every test drives it through ``FakePool`` (or urllib3's real response objects built
from bytes) and a fake clock: nothing here opens a socket.
"""

from __future__ import annotations

import gzip
import io
import json
import secrets
import ssl
from dataclasses import replace
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qsl, urlsplit

import pytest
import urllib3
from fakes import BANNED, FIXED_NOW, FakeClock, FakePool, FakeRaw
from stubs import HOST, Stub, stub_info
from toys import ToyJson

import pyeconomics
from pyeconomics.data import (
    Authentication,
    CredentialError,
    KeyPlacement,
    LicenceClass,
    LicenceError,
    RateLimit,
    RateLimitError,
    ResponseError,
    Series,
    TransportError,
    config,
    configure,
)
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.http import MAX_ATTEMPTS, HttpTransport, user_agent

if TYPE_CHECKING:
    from pyeconomics.data import ProviderInfo

KEYED = ToyJson.info  # api_key in the query string, hosted-safe, two rate limits
REQUEST = Request(
    host=KEYED.hosts[0], path="/v1/observations", params=(("series_id", "TOYRATE"),)
)
KEY = secrets.token_hex(16)


def make(
    *script: Any,
    **options: Any,
) -> tuple[HttpTransport, FakePool, FakeClock]:
    clock, pool = FakeClock(), FakePool(*script)
    options.setdefault("jitter", lambda ceiling: ceiling)
    transport = HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        **options,
    )
    return transport, pool, clock


def ok(body: bytes = b"{}", **headers: str) -> FakeRaw:
    return FakeRaw(200, body, headers)


def query(call_url: str) -> dict[str, str]:
    return dict(parse_qsl(urlsplit(call_url).query))


# --- the request that leaves the process --------------------------------------


def test_the_url_is_https_on_the_declared_host_with_the_key_in_the_query() -> None:
    transport, pool, _ = make(ok())
    response = transport.send(KEYED, REQUEST, key=KEY)
    (call,) = pool.calls
    parts = urlsplit(call.url)
    assert (parts.scheme, parts.netloc, parts.path) == (
        "https",
        KEYED.hosts[0],
        "/v1/observations",
    )
    assert query(call.url) == {"series_id": "TOYRATE", "api_key": KEY}
    assert call.method == "GET"
    assert call.body is None
    assert response.status == 200
    assert response.retrieved_at == FIXED_NOW


def test_the_key_comes_from_the_chain_when_none_is_passed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("TOY_JSON_API_KEY", KEY)
    transport, pool, _ = make(ok())
    transport.send(KEYED, REQUEST)
    assert query(pool.calls[0].url)["api_key"] == KEY


def test_a_missing_key_is_a_credential_error_naming_the_variable() -> None:
    transport, pool, _ = make(BANNED)
    with pytest.raises(CredentialError, match="TOY_JSON_API_KEY"):
        transport.send(KEYED, REQUEST)
    assert pool.calls == []


def test_parameters_are_percent_encoded() -> None:
    request = replace(REQUEST, params=(("q", "a b&c=d/é"),))
    transport, pool, _ = make(ok())
    transport.send(KEYED, request, key=KEY)
    assert "q=a%20b%26c%3Dd%2F%C3%A9" in pool.calls[0].url


def test_the_headers_name_pyeconomics_and_ask_for_gzip() -> None:
    transport, pool, _ = make(ok())
    transport.send(
        KEYED, replace(REQUEST, headers=(("Accept", "application/json"),)), key=KEY
    )
    headers = pool.calls[0].headers
    assert headers["User-Agent"] == (
        f"pyeconomics/{pyeconomics.__version__} "
        "(+https://github.com/pyeconomics-dev/pyeconomics)"
    )
    assert headers["Accept-Encoding"] == "gzip"
    assert headers["Accept"] == "application/json"
    assert "Authorization" not in headers


def test_the_user_agent_can_carry_a_contact() -> None:
    assert user_agent().endswith("pyeconomics)")
    assert user_agent("Name name@example.org").endswith(
        "pyeconomics) Name name@example.org"
    )


def test_the_pool_is_called_without_redirects_retries_or_preloading() -> None:
    seen: dict[str, Any] = {}

    def capture(call: Any) -> FakeRaw:
        return ok()

    class Spy(FakePool):
        def request(self, method: str, url: str, **kwargs: Any) -> Any:
            seen.update(kwargs)
            return super().request(method, url, **kwargs)

    clock = FakeClock()
    transport = HttpTransport(
        pool=Spy(capture), clock=clock.monotonic, sleep=clock.sleep
    )
    transport.send(KEYED, REQUEST, key=KEY)
    assert (seen["redirect"], seen["retries"], seen["preload_content"]) == (
        False,
        False,
        False,
    )
    timeout = seen["timeout"]
    assert (timeout.connect_timeout, timeout.read_timeout) == (10.0, 30.0)


# --- keys and contacts --------------------------------------------------------


def test_a_key_in_a_header_carries_its_scheme() -> None:
    info = replace(
        KEYED,
        auth=Authentication.key("Authorization", KeyPlacement.HEADER, scheme="Bearer"),
    )
    transport, pool, _ = make(ok())
    transport.send(info, REQUEST, key=KEY)
    assert pool.calls[0].headers["Authorization"] == f"Bearer {KEY}"
    assert "api_key" not in pool.calls[0].url


def test_a_key_in_a_header_without_a_scheme_is_sent_bare() -> None:
    info = replace(KEYED, auth=Authentication.key("X-Api-Key", KeyPlacement.HEADER))
    transport, pool, _ = make(ok())
    transport.send(info, REQUEST, key=KEY)
    assert pool.calls[0].headers["X-Api-Key"] == KEY


def test_a_key_in_a_body_is_added_to_the_json_object() -> None:
    info = replace(KEYED, auth=Authentication.key("registrationkey", KeyPlacement.BODY))
    request = Request(
        host=info.hosts[0],
        path="/v2/timeseries",
        method="POST",
        body={"seriesid": ["A"]},
    )
    transport, pool, _ = make(ok())
    transport.send(info, request, key=KEY)
    call = pool.calls[0]
    assert call.method == "POST"
    assert json.loads(call.body or b"") == {"seriesid": ["A"], "registrationkey": KEY}
    assert call.headers["Content-Type"] == "application/json"
    assert KEY not in call.url


def test_a_body_key_with_no_body_makes_a_body_of_just_the_key() -> None:
    info = replace(KEYED, auth=Authentication.key("registrationkey", KeyPlacement.BODY))
    request = Request(host=info.hosts[0], path="/v2/timeseries", method="POST")
    transport, pool, _ = make(ok())
    transport.send(info, request, key=KEY)
    assert json.loads(pool.calls[0].body or b"") == {"registrationkey": KEY}


def test_a_body_key_cannot_go_into_a_list_body() -> None:
    info = replace(KEYED, auth=Authentication.key("registrationkey", KeyPlacement.BODY))
    request = Request(
        host=info.hosts[0], path="/v1/map", method="POST", body=[{"id": 1}]
    )
    transport, pool, _ = make(BANNED)
    with pytest.raises(CredentialError, match="body"):
        transport.send(info, request, key=KEY)
    assert pool.calls == []


def test_a_post_body_is_sent_as_compact_json() -> None:
    request = Request(
        host=HOST, path="/v1/x", method="POST", body={"b": [1, 2], "a": "é"}
    )
    transport, pool, _ = make(ok())
    transport.send(stub_info(), request)
    assert pool.calls[0].body == b'{"a":"\\u00e9","b":[1,2]}'


def test_an_optional_key_is_sent_only_when_the_chain_has_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = replace(
        KEYED,
        id="optional",
        auth=Authentication.key("api_key", KeyPlacement.QUERY, required=False),
    )
    transport, pool, _ = make(ok(), ok())
    transport.send(info, REQUEST)
    assert "api_key" not in pool.calls[0].url
    monkeypatch.setenv("OPTIONAL_API_KEY", KEY)
    transport.send(info, REQUEST)
    assert query(pool.calls[1].url)["api_key"] == KEY


def test_a_contact_goes_in_the_user_agent_and_a_missing_one_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    info = stub_info(id="needs_contact", auth=Authentication.contact())
    transport, pool, _ = make(BANNED, ok())
    with pytest.raises(CredentialError, match="PYECONOMICS_SEC_CONTACT") as caught:
        transport.send(info, Request(host=HOST, path="/v1/x"))
    assert caught.value.provider == "needs_contact"
    assert len(pool.calls) == 0
    contact = f"Pat Example pat{secrets.token_hex(3)}@example.org"
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", contact)
    config.reset()  # the settings are read once per process
    pool.script.clear()
    pool.script.append(ok())
    transport.send(info, Request(host=HOST, path="/v1/x"))
    assert pool.calls[0].headers["User-Agent"].endswith(contact)


# --- hosts and redirects ------------------------------------------------------


def test_a_foreign_host_is_refused_before_anything_is_built() -> None:
    transport, pool, _ = make(BANNED)
    with pytest.raises(TransportError, match="not a declared host"):
        transport.send(
            KEYED, Request(host="foreign.example.net", path="/v1/x"), key=KEY
        )
    assert pool.calls == []


def test_hosted_mode_refuses_a_library_only_source_before_any_request() -> None:
    info = replace(KEYED, terms=replace(KEYED.terms, licence=LicenceClass.LIBRARY_ONLY))
    configure(mode="hosted")
    transport, pool, _ = make(BANNED)
    with pytest.raises(LicenceError, match="library-only"):
        transport.send(info, REQUEST, key=KEY)
    assert pool.calls == []


def test_a_redirect_on_the_allowlist_is_followed() -> None:
    target = f"https://{KEYED.hosts[0]}/v1/moved"
    transport, pool, _ = make(
        FakeRaw(302, headers={"Location": target}), ok(b'"moved"')
    )
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert [urlsplit(c.url).path for c in pool.calls] == [
        "/v1/observations",
        "/v1/moved",
    ]
    assert response.body == b'"moved"'


def test_a_relative_redirect_resolves_against_the_current_url() -> None:
    transport, pool, _ = make(FakeRaw(301, headers={"Location": "/v1/elsewhere"}), ok())
    transport.send(KEYED, REQUEST, key=KEY)
    assert pool.calls[1].url == f"https://{KEYED.hosts[0]}/v1/elsewhere"


@pytest.mark.parametrize(
    "target",
    [
        "http://api.toyjson.example.org/v1/x",
        "https://foreign.example.net/v1/x",
        "https://api.toyjson.example.org:8443/v1/x",
        "https://someone@api.toyjson.example.org/v1/x",
        "ftp://api.toyjson.example.org/v1/x",
        "//foreign.example.net/v1/x",
    ],
)
def test_a_redirect_off_https_or_off_the_allowlist_is_refused(target: str) -> None:
    transport, pool, _ = make(FakeRaw(302, headers={"Location": target}), BANNED)
    with pytest.raises(TransportError):
        transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 1


def test_a_redirect_to_port_443_is_the_same_as_none() -> None:
    target = f"https://{KEYED.hosts[0]}:443/v1/x"
    transport, pool, _ = make(FakeRaw(302, headers={"Location": target}), ok())
    transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 2


def test_a_redirect_message_names_the_host_but_never_the_query() -> None:
    target = "https://foreign.example.net/v1/x?token=" + secrets.token_hex(8)
    transport, _, _ = make(FakeRaw(302, headers={"Location": target}))
    with pytest.raises(TransportError) as caught:
        transport.send(KEYED, REQUEST, key=KEY)
    assert str(caught.value) == (
        "toy_json was redirected to foreign.example.net, which is not a declared host"
    )


def test_too_many_redirects_are_refused() -> None:
    loop = FakeRaw(302, headers={"Location": f"https://{KEYED.hosts[0]}/v1/loop"})
    transport, pool, _ = make(*[loop] * 4, max_redirects=3)
    with pytest.raises(TransportError, match="more than 3 times"):
        transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 4


def test_a_redirect_without_a_location_is_a_final_response() -> None:
    transport, _, _ = make(FakeRaw(302))
    assert transport.send(KEYED, REQUEST, key=KEY).status == 302


def test_301_302_and_303_turn_a_post_into_a_get_and_307_and_308_keep_it() -> None:
    request = Request(host=HOST, path="/v1/x", method="POST", body={"a": 1})
    for status, method in (
        (301, "GET"),
        (302, "GET"),
        (303, "GET"),
        (307, "POST"),
        (308, "POST"),
    ):
        target = FakeRaw(status, headers={"Location": f"https://{HOST}/v1/y"})
        transport, pool, _ = make(target, ok())
        transport.send(stub_info(), request)
        second = pool.calls[1]
        assert second.method == method, status
        assert (second.body is None) == (method == "GET"), status
        assert ("Content-Type" in second.headers) == (method == "POST"), status


# --- retries and backoff ------------------------------------------------------


def test_a_server_error_is_retried_with_exponential_backoff() -> None:
    transport, pool, clock = make(FakeRaw(503), FakeRaw(500), FakeRaw(502), ok(b"done"))
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert response.body == b"done"
    assert len(pool.calls) == 4
    assert clock.slept == [0.5, 1.0, 2.0]  # the ceilings; jitter returns each whole


def test_backoff_is_full_jitter_up_to_the_ceiling() -> None:
    transport, _, clock = make(
        FakeRaw(503), FakeRaw(503), ok(), jitter=lambda ceiling: ceiling / 4
    )
    transport.send(KEYED, REQUEST, key=KEY)
    assert clock.slept == [0.125, 0.25]


def test_backoff_stops_doubling_at_its_cap() -> None:
    transport, _, clock = make(*[FakeRaw(503)] * 5, backoff_cap=1.5)
    transport.send(KEYED, REQUEST, key=KEY)
    assert clock.slept == [0.5, 1.0, 1.5, 1.5]


def test_the_last_attempts_response_is_returned_not_raised() -> None:
    transport, pool, _ = make(*[FakeRaw(503, b"down")] * 5)
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert (response.status, response.body) == (503, b"down")
    assert len(pool.calls) == MAX_ATTEMPTS == 5


def test_attempts_never_exceed_five_whatever_is_asked() -> None:
    transport, pool, _ = make(*[FakeRaw(503)] * 9, max_attempts=50)
    transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 5
    one, pool_one, _ = make(FakeRaw(503), max_attempts=0)
    assert one.send(KEYED, REQUEST, key=KEY).status == 503
    assert len(pool_one.calls) == 1


def test_a_429_is_retried_and_honours_retry_after() -> None:
    transport, _, clock = make(FakeRaw(429, headers={"Retry-After": "10"}), ok())
    transport.send(KEYED, REQUEST, key=KEY)
    assert clock.slept == [10.0]


def test_a_retry_after_date_is_measured_from_the_response_time() -> None:
    when = "Thu, 15 Oct 2026 15:00:20 GMT"  # FIXED_NOW is 15:00:00
    transport, _, clock = make(FakeRaw(503, headers={"Retry-After": when}), ok())
    transport.send(KEYED, REQUEST, key=KEY)
    assert clock.slept == [20.0]


def test_a_retry_after_longer_than_the_cap_ends_the_retries() -> None:
    transport, pool, clock = make(FakeRaw(429, headers={"Retry-After": "600"}), BANNED)
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert response.status == 429
    assert response.header("retry-after") == "600"
    assert len(pool.calls) == 1
    assert clock.slept == []


def test_a_retry_after_shorter_than_the_backoff_does_not_shorten_it() -> None:
    transport, _, clock = make(
        FakeRaw(429, headers={"Retry-After": "0"}),
        FakeRaw(429, headers={"Retry-After": "0"}),
        ok(),
    )
    transport.send(KEYED, REQUEST, key=KEY)
    assert clock.slept == [0.5, 1.0]


def test_a_client_error_is_returned_without_a_retry() -> None:
    transport, pool, _ = make(FakeRaw(404, b"missing"))
    assert transport.send(KEYED, REQUEST, key=KEY).status == 404
    assert len(pool.calls) == 1


@pytest.mark.parametrize(
    "failure",
    [
        ConnectionResetError("reset"),
        TimeoutError("timed out"),
        urllib3.exceptions.ProtocolError("aborted"),
        urllib3.exceptions.HTTPError("generic"),
    ],
)
def test_a_connection_failure_is_retried_then_raised_without_context(
    failure: BaseException,
) -> None:
    transport, pool, clock = make(*[failure] * 5)
    with pytest.raises(TransportError, match="after 5 attempts") as caught:
        transport.send(KEYED, REQUEST, key=KEY)
    assert caught.value.__context__ is None
    assert caught.value.__cause__ is None
    assert caught.value.provider == "toy_json"
    assert len(pool.calls) == 5
    assert len(clock.slept) == 4


def test_a_connection_failure_that_clears_is_retried_to_success() -> None:
    transport, pool, _ = make(ConnectionResetError("reset"), ok(b"fine"))
    assert transport.send(KEYED, REQUEST, key=KEY).body == b"fine"
    assert len(pool.calls) == 2


@pytest.mark.parametrize(
    "failure",
    [
        ssl.SSLError("certificate verify failed"),
        urllib3.exceptions.SSLError("tls"),
        ValueError("bad"),
    ],
)
def test_a_tls_failure_or_a_bug_is_not_retried(failure: BaseException) -> None:
    transport, pool, clock = make(failure, BANNED)
    with pytest.raises(TransportError, match="could not be reached") as caught:
        transport.send(KEYED, REQUEST, key=KEY)
    assert caught.value.__context__ is None
    assert len(pool.calls) == 1
    assert clock.slept == []


def test_an_error_message_holds_neither_the_key_nor_the_query() -> None:
    leaky = OSError(
        f"GET https://api.toyjson.example.org/v1/x?api_key={KEY}&x=1 failed"
    )
    transport, _, _ = make(*[leaky] * 5)
    # the key is registered the moment the chain reads it
    with pytest.raises(TransportError) as caught:
        transport.send(KEYED, REQUEST, key=KEY)
    text = str(caught.value) + repr(caught.value)
    assert (KEY in text) is False
    assert ("api_key" in text) is False
    assert "https://api.toyjson.example.org/v1/x" in text


# --- rate limits --------------------------------------------------------------


def test_requests_wait_for_the_providers_declared_limits() -> None:
    info = replace(stub_info(), rate_limits=(RateLimit(requests=2, per="second"),))
    transport, _, clock = make(ok(), ok(), ok(), ok(), ok())
    for _ in range(5):
        transport.send(info, Request(host=HOST, path="/v1/x"))
    assert clock.slept == [1.0, 1.0]  # grants at 0, 0, 1, 1, 2


def test_a_spent_daily_limit_raises_without_sending() -> None:
    info = replace(stub_info(), rate_limits=(RateLimit(requests=1, per="day"),))
    transport, pool, _ = make(ok(), BANNED)
    transport.send(info, Request(host=HOST, path="/v1/x"))
    with pytest.raises(RateLimitError) as caught:
        transport.send(info, Request(host=HOST, path="/v1/x"))
    assert caught.value.retry_after is not None
    assert caught.value.retry_after > 60
    assert len(pool.calls) == 1


def test_each_retry_waits_for_the_limiter_too() -> None:
    info = replace(stub_info(), rate_limits=(RateLimit(requests=1, per="minute"),))
    transport, pool, clock = make(FakeRaw(503), ok(), max_wait=61.0)
    transport.send(info, Request(host=HOST, path="/v1/x"))
    assert len(pool.calls) == 2
    assert sum(clock.slept) >= 60.0


# --- sizes and bodies ---------------------------------------------------------


def test_the_response_keeps_only_the_headers_a_client_reads() -> None:
    raw = FakeRaw(
        200,
        b"{}",
        {
            "Content-Type": "application/json",
            "Set-Cookie": "session=abc",
            "ETag": '"x"',
            "X-Other": "ignored",
        },
    )
    transport, _, _ = make(raw)
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert dict(response.headers) == {"content-type": "application/json", "etag": '"x"'}


def test_a_declared_length_over_the_cap_is_refused_unread() -> None:
    raw = FakeRaw(200, b"x" * 10, {"Content-Length": "5000000"})
    info = replace(KEYED, max_response_bytes=1_024)
    transport, _, _ = make(raw)
    with pytest.raises(ResponseError, match="larger than 1024 bytes"):
        transport.send(info, REQUEST, key=KEY)
    assert raw.closed


def test_a_streamed_body_over_the_cap_is_refused_and_closed() -> None:
    raw = FakeRaw(200, b"x" * 5_000)
    info = replace(KEYED, max_response_bytes=1_024)
    transport, _, _ = make(raw)
    with pytest.raises(ResponseError, match="larger than 1024 bytes"):
        transport.send(info, REQUEST, key=KEY)
    assert raw.closed


def test_a_body_exactly_at_the_cap_is_accepted() -> None:
    raw = FakeRaw(200, b"x" * 1_024)
    info = replace(KEYED, max_response_bytes=1_024)
    transport, _, _ = make(raw)
    assert len(transport.send(info, REQUEST, key=KEY).body) == 1_024
    assert raw.released


def test_a_failure_while_reading_the_body_is_retried() -> None:
    broken = FakeRaw(200, b"abc", chunk_error=urllib3.exceptions.ProtocolError("cut"))
    transport, pool, _ = make(broken, ok(b"whole"))
    assert transport.send(KEYED, REQUEST, key=KEY).body == b"whole"
    assert len(pool.calls) == 2


def test_a_tls_failure_while_reading_is_not_retried() -> None:
    broken = FakeRaw(200, b"abc", chunk_error=ssl.SSLError("bad record"))
    transport, pool, _ = make(broken, BANNED)
    with pytest.raises(TransportError):
        transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 1


def real_response(body: bytes, **headers: str) -> urllib3.HTTPResponse:
    """A real urllib3 response over bytes, as the pool would return it."""
    return urllib3.HTTPResponse(
        body=io.BytesIO(body), headers=headers, status=200, preload_content=False
    )


def test_real_urllib3_responses_work_with_the_transport() -> None:
    transport, _, _ = make(
        real_response(b'{"a":1}', **{"Content-Type": "application/json"})
    )
    response = transport.send(KEYED, REQUEST, key=KEY)
    assert response.json() == {"a": 1}
    assert response.header("content-type") == "application/json"


def test_a_gzip_body_is_decoded() -> None:
    raw = real_response(
        gzip.compress(b'{"hello":"world"}'), **{"Content-Encoding": "gzip"}
    )
    transport, _, _ = make(raw)
    assert transport.send(KEYED, REQUEST, key=KEY).json() == {"hello": "world"}


def test_a_decompression_bomb_hits_the_cap_on_the_decoded_size() -> None:
    bomb = gzip.compress(b"\0" * 20_000_000)  # about 20 KB on the wire
    assert len(bomb) < 100_000
    raw = real_response(bomb, **{"Content-Encoding": "gzip"})
    info = replace(KEYED, max_response_bytes=64 * 1_024)
    transport, _, _ = make(raw)
    with pytest.raises(ResponseError, match="larger than 65536 bytes"):
        transport.send(info, REQUEST, key=KEY)


# --- the shared pool and construction -----------------------------------------


def test_the_shared_pool_is_one_urllib3_manager_with_the_os_trust_store(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import truststore  # noqa: PLC0415

    from pyeconomics.data.transport import http  # noqa: PLC0415

    monkeypatch.setattr(http, "_SHARED_POOL", {})
    first, second = HttpTransport()._pool(), HttpTransport()._pool()  # noqa: SLF001
    assert first is second
    assert isinstance(first, urllib3.PoolManager)
    context = first.connection_pool_kw["ssl_context"]
    assert isinstance(context, truststore.SSLContext)
    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname is True


def test_a_transport_with_its_own_pool_clears_it_on_close() -> None:
    transport, pool, _ = make(ok())
    transport.close()
    assert pool.script == []
    HttpTransport(pool=object()).close()  # a pool without clear() is fine
    HttpTransport().close()


def test_the_default_transport_is_one_http_transport() -> None:
    from pyeconomics.data.transport import default_transport  # noqa: PLC0415

    assert default_transport() is default_transport()
    assert isinstance(default_transport(), HttpTransport)


def test_a_provider_fetches_through_the_http_transport_end_to_end() -> None:
    body = json.dumps(
        {
            "title": "Toy policy rate",
            "units": "Percent",
            "frequency": "monthly",
            "seasonal_adjustment": "NSA",
            "observations": [{"date": "2025-01-01", "value": "4.50"}],
        }
    ).encode()
    transport, pool, _ = make(ok(body, **{"Content-Type": "application/json"}))
    series = ToyJson().fetch({"series": ("TOYRATE",)}, key=KEY, transport=transport)
    assert isinstance(series, Series)
    assert series.values == (0.045,)
    assert series.meta.retrieved_at == FIXED_NOW
    assert query(pool.calls[0].url)["series_id"] == "TOYRATE"


def test_a_stub_provider_has_no_key_in_its_url() -> None:
    transport, pool, _ = make(ok())
    transport.send(Stub.info, Request(host=HOST, path="/v1/x"))
    assert urlsplit(pool.calls[0].url).query == ""
    info: ProviderInfo = Stub.info
    assert info.key_variable is None


# --- hardening ----------------------------------------------------------------


def test_every_request_on_the_wire_takes_a_place_in_the_limit_a_redirect_included() -> (
    None
):
    info = replace(KEYED, rate_limits=(RateLimit(requests=1, per="second"),))
    target = f"https://{info.hosts[0]}/v1/moved"
    transport, pool, clock = make(FakeRaw(302, headers={"Location": target}), ok())
    transport.send(info, REQUEST, key=KEY)
    assert len(pool.calls) == 2
    assert clock.slept == [1.0]


class Dribbling(FakeRaw):
    """A body that arrives slowly: each chunk costs the fake clock some seconds."""

    clock: FakeClock | None = None
    cost: float = 6.0

    def stream(self, amt: int, decode_content: bool = True) -> Any:  # noqa: FBT001, FBT002
        for chunk in super().stream(amt, decode_content):
            assert self.clock is not None
            self.clock.now += self.cost
            yield chunk


def dribbling(clock: FakeClock) -> Dribbling:
    raw = Dribbling(200, b"x" * 100_000)
    raw.clock = clock
    return raw


def test_a_body_that_dribbles_in_past_the_deadline_is_dropped_and_retried() -> None:
    clock = FakeClock()
    slow = dribbling(clock)
    pool = FakePool(slow, ok(b"quick"))
    transport = HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        jitter=lambda ceiling: ceiling,
        max_duration=10.0,
    )
    assert transport.send(KEYED, REQUEST, key=KEY).body == b"quick"
    assert slow.closed
    assert len(pool.calls) == 2


def test_a_body_that_is_always_too_slow_ends_in_a_scrubbed_transport_error() -> None:
    clock = FakeClock()
    pool = FakePool(*[dribbling(clock) for _ in range(5)])
    transport = HttpTransport(
        pool=pool,
        clock=clock.monotonic,
        sleep=clock.sleep,
        now=lambda: FIXED_NOW,
        max_duration=10.0,
    )
    with pytest.raises(TransportError, match="took longer than 10 s") as caught:
        transport.send(KEYED, REQUEST, key=KEY)
    assert caught.value.__context__ is None


def test_the_wire_request_shows_neither_its_url_nor_its_headers() -> None:
    transport, _, _ = make()
    wire = transport._wire(KEYED, REQUEST, KEY)  # noqa: SLF001
    assert (KEY in repr(wire)) is False
    assert repr(wire) == "<wire request GET>"


def test_a_host_list_that_is_not_a_tuple_of_text_admits_nothing() -> None:
    from pyeconomics.data.transport.base import declared_hosts  # noqa: PLC0415

    assert declared_hosts(KEYED) == KEYED.hosts
    for hosts in ("api.toyjson.example.org", ["api.toyjson.example.org"], (7,), None):
        broken = replace(KEYED)
        object.__setattr__(broken, "hosts", hosts)
        assert declared_hosts(broken) == ()
    substring = replace(KEYED)
    object.__setattr__(substring, "hosts", "api.toyjson.example.org")
    transport, pool, _ = make(BANNED)
    with pytest.raises(TransportError, match="not a declared host"):
        transport.send(
            substring, Request(host="toyjson.example.org", path="/v1/x"), key=KEY
        )
    assert pool.calls == []


def test_a_redirect_to_a_parent_domain_of_a_declared_host_is_refused() -> None:
    target = "https://toyjson.example.org/v1/x"
    transport, pool, _ = make(FakeRaw(302, headers={"Location": target}), BANNED)
    with pytest.raises(TransportError, match="not a declared host"):
        transport.send(KEYED, REQUEST, key=KEY)
    assert len(pool.calls) == 1
