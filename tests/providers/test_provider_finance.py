# tests/providers/test_provider_finance.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Source-layout regressions, recording privacy and explicit Yahoo opt-in."""

from __future__ import annotations

import datetime as dt
import importlib.util
import sys
from importlib.machinery import ModuleSpec
from types import ModuleType, SimpleNamespace
from typing import TYPE_CHECKING

import pandas as pd
import pytest
from canned import NOW, Canned, ok
from leakcheck import LeakCheck, canary
from provider_contract import load_cassette, replay

from pyeconomics.core.errors import MissingOptionalDependencyError
from pyeconomics.data import (
    DataError,
    DataWarning,
    LicenceError,
    Query,
    ResponseError,
    cache,
    configure,
)
from pyeconomics.data.config import CONFIG_FILE, reset, settings
from pyeconomics.data.providers.aqr import Aqr
from pyeconomics.data.providers.cboe import Cboe
from pyeconomics.data.providers.coin_metrics import CoinMetrics
from pyeconomics.data.providers.damodaran import Damodaran
from pyeconomics.data.providers.hou_xue_zhang import HouXueZhang
from pyeconomics.data.providers.jkp import Jkp
from pyeconomics.data.providers.ken_french import KenFrench
from pyeconomics.data.providers.open_source_asset_pricing import OpenSourceAssetPricing
from pyeconomics.data.providers.shiller import Shiller
from pyeconomics.data.providers.yfinance import YFinance
from pyeconomics.data.transport import files, yahoo
from pyeconomics.data.transport.base import Request, Response
from pyeconomics.data.types import ObservationFrequency, Table

if TYPE_CHECKING:
    from pathlib import Path

    from pyeconomics.data.providers.base import DataProvider

LIBRARY = (
    KenFrench,
    Shiller,
    Aqr,
    HouXueZhang,
    Jkp,
    OpenSourceAssetPricing,
    Cboe,
    CoinMetrics,
)


def query(identifier: str, **kwargs: object) -> Query:
    return Query(series=(identifier,), max_observations=24, **kwargs)  # type: ignore[arg-type]


def french(rows: list[list[object]]) -> Response:
    return ok(files.zip_document({"factors.csv": files.csv_document(rows)}))


def test_french_sections_missing_values_and_decimal_boundary() -> None:
    response = french(
        [
            ["Synthetic fixture"],
            ["", "Mkt-RF", "SMB"],
            [202402, 5, -99.99],
            [202403, -2, -999],
            [],
            ["Annual Factors"],
            ["", "Mkt-RF", "SMB"],
            [2024, 12, 3],
        ]
    )
    provider = KenFrench()
    monthly = provider.parse([response], query("ff3:monthly"))
    assert monthly.index == (dt.date(2024, 2, 29), dt.date(2024, 3, 31))
    assert monthly.data == ((0.05, -0.02), (None, None))
    annual = provider.parse([response], query("ff3:annual"))
    assert annual.index == (dt.date(2024, 12, 31),)
    assert annual.data == ((0.12,), (0.03,))
    daily = provider.parse(
        [french([["", "Mom"], [20240229, 4]])], query("momentum:daily")
    )
    assert daily.index == (dt.date(2024, 2, 29),)
    assert daily.data == ((0.04,),)


def test_french_daily_files_keep_the_saturday_sessions_before_1952() -> None:
    # The NYSE traded on Saturdays until 1952: the daily files are trading days,
    # dated by calendar day, not business days (Phase 3 Step 17).
    response = french([["", "Mkt-RF"], [19260709, 1.0], [19260710, 0.5]])
    daily = KenFrench().parse([response], query("ff3:daily"))
    assert daily.index == (dt.date(1926, 7, 9), dt.date(1926, 7, 10))
    assert dt.date(1926, 7, 10).weekday() == 5  # a Saturday
    assert daily.meta.frequency is ObservationFrequency.DAILY


def test_global_q_long_format_pivots_portfolios_without_converting_ranks() -> None:
    body = files.csv_document(
        [
            [
                "year",
                "month",
                "rank_ME",
                "rank_IA",
                "rank_ROE",
                "nstocks",
                "ret_vw",
                "retx_vw",
            ],
            [2025, 1, 1, 1, 1, 100, 5, 4],
            [2025, 1, 2, 1, 1, 200, 9, 8],
        ]
    )
    result = HouXueZhang().parse([ok(body)], query("benchmark:monthly"))
    assert result.index == (dt.date(2025, 1, 31),)
    assert [c.name for c in result.columns] == [
        "me1_ia1_roe1:ret_vw",
        "me1_ia1_roe1:retx_vw",
        "me2_ia1_roe1:ret_vw",
        "me2_ia1_roe1:retx_vw",
    ]
    assert result.data == ((0.05,), (0.04,), (0.09,), (0.08,))


