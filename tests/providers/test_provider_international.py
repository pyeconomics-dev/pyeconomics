# tests/providers/test_provider_international.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""International source boundaries: licensing, XML, adapters and paged data."""

from __future__ import annotations

import datetime as dt
import gzip
import sys
from dataclasses import replace
from typing import Any

import pytest
import requests
from canned import Canned, ok
from leakcheck import LeakCheck, canary
from provider_contract import replay

from pyeconomics.core import UnitKind
from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.data import (
    CachePolicy,
    LicenceClass,
    LicenceError,
    LlmUse,
    Query,
    ResponseError,
    Series,
    Table,
    cache,
    configure,
    registry,
)
from pyeconomics.data.providers import _shared
from pyeconomics.data.providers._international import combine
from pyeconomics.data.providers._sdmx import restricted_terms
from pyeconomics.data.providers.ecb import Ecb
from pyeconomics.data.providers.eurostat import Eurostat
from pyeconomics.data.providers.imf import Imf
from pyeconomics.data.providers.world_bank import WorldBank, page_number
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.sdmx import read_xml, send, trim_xml, xml_body


@pytest.mark.parametrize("provider_id", ["imf", "oecd", "ecb", "bis", "eurostat"])
def test_missing_sdmx_names_the_extra(
    provider_id: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    provider = registry.get(provider_id)
    monkeypatch.setitem(sys.modules, "sdmx", None)
    query = provider.cases[0].argument
    assert isinstance(query, Query)
    with cache.bypass(), pytest.raises(MissingOptionalDependencyError, match="sdmx"):
        provider.fetch(query)


@pytest.mark.parametrize(
    ("scheme", "host"),
    [("http", "data-api.ecb.europa.eu"), ("https", "foreign.example.org")],
)
def test_the_sdmx_adapter_refuses_http_and_foreign_hosts(
    scheme: str, host: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    prepare = requests.Session.prepare_request

    def altered(self: Any, request: Any) -> Any:
        prepared = prepare(self, request)
        prepared.url = f"{scheme}://{host}/data"
        return prepared

    monkeypatch.setattr(requests.Session, "prepare_request", altered)
    wire = Canned(lambda _: ok({}))
    with pytest.raises(Exception, match=r"refused|allowlist|host"):
        send(Ecb.info, Request(host=Ecb.info.hosts[0], path="/data"), wire)
    assert wire.sent == []


def test_sdmx_xml_error_prints_and_logs_no_source_body(
    capsys: pytest.CaptureFixture[str],
) -> None:
    planted = canary()
    check = LeakCheck(planted)
    body = (
        f'<message:Structure xmlns:message="http://www.sdmx.org/resources/sdmxml/schemas/v2_1/message"><unknown>{planted.value}</unknown></message:Structure>'
    ).encode()
    check.run(lambda: read_xml(body, "ecb"))
    captured = capsys.readouterr()
    check.add("stdout", captured.out)
    check.add("stderr", captured.err)
    check.assert_clean()
    assert captured.out == captured.err == ""


@pytest.mark.parametrize(
    "body",
    [
        b'<!DOCTYPE root [<!ENTITY xx SYSTEM "https://foreign.example.org/">]><root>&xx;</root>',
        b'<!ENTITY xx "test"><root/>',
    ],
)
def test_sdmx_rejects_dtds_and_entities(body: bytes) -> None:
    with pytest.raises(ResponseError, match="DTDs and entities"):
        read_xml(body, "ecb")


def test_headerless_gzip_is_bounded_and_round_trips() -> None:
    assert xml_body(gzip.compress(b"<root/>"), "eurostat") == b"<root/>"
    with pytest.raises(ResponseError, match="size limit"):
        xml_body(gzip.compress(b"x" * 64_000_001), "eurostat")


@pytest.mark.parametrize(
    ("dimensions", "expected"),
    [
        ({"geo": "DE"}, LicenceClass.HOSTED_SAFE),
        ({"geo": "US"}, LicenceClass.LIBRARY_ONLY),
        ({"geo": "JP"}, LicenceClass.LIBRARY_ONLY),
        ({"geo": "CH", "product": "TOTAL"}, LicenceClass.LIBRARY_ONLY),
        ({"geo": "LI", "product": "01"}, LicenceClass.LIBRARY_ONLY),
        ({"geo": "AT", "product": "01012100"}, LicenceClass.LIBRARY_ONLY),
        ({"geo": "AT", "product": "01"}, LicenceClass.HOSTED_SAFE),
    ],
)
def test_eurostat_country_and_trade_exceptions(
    dimensions: dict[str, str], expected: LicenceClass
) -> None:
    terms = restricted_terms(Eurostat.info, dimensions, "", dt.date(2026, 10, 16))
    assert terms.licence is expected


def test_explicit_third_party_restrictions_override_oecd() -> None:
    info = registry.get("oecd").info
    terms = restricted_terms(
        info, {}, "Third-party data: permission required", dt.date(2026, 10, 16)
    )
    assert terms.licence is LicenceClass.LIBRARY_ONLY


def world_bank_wire(licence: str) -> Canned:
    """Two data pages and independent metadata responses."""

    def route(request: Request) -> Any:
        if request.path.endswith("metadata"):
            return ok({"metatype": [{"id": "License_Type", "value": licence}]})
        if request.path == "/v2/indicator/NY.GDP.MKTP.CD":
            return ok(
                [
                    {"page": 1, "pages": 1},
                    [
                        {
                            "id": "NY.GDP.MKTP.CD",
                            "name": "GDP",
                            "unit": "USD",
                            "source": {"value": "WDI"},
                        }
                    ],
                ]
            )
        if request.path in {"/v2/country/USA", "/v2/country/US"}:
            return ok([{"page": 1, "pages": 1}, [{"id": "USA", "iso2Code": "US"}]])
        page = int(dict(request.params).get("page", "1"))
        return ok(
            [
                {"page": page, "pages": 2},
                [
                    {
                        "date": str(2021 + page),
                        "value": None if page == 2 else 100,
                        "countryiso3code": "USA",
                        "indicator": {"id": "NY.GDP.MKTP.CD"},
                    }
                ],
            ]
        )

    return Canned(route)


def test_world_bank_pages_preserve_missing_values_and_period_ends() -> None:
    wire = world_bank_wire("CC BY-4.0")
    with cache.bypass():
        frame = WorldBank().fetch(
            Query(series=("2/USA/NY.GDP.MKTP.CD",)), transport=wire
        )
    assert isinstance(frame, Series)
    assert frame.index == (dt.date(2022, 12, 31), dt.date(2023, 12, 31))
    assert frame.values == (100.0, None)
    assert len(wire.sent) == 5
    assert frame.meta.terms.licence is LicenceClass.HOSTED_SAFE


@pytest.mark.parametrize("licence", ["CC BY-NC 4.0", "", "Unspecified"])
def test_hosted_world_bank_refuses_a_series_without_explicit_cc_by(
    licence: str,
) -> None:
    configure(mode="hosted")
    with cache.bypass(), pytest.raises(LicenceError):
        WorldBank().fetch(
            Query(series=("2/USA/NY.GDP.MKTP.CD",)), transport=world_bank_wire(licence)
        )


def test_bis_policy_rates_are_decimals_from_dataset_level_units() -> None:
    provider = registry.get("bis")
    case = provider.cases[0]
    with cache.bypass():
        frame = provider.run_case(case, transport=replay("bis", case))
    assert isinstance(frame, Series)
    assert frame.meta.unit.kind is UnitKind.RATE
    assert all(value is None or abs(value) < 1 for value in frame.values)


def test_a_bad_sdmx_dimension_never_reaches_the_data_endpoint() -> None:
    provider = Ecb()
    case = Ecb.cases[0]
    recorded = replay("ecb", case)
    wire = Canned(lambda request: recorded.send(Ecb.info, request))
    assert isinstance(case.argument, Query)
    query = case.argument.model_copy(
        update={"series": ("ECB/EXR/A.NOT_CURRENCY.EUR.SP00.A",)}
    )
    # The structure request is identical apart from its diagnostic series id;
    # replay identity deliberately excludes that diagnostic field.
    with cache.bypass(), pytest.raises(Exception, match="unknown CURRENCY"):
        provider.fetch(query, transport=wire)
    assert len(wire.sent) == 1


def test_multiple_world_bank_series_form_a_table_without_filling_gaps() -> None:
    query = Query(series=("2/USA/NY.GDP.MKTP.CD", "2/US/NY.GDP.MKTP.CD"))
    with cache.bypass():
        frame = WorldBank().fetch(query, transport=world_bank_wire("CC BY-4.0"))
    assert isinstance(frame, Table)
    assert frame.data == ((100.0, None), (100.0, None))
    assert frame.column_names == ("series_1", "series_2")


def test_a_restriction_never_weakens_imfs_llm_prohibition() -> None:
    terms = restricted_terms(Imf.info, {}, "third-party data", dt.date(2026, 10, 16))
    assert terms.llm_use is LlmUse.FORBIDDEN


def test_a_table_preserves_all_no_storage_and_llm_prohibitions() -> None:
    query = Query(series=("2/USA/NY.GDP.MKTP.CD", "2/US/NY.GDP.MKTP.CD"))
    with cache.bypass():
        frame = WorldBank().fetch(
            Query(series=(query.series[0],)), transport=world_bank_wire("CC BY-4.0")
        )
    assert isinstance(frame, Series)
    first = replace(
        frame,
        meta=replace(
            frame.meta,
            terms=replace(
                frame.meta.terms, llm_use=LlmUse.FORBIDDEN, cache=CachePolicy.FORBIDDEN
            ),
        ),
    )
    second = replace(
        frame,
        meta=replace(
            frame.meta,
            series_id=query.series[1],
            terms=replace(
                frame.meta.terms,
                licence=LicenceClass.LIBRARY_ONLY,
                llm_use=LlmUse.UNCLEAR,
            ),
        ),
    )
    combined = combine((first, second), query)
    assert combined.meta.terms.llm_use is LlmUse.FORBIDDEN
    assert combined.meta.terms.cache is CachePolicy.FORBIDDEN


def test_a_restricted_world_bank_series_creates_no_cache_file(isolated: Any) -> None:
    directory = isolated.cache_dir
    frame = WorldBank().fetch(
        Query(series=("2/USA/NY.GDP.MKTP.CD",)),
        transport=world_bank_wire("CC BY-NC 4.0"),
    )
    assert frame.meta.terms.cache is CachePolicy.FORBIDDEN
    assert not directory.exists()


@pytest.mark.parametrize("bad", [True, -1, 1.2, "not a page", "99999999999999999999"])
def test_malformed_pagination_is_a_source_error(bad: object) -> None:
    with pytest.raises(ResponseError, match="pagination metadata"):
        page_number(bad)


def test_numeric_errors_echo_neither_a_secret_nor_its_prefix() -> None:
    planted = canary()

    class Prefixes:
        def needles(self) -> tuple[str, ...]:
            return planted.value, planted.value[:16]

    check = LeakCheck(Prefixes())
    check.run(lambda: _shared.number(planted.value, "world_bank"))
    check.assert_clean()


def test_malformed_gzip_is_reported_without_source_bytes() -> None:
    planted = canary()
    check = LeakCheck(planted)
    with pytest.raises(ResponseError, match="invalid gzip"):
        xml_body(b"\x1f\x8b" + planted.value.encode(), "eurostat")
    check.run(lambda: xml_body(b"\x1f\x8b" + planted.value.encode(), "eurostat"))
    check.assert_clean()


def test_recording_retains_rights_annotations() -> None:
    body = (
        b'<Structure><Dataflow id="flow"><Annotations><Annotation>'
        b"<AnnotationText>Third-party data: permission required</AnnotationText>"
        b"</Annotation></Annotations></Dataflow></Structure>"
    )
    trimmed = trim_xml(body, "oecd", codes=frozenset())
    assert b"permission required" in trimmed


def test_ecb_exchange_quotes_keep_the_denominator_and_ratio_unit() -> None:
    case = Ecb.cases[0]
    with cache.bypass():
        frame = Ecb().run_case(case, transport=replay("ecb", case))
    assert isinstance(frame, Series)
    assert frame.meta.unit.kind is UnitKind.RATIO
    assert frame.meta.unit.text == "USD per EUR"
