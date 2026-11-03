# tests/web/build_user_data_fixtures.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Write the files the "use my own data" end-to-end tests upload (Phase 5 Step 9).

``web/tests/e2e/user-data.spec.ts`` uploads a CSV and an XLSX to a model page
and proves that nothing but the mapped values leaves the browser. Both files
hold what a hostile or careless file holds:

- a ``cpi`` and an ``earnings`` column of ten valid values, which the test maps
  to ``equity.cape``'s two array fields;
- a ``long`` column of 600 numbers, more than any of the model's fields takes
  (480), which the page must refuse to map;
- formulas (``=SUM(...)``, ``=1+1``, a ``HYPERLINK`` to another origin and a
  reference into an external workbook), which are read as values only, never
  evaluated or followed;
- a cell hyperlink to another origin (in the XLSX) and a ``note`` column
  holding :data:`MARKER`, which must appear in no request.

The XLSX is written by openpyxl, which stores formulas without cached values,
so a reader that reads values only sees those cells empty. Run it again after
changing the files' layout:

    uv run python tests/web/build_user_data_fixtures.py
"""

from __future__ import annotations

import csv
import io
from pathlib import Path
from typing import Final

from openpyxl import Workbook

OUT: Final = Path(__file__).resolve().parents[2] / "web" / "tests" / "e2e" / "fixtures"
#: Text in a column no field maps: it must reach no request.
MARKER: Final = "PRIVATE-MARKER-7c41"
#: The other origin the file's links name: the browser must never ask it.
ELSEWHERE: Final = "https://files.example.org/leak"
CPI: Final = (220, 225, 230, 236, 241, 246, 252, 260, 275, 290)
EARNINGS: Final = (100, 105, 98, 120, 140, 150, 160, 170, 190, 210)
LONG: Final = 600
HEADER: Final = ("cpi", "earnings", "long", "note", "formula")


def rows() -> list[list[object]]:
    """The table both files hold, its header first."""
    table: list[list[object]] = [list(HEADER)]
    for index in range(LONG):
        cpi = CPI[index] if index < len(CPI) else None
        earnings = EARNINGS[index] if index < len(EARNINGS) else None
        note = MARKER if index == 0 else None
        formula = {
            0: "=SUM(A2:A3)",
            1: "=1+1",
            2: f'=HYPERLINK("{ELSEWHERE}","link")',
            3: "='[external.xlsx]Sheet1'!A1",
        }.get(index)
        table.append([cpi, earnings, 1000 + index, note, formula])
    return table


def csv_bytes() -> bytes:
    """The table as CSV, LF line ends."""
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    for row in rows():
        writer.writerow(["" if cell is None else cell for cell in row])
    return buffer.getvalue().encode("utf-8")


def write_xlsx(path: Path) -> None:
    """The table as an XLSX, with a cell hyperlink to another origin."""
    book = Workbook()
    sheet = book.active
    assert sheet is not None
    sheet.title = "data"
    for row in rows():
        sheet.append(row)
    sheet["D3"].hyperlink = ELSEWHERE
    sheet["D3"].value = "see the source"
    book.save(path)


def main() -> None:
    """Write both files into web/tests/e2e/fixtures/."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "user-data.csv").write_bytes(csv_bytes())
    write_xlsx(OUT / "user-data.xlsx")


if __name__ == "__main__":
    main()
