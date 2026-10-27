# tests/ai/test_ai_prices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The dated price table: fresh, complete for every default, and exact.

The staleness test reads today's date: it fails once the table is more than
:data:`~pyeconomics.ai.prices.MAX_PRICE_AGE_DAYS` days old, and the fix is to
read every page in :data:`~pyeconomics.ai.prices.SOURCES` again and move their
dates.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal
from urllib.parse import urlsplit

import pytest

from pyeconomics.ai.defaults import (
    CHOSEN_ON,
    DEFAULT_MODEL,
    DEFAULT_PROVIDER,
    PROVIDER_MODELS,
    SELECTOR,
)
from pyeconomics.ai.prices import (
    MAX_PRICE_AGE_DAYS,
    PRICES,
    PRICES_READ_ON,
    SOURCES,
    cost,
    price_for,
)
from pyeconomics.ai.providers import MAX_OUTPUT_TOKENS, PROVIDERS


def test_the_price_table_is_no_more_than_180_days_old() -> None:
    age = (dt.datetime.now(dt.UTC).date() - PRICES_READ_ON).days
    assert MAX_PRICE_AGE_DAYS == 180
    assert age <= MAX_PRICE_AGE_DAYS, (
        f"the AI price table was read {age} days ago; read every page in "
        "pyeconomics.ai.prices.SOURCES again and update the prices and dates"
    )


def test_every_provider_has_a_source_page() -> None:
    assert sorted(SOURCES) == sorted(PROVIDERS)
    for source in SOURCES.values():
        parts = urlsplit(source.url)
        assert parts.scheme == "https"
        assert not parts.query
        assert source.read_on >= PRICES_READ_ON


@pytest.mark.parametrize("provider", sorted(PROVIDERS))
def test_every_providers_default_model_has_a_price(provider: str) -> None:
    assert price_for(provider, PROVIDER_MODELS[provider], PRICES_READ_ON) is not None


def test_the_default_is_the_recorded_selector_choice() -> None:
    assert (DEFAULT_PROVIDER, DEFAULT_MODEL) == ("openai", "gpt-6.1-sol")
    assert PROVIDER_MODELS[DEFAULT_PROVIDER] == DEFAULT_MODEL
    assert sorted(PROVIDER_MODELS) == sorted(PROVIDERS)
    assert SELECTOR.startswith("roadmodel ladder --category knowledge --complexity low")
    assert dt.date(2026, 10, 26) == CHOSEN_ON


def test_every_row_is_a_positive_price_of_a_declared_provider() -> None:
    for row in PRICES:
        assert row.provider in PROVIDERS
        assert row.input_per_million > 0
        assert row.output_per_million >= row.input_per_million


def test_no_two_rows_hold_for_one_model_on_one_day() -> None:
    keys = [(row.provider, row.model, row.starts) for row in PRICES]
    assert len(set(keys)) == len(keys)


def test_a_scheduled_change_takes_effect_on_its_day() -> None:
    before = price_for("gemini", "gemini-3.8-flash", dt.date(2026, 12, 31))
    after = price_for("gemini", "gemini-3.8-flash", dt.date(2027, 1, 1))
    assert before is not None
    assert after is not None
    assert (before.input_per_million, before.output_per_million) == (
        Decimal("0.75"),
        Decimal("3.75"),
    )
    assert (after.input_per_million, after.output_per_million) == (
        Decimal("1.50"),
        Decimal("7.50"),
    )


@pytest.mark.parametrize(
    ("provider", "model", "tokens", "expected"),
    [
        ("openai", "gpt-6.1-sol", (782, 190), "0.003464"),
        ("anthropic", "claude-haiku-5-5", (1_131, 897), "0.0005616"),
        ("gemini", "gemini-3.8-flash", (893, 1_271), "0.00543600"),
        ("openrouter", "openai/gpt-6.1-sol", (782, 185), "0.003414"),
        ("openai", "gpt-6.1-sol", (0, 0), "0"),
    ],
)
def test_the_cost_arithmetic_is_exact(
    provider: str, model: str, tokens: tuple[int, int], expected: str
) -> None:
    price = price_for(provider, model, dt.date(2026, 10, 26))
    assert price is not None
    spent = cost(price, input_tokens=tokens[0], output_tokens=tokens[1])
    assert spent == Decimal(expected)


def test_the_output_limit_bounds_what_one_narrative_of_the_default_costs() -> None:
    price = price_for(DEFAULT_PROVIDER, DEFAULT_MODEL, PRICES_READ_ON)
    assert price is not None
    worst = cost(price, input_tokens=10_000, output_tokens=MAX_OUTPUT_TOKENS)
    assert worst < Decimal("0.07")
