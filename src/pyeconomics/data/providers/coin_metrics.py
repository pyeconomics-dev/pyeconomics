# src/pyeconomics/data/providers/coin_metrics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Coin Metrics community API, with a machine-readable prohibition on paid use."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.core import UnitKind
from pyeconomics.data.errors import DataError, SeriesNotFoundError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.types import ObservationFrequency as F
from pyeconomics.data.types import UnitRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response
    from pyeconomics.data.types import Table

__all__ = ["CoinMetrics"]
_METRICS = {
    "PriceUSD",
    "CapMrktCurUSD",
    "SplyCur",
    "IssContNtv",
    "TxCnt",
    "AdrActCnt",
    "HashRate",
}


class CoinMetrics(DataProvider):
    """Daily community metrics under CC BY-NC 4.0; never a paid feature."""

    info = replace(
        f.info(
            "coin_metrics",
            "Coin Metrics community data",
            "https://coinmetrics.io",
            "https://github.com/coinmetrics/data/blob/master/LICENSE",
            "Source: Coin Metrics Community Network Data.",
            "Creative Commons Attribution-NonCommercial 4.0 International",
            ("community-api.coinmetrics.io",),
        ),
        never_paid=True,
    )
    cases = f.cases("btc:PriceUSD:SplyCur", "eth:TxCnt")

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Only asset identifiers and enumerated public metrics reach the API."""
        parts = f.single(query, self.info.id).split(":")
        if (
            len(parts) < 2
            or not re.fullmatch(r"[a-z0-9-]{1,30}", parts[0])
            or not set(parts[1:]) <= _METRICS
            or query.max_observations > 10000
        ):
            msg = "choose community metrics and at most 10000 daily observations"
            raise DataError(
                msg,
                provider=self.info.id,
            )
        params = [
            ("assets", parts[0]),
            ("metrics", ",".join(parts[1:])),
            ("frequency", "1d"),
            ("page_size", str(query.max_observations)),
            ("paging_from", "end"),
        ]
        if query.start:
            params.append(("start_time", query.start.isoformat()))
        if query.end:
            params.append(("end_time", query.end.isoformat()))
        return (
            Request(
                host=self.info.hosts[0],
                path="/v4/timeseries/asset-metrics",
                params=tuple(params),
                series=query.series[0],
            ),
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Preserve native quantities and USD prices, keeping missing metrics None."""
        rows = {}
        names = query.series[0].split(":")[1:]
        for response in responses:
            body = s.body_object(response, self.info.id)
            for row in s.items(body.get("data"), self.info.id, "community metrics"):
                observed = f.day(s.text(row, "time", self.info.id), F.DAILY)
                rows[observed] = {n: f.value(row.get(n), self.info.id) for n in names}
        units = {
            n: UnitRecord(text="USD", kind=UnitKind.MONEY, currency="USD")
            if n.endswith("USD")
            else UnitRecord(text=n)
            for n in names
        }
        return f.table(
            rows,
            units,
            query,
            self.info,
            responses[0],
            F.DAILY,
            notes=("licence: CC BY-NC 4.0", "never_paid"),
        )

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """Map an unavailable community asset/metric to a missing series."""
        if response.status == 400:
            return SeriesNotFoundError(self.info.id, request.series or "community")
        return None

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Keep only structural fields and invented community metric values."""
        names = (request.series or seed).split(":")[1:]
        rows = s.items(
            s.body_object(response, self.info.id).get("data"),
            self.info.id,
            "community metrics",
        )
        data = [
            {
                "asset": row["asset"],
                "time": row["time"],
                **{
                    n: str(synthetic_value(seed, i * len(names) + j))
                    for j, n in enumerate(names)
                },
            }
            for i, row in enumerate(rows[-3:])
        ]
        return replace(response, body=json.dumps({"data": data}).encode())
