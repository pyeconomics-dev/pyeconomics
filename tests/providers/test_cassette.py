# tests/providers/test_cassette.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The cassette format: scrubbing, strict reading, keys, the scan and replay."""

from __future__ import annotations

import base64
import datetime as dt
import json
import random
import re
import string
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st
from leakcheck import LeakCheck, canary
from stubs import HOST, STUB_TERMS, stub_info

from pyeconomics.core.errors import InputError
from pyeconomics.data import (
    DataError,
    LicenceClass,
    LicenceError,
    TransportError,
    configure,
)
from pyeconomics.data.transport.base import Request, Response, request_key
from pyeconomics.data.transport.cassette import (
    MAX_CASSETTE_BYTES,
    MAX_OBSERVATIONS,
    SECRET_PATTERNS,
    Cassette,
    RecordedResponse,
    scan_text,
    synthetic_value,
)
from pyeconomics.data.transport.replay import ReplayTransport

WHEN = dt.datetime(2026, 10, 15, 14, 0, tzinfo=dt.UTC)
REQUEST = Request(host=HOST, path="/v1/x", params=(("id", "A"), ("limit", "24")))


def response(
    body: bytes = b'{"ok":true}', status: int = 200, **headers: str
) -> Response:
    return Response(status, body, WHEN, tuple(headers.items()))


def cassette(*exchanges: tuple[Request, Response], synthetic: bool = False) -> Cassette:
    return Cassette.from_exchanges("stub", WHEN, exchanges, synthetic=synthetic)


def document(**changes: Any) -> dict[str, Any]:
    base = json.loads(cassette((REQUEST, response())).canonical_json())
    return {**base, **changes}


def read(value: dict[str, Any]) -> Cassette:
    return Cassette.from_json(json.dumps(value))


# --- the format ---------------------------------------------------------------


def test_a_cassette_round_trips_through_canonical_json() -> None:
    built = cassette((REQUEST, response(content_type="text/plain")))
    assert Cassette.from_json(built.canonical_json()) == built
    assert (
        built.canonical_json()
        == Cassette.from_json(built.canonical_json()).canonical_json()
    )


def test_the_stored_document_is_canonical_json_and_one_line_feed() -> None:
    built = cassette((REQUEST, response()))
    stored = built.document()
    assert stored == built.canonical_json() + b"\n"
    assert stored.count(b"\n") == 1
    assert b"\r" not in stored
    assert Cassette.from_json(stored) == built


def test_a_cassette_holds_the_provider_the_time_the_flag_and_the_requests() -> None:
    parsed = json.loads(
        cassette((REQUEST, response()), synthetic=True).canonical_json()
    )
    assert sorted(parsed) == ["provider", "recorded_on", "requests", "synthetic"]
    assert parsed["recorded_on"] == "2026-10-15T14:00:00+00:00"
    (record,) = parsed["requests"]
    assert sorted(record) == ["body", "method", "parameters", "response", "url"]
    assert record["url"] == f"https://{HOST}/v1/x"
    assert record["parameters"] == [["id", "A"], ["limit", "24"]]
    assert sorted(record["response"]) == ["body", "encoding", "headers", "status"]


def test_a_binary_body_is_stored_as_base64() -> None:
    blob = bytes(range(256))
    built = cassette((REQUEST, response(blob)))
    stored = json.loads(built.canonical_json())["requests"][0]["response"]
    assert stored["encoding"] == "base64"
    assert base64.b64decode(stored["body"]) == blob
    assert Cassette.from_json(built.canonical_json()).requests[0].response.body == blob


def test_the_key_of_a_recorded_request_is_the_one_replay_looks_up() -> None:
    built = cassette((REQUEST, response()))
    assert built.requests[0].key == request_key(REQUEST)
    assert built.lookup(REQUEST) is built.requests[0]


def test_parameters_in_any_order_find_the_same_recording() -> None:
    built = cassette((REQUEST, response()))
    shuffled = replace(REQUEST, params=tuple(reversed(REQUEST.params)))
    assert built.lookup(shuffled) is not None
    assert request_key(shuffled) == request_key(REQUEST)


def test_a_request_with_a_body_is_keyed_by_the_hash_of_its_canonical_body() -> None:
    first = Request(host=HOST, path="/v1/x", method="POST", body={"b": 1, "a": 2})
    same = Request(host=HOST, path="/v1/x", method="POST", body={"a": 2, "b": 1})
    other = Request(host=HOST, path="/v1/x", method="POST", body={"a": 3, "b": 1})
    assert request_key(first) == request_key(same)
    assert request_key(first) != request_key(other)
    assert re.search(r" body-sha256:[0-9a-f]{64}$", request_key(first))
    built = cassette((first, response()))
    assert built.lookup(same) is not None
    assert built.lookup(other) is None
    get = replace(first, method="GET", body=None)
    assert built.lookup(get) is None


