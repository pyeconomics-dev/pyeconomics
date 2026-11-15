# src/pyeconomics/data/providers/shiller.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Robert Shiller's monthly US equity data, including nineteenth-century dates."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.data.errors import ResponseError, SeriesNotFoundError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import legacy_spreadsheet, legacy_workbook
from pyeconomics.data.types import ObservationFrequency as F
from pyeconomics.data.types import UnitRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["Shiller"]
#: Each series by its label in the Data sheet's header row, as the file names them
#: (read 2026-11-15). The header is the one row before the first date whose first
#: cell is "Date"; each label must appear in it exactly once, matched after trimming.
#: A file that breaks any of this is refused, never read by position, so a column
#: the source inserts or moves cannot shift a series (issue #324).
_LABELS = {
    "price": "P",
    "dividend": "D",
    "earnings": "E",
    "cpi": "CPI",
    "long_rate": "Rate GS10",
    "cape": "CAPE",
}
_DATE_LABEL = "Date"
_PATH = (
    "/blobby/go/e5e77e0b-59d1-44d9-ab25-4763ac982e53/downloads/"
    "1449043e-a1ed-4e2e-8e9c-7b9a2a064493/ie_data.xls"
)


class Shiller(DataProvider):
    """Long-run price, dividend, earnings, CPI, Treasury rate and CAPE."""

    info = f.info(
        "shiller",
        "Robert Shiller US equity data",
        "https://shillerdata.com",
        "https://shillerdata.com/",
        "Source: Robert J. Shiller.",
        (
            "The data and CAPE Ratio on this spreadsheet were "
            "developed by Robert J. Shiller using various public sources."
        ),
        ("img1.wsimg.com",),
    )
    cases = f.cases("us_equity")

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Fetch the author's current official legacy XLS workbook."""
        if f.single(query, self.info.id) != "us_equity":
            raise SeriesNotFoundError(self.info.id, query.series[0])
        return (Request(host=self.info.hosts[0], path=_PATH, series="us_equity"),)

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Interpret YYYY.MM as a calendar label, never as an Excel serial date."""
        cells = legacy_spreadsheet(responses[0].body, "Data", self.info.id)
        columns = _columns(_header(cells, self.info.id), self.info.id)
        rows = {}
        for row in cells:
            if not _dated(row):
                continue
            year, month = f"{row[0]:.2f}".split(".")
            observed = s.month_end(int(year), int(month))
            rows[observed] = {
                n: f.value(
                    row[i] if i < len(row) else None,
                    self.info.id,
                    percent=n == "long_rate",
                )
                for n, i in columns.items()
            }
        units = {
            n: UnitRecord(text="Percent", kind=UnitKind.RATE)
            if n == "long_rate"
            else UnitRecord(
                text="CPI index"
                if n == "cpi"
                else "CAPE ratio"
                if n == "cape"
                else "USD",
                currency="USD" if n in {"price", "dividend", "earnings"} else None,
            )
            for n in _LABELS
        }
        return f.table(
            rows,
            units,
            query,
            self.info,
            responses[0],
            F.MONTHLY,
            notes=("revised_data", "source_dating: YYYY.MM monthly label"),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep the file's own header row, with invented prices, ratios and rates."""
        del request
        cells = legacy_spreadsheet(response.body, "Data", self.info.id)
        header = _header(cells, self.info.id)
        _columns(header, self.info.id)
        values = len(header) - 1
        dated = [row for row in cells if _dated(row)]
        rows: list[list[object]] = [list(header)]
        rows += [
            [row[0], *(synthetic_value(seed, i * values + j) for j in range(values))]
            for i, row in enumerate(dated[-3:])
        ]
        return replace(response, body=legacy_workbook("Data", rows))


def _dated(row: Sequence[object]) -> bool:
    """Whether a row holds an observation: a YYYY.MM label from 1700 first."""
    return bool(row) and isinstance(row[0], int | float) and row[0] >= 1700


def _label(cell: object) -> str:
    return cell.strip() if isinstance(cell, str) else ""


def _header(cells: Sequence[Sequence[object]], provider: str) -> Sequence[object]:
    """Return the one row before the first date whose first cell is ``Date``."""
    found = []
    for row in cells:
        if _dated(row):
            break
        if row and _label(row[0]) == _DATE_LABEL:
            found.append(row)
    if len(found) != 1:
        msg = (
            f"{provider}: the Data sheet has {len(found)} header rows starting "
            f"{_DATE_LABEL!r} before its first date, not one; its layout changed"
        )
        raise ResponseError(msg, provider=provider)
    return found[0]


def _columns(header: Sequence[object], provider: str) -> dict[str, int]:
    """Map each series to its column by label, refusing a missing or repeated one."""
    labels = [_label(cell) for cell in header]
    columns = {}
    for name, label in _LABELS.items():
        where = [i for i, text in enumerate(labels) if text == label]
        if len(where) != 1:
            msg = (
                f"{provider}: the Data sheet's header has {len(where)} columns "
                f"labelled {label!r}, not one; its layout changed"
            )
            raise ResponseError(msg, provider=provider)
        columns[name] = where[0]
    return columns
