# tests/cli/test_cli_data.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bound runs and ``pyeconomics data`` over the scripted providers (Phase 4 Step 4).

The toy bound models and the scripted providers of
tests/data/bindings/bound_support.py are installed as the registries, with the
cache bypassed, so every command reads the same data a direct call reads and
nothing touches the network. A bound run must print the bytes ``invoke`` gives
for the same bind request and record its data sources; each data command must
print what the data API returns, and its table the attributions below the data.
"""

from __future__ import annotations

import datetime as dt
import json
from typing import TYPE_CHECKING

import pytest
from cli_support import cli, install_world

from pyeconomics import data
from pyeconomics.cli import model_commands
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import Table, cache
from pyeconomics.surfaces.documents import data_document, jsonable
from pyeconomics.surfaces.envelope import canonical_bytes
from pyeconomics.surfaces.invoke import BindRequest, invoke

if TYPE_CHECKING:
    from collections.abc import Iterator

UNEMPLOYMENT = "macro.toy_unemployment"
PAST = "2024-03-20"


@pytest.fixture(autouse=True)
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    install_world(monkeypatch)
    with cache.bypass():
        yield


def test_a_bound_run_prints_the_bytes_of_invoke_and_its_sources() -> None:
    outcome = cli("models", "run", UNEMPLOYMENT, "--as-of", PAST, "--weight", "2")
    assert (outcome.code, outcome.stderr) == (0, "")
    expected = invoke(UNEMPLOYMENT, {"weight": 2.0}, bind=BindRequest(as_of=PAST))
    assert outcome.stdout == canonical_bytes(expected) + b"\n"
    records = json.loads(outcome.stdout)["manifest"]["data_sources"]
    assert [record["provider"] for record in records] == ["fred"]


@pytest.mark.parametrize(
    ("arguments", "bind_request"),
    [
        (("--profile", "default"), BindRequest()),
        (("--vintage", "latest"), BindRequest(vintage="latest")),
        (("--profile", "uk"), BindRequest(profile="uk")),
        (
            ("--as-of", PAST, "--concept", "unemployment=us.unemployment.rate"),
            BindRequest(as_of=PAST, concepts={"unemployment": "us.unemployment.rate"}),
        ),
    ],
    ids=["profile", "vintage", "uk", "concept"],
)
def test_every_bind_option_reaches_the_bind(
    arguments: tuple[str, ...], bind_request: BindRequest
) -> None:
    outcome = cli("models", "run", UNEMPLOYMENT, *arguments)
    assert outcome.code == 0
    expected = invoke(UNEMPLOYMENT, {}, bind=bind_request)
    assert outcome.stdout == canonical_bytes(expected) + b"\n"


def test_parameters_reach_the_bind_request() -> None:
    request = model_commands._bind_request(  # noqa: SLF001
        as_of=None,
        vintage=None,
        profile=None,
        concept=(),
        param=("meeting=2024-09",),
    )
    assert request == BindRequest(parameters={"meeting": "2024-09"})
    assert (
        model_commands._bind_request(  # noqa: SLF001
            as_of=None, vintage=None, profile=None, concept=(), param=()
        )
        is None
    )


def test_a_bound_table_shows_the_data_and_its_attribution() -> None:
    outcome = cli("models", "run", UNEMPLOYMENT, "--as-of", PAST, "--format", "table")
    assert outcome.code == 0
    result = invoke(UNEMPLOYMENT, {}, bind=BindRequest(as_of=PAST))
    lines = outcome.text.splitlines()
    assert "Data" in lines
    assert any(line.startswith("unemployment") and "fred" in line for line in lines)
    for text in result.attributions():
        assert text in lines


def test_a_run_without_bindings_refuses_bind_options() -> None:
    outcome = cli("models", "run", "macro.toy_plain", "--profile", "default")
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: ")


# --- data get ----------------------------------------------------------------------


def test_data_get_prints_the_frame_its_sources_and_attributions() -> None:
    outcome = cli("data", "get", "us.unemployment.rate", "--as-of", PAST)
    assert (outcome.code, outcome.stderr) == (0, "")
    resolved = data.get("us.unemployment.rate", as_of=dt.date(2024, 3, 20))
    assert outcome.stdout == canonical_json(data_document(resolved)) + b"\n"
    document = json.loads(outcome.stdout)
    assert document["attributions"]
    assert document["frame"]["type"] == "series"


def test_data_get_reads_a_provider_series_and_a_window() -> None:
    outcome = cli(
        "data", "get", "bls:LNS14000000", "--start", "2024-02-01", "--end", "2024-05-31"
    )
    assert outcome.code == 0
    resolved = data.get(
        "bls:LNS14000000", start=dt.date(2024, 2, 1), end=dt.date(2024, 5, 31)
    )
    assert outcome.stdout == canonical_json(data_document(resolved)) + b"\n"
    assert json.loads(outcome.stdout)["concept"] is None


def test_data_get_as_a_table_ends_with_the_attributions() -> None:
    outcome = cli(
        "data", "get", "us.unemployment.rate", "--as-of", PAST, "--format", "table"
    )
    assert outcome.code == 0
    resolved = data.get("us.unemployment.rate", as_of=dt.date(2024, 3, 20))
    lines = outcome.text.splitlines()
    assert lines[0].startswith(resolved.frame.meta.title)
    assert resolved.frame.index[-1].isoformat() in outcome.text
    assert "Sources" in lines
    assert lines[-1] == resolved.sources[-1].attribution


def test_a_concepts_passed_over_candidates_are_listed() -> None:
    outcome = cli(
        "data", "get", "us.unemployment.rate", "--as-of", PAST, "--format", "table"
    )
    assert outcome.code == 0
    (skip,) = data.get("us.unemployment.rate", as_of=dt.date(2024, 3, 20)).skipped
    assert (
        f"Passed over: {skip.provider} ({skip.reason}: {skip.detail})" in outcome.text
    )


def test_a_table_frame_lists_its_columns() -> None:
    outcome = cli("data", "get", "bea:NIPA/T10106/Q/1", "--format", "table")
    assert outcome.code == 0
    frame = data.get("bea:NIPA/T10106/Q/1").frame
    header = outcome.text.splitlines()[1].split()
    if isinstance(frame, Table):
        assert header[1:] == [column.name for column in frame.columns]
    else:
        assert header == ["Date", "Value"]


@pytest.mark.parametrize(
    ("arguments", "slug"),
    [
        (("not a target",), "invalid-input"),
        (("us.unemployment.rate", "--start", "2024-02-30"), "invalid-input"),
        (("nowhere:SERIES",), "provider-not-found"),
        (("us.nothing.here",), "concept-not-found"),
    ],
    ids=["target", "date", "provider", "concept"],
)
def test_data_get_failures_reach_the_error_table(
    arguments: tuple[str, ...], slug: str
) -> None:
    outcome = cli("data", "get", *arguments)
    assert outcome.code in {3, 5}
    assert outcome.stderr.startswith(f"{slug}: ")


# --- search, describe, vintages, sources --------------------------------------


def test_data_search_finds_concepts_without_asking_a_provider() -> None:
    outcome = cli(
        "data", "search", "unemployment rate", "--limit", "2", "--format", "json"
    )
    assert outcome.code == 0
    found = data.search("unemployment rate", 2)
    assert json.loads(outcome.stdout) == {
        "hits": jsonable(found.hits),
        "skipped": [{"provider": p, "reason": r} for p, r in found.skipped],
    }
    table = cli("data", "search", "unemployment rate", "--limit", "2")
    assert "us.unemployment.rate" in table.text


def test_data_search_lists_the_providers_it_passed_over() -> None:
    outcome = cli("data", "search", "zzzz qqqq", "--limit", "5")
    assert outcome.code == 0
    found = data.search("zzzz qqqq", 5)
    for provider, reason in found.skipped:
        assert f"Not asked: {provider} ({reason})" in outcome.text


@pytest.mark.parametrize("target", ["us.unemployment.rate", "bls"])
def test_data_describe_prints_every_field(target: str) -> None:
    outcome = cli("data", "describe", target, "--format", "json")
    assert outcome.code == 0
    assert outcome.stdout == canonical_json(jsonable(data.describe(target))) + b"\n"
    table = cli("data", "describe", target)
    assert table.code == 0
    assert table.text.splitlines()[0] == target


def test_a_series_its_provider_cannot_describe_is_data_unavailable() -> None:
    outcome = cli("data", "describe", "fred:UNRATE")
    assert outcome.code == 7
    assert outcome.stderr == "data-unavailable: fred does not support describe\n"


def test_data_describe_lays_out_nested_records() -> None:
    lines = cli("data", "describe", "us.unemployment.rate").text.splitlines()
    assert "candidates" in lines
    assert any(line.startswith("concept.title") for line in lines)


def test_data_vintages_lists_the_dates() -> None:
    outcome = cli("data", "vintages", "fred:UNRATE", "--format", "json")
    assert outcome.code == 0
    dates = [day.isoformat() for day in data.vintages("fred:UNRATE")]
    assert json.loads(outcome.stdout) == dates
    table = cli("data", "vintages", "us.unemployment.rate")
    assert f"{len(dates)} vintages of us.unemployment.rate." in table.text
    assert cli("data", "vintages", "fred").code == 3