def test_the_same_request_recorded_twice_is_kept_once() -> None:
    assert (
        len(cassette((REQUEST, response()), (REQUEST, response(b"[]"))).requests) == 1
    )


def test_a_cassette_cannot_hold_one_request_twice() -> None:
    entry = json.loads(cassette((REQUEST, response())).canonical_json())["requests"][0]
    with pytest.raises(InputError, match="once"):
        read(document(requests=[entry, entry]))


# --- scrubbing ----------------------------------------------------------------


def test_every_registered_secret_is_scrubbed_from_everything_recorded() -> None:
    held = canary("stub")
    key = held.value
    request = Request(
        host=HOST,
        path="/v1/x",
        params=(("note", f"key is {key}"),),
        method="POST",
        body={"echo": [f"see {key}"]},
    )
    reply = response(
        f'{{"echo":"{key}","url":"https://{HOST}/v1/x?api_key={key}"}}'.encode(),
        etag=f'"{key}"',
    )
    built = cassette((request, reply))
    check = LeakCheck(held)
    check.add("canonical_json", built.canonical_json())
    check.add("document", built.document())
    check.add("repr", repr(built))
    check.assert_clean()
    assert "[redacted]" in built.canonical_json().decode()


def test_a_credential_in_a_response_header_or_cookie_is_never_kept() -> None:
    reply = Response(
        200,
        b"{}",
        WHEN,
        (
            ("Set-Cookie", "session=abc123"),
            ("Authorization", "Bearer abc"),
            ("X-Api-Key", "abc"),
            ("Content-Type", "application/json"),
            ("X-Unrelated", "dropped"),
        ),
    )
    (record,) = cassette((REQUEST, reply)).requests
    assert dict(record.response.headers) == {"content-type": "application/json"}


def test_a_binary_body_holding_a_registered_key_cannot_be_recorded() -> None:
    held = canary("stub")
    blob = b"\xff\xfe" + held.value.encode() + b"\x00"
    with pytest.raises(DataError, match="registered key") as caught:
        cassette((REQUEST, response(blob)))
    assert held.value not in str(caught.value)


def test_a_cassette_never_holds_a_credential_parameter() -> None:
    request = replace(REQUEST)  # a Request refuses credentials, so build around it
    object.__setattr__(
        request, "params", (*request.params, ("api_key", "value-1234567"))
    )
    (record,) = cassette((request, response())).requests
    assert "api_key" not in dict(record.parameters)
    assert dict(record.parameters) == {"id": "A", "limit": "24"}


# --- strict reading -----------------------------------------------------------


@pytest.mark.parametrize(
    "mutate",
    [
        lambda d: {**d, "extra": 1},
        lambda d: {k: v for k, v in d.items() if k != "synthetic"},
        lambda d: {**d, "synthetic": "yes"},
        lambda d: {**d, "provider": "Not Snake"},
        lambda d: {**d, "recorded_on": "2026-10-15T14:00:00"},
        lambda d: {**d, "recorded_on": "yesterday"},
        lambda d: {**d, "recorded_on": None},
        lambda d: {**d, "requests": "none"},
        lambda d: {**d, "requests": [1]},
    ],
)
def test_a_malformed_cassette_is_refused(mutate: Any) -> None:
    with pytest.raises(InputError):
        read(mutate(document()))


def mutate_request(**changes: Any) -> dict[str, Any]:
    base = document()
    base["requests"][0] = {**base["requests"][0], **changes}
    return base


def mutate_response(**changes: Any) -> dict[str, Any]:
    base = document()
    stored = base["requests"][0]["response"]
    base["requests"][0]["response"] = {**stored, **changes}
    return base


