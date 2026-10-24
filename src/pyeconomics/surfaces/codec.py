# src/pyeconomics/surfaces/codec.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""Decode a run's inputs: bounded, strict and typed by the model's schema.

Every surface hands what a caller sent to :func:`decode`, which returns a plain
``dict`` of field values for the model to validate:

- **a mapping** (a Python caller, an MCP tool's arguments) is copied, after a
  check that it nests at most :data:`MAX_INPUT_DEPTH` levels, that its keys are
  strings, and that it holds no NaN, infinity, integer beyond ±2\ :sup:`53` or
  lone surrogate, none of which canonical JSON can carry (ADR-0008 decision 12);
- **JSON text or bytes** (an HTTP body, an ``--inputs`` file, standard input)
  is refused above its size limit (:data:`MAX_INPUT_BYTES` by default; hosted
  mode passes :data:`~pyeconomics.surfaces.budgets.HOSTED_BODY_LIMIT`) and above
  :data:`MAX_INPUT_DEPTH` levels of nesting before it is parsed, then parsed
  strictly: one object, no repeated key, no NaN or infinity;
- **``field=value`` pairs** (the command line's generated options) are typed by
  the model's input schema: a number for a numeric field (a boolean is refused,
  as issue #75 fixed in the models), the text itself for a string, a date or a
  choice, ``true`` or ``false`` for a boolean, ``null`` for an optional field and
  a JSON literal for an array or an object.

ADR-0012 decision 10. The codec never evaluates text: no ``eval``, no YAML, no
pickle. It validates
nothing a model validates: bounds, types, required and unknown fields are the
model's own, so an error names the field as the model does. A message never
repeats an input's value.

Examples
--------
>>> decode('{"rate": 0.05, "years": 10}')
{'rate': 0.05, 'years': 10}
>>> decode(b'{"rate": 0.05, "rate": 0.06}')
Traceback (most recent call last):
...
pyeconomics.core.errors.InputError: the inputs repeat the key 'rate'
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import MAX_EXACT_INTEGER
from pyeconomics.core.errors import InputError
from pyeconomics.core.schema import input_schema

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pyeconomics.core.model import Model

__all__ = [
    "MAX_INPUT_BYTES",
    "MAX_INPUT_DEPTH",
    "InputTooLargeError",
    "decode",
    "decode_json",
    "decode_pairs",
]

#: The largest JSON input decoded by default, in bytes: 16 MiB, above the largest
#: valid input of any registered model (ADR-0012 decision 10).
MAX_INPUT_BYTES: Final = 16 * 1024 * 1024
#: The deepest nesting accepted; the top-level object is level 1.
MAX_INPUT_DEPTH: Final = 32

# One JSON token at a time, so a string's brackets are never counted: a string
# (its closing quote optional, so an unterminated one ends the scan instead of
# being retried at every later quote), one bracket, or a run of anything else.
_TOKEN: Final = re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"?|[\[\]{}]|[^"\[\]{}]+', re.DOTALL)
_FIELD: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_NUMBER: Final = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?")
_SURROGATE: Final = re.compile(r"[\ud800-\udfff]")
_BOM: Final = "\ufeff"
#: The JSON type of each value an ``enum`` or ``const`` may hold.
_JSON_TYPES: Final = {
    bool: "boolean",
    int: "integer",
    float: "number",
    str: "string",
    type(None): "null",
}


class InputTooLargeError(InputError):
    """The inputs are larger than the limit the surface decodes.

    Parameters
    ----------
    size
        The size of what was sent, in bytes.
    limit
        The limit, in bytes.
    advice
        What to do instead.

    Examples
    --------
    >>> print(InputTooLargeError(2_000_000, 1_048_576))
    the inputs are 2000000 bytes, above the limit of 1048576; run large inputs locally

    """

    def __init__(
        self, size: int, limit: int, *, advice: str = "run large inputs locally"
    ) -> None:
        super().__init__(
            f"the inputs are {size} bytes, above the limit of {limit}; {advice}"
        )
        self.size = size
        self.limit = limit


def _fail(message: str) -> InputError:
    return InputError(message)


def _refuse_constant(name: str) -> object:
    msg = f"the inputs hold {name}, which is not a finite number"
    raise _fail(msg)


def _unique_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    found: dict[str, object] = {}
    for key, value in pairs:
        if key in found:
            msg = f"the inputs repeat the key {key!r}"
            raise _fail(msg)
        found[key] = value
    return found


def _check_text_depth(text: str, depth: int) -> None:
    """Refuse JSON text nested deeper than ``depth`` levels, without parsing it."""
    level = 0
    for match in _TOKEN.finditer(text):
        kind = match.group()[0]
        if kind in "[{":
            level += 1
            if level > depth:
                msg = f"the inputs nest deeper than {depth} levels"
                raise _fail(msg)
        elif kind in "]}":
            level -= 1


def _check_value(value: object, depth: int) -> None:
    """Refuse what canonical JSON cannot carry, and nesting deeper than ``depth``."""
    pending: list[tuple[object, int]] = [(value, 1)]
    while pending:
        item, level = pending.pop()
        if isinstance(item, Mapping | list | tuple):
            if level > depth:
                msg = f"the inputs nest deeper than {depth} levels"
                raise _fail(msg)
            pending.extend((child, level + 1) for child in _children(item))
        else:
            _check_scalar(item)


def _children(
    item: Mapping[object, object] | list[object] | tuple[object, ...],
) -> list[object]:
    """Return a container's values, checking a mapping's keys on the way."""
    if not isinstance(item, Mapping):
        return list(item)
    for key in item:
        if not isinstance(key, str):
            msg = f"an input name is text, not {type(key).__name__}"
            raise _fail(msg)
        _check_text(key)
    return list(item.values())


def _check_scalar(item: object) -> None:
    if isinstance(item, str):
        _check_text(item)
    elif isinstance(item, bool):
        return
    elif isinstance(item, int) and abs(item) > MAX_EXACT_INTEGER:
        msg = f"the inputs hold an integer beyond ±{MAX_EXACT_INTEGER}"
        raise _fail(msg)
    elif isinstance(item, float) and not math.isfinite(item):
        msg = "the inputs hold a number that is not finite"
        raise _fail(msg)


def _check_text(text: str) -> None:
    if _SURROGATE.search(text):
        msg = "the inputs hold text with a lone surrogate, which is not Unicode"
        raise _fail(msg)


def _text(document: str | bytes | bytearray, limit: int) -> str:
    """Return a document as text, refusing it above ``limit`` bytes or not UTF-8."""
    if isinstance(document, str):
        size = len(document)
        if size <= limit and not document.isascii():
            size = len(document.encode("utf-8", "surrogatepass"))
        text = document
    else:
        size = len(document)
        if size > limit:
            raise InputTooLargeError(size, limit)
        try:
            text = bytes(document).decode("utf-8")
        except UnicodeDecodeError as error:
            msg = "the inputs are not UTF-8 text"
            raise _fail(msg) from error
    if size > limit:
        raise InputTooLargeError(size, limit)
    return text.removeprefix(_BOM)


def _loads(text: str, depth: int) -> object:
    """Parse one JSON value strictly, after its depth has been checked."""
    _check_text_depth(text, depth)
    try:
        value = json.loads(
            text, parse_constant=_refuse_constant, object_pairs_hook=_unique_keys
        )
    except InputError:
        raise
    except (ValueError, RecursionError) as error:
        msg = f"the inputs are not a JSON document: {error}"
        raise _fail(msg) from error
    _check_value(value, depth)
    return value


def decode_json(
    document: str | bytes | bytearray, *, limit: int = MAX_INPUT_BYTES
) -> dict[str, object]:
    r"""Decode a JSON object of inputs, refusing it above ``limit`` bytes.

    A UTF-8 byte-order mark at the start is ignored, as Windows editors write one.

    Raises
    ------
    InputTooLargeError
        If the document is larger than ``limit`` bytes.
    InputError
        If it is not UTF-8, nests deeper than :data:`MAX_INPUT_DEPTH` levels, is
        not one JSON object, repeats a key, or holds NaN, infinity, an integer
        beyond ±2\ :sup:`53` or a lone surrogate.
    """
    value = _loads(_text(document, limit), MAX_INPUT_DEPTH)
    if not isinstance(value, dict):
        msg = f"the inputs are a JSON object, not {type(value).__name__}"
        raise _fail(msg)
    return value


def _resolve(schema: Mapping[str, Any], root: Mapping[str, Any]) -> Mapping[str, Any]:
    """Follow a local ``$ref`` into the document's ``$defs``."""
    reference = schema.get("$ref")
    if isinstance(reference, str) and reference.startswith("#/$defs/"):
        resolved: Mapping[str, Any] = root["$defs"][reference.removeprefix("#/$defs/")]
        return resolved
    return schema


def _properties(
    model: Model[Any, Any], root: Mapping[str, Any], raw: Mapping[str, str]
) -> Mapping[str, Any]:
    """Return the field schemas of the model, or of the calculation named."""
    discriminator = root.get("discriminator")
    if not isinstance(discriminator, Mapping):
        properties: Mapping[str, Any] = root.get("properties", {})
        return properties
    name = discriminator["propertyName"]
    mapping = discriminator["mapping"]
    choices = ", ".join(sorted(mapping))
    if name not in raw:
        msg = f"{model.id} has several calculations; name one with {name}=<name>"
        msg += f" (one of: {choices})"
        raise _fail(msg)
    if raw[name] not in mapping:
        msg = f"{model.id} has no {name} of that name; its calculations: {choices}"
        raise _fail(msg)
    member = _resolve({"$ref": mapping[raw[name]]}, root)
    member_properties: Mapping[str, Any] = member["properties"]
    return member_properties


def _kinds(schema: Mapping[str, Any], root: Mapping[str, Any]) -> set[str]:
    """Return the JSON types a field's schema accepts, through refs and anyOf."""
    options = schema.get("anyOf", [schema])
    kinds: set[str] = set()
    for option in options:
        resolved = _resolve(option, root)
        kind = resolved.get("type")
        if isinstance(kind, str):
            kinds.add(kind)
        elif isinstance(kind, list):
            kinds.update(k for k in kind if isinstance(k, str))
        else:
            values = list(resolved.get("enum", ()))
            if "const" in resolved:
                values.append(resolved["const"])
            kinds.update(_JSON_TYPES.get(type(v), "string") for v in values)
    return kinds


def _typed(name: str, text: str, kinds: set[str], limit: int) -> object:
    """Type one value's text by the JSON types its field accepts."""
    if "null" in kinds and text == "null":
        return None
    if kinds & {"array", "object"} and text[:1] in {"[", "{"}:
        return _loads(_text(text, limit), MAX_INPUT_DEPTH - 1)
    if kinds & {"number", "integer"} and _NUMBER.fullmatch(text):
        number: object = json.loads(text)
        _check_value(number, 1)
        return number
    if "boolean" in kinds and text in {"true", "false"}:
        return text == "true"
    if "string" in kinds or not kinds:
        return text
    if kinds & {"number", "integer"}:
        why = "a boolean" if text in {"true", "false"} else "that text"
        msg = f"{name} takes a number, not {why}"
        raise _fail(msg)
    expected = " or ".join(sorted(kinds - {"null"}))
    msg = f"{name} takes {expected}; write it as a JSON literal"
    raise _fail(msg)


def decode_pairs(
    model: Model[Any, Any], pairs: Iterable[object], *, limit: int = MAX_INPUT_BYTES
) -> dict[str, object]:
    """Decode ``field=value`` pairs, typing each value by the model's input schema.

    A field the schema does not list is passed on as text, for the model to
    refuse by name. A model with several calculations needs its
    ``calculation=<name>`` pair, which picks the fields' schemas.

    Raises
    ------
    InputError
        For a pair without ``=`` or with an invalid name, a repeated field, a
        missing or unknown calculation, a numeric field given anything but a
        JSON number (a boolean included), or an array or object field given
        anything but a JSON literal.
    """
    raw: dict[str, str] = {}
    for index, pair in enumerate(pairs, start=1):
        if not isinstance(pair, str):
            msg = f"input {index} is a {type(pair).__name__}, not field=value text"
            raise _fail(msg)
        name, separator, text = pair.partition("=")
        if not separator or not _FIELD.fullmatch(name):
            msg = f"input {index} is not written field=value"
            raise _fail(msg)
        if name in raw:
            msg = f"the inputs repeat the field {name!r}"
            raise _fail(msg)
        _check_text(text)
        raw[name] = text
    root = input_schema(model)
    properties = _properties(model, root, raw)
    decoded: dict[str, object] = {}
    for name, text in raw.items():
        schema = properties.get(name)
        kinds = set() if schema is None else _kinds(schema, root)
        decoded[name] = _typed(name, text, kinds, limit)
    return decoded


def decode(
    inputs: object,
    model: Model[Any, Any] | None = None,
    *,
    limit: int = MAX_INPUT_BYTES,
) -> dict[str, object]:
    """Decode a run's inputs from whatever a surface received.

    Parameters
    ----------
    inputs
        ``None`` (no inputs), a mapping, JSON text or bytes, or a list or tuple
        of ``field=value`` strings.
    model
        The model the inputs are for; needed to type ``field=value`` pairs.
    limit
        The largest JSON document accepted, in bytes.

    Returns
    -------
    dict
        The field values, for the model to validate.

    Raises
    ------
    InputTooLargeError
        If a JSON document is larger than ``limit``.
    InputError
        As :func:`decode_json` and :func:`decode_pairs` raise it, for a mapping
        that nests too deep or holds a value canonical JSON cannot carry, or for
        inputs of any other type.
    """
    if inputs is None:
        return {}
    if isinstance(inputs, Mapping):
        _check_value(inputs, MAX_INPUT_DEPTH)
        return dict(inputs)
    if isinstance(inputs, str | bytes | bytearray):
        return decode_json(inputs, limit=limit)
    if isinstance(inputs, list | tuple):
        if model is None:
            msg = "field=value inputs need the model whose schema types them"
            raise _fail(msg)
        return decode_pairs(model, inputs, limit=limit)
    msg = (
        "inputs are a mapping, JSON text or bytes, or field=value pairs, "
        f"not {type(inputs).__name__}"
    )
    raise _fail(msg)
