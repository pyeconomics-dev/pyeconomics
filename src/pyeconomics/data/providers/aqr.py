# src/pyeconomics/data/providers/aqr.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""AQR's published BAB, QMJ and value/momentum research-factor workbooks."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import DataError, ResponseError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import selected_spreadsheet, workbook
from pyeconomics.data.types import ObservationFrequency as F

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["Aqr"]
_FILES = {
    "bab": ("Betting-Against-Beta-Equity-Factors", "BAB Factors"),
    "qmj": ("Quality-Minus-Junk-Factors", "QMJ Factors"),
    "value_momentum": (
        "Value-and-Momentum-Everywhere-Factors",
        "Value and Momentum Factors",
    ),
}


class Aqr(DataProvider):
    """Research-only excess returns; spreadsheet values are already decimals."""

    info = f.info(
        "aqr",
        "AQR research datasets",
        "https://www.aqr.com",
        "https://www.aqr.com/Terms-of-Use",
        "Source: AQR Capital Management, LLC.",
        "PAST PERFORMANCE DOES NOT GUARANTEE FUTURE RESULTS.",
        ("www.aqr.com",),
    )
    cases = f.cases("bab:monthly", "bab:daily", "qmj:monthly")

    def _selection(self, identifier: str) -> tuple[str, str, str]:
        parts = identifier.split(":")
        if (
            len(parts) != 2
            or parts[0] not in _FILES
            or parts[1] not in {"monthly", "daily"}
        ):
            msg = "choose an AQR family and frequency"
            raise DataError(msg, provider=self.info.id)
        filename, sheet = _FILES[parts[0]]
        return filename, sheet, parts[1]

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Select a known workbook, leaving its download entirely in memory."""
        filename, _, frequency = self._selection(f.single(query, self.info.id))
        return (
            Request(
                host=self.info.hosts[0],
                series=query.series[0],
                path=f"/-/media/AQR/Documents/Insights/Data-Sets/{filename}-{frequency.title()}.xlsx",
            ),
        )

    def _source(
        self, body: bytes, identifier: str
    ) -> tuple[tuple[object, ...], list[tuple[object, ...]]]:
        _, sheet, _ = self._selection(identifier)
        cells = selected_spreadsheet(body, sheet, self.info.id)
        header_at = next(
            (
                i
                for i, row in enumerate(cells)
                if row and str(row[0]).strip().upper() == "DATE"
            ),
            None,
        )
        if header_at is None:
            msg = "AQR workbook has no DATE header"
            raise ResponseError(msg, provider=self.info.id)
        header = cells[header_at]
        return header, [
            row
            for row in cells[header_at + 1 :]
            if row
            and (
                isinstance(row[0], dt.datetime)
                or (
                    isinstance(row[0], str)
                    and re.fullmatch(r"[0-9]{2}/[0-9]{2}/[0-9]{4}", row[0])
                )
            )
        ]

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Keep all countries/regions in the selected sheet at native frequency."""
        header, source = self._source(responses[0].body, query.series[0])
        columns = {i: str(n).strip() for i, n in enumerate(header) if i and n}
        frequency = (
            F.MONTHLY if query.series[0].endswith(":monthly") else F.BUSINESS_DAILY
        )
        rows = {}
        for row in source:
            stamp = row[0]
            if isinstance(stamp, str):
                stamp = dt.datetime.strptime(stamp, "%m/%d/%Y").replace(tzinfo=dt.UTC)
            if not isinstance(stamp, dt.datetime):
                msg = "AQR observation date is not a datetime"
                raise ResponseError(msg, provider=self.info.id)
            observed = (
                s.month_end(stamp.year, stamp.month)
                if frequency is F.MONTHLY
                else stamp.date()
            )
            rows[observed] = {
                n: f.value(row[i], self.info.id) for i, n in columns.items()
            }
        return f.table(
            rows,
            dict.fromkeys(columns.values(), f.RATE),
            query,
            self.info,
            responses[0],
            frequency,
            notes=("source_units: decimal excess returns",),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Write synthetic return rows using the native sheet and date header."""
        identifier = request.series or seed
        _, sheet, _ = self._selection(identifier)
        header, rows = self._source(response.body, identifier)
        data = (
            header,
            *(
                (
                    row[0],
                    *(
                        synthetic_value(seed, i * len(header) + j)
                        for j in range(1, len(header))
                    ),
                )
                for i, row in enumerate(rows[-3:])
            ),
        )
        return replace(response, body=workbook({sheet: data}))
