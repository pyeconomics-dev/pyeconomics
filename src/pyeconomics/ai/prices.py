# src/pyeconomics/ai/prices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The dated price table a narrative's cost comes from (ADR-0012 decision 17).

Each :class:`Price` is one model's list price per million input and output
tokens, in US dollars, at the standard tier without caching or batching, read
from its provider's page in :data:`SOURCES` on the date given there. A price
that the page schedules to change has one row per period, each from its
``starts`` day, and :func:`price_for` picks the row in force on the day the
answer arrived. A model missing from the table has no cost: the narrative says
so rather than guess.

The cost is an upper bound when a provider caches part of a prompt, since a
cached token costs less than the list price used here. Reasoning ("thinking")
tokens are billed as output, and every provider counts them in the output
tokens the cost uses. Claude Haiku 5.5's price holds for prompts up to 100,000
tokens; a narrative's prompt is far below that (:data:`~pyeconomics.ai.prompt.
MAX_PROMPT_CHARACTERS`).

The table is read again within :data:`MAX_PRICE_AGE_DAYS`: a test fails when
:data:`PRICES_READ_ON` is older. Nothing here reads the clock.

Examples
--------
>>> import datetime as dt
>>> price = price_for("openai", "gpt-6.1-sol", dt.date(2026, 10, 26))
>>> price.input_per_million, price.output_per_million
(Decimal('2.00'), Decimal('10.00'))
>>> cost(price, input_tokens=1_000, output_tokens=500)
Decimal('0.007')
>>> price_for("gemini", "gemini-3.8-flash", dt.date(2027, 1, 1)).input_per_million
Decimal('1.50')
>>> price_for("openai", "no-such-model", dt.date(2026, 10, 26)) is None
True
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

__all__ = [
    "MAX_PRICE_AGE_DAYS",
    "PRICES",
    "PRICES_READ_ON",
    "SOURCES",
    "Price",
    "PriceSource",
    "cost",
    "price_for",
]

#: Prices read longer ago than this many days are stale: a test fails on them.
MAX_PRICE_AGE_DAYS: Final = 180
_MILLION: Final = Decimal(1_000_000)


@dataclass(frozen=True, slots=True)
class PriceSource:
    """Where a provider's prices were read, and when."""

    url: str
    read_on: dt.date


@dataclass(frozen=True, slots=True)
class Price:
    """One model's list price per million tokens, in US dollars, from a day on."""

    provider: str
    model: str
    input_per_million: Decimal
    output_per_million: Decimal
    starts: dt.date | None = None
    """The first day the price holds; ``None`` for a price with no start."""


#: The pages each provider's prices were read from.
SOURCES: Final = {
    "anthropic": PriceSource(
        "https://platform.claude.com/docs/en/about-claude/pricing",
        dt.date(2026, 10, 26),
    ),
    "gemini": PriceSource(
        "https://ai.google.dev/gemini-api/docs/pricing", dt.date(2026, 10, 26)
    ),
    "openai": PriceSource(
        "https://developers.openai.com/api/docs/pricing", dt.date(2026, 10, 26)
    ),
    "openrouter": PriceSource(
        "https://openrouter.ai/api/v1/models", dt.date(2026, 10, 26)
    ),
}
#: The oldest date in :data:`SOURCES`: the table is as fresh as its oldest read.
PRICES_READ_ON: Final = min(source.read_on for source in SOURCES.values())


def _price(
    provider: str,
    model: str,
    prices: tuple[str, str],
    starts: dt.date | None = None,
) -> Price:
    return Price(provider, model, Decimal(prices[0]), Decimal(prices[1]), starts)


#: The price table: input and output dollars per million tokens.
PRICES: Final = (
    _price("anthropic", "claude-haiku-5-5", ("0.10", "0.50")),
    _price("anthropic", "claude-sonnet-5-5", ("2.00", "10.00")),
    _price("anthropic", "claude-opus-5-5", ("4.00", "20.00")),
    _price("gemini", "gemini-3.8-flash", ("0.75", "3.75")),
    _price("gemini", "gemini-3.8-flash", ("1.50", "7.50"), dt.date(2027, 1, 1)),
    _price("gemini", "gemini-4-argon", ("2.00", "10.00")),
    _price("gemini", "gemini-4-argon", ("4.00", "20.00"), dt.date(2026, 12, 1)),
    _price("gemini", "gemini-3.5-flash-lite", ("0.30", "2.50")),
    _price("openai", "gpt-6.1-sol", ("2.00", "10.00")),
    _price("openai", "gpt-6.1-terra", ("1.00", "5.00")),
    _price("openai", "gpt-6-luna", ("0.10", "0.50")),
    _price("openai", "gpt-6-astra", ("10.00", "50.00")),
    _price("openrouter", "openai/gpt-6.1-sol", ("2.00", "10.00")),
    _price("openrouter", "anthropic/claude-haiku-5.5", ("0.10", "0.50")),
    _price("openrouter", "google/gemini-3.8-flash", ("0.825", "4.125")),
)


def price_for(provider: str, model: str, on: dt.date) -> Price | None:
    """Return a model's price in force on a day, or ``None`` if the table has none."""
    rows = [
        row
        for row in PRICES
        if row.provider == provider
        and row.model == model
        and (row.starts is None or row.starts <= on)
    ]
    if not rows:
        return None
    return max(rows, key=lambda row: row.starts or dt.date.min)


def cost(price: Price, *, input_tokens: int, output_tokens: int) -> Decimal:
    """Return the dollars a call cost: each kind of token at its list price."""
    spent = (
        Decimal(input_tokens) * price.input_per_million
        + Decimal(output_tokens) * price.output_per_million
    ) / _MILLION
    return spent.normalize()
