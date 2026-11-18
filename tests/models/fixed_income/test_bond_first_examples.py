# tests/models/fixed_income/test_bond_first_examples.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The bond models open on a bond a reader recognises (issue #351).

In three rounds of the site's dogfooding protocol, a visitor asked to price "a
five-year bond with a 4% annual coupon at a 5% yield" reached the answer only
after working out two dates, finding the coupon frequency among the
conventions and reading a price that did not say it was per 100 of face value.
A calculator starts from its model's first example, so each bond model's first
example is that bond, its note gives the answer, and the fields say what a
price is per. These tests hold the notes to the models and to the closed form.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

import pytest

import pyeconomics
from pyeconomics import registry

#: Each model, and the outputs its first example's note quotes to four places.
NOTED = {
    "fixed_income.bond_pricing": {"full_price": "95.6705"},
    "fixed_income.duration": {
        "macaulay_duration": "4.6203",
        "modified_duration": "4.4003",
    },
    "fixed_income.convexity": {"convexity": "24.4724"},
}

COUPON, YIELD, YEARS, FACE = 0.04, 0.05, 5, 100.0


def closed_form_price() -> float:
    """Return the annuity formula's price of the bond, per 100 of face value."""
    discount = (1 + YIELD) ** -YEARS
    return FACE * (COUPON * (1 - discount) / YIELD + discount)


@pytest.mark.parametrize("model_id", sorted(NOTED))
def test_the_first_example_is_a_five_year_annual_bond(model_id: str) -> None:
    example = registry.get(model_id).spec.examples[0]
    assert example.name == "five_year_annual"
    inputs = dict(example.inputs)
    settlement = dt.date.fromisoformat(str(inputs["settlement"]))
    maturity = dt.date.fromisoformat(str(inputs["maturity"]))
    assert maturity == settlement.replace(year=settlement.year + YEARS)
    assert inputs["frequency"] == "annual"
    assert (inputs["coupon_rate"], inputs["yield_to_maturity"]) == (COUPON, YIELD)
    # It prices the default face value, so its price is per 100.
    assert "face_value" not in inputs


@pytest.mark.parametrize("model_id", sorted(NOTED))
def test_the_first_example_s_note_gives_what_the_model_answers(model_id: str) -> None:
    example = registry.get(model_id).spec.examples[0]
    outputs = pyeconomics.run(model_id, dict(example.inputs)).outputs
    assert example.note is not None
    for field, quoted in NOTED[model_id].items():
        assert f"{getattr(outputs, field):.4f}" == quoted
        assert quoted in example.note, (field, example.note)
    assert outputs.full_price == pytest.approx(closed_form_price(), rel=1e-12)


def test_the_closed_form_gives_the_quoted_price() -> None:
    assert (
        f"{closed_form_price():.4f}" == NOTED["fixed_income.bond_pricing"]["full_price"]
    )


@pytest.mark.parametrize("model_id", sorted(NOTED))
def test_a_price_says_what_it_is_per(model_id: str) -> None:
    spec = registry.get(model_id).spec
    outputs: list[Any] = list(spec.output_models)
    inputs: list[Any] = list(spec.input_models)
    for member in outputs:
        field = member.model_fields.get("full_price")
        if field is not None:
            assert "per 100 by default" in (field.description or ""), member
    for member in inputs:
        face = member.model_fields["face_value"].description or ""
        assert "per 100 of face value" in face, member
        maturity = member.model_fields["maturity"].description or ""
        assert "years after settlement" in maturity, member
