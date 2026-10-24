# tests/cli/test_cli_exports.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The export formats, --bundle, --batch and bundle check on the command line (Step 5).

``models run`` and ``data get`` must write :func:`pyeconomics.exports.export`'s
bytes for each export format; a binary format is refused on a terminal and,
without pyarrow, Parquet and Arrow exit 8 naming it. ``--bundle`` writes the
bundle ``write_bundle`` writes; ``--batch`` runs a CSV or JSON Lines file
through ``invoke_batch``; ``bundle check`` verifies a bundle and exits 3 on a bad
one.
"""

from __future__ import annotations

import datetime as dt
import io
import json
import sys
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from cli_support import FakeTerminal, cli, install_world
from export_support import arrow_table

from pyeconomics import data
from pyeconomics.core.canonical import canonical_json
from pyeconomics.data import cache
from pyeconomics.exports import check_bundle, export_bytes
from pyeconomics.exports.bundle import bundle_bytes, bundle_members
from pyeconomics.surfaces import codec
from pyeconomics.surfaces.invoke import BindRequest, invoke, invoke_batch

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

TIME_VALUE = "foundations.time_value"
PV_ARGS = (
    "--calculation",
    "present_value",
    "--rate",
    "0.05",
    "--periods",
    "10",
    "--future-value",
    "100",
)
PV = {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}


@pytest.mark.parametrize("export_format", ["csv", "parquet", "arrow"])
def test_models_run_writes_the_export_of_its_result(export_format: str) -> None:
    outcome = cli("models", "run", TIME_VALUE, *PV_ARGS, "--format", export_format)
    assert (outcome.code, outcome.stderr) == (0, "")
    assert outcome.stdout == export_bytes(invoke(TIME_VALUE, PV), export_format)


def test_models_run_writes_xlsx_to_out(tmp_path: Path) -> None:
    path = tmp_path / "pv.xlsx"
    outcome = cli(
        "models", "run", TIME_VALUE, *PV_ARGS, "--format", "xlsx", "--out", str(path)
    )
    assert (outcome.code, outcome.stdout) == (0, b"")
    frame = pd.read_excel(path, sheet_name="data")
    assert (
        frame.loc[0, "outputs.present_value"]
        == invoke(TIME_VALUE, PV).outputs.present_value
    )


def test_parquet_piped_into_pandas_gives_the_python_apis_values_and_manifest() -> None:
    outcome = cli("models", "run", TIME_VALUE, *PV_ARGS, "--format", "parquet")
    assert outcome.code == 0
    frame = pd.read_parquet(io.BytesIO(outcome.stdout))
    expected = invoke(TIME_VALUE, PV)
    pd.testing.assert_frame_equal(frame, expected.to_pandas(), check_dtype=False)
    metadata = arrow_table(outcome.stdout, "parquet").schema.metadata
    assert json.loads(metadata[b"pyeconomics.manifest"]) == expected.manifest.to_dict()


@pytest.mark.parametrize("export_format", ["xlsx", "parquet", "arrow"])
def test_a_binary_format_is_refused_on_a_terminal(export_format: str) -> None:
    outcome = cli(
        "models",
        "run",
        TIME_VALUE,
        *PV_ARGS,
        "--format",
        export_format,
        terminal=FakeTerminal(),
    )
    assert outcome.code == 2
    assert outcome.stderr.startswith(f"usage-error: --format {export_format} writes")
    assert outcome.stdout == b""


def test_csv_may_be_written_to_a_terminal() -> None:
    outcome = cli(
        "models",
        "run",
        TIME_VALUE,
        *PV_ARGS,
        "--format",
        "csv",
        terminal=FakeTerminal(),
    )
    assert outcome.code == 0
    assert outcome.stdout.startswith(b"# pyeconomics: ")


@pytest.mark.parametrize("export_format", ["parquet", "arrow"])
def test_without_pyarrow_the_arrow_formats_exit_8_naming_it(
    export_format: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(sys.modules, "pyarrow", None)
    outcome = cli("models", "run", TIME_VALUE, *PV_ARGS, "--format", export_format)
    assert outcome.code == 8
    assert outcome.stderr.startswith("missing-extra: ")
    assert "pyarrow" in outcome.stderr


# --- bundles ----------------------------------------------------------------------


def test_bundle_writes_the_runs_bundle_beside_its_output(tmp_path: Path) -> None:
    path = tmp_path / "pv.zip"
    outcome = cli("models", "run", TIME_VALUE, *PV_ARGS, "--bundle", str(path))
    assert outcome.code == 0
    result = invoke(TIME_VALUE, PV)
    assert outcome.stdout == result.to_json().encode() + b"\n"
    assert path.read_bytes() == bundle_bytes(bundle_members(result))


def test_a_bundle_that_cannot_be_written_is_invalid_input(tmp_path: Path) -> None:
    outcome = cli("models", "run", TIME_VALUE, *PV_ARGS, "--bundle", str(tmp_path))
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: the --bundle file cannot be")
    assert str(tmp_path) not in outcome.stderr


def test_bundle_check_reports_a_valid_bundle(tmp_path: Path) -> None:
    path = tmp_path / "pv.zip"
    path.write_bytes(bundle_bytes(bundle_members(invoke(TIME_VALUE, PV))))
    outcome = cli("bundle", "check", str(path))
    assert outcome.code == 0, outcome.stderr
    lines = outcome.text.splitlines()
    assert any(line.startswith("result_sha256") for line in lines)
    assert "reproduce.py is a program" in outcome.text
    as_json = cli("bundle", "check", str(path), "--format", "json")
    assert json.loads(as_json.stdout) == check_bundle(path).to_dict()


def test_bundle_check_refuses_a_bad_bundle_with_exit_3(tmp_path: Path) -> None:
    members = bundle_members(invoke(TIME_VALUE, PV))
    members["inputs.json"] = b'{"rate":1}'
    path = tmp_path / "bad.zip"
    path.write_bytes(bundle_bytes(members))
    outcome = cli("bundle", "check", str(path))
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: the bundle is not valid: ")


# --- batches ----------------------------------------------------------------------


def test_a_csv_batch_runs_each_row_as_invoke_batch_does(tmp_path: Path) -> None:
    path = tmp_path / "rows.csv"
    path.write_bytes(
        b"calculation,rate,periods,future_value\n"
        b"present_value,0.05,10,100\n"
        b"present_value,0.06,10,\n"
    )
    outcome = cli("models", "run", TIME_VALUE, "--batch", str(path))
    assert outcome.code == 0, outcome.stderr
    expected = invoke_batch(
        TIME_VALUE,
        [PV, {"calculation": "present_value", "rate": 0.06, "periods": 10}],
    )
    assert outcome.stdout == export_bytes(expected, "json") + b"\n"


def test_a_json_lines_batch_from_standard_input_writes_csv() -> None:
    lines = [canonical_json(PV), canonical_json({**PV, "rate": 0.06})]
    outcome = cli(
        "models",
        "run",
        TIME_VALUE,
        "--batch",
        "-",
        "--format",
        "csv",
        stdin=b"\n".join(lines) + b"\n\n",
    )
    assert outcome.code == 0, outcome.stderr
    expected = invoke_batch(TIME_VALUE, [PV, {**PV, "rate": 0.06}])
    assert outcome.stdout == export_bytes(expected, "csv")


def test_a_batch_table_lists_one_row_per_run() -> None:
    stdin = b"rate,periods,future_value,calculation\n0.05,10,100,present_value\n"
    outcome = cli(
        "models", "run", TIME_VALUE, "--batch", "-", "--format", "table", stdin=stdin
    )
    assert outcome.code == 0, outcome.stderr
    assert outcome.text.splitlines()[-1] == "1 rows."


@pytest.mark.parametrize(
    "extra",
    [("--rate", "0.05"), ("--inputs", "-"), ("--bundle", "b.zip"), ("--profile", "x")],
    ids=["field", "inputs", "bundle", "bind"],
)
def test_batch_cannot_be_combined_with_other_inputs(extra: tuple[str, ...]) -> None:
    outcome = cli("models", "run", TIME_VALUE, "--batch", "-", *extra, stdin=b"{}")
    assert outcome.code == 2
    assert outcome.stderr.startswith("usage-error: --batch takes every row's inputs")


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"", "the --batch file holds no rows"),
        (b"rate,rate\n1,2\n", "header row repeats a field"),
        (b"not a field\n1\n", "header row holds a name that is not a field"),
        (b"rate,periods\n0.05\n", "row 0 of the batch has 1 cells for 2 fields"),
        (b'{"rate": 0.05}\n{"rate": 0.05, "rate": 1}\n', "row 1 of the batch:"),
        (b"\xff\xfe", "not UTF-8 text"),
        (b"rate\n" + b"9" * 200_000 + b"\n", "the --batch file is not CSV"),
    ],
    ids=["empty", "repeated", "name", "short", "json-row", "encoding", "field"],
)
def test_a_bad_batch_file_is_invalid_input(content: bytes, message: str) -> None:
    outcome = cli("models", "run", TIME_VALUE, "--batch", "-", stdin=content)
    assert outcome.code == 3
    assert outcome.stderr.startswith("invalid-input: ")
    assert message in outcome.stderr


def test_a_batch_file_that_is_missing_or_too_large_is_refused(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome = cli("models", "run", TIME_VALUE, "--batch", str(tmp_path / "x.csv"))
    assert outcome.code == 3
    assert "the --batch file cannot be read (FileNotFoundError)" in outcome.stderr
    monkeypatch.setattr(codec, "MAX_INPUT_BYTES", 8)
    outcome = cli("models", "run", TIME_VALUE, "--batch", "-", stdin=b"rate\n" * 4)
    assert outcome.code == 3
    assert outcome.stderr.startswith("input-too-large: ")


# --- data get ---------------------------------------------------------------------


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    install_world(monkeypatch)
    with cache.bypass():
        yield


@pytest.mark.usefixtures("world")
@pytest.mark.parametrize("export_format", ["csv", "parquet", "arrow"])
def test_data_get_writes_the_export_of_what_it_resolved(export_format: str) -> None:
    outcome = cli(
        "data",
        "get",
        "us.unemployment.rate",
        "--as-of",
        "2024-03-20",
        "--format",
        export_format,
    )
    assert (outcome.code, outcome.stderr) == (0, "")
    resolved = data.get("us.unemployment.rate", as_of=dt.date(2024, 3, 20))
    assert outcome.stdout == export_bytes(resolved, export_format)


@pytest.mark.usefixtures("world")
def test_data_get_refuses_a_binary_format_on_a_terminal_before_fetching() -> None:
    outcome = cli(
        "data",
        "get",
        "us.unemployment.rate",
        "--format",
        "parquet",
        terminal=FakeTerminal(),
    )
    assert outcome.code == 2


@pytest.mark.usefixtures("world")
def test_a_bound_run_bundles_its_request(tmp_path: Path) -> None:
    path = tmp_path / "bound.zip"
    outcome = cli(
        "models",
        "run",
        "macro.toy_unemployment",
        "--as-of",
        "2024-03-20",
        "--bundle",
        str(path),
    )
    assert outcome.code == 0, outcome.stderr
    request = BindRequest(as_of="2024-03-20")
    result = invoke("macro.toy_unemployment", {}, bind=request)
    assert path.read_bytes() == bundle_bytes(bundle_members(result, request))
    assert check_bundle(path).bound
