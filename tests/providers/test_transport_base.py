# tests/providers/test_transport_base.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``Request`` and ``Response``: what a provider may ask for and what it gets back."""

from __future__ import annotations

import datetime as dt
import json
from dataclasses import replace
from typing import Any

import pytest
from stubs import HOST, stub_info

from pyeconomics.core import InputError
from pyeconomics.data import ResponseError, TransportError
from pyeconomics.data.transport.base import (
    KEPT_HEADERS,
    MAX_BODY_BYTES,
    MAX_PARAMETERS,
    Request,
    Response,
    check_host,
    request_key,
    request_path,
    retry_after_seconds,
)

WHEN = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.UTC)


def request(**changes: Any) -> Request:
    return Request(**{"host": HOST, "path": "/v1/x", **changes})


# --- paths --------------------------------------------------------------------


def test_each_segment_is_encoded_whole() -> None:
    assert request_path("v1", "series", "GDP/REAL") == "/v1/series/GDP%2FREAL"
    assert request_path("a b", "c?d=e#f") == "/a%20b/c%3Fd%3De%23f"
    assert request_path("é") == "/%C3%A9"
    assert request_path() == ""


@pytest.mark.parametrize("segment", ["", ".", ".."])
def test_a_segment_that_climbs_or_is_empty_is_refused(segment: str) -> None:
    with pytest.raises(InputError):
        request_path("v1", segment)


@pytest.mark.parametrize(
    "path",
    [
        "v1/x",  # no leading slash
        "",
        "/v1/x?a=1",
        "/v1/x#frag",
        "/v1/ x",
        "/v1//x",
        "/v1/../x",
        "/v1/%2e%2E/x",
        "/v1/./x",
        "/v1/x%",
        "/v1/x%zz",
        "/v1/x\\y",
        "/v1/x\ny",
        pytest.param("/" + "a" * 2_100, id="too-long"),
        7,
    ],
)
def test_an_unsafe_path_is_refused(path: Any) -> None:
    with pytest.raises(InputError):
        request(path=path)


@pytest.mark.parametrize(
    "path",
    ["/", "/v1/x", "/v1/x/", "/v1/a%2Fb", "/datadownload/Output.aspx", "/v1/a,b;c=d"],
)
def test_an_ordinary_path_is_accepted(path: str) -> None:
    assert request(path=path).path == path


# --- hosts, methods, parameters, headers --------------------------------------


@pytest.mark.parametrize(
    "host",
    [
        "",
        "http://api.example.org",
        "api.example.org:8443",
        "API.example.org",
        "example",
        "10.0.0.1",
        pytest.param("a" * 300 + ".org", id="too-long"),
        "api.example.org/",
        "api .example.org",
        7,
    ],
)
def test_a_host_must_be_an_exact_lower_case_dns_name(host: Any) -> None:
    with pytest.raises(InputError):
        request(host=host)


def test_only_get_and_post_are_methods_and_a_get_has_no_body() -> None:
    assert request(method="POST", body={"a": 1}).method == "POST"
    for method in ("PUT", "DELETE", "get", 7):
        with pytest.raises(InputError):
            request(method=method)
    with pytest.raises(InputError):
        request(body={"a": 1})


def test_parameters_are_pairs_of_plain_text() -> None:
    params = request(params=[("a", "1"), ["b", "two words"]]).params
    assert params == (("a", "1"), ("b", "two words"))
    for bad in (
        [("a",)],
        [("a", 1)],
        [(1, "a")],
        [("bad name", "1")],
        [("", "1")],
        [("a", "x\x00y")],
        [("a", "y" * 2_100)],  # a value over 2,048 characters
        "a=b",
        [("n" + str(i), "1") for i in range(MAX_PARAMETERS + 1)],
    ):
        with pytest.raises(InputError):
            request(params=bad)


@pytest.mark.parametrize(
    "name",
    [
        "api_key",
        "API_KEY",
        "apikey",
        "key",
        "registrationkey",
        "UserID",
        "token",
        "access_token",
    ],
)
def test_a_credential_parameter_is_refused(name: str) -> None:
    with pytest.raises(InputError, match="credential"):
        request(params=((name, "value-12345"),))


@pytest.mark.parametrize(
    "name",
    ["Authorization", "X-Api-Key", "Cookie", "X-Auth-Token", "Proxy-Authorization"],
)
def test_a_credential_header_is_refused(name: str) -> None:
    with pytest.raises(InputError, match="credential"):
        request(headers=((name, "value-12345"),))


@pytest.mark.parametrize(
    "name",
    [
        "Host",
        "Content-Length",
        "User-Agent",
        "Accept-Encoding",
        "Transfer-Encoding",
        "Connection",
        "Content-Type",
    ],
)
def test_a_header_the_transport_owns_is_refused(name: str) -> None:
    with pytest.raises(InputError, match="itself"):
        request(headers=((name, "x"),))
    assert request(headers=(("Accept", "application/json"),)).headers == (
        ("Accept", "application/json"),
    )


# --- bodies -------------------------------------------------------------------


def test_a_body_is_copied_so_the_callers_object_cannot_change_it() -> None:
    inner = [1, 2]
    body = {"a": inner, "b": {"c": "d"}}
    made = request(method="POST", body=body)
    inner.append(3)
    assert made.body == {"a": [1, 2], "b": {"c": "d"}}


@pytest.mark.parametrize(
    "body",
    [
        {"registrationkey": "abc"},
        {"outer": {"API_KEY": 1}},
        [{"token": 1}],  # nosec B105 - a credential-named field Request must refuse
        {"a": [{"Key": 1}]},
    ],
)
def test_a_credential_field_anywhere_in_a_body_is_refused(body: Any) -> None:
    with pytest.raises(InputError, match="credential"):
        request(method="POST", body=body)


