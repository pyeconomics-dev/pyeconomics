# tests/results/test_cards.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Model cards and ``registry.describe``."""

from __future__ import annotations

import dataclasses
import json
import re
import warnings
from typing import Any

import pytest
import toy_models as tm
import toy_results_models as rm

from pyeconomics import registry
from pyeconomics.core import (
    Evidence,
    Example,
    Model,
    ModelCard,
    PyeconomicsDeprecationWarning,
    Registry,
    canonical_json,
    run_model,
)
from pyeconomics.core import registry as core_registry
from pyeconomics.core.cards import (
    BOUND_SECTION_TITLES,
    CURRICULUM_NOTE,
    EVIDENCE_MEANING,
    NOTICE,
    SECTION_TITLES,
)
from pyeconomics.core.describe import DESCRIPTION_KEYS, describe

TOYS = (*tm.ALL_MODELS, *rm.ALL_MODELS)
MODELS: tuple[Model[Any, Any], ...] = (*registry.models(), *TOYS)
IDS = [m.id for m in MODELS]


def headings(markdown: str) -> list[str]:
    return re.findall(r"^## (.+)$", markdown, flags=re.MULTILINE)


@pytest.mark.parametrize("model", MODELS, ids=IDS)
def test_every_card_renders_every_section_in_order(model: Model[Any, Any]) -> None:
    markdown = ModelCard.from_model(model).to_markdown()
    # A model that reads data (the macro catalog) adds the "Data" section.
    titles = BOUND_SECTION_TITLES if model.spec.bindings else SECTION_TITLES
    assert headings(markdown) == list(titles)
    assert markdown.startswith(f"# {model.spec.title}\n")
    assert markdown.endswith("\n")
    assert "\r" not in markdown
    assert NOTICE in markdown
    assert CURRICULUM_NOTE in markdown
    for latex in model.spec.formula:
        assert f"$$\n{latex}\n$$" in markdown
    assert str(ModelCard.from_model(model)) == markdown
    assert ModelCard.from_model(model)._repr_markdown_() == markdown


def test_the_card_text_is_pinned_for_a_scalar_model() -> None:
    markdown = ModelCard.from_model(tm.zero_coupon).to_markdown()
    assert markdown == (
        "# Toy zero-coupon bond price\n"
        "\n"
        "Price of a zero-coupon bond from its annual yield.\n"
        "\n"
        "Model `fixed_income.toy_zero_coupon`, version 1.\n"
        "\n"
        "## Formula\n"
        "\n"
        "$$\n"
        "P = \\frac{F}{(1 + y)^T}\n"
        "$$\n"
        "\n"
        "## Variables\n"
        "\n"
        "### Inputs\n"
        "\n"
        "| Name | Unit | Bounds | Description |\n"
        "| --- | --- | --- | --- |\n"
        "| `face_value` | money | (0, 1e+12] | Face value |\n"
        "| `rate` | rate | [-0.5, 1] | Annual yield |\n"
        "| `years` | years | (0, 100] | Time to maturity |\n"
        "\n"
        "### Outputs\n"
        "\n"
        "| Name | Unit | Bounds | Description |\n"
        "| --- | --- | --- | --- |\n"
        "| `price` | money | [0, 1e+14] | Present value |\n"
        "\n"
        "## Assumptions\n"
        "\n"
        "- The yield is compounded once a year.\n"
        "\n"
        "## Limitations\n"
        "\n"
        "- Ignores credit risk, taxes and settlement conventions.\n"
        "\n"
        "## Evidence\n"
        "\n"
        "Status: **standard**. Textbook consensus, such as bond duration or the "
        "CAPM formula.\n"
        "\n"
        "## Worked example\n"
        "\n"
        "Example `ten_years_at_five_percent`. Inputs:\n"
        "\n"
        "```json\n"
        '{\n  "face_value": 100.0,\n  "rate": 0.05,\n  "years": 10.0\n}\n'
        "```\n"
        "\n"
        "Outputs:\n"
        "\n"
        "```json\n"
        '{\n  "price": 61.39132535407592\n}\n'
        "```\n"
        "\n"
        "## References\n"
        "\n"
        "- Fisher, I. (1930). The Theory of Interest. Macmillan. "
        "https://www.econlib.org/library/YPDBooks/Fisher/fshToI.html (Part I)\n"
        "\n"
        "## Curriculum mapping\n"
        "\n"
        "Not yet mapped; syllabus crosswalks arrive in Phase 7.\n"
        "\n"
        "## Changelog\n"
        "\n"
        "- Version 1: First version.\n"
        "\n"
        "## Notice\n"
        "\n"
        "Educational and informational use only; not investment advice.\n"
    )


