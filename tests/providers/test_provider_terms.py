# tests/providers/test_provider_terms.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A provider's terms are read again within 13 months (ADR-0011 decision 7).

ROADMAP section 5's yearly review becomes a check: a registered provider whose
terms-checked date is more than 13 months old fails here, which is why the check
is a test and not a ``validate()`` rule: ``validate()`` reads no clock. The toys'
terms are fixtures with a fixed date, so they are judged on the day they were
written; the rule they exercise is the same.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace

import pytest
from stubs import STUB_TERMS
from toys import ToyJson, ToyVintage

from pyeconomics.data import TERMS_MAX_AGE_MONTHS, DataProvider, registry

TODAY = dt.datetime.now(dt.UTC).date()


def stale_providers(providers: list[type[DataProvider]], today: dt.date) -> list[str]:
    """Return the ids of providers whose terms are older than 13 months on ``today``."""
    return sorted(p.info.id for p in providers if p.info.terms.is_stale(today))


def test_no_registered_provider_has_stale_terms() -> None:
    real = [type(registry.get(provider_id)) for provider_id in registry.ids()]
    assert stale_providers(real, TODAY) == [], (
        "read the terms page again, update the Terms (date, wording, class) and the "
        "notices test, and record any change in the changelog (ADR-0005 rule 7)"
    )


def test_the_horizon_is_thirteen_months() -> None:
    assert TERMS_MAX_AGE_MONTHS == 13


def test_the_check_fails_a_provider_the_day_after_thirteen_months() -> None:
    providers = [ToyJson, ToyVintage]
    checked = ToyJson.info.terms.checked  # 2026-10-15
    assert stale_providers(providers, dt.date(2027, 11, 15)) == []
    assert stale_providers(providers, dt.date(2027, 11, 16)) == [
        "toy_json",
        "toy_vintage",
    ]
    assert checked == dt.date(2026, 10, 15)


@pytest.mark.parametrize(
    ("checked", "last_good_day"),
    [
        (dt.date(2026, 1, 31), dt.date(2027, 2, 28)),
        (dt.date(2024, 1, 31), dt.date(2025, 2, 28)),
        (dt.date(2026, 10, 15), dt.date(2027, 11, 15)),
    ],
)
def test_month_ends_clamp_to_the_months_last_day(
    checked: dt.date, last_good_day: dt.date
) -> None:
    terms = replace(STUB_TERMS, checked=checked)
    assert not terms.is_stale(last_good_day)
    assert terms.is_stale(last_good_day + dt.timedelta(days=1))
