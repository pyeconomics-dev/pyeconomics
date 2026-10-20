# tests/providers/test_provider_sec_edgar.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""SEC EDGAR: identifiers, the contact, filings, spans, units and trimming."""

from __future__ import annotations

import datetime as dt
import json
from typing import Any

import pytest
from canned import NOW, Canned, http, ok
from fakes import BANNED, FakeClock, FakePool, FakeRaw
from leakcheck import LeakCheck, contact_canary

import pyeconomics
from pyeconomics.core import UnitKind
from pyeconomics.data import (
    CredentialError,
    DataError,
    Filing,
    Query,
    Records,
    ResponseError,
    SeriesNotFoundError,
    cache,
    config,
)
from pyeconomics.data.providers.base import RateLimit
from pyeconomics.data.providers.sec_edgar import SecEdgar, cik
from pyeconomics.data.transport.base import Request
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.http import HttpTransport
from pyeconomics.data.transport.recording import trim_response
from pyeconomics.data.types import Series

CONCEPT = "concept:320193:us-gaap:Revenues:USD:quarter"


def _query(series: str, **kwargs: object) -> Query:
    return Query(series=(series,), max_observations=24, **kwargs)  # type: ignore[arg-type]


def _fetch(series: str, body: object, **kwargs: object) -> Series:
    with cache.bypass():
        result = SecEdgar().fetch(
            _query(series, **kwargs), transport=Canned(lambda _: ok(body))
        )
    assert isinstance(result, Series)
    return result


@pytest.fixture
def contact(monkeypatch: pytest.MonkeyPatch) -> Any:
    planted = contact_canary()
    monkeypatch.setenv("PYECONOMICS_SEC_CONTACT", planted.value)
    config.reset()
    return planted


# --- identifiers -----------------------------------------------------------------


@pytest.mark.parametrize("value", ["../123", "123/456", "-1", "12345678901", "", "1.0"])
def test_a_cik_is_one_to_ten_digits(value: str) -> None:
    with pytest.raises(DataError, match="one to ten digits"):
        cik(value)


@pytest.mark.parametrize(
    "series",
    [
        "concept:320193:us-gaap:Assets:USD",  # no span
        "concept:320193:us-gaap:Assets:USD:month",
        "concept:320193:unknown:Assets:USD:instant",
        "concept:320193:us-gaap:../Assets:USD:instant",
        "concept:320193:us-gaap:Assets:USD/../x:instant",
        "concept:abc:us-gaap:Assets:USD:instant",
        "facts:https://example.org:us-gaap:Assets:USD:instant",
        "frame:us-gaap:Assets:USD:CY2026Q9I:320193",
        "frame:us-gaap:Assets:USD:2024:320193",
        "frame:us-gaap:Assets:USD:CY2024:abc",
        "frame:us-gaap:EarningsPerShareDiluted:USD/shares:CY2024:320193",
        "submissions:320193",
        "documents:320193",
    ],
)
def test_a_selection_cannot_name_a_path_or_an_undocumented_route(series: str) -> None:
    with pytest.raises(DataError):
        SecEdgar().build_requests(_query(series))


@pytest.mark.parametrize(
    "series", ["submissions", "submissions:320193:x", "concept:320193", "x:320193"]
)
def test_records_take_submissions_and_a_cik_only(series: str) -> None:
    with pytest.raises(DataError):
        SecEdgar().build_records(_query(series))


def test_one_series_per_query() -> None:
    with pytest.raises(DataError, match="one series"):
        SecEdgar().build_requests(
            Query(series=("submissions:1", "submissions:2"), max_observations=24)
        )


def test_ciks_are_zero_padded_into_the_documented_routes() -> None:
    edgar = SecEdgar()
    assert cik("320193") == "0000320193"
    paths = {
        "submissions": edgar.build_records(_query("submissions:320193"))[0].path,
        "concept": edgar.build_requests(
            _query("concept:320193:us-gaap:Assets:USD:instant")
        )[0].path,
        "facts": edgar.build_requests(
            _query("facts:320193:us-gaap:Assets:USD:instant")
        )[0].path,
        "frame": edgar.build_requests(
            _query("frame:us-gaap:EarningsPerShareDiluted:USD-per-shares:CY2024:320193")
        )[0].path,
    }
    assert paths == {
        "submissions": "/submissions/CIK0000320193.json",
        "concept": "/api/xbrl/companyconcept/CIK0000320193/us-gaap/Assets.json",
        "facts": "/api/xbrl/companyfacts/CIK0000320193.json",
        "frame": (
            "/api/xbrl/frames/us-gaap/EarningsPerShareDiluted/USD-per-shares/CY2024.json"
        ),
    }


