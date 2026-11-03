# tests/data/snapshots/test_snapshot_writer.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The snapshot job: per-provider objects, current.json last, failures kept.

A run over scripted providers into a temporary directory writes one object per
provider under its run id and ``current.json`` last; a failed series keeps its
last good frame and a failed provider its last good object, each marked with
the problem slug; nothing library-only, storage-forbidden or secret is written;
old runs are pruned; and the heartbeat goes through the transport to its one
host (Phase 5 Step 8; ADR-0013 decisions 6 and 15).
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import gzip
import logging
from typing import TYPE_CHECKING, Any

import pytest
from catalog_support import HOSTED_TERMS
from leakcheck import LeakCheck, canary
from scripted import calls_of, scripted
from snapshot_support import (
    HEARTBEAT_URL,
    STARTED,
    WHEN,
    HeartbeatTransport,
    entry,
    forbidding,
    frame,
    hosted,
    manifest_of,
    object_of,
    run,
    windowed,
)

from pyeconomics.core import errors as core_errors
from pyeconomics.data import (
    CachePolicy,
    LicenceClass,
    SeriesNotFoundError,
    TransportError,
    errors,
    redaction,
)
from pyeconomics.data.errors import ConfigError
from pyeconomics.data.snapshots import __main__ as entry_point
from pyeconomics.data.snapshots import codec, writer
from pyeconomics.data.transport import files
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.surfaces import problems

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from pyeconomics.data import DataProvider, Query

A, B, C = (frame("alpha", "A"), frame("alpha", "B"), frame("beta", "C"))
ENTRIES = (entry("alpha", "A"), entry("alpha", "B"), entry("beta", "C"))


def _providers(
    **failures: Exception,
) -> tuple[type[DataProvider], type[DataProvider]]:
    alpha = scripted("alpha", {"A": failures.get("A", A), "B": failures.get("B", B)})
    beta = scripted("beta", {"C": failures.get("C", C)})
    return alpha, beta


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "snapshots"
    directory.mkdir()
    hosted(monkeypatch, directory)
    return directory


def test_the_writer_runs_only_in_hosted_mode_with_a_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(ConfigError, match="hosted mode"):
        writer.write(tmp_path)
    hosted(monkeypatch, None)
    with pytest.raises(ConfigError, match="PYECONOMICS_SNAPSHOT_DIR"):
        writer.write()


def test_a_run_writes_each_providers_object_then_current_json(snapshot: Path) -> None:
    report = run(snapshot, *_providers(), entries=ENTRIES)
    assert report.ok
    assert report.run == "20261015T233000Z-0000000a"
    assert (report.succeeded, report.failed) == (("alpha", "beta"), ())
    assert (report.series_written, report.series_failed) == (3, 0)
    assert report.heartbeat == "not_configured"
    files_written = sorted(
        p.relative_to(snapshot).as_posix() for p in snapshot.rglob("*")
    )
    assert files_written == [
        "20261015T233000Z-0000000a",
        "20261015T233000Z-0000000a/alpha.json.gz",
        "20261015T233000Z-0000000a/beta.json.gz",
        "current.json",
    ]
    manifest = manifest_of(snapshot)
    assert manifest == report.manifest
    assert manifest.completed_at == STARTED
    alpha = manifest.providers["alpha"]
    assert alpha.object is not None
    data = (snapshot / alpha.object.name).read_bytes()
    assert codec.digest(data) == alpha.object.sha256
    assert set(codec.decode_object(data, provider="alpha")) == {"A", "B"}
    assert alpha.series["A"] == codec.SeriesStatus(
        last_observation=A.index[-1], retrieved_at=WHEN
    )
    assert alpha.previous is None
    assert alpha.failure is None


