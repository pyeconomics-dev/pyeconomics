# src/pyeconomics/exports/spreadsheet.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""XLSX exports through openpyxl's write-only workbook (ADR-0012 decision 6).

The workbook has two sheets:

- ``data``: the header row, then one row per result run, observation or record;
- ``manifest``: every attribution, required notice and terms page first, one
  per row (``attribution``, ``notice``, ``terms`` in the first column), then the
  manifest's fields with their dotted names, then each list of records (the
  data sources) as a table with its own header row.

Every string is written with the string type and the formula escape of the CSV
export (:func:`~pyeconomics.exports.layout.escape_text`), so no cell is ever a
formula; numbers and booleans keep their types (a number written as its shortest
round-trip text, so it reads back equal), a date is its ISO 8601 text
(Excel's dates start in 1900, and data dates go back to 1700) and an array its
canonical JSON. XLSX holds at most 32,767 characters in a cell, so a longer text
is refused rather than cut.

openpyxl writes each sheet to a temporary file of its own (owner-only, in the
system's temporary directory) and deletes it when the workbook is saved, or at
the latest when the process exits; every cell is checked before the workbook is
created, so a refused value leaves no such file.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING, Any, Final, TypeGuard

from pyeconomics.core.errors import InputError
from pyeconomics.exports.layout import cell_text, escape_text

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from pyeconomics.exports.layout import Subject

__all__ = ["MAX_CELL_CHARACTERS", "to_xlsx"]

#: The longest text an XLSX cell holds.
MAX_CELL_CHARACTERS: Final = 32_767
#: The header labels of the texts the data must be shown with.
_PROVENANCE: Final = frozenset({"attribution", "notice", "terms"})


def _prepared(value: object) -> object:
    """Return a cell's value: a number as it is, anything else as escaped text.

    Raises
    ------
    InputError
        For a text longer than a cell holds or with a control character.
    """
    if value is None or isinstance(value, bool | int | float):
        return value
    from openpyxl.cell.cell import ILLEGAL_CHARACTERS_RE  # noqa: PLC0415

    text = escape_text(cell_text(value))
    if len(text) > MAX_CELL_CHARACTERS:
        msg = (
            f"an XLSX cell holds at most {MAX_CELL_CHARACTERS} characters; export "
            "this value as csv, parquet, arrow or json"
        )
        raise InputError(msg)
    if ILLEGAL_CHARACTERS_RE.search(text):
        msg = "a text cell holds a control character, which XLSX cannot store"
        raise InputError(msg)
    return text


def _cell(sheet: Any, value: object) -> object:  # noqa: ANN401 - an openpyxl sheet
    """Return a prepared value for a write-only sheet: text as text, numbers exact."""
    if value is None or isinstance(value, bool):
        return value
    from openpyxl.cell import WriteOnlyCell  # noqa: PLC0415 - loads with the export

    if isinstance(value, str):
        text = WriteOnlyCell(sheet, value=value)
        # openpyxl reads a string starting with "=" as a formula; this one is text.
        text.data_type = "s"
        return text
    # openpyxl writes a number with 16 significant digits ("%.16g"), which loses
    # the last bit of some floats and integers beyond 1e16; a number cell holding
    # its shortest round-trip text reads back equal.
    number: Any = WriteOnlyCell(sheet, value=0)
    number._value = repr(value)  # noqa: SLF001 - the text the writer emits
    return number


def _flatten(
    mapping: Mapping[str, object], prefix: str = ""
) -> Iterator[tuple[str, object]]:
    """Yield a mapping's fields by dotted name; a list of records stays whole."""
    for key, value in mapping.items():
        name = f"{prefix}{key}"
        if isinstance(value, dict):
            yield from _flatten(value, f"{name}.")
        else:
            yield name, value


def _is_records(value: object) -> TypeGuard[list[dict[str, object]]]:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, dict) for item in value)
    )


def _manifest_rows(subject: Subject) -> Iterator[list[object]]:
    """Yield the manifest sheet's rows: provenance, fields, then record tables."""
    provenance: list[list[object]] = [
        [label, text] for label, text in subject.header if label in _PROVENANCE
    ]
    yield from provenance
    tables: list[tuple[str, list[dict[str, object]]]] = []
    fields = list(_flatten(subject.manifest))
    if provenance and fields:
        yield []
    for name, value in fields:
        if _is_records(value):
            tables.append((name, value))
        else:
            yield [name, value]
    for name, records in tables:
        keys: dict[str, None] = {}
        for record in records:
            keys.update(dict.fromkeys(record))
        yield []
        yield [name]
        yield list(keys)
        for record in records:
            yield [record.get(key) for key in keys]


def to_xlsx(subject: Subject) -> bytes:
    """Return a subject as XLSX bytes: its ``data`` and ``manifest`` sheets.

    Raises
    ------
    InputError
        For a text longer than an XLSX cell holds, or with a control character
        XLSX cannot store.
    """
    from openpyxl import Workbook  # noqa: PLC0415 - loads with the export

    # Every cell is checked before the workbook exists: openpyxl spools each
    # sheet to a temporary file, which a refusal half-way would leave behind.
    data_rows = [
        [_prepared(name) for name in subject.columns],
        *(
            [_prepared(value) for value in values]
            for values in zip(*subject.columns.values(), strict=True)
        ),
    ]
    manifest_rows = [[_prepared(v) for v in row] for row in _manifest_rows(subject)]
    workbook = Workbook(write_only=True)
    workbook.properties.creator = f"pyeconomics {subject.version}"
    for title, rows in (("data", data_rows), ("manifest", manifest_rows)):
        sheet = workbook.create_sheet(title)
        for row in rows:
            sheet.append([_cell(sheet, value) for value in row])
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
