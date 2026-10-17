# src/pyeconomics/data/providers/_sdmx.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Structure-aware SDMX provider hooks shared by the five official sources.

Ids are ``agency/flow/key``; keys name exactly one value per non-time
dimension, in the order published by the dataflow's structure. Fetch several
ids for a table. No positional key is sent before its structure validates it.
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import replace
from typing import TYPE_CHECKING, Any, ClassVar

from pyeconomics.core import UnitKind
from pyeconomics.core._optional import import_optional
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
    SearchHit,
)
from pyeconomics.data.transport import default_transport
from pyeconomics.data.transport.base import Request, Response, request_path
from pyeconomics.data.transport.sdmx import (
    data_codes,
    flows,
    read_xml,
    send,
    synthetic_xml,
    trim_data,
    trim_xml,
    xml_body,
)
from pyeconomics.data.types import (
    DateConvention,
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    SeriesMeta,
    Table,
    UnitRecord,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.data.credentials import Secret
    from pyeconomics.data.terms import Terms
    from pyeconomics.data.transport.base import Transport

_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.@-]{0,63}")
_MAX_UNIT_MULTIPLIER = 15
_GEO = frozenset(
    [
        "AT",
        "BE",
        "BG",
        "HR",
        "CY",
        "CZ",
        "DK",
        "EE",
        "FI",
        "FR",
        "DE",
        "EL",
        "GR",
        "HU",
        "IE",
        "IT",
        "LV",
        "LT",
        "LU",
        "MT",
        "NL",
        "PL",
        "PT",
        "RO",
        "SK",
        "SI",
        "ES",
        "SE",
        "IS",
        "LI",
        "NO",
        "CH",
        "AL",
        "BA",
        "GE",
        "MD",
        "ME",
        "MK",
        "RS",
        "TR",
        "UA",
        "XK",
        "EU",
        "EU27_2020",
        "EU28",
        "EA",
        "EA19",
        "EA20",
        "EA21",
        "EEA",
        "EFTA",
    ]
)


def selection(series_id: str) -> tuple[str, str, str]:
    """Read an agency, flow and fully specified series key."""
    parts = series_id.split("/")
    if len(parts) != 3 or not all(_TOKEN.fullmatch(part) for part in parts):  # noqa: PLR2004 - fixed REST shape, HTTP status or response size bound
        msg = "an SDMX id is agency/flow/key with plain code tokens"
        raise DataError(msg)
    return parts[0], parts[1], parts[2]


def cases(
    sample: str,
    search: str,
    *,
    start: dt.date = dt.date(2022, 1, 1),
    end: dt.date = dt.date(2023, 12, 31),
) -> tuple[Case, ...]:
    """Declare capability and error recordings shared by the SDMX sources."""
    query = Query(
        series=(sample,),
        start=start,
        end=end,
        max_observations=2,
    )
    agency, _, key = selection(sample)
    return (
        Case(name="fetch_ok", operation=Capability.FETCH, argument=query),
        Case(name="describe_ok", operation=Capability.DESCRIBE, argument=sample),
        Case(name="search_ok", operation=Capability.SEARCH, argument=search),
        Case(
            name="error_not_found",
            operation=Capability.FETCH,
            argument=Query(
                series=(f"{agency}/NO_SUCH_FLOW/{key}",), max_observations=24
            ),
            expect=SeriesNotFoundError,
        ),
        Case(
            name="error_rate_limited",
            operation=Capability.FETCH,
            argument=query,
            expect=RateLimitError,
            simulate=429,
        ),
    )


def structure(response: Response, flow_id: str, provider: str) -> tuple[Any, Any]:
    """Return the dataflow and resolved DSD, refusing incomplete structures."""
    message = read_xml(response.body, provider)
    flow = next(
        (v for k, v in message.dataflow.items() if k.casefold() == flow_id.casefold()),
        None,
    )
    if (
        flow is None
        or flow.structure is None
        or not flow.structure.dimensions.components
    ):
        msg = "SDMX dataflow has no resolved structure"
        raise ResponseError(msg, provider=provider)
    return flow, flow.structure


