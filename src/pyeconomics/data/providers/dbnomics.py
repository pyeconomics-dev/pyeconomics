# src/pyeconomics/data/providers/dbnomics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""DBnomics REST v22, library-only, retaining its upstream source's attribution.

Ids are ``provider/dataset/series``. No DBnomics client is imported: its AGPL
licence is excluded by ADR-0004. Aggregation does not grant upstream rights.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Any, ClassVar

from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
)
from pyeconomics.data.providers import _international as i
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Capability,
    Case,
    DataProvider,
    ProviderInfo,
    Query,
    RateLimit,
    SearchHit,
)
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, request_path
from pyeconomics.data.transport.cassette import synthetic_value
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["Dbnomics"]

_DATASET_PARTS = 2
HOST = "api.db.nomics.world"
TERMS = Terms(
    licence=LicenceClass.LIBRARY_ONLY,
    terms_url="https://db.nomics.world/about",
    checked=dt.date(2026, 10, 16),
    attribution="Source: DBnomics and the original data provider.",
    notice=(
        "Data distributed by DBnomics is subject to the same license "
        "and terms of use as its original source provider."
    ),
    llm_use=LlmUse.UNCLEAR,
    cache=CachePolicy.FORBIDDEN,
)
_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.@-]{0,63}")
_SAMPLE = Query(
    series=("ECB/EXR/A.USD.EUR.SP00.A",),
    start=dt.date(2022, 1, 1),
    end=dt.date(2023, 12, 31),
    max_observations=24,
)


def selection(series_id: str) -> tuple[str, str, str]:
    """Refuse selectors that could change a REST path."""
    parts = series_id.split("/")
    if len(parts) != 3 or not all(_TOKEN.fullmatch(part) for part in parts):  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
        msg = "a dbnomics id is provider/dataset/series"
        raise DataError(msg, provider="dbnomics")
    return parts[0], parts[1], parts[2]


