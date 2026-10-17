# tests/providers/test_provider_research.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Research publication dates, units, source layouts and parser boundaries."""

from __future__ import annotations

import datetime as dt
from io import BytesIO
from zipfile import ZipFile

import pytest
from canned import Canned
from leakcheck import LeakCheck, canary
from provider_contract import load_cassette, replay

from pyeconomics.data import (
    DataError,
    DataProvider,
    Query,
    ResponseError,
    Series,
    SeriesNotFoundError,
    cache,
    registry,
)
from pyeconomics.data.providers import _research as r
from pyeconomics.data.providers.atlanta_fed import AtlantaFed
from pyeconomics.data.providers.base import Capability, tail
from pyeconomics.data.providers.cbo import RELEASES, Cbo, records
from pyeconomics.data.providers.cleveland_fed import ClevelandFed
from pyeconomics.data.providers.penn_world_table import PennWorldTable
from pyeconomics.data.providers.philadelphia_fed import PhiladelphiaFed, release_dates
from pyeconomics.data.transport import files
from pyeconomics.data.transport.base import Response
from pyeconomics.data.transport.files import spreadsheet, workbook

NOW = dt.datetime(2026, 10, 17, tzinfo=dt.UTC)
PROVIDERS = (PhiladelphiaFed, AtlantaFed, ClevelandFed, Cbo, PennWorldTable)


def response(body: bytes) -> Response:
    return Response(200, body, NOW)


def matrix() -> bytes:
    return workbook(
        {
            "ROUTPUT": (
                ("DATE", "ROUTPUT24Q1", "ROUTPUT24Q2", "ROUTPUT24Q3"),
                ("2023:Q3", 100, 101, 102),
                ("2023:Q4", 110, 111, 112),
                ("2024:Q1", None, 120, 121),
            )
        }
    )


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("as_of:2024-02-14", ()),
        ("as_of:2024-02-15", (100.0, 110.0)),
        ("as_of:2024-05-14", (100.0, 110.0)),
        ("as_of:2024-05-15", (101.0, 111.0, 120.0)),
        ("as_of:2024-08-15", (102.0, 112.0, 121.0)),
        ("first_release", (100.0, 110.0, 120.0)),
        ("latest", (102.0, 112.0, 121.0)),
        ("all", (100.0, 101.0, 102.0, 110.0, 111.0, 112.0, 120.0, 121.0)),
    ],
)
def test_matrix_selects_publication_columns_at_inclusive_boundaries(
    label: str, expected: tuple[float, ...]
) -> None:
    with cache.bypass():
        result = PhiladelphiaFed().fetch(
            Query(series=("rtd:ROUTPUT",), vintage=label),
            transport=Canned(lambda _: response(matrix())),
        )
    assert isinstance(result, Series)
    assert result.values == expected
    assert result.realtime is not None


def test_cbo_release_day_is_distinct_from_vintage_month_and_projection_year() -> None:
    schema = response(
        b'{"fields":{"output_gap":{"unit":"Percent of potential GDP","'
        b'description":"Output gap"}}}'
    )
    responses = [
        schema,
        *(
            response(f"date,variable,value\n2026q1,output_gap,{i + 1}\n".encode())
            for i in range(len(RELEASES))
        ),
    ]
    provider = Cbo()
    query = Query(series=("quarterly:output_gap",), vintage="all")
    frame = provider.parse(responses, query)
    assert frame.values == (0.01, 0.02, 0.03, 0.04, 0.05)
    assert frame.realtime is not None
    assert tuple(p.realtime_start for p in frame.realtime) == RELEASES
    from pyeconomics.data import Vintage  # noqa: PLC0415

    assert Vintage.as_of(dt.date(2026, 2, 10)).select(frame).values == (0.04,)
    assert Vintage.as_of(dt.date(2026, 2, 11)).select(frame).values == (0.05,)
    assert Vintage.first_release().select(frame).values == (0.01,)


