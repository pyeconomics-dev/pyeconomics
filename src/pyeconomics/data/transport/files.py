# src/pyeconomics/data/transport/files.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Bounded in-memory spreadsheet readers; formulas are never evaluated."""

from __future__ import annotations

import csv
import datetime as dt
import math
from html import escape
from io import BytesIO, StringIO
from typing import TYPE_CHECKING, Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from pyeconomics.data.errors import ResponseError
from pyeconomics.data.redaction import call_scrubbed

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

MAX_EXPANDED_BYTES = 96 * 1024 * 1024
MAX_MEMBER_BYTES = MAX_EXPANDED_BYTES
MAX_ARCHIVE_ENTRIES = 512
MAX_SHEET_ROWS = 100_100
MAX_SHEET_COLUMNS = 1000
MAX_SHEET_CELLS = 2_000_000


def csv_document(rows: Sequence[Sequence[object]]) -> bytes:
    """Write a small synthetic CSV in memory, quoting names correctly."""
    stream = StringIO(newline="")
    csv.writer(stream, lineterminator="\n").writerows(rows)
    return stream.getvalue().encode("utf-8")


def zip_document(members: Mapping[str, bytes]) -> bytes:
    """Write a deterministic in-memory archive, without following member paths."""
    stream = BytesIO()
    with ZipFile(stream, "w") as zipped:
        for name, body in members.items():
            zipped.writestr(ZipInfo(name), body, compress_type=ZIP_DEFLATED)
    return stream.getvalue()


def legacy_workbook(sheet: str, rows: Sequence[Sequence[object]]) -> bytes:
    """Write a recorder-only XLS fixture in memory; xlwt is development-only."""
    import xlwt  # noqa: PLC0415

    book = xlwt.Workbook()
    target = book.add_sheet(sheet)
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            if value is not None:
                if isinstance(value, dt.date):
                    target.write(i, j, value, xlwt.easyxf(num_format_str="YYYY-MM-DD"))
                else:
                    target.write(i, j, value)
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def archive(
    body: bytes, provider: str, *, selected: frozenset[str] | None = None
) -> dict[str, bytes]:
    """Read a bounded ZIP in memory, refusing encryption and duplicate members."""

    def read() -> dict[str, bytes]:
        if len(body) > MAX_EXPANDED_BYTES:
            msg = "archive exceeds the compressed size cap"
            raise ValueError(msg)
        with ZipFile(BytesIO(body)) as zipped:
            members = zipped.infolist()
            if (
                len(members) > MAX_ARCHIVE_ENTRIES
                or sum(
                    m.file_size
                    for m in members
                    if selected is None or m.filename in selected
                )
                > MAX_EXPANDED_BYTES
                or len({m.filename for m in members}) != len(members)
                or any(
                    m.flag_bits & 1 or m.file_size > MAX_MEMBER_BYTES for m in members
                )
                or any(
                    m.filename.startswith(("/", "\\"))
                    or "\\" in m.filename
                    or ".." in m.filename.split("/")
                    or ":" in m.filename.split("/", 1)[0]
                    for m in members
                )
            ):
                msg = "archive exceeds its bounds or has duplicate or encrypted members"
                raise ValueError(msg)
            return {
                m.filename: zipped.read(m)
                for m in members
                if selected is None or m.filename in selected
            }

    return call_scrubbed(
        read, lambda message: ResponseError(message, provider=provider)
    )


def _dimensions(xml: bytes) -> tuple[int, int]:
    """Bound actual cells, ignoring empty formatting at Excel's last row (PWT)."""
    from defusedxml.ElementTree import iterparse  # noqa: PLC0415
    from openpyxl.utils.cell import coordinate_to_tuple  # noqa: PLC0415

    rows = columns = cells = 0
    for _, element in iterparse(BytesIO(xml), events=("end",), forbid_dtd=True):
        if element.tag.rsplit("}", 1)[-1] != "c":
            continue
        cells += 1
        if cells > MAX_SHEET_CELLS:
            msg = "worksheet exceeds its cell bound"
            raise ValueError(msg)
        if len(element):
            row, column = coordinate_to_tuple(element.attrib["r"])
            rows, columns = max(rows, row), max(columns, column)
            if rows > MAX_SHEET_ROWS or columns > MAX_SHEET_COLUMNS:
                msg = "worksheet exceeds its row or column bound"
                raise ValueError(msg)
        element.clear()
    return rows, columns