# --- the contact -----------------------------------------------------------------


def test_a_missing_contact_names_the_setting_before_any_request() -> None:
    pool = FakePool(BANNED)
    with pytest.raises(CredentialError, match="PYECONOMICS_SEC_CONTACT"):
        SecEdgar().records(_query("submissions:320193"), transport=http(pool))
    with pytest.raises(CredentialError, match="sec_contact"), cache.bypass():
        SecEdgar().fetch(
            _query("concept:320193:us-gaap:Assets:USD:instant"), transport=http(pool)
        )
    assert pool.calls == []


def test_the_contact_goes_only_in_the_user_agent_and_reaches_no_sink(
    contact: Any,
) -> None:
    echo = json.dumps({"filings": {"recent": {"note": contact.value}}}).encode()
    pool = FakePool(FakeRaw(200, body=echo), FakeRaw(403, body=echo))
    wire = http(pool)
    request = SecEdgar().build_records(_query("submissions:320193"))[0]
    response = wire.send(SecEdgar.info, request)
    # A declared User-Agent: the product and the contact, and no URL.
    agent = pool.calls[0].headers["User-Agent"]
    assert agent == f"pyeconomics/{pyeconomics.__version__} {contact.value}"
    assert contact.value not in pool.calls[0].url
    check = LeakCheck(contact)
    check.add(
        "cassette",
        Cassette.from_exchanges(
            "sec_edgar", NOW, [(request, response)], synthetic=True
        ).document(),
    )
    check.run(
        lambda: SecEdgar().records(
            _query("submissions:320193"), transport=Canned(lambda _: response)
        )
    )
    check.run(lambda: SecEdgar().records(_query("submissions:320193"), transport=wire))
    check.assert_clean()


def test_a_refusal_is_a_credential_error_naming_the_contact_setting(
    contact: Any,
) -> None:
    del contact
    with pytest.raises(CredentialError, match="PYECONOMICS_SEC_CONTACT"):
        SecEdgar().records(
            _query("submissions:320193"), transport=Canned(lambda _: ok({}, 403))
        )


def test_requests_are_held_to_ten_a_second(
    contact: Any,
) -> None:
    del contact
    assert SecEdgar.info.rate_limits == (RateLimit(requests=10, per="second"),)
    clock = FakeClock()
    body = json.dumps({"units": {}}).encode()
    pool = FakePool(*(FakeRaw(200, body=body) for _ in range(21)))
    wire = HttpTransport(pool=pool, clock=clock.monotonic, sleep=clock.sleep)
    request = SecEdgar().build_records(_query("submissions:320193"))[0]
    start = clock.now
    for _ in range(21):
        wire.send(SecEdgar.info, request)
    assert clock.now - start >= 2.0  # the 11th and 21st requests waited a second


def test_the_default_transport_holds_one_limit_for_the_process() -> None:
    from pyeconomics.data.transport import default_transport  # noqa: PLC0415

    assert default_transport() is default_transport()


# --- filings ---------------------------------------------------------------------

RECENT: dict[str, list[Any]] = {
    "accessionNumber": [
        "0000320193-25-000003",
        "0000320193-25-000002",
        "0000320193-25-000001",
    ],
    "form": ["8-K", "10-Q", "10-K"],
    "filingDate": ["2025-05-01", "2025-04-01", "2025-01-01"],
    "reportDate": ["", "2025-03-29", "2024-12-28"],
    "primaryDocument": ["a/b.htm", "c.htm", "d.htm"],
}


def test_filings_are_bounded_typed_records_without_document_names() -> None:
    result = SecEdgar().records(
        Query(
            series=("submissions:320193",),
            start=dt.date(2025, 2, 1),
            max_observations=1,
        ),
        transport=Canned(
            lambda _: ok({"cik": "320193", "filings": {"recent": RECENT}})
        ),
    )
    assert isinstance(result, Records)
    assert result.rows == (
        Filing(
            cik="0000320193",
            accession="0000320193-25-000003",
            form="8-K",
            filed=dt.date(2025, 5, 1),
            report_date=None,
        ),
    )
    assert b"htm" not in result.canonical_json()
    assert Records.from_json(result.canonical_json()) == result


