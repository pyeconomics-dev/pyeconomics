# src/pyeconomics/data/providers/yfinance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Explicitly enabled personal-use Yahoo prices, fundamentals and option chains.

Ids: ``prices:IBM``, ``fundamentals:IBM``, ``options:IBM:calls`` (or ``puts``).
An option id can append ``:YYYY-MM-DD`` to choose an expiry. Default expiry
means the first expiry the source offers; it is recorded in column names.
The network client is imported only inside the transport's fetch function.
"""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import re
from dataclasses import replace
from typing import TYPE_CHECKING

from pyeconomics.data.errors import DataError
from pyeconomics.data.providers import _finance as f
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import Access, DataProvider
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.yahoo import require_enabled
from pyeconomics.data.types import ObservationFrequency as F
from pyeconomics.data.types import UnitRecord

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import Query
    from pyeconomics.data.transport.base import Response, Transport
    from pyeconomics.data.types import Table

__all__ = ["YFinance"]


class YFinance(DataProvider):
    """A transport adapter, off by default and excluded from automated live runs."""

    info = replace(
        f.info(
            "yfinance",
            "Yahoo Finance via yfinance",
            "https://finance.yahoo.com",
            "https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html",
            "Source: Yahoo Finance, through yfinance.",
            "the Yahoo! finance API is intended for personal use only.",
            (),
        ),
        access=Access.SESSION,
        extra="yfinance",
        automated_collection=False,
    )
    cases = f.cases("prices:IBM", "fundamentals:IBM", "options:IBM:calls")

    def check_configuration(self) -> None:
        """Keep cached results behind the same explicit opt-in as live results."""
        from pyeconomics.data.transport.yahoo import warn_once  # noqa: PLC0415

        require_enabled()
        warn_once()

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Require explicit opt-in before even a supplied session can run."""
        require_enabled()
        parts = f.single(query, self.info.id).split(":")
        if (
            len(parts) < 2
            or parts[0] not in {"prices", "fundamentals", "options"}
            or not re.fullmatch(r"[A-Za-z0-9^][A-Za-z0-9.^=-]{0,31}", parts[1])
            or (parts[0] != "options" and len(parts) != 2)
            or (
                parts[0] == "options"
                and (len(parts) not in {3, 4} or parts[2] not in {"calls", "puts"})
            )
        ):
            msg = "choose prices, fundamentals or an option-chain side"
            raise DataError(
                msg,
                provider=self.info.id,
            )
        if len(parts) == 4:
            f.day(parts[3], F.DAILY)
        params = tuple(
            (n, v.isoformat())
            for n, v in (("start", query.start), ("end", query.end))
            if v
        )
        return (
            Request(
                host="yfinance-session.localhost",
                path="/fetch",
                params=params,
                body={"selection": parts, "limit": query.max_observations},
                series=query.series[0],
                method="POST",
            ),
        )

    def exchange(
        self,
        requests: Sequence[Request],
        *,
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        """Use an injected replay or the lazily loaded local yfinance adapter."""
        from pyeconomics.data.transport.yahoo import YahooTransport  # noqa: PLC0415

        return super().exchange(
            requests, key=key, transport=transport or YahooTransport()
        )

    def parse(self, responses: Sequence[Response], query: Query) -> Table:
        """Only the adapter's finite numeric fields enter the public Table."""
        body = s.body_object(responses[0], self.info.id)
        columns = body["columns"]
        rows = {
            f.day(row[0], F.DAILY): dict(zip(columns, row[1:], strict=True))
            for row in body["rows"]
        }
        units = {n: UnitRecord(**body["units"][n]) for n in columns}
        return f.table(
            rows,
            units,
            query,
            self.info,
            responses[0],
            F.BUSINESS_DAILY if query.series[0].startswith("prices:") else F.IRREGULAR,
            notes=("personal_use_only", "automated_collection_barred"),
        )

    def synthesize(
        self, request: Request, response: Response, *, seed: str
    ) -> Response:
        """Replace the local adapter's numeric results for offline replay."""
        from pyeconomics.data.transport.yahoo import synthetic_response  # noqa: PLC0415

        return synthetic_response(request, response, seed=seed)
