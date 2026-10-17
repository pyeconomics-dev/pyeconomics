# src/pyeconomics/data/transport/yahoo.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Local opt-in yfinance session. No Yahoo traffic is used by ordinary CI."""

# ruff: noqa: PLR2004 - fixed source layouts, HTTP status and calendar bounds

from __future__ import annotations

import datetime as dt
import importlib.util
import json
import math
import threading
import warnings
from dataclasses import replace
from typing import TYPE_CHECKING, Any

from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import modes
from pyeconomics.data.config import settings
from pyeconomics.data.errors import DataWarning, LicenceError, TransportError
from pyeconomics.data.redaction import call_scrubbed
from pyeconomics.data.transport.base import Response
from pyeconomics.data.transport.cassette import synthetic_value

if TYPE_CHECKING:
    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.providers.base import ProviderInfo
    from pyeconomics.data.transport.base import Request

_LOCK = threading.Lock()
_WARNED = False
_TERMS = (
    "Yahoo Finance is for personal use only; its terms bar automated collection. "
    "Review https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html"
)


def require_enabled() -> None:
    """Installing the extra is insufficient: opt-in must also be explicit."""
    if importlib.util.find_spec("yfinance") is None:
        msg = "yfinance"
        raise MissingOptionalDependencyError(msg, extra="yfinance")
    if not settings().enable_yfinance:
        msg = (
            "yfinance is disabled; explicitly set "
            "enable_yfinance=True after reviewing Yahoo's personal-use terms"
        )
        raise LicenceError(
            msg,
            provider="yfinance",
            licence=LicenceClass.LIBRARY_ONLY,
        )


def warn_once() -> None:
    """Show the terms once per process, including before a cached result."""
    global _WARNED  # noqa: PLW0603 - exactly one warning per process
    with _LOCK:
        if not _WARNED:
            _WARNED = True
            warnings.warn(DataWarning("yahoo_personal_use", _TERMS), stacklevel=3)


def _numeric(value: object) -> float | None:
    if value is None:
        return None
    if not isinstance(value, str | int | float):
        msg = "Yahoo returned a nonnumeric field"
        raise TypeError(msg)
    number = float(value)
    return number if math.isfinite(number) else None