def test_spf_release_calendar_keeps_delays_and_does_not_invent_early_dates() -> None:
    dates = release_dates(
        b"Survey True Deadline Date News Release Date\n1990 Q2 8/23/90*"
        b" 8/31/90*\n Q3 8/23/90 8/31/90\n2026 Q1 2/2/26 2/6/26\n"
    )
    assert dates == {
        (1990, 2): dt.date(1990, 8, 31),
        (1990, 3): dt.date(1990, 8, 31),
        (2026, 1): dt.date(2026, 2, 6),
    }


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        ("1", dt.date(2025, 12, 31)),
        ("2", dt.date(2026, 3, 31)),
        ("3", dt.date(2026, 6, 30)),
        ("A", dt.date(2026, 12, 31)),
        ("B", dt.date(2027, 12, 31)),
    ],
)
def test_spf_horizon_names_the_target_period(suffix: str, expected: dt.date) -> None:
    body = workbook(
        {"UNEMP": (("YEAR", "QUARTER", "UNEMP" + suffix), (1980, 1, 8), (2026, 1, 4))}
    )
    dates = b"2026 Q1 2/2/26 2/6/26\n"
    frame = PhiladelphiaFed().parse(
        (response(body), response(dates)), Query(series=("spf:median:UNEMP:" + suffix,))
    )
    assert frame.index == (expected,)
    assert frame.values == (0.04,)
    assert frame.realtime is not None
    assert frame.realtime[0].realtime_start == dt.date(2026, 2, 6)


def test_same_day_spf_surveys_use_the_later_surveys_annual_forecast() -> None:
    body = workbook(
        {"UNEMP": (("YEAR", "QUARTER", "UNEMPA"), (1990, 2, 5), (1990, 3, 6))}
    )
    dates = b"1990 Q2 8/23/90 8/31/90\n Q3 8/23/90 8/31/90\n"
    frame = PhiladelphiaFed().parse(
        (response(body), response(dates)), Query(series=("spf:mean:UNEMP:A",))
    )
    assert frame.values == (0.06,)


@pytest.mark.parametrize("provider", PROVIDERS)
def test_research_provider_refuses_independent_series_alignment(
    provider: type[DataProvider],
) -> None:
    with pytest.raises(DataError, match="separately"):
        provider().build_requests(Query(series=("one", "two")))


@pytest.mark.parametrize("provider", PROVIDERS)
def test_unknown_research_series_is_refused_before_a_request(
    provider: type[DataProvider],
) -> None:
    with pytest.raises(SeriesNotFoundError):
        provider().build_requests(Query(series=("unknown",)))


@pytest.mark.parametrize("provider", [ClevelandFed, PennWorldTable])
def test_revised_only_sources_never_pretend_to_keep_vintages(
    provider: type[DataProvider],
) -> None:
    case = provider.cases[0]
    assert isinstance(case.argument, Query)
    query = case.argument.model_copy(update={"vintage": "as_of:2026-01-01"})
    with cache.bypass(), pytest.raises(DataError):
        provider().fetch(query, transport=replay(provider.info.id, case))


def test_pwt_keeps_decimal_shares_and_release_metadata() -> None:
    body = workbook(
        {
            "Info": (("Penn World Table, version 11.0",),),
            "Legend": (("labsh", "Share of labour compensation in GDP"),),
            "Data": (("countrycode", "year", "labsh"), ("USA", 2023, 0.6)),
        }
    )
    frame = PennWorldTable().parse((response(body),), Query(series=("USA:labsh",)))
    assert frame.values == (0.6,)
    assert "release_version: 11.0" in frame.meta.notes
    assert frame.meta.unit.scale == 1


def test_no_spreadsheet_formula_is_evaluated() -> None:
    body = workbook({"data": (("=1+1", '=HYPERLINK("https://example.org")'),)})
    assert spreadsheet(body, "data", "test") == ((None, None),)


def alter_member(body: bytes, member: str, content: bytes) -> bytes:
    stream = BytesIO()
    with ZipFile(BytesIO(body)) as source, ZipFile(stream, "w") as target:
        for item in source.infolist():
            target.writestr(
                item.filename, content if item.filename == member else source.read(item)
            )
    return stream.getvalue()


