# src/pyeconomics/data/providers/damodaran.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Damodaran's published aggregate ERP, country-risk, beta and multiple files.

Category selection is explicit, for example ``country_risk:united_states`` or
``industry_betas:advertising``. Aggregate snapshots are dated by the file's
published update, never by retrieval time. Content hashes identify file versions;
historical availability is not invented for current files.
"""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import datetime as dt
import hashlib
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.data.errors import DataError, ResponseError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.files import (
    legacy_spreadsheet,
    legacy_workbook,
    spreadsheet,
    workbook,
)
from pyeconomics.data.types import ObservationFrequency as F
from pyeconomics.data.types import UnitRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["Damodaran"]
_FILES = {
    "implied_erp": ("histimpl.xls", "Historical Impl Premiums", "Year"),
    "country_risk": ("ctryprem.xlsx", "ERPs by country", "Country"),
    "industry_betas": ("betas.xls", "Industry Averages", "Industry Name"),
    "industry_multiples": ("vebitda.xls", "Industry Averages", "Industry Name"),
}
_FIELDS = {
    "implied_erp": (1, 2, 3, 6, 9, 10, 13, 14, 15, 16, 17),
    "country_risk": (3, 4, 5),
    "industry_betas": (2, 5, 7),
    "industry_multiples": (2, 3, 4, 5, 6, 7, 8, 9),
}
#: The implied-premium file's columns that are not decimal rates: the S&P 500's
#: year-end level and the dividends and buybacks paid on it, both in index points.
_LEVELS = {
    3: UnitRecord(text="Index points", kind=UnitKind.INDEX_LEVEL),
    6: UnitRecord(
        text="Index points (US dollars per unit of the index)",
        kind=UnitKind.MONEY,
        currency="USD",
    ),
}


class Damodaran(DataProvider):
    """Credited aggregates only; no bulk mirror or resale of the author's data."""

    info = f.info(
        "damodaran",
        "Damodaran Online aggregates",
        "https://pages.stern.nyu.edu/~adamodar/",
        "https://pages.stern.nyu.edu/~adamodar/New_Home_Page/guide.html",
        "Source: Aswath Damodaran, Damodaran Online.",
        (
            "The second is that you acknowledge the "
            "parentage when you used the data from this site."
        ),
        ("pages.stern.nyu.edu",),
        hosted=True,
    )
    cases = f.cases(
        "implied_erp",
        "country_risk:united_states",
        "industry_betas:advertising",
        "industry_multiples:advertising",
    )

    def _selection(self, identifier: str) -> tuple[str, str]:
        name, _, category = identifier.partition(":")
        if name not in _FILES or (name != "implied_erp" and not category):
            msg = "select an aggregate dataset and category"
            raise DataError(msg, provider=self.info.id)
        return name, category

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Download one known aggregate workbook, never company-level datasets."""
        name, _ = self._selection(f.single(query, self.info.id))
        return (
            Request(
                host=self.info.hosts[0],
                path="/~adamodar/pc/datasets/" + _FILES[name][0],
                series=query.series[0],
            ),
        )

    def _source(
        self, body: bytes, name: str
    ) -> tuple[dt.datetime, tuple[object, ...], list[tuple[object, ...]], str]:
        filename, sheet, marker = _FILES[name]
        cells = (
            spreadsheet(body, sheet, self.info.id)
            if filename.endswith("xlsx")
            else legacy_spreadsheet(body, sheet, self.info.id)
        )
        updates = [
            row[1]
            for row in cells[:12]
            if row and str(row[0]).lower() in {"date updated:", "date of update:"}
        ]
        if not updates or not isinstance(updates[0], dt.datetime):
            msg = "aggregate file has no published update date"
            raise ResponseError(msg, provider=self.info.id)
        start = next(
            i for i, row in enumerate(cells) if row and str(row[0]).strip() == marker
        )
        versions = [row[1] for row in cells[:12] if row and row[0] == "Source version:"]
        version = str(versions[0]) if versions else hashlib.sha256(body).hexdigest()
        return updates[0], cells[start], list(cells[start + 1 :]), version

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Preserve decimal percentages and dimensionless beta/multiple units."""
        name, category = self._selection(query.series[0])
        response = responses[0]
        updated, header, cells, version = self._source(response.body, name)
        columns = {i: f.slug(str(header[i])) + f"_{i}" for i in _FIELDS[name]}
        rows = {}
        for row in cells:
            if not row or not row[0]:
                continue
            if name == "implied_erp":
                if not isinstance(row[0], int | float) or not 1700 <= row[0] <= 2200:
                    continue
                observed = dt.date(int(row[0]), 12, 31)
            else:
                if f.slug(str(row[0])) != category:
                    continue
                observed = updated.date()
            rows[observed] = {
                n: f.value(row[i], self.info.id) for i, n in columns.items()
            }
        unit = (
            UnitRecord(text="Decimal rate", kind=UnitKind.RATE)
            if name in {"country_risk", "implied_erp"}
            else UnitRecord(text="Dimensionless beta or enterprise-value multiple")
        )
        return f.table(
            rows,
            {
                n: _LEVELS.get(i, unit) if name == "implied_erp" else unit
                for i, n in columns.items()
            },
            query,
            self.info,
            response,
            F.ANNUAL if name == "implied_erp" else F.IRREGULAR,
            notes=(
                "no_bulk_mirror",
                "no_resale",
                "revised_data",
                "source_update: " + updated.date().isoformat(),
                "source_version: sha256:" + version,
            ),
        )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep genuine values only for the explicitly selected aggregate category."""
        del request
        if not response.ok:
            return replace(response, body=b"")
        name, category = self._selection(query.series[0])
        updated, header, source, version = self._source(response.body, name)
        if name == "implied_erp":
            selected = [
                row
                for row in source
                if row
                and isinstance(row[0], int | float)
                and 1700 <= row[0] <= 2200
                and (query.start is None or int(row[0]) >= query.start.year)
                and (query.end is None or int(row[0]) <= query.end.year)
            ][-query.max_observations :]
        else:
            selected = [
                row for row in source if row and f.slug(str(row[0])) == category
            ]
        # Only supported aggregate fields are retained; no email or unrelated sheet.
        keep = {0, *_FIELDS[name]}
        data = (
            ("Date updated:", updated),
            ("Source version:", version),
            header,
            *(
                tuple(v if i in keep else None for i, v in enumerate(row))
                for row in selected
            ),
        )
        filename, sheet, _ = _FILES[name]
        body = (
            workbook({sheet: data})
            if filename.endswith("xlsx")
            else legacy_workbook(sheet, data)
        )
        return replace(response, body=body)