def test_filings_in_a_window_keep_their_report_dates() -> None:
    result = SecEdgar().records(
        _query("submissions:320193", end=dt.date(2025, 4, 30)),
        transport=Canned(lambda _: ok({"filings": {"recent": RECENT}})),
    )
    assert [(r.form, r.report_date) for r in result.rows] == [  # type: ignore[union-attr]
        ("10-Q", dt.date(2025, 3, 29)),
        ("10-K", dt.date(2024, 12, 28)),
    ]


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"filings": []},
        {"filings": {"recent": {**RECENT, "form": ["8-K"]}}},
        {"filings": {"recent": {**RECENT, "filingDate": [1, 2, 3]}}},
        {"filings": {"recent": {**RECENT, "filingDate": ["x", "y", "z"]}}},
    ],
)
def test_malformed_submissions_are_response_errors(body: object) -> None:
    with pytest.raises(ResponseError):
        SecEdgar().records(
            _query("submissions:320193"), transport=Canned(lambda _: ok(body))
        )


@pytest.mark.parametrize(
    "fields",
    [
        {"cik": "320193"},
        {"accession": "0000320193-25-1"},
        {"filed": dt.date(1600, 1, 1)},
        {"form": "https://example.org"},
        {"unknown": "x"},
    ],
)
def test_a_filing_refuses_bad_fields(fields: dict[str, object]) -> None:
    valid: dict[str, object] = {
        "cik": "0000320193",
        "accession": "0000320193-25-000001",
        "form": "10-K",
        "filed": dt.date(2025, 1, 1),
    }
    with pytest.raises(ValueError, match="validation error"):
        Filing.model_validate({**valid, **fields})


# --- XBRL facts ------------------------------------------------------------------

#: Two 10-Q facts ending on one day: three months (framed by SEC) and the year
#: to date (no frame), then a year, and an instant restated by a later filing.
FACTS: list[dict[str, Any]] = [
    {
        "start": "2026-03-29",
        "end": "2026-06-27",
        "val": 109_417,
        "filed": "2026-07-31",
        "accn": "0000320193-26-000020",
        "frame": "CY2026Q2",
    },
    {
        "start": "2025-09-28",
        "end": "2026-06-27",
        "val": 364_357,
        "filed": "2026-07-31",
        "accn": "0000320193-26-000020",
    },
    {
        "start": "2025-12-28",
        "end": "2026-03-28",
        "val": 111_184,
        "filed": "2026-05-01",
        "accn": "0000320193-26-000013",
        "frame": "CY2026Q1",
    },
    {
        "start": "2024-09-29",
        "end": "2025-09-27",
        "val": 416_161,
        "filed": "2025-10-31",
        "accn": "0000320193-25-000079",
        "frame": "CY2025",
    },
]


@pytest.mark.parametrize(
    ("span", "expected"),
    [
        (
            "quarter",
            {dt.date(2026, 3, 28): 111_184.0, dt.date(2026, 6, 27): 109_417.0},
        ),
        ("year", {dt.date(2025, 9, 27): 416_161.0}),
    ],
)
def test_a_span_keeps_its_own_facts_at_their_actual_period_ends(
    span: str, expected: dict[dt.date, float]
) -> None:
    result = _fetch(
        f"concept:320193:us-gaap:Revenues:USD:{span}", {"units": {"USD": FACTS}}
    )
    assert dict(zip(result.index, result.values, strict=True)) == expected
    assert result.meta.unit.kind is UnitKind.MONEY
    assert result.meta.unit.currency == "USD"
    assert "revised_data" in {n.split(":")[0] for n in result.meta.notes}


def test_company_facts_read_the_same_fact_as_the_concept() -> None:
    concept = _fetch(CONCEPT, {"units": {"USD": FACTS}})
    facts = _fetch(
        CONCEPT.replace("concept:", "facts:", 1),
        {"facts": {"us-gaap": {"Revenues": {"units": {"USD": FACTS}}}}},
    )
    assert (facts.index, facts.values) == (concept.index, concept.values)