def test_a_union_model_has_a_table_per_calculation() -> None:
    markdown = ModelCard.from_model(tm.time_value).to_markdown()
    assert "#### Calculation `present_value`" in markdown
    assert "#### Calculation `future_value`" in markdown
    card = ModelCard.from_model(tm.time_value)
    assert [label for label, _ in card.inputs] == ["present_value", "future_value"]
    assert {v.name for v in card.inputs[0][1]} >= {"future_value", "rate", "years"}


def test_array_fields_show_their_length_and_element_bounds() -> None:
    card = ModelCard.from_model(tm.mean_return)
    ((_, rows),) = card.inputs
    (returns,) = rows
    assert returns.unit == "return (array)"
    assert returns.bounds == "length min 1, max 252; each [-1, 100]"


def test_a_nullable_output_and_a_date_field() -> None:
    card = ModelCard.from_model(rm.dated)
    inputs = {v.name: v for v in card.inputs[0][1]}
    outputs = {v.name: v for v in card.outputs[0][1]}
    assert inputs["start"].unit == "date"
    assert outputs["per_day"].unit == "ratio"
    assert outputs["per_day"].bounds == "[-1e+06, 1e+06]"
    assert outputs["dates"].unit == "date (array)"


def test_the_worked_example_is_the_first_example_with_computed_outputs() -> None:
    example = ModelCard.from_model(rm.dated).example
    assert example is not None
    assert example.name == "thirty"
    assert example.inputs == {"start": "2026-01-31", "days": 30}
    assert example.outputs is not None
    assert example.outputs["end"] == "2026-03-02"
    assert example.unavailable is None


def test_the_worked_example_does_not_leak_the_models_warnings() -> None:

    # The mean-return model warns on all-zero returns; the card runs its example
    # inside a collector, so nothing reaches the warnings machinery.
    zeros = Example(name="zeros", inputs={"returns": [0, 0]})
    spec = dataclasses.replace(tm.mean_return.spec, examples=(zeros,))
    noisy = Model(spec, tm.mean_return.compute)
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        card = ModelCard.from_model(noisy)
    assert card.example is not None
    assert card.example.outputs == {"mean": 0.0, "count": 2}


def test_a_model_whose_extra_is_missing_shows_why_instead_of_outputs() -> None:
    card = ModelCard.from_model(tm.needs_extra)
    assert card.example is not None
    assert card.example.outputs is None
    assert "pyeconomics[toy]" in str(card.example.unavailable)
    assert "Outputs are not available here" in card.to_markdown()
    assert headings(card.to_markdown()) == list(SECTION_TITLES)


def test_a_model_with_no_example_says_so() -> None:
    bare = Model(
        dataclasses.replace(tm.zero_coupon.spec, examples=()), tm.zero_coupon.compute
    )
    card = ModelCard.from_model(bare)
    assert card.example is None
    assert "The model declares no example." in card.to_markdown()


def test_evidence_statuses_all_have_a_meaning_and_show_in_the_card() -> None:
    assert set(EVIDENCE_MEANING) == set(Evidence)
    for status in Evidence:
        spec = dataclasses.replace(tm.zero_coupon.spec, evidence=status)
        text = ModelCard.from_model(Model(spec, tm.zero_coupon.compute)).to_markdown()
        assert f"Status: **{status.value}**. {EVIDENCE_MEANING[status]}" in text
    spec = dataclasses.replace(tm.zero_coupon.spec, evidence=None)
    text = ModelCard.from_model(Model(spec, tm.zero_coupon.compute)).to_markdown()
    assert "Status: **not declared**." in text


def test_references_prefer_a_doi_link_and_end_with_the_locator() -> None:
    card = ModelCard.from_model(rm.growth)
    expected = (
        "Hull, J. (2022). Options, Futures, and Other Derivatives. Pearson. "
        "https://doi.org/10.1000/toy (Chapter 4)"
    )
    assert card.references == (expected,)


