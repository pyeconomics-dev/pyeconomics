# tests/exports/test_export_escaping.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Formula injection (ROADMAP §5 threat 6): hostile text stays text, numbers numbers.

A text cell that starts with ``=``, ``+``, ``-``, ``@``, a tab or a carriage
return is written with a leading ``'`` in CSV and XLSX; a number is never
escaped; and XLSX stores every string as a string, never a formula. Each file is
read back (pandas, openpyxl, the raw XML) to prove it.
"""

from __future__ import annotations

import dataclasses
import io
import math
import re
import zipfile
from typing import Any

import pytest
from export_support import HOSTILE, NUMBERS, read_csv, xlsx_cells, xlsx_sheet

from pyeconomics.core.errors import InputError
from pyeconomics.exports.delimited import csv_cell, to_csv
from pyeconomics.exports.layout import FORMULA_PREFIXES, Subject, escape_text
from pyeconomics.exports.spreadsheet import MAX_CELL_CHARACTERS, to_xlsx


def hostile(**columns: list[Any]) -> Subject:
    """A subject holding the hostile text beside numbers, with a hostile notice."""
    return Subject(
        kind="records",
        columns={"text": list(HOSTILE), "number": list(NUMBERS), **columns},
        header=(
            ("pyeconomics", "0"),
            ("attribution", "Source: =an agency"),
            ("notice", "-a notice"),
        ),
        attributions=("Source: =an agency", "-a notice"),
        terms=(),
        manifest={"provider": "=evil()", "count": -2},
        document=b"{}",
        version="0",
    )


def escaped(text: str) -> str:
    return f"'{text}" if text[:1] in FORMULA_PREFIXES else text


def test_every_formula_prefix_is_escaped_and_nothing_else() -> None:
    for prefix in ("=", "+", "-", "@", "\t", "\r"):
        assert escape_text(f"{prefix}x") == f"'{prefix}x"
    assert escape_text("x=1") == "x=1"
    assert escape_text("'already") == "'already"
    assert escape_text("") == ""


def test_hostile_csv_text_round_trips_through_pandas_exactly() -> None:
    data = to_csv(hostile())
    frame = read_csv(data, keep_default_na=False)
    assert list(frame["text"]) == [escaped(text) for text in HOSTILE]


def test_negative_and_exponent_numbers_stay_numbers_in_csv() -> None:
    data = to_csv(hostile())
    frame = read_csv(data, float_precision="round_trip")
    assert frame["number"].dtype.kind == "f"
    assert list(frame["number"]) == [float(number) for number in NUMBERS]
    assert math.copysign(1.0, frame["number"][6]) == -1.0  # -0.0 kept its sign
    raw = data.decode("utf-8")
    for token in ("-1.5", "1e-07", "-2.5e+20", "6.02e+23", "1e+16", "-42"):
        assert f",{token}\n" in raw, token  # bare: never quoted, never prefixed


def test_every_csv_text_cell_is_quoted() -> None:
    assert csv_cell("plain") == '"plain"'
    assert csv_cell("") == '""'
    assert csv_cell(None) == ""
    assert csv_cell(value=False) == "false"
    with pytest.raises(ValueError, match="finite"):
        csv_cell(math.inf)


def test_the_csv_metadata_block_is_never_read_as_data() -> None:
    data = to_csv(hostile())
    assert data.startswith(b"# pyeconomics: 0\n# attribution: Source: =an agency\n")
    assert len(read_csv(data, keep_default_na=False)) == len(HOSTILE)


def test_a_line_break_in_a_metadata_text_cannot_end_the_block() -> None:
    subject = hostile()
    broken = dataclasses.replace(subject, header=(("notice", "first\nx,y,z\rsecond"),))
    assert to_csv(broken).startswith(b"# notice: first x,y,z second\n")


def test_hostile_xlsx_text_stays_text_and_numbers_stay_numbers() -> None:
    data = to_xlsx(hostile())
    rows = xlsx_sheet(data, "data")
    assert rows[0] == ["text", "number"]
    assert [row[0] for row in rows[1:]] == [escaped(text) for text in HOSTILE]
    numbers = [row[1] for row in rows[1:]]
    assert numbers == list(NUMBERS)
    assert all(isinstance(value, int | float) for value in numbers)


def test_xlsx_numbers_read_back_equal_to_the_last_bit() -> None:
    subject = hostile()
    exact: list[object] = [
        0.1 + 0.2,
        61.391325354075946,
        12_345_678_901_234_567,
        2.0**-1074,
    ]
    precise = dataclasses.replace(subject, columns={"number": exact})
    rows = xlsx_sheet(to_xlsx(precise), "data")
    assert [row[0] for row in rows[1:]] == exact


def test_no_xlsx_cell_is_a_formula_by_type_or_by_xml() -> None:
    data = to_xlsx(hostile())
    cells = xlsx_cells(data)
    assert cells
    types = {cell.data_type for cell in cells if cell.value is not None}
    assert types <= {"s", "n"}, types
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        sheets = [n for n in archive.namelist() if n.startswith("xl/worksheets/")]
        assert len(sheets) == 2
        for name in sheets:
            xml = archive.read(name).decode("utf-8")
            assert not re.search(r"<f[ >]", xml), name


def test_the_manifest_sheet_escapes_its_text_too() -> None:
    rows = xlsx_sheet(to_xlsx(hostile()), "manifest")
    assert rows[:2] == [
        ["attribution", "Source: =an agency"],
        ["notice", "'-a notice"],
    ]
    assert ["provider", "'=evil()"] in rows
    assert ["count", -2] in rows


def test_a_text_longer_than_an_xlsx_cell_is_refused_not_cut() -> None:
    subject = hostile()
    long = dataclasses.replace(
        subject, columns={"text": ["x" * (MAX_CELL_CHARACTERS + 1)]}
    )
    with pytest.raises(InputError, match="32767 characters"):
        to_xlsx(long)


def test_a_control_character_xlsx_cannot_store_is_refused() -> None:
    subject = hostile()
    control = dataclasses.replace(subject, columns={"text": ["bell\x07"]})
    with pytest.raises(InputError, match="control character"):
        to_xlsx(control)
