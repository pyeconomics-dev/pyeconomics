# src/pyeconomics/data/providers/atlanta_fed.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""GDPNow current estimate and historical updates, each update a vintage.

``gdpnow`` includes the live TrackingHistory sheet and both archives. Only
GDPNow's own forecast is read; proprietary Blue Chip forecasts are excluded.
"""

# ruff: noqa: PLR2004 - source calendar and fixed spreadsheet layout constants

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Final

from pyeconomics.core import UnitKind
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import ResponseError, SeriesNotFoundError
from pyeconomics.data.providers import _research as r
from pyeconomics.data.providers.base import Capability, ProviderInfo, Query, RateLimit
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.transport.files import spreadsheet, workbook
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from typing import Any

PROVIDER: Final = "atlanta_fed"

__all__ = ["AtlantaFed"]
HOST: Final = "www.atlantafed.org"
PATH: Final = (
    "/-/media/Project/Atlanta/FRBA/Documents/research-and-"
    "data/data/gdpnow/GDPTrackingModelDataAndForecasts.xlsx"
)
SHEETS: Final = ("TrackingDeepArchives", "TrackingArchives", "TrackingHistory")
NOTICE: Final = (
    "Permission is granted to reproduce for personal and educational use only."
)
TERMS: Final = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://www.atlantafed.org/research-and-data/data/gdpnow",
    checked=dt.date(2026, 10, 17),
    attribution="Source: Federal Reserve Bank of Atlanta, GDPNow.",
    notice=NOTICE,
    llm_use=LlmUse.UNCLEAR,
    cache=CachePolicy.ALLOWED,
)


def observations(body: bytes) -> list[r.Observation]:
    """Read dated archive rows and dated columns for the current quarter."""
    pairs: dict[tuple[dt.date, dt.date], float | None] = {}
    for sheet in SHEETS[:2]:
        rows = spreadsheet(body, sheet, "atlanta_fed")
        header = [str(v).strip() for v in rows[0]]
        if "GDP Nowcast" not in header:
            msg = "GDPNow archive has no forecast column"
            raise ResponseError(msg, provider="atlanta_fed")
        column = header.index("GDP Nowcast")
        for row in rows[1:]:
            if row[0] is not None and row[1] is not None:
                pairs[r.day(row[1], "atlanta_fed"), r.day(row[0], "atlanta_fed")] = (
                    r.number(row[column], "atlanta_fed", percent=True)
                )
    rows = spreadsheet(body, "TrackingHistory", "atlanta_fed")
    target = re.search(r"(\d{4})[qQ]([1-4])", str(rows[1][0]))
    forecast = next((row for row in rows if str(row[0]).strip().upper() == "GDP"), None)
    if target is None or forecast is None:
        msg = "GDPNow current sheet has no quarter or GDP row"
        raise ResponseError(msg, provider="atlanta_fed")
    observed = r.period(target[1] + "Q" + target[2], "atlanta_fed")
    for j, value in enumerate(rows[0][2:], 2):
        if value is not None:
            pairs[observed, r.day(value, "atlanta_fed")] = r.number(
                forecast[j], "atlanta_fed", percent=True
            )
    return [(d, v, x) for (d, v), x in sorted(pairs.items())]


class AtlantaFed(r.VintageResearch):
    """The GDPNow workbook's estimates, with their true update dates."""

    info = ProviderInfo(
        id="atlanta_fed",
        name="Federal Reserve Bank of Atlanta",
        homepage="https://www.atlantafed.org",
        terms=TERMS,
        hosts=(HOST,),
        capabilities=(Capability.FETCH, Capability.VINTAGES),
        rate_limits=(RateLimit(requests=2, per="second"),),
        ttl_seconds=86400,
    )
    cases = r.cases("gdpnow", vintages=True)

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Read the source's current workbook location, not its stale legacy links."""
        series_id = r.single(query, self.info.id)
        if series_id != "gdpnow":
            raise SeriesNotFoundError(self.info.id, series_id)
        return (Request(host=HOST, path=PATH, series=series_id),)

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Close update intervals independently for each target quarter."""
        meta = SeriesMeta(
            provider=self.info.id,
            series_id=r.single(query, self.info.id),
            title="GDPNow real GDP growth estimate",
            unit=UnitRecord(text="Quarterly percent change (SAAR)", kind=UnitKind.RATE),
            frequency=ObservationFrequency.QUARTERLY,
            seasonal_adjustment=SeasonalAdjustment.SEASONALLY_ADJUSTED_ANNUAL_RATE,
            source_dating=DateConvention.PERIOD_END,
            terms=TERMS,
            notes=(
                "model_estimate: GDPNow is not an official forecast of the Atlanta Fed",
            ),
        )
        return r.frame(observations(responses[0].body), meta, query)

    def synthesize(
        self,
        request: Request,  # noqa: ARG002 - hook signature
        response: Response,
        *,
        seed: str,
    ) -> Response:
        """Keep minimal archive/current layouts, replacing all forecasts."""
        sheets: dict[str, tuple[tuple[Any, ...], ...]] = {}
        for name in SHEETS[:2]:
            rows = spreadsheet(response.body, name, self.info.id)
            out: list[tuple[Any, ...]] = [
                ("Forecast Date", "Quarter being forecasted", "GDP Nowcast")
            ]
            out.extend(
                (row[0], row[1], synthetic_value(seed + name, i))
                for i, row in enumerate(rows[-3:])
                if row[0] is not None
            )
            sheets[name] = tuple(out)
        rows = spreadsheet(response.body, "TrackingHistory", self.info.id)
        positions = [i for i, v in enumerate(rows[0]) if i >= 2 and v is not None][-3:]
        sheets["TrackingHistory"] = (
            ("Date", None, *(rows[0][i] for i in positions)),
            (rows[1][0], None, *(None for _ in positions)),
            ("GDP", "GDP Nowcast", *(synthetic_value(seed, i) for i in positions)),
        )
        return replace(response, body=workbook(sheets))