@pytest.mark.parametrize("bound", ["MAX_CSV_ROWS", "MAX_CSV_COLUMNS", "MAX_CSV_CELLS"])
def test_csv_resource_limits_precede_large_allocations(
    bound: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pyeconomics.data.providers import _finance  # noqa: PLC0415

    monkeypatch.setattr(_finance, bound, 1)
    with pytest.raises(ResponseError, match="bound"):
        _finance.csv_rows(b"a,b\n1,2\n")


def test_french_portfolio_weights_do_not_mix_with_counts_or_ratios() -> None:
    response = french(
        [
            ["Average Value Weighted Returns -- Monthly"],
            ["", "SMALL LoBM"],
            [202401, 5],
            ["Average Equal Weighted Returns -- Monthly"],
            ["", "SMALL LoBM"],
            [202401, 9],
            ["Number of Firms in Portfolios"],
            ["", "SMALL LoBM"],
            [202401, 999],
        ]
    )
    assert KenFrench().parse([response], query("size_bm25:monthly")).data == ((0.05,),)
    assert KenFrench().parse([response], query("size_bm25:monthly:equal")).data == (
        (0.09,),
    )


@pytest.mark.parametrize(
    "rows", [[["", "Mkt"], [202401, 1, 2]], [["", "Mkt"], [202401, 1], [202401, 2]]]
)
def test_french_rejects_changed_width_or_duplicate_dates(
    rows: list[list[object]],
) -> None:
    with pytest.raises(ResponseError):
        KenFrench().parse([french(rows)], query("ff3:monthly"))


@pytest.mark.parametrize(
    "name", ["../data.csv", "/data.csv", "C:/data.csv", "sub\\..\\data.csv"]
)
def test_zip_member_paths_are_refused_without_extraction(name: str) -> None:
    with pytest.raises(ResponseError):
        files.archive(files.zip_document({name: b"payload"}), "ken_french")


def test_zip_member_and_entry_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    body = files.zip_document({"data.csv": b"12345"})
    monkeypatch.setattr(files, "MAX_MEMBER_BYTES", 4)
    with pytest.raises(ResponseError):
        files.archive(body, "ken_french")
    monkeypatch.setattr(files, "MAX_MEMBER_BYTES", 100)
    monkeypatch.setattr(files, "MAX_ARCHIVE_ENTRIES", 1)
    with pytest.raises(ResponseError):
        files.archive(files.zip_document({"a": b"1", "b": b"2"}), "ken_french")


def test_selected_workbook_retains_reader_bounds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    body = files.workbook(
        {
            "wanted": (("DATE", "ret"), (dt.datetime(2025, 1, 31, tzinfo=dt.UTC), 0.1)),
            "unused": (("x",),),
        }
    )
    assert files.selected_spreadsheet(body, "wanted", "aqr")[1][1] == 0.1
    with pytest.raises(ResponseError):
        files.selected_spreadsheet(body, "absent", "aqr")
    monkeypatch.setattr(files, "MAX_SHEET_CELLS", 1)
    with pytest.raises(ResponseError, match="bound"):
        files.selected_spreadsheet(body, "wanted", "aqr")


@pytest.mark.parametrize("provider", LIBRARY)
def test_library_recordings_are_synthetic_and_can_be_resynthesized(
    provider: type[DataProvider],
) -> None:
    for case in provider.cases:
        if case.expect is not None:
            continue
        cassette = load_cassette(provider.info.id, case)
        assert cassette.synthetic
        recorded = cassette.requests[0].response
        response = Response(
            recorded.status, recorded.body, cassette.recorded_on, recorded.headers
        )
        assert isinstance(case.argument, Query)
        request = provider().build_requests(case.argument)[0]
        changed = provider().synthesize(
            request, response, seed="independent_synthetic_seed"
        )

        def route(_: Request, answer: Response = changed) -> Response:
            return answer

        with cache.bypass():
            result = provider().run_case(case, transport=Canned(route))
        assert isinstance(result, Table)
        original = provider().parse([response], case.argument)
        assert isinstance(original, Table)
        assert result.data != original.data
        assert Table.from_json(result.canonical_json()) == result


@pytest.mark.parametrize(
    ("provider", "identifier"),
    [
        (KenFrench, "unknown:monthly"),
        (KenFrench, "ff3:weekly"),
        (Aqr, "unknown:daily"),
        (HouXueZhang, "q5:unknown"),
        (Jkp, "usa:be_me:monthly:unknown"),
        (CoinMetrics, "btc:unknown"),
        (Damodaran, "country_risk"),
        (Shiller, "unknown"),
        (Cboe, "unknown"),
        (OpenSourceAssetPricing, "unknown"),
    ],
)
def test_file_selection_refuses_unknown_or_unsafe_requests(
    provider: type[DataProvider], identifier: str
) -> None:
    with pytest.raises(DataError):
        provider().build_requests(query(identifier))


def test_coin_metrics_and_damodaran_usage_conditions_are_machine_readable() -> None:
    assert CoinMetrics.info.never_paid is True
    assert CoinMetrics.info.terms.licence.value == "library-only"
    case = Damodaran.cases[1]
    result = Damodaran().run_case(case, transport=replay("damodaran", case))
    assert isinstance(result, Table)
    assert "no_bulk_mirror" in result.meta.notes
    assert any(n.startswith("source_update: ") for n in result.meta.notes)
    assert result.meta.terms.licence.value == "hosted-safe"


def test_aqr_returns_are_not_scaled_twice_and_shiller_dates_are_not_serials() -> None:
    response = ok(
        files.workbook({"BAB Factors": (("DATE", "USA"), ("02/29/2024", 0.05))})
    )
    assert Aqr().parse([response], query("bab:monthly")).data == ((0.05,),)
    cells: list[list[object]] = [
        [
            "Date",
            "P",
            "D",
            "E",
            "CPI",
            "Fraction",
            "Rate GS10",
            "",
            "",
            "",
            "",
            "",
            "CAPE",
        ],
        [1871.02, 2, 3, 4, 5, 1871.1, 5, None, None, None, None, None, "NA"],
    ]
    result = Shiller().parse(
        [ok(files.legacy_workbook("Data", cells))], query("us_equity")
    )
    assert result.index == (dt.date(1871, 2, 28),)
    assert result.data[4] == (0.05,)
    assert result.data[5] == (None,)


def test_yahoo_requires_installation_and_explicit_opt_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(LicenceError, match="enable_yfinance"):
        YFinance().fetch(query("prices:IBM"))
    monkeypatch.setattr(importlib.util, "find_spec", lambda _: None)
    with pytest.raises(
        MissingOptionalDependencyError, match="pyeconomics\\[yfinance\\]"
    ):
        YFinance().fetch(query("prices:IBM"))


def test_yahoo_opt_in_is_available_in_toml_and_configure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / CONFIG_FILE).write_bytes(b"enable_yfinance = true\n")
    reset()
    assert settings().enable_yfinance is True
    configure(enable_yfinance=False)
    assert settings().enable_yfinance is False


