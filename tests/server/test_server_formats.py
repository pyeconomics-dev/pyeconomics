# tests/server/test_server_formats.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``?format=`` downloads and the series route (Phase 4 Step 6).

A run's or a series' download must be the exports' own bytes, with its media
type and an attachment ``Content-Disposition``; a bound run's bundle records its
bind request. An XLSX file records the second it was written in its zip entries
and properties, so two are compared by their sheets' values instead. Parquet
and Arrow without pyarrow answer 501 naming it. The series route answers ``data
get --format json``'s document over the scripted providers, takes slashes in a
provider's series key, refuses a URL as a target and, in hosted mode, refuses a
library-only source with the licence problem.
"""

from __future__ import annotations

import io
import json
import sys
import zipfile

import pytest
from cli_support import install_world
from export_support import xlsx_sheet
from server_support import LOOPBACK_ONLY, client, encode, problem

import pyeconomics
from pyeconomics.core.canonical import canonical_json
from pyeconomics.exports import export_bytes
from pyeconomics.exports.bundle import bundle_bytes, bundle_members
from pyeconomics.server import formats
from pyeconomics.surfaces.documents import data_document
from pyeconomics.surfaces.invoke import BindRequest

pytestmark = LOOPBACK_ONLY

MODEL = "foundations.time_value"
INPUTS = {"calculation": "irr", "cash_flows": [-100, 30, 40, 50]}
PAST = "2024-03-20"


def _same(export_format: str, answered: bytes, exported: bytes) -> bool:
    """Whether a download is the export: its bytes, or an XLSX file's values."""
    if export_format != "xlsx":
        return answered == exported
    return all(
        xlsx_sheet(answered, sheet) == xlsx_sheet(exported, sheet)
        for sheet in ("data", "manifest")
    )


@pytest.mark.parametrize("export_format", ["csv", "xlsx", "parquet", "arrow"])
def test_each_run_format_is_the_exports_bytes(export_format: str) -> None:
    result = pyeconomics.run(MODEL, INPUTS)
    with client() as api:
        response = api.post(
            f"/v1/models/{MODEL}/run",
            params={"format": export_format},
            content=canonical_json(INPUTS),
        )
    assert response.status_code == 200
    assert _same(export_format, response.content, export_bytes(result, export_format))
    assert response.headers["content-type"] == formats.MEDIA_TYPES[export_format]
    extension = formats.EXTENSIONS[export_format]
    assert response.headers["content-disposition"] == (
        f'attachment; filename="{MODEL}.{extension}"'
    )


def test_json_is_the_default_and_shows_inline() -> None:
    with client() as api:
        default = api.post(f"/v1/models/{MODEL}/run", content=canonical_json(INPUTS))
        explicit = api.post(
            f"/v1/models/{MODEL}/run?format=json", content=canonical_json(INPUTS)
        )
    assert default.content == explicit.content
    assert "content-disposition" not in default.headers


def test_a_bundle_is_the_bundles_bytes() -> None:
    result = pyeconomics.run(MODEL, INPUTS)
    with client() as api:
        response = api.get(
            f"/v1/models/{MODEL}/run",
            params={"format": "bundle", "inputs": encode(INPUTS)},
        )
    assert response.content == bundle_bytes(bundle_members(result, None))
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].endswith(f'{MODEL}.zip"')


def test_a_bound_runs_bundle_records_its_bind_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_world(monkeypatch)
    with client() as api:
        response = api.post(
            "/v1/models/macro.toy_unemployment/run",
            params={"format": "bundle", "as_of": PAST},
            content=b'{"weight": 2}',
        )
    assert response.status_code == 200
    members = zipfile.ZipFile(io.BytesIO(response.content))
    recorded = json.loads(members.read("request.json"))
    assert recorded == BindRequest(as_of=PAST).to_dict()


@pytest.mark.parametrize("export_format", ["parquet", "arrow"])
def test_parquet_and_arrow_without_pyarrow_answer_501_naming_it(
    monkeypatch: pytest.MonkeyPatch, export_format: str
) -> None:
    install_world(monkeypatch)
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with client() as api:
        run = api.post(
            "/v1/models/macro.toy_plain/run",
            params={"format": export_format},
            content=b'{"unemployment": 0.04}',
        )
        series = api.get(
            "/v1/series/fred:UNRATE", params={"as_of": PAST, "format": export_format}
        )
    for response in (run, series):
        assert response.status_code == 501
        body = problem(response)
        assert body["type"].endswith("/missing-extra")
        assert "pyarrow" in body["detail"]


# --- the series route ---------------------------------------------------------------


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> None:
    install_world(monkeypatch)


def test_a_series_is_the_data_get_document(world: None) -> None:
    del world
    import datetime as dt  # noqa: PLC0415

    from pyeconomics.data import api as data_api  # noqa: PLC0415
    from pyeconomics.data import cache  # noqa: PLC0415

    with cache.bypass():
        resolved = data_api.get("us.unemployment.rate", start=dt.date(2024, 2, 1))
    with client() as api:
        response = api.get(
            "/v1/series/us.unemployment.rate", params={"start": "2024-02-01"}
        )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.content == canonical_json(data_document(resolved))
    assert response.json()["attributions"]


@pytest.mark.parametrize("export_format", ["csv", "xlsx"])
def test_each_series_format_is_the_exports_bytes(
    world: None, export_format: str
) -> None:
    del world
    import datetime as dt  # noqa: PLC0415

    from pyeconomics.data import api as data_api  # noqa: PLC0415

    resolved = data_api.get("fred:UNRATE", as_of=dt.date.fromisoformat(PAST))
    with client() as api:
        response = api.get(
            "/v1/series/fred:UNRATE", params={"as_of": PAST, "format": export_format}
        )
    assert _same(export_format, response.content, export_bytes(resolved, export_format))
    assert response.headers["content-disposition"] == (
        f'attachment; filename="fred_UNRATE.{formats.EXTENSIONS[export_format]}"'
    )


def test_a_series_key_may_hold_slashes(world: None) -> None:
    del world
    from bound_support import UK_INFLATION  # noqa: PLC0415

    with client() as api:
        response = api.get(f"/v1/series/oecd:{UK_INFLATION}")
    assert response.status_code == 200
    assert response.json()["sources"][0]["series_id"] == UK_INFLATION


@pytest.mark.parametrize(
    ("path", "status", "slug"),
    [
        ("/v1/series/https://api.example.org/v1/data", 422, "invalid-input"),
        ("/v1/series/fred", 422, "invalid-input"),
        ("/v1/series/nowhere:SERIES", 404, "provider-not-found"),
        ("/v1/series/us.unemployment.rate?format=bundle", 422, "invalid-input"),
        ("/v1/series/us.unemployment.rate?start=soon", 422, "invalid-input"),
        ("/v1/series/us.unemployment.rate?api_key=x", 422, "invalid-input"),
    ],
    ids=["url", "provider-only", "provider", "bundle", "date", "key"],
)
def test_a_bad_series_request_is_a_problem(
    world: None, path: str, status: int, slug: str
) -> None:
    del world
    with client() as api:
        response = api.get(path)
    assert response.status_code == status
    assert problem(response)["type"].endswith(f"/{slug}")


def test_hosted_mode_refuses_a_library_only_source(world: None) -> None:
    del world
    with client(mode="hosted") as api:
        response = api.get("/v1/series/fred:UNRATE")
    assert response.status_code == 403
    body = problem(response)
    assert body["type"].endswith("/licence-refused")
    assert body["licence"] == "library-only"
