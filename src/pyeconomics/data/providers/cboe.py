# src/pyeconomics/data/providers/cboe.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Cboe daily VIX OHLC, expressed as decimal annualized volatility."""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.data.errors import SeriesNotFoundError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import csv_document
from pyeconomics.data.types import ObservationFrequency as F
from pyeconomics.data.types import UnitRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["Cboe"]
_HEADERS = ("OPEN", "HIGH", "LOW", "CLOSE")


class Cboe(DataProvider):
    """Library-only VIX data, never redistributed as a hosted dataset."""

    info = f.info(
        "cboe",
        "Cboe VIX",
        "https://www.cboe.com",
        "https://www.cboe.com/terms",
        "Source: Cboe Global Markets, VIX Index.",
        "All Rights Reserved.",
        ("cdn-api.cboe.com",),
    )
    cases = f.cases("vix")

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Request the official daily-history CSV."""
        if f.single(query, self.info.id) != "vix":
            raise SeriesNotFoundError(self.info.id, query.series[0])
        return (
            Request(
                host=self.info.hosts[0],
                path="/api/global/us_indices/daily_prices/VIX_History.csv",
                series="vix",
            ),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Read US dates and convert the index's percent volatility to decimal."""
        cells = f.csv_rows(responses[0].body)
        rows = {}
        for row in cells[1:]:
            if not row:
                continue
            observed = (
                dt.datetime.strptime(row[0], "%m/%d/%Y").replace(tzinfo=dt.UTC).date()
            )
            rows[observed] = dict(
                zip(
                    _HEADERS,
                    (f.value(v, self.info.id, percent=True) for v in row[1:]),
                    strict=True,
                )
            )
        unit = UnitRecord(text="VIX volatility, decimal", kind=UnitKind.VOLATILITY)
        return f.table(
            rows,
            dict.fromkeys(_HEADERS, unit),
            query,
            self.info,
            responses[0],
            F.BUSINESS_DAILY,
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Replace every index value and keep the CSV's shape."""
        del request
        rows = f.csv_rows(response.body)
        return replace(
            response,
            body=csv_document(
                [
                    rows[0],
                    *[
                        [
                            row[0],
                            *(100 * synthetic_value(seed, i * 4 + j) for j in range(4)),
                        ]
                        for i, row in enumerate(rows[-3:])
                    ],
                ]
            ),
        )
