# tests/server/test_server_caching.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The GET run cache, entity tags and Cache-Control (Phase 4 Step 7; decision 12).

A GET run carries ``ETag: W/"<result_sha256>"`` and ``Cache-Control``; a matching
``If-None-Match`` answers 304; a repeat is served from memory, with ``Age``,
without running again. A POST run, which may carry a user's file, and every
problem are ``no-store``, and the cache never holds either. A bound run is kept
for five minutes when its data may be stored, and nowhere when it may not (a
library-only source in local mode). The cache is bounded by entries and bytes,
and drops an entry past its max-age.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import bound_support as bs
import pytest
from server_support import LOOPBACK_ONLY, client, encode, problem, service_of

import pyeconomics
from pyeconomics.core import registry as core_registry
from pyeconomics.core.canonical import canonical_json
from pyeconomics.server.run_cache import (
    BOUND_CONTROL,
    DATA_FREE_CONTROL,
    NO_STORE,
    Entry,
    RunCache,
    etag_matches,
    max_age,
    run_key,
)
from pyeconomics.surfaces.envelope import canonical_bytes, etag

if TYPE_CHECKING:
    from fastapi.testclient import TestClient

    from pyeconomics.server.work import Outcome, Task

pytestmark = LOOPBACK_ONLY

MODEL = "foundations.time_value"
RUN = f"/v1/models/{MODEL}/run"
INPUTS = {
    "calculation": "present_value",
    "rate": 0.05,
    "periods": 10,
    "future_value": 100,
}
OTHER = {**INPUTS, "periods": 11}


