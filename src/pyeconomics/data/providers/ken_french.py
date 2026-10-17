# src/pyeconomics/data/providers/ken_french.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Ken French factors and portfolios, with explicit frequency/weight sections.

Ids are ``ff3:monthly``, ``ff5:annual``, ``momentum:daily``,
``industry12:monthly`` and ``size_bm25:monthly``. Portfolio ids optionally end
in ``:equal``; value-weighted returns are the default. No portfolio counts,
firm sizes or valuation ratios are mislabelled as returns.
"""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import DataError, ResponseError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import archive, csv_document, zip_document
from pyeconomics.data.types import ObservationFrequency as F

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["KenFrench"]
_FILES = {
    "ff3": "F-F_Research_Data_Factors",
    "ff5": "F-F_Research_Data_5_Factors_2x3",
    "momentum": "F-F_Momentum_Factor",
    "industry12": "12_Industry_Portfolios",
    "industry49": "49_Industry_Portfolios",
    "size_bm25": "25_Portfolios_5x5",
}
_FREQUENCIES = {"monthly": F.MONTHLY, "annual": F.ANNUAL, "daily": F.BUSINESS_DAILY}


class KenFrench(DataProvider):
    """Runtime access with the Data Library's copyright notice."""

    info = f.info(
        "ken_french",
        "Ken French Data Library",
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html",
        "Source: Eugene F. Fama and Kenneth R. French, Data Library.",
        "Copyright Eugene F. Fama and Kenneth R. French",
        ("mba.tuck.dartmouth.edu",),
    )
    cases = f.cases(
        "ff3:monthly",
        "ff3:annual",
        "ff3:daily",
        "ff5:monthly",
        "ff5:daily",
        "momentum:monthly",
        "momentum:daily",
        "industry12:monthly",
        "size_bm25:monthly",
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Select only known library files; the caller supplies no filename."""
        parts = f.single(query, self.info.id).split(":")
        if (
            len(parts) not in {2, 3}
            or parts[0] not in _FILES
            or parts[1] not in _FREQUENCIES
            or (len(parts) == 3 and parts[2] not in {"value", "equal"})
        ):
            msg = "choose a known French dataset and frequency"
            raise DataError(msg, provider=self.info.id)
        suffix = "_daily" if parts[1] == "daily" else ""
        filename = _FILES[parts[0]] + suffix + "_CSV.zip"
        return (
            Request(
                host=self.info.hosts[0],
                path="/pages/faculty/ken.french/ftp/" + filename,
                series=query.series[0],
            ),
        )

    def _section(
        self, body: bytes, identifier: str
    ) -> tuple[list[str], list[list[str]]]:
        parts = identifier.split(":")
        frequency = parts[1]
        digits = {"daily": 8, "monthly": 6, "annual": 4}[frequency]
        members = archive(body, self.info.id)
        files = [b for n, b in members.items() if n.lower().endswith(".csv")]
        if len(files) != 1:
            msg = "expected one French CSV member"
            raise ResponseError(msg, provider=self.info.id)
        header: list[str] = []
        rows: list[list[str]] = []
        section = "value"
        portfolio = parts[0].startswith(("industry", "size_"))
        wanted = parts[2] if len(parts) == 3 else "value"
        for row in f.csv_rows(files[0]):
            if not row:
                continue
            label = row[0].strip()
            if portfolio and "Returns" in label:
                section = "equal" if "Equal" in label else "value"
            elif portfolio and any(
                word in label for word in ("Number of", "Average", "Book-to-Market")
            ):
                section = "other"
            if not label and len(row) > 1:
                header = [n.strip() for n in row[1:]]
            elif re.fullmatch(r"\d{" + str(digits) + "}", label) and (
                not portfolio or section == wanted
            ):
                if not header or len(row) != len(header) + 1:
                    msg = "French section width changed"
                    raise ResponseError(msg, provider=self.info.id)
                rows.append(row)
        return header, rows

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Split monthly/annual/daily sections; convert percent and sentinels."""
        header, source = self._section(responses[0].body, query.series[0])
        frequency = _FREQUENCIES[query.series[0].split(":")[1]]
        rows = {}
        for row in source:
            observed = f.day(row[0], frequency)
            if observed in rows:
                msg = "French section repeats a date"
                raise ResponseError(msg, provider=self.info.id)
            rows[observed] = {
                n: None
                if v.strip() in {"-99.99", "-999", "-999.00"}
                else f.value(v, self.info.id, percent=True)
                for n, v in zip(header, row[1:], strict=True)
            }
        return f.table(
            rows,
            dict.fromkeys(header, f.RATE),
            query,
            self.info,
            responses[0],
            frequency,
            notes=(
                (
                    "source_methodology: CRSP CIZ from "
                    "January 2025; dividends reinvested on ex-dates"
                ),
            ),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep the section layout and replace every return before recording."""
        header, rows = self._section(response.body, request.series or seed)
        synthetic = [
            [
                r[0],
                *(
                    synthetic_value(seed, i * len(header) + j)
                    for j in range(len(header))
                ),
            ]
            for i, r in enumerate(rows[-3:])
        ]
        body = csv_document([["Synthetic research returns"], ["", *header], *synthetic])
        return replace(response, body=zip_document({"synthetic.csv": body}))