def test_a_failed_series_keeps_its_last_good_frame_marked_with_its_slug(
    snapshot: Path,
) -> None:
    first = run(snapshot, *_providers(), entries=ENTRIES)
    later = STARTED + dt.timedelta(days=1)
    failing = _providers(
        B=TransportError("alpha could not be reached", provider="alpha")
    )
    report = run(snapshot, *failing, entries=ENTRIES, started=later, nonce="0000000b")
    assert report.ok
    assert (report.series_written, report.series_failed) == (2, 1)
    alpha = manifest_of(snapshot).providers["alpha"]
    assert alpha.failure is None
    assert alpha.series["B"].failure == "upstream-unavailable"
    assert alpha.series["B"].retrieved_at == WHEN
    assert alpha.previous == first.manifest.providers["alpha"].object
    kept = object_of(snapshot, "alpha")["series"]
    assert set(kept) == {"A", "B"}
    assert kept["B"]["frame"]["meta"]["retrieved_at"] == WHEN.isoformat()
    assert kept["B"]["frame"]["values"] == list(B.values)


def test_a_provider_none_of_whose_series_succeeded_keeps_its_last_good_object(
    snapshot: Path,
) -> None:
    first = run(snapshot, *_providers(), entries=ENTRIES)
    down = TransportError("beta could not be reached", provider="beta")
    report = run(
        snapshot,
        *_providers(C=down),
        entries=ENTRIES,
        started=STARTED + dt.timedelta(days=1),
        nonce="0000000b",
    )
    assert (report.succeeded, report.failed) == (("alpha",), ("beta",))
    beta = manifest_of(snapshot).providers["beta"]
    assert beta.object == first.manifest.providers["beta"].object
    assert beta.failure == "upstream-unavailable"
    assert beta.series["C"].failure == "upstream-unavailable"
    assert beta.series["C"].retrieved_at == WHEN
    assert not (snapshot / "20261015T233000Z-0000000b" / "beta.json.gz").exists()


def test_a_provider_that_never_succeeded_is_listed_without_an_object(
    snapshot: Path,
) -> None:
    missing = SeriesNotFoundError("beta", "C")
    report = run(snapshot, *_providers(C=missing), entries=ENTRIES)
    beta = report.manifest.providers["beta"]
    assert (beta.object, beta.failure) == (None, "series-not-found")
    assert beta.series["C"] == codec.SeriesStatus(failure="series-not-found")


def test_the_job_fails_only_when_no_provider_succeeded(snapshot: Path) -> None:
    down = {k: TransportError("down", provider="x") for k in "ABC"}
    report = run(snapshot, *_providers(**down), entries=ENTRIES)
    assert not report.ok
    assert report.failed == ("alpha", "beta")
    assert manifest_of(snapshot).providers["alpha"].object is None


def test_a_library_only_source_is_refused_before_any_request(snapshot: Path) -> None:
    library = scripted(
        "libre", {"L": frame("libre", "L")}, licence=LicenceClass.LIBRARY_ONLY
    )
    report = run(snapshot, library, entries=(entry("libre", "L"),))
    assert calls_of(library) == []
    assert report.manifest.providers["libre"].series["L"].failure == "licence-refused"
    assert not list(snapshot.rglob("*.json.gz"))


def test_a_series_whose_own_terms_forbid_storage_is_never_written(
    snapshot: Path,
) -> None:
    own = frame(
        "alpha", "A", terms=HOSTED_TERMS.with_overrides(cache=CachePolicy.FORBIDDEN)
    )
    alpha = scripted("alpha", {"A": own, "B": B})
    report = run(snapshot, alpha, entries=(entry("alpha", "A"), entry("alpha", "B")))
    assert report.manifest.providers["alpha"].series["A"].failure == "licence-refused"
    assert set(object_of(snapshot, "alpha")["series"]) == {"B"}


def test_a_source_whose_terms_forbid_storage_is_never_written(snapshot: Path) -> None:
    source = forbidding("alpha", {"A": A})
    report = run(snapshot, source, entries=(entry("alpha", "A"),))
    assert report.manifest.providers["alpha"].series["A"].failure == "licence-refused"
    assert not list(snapshot.rglob("*.json.gz"))


LONG = frame("alpha", "A", 81, first=(2020, 1))
WINDOWED = (entry("alpha", "A", start=dt.date(2020, 1, 1)),)
NEXT_DAY = STARTED + dt.timedelta(days=1)


