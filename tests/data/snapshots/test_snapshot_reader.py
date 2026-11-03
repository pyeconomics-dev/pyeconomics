# tests/data/snapshots/test_snapshot_reader.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot reader: hosted series and bound runs from the daily copy.

With ``PYECONOMICS_SNAPSHOT_DIR`` in hosted mode every fetch is answered from the
snapshot after the licence gate and before any transport: the round trip keeps
the snapshot's retrieval time and marks the record; a series outside the set is
``not-in-snapshot`` (404, exit 7) with the local command; a stale series is
served with ``stale_snapshot``; a bad object is reported and the previous one
served. Without the directory hosted mode fetches per request, as in Phase 4
(Phase 5 Step 8).
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import TYPE_CHECKING

import bound_support as bs
import pytest
from catalog_support import HOSTED_TERMS
from leakcheck import LeakCheck, canary
from scripted import calls_of, registry_of, scripted
from snapshot_support import WHEN, entry, frame, hosted, manifest_of, run, windowed

from pyeconomics.core import run_model
from pyeconomics.data import (
    Capability,
    CredentialError,
    DataProvider,
    DataWarning,
    LicenceClass,
    LicenceError,
    Mode,
    Series,
    SnapshotMissingError,
    Table,
    api,
    bind_model,
    cache,
)
from pyeconomics.data.errors import local_data_command
from pyeconomics.data.snapshots import codec, reader
from pyeconomics.surfaces import budgets, problems

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path

    from pyeconomics.data.cache.policy import Fetched

A = frame("alpha", "A", count=12)
ENTRIES = (entry("alpha", "A"),)
FRESH = WHEN + dt.timedelta(hours=12)


def _alpha(series: Series | Table = A) -> type[DataProvider]:
    return scripted(
        "alpha", {"A": series}, capabilities=(Capability.FETCH, Capability.SEARCH)
    )


def _series(fetched: Fetched) -> Series:
    assert isinstance(fetched.frame, Series)
    return fetched.frame


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    directory = tmp_path / "snapshots"
    directory.mkdir()
    hosted(monkeypatch, directory)
    with reader.override(clock=lambda: FRESH):
        yield directory


def _ticking() -> tuple[list[float], Callable[[], float]]:
    now = [0.0]
    return now, lambda: now[0]


def test_a_series_round_trips_with_the_snapshots_retrieval_time(snapshot: Path) -> None:
    alpha = _alpha()
    run(snapshot, alpha, entries=ENTRIES)
    asked = len(calls_of(alpha))
    fetched = alpha().fetch_with_origin({"series": ("A",)})
    assert len(calls_of(alpha)) == asked
    assert (fetched.frame.index, _series(fetched).values) == (A.index, A.values)
    record = fetched.source()
    assert record.retrieved_at == WHEN
    assert record.warnings == ("served_from_snapshot",)
    assert (record.cache_hit, record.served_offline) == (False, False)


