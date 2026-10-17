# tests/data/catalog/test_recorded_concepts.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Concepts resolved through the real provider parsers, replayed from cassettes.

``test_world_resolution.py`` proves the catalog and the resolver agree for every
concept against synthetic stand-ins. These tests add the real parsers: for each
concept whose originator has a cassette recorded in Steps 6 to 10, the real
provider answers from that recording through ``ReplayTransport``, and the
resolver's shaping, transforms and definition checks run on what it parsed.
The queries are the cassettes' own (same window, same size bound), because a
replay answers a request only when it matches the recorded one.
"""

from __future__ import annotations

import datetime as dt
import secrets
from pathlib import Path
from typing import Any

import pytest

from pyeconomics import data
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import Mode, ObservationFrequency, Table
from pyeconomics.data.transport.replay import ReplayTransport

CASSETTES = Path(__file__).resolve().parents[2] / "providers" / "cassettes"
JAN: dict[str, Any] = {
    "start": dt.date(2025, 1, 1),
    "end": dt.date(2025, 1, 31),
    "max_observations": 24,
}


def replay(provider: str, name: str) -> ReplayTransport:
    return ReplayTransport.from_file(CASSETTES / provider / f"{name}.json")


#: concept, cassette (provider, name), the arguments the recorded query implies,
#: the provider the answer must come from.
SERIES_CASES: list[tuple[str, tuple[str, str], dict[str, Any], str]] = [
    ("us.policy_rate.effective", ("nyfed", "effr"), {"max_observations": 3}, "nyfed"),
    (
        "us.policy_rate.target_upper",
        ("fed_board", "target_range"),
        {
            "start": dt.date(2025, 1, 1),
            "end": dt.date(2025, 12, 31),
            "max_observations": 3,
        },
        "fed_board",
    ),
    (
        "us.policy_rate.target_lower",
        ("fed_board", "target_range"),
        {
            "start": dt.date(2025, 1, 1),
            "end": dt.date(2025, 12, 31),
            "max_observations": 3,
        },
        "fed_board",
    ),
    ("us.treasury.nominal_10y", ("treasury", "par_nominal"), JAN, "treasury"),
    ("us.treasury.nominal_3m", ("treasury", "par_nominal"), JAN, "treasury"),
    ("us.treasury.real_10y", ("treasury", "par_real"), JAN, "treasury"),
    ("us.fiscal.federal_debt", ("treasury", "debt"), JAN, "treasury"),
    (
        "us.fiscal.average_interest_rate",
        ("treasury", "average_interest"),
        JAN,
        "treasury",
    ),
    (
        "us.neutral_rate.laubach_williams",
        ("nyfed", "lw"),
        {"max_observations": 3},
        "nyfed",
    ),
    ("us.neutral_rate.hlw", ("nyfed", "hlw"), {"max_observations": 3}, "nyfed"),
    ("ea.neutral_rate.hlw", ("nyfed", "hlw"), {"max_observations": 3}, "nyfed"),
    ("ca.neutral_rate.hlw", ("nyfed", "hlw"), {"max_observations": 3}, "nyfed"),
    ("us.output.potential_gdp", ("cbo", "fetch_ok"), {"max_observations": 3}, "cbo"),
    ("us.output_gap.cbo", ("cbo", "gap_fetch_ok"), {"max_observations": 3}, "cbo"),
    (
        "pwt.rgdpna.us.annual",
        ("penn_world_table", "fetch_ok"),
        {"max_observations": 3},
        "penn_world_table",
    ),
    (
        "pwt.rkna.us.annual",
        ("penn_world_table", "capital_fetch_ok"),
        {"max_observations": 3},
        "penn_world_table",
    ),
    (
        "pwt.labsh.us.annual",
        ("penn_world_table", "share_fetch_ok"),
        {"max_observations": 3},
        "penn_world_table",
    ),
    ("us.equity.cape", ("shiller", "fetch_0"), {"max_observations": 3}, "shiller"),
    (
        "us.equity.implied_erp",
        ("damodaran", "fetch_0"),
        {"max_observations": 3},
        "damodaran",
    ),
    (
        "us.spf.cpi.median_h1",
        ("philadelphia_fed", "spf_fetch_ok"),
        {"max_observations": 3},
        "philadelphia_fed",
    ),
    (
        "us.spf.cpi.median_10y",
        ("philadelphia_fed", "long_fetch_ok"),
        {"max_observations": 3},
        "philadelphia_fed",
    ),
]

TABLE_CASES: list[tuple[str, tuple[str, str], dict[str, Any], str, int]] = [
    ("us.treasury.par_curve", ("treasury", "par_nominal"), JAN, "treasury", 13),
    ("us.treasury.par_curve_real", ("treasury", "par_real"), JAN, "treasury", 5),
    (
        "us.treasury.gsw_curve",
        ("fed_board", "gsw"),
        {
            "start": dt.date(2025, 1, 1),
            "end": dt.date(2025, 1, 6),
            "max_observations": 3,
        },
        "fed_board",
        0,
    ),
    (
        "equity.shiller.us.monthly",
        ("shiller", "fetch_0"),
        {"max_observations": 3},
        "shiller",
        6,
    ),
    (
        "factors.ff3.us.monthly",
        ("ken_french", "fetch_0"),
        {"max_observations": 3},
        "ken_french",
        4,
    ),
    (
        "factors.ff3.us.daily",
        ("ken_french", "fetch_2"),
        {"max_observations": 3},
        "ken_french",
        4,
    ),
    (
        "factors.ff5.us.monthly",
        ("ken_french", "fetch_3"),
        {"max_observations": 3},
        "ken_french",
        6,
    ),
    (
        "factors.ff5.us.daily",
        ("ken_french", "fetch_4"),
        {"max_observations": 3},
        "ken_french",
        6,
    ),
    (
        "factors.momentum.us.monthly",
        ("ken_french", "fetch_5"),
        {"max_observations": 3},
        "ken_french",
        1,
    ),
    (
        "factors.momentum.us.daily",
        ("ken_french", "fetch_6"),
        {"max_observations": 3},
        "ken_french",
        1,
    ),
    (
        "portfolios.industry12.us.monthly",
        ("ken_french", "fetch_7"),
        {"max_observations": 3},
        "ken_french",
        12,
    ),
    (
        "portfolios.size_bm25.us.monthly",
        ("ken_french", "fetch_8"),
        {"max_observations": 3},
        "ken_french",
        25,
    ),
]


@pytest.mark.parametrize(
    ("concept", "cassette", "arguments", "provider"),
    SERIES_CASES,
    ids=[case[0] for case in SERIES_CASES],
)
def test_a_recorded_series_resolves_through_its_real_parser(
    concept: str, cassette: tuple[str, str], arguments: dict[str, Any], provider: str
) -> None:
    result = data.get(concept, transport=replay(*cassette), **arguments)
    assert result.concept == concept
    assert result.source.provider == provider
    assert result.source.concept == concept
    assert len(result.frame.index) >= 1
    assert result.skipped == ()
    assert result.source.retrieved_at is not None


@pytest.mark.parametrize(
    ("concept", "cassette", "arguments", "provider", "columns"),
    TABLE_CASES,
    ids=[case[0] for case in TABLE_CASES],
)
def test_a_recorded_table_resolves_through_its_real_parser(
    concept: str,
    cassette: tuple[str, str],
    arguments: dict[str, Any],
    provider: str,
    columns: int,
) -> None:
    result = data.get(concept, transport=replay(*cassette), **arguments)
    assert isinstance(result.frame, Table)
    assert result.source.provider == provider
    assert len(result.frame.index) >= 1
    if columns:
        assert len(result.frame.columns) == columns


def test_the_treasury_curve_columns_are_renamed_to_tenors() -> None:
    result = data.get(
        "us.treasury.par_curve", transport=replay("treasury", "par_nominal"), **JAN
    )
    assert isinstance(result.frame, Table)
    assert result.frame.column_names[:3] == ("1m", "2m", "3m")
    assert result.frame.column_names[-1] == "30y"


def test_the_sep_medians_keep_only_median_columns_for_the_named_meeting() -> None:
    result = data.get(
        "us.sep.medians",
        parameters={"meeting": "2026-09-16"},
        transport=replay("fed_board", "sep"),
        max_observations=3,
    )
    assert isinstance(result.frame, Table)
    assert all("_median_" in name for name in result.frame.column_names)
    assert result.frame.index == (dt.date(2026, 9, 16),)
    assert result.source.series_id == "sep:2026-09-16"
    one = data.get(
        "us.sep.policy_rate_longer_run",
        parameters={"meeting": "2026-09-16"},
        transport=replay("fed_board", "sep"),
        max_observations=3,
    )
    assert one.source.series_id == "sep:2026-09-16:federal_funds_rate_median_Longer_run"


def test_a_vintage_request_reads_the_cbo_vintage_in_force_on_the_date() -> None:
    result = data.get(
        "us.output.potential_gdp",
        as_of=dt.date(2025, 6, 30),
        transport=replay("cbo", "fetch_ok"),
        max_observations=3,
    )
    assert result.source.vintage == "as_of:2025-06-30"
    assert result.source.realtime is not None
    assert result.source.realtime.covers(dt.date(2025, 6, 30))


def test_hosted_mode_refuses_recorded_library_only_sources_and_serves_others() -> None:
    for concept, cassette, arguments, _ in (
        case for case in SERIES_CASES if case[3] in {"shiller", "philadelphia_fed"}
    ):
        with pytest.raises(data.LicenceError):
            data.get(
                concept, mode=Mode.HOSTED, transport=replay(*cassette), **arguments
            )
    served = data.get(
        "us.policy_rate.effective",
        mode=Mode.HOSTED,
        transport=replay("nyfed", "effr"),
        max_observations=3,
    )
    assert served.source.licence is LicenceClass.HOSTED_SAFE


def test_fred_answers_the_unemployment_rate_as_the_aggregator(isolated: Any) -> None:
    isolated.keyring.set_password("pyeconomics", "fred", secrets.token_hex(16))
    result = data.get(
        "us.unemployment.rate",
        provider="fred",
        transport=replay("fred", "fetch_ok"),
        start=dt.date(2024, 1, 1),
        end=dt.date(2025, 12, 31),
        max_observations=24,
    )
    assert result.source.provider == "fred"
    assert result.source.licence is LicenceClass.LIBRARY_ONLY
    assert result.frame.meta.frequency is ObservationFrequency.MONTHLY
    assert result.frame.meta.terms.notice  # FRED's required notice travels with it
    assert result.source.notice == result.frame.meta.terms.notice


def test_a_missing_recording_is_a_skip_and_not_a_crash() -> None:
    with pytest.raises(data.DataError, match="unavailable"):
        data.get(
            "us.policy_rate.effective",
            provider="nyfed",
            transport=replay("nyfed", "sofr"),  # a different request than effr's
            max_observations=3,
        )
