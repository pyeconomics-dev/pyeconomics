# src/pyeconomics/data/providers/openfigi.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""OpenFIGI v3 mapping: ``records(Query(series=(\"TICKER:IBM\",)))``.

Each id consists of an allowlisted identifier type and a value. The optional
key raises the job cap from 10 to 100 and the request limit from 25 to 250 per
minute. Mapping results are typed records and cannot be bound to a model.
"""

from __future__ import annotations

import datetime as dt
from typing import TYPE_CHECKING, Final

from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.errors import (
    CredentialError,
    DataError,
    RateLimitError,
    ResponseError,
    SeriesNotFoundError,
)
from pyeconomics.data.providers import _shared as s
from pyeconomics.data.providers.base import (
    Authentication,
    Capability,
    Case,
    DataProvider,
    KeyPlacement,
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.records import FigiMapping, Records
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = ["OpenFigi"]

_ID: Final = "openfigi"

_TYPES: Final = frozenset(
    {
        "ID_BB_GLOBAL",
        "COMPOSITE_ID_BB_GLOBAL",
        "ID_ISIN",
        "ID_CUSIP",
        "ID_SEDOL",
        "TICKER",
        "ID_BB_UNIQUE",
        "ID_EXCH_SYMBOL",
        "BASE_TICKER",
    }
)
_FIELDS: Final = {
    "ticker": "ticker",
    "name": "name",
    "exchCode": "exchange",
    "marketSector": "market_sector",
    "securityType": "security_type",
    "compositeFIGI": "composite_figi",
    "shareClassFIGI": "share_class_figi",
}


class OpenFigi(DataProvider):
    """Identifier mapping, with optional OPENFIGI_API_KEY authentication."""

    info = ProviderInfo(
        id="openfigi",
        name="OpenFIGI",
        homepage="https://www.openfigi.com",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.openfigi.com/docs/terms-of-service",
            checked=dt.date(2026, 10, 16),
            attribution="Source: Bloomberg, OpenFIGI.",
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        hosts=("api.openfigi.com",),
        capabilities=(Capability.RECORDS,),
        auth=Authentication.key(
            "X-OPENFIGI-APIKEY", KeyPlacement.HEADER, required=False
        ),
        rate_limits=(
            RateLimit(requests=250, per="minute"),
            RateLimit(requests=25, per="minute", without_key=True),
        ),
    )
    cases = (
        Case(
            name="mapping",
            operation=Capability.RECORDS,
            argument=Query(series=("ID_BB_GLOBAL:BBG000BLNNH6",), max_observations=24),
            keyless=True,
        ),
        Case(
            name="error_not_found",
            operation=Capability.RECORDS,
            argument=Query(series=("ID_BB_GLOBAL:BBG000000000",), max_observations=24),
            expect=SeriesNotFoundError,
            keyless=True,
        ),
        Case(
            name="error_unauthorized",
            operation=Capability.RECORDS,
            argument=Query(series=("ID_BB_GLOBAL:BBG000BLNNH6",), max_observations=24),
            expect=CredentialError,
            invalid_key=True,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.RECORDS,
            argument=Query(series=("ID_BB_GLOBAL:BBG000BLNNH6",), max_observations=24),
            expect=RateLimitError,
            simulate=429,
            keyless=True,
        ),
    )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep a handful of genuine observations in the source's format."""
        from pyeconomics.data.transport.recording import trim_response  # noqa: PLC0415

        return trim_response(self.info.id, request, response, query)

    def build_records(self, query: Query) -> Sequence[Request]:
        """Batch mapping jobs at the authenticated or keyless cap."""
        jobs = []
        for identifier in query.series:
            kind, separator, value = identifier.partition(":")
            if not separator or kind not in _TYPES or not value:
                msg = "openfigi ids are an allowed identifier type followed by :value"
                raise DataError(msg, provider="openfigi")
            jobs.append({"idType": kind, "idValue": value})
        cap = 100 if self.sends_key else 10
        return tuple(
            Request(
                host="api.openfigi.com",
                path="/v3/mapping",
                method="POST",
                body=jobs[i : i + cap],
            )
            for i in range(0, len(jobs), cap)
        )

    def parse_records(self, responses: Sequence[Response], query: Query) -> Records:
        """Keep each result associated with its input identifier; reject job errors."""
        results = [
            item
            for response in responses
            for item in s.items(
                response.json(provider="openfigi"), "openfigi", "mapping results"
            )
        ]
        if len(results) != len(query.series):
            msg = "openfigi returned a different number of jobs"
            raise ResponseError(msg, provider="openfigi")
        rows = []
        for identifier, result in zip(query.series, results, strict=True):
            if not isinstance(result, dict) or result.get("error"):
                msg = "openfigi could not process a mapping job"
                raise ResponseError(msg, provider="openfigi")
            if result.get("warning") or not result.get("data"):
                msg = "openfigi found no instrument for an identifier"
                raise SeriesNotFoundError(_ID, query.series[0])
            kind, _, value = identifier.partition(":")
            for item in s.items(result["data"], "openfigi", "instruments"):
                rows.append(
                    FigiMapping(
                        identifier_type=kind,
                        identifier=value,
                        figi=s.text(item, "figi", "openfigi"),
                        **{dest: item.get(source) for source, dest in _FIELDS.items()},
                    )
                )
                if len(rows) > query.max_observations:
                    msg = "openfigi mapping exceeds max_observations; narrow the query"
                    raise DataError(msg, provider="openfigi")
        return Records(
            provider="openfigi",
            terms=self.info.terms,
            retrieved_at=responses[-1].retrieved_at,
            rows=tuple(rows),
        )