def test_a_window_answers_as_a_live_fetch_does(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alpha = _alpha()
    run(snapshot, alpha, entries=ENTRIES)
    registry = registry_of(alpha)
    start, end = dt.date(2024, 3, 1), dt.date(2024, 9, 30)
    served = api.get("alpha:A", registry=registry, start=start, end=end)
    # The most recent observations of the window, as from a source that filters
    # by date (the scripted one answers its whole series whatever the window).
    recent = api.get(
        "alpha:A", registry=registry, max_observations=4, start=start, end=end
    )
    hosted(monkeypatch, None)
    live = api.get("alpha:A", registry=registry, start=start, end=end)
    assert served.frame == live.frame
    assert served.frame.index[0] == dt.date(2024, 3, 31)
    assert recent.frame.index == (
        dt.date(2024, 6, 30),
        dt.date(2024, 7, 31),
        dt.date(2024, 8, 31),
        dt.date(2024, 9, 30),
    )
    assert served.sources[0].warnings == ("served_from_snapshot",)
    assert live.sources[0].warnings == ()


def test_a_concept_resolves_from_the_snapshot_and_no_aggregator_is_asked(
    snapshot: Path,
) -> None:
    bls, fred = bs.bls(), bs.fred()
    run(snapshot, bls, entries=(entry("bls", "LNS14000000"),))
    resolved = api.get("us.unemployment.rate", registry=registry_of(bls, fred))
    (record,) = resolved.sources
    assert (record.provider, record.concept) == ("bls", "us.unemployment.rate")
    assert record.retrieved_at == WHEN
    assert "served_from_snapshot" in record.warnings
    assert calls_of(fred) == []


def test_a_series_outside_the_set_is_not_in_snapshot_with_the_local_command(
    snapshot: Path,
) -> None:
    alpha = scripted("alpha", {"A": A, "B": frame("alpha", "B")})
    run(snapshot, alpha, entries=ENTRIES)
    with pytest.raises(SnapshotMissingError) as caught:
        api.get("alpha:B", registry=registry_of(alpha))
    problem = problems.problem_for(caught.value)
    assert (problem.slug, problem.status, problem.exit_code) == (
        "not-in-snapshot",
        404,
        7,
    )
    assert local_data_command("alpha:B") in problem.detail
    assert local_data_command("x:y") == budgets.local_data_command("x:y")
    assert [q.series for q in calls_of(alpha)] == [("A",)]


def test_a_concept_none_of_whose_hosted_candidates_is_held_is_not_in_snapshot(
    snapshot: Path,
) -> None:
    bls, fred = bs.bls(), bs.fred()
    other = scripted("alpha", {"A": A})
    run(snapshot, other, entries=ENTRIES)
    with pytest.raises(SnapshotMissingError) as caught:
        api.get("us.unemployment.rate", registry=registry_of(bls, fred))
    assert caught.value.target == "us.unemployment.rate"
    assert "pyeconomics data get us.unemployment.rate" in str(caught.value)
    assert (calls_of(bls), calls_of(fred)) == ([], [])


def test_a_keyed_source_is_served_though_the_service_holds_no_key(
    snapshot: Path,
) -> None:
    with cache.bypass():
        gdp = bs.bea()().fetch({"series": (bs.REAL_GDP,)})
    bea = scripted("bea", {bs.REAL_GDP: gdp}, keyed=True)
    run(snapshot, bea, entries=(entry("bea", bs.REAL_GDP),))
    resolved = api.get("us.output.real_gdp", registry=registry_of(bea))
    assert resolved.sources[0].provider == "bea"
    # Without the snapshot, the same request is passed over for want of a key.
    with cache.bypass(), pytest.raises(CredentialError, match="BEA_API_KEY"):
        api.get("us.output.real_gdp", registry=registry_of(bea), strict=True)


def test_a_series_retrieved_more_than_two_days_ago_is_served_stale(
    snapshot: Path,
) -> None:
    run(snapshot, _alpha(), entries=ENTRIES)
    with reader.override(clock=lambda: WHEN + dt.timedelta(days=3)):
        stale = _alpha()().fetch_with_origin({"series": ("A",)})
    assert stale.source().warnings == ("served_from_snapshot", "stale_snapshot")
    assert stale.frame.meta.notes[0].startswith("stale_snapshot: retrieved 2026-10-15")
    fresh = _alpha()().fetch_with_origin({"series": ("A",)})
    assert fresh.source().warnings == ("served_from_snapshot",)


def _second(snapshot: Path) -> codec.Manifest:
    later = WHEN + dt.timedelta(days=1)
    run(snapshot, _alpha(), entries=ENTRIES)
    run(
        snapshot,
        _alpha(frame("alpha", "A", 12, title="Second")),
        entries=ENTRIES,
        started=later,
        nonce="0000000b",
    )
    return manifest_of(snapshot)


def test_a_bad_object_is_reported_and_the_previous_one_served(
    snapshot: Path, caplog: pytest.LogCaptureFixture
) -> None:
    manifest = _second(snapshot)
    status = manifest.providers["alpha"]
    assert status.object is not None
    assert status.previous is not None
    (snapshot / status.object.name).write_bytes(b"tampered")
    with (
        caplog.at_level(logging.WARNING, logger="pyeconomics.data.snapshots"),
        pytest.warns(DataWarning, match="snapshot_object_rejected"),
    ):
        fetched = _alpha()().fetch_with_origin({"series": ("A",)})
    assert fetched.frame.meta.title == A.meta.title
    assert "SHA-256 differs" in caplog.text
    assert str(snapshot) not in caplog.text


def test_with_no_good_object_the_series_is_refused(snapshot: Path) -> None:
    manifest = _second(snapshot)
    status = manifest.providers["alpha"]
    assert status.object is not None
    assert status.previous is not None
    for ref in (status.object, status.previous):
        (snapshot / ref.name).unlink()
    with (
        pytest.warns(DataWarning, match="snapshot_object_rejected"),
        pytest.raises(SnapshotMissingError),
    ):
        _alpha()().fetch_with_origin({"series": ("A",)})


def test_the_last_good_object_in_memory_outlives_a_bad_current_json(
    snapshot: Path,
) -> None:
    now, monotonic = _ticking()
    with reader.override(monotonic=monotonic):
        with pytest.raises(SnapshotMissingError, match="not in the hosted snapshot"):
            _alpha()().fetch_with_origin({"series": ("A",)})
        run(snapshot, _alpha(), entries=ENTRIES)
        now[0] = 61.0
        assert (
            _series(_alpha()().fetch_with_origin({"series": ("A",)})).values == A.values
        )
        (snapshot / codec.CURRENT).write_bytes(b"{not json")
        now[0] = 122.0
        with pytest.warns(DataWarning, match="snapshot_object_rejected"):
            served = _alpha()().fetch_with_origin({"series": ("A",)})
    assert _series(served).values == A.values


def test_current_json_is_read_again_at_most_once_a_minute(snapshot: Path) -> None:
    now, monotonic = _ticking()
    with reader.override(monotonic=monotonic):
        run(snapshot, _alpha(), entries=ENTRIES)
        assert (
            _alpha()().fetch_with_origin({"series": ("A",)}).frame.meta.title
            == A.meta.title
        )
        second = frame("alpha", "A", 12, title="Second")
        run(
            snapshot,
            _alpha(second),
            entries=ENTRIES,
            nonce="0000000b",
            started=WHEN + dt.timedelta(days=1),
        )
        now[0] = 59.0
        assert (
            _alpha()().fetch_with_origin({"series": ("A",)}).frame.meta.title
            == A.meta.title
        )
        now[0] = 60.0
        assert (
            _alpha()().fetch_with_origin({"series": ("A",)}).frame.meta.title
            == "Second"
        )


def test_a_provider_current_json_no_longer_names_is_never_served(
    snapshot: Path,
) -> None:
    now, monotonic = _ticking()
    with reader.override(monotonic=monotonic):
        run(snapshot, _alpha(), entries=ENTRIES)
        _alpha()().fetch_with_origin({"series": ("A",)})
        beta = scripted("beta", {"C": frame("beta", "C")})
        run(snapshot, beta, entries=(entry("beta", "C"),), nonce="0000000b")
        now[0] = 61.0
        with pytest.raises(SnapshotMissingError):
            _alpha()().fetch_with_origin({"series": ("A",)})


def test_a_kept_vintage_set_answers_a_real_time_request(snapshot: Path) -> None:
    vintaged = bs._unemployment("vint", vintaged=True, terms=HOSTED_TERMS)  # noqa: SLF001
    vint = scripted(
        "vint",
        {"UNRATE": vintaged},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    run(snapshot, vint, entries=(entry("vint", "UNRATE", vintage="all"),))
    as_of = vint().fetch_with_origin(
        {"series": ("UNRATE",), "vintage": "as_of:2024-03-15"}
    )
    assert isinstance(as_of.frame, Series)
    assert as_of.frame.values[:2] == (0.038, 0.039)
    latest = vint().fetch_with_origin({"series": ("UNRATE",)})
    assert isinstance(latest.frame, Series)
    assert latest.frame.values[:2] == (0.038, 0.040)


def test_a_series_kept_at_its_latest_refuses_a_past_vintage(snapshot: Path) -> None:
    vintaged = bs._unemployment("vint", vintaged=True, terms=HOSTED_TERMS)  # noqa: SLF001
    vint = scripted(
        "vint",
        {"UNRATE": vintaged},
        capabilities=(Capability.FETCH, Capability.VINTAGES),
    )
    run(snapshot, vint, entries=(entry("vint", "UNRATE"),))
    with pytest.raises(SnapshotMissingError, match="keeps its latest data"):
        vint().fetch_with_origin({"series": ("UNRATE",), "vintage": "as_of:2024-03-15"})


def test_a_window_before_the_history_a_windowed_series_holds_is_refused(
    snapshot: Path,
) -> None:
    long = frame("alpha", "A", 81, first=(2020, 1))
    run(
        snapshot,
        windowed("alpha", {"A": long}),
        entries=(entry("alpha", "A", start=dt.date(2020, 1, 1)),),
    )
    alpha = windowed("alpha", {"A": long})
    with pytest.raises(SnapshotMissingError, match="holds it from 2025-10-31"):
        alpha().fetch_with_origin(
            {"series": ("A",), "start": "2021-01-01", "end": "2021-12-31"}
        )
    served = alpha().fetch_with_origin(
        {"series": ("A",), "start": "2025-01-01", "end": "2026-01-31"}
    )
    assert served.frame.index[0] == dt.date(2025, 10, 31)


def test_the_snapshot_answers_fetches_only(snapshot: Path) -> None:
    run(snapshot, _alpha(), entries=ENTRIES)
    with pytest.raises(SnapshotMissingError, match="pyeconomics data search"):
        _alpha()().search("rate")
    with pytest.raises(SnapshotMissingError, match="one plain series"):
        scripted("alpha", {"A": A, "B": A})().fetch_with_origin({"series": ("A", "B")})


@pytest.mark.usefixtures("snapshot")
def test_the_licence_gate_runs_before_the_snapshot() -> None:
    library = scripted(
        "libre", {"L": frame("libre", "L")}, licence=LicenceClass.LIBRARY_ONLY
    )
    with pytest.raises(LicenceError):
        library().fetch_with_origin({"series": ("L",)})
    assert calls_of(library) == []


def test_without_the_directory_hosted_mode_fetches_per_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    alpha = _alpha()
    hosted(monkeypatch, None)
    assert not reader.active()
    alpha().fetch_with_origin({"series": ("A",)})
    assert len(calls_of(alpha)) == 1
    hosted(monkeypatch, tmp_path)
    assert reader.active()
    with cache.bypass():
        assert not reader.active()
    monkeypatch.setenv("PYECONOMICS_MODE", "library")
    from pyeconomics.data import config  # noqa: PLC0415

    config.reset()
    assert not reader.active()
    assert reader.lookup(alpha.info, alpha.query_type(series=("A",))) is None


def test_a_hosted_bound_run_records_the_snapshots_retrieval_times(
    snapshot: Path,
) -> None:
    bls, fred = bs.bls(), bs.fred()
    run(snapshot, bls, entries=(entry("bls", "LNS14000000"),))
    bound = bind_model(
        bs.unemployment, registry=registry_of(bls, fred), mode=Mode.HOSTED
    )
    (record,) = bound.sources
    assert record.retrieved_at == WHEN
    assert "served_from_snapshot" in record.warnings
    result = run_model(bs.unemployment, bound)
    assert result.manifest.data_sources == bound.sources
    assert result.manifest.data_sources[0].retrieved_at == WHEN
    assert calls_of(fred) == []


def test_no_key_reaches_a_refusal_or_a_log(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = canary("alpha")
    monkeypatch.setenv("ALPHA_API_KEY", key.value)
    alpha = scripted("alpha", {"A": A}, keyed=True)
    run(snapshot, alpha, entries=ENTRIES)
    check = LeakCheck(key)
    with check.logs(), check.warnings():
        served = api.get("alpha:A", registry=registry_of(alpha))
        try:
            api.get("alpha:Z", registry=registry_of(alpha))
        except SnapshotMissingError as error:
            check.exception(error)
            check.add("problem", problems.problem_for(error).to_json())
    check.add("record", str(served.sources[0].to_dict()))
    check.assert_clean()