def test_the_latest_filing_wins_a_period_end_and_the_window_applies() -> None:
    restated = [
        {"end": "2024-03-30", "val": 1, "filed": "2024-05-01", "frame": "CY2024Q1I"},
        {"end": "2024-03-30", "val": 2, "filed": "2025-05-01", "frame": "CY2024Q1I"},
        {"end": "2023-12-30", "val": 3, "filed": "2024-02-01", "frame": "CY2023Q4I"},
    ]
    result = _fetch(
        "concept:320193:us-gaap:Assets:USD:instant",
        {"units": {"USD": restated}},
        start=dt.date(2024, 1, 1),
    )
    assert (result.index, result.values) == ((dt.date(2024, 3, 30),), (2.0,))


@pytest.mark.parametrize(
    ("unit", "kind", "currency"),
    [
        ("EUR", UnitKind.MONEY, "EUR"),
        ("shares", UnitKind.COUNT, None),
        ("USD/shares", None, None),
        ("pure", None, None),
    ],
)
def test_units_keep_their_text_and_meaning(
    unit: str, kind: UnitKind | None, currency: str | None
) -> None:
    row = {"end": "2024-03-30", "val": 1.5, "frame": "CY2024Q1I"}
    result = _fetch(
        f"concept:320193:us-gaap:Assets:{unit}:instant", {"units": {unit: [row]}}
    )
    unit_record = result.meta.unit
    assert (unit_record.text, unit_record.kind, unit_record.currency) == (
        unit,
        kind,
        currency,
    )


def test_a_frame_returns_the_one_company() -> None:
    body = {
        "data": [
            {"cik": 1750, "end": "2024-02-29", "val": 9},
            {"cik": 320193, "end": "2024-03-30", "val": 337_411},
        ]
    }
    result = _fetch("frame:us-gaap:Assets:USD:CY2024Q1I:320193", body)
    assert (result.index, result.values) == ((dt.date(2024, 3, 30),), (337_411.0,))
    with pytest.raises(SeriesNotFoundError):
        _fetch("frame:us-gaap:Assets:USD:CY2024Q1I:1", body)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"units": {"EUR": FACTS}},
        {"units": {"USD": [{**FACTS[1]}]}},  # only an unframed fact
        {"units": {"USD": "not a list"}},
    ],
)
def test_a_missing_tag_unit_or_span_is_not_found(body: object) -> None:
    with pytest.raises(SeriesNotFoundError):
        _fetch(CONCEPT, body)


@pytest.mark.parametrize(
    "row",
    [
        {"end": None, "val": 1, "frame": "CY2026Q2"},
        {"end": "June", "val": 1, "frame": "CY2026Q2"},
        {"end": "2026-06-27", "val": None, "frame": "CY2026Q2"},
    ],
)
def test_a_malformed_fact_is_a_response_error(row: dict[str, object]) -> None:
    with pytest.raises(ResponseError):
        _fetch(CONCEPT, {"units": {"USD": [row]}})


# --- recordings ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("series", "body"),
    [
        (
            "submissions:320193",
            {
                "cik": "320193",
                "addresses": {"business": {"street1": "One Apple Park Way"}},
                "filings": {"recent": RECENT, "files": [{"name": "x.json"}]},
            },
        ),
        (CONCEPT, {"units": {"USD": FACTS}, "description": "d"}),
        (
            CONCEPT.replace("concept:", "facts:", 1),
            {
                "facts": {
                    "dei": {"EntityPublicFloat": {}},
                    "us-gaap": {"Revenues": {"units": {"USD": FACTS}}, "Assets": {}},
                }
            },
        ),
        (
            "frame:us-gaap:Assets:USD:CY2024Q1I:320193",
            {
                "data": [
                    {"cik": 1750, "end": "2024-02-29", "val": 9},
                    {"cik": 320193, "end": "2024-03-30", "val": 337_411},
                ]
            },
        ),
    ],
)
def test_trimming_keeps_the_genuine_values_the_query_reads(
    series: str, body: dict[str, Any]
) -> None:
    query = _query(series)
    edgar = SecEdgar()
    request = Request(host="data.sec.gov", path="/example")
    small = trim_response("sec_edgar", request, ok(body), query)
    assert len(small.body) < len(json.dumps(body))
    assert b"Apple Park" not in small.body
    if series.startswith("submissions"):
        assert edgar.parse_records([small], query) == edgar.parse_records(
            [ok(body)], query
        )
    else:
        assert edgar.parse([small], query) == edgar.parse([ok(body)], query)
