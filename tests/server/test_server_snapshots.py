# tests/server/test_server_snapshots.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The hosted API reading the snapshot (Phase 5 Step 8; ADR-0013 decision 6).

With ``PYECONOMICS_SNAPSHOT_DIR`` set, a hosted series of a real provider answers
from the snapshot, with its retrieval time and ``served_from_snapshot``, while
sockets are disabled, so no source is asked; a series outside the set answers
``not-in-snapshot`` (404) with the local command; and a library-only source is
still refused by the licence gate first (403).
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest
from catalog_support import monthly
from server_support import LOOPBACK_ONLY, client, problem
from snapshot_support import WHEN, hosted

from pyeconomics.data import registry as provider_registry
from pyeconomics.data.snapshots import codec, reader

if TYPE_CHECKING:
    from pathlib import Path

pytestmark = LOOPBACK_ONLY

RUN = "20261015T233000Z-0000000a"


def _snapshot(directory: Path) -> None:
    """Write a snapshot holding Treasury's debt series under Treasury's own terms."""
    terms = provider_registry.installed().provider_class("treasury").info.terms
    debt = monthly(
        [3.1e13 + i * 1e11 for i in range(12)], provider="treasury", series_id="debt"
    )
    debt = replace(debt, meta=replace(debt.meta, terms=terms, retrieved_at=WHEN))
    data = codec.encode_object("treasury", RUN, {"debt": codec.Entry(debt)})
    name = codec.object_name(RUN, "treasury")
    (directory / RUN).mkdir()
    (directory / name).write_bytes(data)
    status = codec.ProviderStatus(
        object=codec.ObjectRef(name=name, sha256=codec.digest(data)),
        series={
            "debt": codec.SeriesStatus(
                last_observation=debt.index[-1], retrieved_at=WHEN
            )
        },
    )
    manifest = codec.Manifest(
        run=RUN, completed_at=WHEN, providers={"treasury": status}
    )
    (directory / codec.CURRENT).write_bytes(codec.encode_manifest(manifest))


@pytest.fixture
def snapshot(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "snapshots"
    directory.mkdir()
    _snapshot(directory)
    hosted(monkeypatch, directory)
    return directory


@pytest.mark.usefixtures("snapshot")
def test_a_hosted_series_answers_from_the_snapshot_without_asking_the_source() -> None:
    fresh = WHEN + dt.timedelta(hours=6)
    with reader.override(clock=lambda: fresh), client(mode="hosted") as api:
        response = api.get("/v1/series/treasury:debt?start=2024-03-01&end=2024-06-30")
    assert response.status_code == 200, response.text
    document = response.json()
    (source,) = document["sources"]
    assert source["provider"] == "treasury"
    assert source["retrieved_at"] == WHEN.isoformat()
    assert source["warnings"] == ["served_from_snapshot"]
    assert any("Treasury" in a for a in document["attributions"])


def test_a_series_outside_the_snapshot_is_404_with_the_local_command(
    snapshot: Path,
) -> None:
    with client(mode="hosted") as api:
        response = api.get("/v1/series/treasury:statement")
    assert response.status_code == 404
    body = problem(response)
    assert body["type"].endswith("/problems/not-in-snapshot")
    assert "pyeconomics data get treasury:statement" in body["detail"]
    assert str(snapshot) not in response.text
    assert response.headers["cache-control"] == "no-store"


@pytest.mark.usefixtures("snapshot")
def test_a_library_only_source_is_refused_before_the_snapshot() -> None:
    with client(mode="hosted") as api:
        response = api.get("/v1/series/fred:UNRATE")
    assert response.status_code == 403
    assert problem(response)["type"].endswith("/problems/licence-refused")
