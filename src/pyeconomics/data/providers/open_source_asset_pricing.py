# src/pyeconomics/data/providers/open_source_asset_pricing.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Open Source Asset Pricing's monthly predictor long-short portfolio returns.

Uses the authors' published wide CSV directly, without importing or depending
on the GPL-licensed openassetpricing client. Release 2025.10 / data version 2.0.0.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import SeriesNotFoundError
from pyeconomics.data.providers import _finance as f
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

__all__ = ["OpenSourceAssetPricing"]


class OpenSourceAssetPricing(DataProvider):
    """Research-only anomaly returns with source attribution and release label."""

    info = f.info(
        "open_source_asset_pricing",
        "Open Source Asset Pricing",
        "https://www.openassetpricing.com",
        "https://www.openassetpricing.com/data/",
        "Source: Andrew Y. Chen and Tom Zimmermann, Open Source Asset Pricing.",
        "Data (October 2025 Release)",
        ("drive.usercontent.google.com",),
    )
    cases = f.cases("predictor_long_short")

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Select the authors' fixed published file, never a user Drive id."""
        if f.single(query, self.info.id) != "predictor_long_short":
            raise SeriesNotFoundError(self.info.id, query.series[0])
        return (
            Request(
                host=self.info.hosts[0],
                path="/download",
                params=(
                    ("id", "10sOryk_ddjkXagaajTKUk1nwJs2ZLRiI"),
                    ("export", "download"),
                ),
                series=query.series[0],
            ),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """One return column per anomaly; percentages become decimal returns."""
        cells = f.csv_rows(responses[0].body)
        names = cells[0][1:]
        rows = {
            f.day(row[0], F.MONTHLY): {
                n: f.value(v, self.info.id, percent=True)
                for n, v in zip(names, row[1:], strict=True)
            }
            for row in cells[1:]
            if row
        }
        return f.table(
            rows,
            dict.fromkeys(names, f.RATE),
            query,
            self.info,
            responses[0],
            F.MONTHLY,
            notes=("source_release: 2025.10", "source_version: 2.0.0"),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep the wide CSV layout but no published anomaly return."""
        del request
        cells = f.csv_rows(response.body)
        rows = [
            [
                row[0],
                *(synthetic_value(seed, i * len(row) + j) for j in range(1, len(row))),
            ]
            for i, row in enumerate(cells[-3:])
        ]
        return replace(response, body=csv_document([cells[0], *rows]))
