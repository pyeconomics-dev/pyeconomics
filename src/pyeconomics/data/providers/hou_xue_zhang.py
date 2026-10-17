# src/pyeconomics/data/providers/hou_xue_zhang.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Global-q q5 factors and benchmark portfolios, native daily through annual."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import DataError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import csv_document
from pyeconomics.data.types import ObservationFrequency as F

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["HouXueZhang"]
_FREQUENCIES = {
    "daily": F.BUSINESS_DAILY,
    "monthly": F.MONTHLY,
    "quarterly": F.QUARTERLY,
    "annual": F.ANNUAL,
}
_FILES = {
    "q5": "q5_factors",
    "benchmark": "benportf_me_ia_roe",
    "expected_growth": "benportf_me_eg",
}


class HouXueZhang(DataProvider):
    """Thin client for the authors' research files, without third-party clients."""

    info = f.info(
        "hou_xue_zhang",
        "Hou, Xue and Zhang global-q",
        "https://global-q.org",
        "https://global-q.org/factors.html",
        "Source: Kewei Hou, Haitao Mo, Chen Xue and Lu Zhang, global-q.org.",
        None,
        ("global-q.org",),
    )
    cases = f.cases(
        "q5:monthly",
        "q5:daily",
        "q5:annual",
        "benchmark:monthly",
        "expected_growth:monthly",
        "q5:quarterly",
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Choose a known family and frequency in the current annual release."""
        parts = f.single(query, self.info.id).split(":")
        if len(parts) != 2 or parts[0] not in _FILES or parts[1] not in _FREQUENCIES:
            msg = "choose a global-q family and frequency"
            raise DataError(msg, provider=self.info.id)
        return (
            Request(
                host=self.info.hosts[0],
                series=query.series[0],
                path="/uploads/1/2/2/6/122679606/"
                + _FILES[parts[0]]
                + "_"
                + parts[1]
                + "_2025.csv",
            ),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Keep calendar fields separate from percent returns."""
        cells = f.csv_rows(responses[0].body)
        header = cells[0]
        ranks = [n for n in header if n.startswith("rank_")]
        names = (
            [n for n in header if n.startswith("R_")]
            if not ranks
            else ["ret_vw", "retx_vw"]
        )
        units = {}
        frequency = _FREQUENCIES[query.series[0].split(":")[1]]
        rows: f.Rows = {}
        for values in cells[1:]:
            if not values:
                continue
            row = dict(zip(header, values, strict=True))
            if "DATE" in row:
                observed = f.day(row["DATE"], frequency)
            elif frequency is F.ANNUAL:
                observed = f.day(row["year"], frequency)
            elif frequency is F.BUSINESS_DAILY:
                observed = f.day(row.get("date", ""), frequency)
            else:
                month = (
                    int(row["quarter"]) * 3
                    if frequency is F.QUARTERLY
                    else int(row["month"])
                )
                observed = s.month_end(int(row["year"]), month)
            prefix = "_".join(n[5:].lower() + row[n] for n in ranks)
            target = rows.setdefault(observed, {})
            for name in names:
                column = prefix + ":" + name if prefix else name
                if column in target:
                    msg = "global-q selection repeats a date and portfolio"
                    raise DataError(msg, provider=self.info.id)
                target[column] = f.value(row[name], self.info.id, percent=True)
                units[column] = f.RATE
        return f.table(
            rows,
            units,
            query,
            self.info,
            responses[0],
            frequency,
            notes=("source_release: 2025",),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep calendar columns, replace every factor or portfolio return."""
        del request
        cells = f.csv_rows(response.body)
        dates = {"year", "month", "day", "date", "quarter"}
        calendar = [i for i, name in enumerate(cells[0]) if name.lower() in dates]
        keys = sorted(
            {tuple(row[i] for i in calendar) for row in cells[1:] if row},
            key=lambda key: tuple(int(v) if v.isdigit() else v for v in key),
        )[-3:]
        chosen = [
            row for row in cells[1:] if row and tuple(row[i] for i in calendar) in keys
        ]
        synthetic = []
        for i, row in enumerate(chosen):
            synthetic.append(
                [
                    value
                    if cells[0][j].lower() in dates or cells[0][j].startswith("rank_")
                    else int(100 * synthetic_value(seed, i * len(row) + j)) + 1
                    if cells[0][j] == "nstocks"
                    else synthetic_value(seed, i * len(row) + j)
                    for j, value in enumerate(row)
                ]
            )
        return replace(response, body=csv_document([cells[0], *synthetic]))