def validate_key(dsd: Any, key: str, provider: str) -> dict[str, str]:  # noqa: ANN401 - lazy optional sdmx1 and lxml APIs are untyped
    """Validate the number, ordering and enumerated values of key dimensions."""
    dimensions = [
        dim
        for dim in dsd.dimensions.components
        if type(dim).__name__ != "TimeDimension"
    ]
    values = key.split(".")
    if len(dimensions) != len(values):
        msg = "SDMX key has the wrong number of dimensions"
        raise DataError(msg, provider=provider)
    selected = {}
    for dim, value in zip(dimensions, values, strict=True):
        representation = (
            dim.local_representation or dim.concept_identity.core_representation
        )
        codes = representation.enumerated if representation is not None else None
        if codes is None or value not in codes.items:
            msg = f"SDMX key contains an unknown {dim.id} code"
            raise DataError(msg, provider=provider)
        selected[dim.id] = value
    return selected


def restricted_terms(
    info: ProviderInfo, dimensions: dict[str, str], annotations: str, accessed: dt.date
) -> Terms:
    """Apply Eurostat exceptions and explicit third-party/restriction markers."""
    terms = info.terms
    markers = annotations.casefold()
    restricted = any(
        marker in markers
        for marker in (
            "third party",
            "third-party",
            "non-commercial",
            "all rights reserved",
            "permission required",
        )
    )
    if info.id == "eurostat":
        geo = dimensions.get("geo", dimensions.get("REF_AREA", ""))
        # An unclassified geography is refused conservatively, including
        # aggregates not explicitly covered by the source's permission.
        restricted |= geo not in _GEO
        declaring = dimensions.get("reporter", dimensions.get("DECLARANT", geo))
        commodity = dimensions.get("product", dimensions.get("PRODUCT", ""))
        restricted |= declaring in {"CH", "LI"} and bool(commodity)
        restricted |= declaring == "AT" and bool(re.fullmatch(r"\d{8}", commodity))
    if restricted:
        terms = replace(
            terms,
            licence=LicenceClass.LIBRARY_ONLY,
            llm_use=terms.llm_use
            if terms.llm_use is LlmUse.FORBIDDEN
            else LlmUse.UNCLEAR,
        )
    return replace(terms, attribution=f"{terms.attribution} Accessed {accessed}.")


