# tests/models/test_catalog_documents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every registered model's card renders and its schemas are valid 2020-12.

The card is what Phase 5 renders as a page and the schemas what Phase 4 builds
its CLI, REST API and MCP tools from, so both are held for the installed
catalog, not only for the toy models of ``tests/results/``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from extra_gaps import excluded_gap
from jsonschema import Draft202012Validator

from pyeconomics.core import ModelCard, input_schema, output_schema
from pyeconomics.core.registry import installed

if TYPE_CHECKING:
    from pyeconomics.core import Model

MODELS = [pytest.param(m, id=m.id) for m in installed().models()]


@pytest.mark.parametrize("model", MODELS)
def test_the_card_renders_with_its_worked_example(model: Model[Any, Any]) -> None:
    text = ModelCard.from_model(model).to_markdown()
    assert text.startswith(f"# {model.spec.title}")
    assert model.id in text
    for reference in model.spec.references:
        assert reference.citation in text
    # Where the model's extra leaves its library out of this Python (the Wheel
    # rule), the card says the example cannot run here; elsewhere it shows it.
    unavailable = "Outputs are not available here" in text
    assert unavailable is (excluded_gap(model) is not None)


@pytest.mark.parametrize("model", MODELS)
def test_the_schemas_are_valid_2020_12(model: Model[Any, Any]) -> None:
    for schema in (input_schema(model), output_schema(model)):
        Draft202012Validator.check_schema(schema)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("model", MODELS)
def test_every_example_validates_against_the_input_schema(
    model: Model[Any, Any],
) -> None:
    validator = Draft202012Validator(input_schema(model))
    for example in model.spec.examples:
        validated = model.validate_inputs(example.inputs)
        document = model.input_adapter.dump_python(validated, mode="json")
        assert not list(validator.iter_errors(document)), example.name