def _count_runs(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """Record each task the app's pool is given, by target."""
    pool = service_of(api).pool
    submitted: list[str] = []
    original = pool.submit

    async def counting(task: Task) -> Outcome:
        submitted.append(task.target)
        outcome: Outcome = await original(task)
        return outcome

    monkeypatch.setattr(pool, "submit", counting)
    return submitted


def test_a_get_run_carries_its_tag_and_is_served_again_from_memory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = pyeconomics.run(MODEL, INPUTS)
    with client() as api:
        runs = _count_runs(api, monkeypatch)
        first = api.get(RUN, params={"inputs": encode(INPUTS)})
        again = api.get(RUN, params={"inputs": encode(INPUTS)})
    assert first.content == again.content == canonical_bytes(result)
    for response in (first, again):
        assert response.headers["etag"] == etag(result)
        assert response.headers["etag"].startswith('W/"')
        assert response.headers["cache-control"] == DATA_FREE_CONTROL
    assert "age" not in first.headers
    assert int(again.headers["age"]) >= 0
    assert runs == [MODEL]


def test_a_matching_if_none_match_is_304_with_no_body() -> None:
    tag = etag(pyeconomics.run(MODEL, INPUTS))
    with client() as api:
        query = {"inputs": encode(INPUTS)}
        unseen = api.get(RUN, params=query, headers={"If-None-Match": tag})
        cached = api.get(RUN, params=query, headers={"If-None-Match": f'"x", {tag}'})
        star = api.get(RUN, params=query, headers={"If-None-Match": "*"})
        other = api.get(RUN, params=query, headers={"If-None-Match": 'W/"nope"'})
    for response in (unseen, cached, star):
        assert response.status_code == 304
        assert response.content == b""
        assert response.headers["etag"] == tag
        assert response.headers["cache-control"] == DATA_FREE_CONTROL
    assert other.status_code == 200
    assert other.headers["etag"] == tag


def test_a_post_run_is_no_store_and_never_cached() -> None:
    with client() as api:
        cache = service_of(api).cache
        posted = [api.post(RUN, content=canonical_json(i)) for i in (INPUTS, OTHER)]
        assert len(cache) == 0
        api.get(RUN, params={"inputs": encode(INPUTS)})
        assert len(cache) == 1
        api.post(RUN, content=canonical_json(OTHER))
        assert len(cache) == 1
    for response in posted:
        assert response.status_code == 200
        assert response.headers["cache-control"] == NO_STORE
        assert "etag" not in response.headers


def test_a_problem_is_no_store_and_never_cached() -> None:
    with client() as api:
        bad = api.get(RUN, params={"inputs": encode({**INPUTS, "rate": "five"})})
        undecodable = api.get(RUN, params={"inputs": "e"})
        not_json = api.get(RUN, params={"inputs": "ew"})  # the text "{"
        assert len(service_of(api).cache) == 0
    for response in (bad, undecodable, not_json):
        assert response.status_code == 422
        assert response.headers["cache-control"] == NO_STORE
        assert "etag" not in response.headers
        problem(response)


def test_each_format_is_cached_under_its_own_key() -> None:
    with client() as api:
        csv = api.get(RUN, params={"inputs": encode(INPUTS), "format": "csv"})
        json_ = api.get(RUN, params={"inputs": encode(INPUTS)})
        csv_again = api.get(RUN, params={"inputs": encode(INPUTS), "format": "csv"})
        assert len(service_of(api).cache) == 2
    assert csv.content == csv_again.content
    assert csv.headers["content-type"].startswith("text/csv")
    assert (
        csv_again.headers["content-disposition"] == csv.headers["content-disposition"]
    )
    assert json_.headers["etag"] == csv.headers["etag"]


def test_a_bound_run_on_hosted_safe_data_is_kept_for_five_minutes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from server_support import use_providers  # noqa: PLC0415

    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    use_providers(monkeypatch, bs.bls(), bs.fred())
    path = "/v1/models/macro.toy_unemployment/run"
    with client() as api:
        latest = api.get(path, params={"vintage": "latest", "inputs": encode({})})
        assert len(service_of(api).cache) == 1
        # A past date reads FRED's vintages: library-only, and storage forbidden.
        past = api.get(path, params={"as_of": "2024-03-20", "inputs": encode({})})
        assert len(service_of(api).cache) == 1
    assert latest.status_code == past.status_code == 200
    assert latest.headers["cache-control"] == BOUND_CONTROL
    (record,) = past.json()["manifest"]["data_sources"]
    assert record["provider"] == "fred"
    assert past.headers["cache-control"] == NO_STORE
    assert past.headers["etag"].startswith('W/"')


def test_the_cache_keeps_its_bounds() -> None:
    first, second, third = (encode({**INPUTS, "periods": n}) for n in (10, 11, 12))
    with client(cache_entries=2) as api:
        cache = service_of(api).cache
        for inputs in (first, second, third):
            api.get(RUN, params={"inputs": inputs})
        assert len(cache) == 2
    with client(cache_bytes=10) as api:
        api.get(RUN, params={"inputs": first})
        assert len(service_of(api).cache) == 0
    with client(cache_entries=0) as api:
        api.get(RUN, params={"inputs": first})
        assert len(service_of(api).cache) == 0


def test_a_bound_runs_data_decides_its_cache_control() -> None:
    from pyeconomics.core.provenance import LicenceClass  # noqa: PLC0415
    from pyeconomics.server.work import _control  # noqa: PLC0415

    def result(*records: tuple[LicenceClass, str]) -> Any:  # noqa: ANN401 - a stub
        sources = tuple(
            SimpleNamespace(licence=licence, provider=provider)
            for licence, provider in records
        )
        return SimpleNamespace(manifest=SimpleNamespace(data_sources=sources))

    hosted, library = LicenceClass.HOSTED_SAFE, LicenceClass.LIBRARY_ONLY
    assert _control(result()) == DATA_FREE_CONTROL
    assert _control(result((hosted, "bls"))) == BOUND_CONTROL
    assert _control(result((hosted, "bls"), (library, "fred"))) == NO_STORE
    assert _control(result((hosted, "no_such_provider"))) == NO_STORE
    # FRED's terms forbid storage, whatever a record says of its licence.
    assert _control(result((hosted, "fred"))) == NO_STORE


# --- the cache itself -----------------------------------------------------------------


def _entry(
    body: bytes = b"{}", control: str = DATA_FREE_CONTROL, at: float = 0.0
) -> Entry:
    return Entry(
        body=body,
        media_type="application/json",
        disposition=None,
        etag='W/"ab"',
        control=control,
        stored=at,
    )


def test_an_entry_expires_at_its_max_age_and_the_oldest_goes_first() -> None:
    now = [0.0]
    cache = RunCache(max_entries=2, max_bytes=100, clock=lambda: now[0])
    cache.put("a", _entry(control=BOUND_CONTROL))
    cache.put("b", _entry(at=0.0))
    now[0] = 299.0
    assert cache.get("a") is not None
    assert cache.age(cache.get("b") or _entry()) == 299
    now[0] = 300.0
    assert cache.get("a") is None  # past five minutes
    assert cache.get("b") is not None
    cache.put("c", _entry())
    cache.put("d", _entry())
    assert (cache.get("b"), len(cache)) == (None, 2)  # least recently used out
    cache.put("big", _entry(body=b"x" * 101))
    assert cache.get("big") is None
    cache.put("c", _entry(body=b"x" * 60))
    cache.put("e", _entry(body=b"y" * 60))
    assert (cache.get("c"), cache.size) == (None, 60)  # bytes bound


@pytest.mark.parametrize(
    ("header", "matches"),
    [
        (None, False),
        ("*", True),
        ('W/"ab"', True),
        ('"ab"', True),
        (' "zz" , W/"ab"', True),
        ('"zz"', False),
        ("ab", False),
        ('W/"ab', False),
        ('"zz", nonsense', False),
    ],
)
def test_if_none_match_compares_weakly(header: str | None, matches: bool) -> None:  # noqa: FBT001
    assert etag_matches(header, 'W/"ab"') is matches


def _key(
    *,
    model_id: str = MODEL,
    model_version: int = 1,
    inputs: dict[str, Any] = INPUTS,
    bind: dict[str, Any] | None = None,
    export_format: str = "json",
) -> str:
    return run_key(model_id, model_version, inputs, bind, export_format)


def test_the_key_holds_everything_that_selects_an_answer() -> None:
    key = _key()
    assert _key(inputs=dict(reversed(INPUTS.items()))) == key
    assert _key(model_version=2) != key
    assert _key(inputs=OTHER) != key
    assert _key(bind={"as_of": "2024-03-20"}) != key
    assert _key(export_format="csv") != key
    assert _key(model_id="foundations.other") != key
    assert (max_age(DATA_FREE_CONTROL), max_age(BOUND_CONTROL), max_age(NO_STORE)) == (
        86400,
        300,
        0,
    )
