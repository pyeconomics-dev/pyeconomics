# tests/data/snapshots/test_snapshot_codec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot layout: names, bounded gzip, provider objects and current.json.

Reading is strict: a name outside ``<run-id>/<provider>.json.gz``, an object that
expands beyond its cap, a frame of another provider, a frame under terms that
keep it out of the snapshot and a malformed ``current.json`` are each refused
(Phase 5 Step 8 security: parsing).
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
from dataclasses import replace
from typing import Any

import pytest
from catalog_support import HOSTED_TERMS, LIBRARY_TERMS
from snapshot_support import WHEN, frame

from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import CachePolicy, Series
from pyeconomics.data.errors import ResponseError
from pyeconomics.data.snapshots import codec


def _fetched(provider: str = "toy", series_id: str = "A", **changes: Any) -> Series:  # noqa: ANN401
    series = frame(provider, series_id)
    fields = {"retrieved_at": WHEN, **changes}
    return replace(series, meta=replace(series.meta, **fields))


def test_run_ids_and_object_names_have_one_form() -> None:
    run = codec.run_id(
        dt.datetime(2026, 11, 2, 18, 30, tzinfo=dt.timezone(dt.timedelta(hours=-5))),
        "0a1b2c3d",
    )
    assert run == "20261102T233000Z-0a1b2c3d"
    assert codec.run_started(run) == dt.datetime(2026, 11, 2, 23, 30, tzinfo=dt.UTC)
    assert codec.parse_object_name(codec.object_name(run, "treasury")) == (
        run,
        "treasury",
    )
    with pytest.raises(ValueError, match="eight lowercase hex"):
        codec.run_id(dt.datetime(2026, 11, 2, tzinfo=dt.UTC), "XYZ")
    with pytest.raises(ResponseError, match="not a snapshot run id"):
        codec.run_started("yesterday")


@pytest.mark.parametrize(
    "name",
    [
        "../current.json",
        "20261102T233000Z-0a1b2c3d/../../etc.json.gz",
        "/abs/20261102T233000Z-0a1b2c3d/treasury.json.gz",
        "20261102T233000Z-0a1b2c3d/Treasury.json.gz",
        "20261102T233000Z-0a1b2c3d\\treasury.json.gz",
        "20261102T233000Z-0a1b2c3d/treasury.json",
        7,
    ],
)
def test_a_name_outside_the_layout_is_refused(name: object) -> None:
    with pytest.raises(ResponseError, match=r"<run-id>/<provider>\.json\.gz"):
        codec.parse_object_name(name)


def test_gzip_round_trips_and_is_deterministic() -> None:
    payload = b'{"a":1}' * 100
    assert codec.compress(payload) == codec.compress(payload)
    assert codec.decompress(codec.compress(payload)) == payload


def test_an_object_that_expands_beyond_its_cap_is_refused() -> None:
    bomb = codec.compress(b"0" * 100_000)
    assert len(bomb) < 1_000
    with pytest.raises(ResponseError, match="expands beyond its cap"):
        codec.decompress(bomb, limit=10_000)


@pytest.mark.parametrize(
    ("data", "problem"),
    [
        (b"not gzip at all", "not gzip data"),
        (codec.compress(b"{}") + b"trailing", "one complete gzip member"),
        (codec.compress(b"{}")[:-6], "one complete gzip member"),
    ],
)
def test_bytes_that_are_not_one_gzip_member_are_refused(
    data: bytes, problem: str
) -> None:
    with pytest.raises(ResponseError, match=problem):
        codec.decompress(data)


def test_an_object_larger_than_its_cap_is_refused_before_expanding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(codec, "MAX_OBJECT_BYTES", 10)
    with pytest.raises(ResponseError, match="larger than its cap"):
        codec.decompress(codec.compress(b"{}" * 50))


def test_a_provider_object_round_trips_its_frames() -> None:
    first, second = _fetched(series_id="A"), _fetched(series_id="B")
    data = codec.encode_object(
        "toy",
        "20261015T233000Z-0000000a",
        {"A": codec.Entry(first), "B": codec.Entry(second, "all")},
    )
    entries = codec.decode_object(data, provider="toy")
    assert entries == {"A": codec.Entry(first), "B": codec.Entry(second, "all")}
    document = json.loads(gzip.decompress(data))
    assert sorted(document) == ["format", "provider", "run", "series"]


@pytest.mark.parametrize(
    ("changes", "problem"),
    [
        ({"terms": LIBRARY_TERMS}, "terms keep out"),
        (
            {"terms": HOSTED_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN)},
            "terms keep out",
        ),
        ({"retrieved_at": None}, "without a retrieval time"),
    ],
)
def test_nothing_its_terms_keep_out_is_written(
    changes: dict[str, Any], problem: str
) -> None:
    with pytest.raises(ResponseError, match=problem):
        codec.encode_object(
            "toy", "20261015T233000Z-0000000a", {"A": codec.Entry(_fetched(**changes))}
        )