def test_forged_worksheet_dimensions_do_not_hide_out_of_bounds_data() -> None:
    body = workbook({"data": (("value",),)})
    xml = (
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsh'
        b'eetml/2006/main"><dimension ref="A1"/><sheetData><row r="100'
        b'101"><c r="A100101" t="n"><v>1</v></c></row></sheetData></wo'
        b"rksheet>"
    )
    with pytest.raises(ResponseError, match="bound"):
        spreadsheet(alter_member(body, "xl/worksheets/sheet1.xml", xml), "data", "test")


def test_trailing_formatting_does_not_allocate_a_million_empty_rows() -> None:
    body = workbook({"data": (("value",),)})
    xml = (
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsh'
        b'eetml/2006/main"><dimension ref="A1:A1048576"/><sheetData><r'
        b'ow r="1"><c r="A1" t="n"><v>1</v></c></row><row r="1048576">'
        b'<c r="A1048576" s="0"/></row></sheetData></worksheet>'
    )
    assert spreadsheet(
        alter_member(body, "xl/worksheets/sheet1.xml", xml), "data", "test"
    ) == ((1,),)


@pytest.mark.parametrize(
    "member",
    ["xl/workbook.xml", "xl/worksheets/sheet1.xml", "xl/_rels/workbook.xml.rels"],
)
def test_dtd_and_entities_are_rejected_in_every_xml_member(member: str) -> None:
    body = workbook({"data": ((1,),)})
    xml = b'<!DOCTYPE root [<!ENTITY x SYSTEM "file:///nonexistent">]><root>&x;</root>'
    with pytest.raises(ResponseError):
        spreadsheet(alter_member(body, member, xml), "data", "test")


def test_parser_failure_scrubs_registered_canaries() -> None:
    planted = canary()
    check = LeakCheck(planted)
    body = workbook({"data": ((1,),)})
    check.run(lambda: spreadsheet(body, planted.value, "test"))
    check.assert_clean()


@pytest.mark.parametrize(
    "cap",
    [
        "MAX_EXPANDED_BYTES",
        "MAX_ARCHIVE_ENTRIES",
        "MAX_SHEET_CELLS",
        "MAX_SHEET_ROWS",
        "MAX_SHEET_COLUMNS",
    ],
)
def test_spreadsheet_bounds_are_enforced(
    cap: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = workbook({"data": ((1, 2), (3, 4))})
    monkeypatch.setattr(files, cap, 1)
    with pytest.raises(ResponseError, match=r"bound|cap"):
        spreadsheet(body, "data", "test")


def test_corrupt_and_missing_sheets_are_typed_errors() -> None:
    with pytest.raises(ResponseError):
        spreadsheet(b"broken", "data", "test")
    with pytest.raises(ResponseError):
        spreadsheet(workbook({"data": ((1,),)}), "absent", "test")


def test_duplicate_zip_members_are_refused() -> None:
    body = workbook({"data": ((1,),)})
    stream = BytesIO(body)
    with ZipFile(stream, "a") as target, pytest.warns(UserWarning, match="Duplicate"):
        target.writestr("xl/workbook.xml", b"duplicate")
    with pytest.raises(ResponseError, match="duplicate"):
        files.archive(stream.getvalue(), "test")


@pytest.mark.parametrize("raw", [True, "NaN", "infinity", object()])
def test_nonfinite_or_nonnumeric_source_values_fail(raw: object) -> None:
    with pytest.raises(ResponseError):
        r.number(raw, "test")


@pytest.mark.parametrize("raw", [None, "#N/A", "NA", "-999", "."])
def test_missing_markers_are_none(raw: object) -> None:
    assert r.number(raw, "test", missing_codes=True) is None


def test_cbo_requires_its_documented_csv_fields() -> None:
    with pytest.raises(ResponseError):
        records(b"period,data\n2025,1\n")


@pytest.mark.parametrize("series_id", ["USA:i_xr", "USA:country", "USA:year"])
def test_pwt_never_treats_text_or_categorical_columns_as_measurements(
    series_id: str,
) -> None:
    with pytest.raises(SeriesNotFoundError):
        PennWorldTable().build_requests(Query(series=(series_id,)))


def test_provider_registry_includes_all_five_research_sources() -> None:
    registry.validate()
    assert {p.info.id for p in PROVIDERS} <= set(registry.ids())


def test_early_as_of_selection_precedes_the_row_cap() -> None:
    query = Query(
        series=("rtd:ROUTPUT",), vintage="as_of:2024-02-15", max_observations=1
    )
    with cache.bypass():
        frame = PhiladelphiaFed().fetch(
            query, transport=Canned(lambda _: response(matrix()))
        )
    assert isinstance(frame, Series)
    assert frame.index == (dt.date(2023, 12, 31),)
    assert frame.values == (110.0,)


def test_a_missing_later_vintage_never_extends_an_old_value() -> None:
    body = workbook(
        {
            "ROUTPUT": (
                ("DATE", "ROUTPUT24Q1", "ROUTPUT24Q2"),
                ("2023:Q4", 110, None),
                ("2024:Q1", -999, 120),
            )
        }
    )
    with cache.bypass():
        frame = PhiladelphiaFed().fetch(
            Query(series=("rtd:ROUTPUT",), vintage="as_of:2024-05-15"),
            transport=Canned(lambda _: response(body)),
        )
    assert isinstance(frame, Series)
    assert frame.values == (None, 120.0)
    assert frame.realtime is not None
    assert all(p.realtime_start == dt.date(2024, 5, 15) for p in frame.realtime)


def test_spf_growth_has_integral_excel_float_years_and_decimal_rates() -> None:
    body = workbook({"RGDP": (("YEAR", "QUARTER", "drgdp3"), (2026.0, 1.0, 2.5))})
    result = PhiladelphiaFed().parse(
        (response(body), response(b"2026 Q1 2/2/26 2/6/26\n")),
        Query(series=("spf_growth:median:RGDP:3",)),
    )
    assert result.values == (0.025,)
    assert result.meta.unit.scale == 1


@pytest.mark.parametrize("value", [True, 2026.5, "2026"])
def test_calendar_fields_refuse_nonintegral_or_untyped_source_values(
    value: object,
) -> None:
    with pytest.raises(ResponseError):
        r.integer(value, "test")


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1947:01", dt.date(1947, 1, 31)),
        ("2026:M2", dt.date(2026, 2, 28)),
        ("CY2026", dt.date(2026, 12, 31)),
        ("FY2026", dt.date(2026, 9, 30)),
    ],
)
def test_source_period_labels_have_correct_calendar_and_fiscal_ends(
    text: str, expected: dt.date
) -> None:
    assert r.period(text, "test") == expected