@pytest.mark.parametrize(
    "body",
    [
        object(),
        {1, 2},
        {"a": float("nan")},
        {"a": b"bytes"},
        pytest.param("x" * (MAX_BODY_BYTES + 1), id="over-the-cap"),
    ],
)
def test_a_body_must_be_small_json(body: Any) -> None:
    with pytest.raises(InputError):
        request(method="POST", body=body)


@pytest.mark.parametrize(
    "body", [{"a": 1}, [1, 2], "text", 5, True, None, {"nested": {"x": [None, 1.5]}}]
)
def test_json_ready_bodies_are_accepted(body: Any) -> None:
    assert request(method="POST", body=body).body == body


def test_the_series_a_request_concerns_is_text() -> None:
    assert request(series="GDP").series == "GDP"
    with pytest.raises(InputError):
        request(series="x" * 200)


def test_a_request_key_names_method_host_path_sorted_params_and_a_body_hash() -> None:
    assert (
        request_key(request(params=(("b", "2"), ("a", "1"))))
        == f"GET {HOST}/v1/x?a=1&b=2"
    )
    assert request_key(request()) == f"GET {HOST}/v1/x"
    posted = request(method="POST", body={"a": 1})
    key = request_key(posted)
    assert key.startswith(f"POST {HOST}/v1/x body-sha256:")
    assert len(key.split(":")[-1]) == 64
    assert key != request_key(request(method="POST", body={"a": 2}))
    assert request_key(request(params=(("q", "a b&c"),))).endswith("?q=a%20b%26c")


# --- responses ----------------------------------------------------------------


def response(body: bytes = b"{}", status: int = 200, headers: Any = ()) -> Response:
    return Response(status, body, WHEN, headers)


@pytest.mark.parametrize("status", [99, 600, True, "200", None, 200.0])
def test_a_status_is_an_http_status_code(status: Any) -> None:
    with pytest.raises(InputError):
        response(status=status)


def test_a_body_is_bytes_and_a_time_carries_a_zone() -> None:
    with pytest.raises(InputError):
        Response(200, "text", WHEN)  # type: ignore[arg-type]
    with pytest.raises(InputError):
        Response(200, b"", dt.datetime(2026, 1, 1))  # noqa: DTZ001
    assert (
        Response(
            200, b"", WHEN.astimezone(dt.timezone(dt.timedelta(hours=5)))
        ).retrieved_at
        == WHEN
    )


def test_only_the_headers_a_client_reads_are_kept_and_lower_cased() -> None:
    headers = [
        ("Content-Type", "text/csv"),
        ("Set-Cookie", "a=b"),
        ("ETag", '"1"'),
        ("X-Else", "z"),
    ]
    made = response(headers=headers)
    assert made.headers == (("content-type", "text/csv"), ("etag", '"1"'))
    assert made.header("Content-Type") == "text/csv"
    assert made.header("set-cookie") is None
    assert set(KEPT_HEADERS) >= {"content-type", "retry-after"}


@pytest.mark.parametrize(
    ("status", "ok"),
    [(200, True), (204, True), (299, True), (301, False), (404, False), (500, False)],
)
def test_ok_is_a_2xx(status: int, ok: bool) -> None:  # noqa: FBT001
    assert response(status=status).ok is ok


def test_text_decodes_utf8_or_says_it_is_not() -> None:
    assert response("é".encode()).text() == "é"
    with pytest.raises(ResponseError, match="not UTF-8") as caught:
        response(b"\xff\xfe").text(provider="demo")
    assert caught.value.provider == "demo"


def test_json_is_strict_and_never_repeats_the_body() -> None:
    assert response(json.dumps({"a": [1, None]}).encode()).json() == {"a": [1, None]}
    secret_looking = b'{"a": NaN, "note": "do-not-echo-this-text"}'
    for body in (
        secret_looking,
        b"{",
        b"",
        b'{"a":1,"a":2}',
        b"[" * 200 + b"]" * 200,
        b"\xff",
    ):
        with pytest.raises(ResponseError, match="not strict JSON") as caught:
            response(body).json(provider="demo")
        assert "do-not-echo" not in str(caught.value)
        assert caught.value.provider == "demo"


# --- the allowlist ------------------------------------------------------------


def test_check_host_accepts_a_declared_host_and_refuses_the_rest() -> None:
    info = stub_info()
    check_host(info, request())
    with pytest.raises(TransportError, match="not a declared host"):
        check_host(info, request(host="other.example.org"))
    with pytest.raises(TransportError):
        check_host(replace(info, hosts=()), request())


# --- Retry-After --------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "seconds"),
    [
        ("0", 0.0),
        ("30", 30.0),
        (" 45 ", 45.0),
        ("Thu, 15 Oct 2026 12:00:30 GMT", 30.0),
        ("Thu, 15 Oct 2026 11:00:00 GMT", 0.0),  # in the past: no wait
        ("Thu, 15 Oct 2026 12:01:00 +0000", 60.0),
        ("Thu, 15 Oct 2026 12:01:00", 60.0),  # no zone: read as UTC
    ],
)
def test_retry_after_reads_seconds_or_a_date(value: str, seconds: float) -> None:
    assert retry_after_seconds(value, WHEN) == seconds


@pytest.mark.parametrize(
    "value", [None, "", "soon", "-5", "1.5", "99999999999", "٣٠", "Not, a date"]
)
def test_anything_else_is_no_advice(value: str | None) -> None:
    assert retry_after_seconds(value, WHEN) is None
