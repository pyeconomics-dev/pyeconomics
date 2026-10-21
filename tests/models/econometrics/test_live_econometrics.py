# tests/models/econometrics/test_live_econometrics.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The Step 17 models bind their demonstration data live (``pytest -m live``).

``econometrics.garch`` binds 1,000 trading days of the Ken French daily market
factor (library-only, fetched inside ``cache.bypass()`` so nothing is stored);
``econometrics.time_series`` binds 240 months of US CPI inflation and the
unemployment rate, real-time through ALFRED with the tester's FRED key. The
time-series windows end before October 2025, which BLS never published. The
weekly live run (providers-live.yml) executes them.
"""

from __future__ import annotations

import datetime as dt
import math
import sys
from typing import Any

import pytest

from pyeconomics.core import MissingOptionalDependencyError, run_model
from pyeconomics.core.binding import REVISED_DATA
from pyeconomics.data import cache
from pyeconomics.data.bindings import bind_model
from pyeconomics.models.econometrics import garch, time_series

pytestmark = pytest.mark.live

#: The cells the econometrics extra cannot install arch on (issue #154).
GAP = sys.version_info >= (3, 15)
DAILY_AS_OF = dt.date(2025, 12, 31)
MONTHLY_AS_OF = dt.date(2025, 9, 30)


def _bind(model: Any, as_of: dt.date, **options: Any) -> Any:  # noqa: ANN401
    with cache.bypass():
        return bind_model(model, as_of=as_of, **options)


@pytest.mark.parametrize("calculation", ["garch", "gjr", "egarch"])
def test_garch_binds_the_daily_market_factor(calculation: str) -> None:
    given = {"calculation": calculation, "periods_per_year": 252}
    bound = _bind(garch, DAILY_AS_OF, overrides=given)
    assert len(bound.values["returns"]) == 1000
    (record,) = bound.sources
    assert record.provider == "ken_french"
    assert record.concept == "factors.ff3_market.us.daily"
    assert record.observation_end <= DAILY_AS_OF
    assert REVISED_DATA in record.warnings  # the library keeps no vintages
    if GAP:
        with pytest.raises(MissingOptionalDependencyError, match=r"CPython 3.15"):
            run_model(garch, bound)
        return
    outputs = run_model(garch, bound).outputs
    assert 0.0 < outputs.last_volatility_annualized < 2.0
    assert outputs.persistence < 1.05
    assert all(math.isfinite(v) for v in outputs.variance_forecasts)


def test_garch_rebinds_to_another_daily_return_series() -> None:
    given = {"calculation": "garch", "periods_per_year": 252}
    bound = _bind(
        garch,
        DAILY_AS_OF,
        concepts={"returns": "factors.ff3_smb.us.daily"},
        overrides=given,
    )
    (record,) = bound.sources
    assert record.concept == "factors.ff3_smb.us.daily"
    assert len(bound.values["returns"]) == 1000


@pytest.mark.parametrize("calculation", ["arima", "var", "engle_granger", "johansen"])
def test_time_series_binds_inflation_and_unemployment(calculation: str) -> None:
    bound = _bind(time_series, MONTHLY_AS_OF, overrides={"calculation": calculation})
    expected = {"series"} if calculation == "arima" else {"series", "second"}
    assert set(bound.values) - {"calculation"} == expected
    assert all(len(bound.values[field]) == 240 for field in expected)
    concepts = {record.field: record.concept for record in bound.sources}
    assert concepts["series"] == "us.inflation.cpi.yoy"
    if calculation != "arima":
        assert concepts["second"] == "us.unemployment.rate"
    assert len({record.observation_end for record in bound.sources}) == 1
    outputs = run_model(time_series, bound).outputs
    assert outputs.calculation == calculation


def test_time_series_rebinds_to_another_monthly_rate() -> None:
    bound = _bind(
        time_series,
        MONTHLY_AS_OF,
        concepts={"second": "us.inflation.cpi_core.yoy"},
        overrides={"calculation": "var", "max_lags": 6},
    )
    concepts = {record.field: record.concept for record in bound.sources}
    assert concepts["second"] == "us.inflation.cpi_core.yoy"
    outputs = run_model(time_series, bound).outputs
    assert 1 <= outputs.lags <= 6