def _windows(
    provider: type[DataProvider],
) -> list[tuple[dt.date | None, dt.date | None]]:
    return [(query.start, query.end) for query in calls_of(provider)]


def test_a_whole_series_is_fetched_without_a_window(snapshot: Path) -> None:
    alpha = scripted("alpha", {"A": A})
    run(snapshot, alpha, entries=(entry("alpha", "A"),))
    assert _windows(alpha) == [(None, None)]


def test_a_window_series_starts_with_the_last_year(snapshot: Path) -> None:
    alpha = windowed("alpha", {"A": LONG})
    run(snapshot, alpha, entries=WINDOWED)
    assert _windows(alpha) == [(dt.date(2025, 10, 14), STARTED.date())]
    kept = object_of(snapshot, "alpha")["series"]["A"]
    assert kept["start"] == "2020-01-01"
    assert kept["frame"]["index"][0] == "2025-10-31"


def test_each_run_refreshes_its_end_and_reaches_a_year_further_back(
    snapshot: Path,
) -> None:
    alpha = windowed("alpha", {"A": LONG})
    run(snapshot, alpha, entries=WINDOWED)
    report = run(snapshot, alpha, entries=WINDOWED, started=NEXT_DAY, nonce="0000000b")
    assert report.series_failed == 0
    assert _windows(alpha)[1:] == [
        (dt.date(2026, 8, 16), NEXT_DAY.date()),
        (dt.date(2024, 10, 30), dt.date(2025, 10, 30)),
    ]
    index = object_of(snapshot, "alpha")["series"]["A"]["frame"]["index"]
    assert (index[0], index[-1], len(index)) == ("2024-10-31", "2026-09-30", 24)


def test_a_whole_history_is_only_refreshed(snapshot: Path) -> None:
    alpha = windowed("alpha", {"A": LONG})
    near = (entry("alpha", "A", start=dt.date(2025, 10, 1)),)
    run(snapshot, alpha, entries=near)
    run(snapshot, alpha, entries=near, started=NEXT_DAY, nonce="0000000b")
    assert _windows(alpha)[1:] == [(dt.date(2026, 8, 16), NEXT_DAY.date())]


def test_a_failed_refresh_keeps_the_history_and_a_failed_backfill_is_skipped(
    snapshot: Path,
) -> None:
    alpha = windowed("alpha", {"A": LONG})
    run(snapshot, alpha, entries=WINDOWED)
    down = windowed("alpha", {"A": TransportError("down", provider="alpha")})
    report = run(snapshot, down, entries=WINDOWED, started=NEXT_DAY, nonce="0000000b")
    assert (
        report.manifest.providers["alpha"].series["A"].failure == "upstream-unavailable"
    )

    answering = windowed("alpha", {"A": LONG})

    def parse(self: DataProvider, responses: Sequence[Response], query: Query) -> Any:  # noqa: ANN401
        if query.end is not None and query.end < dt.date(2025, 10, 31):
            msg = "down"
            raise TransportError(msg, provider="alpha")
        return answering.parse(self, responses, query)

    backfill_down = type("BackfillDown", (answering,), {"parse": parse})
    report = run(
        snapshot, backfill_down, entries=WINDOWED, started=NEXT_DAY, nonce="0000000c"
    )
    assert report.series_failed == 0
    index = object_of(snapshot, "alpha")["series"]["A"]["frame"]["index"]
    assert index[0] == "2025-10-31"


def test_a_history_whose_shape_changed_starts_again(snapshot: Path) -> None:
    run(snapshot, windowed("alpha", {"A": LONG}), entries=WINDOWED)
    renamed = frame("alpha", "A", 81, first=(2020, 1), title="Renamed")
    report = run(
        snapshot,
        windowed("alpha", {"A": renamed}),
        entries=WINDOWED,
        started=NEXT_DAY,
        nonce="0000000b",
    )
    assert report.series_failed == 0
    kept = object_of(snapshot, "alpha")["series"]["A"]["frame"]
    assert kept["meta"]["title"] == "Renamed"
    assert kept["index"][0] == "2026-08-31"