def test_another_providers_frame_is_refused_on_both_sides() -> None:
    other = _fetched(provider="else")
    with pytest.raises(ResponseError, match="another provider's frame"):
        codec.encode_object(
            "toy", "20261015T233000Z-0000000a", {"A": codec.Entry(other)}
        )
    data = codec.encode_object(
        "else", "20261015T233000Z-0000000a", {"A": codec.Entry(other)}
    )
    with pytest.raises(ResponseError, match="format-1 object of toy"):
        codec.decode_object(data, provider="toy")


def _object(document: object) -> bytes:
    return codec.compress(canonical_json(document))


def test_a_tampered_object_is_refused_on_reading() -> None:
    good = json.loads(
        gzip.decompress(
            codec.encode_object(
                "toy", "20261015T233000Z-0000000a", {"A": codec.Entry(_fetched())}
            )
        )
    )
    library = json.loads(json.dumps(good))
    library["series"]["A"]["frame"]["meta"]["terms"] = LIBRARY_TERMS.to_dict()
    with pytest.raises(ResponseError, match="terms keep out"):
        codec.decode_object(_object(library), provider="toy")
    for broken in (
        {**good, "extra": 1},
        {**good, "format": 2},
        {**good, "series": []},
        {
            **good,
            "series": {
                "A": {
                    "frame": good["series"]["A"]["frame"],
                    "vintage": "as_of:2020-01-01",
                }
            },
        },
        {**good, "series": {"A": {"frame": {"type": "pickle"}, "vintage": "latest"}}},
        {**good, "series": {"A": {"frame": {"type": "series"}, "vintage": "latest"}}},
    ):
        with pytest.raises(ResponseError):
            codec.decode_object(_object(broken), provider="toy")
    with pytest.raises(ResponseError, match="malformed"):
        codec.decode_object(
            codec.compress(b'{"format": 1, "format": 1}'), provider="toy"
        )


def _manifest() -> codec.Manifest:
    ref = codec.ObjectRef(name="20261015T233000Z-0000000a/toy.json.gz", sha256="a" * 64)
    status = codec.ProviderStatus(
        object=ref,
        previous=None,
        series={
            "A": codec.SeriesStatus(
                last_observation=dt.date(2024, 6, 30), retrieved_at=WHEN
            ),
            "B": codec.SeriesStatus(failure="upstream-unavailable"),
        },
    )
    return codec.Manifest(
        run="20261015T233000Z-0000000a",
        completed_at=WHEN,
        providers={"toy": status},
    )


def test_current_json_round_trips() -> None:
    manifest = _manifest()
    data = codec.encode_manifest(manifest)
    assert codec.decode_manifest(data) == manifest
    assert manifest.names() == {"20261015T233000Z-0000000a/toy.json.gz"}
    document = json.loads(data)
    assert document["providers"]["toy"]["series"]["B"] == {
        "failure": "upstream-unavailable",
        "last_observation": None,
        "retrieved_at": None,
    }


def test_a_malformed_current_json_is_refused() -> None:
    good = json.loads(codec.encode_manifest(_manifest()))
    toy = good["providers"]["toy"]
    cases = [
        {**good, "format": 2},
        {**good, "run": "../x"},
        {**good, "providers": {"Toy": toy}},
        {**good, "providers": {"else": toy}},
        {
            **good,
            "providers": {
                "toy": {**toy, "object": {"name": "../x", "sha256": "a" * 64}}
            },
        },
        {
            **good,
            "providers": {
                "toy": {**toy, "object": {"name": toy["object"]["name"], "sha256": "z"}}
            },
        },
        {**good, "providers": {"toy": {**toy, "failure": "Not A Slug"}}},
        {**good, "completed_at": "2026-10-15T23:30:00"},
        {**good, "providers": []},
    ]
    for broken in cases:
        with pytest.raises(ResponseError):
            codec.decode_manifest(canonical_json(broken))
    with pytest.raises(ResponseError, match="malformed"):
        codec.decode_manifest(b"[1, 2")


def test_a_current_json_larger_than_its_cap_is_refused() -> None:
    with pytest.raises(ResponseError, match="larger than its cap"):
        codec.decode_manifest(b" " * (codec.MAX_CURRENT_BYTES + 1))


def test_a_frame_retrieved_more_than_two_days_ago_is_marked_stale() -> None:
    fetched = _fetched()
    assert codec.stale_note(fetched, WHEN + dt.timedelta(days=2)) is fetched
    stale = codec.stale_note(fetched, WHEN + dt.timedelta(days=2, seconds=1))
    assert stale.meta.notes[0].startswith("stale_snapshot: retrieved 2026-10-15")
    assert codec.stale_note(stale, WHEN + dt.timedelta(days=9)) is stale
    full = replace(
        fetched, meta=replace(fetched.meta, notes=tuple(f"n{i}" for i in range(32)))
    )
    marked = codec.stale_note(full, WHEN + dt.timedelta(days=3))
    assert len(marked.meta.notes) == 32
    assert marked.meta.notes[0].startswith("stale_snapshot")