class Dbnomics(DataProvider):
    """Fetch and search the API without a third-party data client."""

    info = ProviderInfo(
        id="dbnomics",
        name="DBnomics",
        homepage="https://db.nomics.world",
        terms=TERMS,
        hosts=(HOST,),
        rate_limits=(RateLimit(requests=5, per="second"),),
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
    )
    cases: ClassVar = (
        Case(
            name="search_datasets",
            operation=Capability.SEARCH,
            argument="dataset:exchange rate",
        ),
        Case(name="fetch_ok", operation=Capability.FETCH, argument=_SAMPLE),
        Case(
            name="search_ok",
            operation=Capability.SEARCH,
            argument="series:ECB/EXR:dollar",
        ),
        Case(
            name="describe_ok",
            operation=Capability.DESCRIBE,
            argument=_SAMPLE.series[0],
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(series=("ECB/EXR/NO_SUCH_SERIES",), max_observations=24),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=_SAMPLE,
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Request observations with metadata; slicing stays explicit locally."""
        return tuple(
            Request(
                host=HOST,
                path=request_path("v22", "series", *selection(series_id)),
                params=(("observations", "1"), ("metadata", "1")),
                series=series_id,
            )
            for series_id in query.series
        )

    def build_describe(self, series_id: str) -> Sequence[Request]:
        """Ask for series metadata without observations."""
        return (
            Request(
                host=HOST,
                path=request_path("v22", "series", *selection(series_id)),
                params=(("observations", "0"), ("metadata", "1")),
                series=series_id,
            ),
        )

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        """Search series, or datasets with the explicit ``dataset:`` prefix."""
        path = "/v22/search"
        query = text.removeprefix("dataset:")
        params = [("limit", str(limit))]
        if text.startswith("series:"):
            dataset, separator, query = text.removeprefix("series:").partition(":")
            parts = dataset.split("/")
            if (
                not separator
                or len(parts) != _DATASET_PARTS
                or not all(_TOKEN.fullmatch(part) for part in parts)
            ):
                msg = "series search is series:provider/dataset:text"
                raise DataError(msg, provider=self.info.id)
            path = request_path("v22", "series", *parts)
            params += [("observations", "0"), ("metadata", "0")]
        params.append(("q", query))
        return (Request(host=HOST, path=path, params=tuple(params)),)

    def parse_search(
        self, responses: Sequence[Response], text: str, limit: int
    ) -> Sequence[SearchHit]:
        """Keep provider/dataset identity on every search hit."""
        body = s.body_object(responses[0], self.info.id)
        is_series = text.startswith("series:")
        section = body.get("series" if is_series else "results", {})
        hits = []
        for row in s.items(section.get("docs"), self.info.id, "search results")[:limit]:
            series_id = (
                str(row.get("provider_code", ""))
                + "/"
                + str(row.get("dataset_code", row.get("code", "")))
            )
            if is_series:
                series_id += f"/{row.get('series_code', '')}"
            hits.append(
                SearchHit(
                    series_id=series_id,
                    title=str(row.get("series_name") or row.get("name") or series_id)[
                        :1000
                    ],
                )
            )
        return tuple(hits)

    def _metadata(
        self, response: Response, series_id: str
    ) -> tuple[SeriesMeta, dict[str, Any]]:
        body = s.body_object(response, self.info.id)
        rows = s.items(body.get("series", {}).get("docs"), self.info.id, "series")
        if not rows:
            raise SeriesNotFoundError(self.info.id, series_id)
        row = rows[0]
        provider, dataset, code = selection(series_id)
        if (
            row.get("provider_code"),
            row.get("dataset_code"),
            row.get("series_code"),
        ) != (provider, dataset, code):
            msg = "DBnomics returned another series"
            raise ResponseError(msg, provider=self.info.id)
        units, _ = i.unit(
            str(
                row.get("unit")
                or row.get("dimensions", {}).get("UNIT", "Not specified by source")
            )
        )
        frequency = {
            "A": ObservationFrequency.ANNUAL,
            "Q": ObservationFrequency.QUARTERLY,
            "M": ObservationFrequency.MONTHLY,
            "D": ObservationFrequency.DAILY,
        }.get(
            str(row.get("@frequency") or row.get("frequency") or code.split(".")[0]),
            ObservationFrequency.IRREGULAR,
        )
        source = str(body.get("provider", {}).get("name") or provider)
        terms = replace(
            TERMS,
            attribution=(
                f"Source: {source}, {dataset}; via DBnomics; "
                f"accessed {response.retrieved_at.date()}."
            ),
        )
        return SeriesMeta(
            provider=self.info.id,
            series_id=series_id,
            dataset=f"{provider}/{dataset}",
            title=str(row.get("series_name") or series_id)[:1000],
            unit=units,
            frequency=frequency,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            source_dating=DateConvention.PERIOD_START,
            terms=terms,
            retrieved_at=response.retrieved_at,
            notes=("revised_data",),
        ), row

    def parse_describe(
        self, responses: Sequence[Response], series_id: str
    ) -> SeriesMeta:
        """Describe the source and its upstream rights."""
        return self._metadata(responses[0], series_id)[0]

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Convert source periods and missing markers, keeping decimal rates."""
        frames = []
        for response, series_id in zip(responses, query.series, strict=True):
            meta, row = self._metadata(response, series_id)
            periods = s.items(row.get("period"), self.info.id, "periods")
            raw = s.items(row.get("value"), self.info.id, "values")
            if len(periods) != len(raw):
                msg = "DBnomics period and value lengths differ"
                raise ResponseError(msg, provider=self.info.id)
            values = {}
            frequency = meta.frequency
            _, percent = i.unit(meta.unit.text)
            for p, v in zip(periods, raw, strict=True):
                day, frequency = i.period(str(p), self.info.id)
                value = (
                    None
                    if v is None
                    else s.number(v, self.info.id, missing=("NA", "NaN"))
                )
                values[day] = s.rate_or_value(value, percent=percent)
            meta = replace(meta, frequency=frequency)
            days = tuple(sorted(values))
            frames.append(
                i.window(Series(days, tuple(values[d] for d in days), meta), query)
            )
        return i.combine(frames, query)

    def synthesize(
        self,
        request: Request,
        response: Response,
        *,
        seed: str,
    ) -> Response:
        """Replace all observed values, retaining only 24 periods per series."""
        body = s.body_object(response, self.info.id)
        for row in body.get("series", {}).get("docs", []):
            if "value" not in row:
                continue
            values = row["value"][-24:]
            row["value"] = [
                None if value in {None, "NA", "NaN"} else synthetic_value(seed, index)
                for index, value in enumerate(values)
            ]
            for name in ("period", "period_start_day", "original_period"):
                if isinstance(row.get(name), list):
                    row[name] = row[name][-24:]
        # Dataset dimension labels can exceed the cassette limit by themselves.
        for row in body.get("results", {}).get("docs", []):
            row.pop("description", None)
        dataset = body.get("dataset")
        if isinstance(dataset, dict):
            dataset.pop("dimensions_values_labels", None)
        return replace(response, body=json.dumps(body).encode())

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Remove large dimension-label catalogs, retaining the series metadata."""
        if not response.ok:
            return response
        body = s.body_object(response, self.info.id)
        for row in body.get("results", {}).get("docs", []):
            row.pop("description", None)
        dataset = body.get("dataset")
        if isinstance(dataset, dict):
            dataset.pop("dimensions_values_labels", None)
        return replace(response, body=json.dumps(body).encode())