def test_old_runs_current_json_no_longer_names_are_pruned(snapshot: Path) -> None:
    run(snapshot, *_providers(), entries=ENTRIES)
    old = snapshot / "20260901T233000Z-00000001"
    old.mkdir()
    (old / "alpha.json.gz").write_bytes(b"old")
    recent = snapshot / "20261001T233000Z-00000002"
    recent.mkdir()
    unrelated = snapshot / "notes"
    unrelated.mkdir()
    report = run(
        snapshot,
        *_providers(),
        entries=ENTRIES,
        started=STARTED + dt.timedelta(days=1),
        nonce="0000000b",
    )
    assert report.pruned == ("20260901T233000Z-00000001",)
    assert not old.exists()
    assert recent.exists()
    assert unrelated.exists()
    assert (snapshot / "20261015T233000Z-0000000a").exists()  # the previous objects


def test_a_run_named_as_previous_is_kept_however_old(snapshot: Path) -> None:
    first = run(snapshot, *_providers(), entries=ENTRIES)
    later = STARTED + dt.timedelta(days=40)
    down = {k: TransportError("down", provider="x") for k in "ABC"}
    report = run(
        snapshot, *_providers(**down), entries=ENTRIES, started=later, nonce="0000000b"
    )
    assert report.pruned == ()
    assert (snapshot / first.run).exists()


