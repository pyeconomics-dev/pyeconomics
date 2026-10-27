# src/pyeconomics/ai/prompt.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The narrative's fixed prompt and the facts it is given (ADR-0012 decision 17).

:data:`SYSTEM_PROMPT` is the same for every narrative. :func:`render_prompt`
writes the user's turn from the result's own facts and nothing else: the
model's title, id, version and summary; each input and output with its unit
and description, each number to ten significant digits; the result's
warnings; and the card's assumptions and limitations. The manifest is never
read, so no source record, terms page, retrieval time or hash reaches a
provider, and every piece of text is scrubbed of registered secrets, URLs, host
fields and file paths
(:func:`pyeconomics.surfaces.problems.scrub`). An array shows its first
:data:`MAX_ARRAY_VALUES` values and how many follow.

Examples
--------
>>> import pyeconomics
>>> result = pyeconomics.run(
...     "foundations.time_value",
...     {"calculation": "future_value", "present_value": 100, "rate": 0.05,
...      "periods": 10},
... )
>>> print(render_prompt(result).splitlines()[0])
Model: Time value of money (foundations.time_value, version 2)
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.data.redaction import scrub_text
from pyeconomics.surfaces.problems import scrub

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core.results import Result

__all__ = [
    "MAX_ARRAY_VALUES",
    "MAX_PROMPT_CHARACTERS",
    "SIGNIFICANT",
    "SYSTEM_PROMPT",
    "render_prompt",
]

#: The instructions every narrative is written under.
SYSTEM_PROMPT: Final = (
    "You explain the result of one economic or financial model to a general "
    "reader, in plain language. Use only the facts given: the model, its inputs "
    "and outputs with their units, its warnings, and the assumptions and "
    "limitations of the model. Rates, returns, yields and percentages are given "
    "as decimals: 0.05 means 5%. Do not add other data, forecasts or "
    "recommendations, and do not give investment advice. Mention any warning, "
    "and the assumption or limitation that matters most for reading the "
    "result. Write at most 150 words in one or two short paragraphs of plain "
    "text, without headings, lists or formatting."
)
#: The most values of one array the prompt shows.
MAX_ARRAY_VALUES: Final = 12
#: How a number is written: ten significant digits, which every output's
#: precision exceeds and no platform's last-bit rounding reaches.
SIGNIFICANT: Final = ".10g"
#: The longest prompt sent, in characters.
MAX_PROMPT_CHARACTERS: Final = 32_000
_DEFINITION: Final = "#/$defs/"
_SPACE: Final = re.compile(r"\s+")


def _clean(text: str) -> str:
    """Scrub a piece of text and fold it onto one line."""
    return _SPACE.sub(" ", scrub(scrub_text(text))).strip()


def _resolve(node: Mapping[str, Any], root: Mapping[str, Any]) -> Mapping[str, Any]:
    reference = node.get("$ref")
    if isinstance(reference, str) and reference.startswith(_DEFINITION):
        resolved: Mapping[str, Any] = root["$defs"][reference.removeprefix(_DEFINITION)]
        return resolved
    return node


def _properties(
    root: Mapping[str, Any], values: Mapping[str, object]
) -> Mapping[str, Any]:
    """Return the field schemas of the member of a schema the values belong to."""
    discriminator = root.get("discriminator")
    if not isinstance(discriminator, dict):
        properties: Mapping[str, Any] = root.get("properties", {})
        return properties
    reference = discriminator["mapping"].get(values.get(discriminator["propertyName"]))
    if reference is None:  # pragma: no cover - a result names its calculation
        return {}
    member: Mapping[str, Any] = _resolve({"$ref": reference}, root)["properties"]
    return member


def _unit(node: Mapping[str, Any], root: Mapping[str, Any]) -> str:
    node = _resolve(node, root)
    for candidate in [node, *node.get("anyOf", ())]:
        option = _resolve(candidate, root)
        if isinstance(option.get("x-unit"), str):
            return str(option["x-unit"])
        items = option.get("items")
        if isinstance(items, dict):
            inner = _unit(items, root)
            if inner:
                return f"{inner}, each"
    return ""


def _value(value: object) -> str:
    if isinstance(value, list | tuple):
        shown = ", ".join(_value(item) for item in value[:MAX_ARRAY_VALUES])
        more = len(value) - MAX_ARRAY_VALUES
        return f"[{shown}{f', ... and {more} more' if more > 0 else ''}]"
    if isinstance(value, str):
        return _clean(value)
    if isinstance(value, float):
        return format(value, SIGNIFICANT)
    return canonical_json(value).decode("utf-8")


def _fields(
    title: str, root: Mapping[str, Any], values: Mapping[str, object]
) -> list[str]:
    properties = _properties(root, values)
    lines = [f"{title}:"]
    for name, value in values.items():
        node = properties.get(name, {})
        unit = _unit(node, root)
        description = node.get("description")
        line = f"- {name} = {_value(value)}"
        if unit:
            line += f" (unit: {unit})"
        if isinstance(description, str) and description:
            line += f": {_clean(description)}"
        lines.append(line)
    return lines


def _items(title: str, texts: Iterable[str]) -> list[str]:
    entries = [f"- {_clean(text)}" for text in texts]
    return [f"{title}:", *entries] if entries else [f"{title}: none"]


def render_prompt(result: Result[Any, Any]) -> str:
    """Write the user's turn: the result's own facts, scrubbed, as plain text.

    Raises
    ------
    InputError
        If the prompt would be longer than :data:`MAX_PROMPT_CHARACTERS`.
    """
    model = result.model
    spec = model.spec
    inputs = result.inputs.model_dump(mode="json")
    outputs = result.outputs.model_dump(mode="json")
    lines = [
        (
            f"Model: {_clean(spec.title)} ({result.model_id}, version "
            f"{result.model_version})"
        ),
        f"Summary: {_clean(spec.summary)}",
        *_fields("Inputs", input_schema(model), inputs),
        *_fields("Outputs", output_schema(model), outputs),
        *_items(
            "Warnings",
            (f"{warning.code}: {warning.message}" for warning in result.warnings),
        ),
        *_items("Assumptions", spec.assumptions),
        *_items("Limitations", spec.limitations),
    ]
    prompt = "\n".join(lines)
    if len(prompt) > MAX_PROMPT_CHARACTERS:
        msg = (
            f"the result is too large to narrate: its prompt would be over "
            f"{MAX_PROMPT_CHARACTERS} characters"
        )
        raise InputError(msg)
    return prompt
