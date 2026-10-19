# tests/models/macro/test_live_policy_rule.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Taylor (1993) rule for a past date on the real sources (``pytest -m live``).

The weekly live run (providers-live.yml) executes this with the FRED key. As of
a past date the default profile reads ALFRED's vintages (and CBO's report of
the day) for every field whose sources keep them, and records each vintage in
the manifest; the r* and the funds rate have none, so they are read as revised
data, labelled so.
A ``LATEST`` run of the same date reads revised data throughout, differs, and
warns ``revised_data``.
"""

from __future__ import annotations

import datetime as dt

import pytest

import pyeconomics
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.data.credentials import has_key

pytestmark = pytest.mark.live

#: A date long enough ago that core PCE prices have been revised since.
PAST = dt.date(2019, 6, 28)
#: Fields whose sources keep no vintages of them (the New York Fed's r* and
#: funds rate; ALFRED holds none of FRED's daily EFFR): read as revised data.
KEPT_AS_THEY_STAND = frozenset({"neutral_real_rate", "previous_rate"})


@pytest.fixture
def fred_key() -> None:
    if not has_key("fred"):
        pytest.skip("the live policy-rule run needs a FRED key")


@pytest.mark.usefixtures("fred_key")
def test_taylor_1993_as_of_a_past_date_reads_the_vintages_of_the_day() -> None:
    bound = pyeconomics.bind("macro.policy_rule", as_of=PAST, calculation="taylor_1993")
    result = pyeconomics.run("macro.policy_rule", bound)
    records = {record.field: record for record in result.manifest.data_sources}
    assert set(records) == {
        "inflation",
        "natural_unemployment",
        "neutral_real_rate",
        "previous_rate",
        "unemployment",
    }
    assert records["inflation"].provider == "fred"
    for field, record in records.items():
        if field in KEPT_AS_THEY_STAND:
            assert REVISED_DATA in record.warnings, field
            continue
        assert record.vintage == f"as_of:{PAST.isoformat()}", field
        assert record.realtime is not None, field
        assert record.realtime.covers(PAST), field
        assert REVISED_DATA not in record.warnings, field
    assert 0.0 < result.outputs.prescribed_rate < 0.1

    latest = pyeconomics.bind(
        "macro.policy_rule", as_of=PAST, vintage="latest", calculation="taylor_1993"
    )
    revised = pyeconomics.run("macro.policy_rule", latest)
    assert revised.outputs.prescribed_rate != result.outputs.prescribed_rate
    assert REVISED_DATA in [warning.code for warning in revised.warnings]
    assert all(
        REVISED_DATA in record.warnings for record in revised.manifest.data_sources
    )
