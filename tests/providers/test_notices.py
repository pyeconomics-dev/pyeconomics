# tests/providers/test_notices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A reviewed diff for every notice (ADR-0005's Confirmation).

"A test per provider checks the exact wording": ``NOTICES`` pins, per provider, the
exact attribution, the exact required notice (or ``None``) and the terms page, each
quoted from the terms page on the provider's terms-checked date. A change to a
notice is then a diff someone reads. The suite fails for a registered provider
without a row, and for a row without a provider. Every provider step adds its
providers' rows.

The toys' rows pin the toys' own invented wording.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import replace
from typing import TYPE_CHECKING, NamedTuple

import pytest
from toys import ToyJson, ToyVintage

from pyeconomics.data import DataProvider, registry

if TYPE_CHECKING:
    from collections.abc import Iterable


class Row(NamedTuple):
    """The wording pinned for one provider."""

    attribution: str
    notice: str | None
    terms_url: str
    checked: dt.date


NOTICES: dict[str, Row] = {
    "toy_json": Row(
        attribution="Source: Toy JSON Agency (a test fixture with invented numbers).",
        notice=(
            "This product uses the Toy JSON API but is not endorsed by Toy JSON Agency."
        ),
        terms_url="https://www.toyjson.example.org/terms",
        checked=dt.date(2026, 10, 15),
    ),
    "toy_vintage": Row(
        attribution="Source: Toy Vintage Bank (a test fixture with invented numbers).",
        notice=None,
        terms_url="https://www.toyvintage.example.org/terms",
        checked=dt.date(2026, 10, 15),
    ),
}

PROVIDERS: tuple[type[DataProvider], ...] = (
    ToyJson,
    ToyVintage,
    *(type(registry.get(provider_id)) for provider_id in registry.ids()),
)


@pytest.mark.parametrize("provider", PROVIDERS, ids=lambda p: p.info.id)
def test_the_wording_is_exactly_what_the_row_pins(provider: type[DataProvider]) -> None:
    row = NOTICES[provider.info.id]
    terms = provider.info.terms
    assert terms.attribution == row.attribution
    assert terms.notice == row.notice
    assert terms.terms_url == row.terms_url
    assert terms.checked == row.checked


def unpinned(
    providers: Iterable[type[DataProvider]], notices: dict[str, Row]
) -> list[str]:
    """Return the ids of providers that have no pinned row."""
    return sorted(p.info.id for p in providers if p.info.id not in notices)


def test_every_registered_provider_has_a_row_and_every_row_a_provider() -> None:
    assert unpinned(PROVIDERS, NOTICES) == []
    assert {p.info.id for p in PROVIDERS} == set(NOTICES)


def test_a_provider_without_a_row_fails_the_suite() -> None:
    other = type("Other", (ToyJson,), {"info": replace(ToyJson.info, id="unpinned")})
    assert unpinned([*PROVIDERS, other], NOTICES) == ["unpinned"]
