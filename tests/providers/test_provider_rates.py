# tests/providers/test_provider_rates.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Rate-provider transformations and the separate records contract."""

from __future__ import annotations

import datetime as dt
from io import BytesIO
from typing import TYPE_CHECKING
from zipfile import ZipFile

import pytest
from canned import Canned, ok
from defusedxml.common import DefusedXmlException
from provider_contract import load_cassette, replay
from pydantic import ValidationError

from pyeconomics.core import UnitKind
from pyeconomics.data import (
    DataError,
    OfflineError,
    Query,
    ResponseError,
    cache,
    configure,
)
from pyeconomics.data.providers.fed_board import FedBoard, ProjectionTable
from pyeconomics.data.providers.nyfed import NyFed
from pyeconomics.data.providers.openfigi import OpenFigi
from pyeconomics.data.providers.treasury import Treasury
from pyeconomics.data.records import FigiMapping
from pyeconomics.data.transport import files
from pyeconomics.data.types import Table

if TYPE_CHECKING:
    from collections.abc import Callable

    from pyeconomics.data import DataProvider
    from pyeconomics.data.transport.base import Request, Response, Transport


def _query(series: str, **kwargs: object) -> Query:
    return Query(series=(series,), max_observations=24, **kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("provider", "identifier"),
    [
        (OpenFigi, "https://example.org"),
        (OpenFigi, "UNSUPPORTED:IBM"),
        (NyFed, "unknown"),
        (NyFed, "lw:2026q9"),
        (FedBoard, "unknown"),
    ],
)
def test_untrusted_identifiers_cannot_change_a_host_or_path(
    provider: type[DataProvider], identifier: str
) -> None:
    with pytest.raises((DataError, ValidationError)):  # noqa: PT012 - construction or hook rejects the input
        instance = provider()
        query = _query(identifier)
        if provider is OpenFigi:
            instance.build_records(query)
        else:
            instance.build_requests(query)


@pytest.mark.parametrize("keyed", [False, True])
def test_figi_batches_at_the_correct_job_cap(*, keyed: bool) -> None:
    instance = OpenFigi()
    query = Query(series=tuple(f"TICKER:DEMO{i}" for i in range(101)))
    with instance._keyed(  # noqa: SLF001 - tests both authenticated build modes
        "k" * 24 if keyed else None
    ):
        requests = instance.build_records(query)
    assert len(requests) == (2 if keyed else 11)
    assert requests[0].method == "POST"
    assert len(requests[0].body) == (100 if keyed else 10)


@pytest.mark.parametrize(
    "body", [[{}], [{"warning": "No identifier found"}], [{"error": "job failed"}], []]
)
def test_figi_maps_job_failures_and_cardinality(body: object) -> None:
    with pytest.raises(DataError):
        OpenFigi().records(_query("TICKER:DEMO"), transport=Canned(lambda _: ok(body)))


def test_records_refuse_offline_and_vintage_requests_before_transport() -> None:
    transport = Canned(lambda _: ok([]))
    with pytest.raises(DataError):
        OpenFigi().records(_query("TICKER:DEMO", vintage="all"), transport=transport)
    configure(offline=True)
    with pytest.raises(OfflineError):
        OpenFigi().records(_query("TICKER:DEMO"), transport=transport)
    assert transport.sent == []


@pytest.mark.parametrize("value", ["https://example.org", "bad\nvalue", "x" * 513])
def test_record_text_uses_the_frame_security_rule(value: str) -> None:
    with pytest.raises((ValidationError, ValueError)):
        FigiMapping(identifier_type="TICKER", identifier="DEMO", figi=value)


def test_treasury_months_and_fiscal_pagination_never_follow_a_link() -> None:
    provider = Treasury()
    requests = provider.build_requests(
        _query("par_real", start=dt.date(2024, 12, 1), end=dt.date(2025, 1, 31))
    )
    assert [dict(r.params)["field_tdr_date_value_month"] for r in requests] == [
        "202412",
        "202501",
    ]
    first = provider.build_requests(_query("debt"))[0]
    second = provider.next_page(
        first,
        ok(
            {
                "meta": {"total-pages": 2},
                "links": {"next": "https://untrusted.example.org"},
            }
        ),
    )
    assert second is not None
    assert second.host == first.host
    assert second.path == first.path
    assert dict(second.params)["page[number]"] == "2"
    assert provider.next_page(second, ok({"meta": {"total-pages": 2}})) is None


