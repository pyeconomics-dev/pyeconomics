# src/pyeconomics/core/schema.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""JSON Schema 2020-12 for a model's inputs and outputs.

Phases 4 and 5 generate CLI options, API schemas, MCP tool schemas and web forms
from these documents, so their shape is part of the contract:

- ``$schema`` is the 2020-12 dialect and ``$id`` is stable:
  ``urn:pyeconomics:model:<id>:<version>:input`` or ``...:output``;
- every numeric field carries ``x-unit`` (ADR-0008 decision 2), its bounds,
  its ``description`` and, for an array, ``maxItems``;
- the input schema lists the specification's examples under ``examples``;
- a family of calculations is ``oneOf`` its members, with a ``discriminator``
  whose mapping is keyed on the ``calculation`` field;
- ``additionalProperties`` is ``false``, as the models forbid unknown fields.

Examples
--------
>>> from pyeconomics.core.schema import SCHEMA_DIALECT, schema_id
>>> SCHEMA_DIALECT
'https://json-schema.org/draft/2020-12/schema'
>>> schema_id("fixed_income.bond", 2, "input")
'urn:pyeconomics:model:fixed_income.bond:2:input'
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final, Literal

if TYPE_CHECKING:
    from pyeconomics.core.model import Model

__all__ = ["SCHEMA_DIALECT", "input_schema", "output_schema", "schema_id"]

#: The JSON Schema dialect every exported schema declares.
SCHEMA_DIALECT: Final = "https://json-schema.org/draft/2020-12/schema"

Side = Literal["input", "output"]


def schema_id(model_id: str, version: int, side: Side) -> str:
    """Return the stable ``$id`` of a model's input or output schema."""
    return f"urn:pyeconomics:model:{model_id}:{version}:{side}"


def _resolve(model: Model[Any, Any] | str) -> Model[Any, Any]:
    if isinstance(model, str):
        from pyeconomics.core.registry import installed  # noqa: PLC0415

        return installed().resolve(model, stacklevel=4)
    return model


def _document(model: Model[Any, Any], side: Side) -> dict[str, Any]:
    adapter = model.input_adapter if side == "input" else model.output_adapter
    mode: Literal["validation", "serialization"] = (
        "validation" if side == "input" else "serialization"
    )
    body: dict[str, Any] = adapter.json_schema(mode=mode)
    title = f"{model.spec.title}: {side}s"
    head: dict[str, Any] = {
        "$schema": SCHEMA_DIALECT,
        "$id": schema_id(model.id, model.version, side),
        "title": title,
        "description": model.spec.summary,
    }
    # The adapter's own title, if any, would be a class name, and its
    # description an input class's docstring: the model's replace both.
    body.pop("title", None)
    body.pop("description", None)
    document = {**head, **body}
    if side == "input":
        document["examples"] = [
            model.validate_inputs(example.inputs).model_dump(mode="json")
            for example in model.spec.examples
        ]
    return document


def input_schema(model: Model[Any, Any] | str) -> dict[str, Any]:
    """Return the JSON Schema 2020-12 document of a model's inputs.

    Parameters
    ----------
    model
        A model object or a registered id (an alias warns and resolves).

    Raises
    ------
    ModelNotFoundError
        If an id is not registered.
    """
    return _document(_resolve(model), "input")


def output_schema(model: Model[Any, Any] | str) -> dict[str, Any]:
    """Return the JSON Schema 2020-12 document of a model's outputs.

    See :func:`input_schema` for the arguments. The document describes outputs
    as serialized, so every field the model always returns is required.
    """
    return _document(_resolve(model), "output")
