# tests/models/macro/test_output_gap_chain.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""An HP-filtered gap feeds the policy rule, offline, through cassettes.

``macro.output_gap``'s ``hp`` calculation runs on bound real GDP, and its latest
gap is passed to ``macro.policy_rule`` as a ``bind()`` override of the rule's
``output_gap``. The manifest records the override as user-supplied, beside the
records of the rule's other bindings, so a filtered gap and a published one stay
distinguishable.

The data arrive through :class:`~pyeconomics.data.transport.replay.ReplayTransport`
and the real provider parsers. BEA's answers are cassettes built here in BEA's own
response format, with invented values (``synthetic``): a recorded cassette keeps at
most 24 observations, and the filter binds 120 quarters. The New York Fed's r*
comes from its recorded cassette. The rule's previous rate is supplied too: the New
York Fed's funds-rate route has no recording for a whole-history request (issue
#135), and the Taylor (1993) rule here is not smoothed.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import secrets
from pathlib import Path
from typing import Any

import pytest

from pyeconomics.core import run_model
from pyeconomics.core.binding import USER_PROVIDER
from pyeconomics.core.cards import ModelCard
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.data import Query
from pyeconomics.data.bindings import bind_model
from pyeconomics.data.providers.bea import Bea
from pyeconomics.data.transport.base import Response
from pyeconomics.data.transport.cassette import Cassette
from pyeconomics.data.transport.replay import ReplayTransport
from pyeconomics.models.macro import output_gap, policy_rule

CASSETTES = Path(__file__).resolve().parents[2] / "providers" / "cassettes"
RECORDED = dt.datetime(2026, 10, 19, 12, 0, tzinfo=dt.UTC)
QUARTERS = 130
MONTHS = 36


def _bea_body(
    table: str, line: str, rows: list[tuple[str, float]], **row: str
) -> bytes:
    note = {"NoteRef": table, "NoteText": row.pop("note", "")}
    data = [
        {
            "TableName": table,
            "LineNumber": line,
            "TimePeriod": period,
            "DataValue": f"{value:,.1f}",
            **row,
        }
        for period, value in rows
    ]
    body = {
        "BEAAPI": {
            "Results": {"Statistic": "NIPA Table", "Data": data, "Notes": [note]}
        }
    }
    return json.dumps(body).encode()


def _bea_cassette(series_id: str, body: bytes) -> Cassette:
    (request,) = Bea().build_requests(Query(series=(series_id,)))
    return Cassette.from_exchanges(
        "bea", RECORDED, [(request, Response(200, body, RECORDED))], synthetic=True
    )


def _real_gdp() -> Cassette:
    """130 quarters of real GDP to 2026 Q2, in millions of chained dollars."""
    rows = []
    for t in range(QUARTERS):
        year, quarter = divmod(1994 * 4 + t, 4)
        level = 11_000_000.0 * math.exp(0.006 * t + 0.012 * math.sin(t / 5))
        rows.append((f"{year}Q{quarter + 1}", level))
    body = _bea_body(
        "T10106",
        "1",
        rows,
        LineDescription="Gross domestic product",
        SeriesCode="A191RX",
        METRIC_NAME="Chained Dollars",
        CL_UNIT="Level",
        UNIT_MULT="6",
        note=(
            "Table 1.1.6. Real Gross Domestic Product, Chained Dollars. Seasonally "
            "adjusted at annual rates."
        ),
    )
    return _bea_cassette("NIPA/T10106/Q/1", body)


def _core_prices() -> Cassette:
    """36 months of the core PCE price index to August 2026."""
    rows = []
    for t in range(MONTHS):
        year, month = divmod(2023 * 12 + 8 + t, 12)
        rows.append((f"{year}M{month + 1:02d}", 120.0 * 1.0024**t))
    body = _bea_body(
        "T20804",
        "25",
        rows,
        LineDescription="PCE excluding food and energy",
        SeriesCode="DPCCRG",
        METRIC_NAME="Fisher Price Index",
        CL_UNIT="Level",
        UNIT_MULT="0",
        note="Table 2.8.4. Price Indexes for PCE by Major Type. Seasonally adjusted.",
    )
    return _bea_cassette("NIPA/T20804/M/25", body)


@pytest.fixture
def replay(isolated: Any) -> ReplayTransport:  # noqa: ANN401 - the isolation fixture
    """BEA's built cassettes, the New York Fed's recorded r*, and a BEA key."""
    isolated.keyring.set_password("pyeconomics", "bea", secrets.token_hex(16))
    hlw = Cassette.from_json((CASSETTES / "nyfed" / "hlw.json").read_bytes())
    return ReplayTransport([_real_gdp(), _core_prices(), hlw])


def test_an_hp_gap_feeds_the_policy_rule_as_a_user_supplied_override(
    replay: ReplayTransport,
) -> None:
    gap_bound = bind_model(
        output_gap,
        overrides={"calculation": "hp", "frequency": "quarterly"},
        transport=replay,
    )
    (gdp,) = gap_bound.sources
    assert (gdp.provider, gdp.concept) == ("bea", "us.output.real_gdp")
    assert gdp.observation_end == dt.date(2026, 6, 30)
    filtered = run_model(output_gap, gap_bound).outputs
    assert len(filtered.cycle) == 120

    rule_bound = bind_model(
        policy_rule,
        profile="us_output_gap",
        overrides={
            "calculation": "taylor_1993",
            "output_gap": filtered.gap,
            "previous_rate": 0.0425,
        },
        transport=replay,
    )
    result = run_model(policy_rule, rule_bound)
    records = {record.field or "": record for record in result.manifest.data_sources}
    assert sorted(records) == [
        "inflation",
        "neutral_real_rate",
        "output_gap",
        "previous_rate",
    ]
    override = records["output_gap"]
    assert override.provider == USER_PROVIDER
    assert override.licence is LicenceClass.USER_SUPPLIED
    assert override.concept == "us.output_gap.real_potential"
    assert override.series_id == "override"
    assert records["inflation"].provider == "bea"
    assert records["inflation"].concept == "us.inflation.pce_core.yoy"
    assert records["neutral_real_rate"].provider == "nyfed"
    assert rule_bound.overridden == ("output_gap", "previous_rate")
    # Real GDP, core PCE prices and r*, each answered once by its cassette.
    assert len(replay.served) == 3
    # Taylor (1993) on the output gap: half the filtered gap.
    assert result.outputs.resource_gap_term == pytest.approx(0.5 * filtered.gap)
    written = result.manifest.to_dict()["data_sources"]
    assert isinstance(written, list)
    (gap_record,) = [r for r in written if r["field"] == "output_gap"]
    assert (gap_record["provider"], gap_record["licence"]) == ("user", "user-supplied")


def test_the_output_gap_card_shows_the_chain() -> None:
    card = ModelCard.from_model(output_gap).to_markdown()
    assert 'calculation="hp"' in card
    assert 'pyeconomics.bind("macro.policy_rule", profile="us_output_gap"' in card
    assert "output_gap=gap" in card
    assert "user-supplied" in card