def spreadsheet(body: bytes, sheet: str, provider: str) -> tuple[tuple[Any, ...], ...]:
    """Read cached XLSX values only, with XML/ZIP and actual-cell bounds.

    Dimensions are checked from XML before loading values: a worksheet's declared
    dimension may understate actual cells or include a million formatting-only
    rows. Neither affects the bounds or causes large empty allocations.
    """
    members = archive(body, provider)

    def read() -> tuple[tuple[Any, ...], ...]:
        from defusedxml.ElementTree import fromstring  # noqa: PLC0415
        from openpyxl import load_workbook  # noqa: PLC0415
        from openpyxl.xml import DEFUSEDXML  # noqa: PLC0415

        if not DEFUSEDXML:
            msg = "spreadsheet parsing requires defusedxml"
            raise ValueError(msg)
        # Check every XML member, including shared strings and relationships,
        # before openpyxl sees it. DTD and entities are never needed by XLSX.
        for name, content in members.items():
            if name.endswith((".xml", ".rels")):
                fromstring(content, forbid_dtd=True)
        book = load_workbook(
            BytesIO(body), read_only=True, data_only=True, keep_links=False
        )
        try:
            source: Any = book[sheet]  # openpyxl stubs omit the streaming path.
            rows, columns = _dimensions(members[source._worksheet_path])  # noqa: SLF001
            if rows * columns > MAX_SHEET_CELLS:
                msg = "worksheet exceeds its rectangular cell bound"
                raise ValueError(msg)
            if not rows:
                return ()
            source.reset_dimensions()
            return tuple(
                source.iter_rows(max_row=rows, max_col=columns, values_only=True)
            )
        finally:
            book.close()

    return call_scrubbed(
        read, lambda message: ResponseError(message, provider=provider)
    )


def selected_spreadsheet(
    body: bytes, sheet: str, provider: str
) -> tuple[tuple[Any, ...], ...]:
    """Read one sheet from a multi-dataset workbook within the existing limits.

    AQR's daily workbook expands beyond 96 MiB across its many datasets. Only
    the selected sheet and its shared metadata are decompressed; the normal
    reader then enforces the same XML, byte, row, column and cell caps. All
    directory entries still pass the path, encryption and per-member checks.
    """

    def select() -> bytes:
        import re  # noqa: PLC0415

        from defusedxml.ElementTree import fromstring, tostring  # noqa: PLC0415

        required = frozenset(
            {
                "[Content_Types].xml",
                "_rels/.rels",
                "xl/workbook.xml",
                "xl/_rels/workbook.xml.rels",
                "xl/styles.xml",
                "xl/sharedStrings.xml",
            }
        )
        metadata = archive(body, provider, selected=required)
        root = fromstring(metadata["xl/workbook.xml"], forbid_dtd=True)
        sheets = next(e for e in root if e.tag.endswith("}sheets"))
        chosen = next(e for e in sheets if e.attrib.get("name") == sheet)
        relation = chosen.attrib["{" + _REL + "}id"]
        relationships = fromstring(
            metadata["xl/_rels/workbook.xml.rels"], forbid_dtd=True
        )
        target = next(
            e.attrib["Target"] for e in relationships if e.attrib["Id"] == relation
        )
        if not re.fullmatch(r"(?:/xl/)?worksheets/sheet\d+\.xml", target):
            msg = "worksheet relationship has an unsupported target"
            raise ValueError(msg)
        path = target.lstrip("/") if target.startswith("/xl/") else "xl/" + target
        members = archive(body, provider, selected=required | {path})
        for other in list(sheets):
            if other is not chosen:
                sheets.remove(other)
        members["xl/workbook.xml"] = tostring(root)
        return zip_document(members)

    reduced = call_scrubbed(
        select, lambda message: ResponseError(message, provider=provider)
    )
    return spreadsheet(reduced, sheet, provider)


_MAIN = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
_CONTENT = "http://schemas.openxmlformats.org/package/2006/content-types"


def _column(number: int) -> str:
    """Return an Excel column label, without allocating a worksheet."""
    letters = ""
    while number:
        number, letter = divmod(number - 1, 26)
        letters = chr(65 + letter) + letters
    return letters