def test_table_cells_are_escaped() -> None:
    from pyeconomics.core.cards import Variable, _table  # noqa: PLC0415

    (_, _, row) = _table((Variable("x", "rate", "[0, 1]", "a | b\nc"),))
    assert row == "| `x` | rate | [0, 1] | a \\| b c |"


# --- describe -------------------------------------------------------------------


@pytest.mark.parametrize("model", MODELS, ids=IDS)
def test_describe_is_json_ready_and_canonical(model: Model[Any, Any]) -> None:
    description = describe(model)
    assert tuple(description) == DESCRIPTION_KEYS
    assert description["bindings"] == [b.to_dict() for b in model.spec.bindings]
    canonical_json(description)
    assert json.loads(json.dumps(description)) == description
    assert description["id"] == model.id
    assert description["version"] == model.version
    assert description["domain"] == model.spec.domain
    assert description["card"] == ModelCard.from_model(model).to_markdown()
    assert description["input_schema"]["$id"].endswith(f"{model.version}:input")
    assert description["output_schema"]["$id"].endswith(f"{model.version}:output")


def test_describe_lists_the_specification() -> None:
    description = describe(rm.growth)
    assert description["evidence"] == "standard"
    assert description["cost"] == "instant"
    assert description["tags"] == []
    assert description["references"][0]["doi"] == "10.1000/toy"
    assert description["invariants"] == [
        {"id": "final_is_last", "statement": "final is the last balance."}
    ]
    assert description["examples"] == [
        {
            "name": "five_periods",
            "note": None,
            "inputs": {"start": 100.0, "rate": 0.05, "periods": 5},
        }
    ]
    assert [chart["id"] for chart in description["charts"]] == ["path", "bars", "dots"]
    assert description["charts"][0]["kind"] == "line"
    assert description["charts"][0]["y"] == ["balance"]
    assert description["changelog"] == [{"version": 1, "note": "First version."}]
    assert describe(tm.time_value)["aliases"] == [
        {"id": "foundations.toy_tvm", "removed_in": "2.0.0"}
    ]
    assert describe(tm.needs_extra)["extra"] == "toy"
    assert describe(tm.time_value)["no_invariants_reason"]


def test_the_facade_describes_by_id_and_by_alias(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        core_registry._CACHE,  # noqa: SLF001
        "registry",
        Registry.from_models(*tm.ALL_MODELS, distribution="toy", extras=tm.EXTRAS),
    )
    assert registry.describe("fixed_income.toy_zero_coupon") == describe(tm.zero_coupon)
    with pytest.warns(PyeconomicsDeprecationWarning) as caught:
        description = registry.describe("foundations.toy_tvm")
    assert description["id"] == "foundations.toy_time_value"
    assert caught[0].filename == __file__


def test_a_result_returns_its_models_card() -> None:
    result = run_model(tm.zero_coupon, face_value=100, rate=0.05, years=10)
    assert result.card() == ModelCard.from_model(tm.zero_coupon)


def test_schema_nodes_the_toy_models_do_not_use() -> None:
    from pyeconomics.core.cards import _bounds, _unit, _unwrap  # noqa: PLC0415

    assert _unit({"type": "boolean"}) == "flag"
    assert _unit({"type": "string"}) == "text"
    assert _bounds({"type": "array", "items": {"type": "string"}}) == ""
    assert _bounds({"type": "string", "maxLength": 256}) == "at most 256 characters"
    assert _bounds({"type": "number", "exclusiveMinimum": 0}) == "(0, inf]"
    assert _bounds({"type": "number", "maximum": 1}) == "[-inf, 1]"
    union = {"anyOf": [{"type": "number"}, {"type": "string"}, {"type": "null"}]}
    assert _unwrap(union) is union  # two non-null options: not an optional field


def test_an_examples_note_leads_the_worked_example() -> None:
    noted = Example(name="noted", inputs={"x": 1}, note="A one.")
    spec = dataclasses.replace(rm.no_chart.spec, examples=(noted,))
    markdown = ModelCard.from_model(Model(spec, rm.no_chart.compute)).to_markdown()
    assert "## Worked example\n\nA one.\n\nExample `noted`." in markdown
