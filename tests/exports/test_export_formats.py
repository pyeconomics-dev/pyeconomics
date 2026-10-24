# tests/exports/test_export_formats.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every export format, for a result, a batch, a frame and records (Phase 4 Step 5).

Each export is read back as a user would read it (pandas, openpyxl, pyarrow) and
must give the Python API's values, the attributions and notices of the data and
the manifest (ADR-0012 decision 6; ADR-0005 rule 2).
"""

from __future__ import annotations

import csv
import datetime as dt
import enum
import io
import json
from typing import TYPE_CHECKING, Any

import frame_builders as fb
import pytest
from export_support import (
    arrow_metadata,
    arrow_table,
    csv_metadata,
    read_csv,
    xlsx_sheet,
)

from pyeconomics import __version__, run, run_batch
from pyeconomics.core import MissingOptionalDependencyError
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import DataSource, LicenceClass, LlmUse
from pyeconomics.core.results import Result
from pyeconomics.data.records import FigiMapping, Records
from pyeconomics.data.resolver import Resolved
from pyeconomics.exports import FORMATS, export, export_bytes
from pyeconomics.exports.layout import cell_text, subject

if TYPE_CHECKING:
    from pathlib import Path

TIME_VALUE = "foundations.time_value"
IRR = {"calculation": "irr", "cash_flows": [-100, 30, 40, 50]}
PV = {"calculation": "present_value", "rate": 0.05, "periods": 10, "future_value": 100}


def irr() -> Result[Any, Any]:
    return run(TIME_VALUE, IRR)


def sourced() -> Result[Any, Any]:
    """A result whose manifest records two sources, one supplied by the user."""
    result = irr()
    terms = fb.TERMS
    records = (
        DataSource(
            provider="example",
            series_id="EXAMPLE_RATE",
            field="cash_flows",
            licence=terms.licence,
            attribution=terms.attribution,
            notice=terms.notice,
            terms_url=terms.terms_url,
            llm_use=terms.llm_use,
        ),
        DataSource(
            provider="user",
            series_id="supplied",
            field="calculation",
            licence=LicenceClass.USER_SUPPLIED,
            attribution="Supplied by the user.",
            llm_use=LlmUse.ALLOWED,
        ),
    )
    return Result.build(result.model, result.inputs, result.outputs, (), records)


def records() -> Records:
    return Records(
        provider="example",
        terms=fb.TERMS,
        retrieved_at=fb.RETRIEVED,
        rows=(
            FigiMapping(
                identifier_type="TICKER",
                identifier="=EVIL",
                figi="BBG000BLNNH6",
                name="-Negative Corp",
            ),
            FigiMapping(identifier_type="TICKER", identifier="IBM", figi="BBG0001"),
        ),
    )


def resolved() -> Resolved:
    frame = fb.monthly((0.01, None, 0.03))
    record = DataSource(
        provider="example",
        series_id="EXAMPLE_RATE",
        concept="us.example.rate",
        licence=fb.TERMS.licence,
        attribution=fb.TERMS.attribution,
        notice=fb.TERMS.notice,
        terms_url=fb.TERMS.terms_url,
        llm_use=fb.TERMS.llm_use,
    )
    return Resolved(frame=frame, sources=(record,), concept="us.example.rate")


# --- a result ---------------------------------------------------------------------


def test_a_result_reads_back_from_csv_with_its_values_and_header() -> None:
    result = irr()
    data = export_bytes(result, "csv")
    frame = read_csv(data, float_precision="round_trip")
    expected = result.to_pandas()
    assert list(frame.columns) == list(expected.columns)
    assert frame.loc[0, "outputs.irr"] == result.outputs.irr
    (_, row) = csv.reader(data.decode().splitlines()[-2:])
    assert float(row[3]) == result.outputs.irr  # the shortest round-trip text
    assert frame.loc[0, "inputs.cash_flows"] == "[-100,30,40,50]"
    assert frame.loc[0, "result_sha256"] == result.manifest.result_sha256
    assert csv_metadata(data) == [
        ("pyeconomics", result.manifest.package_version),
        ("model", f"{TIME_VALUE} version {result.model_version}"),
        ("inputs_sha256", result.manifest.inputs_sha256),
        ("result_sha256", result.manifest.result_sha256),
    ]
    assert data.endswith(b"\n")
    assert b"\r\n" not in data


def test_the_csv_block_lists_every_attribution_notice_and_terms_page() -> None:
    result = sourced()
    lines = csv_metadata(export_bytes(result, "csv"))
    assert lines[4:] == [
        ("attribution", fb.TERMS.attribution),
        ("notice", fb.TERMS.notice),
        ("terms", fb.TERMS.terms_url),
    ]
    assert result.attributions() == (fb.TERMS.attribution, fb.TERMS.notice)


def test_a_result_reads_back_from_xlsx_with_its_manifest_sheet() -> None:
    result = sourced()
    data = export_bytes(result, "xlsx")
    header, row = xlsx_sheet(data, "data")
    assert header == list(result.to_pandas().columns)
    assert row[header.index("outputs.irr")] == result.outputs.irr
    assert row[header.index("outputs.sign_changes")] == 1
    manifest = xlsx_sheet(data, "manifest")
    assert manifest[:3] == [
        ["attribution", fb.TERMS.attribution],
        ["notice", fb.TERMS.notice],
        ["terms", fb.TERMS.terms_url],
    ]
    fields = {row[0]: row[1] for row in manifest if len(row) > 1 and row[0]}
    assert fields["result_sha256"] == result.manifest.result_sha256
    assert fields["dependencies.numpy"] == result.manifest.dependencies["numpy"]
    assert ["data_sources"] in manifest
    keys = manifest[manifest.index(["data_sources"]) + 1]
    assert "attribution" in keys
    assert "provider" in keys


@pytest.mark.parametrize("export_format", ["parquet", "arrow"])
def test_a_result_reads_back_from_arrow_formats_with_its_metadata(
    export_format: str,
) -> None:
    result = sourced()
    data = export_bytes(result, export_format)
    frame = arrow_table(data, export_format).to_pandas()
    expected = result.to_pandas()
    assert list(frame.columns) == list(expected.columns)
    assert frame.loc[0, "outputs.irr"] == result.outputs.irr
    assert list(frame.loc[0, "inputs.cash_flows"]) == [-100.0, 30.0, 40.0, 50.0]
    metadata = arrow_metadata(data, export_format)
    assert metadata["manifest"] == json.loads(canonical_json(result.manifest.to_dict()))
    assert metadata["attributions"] == list(result.attributions())
    assert metadata["version"] == __version__


def test_a_result_as_json_is_its_canonical_bytes() -> None:
    result = sourced()
    assert export_bytes(result, "json") == result.to_json().encode("utf-8")


# --- a batch, a frame, records ----------------------------------------------------


def test_a_batch_has_one_row_per_run_in_every_format() -> None:
    batch = run_batch(TIME_VALUE, [PV, {**PV, "rate": 0.06}])
    data = export_bytes(batch, "csv")
    frame = read_csv(data)
    assert list(frame["inputs.rate"]) == [0.05, 0.06]
    assert list(frame["result_sha256"]) == [
        result.manifest.result_sha256 for result in batch
    ]
    assert ("rows", "2") in csv_metadata(data)
    assert xlsx_sheet(export_bytes(batch, "xlsx"), "data")[2][1] == 0.06
    metadata = arrow_metadata(export_bytes(batch, "parquet"), "parquet")
    assert [m["result_sha256"] for m in metadata["manifest"]["manifests"]] == list(
        frame["result_sha256"]
    )
    document = json.loads(export_bytes(batch, "json"))
    assert document["results"] == [result.to_dict() for result in batch]
    assert document["attributions"] == []


def test_a_series_exports_its_observations_and_terms() -> None:
    frame = fb.monthly((0.01, None, -0.03))
    data = export_bytes(frame, "csv")
    read = read_csv(data)
    assert list(read.columns) == ["date", "value"]
    assert list(read["date"]) == [day.isoformat() for day in frame.index]
    assert read["value"].isna().tolist() == [False, True, False]
    assert read.loc[2, "value"] == -0.03
    lines = csv_metadata(data)
    assert ("data", "example:EXAMPLE_RATE") in lines
    assert ("attribution", fb.TERMS.attribution) in lines
    assert ("notice", fb.TERMS.notice) in lines
    assert ("terms", fb.TERMS.terms_url) in lines
    document = json.loads(export_bytes(frame, "json"))
    assert document["frame"] == json.loads(frame.canonical_json())
    assert document["attributions"] == [fb.TERMS.attribution, fb.TERMS.notice]


def test_a_real_time_series_keeps_its_periods() -> None:
    frame = fb.history()
    read = read_csv(export_bytes(frame, "csv"))
    assert list(read.columns) == ["date", "realtime_start", "realtime_end", "value"]
    assert read["realtime_end"].isna().tolist() == [False, False, True, False, True]
    table = arrow_table(export_bytes(frame, "arrow"), "arrow").to_pydict()
    assert table["realtime_start"][0] == dt.date(2008, 4, 30)
    assert table["value"] == list(frame.values)


def test_a_table_exports_its_columns_and_column_metadata() -> None:
    frame = fb.two_column_table()
    read = read_csv(export_bytes(frame, "csv"))
    assert list(read.columns) == ["date", "short", "long"]
    metadata = arrow_metadata(export_bytes(frame, "parquet"), "parquet")
    assert [c["name"] for c in metadata["manifest"]["columns"]] == ["short", "long"]
    assert metadata["manifest"]["meta"]["table_id"] == "EXAMPLE_TABLE"
    rows = xlsx_sheet(export_bytes(frame, "xlsx"), "data")
    assert rows[0] == ["date", "short", "long"]
    assert rows[1] == ["2020-01-31", 0.01]  # a missing value is an empty cell
    assert rows[2] == ["2020-02-29", None, 0.05]


def test_a_table_column_named_like_an_index_column_is_refused() -> None:
    frame = fb.two_column_table()
    renamed = type(frame)(
        frame.index,
        (fb.column("date"), fb.column("long")),
        frame.data,
        frame.meta,
    )
    with pytest.raises(InputError, match="index column"):
        export_bytes(renamed, "csv")


def test_what_data_get_resolved_exports_its_source_records() -> None:
    value = resolved()
    document = json.loads(export_bytes(value, "json"))
    assert document["concept"] == "us.example.rate"
    assert document["sources"] == [value.sources[0].to_dict()]
    metadata = arrow_metadata(export_bytes(value, "arrow"), "arrow")
    assert metadata["manifest"]["concept"] == "us.example.rate"
    assert metadata["manifest"]["sources"][0]["provider"] == "example"
    assert metadata["attributions"] == [fb.TERMS.attribution, fb.TERMS.notice]


def test_records_export_one_row_per_record() -> None:
    value = records()
    read = read_csv(export_bytes(value, "csv"))
    assert list(read["identifier"]) == ["'=EVIL", "IBM"]
    assert read.loc[0, "name"] == "'-Negative Corp"
    assert read["name"].isna().tolist() == [False, True]
    document = json.loads(export_bytes(value, "json"))
    assert document["records"]["provider"] == "example"
    metadata = arrow_metadata(export_bytes(value, "parquet"), "parquet")
    assert metadata["manifest"]["terms"]["notice"] == fb.TERMS.notice


# --- the API ----------------------------------------------------------------------


@pytest.mark.parametrize("export_format", FORMATS)
def test_export_writes_a_path_and_a_stream_alike(
    export_format: str, tmp_path: Path
) -> None:
    result = irr()
    path = tmp_path / f"result.{export_format}"
    export(result, export_format, path)
    stream = io.BytesIO()
    export(result, export_format, stream)
    expected = export_bytes(result, export_format)
    if export_format == "xlsx":
        # openpyxl stamps the workbook's modified time; compare the sheets.
        assert xlsx_sheet(path.read_bytes(), "data") == xlsx_sheet(expected, "data")
        assert xlsx_sheet(stream.getvalue(), "data") == xlsx_sheet(expected, "data")
    else:
        assert path.read_bytes() == stream.getvalue() == expected


def test_an_unknown_format_or_value_is_refused() -> None:
    with pytest.raises(InputError, match="the export formats are csv, xlsx"):
        export_bytes(irr(), "yaml")
    with pytest.raises(TypeError, match="not dict"):
        export_bytes({"a": 1}, "csv")


@pytest.mark.parametrize("export_format", ["parquet", "arrow"])
def test_arrow_formats_without_pyarrow_name_it(
    export_format: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(__import__("sys").modules, "pyarrow", None)
    with pytest.raises(MissingOptionalDependencyError) as caught:
        export_bytes(irr(), export_format)
    assert caught.value.package == "pyarrow"


class Kind(enum.Enum):
    """An enum whose values are not text."""

    ONE = 1


def test_cell_text_spells_dates_enums_and_arrays_as_json() -> None:
    assert cell_text(dt.date(2024, 3, 31)) == "2024-03-31"
    assert cell_text(LicenceClass.HOSTED_SAFE) == "hosted-safe"
    assert cell_text(Kind.ONE) == "1"
    assert cell_text([1.0, None]) == "[1,null]"
    assert subject(irr()).rows == 1