class SdmxProvider(DataProvider):
    """Hooks for an official SDMX-ML 2.1 service; transport remains confined."""

    root: ClassVar[str]
    search_agency: ClassVar[str] = "all"
    references: ClassVar[str] = "all"

    def _request(
        self,
        path: str,
        *,
        series_id: str | None = None,
        params: tuple[tuple[str, str], ...] = (),
    ) -> Request:
        return Request(
            host=self.info.hosts[0],
            path=path,
            params=params,
            headers=(
                (
                    "Accept",
                    (
                        "application/vnd.sdmx.structurespecificdata+xml;version=2.1"
                        if self.info.id == "imf"
                        else "application/vnd.sdmx.genericdata+xml;version=2.1"
                    )
                    if "/data/" in path
                    else "application/vnd.sdmx.structure+xml;version=2.1",
                ),
            ),
            series=series_id,
        )

    def build_requests(self, query: Query) -> Sequence[Request]:
        """Lazily load the extra, then request the structure before each series."""
        import_optional("sdmx", extra="sdmx")
        requests: list[Request] = []
        for series_id in query.series:
            agency, flow, key = selection(series_id)
            params = []
            if query.start:
                params.append(("startPeriod", query.start.isoformat()))
            if query.end:
                params.append(("endPeriod", query.end.isoformat()))
            params.append(("lastNObservations", str(query.max_observations)))
            requests.extend(
                (
                    self._request(
                        self.root + request_path("dataflow", agency, flow, "latest"),
                        series_id=series_id,
                        params=(("references", self.references),),
                    ),
                    self._request(
                        self.root
                        + request_path(
                            "data",
                            flow
                            if self.info.id in {"bis", "eurostat"}
                            else f"{agency},{flow},latest",
                            key,
                        ),
                        series_id=series_id,
                        params=tuple(params),
                    ),
                )
            )
        return tuple(requests)

    def exchange(
        self,
        requests: Sequence[Request],
        *,
        key: str | Secret | None,
        transport: Transport | None,
    ) -> Sequence[Response]:
        """Check dimension values before sending data; all traffic uses the adapter."""
        active = transport if transport is not None else default_transport()
        responses: list[Response] = []
        for built in requests:
            request = built
            if "/data/" in request.path:
                _, flow, series_key = selection(request.series or "")
                resolved_flow, dsd = structure(responses[-1], flow, self.info.id)
                if self.info.id == "oecd":
                    request = replace(
                        request,
                        path=request.path.replace("%2C", ",")
                        .replace("%40", "@")
                        .replace(",latest/", f",{resolved_flow.version}/"),
                    )
                validate_key(dsd, series_key, self.info.id)
            response = send(self.info, request, active)
            if response.status == 204:  # noqa: PLR2004 - HTTP no content
                raise SeriesNotFoundError(self.info.id, request.series or "unknown")
            self._check_status(request, response)
            responses.append(response)
        return tuple(responses)

    def build_search(self, text: str, limit: int) -> Sequence[Request]:
        """Search all published dataflow titles locally, from official structures."""
        import_optional("sdmx", extra="sdmx")
        return (
            self._request(
                self.root
                + request_path("dataflow", self.search_agency, "all", "latest"),
                params=(("references", "none"),),
            ),
        )

    def parse_search(
        self, responses: Sequence[Response], text: str, limit: int
    ) -> Sequence[SearchHit]:
        """Return matching dataflows with their official agency and flow ids."""
        hits = []
        for agency, flow_id, title in flows(responses[0].body, self.info.id):
            candidate = f"{agency}/{flow_id}"
            if not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_.@/-]{0,127}", candidate):
                continue
            if text.casefold() in f"{flow_id} {title}".casefold():
                hits.append(SearchHit(series_id=candidate, title=title[:1000]))
        return tuple(hits[:limit])

    def build_describe(self, series_id: str) -> Sequence[Request]:
        """Use one observation to obtain the structure and series-level attributes."""
        return self.build_requests(Query(series=(series_id,), max_observations=1))

    def parse_describe(
        self, responses: Sequence[Response], series_id: str
    ) -> SeriesMeta:
        """Return the same licence and units a fetch would carry."""
        frame = self.parse(responses, Query(series=(series_id,), max_observations=1))
        if not isinstance(frame, Series):
            msg = "SDMX describe returned several series"
            raise ResponseError(msg, provider=self.info.id)
        return frame.meta

    def parse(self, responses: Sequence[Response], query: Query) -> Series | Table:
        """Convert SDMX observations into typed, period-end, decimal frames."""
        frames = []
        for index, series_id in enumerate(query.series):
            _, flow_id, key = selection(series_id)
            flow, dsd = structure(responses[index * 2], flow_id, self.info.id)
            dimensions = validate_key(dsd, key, self.info.id)
            response = responses[index * 2 + 1]
            message = read_xml(response.body, self.info.id, structure=dsd)
            observations = [obs for dataset in message.data for obs in dataset.obs]
            if not observations:
                raise SeriesNotFoundError(self.info.id, series_id)
            attributes = {
                name: str(value.value)
                for dataset in message.data
                for name, value in dataset.attrib.items()
            }
            attributes.update(
                {
                    name: str(value.value)
                    for name, value in observations[0].attrib.items()
                }
            )
            unit_code = next(
                (
                    mapping[key]
                    for mapping, key in (
                        (attributes, "UNIT"),
                        (attributes, "UNIT_MEASURE"),
                        (dimensions, "UNIT_MEASURE"),
                        (dimensions, "UNIT"),
                        (dimensions, "unit"),
                        (dimensions, "TYPE_OF_TRANSFORMATION"),
                    )
                    if key in mapping
                ),
                "Not specified by source",
            )
            unit_text = unit_code
            for component in (*dsd.dimensions.components, *dsd.attributes.components):
                if component.id.casefold() not in {
                    "unit",
                    "unit_measure",
                    "type_of_transformation",
                }:
                    continue
                representation = (
                    component.local_representation
                    or component.concept_identity.core_representation
                )
                codes = representation.enumerated if representation else None
                if codes is not None and unit_code in codes.items:
                    unit_text = str(codes.items[unit_code].name)
            raw_multiplier = attributes.get("UNIT_MULT", "0")
            if (
                not re.fullmatch(r"-?\d{1,2}", raw_multiplier)
                or not -_MAX_UNIT_MULTIPLIER
                <= int(raw_multiplier)
                <= _MAX_UNIT_MULTIPLIER
            ):
                msg = "SDMX sent an invalid unit multiplier"
                raise ResponseError(msg, provider=self.info.id)
            multiplier = int(raw_multiplier)
            units, percent = i.unit(unit_text, multiplier=multiplier)
            if "CURRENCY_DENOM" in dimensions:
                units = UnitRecord(
                    text=f"{dimensions.get('CURRENCY', unit_code)} per "
                    f"{dimensions['CURRENCY_DENOM']}",
                    kind=UnitKind.RATIO,
                    scale=10.0**multiplier,
                )
            rows = {}
            frequency = ObservationFrequency.IRREGULAR
            for obs in observations:
                observed = {
                    name: str(value.value) for name, value in obs.key.values.items()
                }
                if any(
                    observed.get(name) != value for name, value in dimensions.items()
                ):
                    msg = "SDMX source returned another series key"
                    raise ResponseError(msg, provider=self.info.id)
                day, frequency = i.period(observed.get("TIME_PERIOD", ""), self.info.id)
                value = (
                    None
                    if obs.value is None
                    else s.number(
                        str(obs.value), self.info.id, missing=("NaN", "nan", "")
                    )
                )
                scaled = (
                    value * 10.0**multiplier if percent and value is not None else value
                )
                rows[day] = s.rate_or_value(scaled, percent=percent)
            annotations = " ".join(
                " ".join(
                    str(getattr(annotation, key, ""))
                    for key in ("id", "text", "title", "type")
                )
                for annotation in (*flow.annotations, *dsd.annotations)
            )
            annotations += " " + " ".join(
                attributes.get(key, "")
                for key in ("COPYRIGHT", "LICENSE", "LICENCE", "RESTRICTIONS")
            )
            terms = restricted_terms(
                self.info, dimensions, annotations, response.retrieved_at.date()
            )
            adjustment = (
                SeasonalAdjustment.SEASONALLY_ADJUSTED
                if dimensions.get("ADJUSTMENT") == "Y"
                else SeasonalAdjustment.NOT_APPLICABLE
            )
            meta = SeriesMeta(
                provider=self.info.id,
                series_id=series_id,
                dataset=flow_id,
                title=attributes.get("TITLE", str(flow.name))[:1000],
                unit=units,
                frequency=frequency,
                seasonal_adjustment=adjustment,
                source_dating=DateConvention.PERIOD_START,
                terms=terms,
                retrieved_at=response.retrieved_at,
                notes=("revised_data",),
            )
            days = tuple(sorted(rows))
            frames.append(
                i.window(Series(days, tuple(rows[d] for d in days), meta), query)
            )
        return i.combine(frames, query)

    def classify_error(self, request: Request, response: Response) -> DataError | None:
        """SDMX services also use 400/204 for an unknown flow or selection."""
        return (
            SeriesNotFoundError(self.info.id, request.series or "unknown")
            if response.status in {204, 400}
            else None
        )

    def synthesize(
        self,
        request: Request,
        response: Response,
        *,
        seed: str,
    ) -> Response:
        """Replace observations in library-only XML recordings."""
        return replace(response, body=synthetic_xml(response.body, seed, self.info.id))

    def trim_recordings(
        self, exchanges: Sequence[tuple[Request, Response]], query: Query
    ) -> Sequence[tuple[Request, Response]]:
        """Retain codes actually used by data, including dataset-level units."""
        used: set[str] = set()
        prepared: list[tuple[Request, Response]] = []
        for request, original in exchanges:
            response = original
            if "/data/" in request.path and response.ok and response.body:
                _, flow, _ = selection(request.series or "")
                _, dsd = structure(prepared[-1][1], flow, self.info.id)
                dimensions = frozenset(dim.id for dim in dsd.dimensions.components)
                response = replace(
                    response, body=trim_data(response.body, self.info.id, dimensions)
                )
                used.update(data_codes(response.body, self.info.id))
            prepared.append((request, response))
        return tuple(
            (
                request,
                self.trim_recording(
                    request, response, query, used_codes=frozenset(used)
                ),
            )
            for request, response in prepared
        )

    def trim_recording(
        self,
        request: Request,
        response: Response,
        query: Query,
        *,
        used_codes: frozenset[str] = frozenset(),
    ) -> Response:
        """Keep selected published codes and matching dataflows in offline fixtures."""
        if not response.ok or not response.body.strip():
            return response
        if "/data/" in request.path:
            return replace(response, body=xml_body(response.body, self.info.id))
        codes = used_codes | (
            frozenset(selection(request.series)[2].split("."))
            if request.series
            else frozenset()
        )
        search = (
            next(
                (
                    str(c.argument)
                    for c in self.cases
                    if c.operation == Capability.SEARCH
                ),
                "",
            )
            if request.series is None
            else ""
        )
        return replace(
            response,
            body=trim_xml(response.body, self.info.id, codes=codes, search=search),
        )