@pytest.mark.parametrize("text", ["2026:Q5", "2026:13", "not_a_date"])
def test_unknown_source_period_labels_fail_without_coercion(text: str) -> None:
    with pytest.raises(ResponseError):
        r.period(text, "test")


def test_a_duplicate_observation_in_one_source_vintage_is_refused() -> None:
    provider = PhiladelphiaFed()
    meta = provider.parse((response(matrix()),), Query(series=("rtd:ROUTPUT",))).meta
    duplicate = (dt.date(2025, 12, 31), dt.date(2026, 2, 15), 100.0)
    with pytest.raises(ResponseError, match="repeats"):
        r.frame((duplicate, duplicate), meta, Query(series=("rtd:ROUTPUT",)))


def test_unknown_vintage_header_is_refused() -> None:
    body = workbook({"ROUTPUT": (("DATE", "unknown"), ("2024:Q1", 100))})
    with pytest.raises(ResponseError, match="vintage"):
        PhiladelphiaFed().parse((response(body),), Query(series=("rtd:ROUTPUT",)))


SYNTHETIC_CASES = [
    pytest.param(provider, case, id=f"{provider.info.id}-{case.name}")
    for provider in (PhiladelphiaFed, AtlantaFed, ClevelandFed)
    for case in provider.cases
    if case.operation is Capability.FETCH and case.expect is None
]


