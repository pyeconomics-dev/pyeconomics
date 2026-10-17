# src/pyeconomics/data/providers/shiller.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Robert Shiller's monthly US equity data, including nineteenth-century dates."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.data.errors import SeriesNotFoundError
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
_COLUMNS = {
    "price": 1,
    "dividend": 2,
    "earnings": 3,
    "cpi": 4,
    "long_rate": 6,
    "cape": 12,
}
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
        rows = {}
        for row in cells:
            if not row or not isinstance(row[0], int | float) or row[0] < 1700:
                continue
            year, month = f"{row[0]:.2f}".split(".")
            observed = s.month_end(int(year), int(month))
            rows[observed] = {
                n: f.value(row[i], self.info.id, percent=n == "long_rate")
                for n, i in _COLUMNS.items()
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
            for n in _COLUMNS
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
        """Preserve the XLS layout with invented prices, ratios and rates."""
        del request
        cells = legacy_spreadsheet(response.body, "Data", self.info.id)
        dated = [
            row
            for row in cells
            if row and isinstance(row[0], int | float) and row[0] >= 1700
        ]
        rows: list[list[object]] = [
            [
                "Date",
                "P",
                "D",
                "E",
                "CPI",
                "Fraction",
                "Rate GS10",
                "Price",
                "Dividend",
                "Price",
                "Earnings",
                "Earnings",
                "CAPE",
            ]
        ]
        rows += [
            [row[0], *(synthetic_value(seed, i * 12 + j) for j in range(12))]
            for i, row in enumerate(dated[-3:])
        ]
        return replace(response, body=legacy_workbook("Data", rows))
