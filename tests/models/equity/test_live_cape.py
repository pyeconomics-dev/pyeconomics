# tests/models/equity/test_live_cape.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``equity.cape`` reproduces Shiller's published CAPE (``pytest -m live``).

Shiller's data is library-only: none of it is committed, so this check reads his
file at run time through the ``shiller`` provider, inside ``cache.bypass()`` so
nothing is stored, and compares the model with his CAPE column for several months.
His CAPE for a month is its real price over the average real earnings of the 120
months before it, and the file stores it at full precision, so the agreement is
to rounding. The weekly live run (providers-live.yml) executes it; it needs no key.
"""

from __future__ import annotations

import datetime as dt
import math

import pytest

import pyeconomics
from pyeconomics.core import run_model
from pyeconomics.data import Table, cache
from pyeconomics.data import get as get_data
from pyeconomics.models.equity import cape

pytestmark = pytest.mark.live

#: Months spread over his history, each with 120 months of earnings before it.
MONTHS = (
    dt.date(1929, 9, 30),
    dt.date(1966, 1, 31),
    dt.date(1982, 7, 31),
    dt.date(2000, 3, 31),
    dt.date(2009, 3, 31),
    dt.date(2021, 11, 30),
)
#: A bind as of this date reads December 2020 and the 120 months before it.
AS_OF = dt.date(2021, 1, 15)


@pytest.fixture(scope="module")
def shiller() -> Table:
    """Shiller's monthly table, fetched now and stored nowhere."""
    with cache.bypass():
        frame = get_data("equity.shiller.us.monthly").frame
    assert isinstance(frame, Table)
    return frame


def _column(table: Table, name: str) -> dict[dt.date, float | None]:
    series = table.column(name)
    return dict(zip(series.index, series.values, strict=True))


def test_the_model_reproduces_shillers_cape(shiller: Table) -> None:
    price, earnings = _column(shiller, "price"), _column(shiller, "earnings")
    cpi, published = _column(shiller, "cpi"), _column(shiller, "cape")
    months = sorted(price)
    for month in MONTHS:
        at = months.index(month)
        window = months[at - 120 : at]
        out = run_model(
            cape,
            {
                "price": price[month],
                "price_cpi": cpi[month],
                "earnings": [earnings[m] for m in window],
                "cpi": [cpi[m] for m in window],
                "real_yield": 0.0,
            },
        ).outputs
        expected = published[month]
        assert expected is not None
        assert math.isclose(out.cape, expected, rel_tol=1e-9), month


def test_a_bind_reproduces_shillers_cape_for_its_month(shiller: Table) -> None:
    with cache.bypass():
        bound = pyeconomics.bind("equity.cape", as_of=AS_OF, profile="nominal")
        result = pyeconomics.run("equity.cape", bound)
    by_field = {r.field: r for r in result.manifest.data_sources}
    december = dt.date(2020, 12, 31)
    assert by_field["price"].observation_end == december
    assert by_field["earnings"].observation_end == december
    expected = _column(shiller, "cape")[december]
    assert expected is not None
    assert math.isclose(result.outputs.cape, expected, rel_tol=1e-9)
    assert "shiller" in {r.provider for r in result.manifest.data_sources}
