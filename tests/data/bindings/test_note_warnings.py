# tests/data/bindings/test_note_warnings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Which frame notes become a record's warning codes (Phase 3 Step 12).

``Fetched.source()`` repeats the notes that say something about the whole series a
run read: ``revised_data`` (the source keeps only its current estimates),
``bls_keyless`` (read without a catalog) and ``stale_snapshot`` (a hosted
snapshot series not refreshed for two days, Phase 5 Step 8). Dated notes stay on
the frame. A snapshot's origin adds ``served_from_snapshot``.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

from frame_builders import monthly

from pyeconomics.data.cache.policy import NOTE_WARNINGS, Fetched, Origin

REVISED = "revised_data: the source serves current estimates only"
KEYLESS = "bls_keyless: read through API v1 without a key"
FOOTNOTE = "footnote: P preliminary (2026-08-31, 2026-09-30)"
STALE = "stale_snapshot: retrieved 2026-10-15, more than 2 days before it was served"


def source_of(*notes: str, origin: Origin | None = None) -> tuple[str, ...]:
    frame = monthly((1.0, 2.0, 3.0), notes=notes)
    return Fetched(frame, origin or Origin(), "latest").source().warnings


def test_the_notes_about_the_whole_series_become_warning_codes() -> None:
    assert set(NOTE_WARNINGS) == {"revised_data", "bls_keyless", "stale_snapshot"}
    assert source_of(REVISED) == ("revised_data",)
    assert source_of(KEYLESS, REVISED) == ("bls_keyless", "revised_data")
    assert source_of(STALE) == ("stale_snapshot",)


def test_a_snapshots_origin_marks_the_record_first() -> None:
    origin = Origin(snapshot=True)
    assert source_of(origin=origin) == ("served_from_snapshot",)
    assert source_of(STALE, origin=origin) == ("served_from_snapshot", "stale_snapshot")


def test_a_dated_note_stays_on_the_frame() -> None:
    assert source_of(FOOTNOTE) == ()
    assert source_of(FOOTNOTE, "annotation: x (2026-01-31)", "transformed: yoy") == ()


def test_the_origins_codes_come_first_and_nothing_repeats() -> None:
    origin = Origin(
        cache_hit=True, served_offline=True, warnings=("served_offline", "revised_data")
    )
    assert source_of(REVISED, origin=origin) == ("served_offline", "revised_data")


def test_a_note_with_a_bare_code_counts() -> None:
    assert source_of("revised_data") == ("revised_data",)


def test_a_cached_frames_notes_are_read_the_same_way() -> None:
    frame = replace(monthly((1.0,)), meta=monthly((1.0,)).meta)
    cached = Fetched(frame, Origin(cache_hit=True), "latest")
    assert cached.source().cache_hit
    assert cached.source().retrieved_at == dt.datetime(
        2026, 10, 14, 13, 30, 5, 123456, tzinfo=dt.UTC
    )
