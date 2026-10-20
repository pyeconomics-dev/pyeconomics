# src/pyeconomics/data/providers/sec_edgar.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""SEC EDGAR's JSON APIs on data.sec.gov, with the user's contact in the User-Agent.

``records`` takes ``submissions:<CIK>`` and returns the company's recent filings
as :class:`~pyeconomics.data.records.Filing` records. ``fetch`` takes

- ``concept:<CIK>:<taxonomy>:<tag>:<unit>:<span>`` (the company concept API),
- ``facts:<CIK>:<taxonomy>:<tag>:<unit>:<span>`` (the same fact, read from the
  company facts API), or
- ``frame:<taxonomy>:<tag>:<unit>:<period>:<CIK>`` (one company's value in the
  frames API, a period such as ``CY2024Q1I``).

``span`` is ``instant``, ``quarter`` or ``year``. A filing reports one tag over
several spans (a 10-Q holds three months and the year to date, both ending on
the same day), so a series keeps only the facts SEC's frames assign to that
span: one per calendar period, from the latest filing. Each value is indexed by
the filer's actual period end, never moved to a calendar date. CIKs are
zero-padded to ten digits; taxonomies, tags and units are identifiers, so a
caller never supplies a path. A ratio unit is ``USD/shares`` in a concept and
``USD-per-shares`` in a frame, as SEC writes them.

