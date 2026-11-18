# tests/registry/test_formula_symbols.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every model says what its formulas' symbols stand for (issue #343).

Round 0 and round 1 of the site's dogfooding protocol each found that a reader
could not tell what a formula's symbols meant: a card showed the LaTeX and the
fields, with nothing between them. A model now declares ``symbols``, the card
lists them under the formulas, and the web app reads that list back, so its
shape is pinned here.
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any

import pytest
import toy_models as tm

from pyeconomics import registry
from pyeconomics.core import Model, Symbol
from pyeconomics.core.cards import ModelCard

#: A line of a card's "Where" list, as ``web/src/lib/models.ts`` reads it.
WHERE_LINE = re.compile(
    r"^- \$(?P<symbol>[^$]+)\$: (?P<meaning>.+?)"
    r"(?: \(`(?P<field>[a-z0-9_]+)`\))?$"
)

MODELS = registry.models()


def _where(card: str) -> list[re.Match[str]]:
    section = card.split("\n## Formula\n", 1)[1].split("\n## ", 1)[0]
    lines = [line for line in section.split("\n") if line.startswith("- ")]
    matches = [WHERE_LINE.fullmatch(line) for line in lines]
    unread = [line for line, match in zip(lines, matches, strict=True) if not match]
    assert not unread, unread
    return [match for match in matches if match]


@pytest.mark.parametrize("model", MODELS, ids=[model.spec.id for model in MODELS])
def test_every_model_defines_the_symbols_of_its_formulas(
    model: Model[Any, Any],
) -> None:
    spec = model.spec
    assert len(spec.symbols) >= 3, f"{spec.id} defines {len(spec.symbols)} symbols"
    members: list[Any] = [*spec.input_models, *spec.output_models]
    fields: set[str] = set()
    for member in members:
        fields.update(member.model_fields)
    for symbol in spec.symbols:
        assert any(symbol.symbol in formula for formula in spec.formula), symbol
        assert symbol.field is None or symbol.field in fields, symbol
        # A meaning is a phrase, not a sentence: it starts a line of the list.
        assert symbol.meaning[0].isupper() or symbol.meaning[0].isdigit(), symbol
        assert not symbol.meaning.endswith("."), symbol


@pytest.mark.parametrize("model", MODELS, ids=[model.spec.id for model in MODELS])
def test_every_card_lists_its_symbols_in_the_shape_the_web_app_reads(
    model: Model[Any, Any],
) -> None:
    card = ModelCard.from_model(model).to_markdown()
    found = _where(card)
    assert [(match["symbol"], match["meaning"], match["field"]) for match in found] == [
        (symbol.symbol, symbol.meaning, symbol.field) for symbol in model.spec.symbols
    ]
    assert "\nWhere:\n\n- $" in card


def test_a_model_without_symbols_has_no_where_list() -> None:
    card = ModelCard.from_model(tm.zero_coupon).to_markdown()
    assert tm.zero_coupon.spec.symbols == ()
    assert "Where:" not in card


def test_the_where_list_sits_between_the_formulas_and_the_variables() -> None:
    spec = dataclasses.replace(
        tm.zero_coupon.spec,
        symbols=(
            Symbol("P", "Price of the bond", "price"),
            Symbol("y", "Yield to maturity"),
        ),
    )
    card = ModelCard.from_model(Model(spec, tm.zero_coupon.compute)).to_markdown()
    assert (
        "$$\n\nWhere:\n\n"
        "- $P$: Price of the bond (`price`)\n"
        "- $y$: Yield to maturity\n\n"
        "## Variables\n"
    ) in card


def test_a_symbol_is_positional_and_frozen() -> None:
    symbol = Symbol(
        r"D_{\mathrm{Mac}}", "Macaulay duration, in years", "macaulay_duration"
    )
    assert (symbol.symbol, symbol.field) == (
        r"D_{\mathrm{Mac}}",
        "macaulay_duration",
    )
    assert Symbol("y", "Yield").field is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        symbol.meaning = "other"  # type: ignore[misc]