def test_treasury_and_board_dates_and_decimal_units_are_pinned() -> None:
    for provider in (Treasury, FedBoard, NyFed):
        for case in provider.cases:
            if case.expect is not None:
                continue
            result = provider().run_case(case, transport=replay(provider.info.id, case))
            assert isinstance(result, Table)
            assert result.index == tuple(sorted(result.index))
            assert type(result).from_json(result.canonical_json()) == result
    case = next(c for c in FedBoard.cases if c.name == "gsw")
    gsw = FedBoard().run_case(case, transport=replay("fed_board", case))
    assert isinstance(gsw, Table)
    units = {c.name: c.unit for c in gsw.columns}
    assert units["TAU1"].text == "Years"
    assert units["SVENY01"].scale == 1
    assert units["BETA0"].text == "Svensson coefficient in decimal rate units"
    # The betas are coefficients in decimal rate units, not rates: some reach
    # hundreds of percentage points, so they are dimensionless decimals.
    assert units["BETA0"].kind is UnitKind.RATIO
    assert units["TAU1"].kind is UnitKind.YEARS


def test_nyfed_zero_volumes_and_multiple_daily_operations_are_preserved() -> None:
    rows = [
        {"operationDate": "2025-01-02", "totalAmtSubmitted": 0, "totalAmtAccepted": 0},
        {
            "operationDate": "2025-01-02",
            "totalAmtSubmitted": 12,
            "totalAmtAccepted": 10,
        },
    ]
    with cache.bypass():
        frame = NyFed().fetch(
            _query("repo"),
            transport=Canned(lambda _: ok({"repo": {"operations": rows}})),
        )
    assert isinstance(frame, Table)
    assert frame.data == ((12.0,), (10.0,))


def test_xml_external_entities_are_refused() -> None:
    body = b'<!DOCTYPE feed [<!ENTITY x SYSTEM "file:///not-a-real-file">]><feed>&x;</feed>'
    with pytest.raises(
        (ResponseError, DefusedXmlException), match=r"DTDForbidden|EntitiesForbidden"
    ):
        Treasury().fetch(
            _query("par_real", start=dt.date(2025, 1, 1), end=dt.date(2025, 1, 31)),
            transport=Canned(lambda _: ok(body)),
        )


def test_bounded_file_readers_refuse_corrupt_and_oversized_archives(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ResponseError):
        files.archive(b"not a zip", "treasury")
    stream = BytesIO()
    with ZipFile(stream, "w") as archive:
        archive.writestr("data", b"payload")
    monkeypatch.setattr(files, "MAX_EXPANDED_BYTES", 1)
    with pytest.raises(ResponseError):
        files.archive(stream.getvalue(), "treasury")


def test_a_recorded_workbook_is_safe_in_memory_and_rejects_a_missing_sheet() -> None:
    case = next(c for c in NyFed.cases if c.name == "lw")
    cassette = load_cassette("nyfed", case)
    body = cassette.requests[0].response.body
    assert files.spreadsheet(body, "data", "nyfed")
    with pytest.raises(ResponseError):
        files.spreadsheet(body, "absent", "nyfed")


def test_the_board_never_builds_a_package_url() -> None:
    paths = [
        r.path
        for case in FedBoard.cases
        if isinstance(case.argument, Query)
        for r in FedBoard().build_requests(case.argument)
    ]
    assert all("datadownload" not in path.casefold() for path in paths)
    parser = ProjectionTable()
    parser.feed(
        "<div>ignored</div><table id='unrelated'><tr><td>ignored</td></tr></table>"
    )
    assert parser.rows == []


@pytest.mark.parametrize("provider", [Treasury, FedBoard, NyFed, OpenFigi])
def test_trimming_preserves_values_and_source_format(
    provider: type[DataProvider],
) -> None:
    for case in provider.cases:
        if case.expect is not None or not isinstance(case.argument, Query):
            continue
        query = case.argument
        original = replay(provider.info.id, case)

        def make_route(
            original: Transport, query: Query
        ) -> Callable[[Request], Response]:
            def route(request: Request) -> Response:
                response = original.send(provider.info, request)
                small = provider().trim_recording(request, response, query)
                assert small.body.lstrip()[:1] == response.body.lstrip()[:1]
                return small

            return route

        with cache.bypass():
            before = provider().run_case(case, transport=original)
            after = provider().run_case(
                case, transport=Canned(make_route(original, query))
            )
        assert before == after


def test_file_reader_limits_precede_value_parsing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = next(c for c in NyFed.cases if c.name == "lw")
    body = load_cassette("nyfed", case).requests[0].response.body
    monkeypatch.setattr(files, "MAX_SHEET_ROWS", 1)
    with pytest.raises(ResponseError, match="bound"):
        files.spreadsheet(body, "data", "nyfed")
    case = next(c for c in NyFed.cases if c.name == "acm")
    legacy = load_cassette("nyfed", case).requests[0].response.body
    with pytest.raises(ResponseError, match="bound"):
        files.legacy_spreadsheet(legacy, "ACM Daily", "nyfed")
    monkeypatch.setattr(files, "MAX_EXPANDED_BYTES", 1)
    with pytest.raises(ResponseError, match="size cap"):
        files.legacy_spreadsheet(legacy, "ACM Daily", "nyfed")