@pytest.mark.parametrize(
    "bad",
    [
        mutate_request(url="http://api.stub.example.org/v1/x"),
        mutate_request(url="https://api.stub.example.org/v1/x?api_key=1"),
        mutate_request(url="https://api.stub.example.org/v1/x#frag"),
        mutate_request(url="https://api.stub.example.org/v1/x y"),
        mutate_request(url=7),
        mutate_request(url="https://other host.example.org/v1/x"),
        mutate_request(parameters=[["only-one"]]),
        mutate_request(parameters=[["a", 1]]),
        mutate_request(parameters="a=b"),
        mutate_request(method="DELETE"),
        mutate_request(method="TOOLONGMETHOD"),
        mutate_request(body={"registrationkey": "abc"}),
        mutate_response(status=99),
        mutate_response(status=True),
        mutate_response(status="200"),
        mutate_response(encoding="latin-1"),
        mutate_response(encoding="base64", body="!!!not base64"),
        mutate_response(body=7),
        mutate_response(headers={"set-cookie": "a=b"}),
        mutate_response(headers={"content-type": 7}),
        mutate_response(headers=[["content-type", "x"]]),
    ],
)
def test_a_malformed_recorded_request_or_response_is_refused(
    bad: dict[str, Any],
) -> None:
    with pytest.raises(InputError):
        read(bad)


def test_duplicate_keys_nan_and_junk_are_refused() -> None:
    for text in ('{"provider":"a","provider":"b"}', "{", "NaN", "[1]", ""):
        with pytest.raises(InputError):
            Cassette.from_json(text)


# --- the scan -----------------------------------------------------------------


def random_text(alphabet: str, length: int) -> str:
    return "".join(random.SystemRandom().choice(alphabet) for _ in range(length))


UPPER_DIGITS = string.ascii_uppercase + string.digits
URLSAFE = string.ascii_letters + string.digits + "-_"


def samples() -> dict[str, str]:
    """One matching text per pattern, built at run time so no source line is a key."""
    fred = random_text(string.ascii_lowercase + string.digits, 32)
    jwt = ".".join(random_text(URLSAFE, 24) for _ in range(3))
    return {
        "fred-api-key": f"fred_api_key = '{fred}'",
        "aws-access-key": "AK" + "IA" + random_text(UPPER_DIGITS, 16),
        "github-token": "ghp_" + random_text(string.ascii_letters + string.digits, 36),
        "slack-token": "xo" + "xb-" + random_text(string.digits, 12),
        "google-api-key": "AI" + "za" + random_text(URLSAFE, 35),
        "openai-style-key": "s" + "k-" + random_text(URLSAFE, 32),
        "private-key-block": "-----" + "BEGIN RSA PRIVATE KEY" + "-----",
        "json-web-token": "ey" + "J" + jwt[:24] + ".ey" + "J" + jwt[25:],
        "bearer-credential": "Bearer " + random_text(URLSAFE, 32),
        "credential-assignment": 'password: "' + random_text(URLSAFE, 20) + '"',
        "credential-parameter": "?key=" + random_text(URLSAFE, 12),
    }


@pytest.mark.parametrize("name", sorted(SECRET_PATTERNS))
def test_the_scan_finds_each_secret_format_and_names_it_without_the_value(
    name: str,
) -> None:
    text = samples()[name]
    found = scan_text(text)
    assert name in found
    assert all(text not in hit for hit in found)


def test_every_pattern_has_a_sample() -> None:
    assert set(samples()) == set(SECRET_PATTERNS)


@pytest.mark.parametrize(
    "benign",
    [
        '{"series":"GDPC1","observations":[{"date":"2025-01-01","value":"4.50"}]}',
        "https://api.stub.example.org/v1/observations?series_id=GDPC1&limit=24",
        "sha256:" + "ab" * 32,
        "The key to the series is its identifier.",
        '{"next_page_token": "short"}',
        "Authorization header values are never recorded.",
    ],
)
def test_the_scan_leaves_ordinary_responses_alone(benign: str) -> None:
    assert scan_text(benign) == []


def test_the_project_fred_rule_agrees_with_gitleaks_toml() -> None:
    config = tomllib.loads(
        (Path(__file__).resolve().parents[2] / ".gitleaks.toml").read_text(
            encoding="utf-8"
        )
    )
    rule = next(r for r in config["rules"] if r["id"] == "fred-api-key")
    theirs = re.compile(rule["regex"])
    ours = SECRET_PATTERNS["fred-api-key"]
    key = random_text(string.ascii_lowercase + string.digits, 32)
    for text in (
        f"fred_api_key = '{key}'",
        f'FRED_API_KEY: "{key}"',
        f"fred token => {key}",
        f"fred_api_key = '{key[:20]}'",
        "fred is a database",
        f"other_key = '{key}'",
    ):
        assert bool(theirs.search(text)) == bool(ours.search(text)), text


@given(st.text(), st.integers(0, 10_000))
def test_a_synthetic_value_depends_only_on_the_seed_and_position(
    seed: str, index: int
) -> None:
    value = synthetic_value(seed, index)
    assert value == synthetic_value(seed, index)
    assert 0.0 <= value <= 1.0
    assert value == round(value, 4)