class YahooTransport:
    """A local session, producing only a bounded numeric table-shaped response."""

    def send(
        self, info: ProviderInfo, request: Request, *, key: str | Secret | None = None
    ) -> Response:
        """Hold the same mode/online gates even when called outside a provider."""
        del key
        modes.require_allowed(info.terms, provider=info.id)
        modes.require_online(provider=info.id)
        require_enabled()
        self._validate(request)
        warn_once()
        return call_scrubbed(
            lambda: self._fetch(request),
            lambda _message: TransportError(
                "Yahoo session failed", provider="yfinance"
            ),
        )

    @staticmethod
    def _validate(request: Request) -> None:
        """Validate direct session calls as strictly as provider-created requests."""
        from pyeconomics.data.providers.base import Query  # noqa: PLC0415
        from pyeconomics.data.providers.yfinance import YFinance  # noqa: PLC0415

        def check() -> None:
            body = request.body
            if not isinstance(body, dict):
                msg = "Yahoo session request body is not an object"
                raise TypeError(msg)
            parts = body["selection"]
            if not isinstance(parts, list) or not all(
                isinstance(part, str) for part in parts
            ):
                msg = "Yahoo session selection is not a list of identifiers"
                raise TypeError(msg)
            params = dict(request.params)
            query = Query.model_validate(
                {
                    "series": (":".join(parts),),
                    "max_observations": body["limit"],
                    **params,
                }
            )
            if request != YFinance().build_requests(query)[0]:
                msg = "Yahoo session request is outside its declared contract"
                raise ValueError(msg)

        call_scrubbed(
            check, lambda message: TransportError(message, provider="yfinance")
        )

    def _fetch(self, request: Request) -> Response:  # noqa: C901, PLR0912 - three native result shapes
        import yfinance as yf  # noqa: PLC0415 - only inside a real fetch

        now = dt.datetime.now(dt.UTC)
        body = request.body
        if not isinstance(body, dict):
            msg = "Yahoo adapter requires a typed request body"
            raise TypeError(msg)
        parts = body["selection"]
        limit = body["limit"]
        ticker = yf.Ticker(parts[1])
        units: dict[str, dict[str, object]] = {}
        rows: list[list[object]] = []
        if parts[0] == "prices":
            params = dict(request.params)
            options: dict[str, Any] = {"auto_adjust": False, "actions": False}
            if params:
                options.update(params)
                if "end" in params:
                    options["end"] = (
                        dt.date.fromisoformat(params["end"]) + dt.timedelta(days=1)
                    ).isoformat()
            else:
                options["period"] = "max"
            frame = ticker.history(**options)
            columns = [
                n for n in ("Open", "High", "Low", "Close", "Volume") if n in frame
            ]
            for stamp, row in frame.tail(limit).iterrows():
                rows.append(
                    [stamp.date().isoformat(), *(_numeric(row[n]) for n in columns)]
                )
            units = {
                n: {"text": "Shares" if n == "Volume" else "Source currency price"}
                for n in columns
            }
        elif parts[0] == "fundamentals":
            source = ticker.info
            fundamental_fields = {
                "marketCap",
                "enterpriseValue",
                "sharesOutstanding",
                "totalRevenue",
                "ebitda",
                "totalDebt",
                "totalCash",
                "trailingPE",
                "forwardPE",
                "priceToBook",
                "beta",
                "profitMargins",
                "operatingMargins",
                "returnOnAssets",
                "returnOnEquity",
            }
            columns = sorted(
                n
                for n in fundamental_fields
                if isinstance(source.get(n), int | float)
                and not isinstance(source[n], bool)
            )
            rows = (
                [[now.date().isoformat(), *(_numeric(source[n]) for n in columns)]]
                if columns
                else []
            )
            units = {n: {"text": "Source field: " + n} for n in columns}
        else:
            expiry = parts[3] if len(parts) == 4 else next(iter(ticker.options), None)
            if expiry is None:
                return Response(404, b"", now)
            chain = ticker.option_chain(expiry)
            frame = getattr(chain, parts[2])
            fields = (
                "strike",
                "lastPrice",
                "bid",
                "ask",
                "impliedVolatility",
                "volume",
                "openInterest",
            )
            columns, values = [], []
            for _, row in frame.iterrows():
                for field in fields:
                    name = str(row["contractSymbol"]) + ":" + field
                    columns.append(name)
                    values.append(_numeric(row[field]))
                    units[name] = (
                        {"text": "Decimal implied volatility", "kind": "volatility"}
                        if field == "impliedVolatility"
                        else {"text": "Contracts"}
                        if field in {"volume", "openInterest"}
                        else {"text": "Source currency price"}
                    )
            rows = [[now.date().isoformat(), *values]] if columns else []
        if not rows:
            return Response(404, b"", now)
        if len(columns) > 1000:
            msg = "Yahoo option chain exceeds the 1000-column bound"
            raise ValueError(msg)
        payload = {"columns": columns, "rows": rows, "units": units}
        return Response(200, json.dumps(payload, allow_nan=False).encode(), now)


def synthetic_response(request: Request, response: Response, *, seed: str) -> Response:
    """Construct a synthetic local-session response without contacting Yahoo."""
    del request
    from pyeconomics.data.providers import _shared as s  # noqa: PLC0415

    body = s.body_object(response, "yfinance")
    columns = body["columns"]
    body["rows"] = [
        [
            row[0],
            *(synthetic_value(seed, i * len(columns) + j) for j in range(len(columns))),
        ]
        for i, row in enumerate(body["rows"][-3:])
    ]
    return replace(response, body=json.dumps(body).encode())