def _cell(reference: str, value: object) -> str:
    """Encode the scalar types read by openpyxl; no formulas are calculated."""
    if value is None:
        return ""
    if isinstance(value, str):
        if value.startswith("="):
            return f'<c r="{reference}"><f>{escape(value[1:])}</f></c>'
        return (
            f'<c r="{reference}" t="inlineStr"><is>'
            f'<t xml:space="preserve">{escape(value)}</t></is></c>'
        )
    if isinstance(value, dt.date):
        kind, text = "d", value.isoformat()
    elif isinstance(value, bool):
        kind, text = "b", str(int(value))
    elif isinstance(value, int | float) and math.isfinite(value):
        kind, text = "n", str(value)
    else:
        msg = "workbook scalar must be finite numeric, date, text, bool or None"
        raise ValueError(msg)
    return f'<c r="{reference}" t="{kind}"><v>{escape(text)}</v></c>'


def workbook(sheets: Mapping[str, tuple[tuple[object, ...], ...]]) -> bytes:
    """Serialize minimal fixtures in memory, with deterministic ZIP metadata.

    openpyxl's writer uses temporary worksheet files even when saving to BytesIO.
    This small OOXML producer writes scalar cells directly into an in-memory ZIP;
    the production reader still handles the source's full XLSX representation.
    """
    entries = {
        "_rels/.rels": (
            f'<Relationships xmlns="{_PACKAGE}"><Relationship Id="rId1" '
            f'Type="{_REL}/officeDocument" Target="xl/workbook.xml"/>'
            "</Relationships>"
        ),
    }
    names, relationships, overrides = [], [], []
    for i, (name, rows) in enumerate(sheets.items(), 1):
        names.append(
            f'<sheet name="{escape(name, quote=True)}" sheetId="{i}" r:id="rId{i}"/>'
        )
        relationships.append(
            f'<Relationship Id="rId{i}" Type="{_REL}/worksheet" '
            f'Target="/xl/worksheets/sheet{i}.xml"/>'
        )
        overrides.append(
            f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>'
        )
        contents = []
        for row_number, row in enumerate(rows, 1):
            cells = "".join(
                _cell(f"{_column(j)}{row_number}", v) for j, v in enumerate(row, 1)
            )
            contents.append(f'<row r="{row_number}">{cells}</row>')
        entries[f"xl/worksheets/sheet{i}.xml"] = (
            f'<worksheet xmlns="{_MAIN}"><sheetData>{"".join(contents)}'
            "</sheetData></worksheet>"
        )
    entries["xl/workbook.xml"] = (
        f'<workbook xmlns="{_MAIN}" xmlns:r="{_REL}"><sheets>'
        f"{''.join(names)}</sheets></workbook>"
    )
    entries["xl/_rels/workbook.xml.rels"] = (
        f'<Relationships xmlns="{_PACKAGE}">{"".join(relationships)}</Relationships>'
    )
    entries["[Content_Types].xml"] = (
        f'<Types xmlns="{_CONTENT}">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        f"{''.join(overrides)}</Types>"
    )
    stream = BytesIO()
    with ZipFile(stream, "w") as zipped:
        for path, xml in entries.items():
            info = ZipInfo(path)
            info.create_system = 3  # Fixed Unix metadata; nothing is extracted.
            info.external_attr = 0o600 << 16
            zipped.writestr(info, xml.encode("utf-8"), compress_type=ZIP_DEFLATED)
    return stream.getvalue()


def legacy_spreadsheet(
    body: bytes, sheet: str, provider: str
) -> tuple[tuple[Any, ...], ...]:
    """Read XLS in memory; macros and external links are ignored."""

    def read() -> tuple[tuple[Any, ...], ...]:
        import xlrd  # noqa: PLC0415 - lazy legacy file reader

        if len(body) > MAX_EXPANDED_BYTES:
            msg = "legacy workbook exceeds the size cap"
            raise ValueError(msg)
        book = xlrd.open_workbook(file_contents=body, on_demand=True)
        try:
            source = book.sheet_by_name(sheet)
            if (
                source.nrows > MAX_SHEET_ROWS
                or source.ncols > MAX_SHEET_COLUMNS
                or source.nrows * source.ncols > MAX_SHEET_CELLS
            ):
                msg = "legacy worksheet exceeds its row or column bound"
                raise ValueError(msg)
            return tuple(
                tuple(
                    None
                    if cell.ctype == xlrd.XL_CELL_ERROR
                    else xlrd.xldate_as_datetime(cell.value, book.datemode)
                    if cell.ctype == xlrd.XL_CELL_DATE
                    else cell.value
                    for cell in source.row(i)
                )
                for i in range(source.nrows)
            )
        finally:
            book.release_resources()

    return call_scrubbed(
        read, lambda message: ResponseError(message, provider=provider)
    )