def install_fake_yahoo(monkeypatch: pytest.MonkeyPatch) -> None:
    module = ModuleType("yfinance")
    module.__spec__ = ModuleSpec("yfinance", loader=None)
    frame = pd.DataFrame(
        {"Open": [1.0], "High": [2.0], "Low": [0.5], "Close": [1.5], "Volume": [10]},
        index=pd.to_datetime(["2025-01-02"]),
    )
    options = pd.DataFrame(
        {
            "contractSymbol": ["DEMO_CALL"],
            "strike": [10.0],
            "lastPrice": [1.0],
            "bid": [0.9],
            "ask": [1.1],
            "impliedVolatility": [0.2],
            "volume": [0],
            "openInterest": [1],
        }
    )
    ticker = SimpleNamespace(
        history=lambda **_: frame,
        info={"marketCap": 100, "trailingPE": 10.0, "name": "ignored text"},
        options=("2025-02-21",),
        option_chain=lambda _: SimpleNamespace(calls=options, puts=options),
    )
    monkeypatch.setattr(module, "Ticker", lambda _: ticker, raising=False)
    monkeypatch.setitem(sys.modules, "yfinance", module)


@pytest.mark.parametrize(
    "identifier",
    [
        "prices:IBM",
        "fundamentals:IBM",
        "options:IBM:calls",
        "options:IBM:puts:2025-02-21",
    ],
)
def test_yahoo_adapter_shapes_with_an_offline_session(
    identifier: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    install_fake_yahoo(monkeypatch)
    configure(enable_yfinance=True)
    monkeypatch.setattr(yahoo, "_WARNED", False)
    with pytest.warns(DataWarning, match="personal use only"), cache.bypass():
        result = YFinance().fetch(query(identifier), transport=yahoo.YahooTransport())
    assert isinstance(result, Table)
    assert result.data
    with cache.bypass():
        YFinance().fetch(query(identifier), transport=yahoo.YahooTransport())


def test_yahoo_client_failure_is_scrubbed(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_yahoo(monkeypatch)
    planted = canary()
    check = LeakCheck(planted)
    configure(enable_yfinance=True)
    monkeypatch.setattr(yahoo, "_WARNED", True)

    def broken(_: object) -> object:
        raise ValueError(planted.value)

    monkeypatch.setattr(sys.modules["yfinance"], "Ticker", broken)
    check.run(
        lambda: YFinance().fetch(query("prices:IBM"), transport=yahoo.YahooTransport())
    )
    check.assert_clean()


@pytest.mark.parametrize(
    "case", [c for c in Damodaran.cases if c.expect is None], ids=lambda c: c.name
)
def test_damodaran_trimming_retains_selected_genuine_aggregates(case: object) -> None:
    from pyeconomics.data.providers.base import Case  # noqa: PLC0415

    assert isinstance(case, Case)
    assert isinstance(case.argument, Query)
    cassette = load_cassette("damodaran", case)
    source = cassette.requests[0].response
    response = Response(
        source.status, source.body, cassette.recorded_on, source.headers
    )
    provider = Damodaran()
    request = provider.build_requests(case.argument)[0]
    small = provider.trim_recording(request, response, case.argument)
    before = provider.parse([response], case.argument)
    after = provider.parse([small], case.argument)
    assert after == before
    assert (
        provider.trim_recording(
            request, Response(404, b"ignored", NOW), case.argument
        ).body
        == b""
    )


def test_damodaran_refuses_an_undated_snapshot() -> None:
    body = files.legacy_workbook(
        "Industry Averages", (("Industry Name", "Beta"), ("Advertising", 1.0))
    )
    with pytest.raises(ResponseError, match="update date"):
        Damodaran().parse([ok(body)], query("industry_betas:advertising"))


def test_jkp_rejects_ambiguous_archives_and_duplicate_dates() -> None:
    header: list[object] = ["date", "ret"]
    rows: list[list[object]] = [header, ["2025-01-31", 0.1], ["2025-01-31", 0.2]]
    response = ok(files.zip_document({"factors.csv": files.csv_document(rows)}))
    with pytest.raises(ResponseError, match="repeats a date"):
        Jkp().parse([response], query("usa:be_me:monthly:vw"))
    response = ok(files.zip_document({"a.csv": b"", "b.csv": b""}))
    with pytest.raises(ResponseError, match="one CSV"):
        Jkp().parse([response], query("usa:be_me:monthly:vw"))


def test_yahoo_rejects_malformed_direct_session_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configure(enable_yfinance=True)
    request = Request(
        host="foreign.example.org",
        path="/fetch",
        method="POST",
        body={"selection": ["prices", "IBM"], "limit": 3},
    )
    with pytest.raises(DataError, match="declared contract"):
        yahoo.YahooTransport().send(YFinance.info, request)
    request = Request(
        host="yfinance-session.localhost",
        path="/fetch",
        method="POST",
        body={"selection": 1},
    )
    with pytest.raises(DataError):
        yahoo.YahooTransport().send(YFinance.info, request)


def test_numeric_yahoo_fields_refuse_objects_and_preserve_missing_values() -> None:
    assert yahoo._numeric(None) is None  # noqa: SLF001 - boundary regression
    assert yahoo._numeric(float("inf")) is None  # noqa: SLF001 - missing source field
    with pytest.raises(TypeError):
        yahoo._numeric([])  # noqa: SLF001 - untrusted source field


def test_disabling_yahoo_also_refuses_cached_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_yahoo(monkeypatch)
    configure(enable_yfinance=True)
    monkeypatch.setattr(yahoo, "_WARNED", True)
    provider = YFinance()
    selection = query("prices:IBM")
    provider.fetch(selection, transport=yahoo.YahooTransport())
    configure(enable_yfinance=False)
    with pytest.raises(LicenceError, match="enable_yfinance"):
        provider.fetch(selection, transport=Canned(lambda _: ok(b"unexpected")))


def test_cached_yahoo_results_still_show_first_use_terms(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_yahoo(monkeypatch)
    configure(enable_yfinance=True)
    monkeypatch.setattr(yahoo, "_WARNED", True)
    selection = query("prices:IBM")
    original = YFinance().fetch(selection, transport=yahoo.YahooTransport())
    monkeypatch.setattr(yahoo, "_WARNED", False)
    unused = Canned(lambda _: ok(b"must not be used"))
    with pytest.warns(DataWarning, match="personal use only"):
        assert YFinance().fetch(selection, transport=unused) == original
    assert unused.sent == []
    assert YFinance().fetch(selection, transport=unused) == original


def test_yahoo_client_exceptions_hide_private_cache_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_yahoo(monkeypatch)
    configure(enable_yfinance=True)
    monkeypatch.setattr(yahoo, "_WARNED", True)

    def inaccessible(_: object) -> object:
        message = "not-a-real-user/private-cache/cookies.sqlite"
        raise OSError(message)

    monkeypatch.setattr(sys.modules["yfinance"], "Ticker", inaccessible)
    with pytest.raises(DataError) as caught:
        YFinance().fetch(query("prices:IBM"), transport=yahoo.YahooTransport())
    assert str(caught.value) == "Yahoo session failed"
    assert caught.value.__context__ is None