edgartools was evaluated and not used: it requires pyarrow and nineteen more
packages (ADR-0011).
"""

from __future__ import annotations

import datetime as dt
import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import UnitKind
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
    ProviderInfo,
    Query,
    RateLimit,
)
from pyeconomics.data.records import Filing, Records
from pyeconomics.data.terms import CachePolicy, Terms
from pyeconomics.data.transport.base import Request, Response, request_path
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

__all__ = ["SecEdgar"]

_ID: Final = "sec_edgar"
_HOST: Final = "data.sec.gov"

_CIK: Final = re.compile(r"[0-9]{1,10}")
_TAG: Final = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,127}")
_UNIT: Final = re.compile(
    r"[A-Za-z][A-Za-z0-9_-]{0,31}(?:/[A-Za-z][A-Za-z0-9_-]{0,31})?"
)
_TAXONOMIES: Final = frozenset({"us-gaap", "ifrs-full", "dei", "srt"})
#: The frames a span keeps: SEC names an instant CY2024Q1I, a quarter CY2024Q1
#: and a year CY2024.
_SPANS: Final = {
    "instant": re.compile(r"CY\d{4}Q[1-4]I"),
    "quarter": re.compile(r"CY\d{4}Q[1-4]"),
    "year": re.compile(r"CY\d{4}"),
}
_PERIOD: Final = re.compile(r"CY\d{4}(?:Q[1-4]I?)?")
_COMPANY_PARTS: Final = len(("concept", "CIK", "taxonomy", "tag", "unit", "span"))
_FRAME_PARTS: Final = len(("frame", "taxonomy", "tag", "unit", "period", "CIK"))
_SUBMISSION_PARTS: Final = len(("submissions", "CIK"))
_CURRENCY: Final = re.compile(r"[A-Z]{3}")

_NOTES: Final = (
    "revised_data: each period holds the value from its latest filing",
    "fiscal_period_end: values are indexed by the filer's actual period end",
)


def cik(value: str) -> str:
    """Return a CIK zero-padded to ten digits, refusing anything but one to ten digits.

    Examples
    --------
    >>> cik("320193")
    '0000320193'

    """
    if not _CIK.fullmatch(value):
        msg = "a sec_edgar CIK is one to ten digits"
        raise DataError(msg, provider=_ID)
    return value.zfill(10)


def _parts(query: Query) -> list[str]:
    if len(query.series) != 1:
        msg = "sec_edgar takes one series per query"
        raise DataError(msg, provider=_ID)
    return query.series[0].split(":")


def _xbrl(taxonomy: str, tag: str, unit: str) -> None:
    """Refuse a taxonomy, tag or unit that is not a documented identifier."""
    if taxonomy not in _TAXONOMIES or not _TAG.fullmatch(tag):
        msg = f"sec_edgar reads the {sorted(_TAXONOMIES)} taxonomies by tag name"
        raise DataError(msg, provider=_ID)
    if not _UNIT.fullmatch(unit):
        msg = "a sec_edgar unit is an identifier such as USD or USD/shares"
        raise DataError(msg, provider=_ID)


def _unit(text: str) -> UnitRecord:
    if _CURRENCY.fullmatch(text):
        return UnitRecord(text=text, kind=UnitKind.MONEY, currency=text)
    if text == "shares":
        return UnitRecord(text=text, kind=UnitKind.COUNT)
    return UnitRecord(text=text)


def _day(raw: object) -> dt.date:
    if not isinstance(raw, str):
        msg = "sec_edgar sent a fact without a date"
        raise ResponseError(msg, provider=_ID)
    try:
        return dt.date.fromisoformat(raw)
    except ValueError:
        msg = "sec_edgar sent a date that is not ISO 8601"
        raise ResponseError(msg, provider=_ID) from None


def _within(day: dt.date, query: Query) -> bool:
    return (query.start is None or day >= query.start) and (
        query.end is None or day <= query.end
    )


class SecEdgar(DataProvider):
    """Filings and XBRL facts from SEC EDGAR; requires the user's SEC contact."""

    info = ProviderInfo(
        id=_ID,
        name="US Securities and Exchange Commission",
        homepage="https://www.sec.gov",
        terms=Terms(
            licence=LicenceClass.HOSTED_SAFE,
            terms_url="https://www.sec.gov/about/privacy-information",
            checked=dt.date(2026, 10, 20),
            attribution="Source: U.S. Securities and Exchange Commission, EDGAR.",
            llm_use=LlmUse.ALLOWED,
            cache=CachePolicy.ALLOWED,
        ),
        auth=Authentication.contact(),
        hosts=(_HOST,),
        capabilities=(Capability.FETCH, Capability.RECORDS),
        # SEC's fair-access limit: ten requests a second in total.
        rate_limits=(RateLimit(requests=10, per="second"),),
        ttl_seconds=3600,
    )
    cases = (
        Case(
            name="submissions",
            operation=Capability.RECORDS,
            argument=Query(
                series=("submissions:320193",),
                start=dt.date(2025, 10, 1),
                end=dt.date(2026, 9, 30),
                max_observations=24,
            ),
        ),
        Case(
            name="concept",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:Assets:USD:instant",),
                start=dt.date(2021, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="facts",
            operation=Capability.FETCH,
            argument=Query(
                series=(
                    (
                        "facts:320193:us-gaap:"
                        "RevenueFromContractWithCustomerExcludingAssessedTax:USD:quarter"
                    ),
                ),
                start=dt.date(2023, 1, 1),
                end=dt.date(2025, 12, 31),
                max_observations=24,
            ),
        ),
        Case(
            name="frame",
            operation=Capability.FETCH,
            argument=Query(
                series=("frame:us-gaap:Assets:USD:CY2024Q1I:320193",),
                max_observations=24,
            ),
        ),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:NonexistentTag:USD:instant",),
                max_observations=24,
            ),
            expect=SeriesNotFoundError,
        ),
        # SEC answers an undeclared client with a 403 and may block its address,
        # so the refusal is simulated, never provoked.
        Case(
            name="error_forbidden",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:Assets:USD:instant",),
                max_observations=24,
            ),
            expect=CredentialError,
            simulate=403,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=Query(
                series=("concept:320193:us-gaap:Assets:USD:instant",),
                max_observations=24,
            ),
            expect=RateLimitError,
            simulate=429,
        ),
    )

    def trim_recording(
        self, request: Request, response: Response, query: Query
    ) -> Response:
        """Keep a handful of genuine filings or facts in the source's format."""
        from pyeconomics.data.transport.recording import trim_response  # noqa: PLC0415

        return trim_response(self.info.id, request, response, query)

    # --- records: submissions ----------------------------------------------------

    def build_records(self, query: Query) -> Sequence[Request]:
        """Build the submissions request for one CIK."""
        parts = _parts(query)
        if len(parts) != _SUBMISSION_PARTS or parts[0] != "submissions":
            msg = "sec_edgar records take submissions:<CIK>"
            raise DataError(msg, provider=_ID)
        path = request_path("submissions", f"CIK{cik(parts[1])}.json")
        return (Request(host=_HOST, path=path, series=query.series[0]),)

    def parse_records(self, responses: Sequence[Response], query: Query) -> Records:
        """Return the recent filings in range, newest first, without document names.

        The submissions file lists a company's latest 1,000 filings or its last
        year, whichever is more; older ones are in files this provider does not read.
        """
        company = cik(_parts(query)[1])
        body = s.body_object(responses[0], _ID)
        filings = body.get("filings")
        recent = filings.get("recent") if isinstance(filings, dict) else None
        if not isinstance(recent, dict):
            msg = "sec_edgar sent submissions without recent filings"
            raise ResponseError(msg, provider=_ID)
        accessions = s.items(recent.get("accessionNumber"), _ID, "accession numbers")
        forms = s.items(recent.get("form"), _ID, "forms")
        filed = s.items(recent.get("filingDate"), _ID, "filing dates")
        reports = s.items(recent.get("reportDate"), _ID, "report dates")
        if not len(accessions) == len(forms) == len(filed) == len(reports):
            msg = "sec_edgar sent filing columns of different lengths"
            raise ResponseError(msg, provider=_ID)
        rows: list[Filing] = []
        for accession, form, day, report in zip(
            accessions, forms, filed, reports, strict=True
        ):
            when = _day(day)
            if not _within(when, query):
                continue
            rows.append(
                Filing(
                    cik=company,
                    accession=accession,
                    form=form,
                    filed=when,
                    report_date=_day(report) if report else None,
                )
            )
            if len(rows) == query.max_observations:
                break
        return Records(
            provider=_ID,
            terms=self.info.terms,
            retrieved_at=responses[0].retrieved_at,
            rows=tuple(rows),
        )

    # --- fetch: XBRL facts ---------------------------------------------------------

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Build a company concept, company facts or frames request."""
        p = _parts(query)
        if len(p) == _COMPANY_PARTS and p[0] in {"concept", "facts"}:
            _xbrl(p[2], p[3], p[4])
            if p[5] not in _SPANS:
                msg = f"a sec_edgar span is one of {sorted(_SPANS)}"
                raise DataError(msg, provider=_ID)
            company = f"CIK{cik(p[1])}"
            segments: tuple[str, ...] = (
                ("companyfacts", f"{company}.json")
                if p[0] == "facts"
                else ("companyconcept", company, p[2], f"{p[3]}.json")
            )
        elif len(p) == _FRAME_PARTS and p[0] == "frame":
            _xbrl(p[1], p[2], p[3])
            cik(p[5])
            if "/" in p[3]:
                msg = "a sec_edgar frame names a ratio unit as USD-per-shares"
                raise DataError(msg, provider=_ID)
            if not _PERIOD.fullmatch(p[4]):
                msg = "a sec_edgar frame period is CY2024, CY2024Q1 or CY2024Q1I"
                raise DataError(msg, provider=_ID)
            segments = ("frames", p[1], p[2], p[3], f"{p[4]}.json")
        else:
            msg = (
                "sec_edgar fetches concept:<CIK>:<taxonomy>:<tag>:<unit>:<span>, "
                "facts:<CIK>:<taxonomy>:<tag>:<unit>:<span> or "
                "frame:<taxonomy>:<tag>:<unit>:<period>:<CIK>"
            )
            raise DataError(msg, provider=_ID)
        path = request_path("api", "xbrl", *segments)
        return (Request(host=_HOST, path=path, series=query.series[0]),)

    def parse(self, responses: Sequence[Response], query: Query) -> Series:
        """Return one value per period end, in the requested unit and span."""
        p = _parts(query)
        body = s.body_object(responses[0], _ID)
        if p[0] == "frame":
            unit = p[3]
            company = int(cik(p[5]))
            facts = [
                row
                for row in s.items(body.get("data"), _ID, "frame data")
                if isinstance(row, dict) and row.get("cik") == company
            ]
        else:
            unit = p[4]
            if p[0] == "facts":
                body = _member(_member(body.get("facts"), p[2]), p[3])
            span = _SPANS[p[5]]
            facts = [
                row
                for row in _member(body.get("units"), unit) or []
                if isinstance(row, dict)
                and isinstance(row.get("frame"), str)
                and span.fullmatch(row["frame"])
            ]
        latest: dict[dt.date, tuple[str, str, float | None]] = {}
        for row in facts:
            day = _day(row.get("end"))
            if not _within(day, query):
                continue
            order = (str(row.get("filed", "")), str(row.get("accn", "")))
            if day not in latest or order >= latest[day][:2]:
                latest[day] = (*order, s.number(row.get("val"), _ID))
        if not latest:
            raise SeriesNotFoundError(_ID, query.series[0])
        index = tuple(sorted(latest))[-query.max_observations :]
        return Series(
            index,
            tuple(latest[day][2] for day in index),
            SeriesMeta(
                provider=_ID,
                series_id=query.series[0],
                title=query.series[0],
                unit=_unit(unit),
                frequency=ObservationFrequency.IRREGULAR,
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
                source_dating=DateConvention.PERIOD_END,
                terms=self.info.terms,
                retrieved_at=responses[0].retrieved_at,
                notes=_NOTES,
            ),
        )


def _member(mapping: object, key: str) -> Any:  # noqa: ANN401 - parsed JSON
    """Return a JSON object's member, or ``None`` when it is absent."""
    return mapping.get(key) if isinstance(mapping, dict) else None