def test_synthetic_values_differ_by_seed_and_position() -> None:
    assert len({synthetic_value("A", i) for i in range(50)}) > 40
    assert synthetic_value("A", 0) != synthetic_value("B", 0)


def test_the_caps_are_the_recording_rules() -> None:
    assert (MAX_OBSERVATIONS, MAX_CASSETTE_BYTES) == (24, 32 * 1024)


# --- the replay transport -----------------------------------------------------


def test_replay_serves_the_recorded_response_stamped_with_the_recording_time() -> None:
    built = cassette((REQUEST, response(b"hello", 200, etag='"v1"')))
    replay = ReplayTransport([built])
    reply = replay.send(stub_info(), REQUEST)
    assert (reply.status, reply.body, reply.retrieved_at) == (200, b"hello", WHEN)
    assert reply.header("etag") == '"v1"'
    assert replay.served == [request_key(REQUEST)]


def test_replay_needs_no_key_and_ignores_one() -> None:
    replay = ReplayTransport([cassette((REQUEST, response()))])
    assert replay.send(stub_info(), REQUEST, key=None).ok
    assert replay.send(stub_info(), REQUEST, key="anything-at-all-123").ok


def test_a_request_with_no_cassette_fails_naming_its_key_but_no_credential() -> None:
    replay = ReplayTransport([cassette((REQUEST, response()))])
    missing = Request(host=HOST, path="/v1/y", params=(("id", "B"),))
    with pytest.raises(TransportError) as caught:
        replay.send(stub_info(), missing)
    assert f"GET {HOST}/v1/y?id=B" in str(caught.value)
    assert caught.value.provider == "stub"


def test_replay_only_reads_the_cassettes_of_the_providers_id() -> None:
    other = Cassette.from_exchanges(
        "other", WHEN, [(REQUEST, response())], synthetic=False
    )
    with pytest.raises(TransportError):
        ReplayTransport([other]).send(stub_info(), REQUEST)


def test_the_first_recording_of_a_key_answers() -> None:
    first = cassette((REQUEST, response(b"first")))
    second = cassette((REQUEST, response(b"second")))
    assert ReplayTransport([first, second]).send(stub_info(), REQUEST).body == b"first"


def test_replay_refuses_a_foreign_host_and_hosted_mode_like_the_real_transport() -> (
    None
):
    foreign = Request(host="foreign.example.net", path="/v1/x")
    with pytest.raises(TransportError, match="not a declared host"):
        ReplayTransport([]).send(stub_info(), foreign)
    library = stub_info(terms=replace(STUB_TERMS, licence=LicenceClass.LIBRARY_ONLY))
    configure(mode="hosted")
    with pytest.raises(LicenceError):
        ReplayTransport([]).send(library, REQUEST)


def test_replay_loads_files_and_directories(tmp_path: Path) -> None:
    one = cassette((REQUEST, response(b"one")))
    (tmp_path / "a" / "b").mkdir(parents=True)
    (tmp_path / "a" / "one.json").write_bytes(one.document())
    other = Request(host=HOST, path="/v1/two")
    (tmp_path / "a" / "b" / "two.json").write_bytes(
        cassette((other, response(b"two"))).document()
    )
    (tmp_path / "a" / "notes.txt").write_text("not a cassette")
    assert (
        ReplayTransport.from_file(tmp_path / "a" / "one.json")
        .send(stub_info(), REQUEST)
        .body
        == b"one"
    )
    everything = ReplayTransport.from_directory(tmp_path)
    assert everything.send(stub_info(), REQUEST).body == b"one"
    assert everything.send(stub_info(), other).body == b"two"


def test_a_provider_fetches_through_a_replay_transport_end_to_end() -> None:
    from stubs import Stub  # noqa: PLC0415

    stub = Stub()
    request = stub.requests[0]
    replay = ReplayTransport([cassette((request, response()))])
    assert stub.fetch({"series": ("S",)}, transport=replay).meta.retrieved_at == WHEN


def test_a_recorded_response_exposes_its_parts() -> None:
    parsed = RecordedResponse.from_dict(
        {"status": 200, "headers": {"etag": "x"}, "body": "hi", "encoding": "utf-8"}
    )
    assert (parsed.status, parsed.body, parsed.headers) == (
        200,
        b"hi",
        (("etag", "x"),),
    )
    assert parsed.to_dict()["body"] == "hi"
