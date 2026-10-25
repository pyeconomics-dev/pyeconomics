# tests/server/test_server_limits.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Per-client rate limits (Phase 4 Step 7; ADR-0012 decision 12; threat 2).

The burst test drives a low limit concurrently and counts the answers: exactly
the limit is served, and every other request is ``429 too-many-requests`` with
``Retry-After``. Runs, series and metadata count separately, and the health
probes never count. A storage outage refuses runs and series (``503
limits-unavailable``) and still serves metadata, logged once by the error's type
name and never with the storage's URL. The Redis URL must be TLS for a remote
host, and its password is registered with redaction. Hosted mode limits by
default; local mode does not.
"""

from __future__ import annotations

import logging
import math
import secrets
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
from leakcheck import LeakCheck
from limits.errors import StorageError
from limits.storage import MemoryStorage, RedisStorage
from redis.exceptions import ConnectionError as RedisConnectionError
from server_support import LOOPBACK_ONLY, Plant, client, problem, service_of

from pyeconomics.core import InputError
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import ConfigError, redaction
from pyeconomics.server import ServerSettings, create_app
from pyeconomics.server import limits as limits_module
from pyeconomics.server.limits import (
    HOSTED_LIMITS,
    STORAGE_VARIABLE,
    RateLimits,
    open_storage,
    route_kind,
)

pytestmark = LOOPBACK_ONLY

MODELS = "/v1/models"
RUN = "/v1/models/foundations.time_value/run"
INPUTS = canonical_json(
    {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}
)


def _redis_url(password: str) -> str:
    """A TLS Redis URL holding a password, built in parts (no literal userinfo)."""
    userinfo = f"default:{password}"
    return "rediss://" + userinfo + "@cache.example.org:6379"


def test_the_burst_test_serves_exactly_the_limit_and_refuses_the_rest() -> None:
    limits = RateLimits(metadata="5/minute")
    with (
        client(mode="hosted", rate_limits=limits) as api,
        ThreadPoolExecutor(max_workers=10) as threads,
    ):
        answers = list(threads.map(lambda _: api.get(MODELS), range(30)))
    statuses = [response.status_code for response in answers]
    assert statuses.count(200) == 5
    assert statuses.count(429) == 25
    for response in answers:
        if response.status_code != 429:
            continue
        body = problem(response)
        assert body["type"].endswith("/too-many-requests")
        assert 0 < body["retry_after"] <= 60
        wait = int(response.headers["retry-after"])
        assert wait == math.ceil(body["retry_after"])
        assert 1 <= wait <= 60
        assert "5 per 1 minute" in body["detail"]
        assert response.headers["cache-control"] == "no-store"


def test_runs_series_and_metadata_count_separately() -> None:
    limits = RateLimits(runs="2/minute", series="1/minute", metadata="1/minute")
    with client(mode="hosted", rate_limits=limits) as api:
        runs = [
            api.post(RUN, content=INPUTS).status_code,
            api.get(RUN, params={"inputs": "e30"}).status_code,  # {} decodes
            api.post(RUN, content=INPUTS).status_code,
        ]
        series = [api.get("/v1/series/no.such.concept").status_code for _ in range(2)]
        metadata = [api.get(MODELS).status_code, api.get("/v1/sources").status_code]
    assert runs[2] == 429  # both forms share the run limit
    assert runs[0] == 200
    assert series == [404, 429]
    assert metadata == [200, 429]


def test_the_health_probes_are_never_limited() -> None:
    limits = RateLimits(runs="1/minute", series="1/minute", metadata="1/minute")
    with client(mode="hosted", rate_limits=limits) as api:
        statuses = {api.get(path).status_code for path in ("/healthz", "/version") * 10}
    assert statuses == {200}


def test_hosted_mode_limits_by_default_and_local_mode_does_not(
    caplog: pytest.LogCaptureFixture,
) -> None:
    with caplog.at_level(logging.WARNING, logger="pyeconomics.server"):
        with client(mode="hosted") as hosted:
            limiter = service_of(hosted).limiter
        with client() as local:
            assert service_of(local).limiter is None
    assert limiter is not None
    assert limiter._items == HOSTED_LIMITS.items()  # noqa: SLF001
    assert (
        RateLimits(runs="60/minute", series="30/minute", metadata="120/minute")
        == HOSTED_LIMITS
    )
    said = [
        r.getMessage() for r in caplog.records if STORAGE_VARIABLE in r.getMessage()
    ]
    assert said == [
        f"{STORAGE_VARIABLE} is not set: each process keeps its own rate-limit counts"
    ]


def test_limits_off_turn_hosted_limits_off() -> None:
    with client(mode="hosted", rate_limits=RateLimits.off()) as api:
        assert service_of(api).limiter is None
        assert {api.get(MODELS).status_code for _ in range(5)} == {200}


# --- a storage outage ---------------------------------------------------------------


class _Flaky(MemoryStorage):
    """Memory storage that fails like an unreachable Redis while ``down``."""

    down = True
    url = ""

    def acquire_entry(self, key: str, limit: int, expiry: int, amount: int = 1) -> bool:
        if self.down:
            message = f"Error 111 connecting to {self.url}. Connection refused."
            raise StorageError(RedisConnectionError(message))
        return super().acquire_entry(key, limit, expiry, amount)


def test_an_outage_fails_closed_for_runs_and_series_and_open_for_metadata(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    password = secrets.token_hex(16)
    url = _redis_url(password)
    storage = _Flaky()
    storage.url = url
    monkeypatch.setattr(limits_module, "open_storage", lambda _url: storage)
    monkeypatch.setenv(STORAGE_VARIABLE, url)
    check = LeakCheck(Plant(password))
    with (
        caplog.at_level(logging.INFO, logger="pyeconomics.server"),
        check.logs("pyeconomics.server"),
        client(mode="hosted") as api,
    ):
        run = api.post(RUN, content=INPUTS)
        series = api.get("/v1/series/us.unemployment.rate")
        metadata = api.get(MODELS)
        again = api.post(RUN, content=INPUTS)
        storage.down = False
        recovered = api.post(RUN, content=INPUTS)
        for response in (run, series, metadata, again, recovered):
            check.add("body", response.content)
    for response in (run, series, again):
        assert response.status_code == 503
        assert problem(response)["type"].endswith("/limits-unavailable")
        assert response.headers["retry-after"] == "5"
    assert metadata.status_code == 200
    assert recovered.status_code == 200
    messages = [record.getMessage() for record in caplog.records]
    outages = [m for m in messages if "rate-limit storage is unavailable" in m]
    assert outages == [
        (
            "the rate-limit storage is unavailable (ConnectionError): runs and "
            "series are refused until it answers"
        )
    ]
    assert messages.count("the rate-limit storage answers again") == 1
    check.assert_clean()
    assert "cache.example.org" not in "\n".join(messages)


class _Uncounted(MemoryStorage):
    """Memory storage that refuses every hit and cannot say when the window frees."""

    def acquire_entry(self, *_args: object, **_kwargs: object) -> bool:
        return False

    def get_moving_window(self, *_args: object, **_kwargs: object) -> tuple[float, int]:
        message = "the window cannot be read"
        raise StorageError(RedisConnectionError(message))


def test_a_refusal_whose_window_cannot_be_read_waits_the_whole_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(limits_module, "open_storage", lambda _url: _Uncounted())
    with client(mode="hosted", rate_limits=RateLimits(metadata="5/minute")) as api:
        refused = api.get(MODELS)
    assert refused.status_code == 429
    assert refused.headers["retry-after"] == "60"
    assert problem(refused)["retry_after"] == 60.0


# --- the storage ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "problem_text"),
    [
        ("redis://cache.example.org:6379", "must use TLS"),
        ("http://cache.example.org", "must be a redis:// or rediss:// URL"),
        ("rediss:///0", "must be a redis:// or rediss:// URL"),
        ("memcached://cache.example.org:11211", "must be a redis:// or rediss:// URL"),
        ("rediss://cache.example.org:port", "must be a redis:// or rediss:// URL"),
    ],
)
def test_a_bad_storage_url_is_a_configuration_error_without_the_url(
    url: str, problem_text: str
) -> None:
    with pytest.raises(ConfigError, match=problem_text) as refused:
        open_storage(url)
    assert url not in str(refused.value)
    assert STORAGE_VARIABLE in str(refused.value)


def test_a_tls_url_opens_redis_without_connecting_and_registers_its_secrets() -> None:
    password = secrets.token_hex(16)
    url = _redis_url(password)
    storage = open_storage(url)
    assert isinstance(storage, RedisStorage)
    assert redaction.scrub_text(f"auth {password}") == f"auth {redaction.MASK}"
    assert password not in redaction.scrub_text(url)
    assert isinstance(open_storage("redis://127.0.0.1:6379/0"), RedisStorage)
    assert isinstance(open_storage(None), MemoryStorage)


def test_hosted_mode_reads_the_storage_url_from_the_environment(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv(STORAGE_VARIABLE, "rediss://cache.example.org:6379")
    with caplog.at_level(logging.WARNING, logger="pyeconomics.server"):
        app = create_app(mode="hosted", settings=ServerSettings(workers=0))
    limiter = app.state.service.limiter
    assert isinstance(limiter._strategy.storage, RedisStorage)  # noqa: SLF001
    assert not [r for r in caplog.records if STORAGE_VARIABLE in r.getMessage()]
    monkeypatch.setenv(STORAGE_VARIABLE, "redis://cache.example.org:6379")
    with pytest.raises(ConfigError, match="must use TLS"):
        create_app(mode="hosted", settings=ServerSettings(workers=0))
    local = create_app(settings=ServerSettings(workers=0, rate_limits=RateLimits()))
    assert isinstance(local.state.service.limiter._strategy.storage, MemoryStorage)  # noqa: SLF001


# --- the settings ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "limits",
    [{"runs": "often"}, {"series": "5/fortnight"}, {"metadata": 5}],
)
def test_a_limit_that_does_not_parse_is_invalid_input(limits: dict[str, Any]) -> None:
    with pytest.raises(InputError, match="limit"):
        RateLimits(**limits)


def test_rate_limits_off_and_items() -> None:
    assert not RateLimits.off().enabled
    assert RateLimits.off().items() == {}
    assert set(RateLimits(runs=None).items()) == {"series", "metadata"}
    assert str(RateLimits().items()["series"]) == "30 per 1 minute"


@pytest.mark.parametrize(
    ("path", "kind"),
    [
        ("/v1/models/risk.var/run", "runs"),
        ("/v1/series/fred:UNRATE", "series"),
        ("/v1/models", "metadata"),
        ("/v1/models/risk.var", "metadata"),
        ("/v1/sources", "metadata"),
        ("/openapi.json", "metadata"),
        ("/no/such/route", "metadata"),
        ("/healthz", None),
        ("/version", None),
    ],
)
def test_each_path_counts_against_its_group(path: str, kind: str | None) -> None:
    assert route_kind(path) == kind


@pytest.mark.parametrize(
    "settings",
    [
        {"rate_limits": {"runs": "1/second"}},
        {"cache_entries": -1},
        {"cache_bytes": 1.5},
        {"cache_entries": True},
    ],
)
def test_bad_limit_or_cache_settings_are_invalid_input(
    settings: dict[str, Any],
) -> None:
    with pytest.raises(InputError):
        ServerSettings(**settings)
