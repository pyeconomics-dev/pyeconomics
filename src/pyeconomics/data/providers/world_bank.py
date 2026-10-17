# src/pyeconomics/data/providers/world_bank.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""World Bank v2: ``source/country/indicator`` ids, per-series licence metadata.

For example ``2/USA/NY.GDP.MKTP.CD`` selects WDI GDP in current US dollars.
Country and indicator syntax is constrained and their identities are checked
against the API. An absent or unfamiliar License_Type is library-only.
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

__all__ = ["WorldBank"]

_MAX_PAGE = 1_000_000
HOST = "api.worldbank.org"
TERMS = Terms(
    licence=LicenceClass.HOSTED_SAFE,
    terms_url="https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
    checked=dt.date(2026, 10, 16),
    attribution="The World Bank: Dataset name: Data source (if known).",
    notice=None,
    llm_use=LlmUse.ALLOWED,
    cache=CachePolicy.ALLOWED,
)
_ID = re.compile(r"([1-9][0-9]{0,3})/([A-Z]{2,3})/([A-Z0-9_][A-Z0-9_.]{1,63})")
_SAMPLE = Query(
    series=("2/USA/NY.GDP.MKTP.CD",),
    start=dt.date(2022, 1, 1),
    end=dt.date(2023, 12, 31),
    max_observations=24,
)


def selection(series_id: str) -> tuple[str, str, str]:
    """Validate and split a World Bank series id."""
    match = _ID.fullmatch(series_id)
    if match is None:
        msg = "a world_bank id is source/country/indicator"
        raise DataError(msg, provider="world_bank")
    return match[1], match[2], match[3]


def metadata(body: object) -> dict[str, str]:
    """Read the API's nested metatype records, without assuming a licence."""
    found: dict[str, str] = {}

    def visit(value: object) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("id"), str) and isinstance(value.get("value"), str):
                found[value["id"]] = value["value"]
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(body)
    return found


def page_number(raw: object) -> int:
    """Read bounded pagination without echoing an untrusted value in an error."""
    if isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw <= _MAX_PAGE:
        return raw
    if isinstance(raw, str) and re.fullmatch(r"[0-9]{1,6}", raw):
        return int(raw)
    msg = "World Bank sent invalid pagination metadata"
    raise ResponseError(msg, provider="world_bank")


def series_terms(fields: dict[str, str], source: str) -> Terms:
    """Only an explicit CC BY 4.0 marker permits hosted reuse."""
    licence = fields.get("License_Type", "").strip().upper().replace("-", " ")
    allowed = licence in {"CC BY 4.0", "CREATIVE COMMONS ATTRIBUTION 4.0"}
    attribution = " ".join(
        re.sub(
            r"https?://[^\s]+",
            "",
            f"The World Bank: {source}: {fields.get('Source', 'World Bank')}",
        ).split()
    )[:1000]
    return replace(
        TERMS,
        licence=LicenceClass.HOSTED_SAFE if allowed else LicenceClass.LIBRARY_ONLY,
        attribution=attribution,
        llm_use=LlmUse.ALLOWED if allowed else LlmUse.UNCLEAR,
        cache=CachePolicy.ALLOWED if allowed else CachePolicy.FORBIDDEN,
    )