@pytest.mark.parametrize(("provider", "case"), SYNTHETIC_CASES)
def test_synthetic_workbooks_replace_values_but_preserve_layout_and_missingness(
    provider: type[DataProvider], case: object
) -> None:
    from pyeconomics.data.providers.base import Case  # noqa: PLC0415

    assert isinstance(case, Case)
    assert isinstance(case.argument, Query)
    instance = provider()
    requests = instance.build_requests(case.argument)
    cassette = load_cassette(provider.info.id, case)
    responses = [
        Response(record.response.status, record.response.body, NOW)
        for record in cassette.requests
    ]
    before = instance.parse(responses, case.argument)
    after_responses = [
        instance.synthesize(request, original, seed="independent-synthetic-seed")
        for request, original in zip(requests, responses, strict=True)
    ]
    after = instance.parse(after_responses, case.argument)
    assert isinstance(before, Series)
    assert isinstance(after, Series)
    assert before.index == after.index
    assert before.realtime == after.realtime
    assert before.meta == after.meta
    assert before.values != after.values
    assert tuple(v is None for v in before.values) == tuple(
        v is None for v in after.values
    )
    assert all(len(answer.body) < 24_000 for answer in after_responses)


@pytest.mark.parametrize("provider", [Cbo, PennWorldTable])
def test_trimmed_hosted_recordings_keep_the_selected_values_and_terms(
    provider: type[DataProvider],
) -> None:
    instance = provider()
    case = provider.cases[0]
    assert isinstance(case.argument, Query)
    query = case.argument.model_copy(update={"max_observations": 1})
    requests = instance.build_requests(query)
    cassette = load_cassette(provider.info.id, case)
    responses = [
        Response(record.response.status, record.response.body, NOW)
        for record in cassette.requests
    ]
    before = instance.parse(responses, query)
    assert isinstance(before, Series)
    trimmed = [
        instance.trim_recording(request, original, query)
        for request, original in zip(requests, responses, strict=True)
    ]
    assert instance.parse(trimmed, query) == tail(before, query.max_observations)
    assert all(len(answer.body) < 16_000 for answer in trimmed)


@pytest.mark.parametrize(
    ("variable", "kind", "scale"),
    [
        ("EMP", "count", 1000),
        ("HOUSING", "count", 1e6),
        ("PGDP", "index_level", 1),
        ("INDPROD", "index_level", 1),
        ("CPI05YF05", "rate", 1),
        ("RGDP", "money", 1e9),
    ],
)
def test_spf_units_follow_its_documentation(
    variable: str, kind: str, scale: float
) -> None:
    from pyeconomics.data.providers.philadelphia_fed import survey_unit  # noqa: PLC0415

    unit, _ = survey_unit(variable, growth=False)
    assert unit.kind is not None
    assert unit.kind.value == kind
    assert unit.scale == scale


def test_empty_worksheet_is_empty_and_does_not_trust_a_declared_dimension() -> None:
    assert spreadsheet(workbook({"data": ()}), "data", "test") == ()


def test_spreadsheet_requires_the_hardened_xml_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openpyxl.xml  # noqa: PLC0415

    monkeypatch.setattr(openpyxl.xml, "DEFUSEDXML", False)
    with pytest.raises(ResponseError, match="requires defusedxml"):
        spreadsheet(workbook({"data": ((1,),)}), "data", "test")


def test_sparse_dimensions_cannot_allocate_an_oversized_rectangle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = workbook({"data": ((1,),)})
    xml = (
        b'<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        b'<sheetData><row r="1"><c r="A1" t="n"><v>1</v></c></row>'
        b'<row r="2"><c r="D2" t="n"><v>2</v></c></row></sheetData></worksheet>'
    )
    monkeypatch.setattr(files, "MAX_SHEET_CELLS", 3)
    with pytest.raises(ResponseError, match="rectangular"):
        spreadsheet(alter_member(body, "xl/worksheets/sheet1.xml", xml), "data", "test")


@pytest.mark.parametrize("value", [-99, -999, "-99", "-999"])
def test_philadelphia_missing_codes_do_not_erase_other_sources_negative_values(
    value: object,
) -> None:
    assert r.number(value, "test") == float(str(value))
    assert r.number(value, "test", missing_codes=True) is None