def test_the_heartbeat_goes_to_its_one_host_and_says_fail_when_nothing_succeeded(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_SNAPSHOT_HEARTBEAT", HEARTBEAT_URL)
    beats = HeartbeatTransport()
    report = run(snapshot, *_providers(), entries=ENTRIES, transport=beats)
    assert report.heartbeat == "sent"
    ((info, request),) = beats.sent
    assert info is writer.HEARTBEAT
    assert (request.host, request.path) == (
        "incidents.betterstack.com",
        "/api/v1/heartbeat/Tok3nForTestsOnly9",
    )
    assert redaction.scrub_text("Tok3nForTestsOnly9") == redaction.MASK
    down = {k: TransportError("down", provider="x") for k in "ABC"}
    report = run(
        snapshot,
        *_providers(**down),
        entries=ENTRIES,
        transport=beats,
        nonce="0000000b",
    )
    assert report.heartbeat == "failure_sent"
    assert beats.sent[-1][1].path.endswith("/fail")


def test_a_heartbeat_that_fails_never_fails_the_run(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_SNAPSHOT_HEARTBEAT", HEARTBEAT_URL)
    report = run(
        snapshot, *_providers(), entries=ENTRIES, transport=HeartbeatTransport(503)
    )
    assert (report.ok, report.heartbeat) == (True, "failed")

    class Unreachable(HeartbeatTransport):
        def send(self, *_: object, **__: object) -> Response:
            msg = "unreachable"
            raise TransportError(msg, provider="snapshot_heartbeat")

    report = run(
        snapshot,
        *_providers(),
        entries=ENTRIES,
        transport=Unreachable(),
        nonce="0000000b",
    )
    assert (report.ok, report.heartbeat) == (True, "failed")


@pytest.mark.parametrize(
    "url",
    [
        "http://incidents.betterstack.com/api/v1/heartbeat/Tok3nForTestsOnly9",
        "https://uptime.betterstack.com/api/v1/heartbeat/Tok3nForTestsOnly9",
        "https://incidents.betterstack.com:8443/api/v1/heartbeat/Tok3nForTestsOnly9",
        "https://incidents.betterstack.com/api/v1/heartbeat/Tok3nForTestsOnly9?x=1",
        "https://incidents.betterstack.com/api/v2/heartbeats",
        "https://user@incidents.betterstack.com/api/v1/heartbeat/Tok3nForTestsOnly9",
    ],
)
def test_a_malformed_heartbeat_url_is_refused_before_any_fetch(
    url: str, snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PYECONOMICS_SNAPSHOT_HEARTBEAT", url)
    alpha, beta = _providers()
    with pytest.raises(ConfigError, match="PYECONOMICS_SNAPSHOT_HEARTBEAT") as caught:
        run(snapshot, alpha, beta, entries=ENTRIES)
    assert "Tok3n" not in str(caught.value)
    assert calls_of(alpha) == []


def test_no_key_reaches_an_object_current_json_a_log_or_a_problem(
    snapshot: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = canary("alpha")
    monkeypatch.setenv("ALPHA_API_KEY", key.value)
    failing = TransportError(f"alpha refused ?api_key={key.value}", provider="alpha")
    alpha = scripted("alpha", {"A": frame("alpha", "A"), "B": failing}, keyed=True)
    check = LeakCheck(key)
    with check.logs(), check.warnings():
        report = run(
            snapshot, alpha, entries=(entry("alpha", "A"), entry("alpha", "B"))
        )
    for path in snapshot.rglob("*"):
        if path.is_file():
            data = path.read_bytes()
            check.add(
                path.name, gzip.decompress(data) if path.suffix == ".gz" else data
            )
    check.add("summary", str(report.summary()))
    check.add("problem", problems.problem_for(failing).to_json())
    check.assert_clean()
    assert (
        report.manifest.providers["alpha"].series["B"].failure == "upstream-unavailable"
    )


def test_failure_slugs_are_the_error_tables() -> None:
    classes = [
        value
        for module in (core_errors, errors)
        for value in vars(module).values()
        if isinstance(value, type)
        and issubclass(value, core_errors.PyeconomicsError)
        and value.__module__ == module.__name__
    ]
    assert len(classes) >= 20
    for kind in classes:
        error = kind.__new__(kind)
        assert writer.failure_slug(error) == problems.row_for(error).slug, kind.__name__
    assert writer.failure_slug(KeyError("x")) == problems.row_for(KeyError("x")).slug


def test_a_providers_repeated_request_is_sent_once() -> None:
    inner = HeartbeatTransport()
    shared = writer._RunTransport(inner)  # noqa: SLF001 - the run's own transport
    request = Request(host="api.example.org", path="/v1/file")
    first = shared.send(writer.HEARTBEAT, request)
    assert shared.send(writer.HEARTBEAT, request) is first
    assert len(inner.sent) == 1
    failing = writer._RunTransport(HeartbeatTransport(503))  # noqa: SLF001
    failing.send(writer.HEARTBEAT, request)
    failing.send(writer.HEARTBEAT, request)


def test_a_workbooks_sheet_is_read_once_within_a_reuse_block() -> None:
    body = files.workbook({"Data": (("year", "value"), (2024, 1.5))})
    outside = files.spreadsheet(body, "Data", "toy")
    assert files.spreadsheet(body, "Data", "toy") is not outside
    with files.reuse():
        first = files.spreadsheet(body, "Data", "toy")
        with files.reuse():
            assert files.spreadsheet(body, "Data", "toy") is first
    assert first == outside
    assert files.spreadsheet(body, "Data", "toy") is not first


def test_the_entry_point_prints_its_counts_and_exits_by_outcome(
    snapshot: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = run(snapshot, *_providers(), entries=ENTRIES)
    monkeypatch.setattr(writer, "write", lambda: report)
    assert entry_point.main(["write"]) == 0
    out = capsys.readouterr().out
    assert out.startswith('{"failed":[],"heartbeat":"not_configured"')
    failed = dataclasses.replace(report, succeeded=())
    monkeypatch.setattr(writer, "write", lambda: failed)
    assert entry_point.main(["write"]) == 1


def test_the_entry_point_refuses_usage_and_configuration_errors(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    assert entry_point.main([]) == 2
    assert entry_point.main(["write", "--now"]) == 2
    assert (
        "usage: python -m pyeconomics.data.snapshots write" in capsys.readouterr().err
    )

    def refuse() -> writer.Report:
        msg = "the snapshot writer runs in hosted mode (PYECONOMICS_MODE=hosted)"
        raise ConfigError(msg)

    monkeypatch.setattr(writer, "write", refuse)
    with caplog.at_level(logging.ERROR, logger="pyeconomics.data.snapshots"):
        assert entry_point.main(["write"]) == 2
    assert "hosted mode" in caplog.text