class WorldBank(DataProvider):
    """Indicator observations with pagination and source-specific terms."""

    info = ProviderInfo(
        id="world_bank",
        name="World Bank",
        homepage="https://data.worldbank.org",
        terms=TERMS,
        hosts=(HOST,),
        rate_limits=(RateLimit(requests=5, per="second"),),
    )
    cases: ClassVar = (
        Case(name="fetch_ok", operation=Capability.FETCH, argument=_SAMPLE),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(series=("2/USA/NO_SUCH_INDICATOR",), max_observations=24),
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
        """Read licence metadata, indicator, country and dated data per selection."""
        requests = []
        for series_id in query.series:
            source, country, indicator = selection(series_id)
            paths = [
                request_path("v2", "sources", source, "series", indicator, "metadata"),
                request_path("v2", "indicator", indicator),
                request_path("v2", "country", country),
                request_path("v2", "country", country, "indicator", indicator),
            ]
            for index, path in enumerate(paths):
                params = [("format", "json"), ("per_page", "1000")]
                if index in {1, 3}:
                    params.append(("source", source))
                if index == 3 and (query.start or query.end):  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
                    params.append(
                        (
                            "date",
                            (
                                f"{query.start.year if query.start else 1700}:"
                                f"{query.end.year if query.end else 2200}"
                            ),
                        )
                    )
                requests.append(
                    Request(
                        host=HOST, path=path, params=tuple(params), series=series_id
                    )
                )
        return tuple(requests)

    def next_page(self, request: Request, response: Response) -> Request | None:
        """Follow every v2 list page, bounded by the base operation ceiling."""
        if (
            response.body.strip() in {b"No Results", b"No results", b"No Results Found"}
            or b'<wb:message id="160"' in response.body
        ):
            raise SeriesNotFoundError(self.info.id, request.series or "unknown")
        body = response.json(provider=self.info.id)
        if isinstance(body, list) and body and isinstance(body[0], dict):
            page = page_number(body[0].get("page", 1))
            pages = page_number(body[0].get("pages", 1))
            if page < pages:
                params = dict(request.params)
                params["page"] = str(page + 1)
                return replace(request, params=tuple(params.items()))
        return None

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Build annual frames, retaining missing values and each series' class."""
        frames = []
        position = 0
        for series_id in query.series:
            fields: dict[str, str] = {}
            indicator_rows: list[Any] = []
            country_rows: list[Any] = []
            data_rows: list[Any] = []
            for rows in (None, indicator_rows, country_rows, data_rows):
                while True:
                    body = responses[position].json(provider=self.info.id)
                    position += 1
                    if rows is None:
                        fields = metadata(body)
                        break
                    if (
                        not isinstance(body, list)
                        or len(body) != 2  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
                        or not isinstance(body[1], list)
                    ):
                        raise SeriesNotFoundError(self.info.id, series_id)
                    rows.extend(body[1])
                    if page_number(body[0].get("page", 1)) >= page_number(
                        body[0].get("pages", 1)
                    ):
                        break
            _, country, indicator = selection(series_id)
            self._require_identity(indicator_rows, country_rows, indicator, series_id)
            identity = country_rows[0]
            if country not in {identity.get("id"), identity.get("iso2Code")}:
                raise SeriesNotFoundError(self.info.id, series_id)
            title = str(indicator_rows[0].get("name", indicator))[:1000]
            units, percent = i.unit(str(indicator_rows[0].get("unit") or title))
            values: dict[dt.date, float | None] = {}
            for row in data_rows:
                if row.get("indicator", {}).get("id") != indicator or row.get(
                    "countryiso3code"
                ) not in {None, "", identity.get("id")}:
                    msg = "World Bank returned another selection"
                    raise ResponseError(msg, provider=self.info.id)
                day, _ = i.period(str(row.get("date")), self.info.id)
                value = (
                    None
                    if row.get("value") is None
                    else s.number(row["value"], self.info.id)
                )
                values[day] = s.rate_or_value(value, percent=percent)
            meta = SeriesMeta(
                provider=self.info.id,
                series_id=series_id,
                dataset="World Bank indicators",
                title=title,
                unit=units,
                frequency=ObservationFrequency.ANNUAL,
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
                source_dating=DateConvention.PERIOD_END,
                terms=series_terms(
                    fields,
                    str(
                        indicator_rows[0]
                        .get("source", {})
                        .get("value", "World Bank indicators")
                    ),
                ),
                retrieved_at=responses[position - 1].retrieved_at,
                notes=(
                    "revised_data",
                    f"license_type: {fields.get('License_Type', 'unspecified')}",
                    f"accessed: {responses[position - 1].retrieved_at.date()}",
                ),
            )
            frames.append(
                i.window(
                    Series(
                        tuple(sorted(values)),
                        tuple(values[d] for d in sorted(values)),
                        meta,
                    ),
                    query,
                )
            )
        return i.combine(frames, query)

    def _require_identity(
        self,
        indicators: list[Any],
        countries: list[Any],
        indicator: str,
        series_id: str,
    ) -> None:
        """Require source metadata for the selected indicator and country."""
        if not indicators or indicators[0].get("id") != indicator or not countries:
            raise SeriesNotFoundError(self.info.id, series_id)

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """Map HTTP 400 unknown indicators to the not-found taxonomy."""
        return (
            SeriesNotFoundError(self.info.id, request.series or "unknown")
            if response.status == 400  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
            else None
        )

    def synthesize(
        self,
        request: Request,
        response: Response,
        *,
        seed: str,
    ) -> Response:
        """Replace numeric observations for a restricted series recording."""
        body = response.json(provider=self.info.id)
        if isinstance(body, list) and len(body) == 2 and isinstance(body[1], list):  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
            for index, row in enumerate(body[1]):
                if isinstance(row, dict) and row.get("value") is not None:
                    row["value"] = synthetic_value(seed, index)
        return replace(response, body=json.dumps(body).encode())

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep the source's licence and identity metadata without long essays."""
        if (
            not response.ok
            or not request.path.endswith("/metadata")
            or response.body.lstrip().startswith(b"<?xml")
        ):
            return response
        fields = metadata(response.json(provider=self.info.id))
        kept = {
            k: " ".join(v.split())[:500]
            for k, v in fields.items()
            if k in {"License_Type", "IndicatorName", "Source"}
        }
        body = {"metatype": [{"id": k, "value": v} for k, v in kept.items()]}
        return replace(response, body=json.dumps(body).encode())