def test_fixture_writer_uses_no_temporary_worksheet_files(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import openpyxl.worksheet._writer as writer  # noqa: PLC0415

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("workbook serialization must not create a temporary file")

    monkeypatch.setattr(writer, "create_temporary_file", forbidden)
    row = (dt.date(2026, 1, 1), True, " <&> ", None, *range(30))
    sheets = {"synthetic & test": (row,)}
    body = workbook(sheets)
    assert body == workbook(sheets)
    assert spreadsheet(body, "synthetic & test", "test") == (row,)


@pytest.mark.parametrize("value", [object(), float("inf"), float("nan")])
def test_fixture_writer_refuses_unsupported_or_nonfinite_cells(value: object) -> None:
    with pytest.raises(ValueError, match="scalar"):
        workbook({"data": ((value,),)})


@pytest.mark.parametrize("value", [dt.date(2026, 1, 1), "2026-01-01"])
def test_source_date_cells_accept_dates_and_iso_dates(value: object) -> None:
    assert r.day(value, "test") == dt.date(2026, 1, 1)


def test_source_date_cells_refuse_untyped_text() -> None:
    with pytest.raises(ResponseError):
        r.day("invalid", "test")


@pytest.mark.parametrize(
    ("info", "data", "legend", "error"),
    [
        (
            "Wrong version",
            (("countrycode", "year", "emp"), ("USA", 2023, 1)),
            (("emp", "Millions of persons"),),
            ResponseError,
        ),
        (
            "Penn World Table, version 11.0",
            (("countrycode", "year", "other"), ("USA", 2023, 1)),
            (("other", "Other"),),
            SeriesNotFoundError,
        ),
        (
            "Penn World Table, version 11.0",
            (("countrycode", "year", "emp"), ("USA", 2023, 1)),
            (("other", "Other"),),
            SeriesNotFoundError,
        ),
        (
            "Penn World Table, version 11.0",
            (("countrycode", "year", "emp"), ("USA", "bad_year", 1)),
            (("emp", "Millions of persons"),),
            ResponseError,
        ),
    ],
)
def test_pwt_rejects_release_or_schema_drift(
    info: str, data: r.Rows, legend: r.Rows, error: type[Exception]
) -> None:
    body = workbook({"Info": ((info,),), "Data": data, "Legend": legend})
    with pytest.raises(error):
        PennWorldTable().parse((response(body),), Query(series=("USA:emp",)))


def test_pwt_country_selection_preserves_employment_units() -> None:
    body = workbook(
        {
            "Info": (("Penn World Table, version 11.0",),),
            "Data": (
                ("countrycode", "year", "emp"),
                ("CAN", 2023, 20),
                ("USA", 2023, 160),
            ),
            "Legend": (("emp", "Millions of persons"),),
        }
    )
    result = PennWorldTable().parse((response(body),), Query(series=("USA:emp",)))
    assert result.values == (160.0,)
    assert result.meta.unit.scale == 1e6


def test_cleveland_rejects_an_unknown_column_without_guessing() -> None:
    body = workbook({"Expected Inflation": (("Model Output Date", "Wrong column"),)})
    with pytest.raises(SeriesNotFoundError):
        ClevelandFed().parse(
            (response(body),), Query(series=("expected_inflation:10",))
        )


@pytest.mark.parametrize("missing", ["archive", "current"])
def test_gdpnow_rejects_source_layout_drift(missing: str) -> None:
    sheets = {
        "TrackingDeepArchives": (
            ("Forecast Date", "Quarter being forecasted", "GDP Nowcast"),
        ),
        "TrackingArchives": (
            ("Forecast Date", "Quarter being forecasted", "GDP Nowcast"),
        ),
        "TrackingHistory": (
            ("Date", None, dt.date(2026, 1, 1)),
            ("Evolution of GDP nowcast for 2026q1",),
            ("GDP", None, 1),
        ),
    }
    if missing == "archive":
        sheets["TrackingDeepArchives"] = (("Missing forecast column",),)
    else:
        sheets["TrackingHistory"] = (("Date",), ("Missing forecast quarter",))
    with pytest.raises(ResponseError):
        AtlantaFed().parse((response(workbook(sheets)),), Query(series=("gdpnow",)))


def test_spf_vintages_are_survey_publication_days() -> None:
    case = next(c for c in PhiladelphiaFed.cases if c.name == "spf_fetch_ok")
    cassette = load_cassette(PhiladelphiaFed.info.id, case)
    responses = [response(record.response.body) for record in cassette.requests]
    dates = PhiladelphiaFed().parse_vintages(responses, "spf:median:CPI:3")
    assert len(dates) == 3
    assert dates == sorted(set(dates))
