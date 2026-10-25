# src/pyeconomics/mcp/schemas.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The JSON Schemas of the MCP tools' inputs and outputs (ADR-0012 decision 13).

Every schema is a self-contained JSON Schema 2020-12 document whose root is an
object, which every protocol revision accepts:

- a headline tool's input is its model's own input schema
  (:func:`pyeconomics.core.schema.input_schema`), with ``"type": "object"`` at
  the root of a family of calculations, whose members already are objects;
- a run's output is the result envelope (:func:`result_output`): the model's
  validated inputs and its outputs, from the model's own schemas, the warnings
  and the manifest, from the same definitions ``registry.json``'s schema uses.
  :func:`run_output` is the same envelope for any model, for ``run_model``;
- in hosted mode a run's output may instead be a large result's notice
  (:func:`with_notice`): its summary, size, hash and the REST download;
- the discovery tools' outputs mirror the REST API's documents: model entries,
  a model's description, a series document and the sources.

An embedded document keeps its own definitions under ``$defs``, prefixed by its
name, with every reference rewritten to point there, and loses its ``$schema``
and ``$id``, which would change what those references resolve against.

Examples
--------
>>> schema = sources_output(local=False)
>>> schema["$schema"], schema["type"]
('https://json-schema.org/draft/2020-12/schema', 'object')
>>> "has_key" in schema["$defs"]["Source"]["properties"]
False
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.binding import DEFAULT_PROFILE, VintagePolicy
from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.core.schema import SCHEMA_DIALECT, input_schema, output_schema
from pyeconomics.core.spec import CostClass
from pyeconomics.surfaces import registry_schema
from pyeconomics.surfaces.listing import MAX_SEARCH_RESULTS

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from pyeconomics.core.model import Model

__all__ = [
    "DEFAULT_SEARCH_LIMIT",
    "describe_input",
    "describe_output",
    "result_output",
    "run_input",
    "run_output",
    "search_input",
    "search_output",
    "series_input",
    "series_output",
    "sources_input",
    "sources_output",
    "tool_input",
    "with_notice",
]

#: How many entries a search returns when no limit is given.
DEFAULT_SEARCH_LIMIT: Final = 20

_DEFS: Final = "#/$defs/"
_TEXT: Final = {"type": "string"}
_TEXTS: Final = {"type": "array", "items": _TEXT}
_TEXT_OR_NULL: Final = {"type": ["string", "null"]}
_DATE: Final = {"type": "string", "format": "date"}
_SHA256: Final = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_NO_ARGUMENTS: Final = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}


def _record(
    properties: Mapping[str, Any],
    *,
    optional: Iterable[str] = (),
    closed: bool = True,
) -> dict[str, Any]:
    """Return an object schema that requires every property but ``optional``."""
    left_out = set(optional)
    schema: dict[str, Any] = {
        "type": "object",
        "properties": dict(properties),
        "required": [name for name in properties if name not in left_out],
    }
    if closed:
        schema["additionalProperties"] = False
    return schema


def _ref(name: str) -> dict[str, str]:
    return {"$ref": _DEFS + name}


def _rewrite(value: Any, names: Mapping[str, str]) -> Any:  # noqa: ANN401 - JSON values
    """Point each ``#/$defs/<Name>`` reference, and discriminator mapping, anew."""
    if isinstance(value, list):
        return [_rewrite(item, names) for item in value]
    if not isinstance(value, dict):
        return value
    rewritten: dict[str, Any] = {}
    for key, item in value.items():
        if key == "$ref" and isinstance(item, str) and item.startswith(_DEFS):
            rewritten[key] = _DEFS + names[item.removeprefix(_DEFS)]
        elif key == "discriminator" and isinstance(item, dict):
            mapping = {
                tag: _DEFS + names[target.removeprefix(_DEFS)]
                if isinstance(target, str) and target.startswith(_DEFS)
                else target
                for tag, target in item.get("mapping", {}).items()
            }
            rewritten[key] = {**item, "mapping": mapping} if mapping else dict(item)
        else:
            rewritten[key] = _rewrite(item, names)
    return rewritten


def _embed(
    document: Mapping[str, Any], name: str, into: dict[str, Any]
) -> dict[str, str]:
    """Put a schema document in ``into`` under ``name``, its definitions below it."""
    body = copy.deepcopy(dict(document))
    body.pop("$schema", None)
    body.pop("$id", None)
    definitions: dict[str, Any] = body.pop("$defs", {})
    names = {definition: f"{name}.{definition}" for definition in definitions}
    into[name] = _rewrite(body, names)
    for definition, schema in definitions.items():
        into[names[definition]] = _rewrite(schema, names)
    return _ref(name)


def _references(value: Any) -> set[str]:  # noqa: ANN401 - JSON values
    """Return the definitions a schema refers to directly."""
    if isinstance(value, list):
        return set().union(*(_references(item) for item in value)) if value else set()
    if not isinstance(value, dict):
        return set()
    found: set[str] = set()
    for key, item in value.items():
        if key == "$ref" and isinstance(item, str) and item.startswith(_DEFS):
            found.add(item.removeprefix(_DEFS))
        else:
            found |= _references(item)
    return found


def _shared(roots: Iterable[str], into: dict[str, Any]) -> None:
    """Copy ``registry.json``'s definitions, and those they refer to, into ``into``."""
    definitions: Mapping[str, Any] = registry_schema.REGISTRY_SCHEMA["$defs"]
    waiting = list(roots)
    while waiting:
        name = waiting.pop()
        if name in into:
            continue
        into[name] = copy.deepcopy(definitions[name])
        waiting += sorted(_references(definitions[name]) - set(into))


def _document(
    title: str, description: str, body: Mapping[str, Any], defs: Mapping[str, Any]
) -> dict[str, Any]:
    """Return a schema document: the dialect, a title, the body and its defs."""
    schema: dict[str, Any] = {
        "$schema": SCHEMA_DIALECT,
        "title": title,
        "description": description,
        **body,
    }
    if defs:
        schema["$defs"] = dict(sorted(defs.items()))
    return schema


# --- inputs ------------------------------------------------------------------------


def tool_input(model: Model[Any, Any]) -> dict[str, Any]:
    """Return a headline tool's input schema: the model's own, an object at its root."""
    schema = input_schema(model)
    if "type" not in schema:
        # A family of calculations is oneOf its members, each an object; earlier
        # protocol revisions require an object at the root.
        schema["type"] = "object"
    return schema


def search_input(domains: Iterable[str]) -> dict[str, Any]:
    """Return ``search_models``' input schema."""
    body = _record(
        {
            "query": {
                "type": "string",
                "minLength": 1,
                "maxLength": 256,
                "description": "Words to look for in each model's id, title, tags, "
                "domain and summary. Without it, every model of the domain (or "
                "every model) is listed, sorted by id.",
            },
            "domain": {
                "enum": sorted(domains),
                "description": "Only the models of this domain.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": MAX_SEARCH_RESULTS,
                "default": DEFAULT_SEARCH_LIMIT,
                "description": "The most entries a search returns, best first.",
            },
        },
        optional=("query", "domain", "limit"),
    )
    return _document("search_models: inputs", "A search of the models.", body, {})


def describe_input() -> dict[str, Any]:
    """Return ``describe_model``'s input schema."""
    body = _record(
        {
            "model_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "description": "A model id, or an alias of one, as search_models "
                "lists them.",
            }
        }
    )
    return _document("describe_model: inputs", "The model to describe.", body, {})


def run_input() -> dict[str, Any]:
    """Return ``run_model``'s input schema."""
    body = _record(
        {
            "model_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 128,
                "description": "A model id, or an alias of one.",
            },
            "inputs": {
                "type": "object",
                "description": "The model's inputs, as its input schema "
                "(describe_model) gives them. With a bind, each one given replaces "
                "the value the data would supply.",
            },
            "as_of": {
                **_DATE,
                "description": "Bind the model's data as published on this date "
                "(YYYY-MM-DD).",
            },
            "vintage": {
                "enum": [policy.value for policy in VintagePolicy],
                "description": "The vintage policy of every binding, in place of "
                "their own.",
            },
            "profile": {
                "type": "string",
                "minLength": 1,
                "maxLength": 64,
                "description": "The named set of bindings to read; "
                f"{DEFAULT_PROFILE!r} binds the latest data.",
            },
            "concepts": {
                "type": "object",
                "additionalProperties": {"type": "string"},
                "description": "Field names mapped to catalog concept ids that "
                "replace their bindings' concepts.",
            },
            "parameters": {
                "type": "object",
                "description": "Values of the bound concepts' parameters.",
            },
        },
        optional=("inputs", "as_of", "vintage", "profile", "concepts", "parameters"),
    )
    description = (
        "A run of any model. Any of as_of, vintage, profile, concepts or "
        "parameters binds the model's data first; without them the model runs on "
        "its inputs alone."
    )
    return _document("run_model: inputs", description, body, {})


def series_input() -> dict[str, Any]:
    """Return ``get_series``' input schema."""
    body = _record(
        {
            "target": {
                "type": "string",
                "minLength": 1,
                "maxLength": 256,
                "description": "A catalog concept id (such as "
                "us.unemployment.rate) or provider:series (such as bls:LNS14000000).",
            },
            "start": {**_DATE, "description": "The first observation date wanted."},
            "end": {**_DATE, "description": "The last observation date wanted."},
            "as_of": {
                **_DATE,
                "description": "Read the data as published on this date.",
            },
            "vintage": {
                "type": "string",
                "description": "A vintage label: latest, first_release, all or "
                "as_of:YYYY-MM-DD.",
            },
            "provider": {
                "type": "string",
                "description": "For a concept, only this provider's candidates.",
            },
        },
        optional=("start", "end", "as_of", "vintage", "provider"),
    )
    return _document("get_series: inputs", "The series to read.", body, {})


def sources_input() -> dict[str, Any]:
    """Return ``list_sources``' input schema: no arguments."""
    return _document("list_sources: inputs", "No arguments.", _NO_ARGUMENTS, {})


# --- outputs -----------------------------------------------------------------------


def _envelope(
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    model_id: dict[str, Any],
    model_version: dict[str, Any],
) -> dict[str, Any]:
    return _record(
        {
            "inputs": inputs,
            "manifest": _ref("manifest"),
            "model_id": model_id,
            "model_version": model_version,
            "outputs": outputs,
            "warnings": {"type": "array", "items": _ref("warning")},
        }
    )


_RESULT_DESCRIPTION: Final = (
    "The run's result as canonical JSON (RFC 8785): the validated inputs and "
    "outputs, the warnings and the manifest."
)


def result_output(model: Model[Any, Any]) -> dict[str, Any]:
    """Return a headline tool's output schema: the model's result envelope."""
    defs: dict[str, Any] = {}
    inputs = _embed(input_schema(model), "input", defs)
    outputs = _embed(output_schema(model), "output", defs)
    _shared(("manifest", "warning"), defs)
    body = _envelope(
        inputs, outputs, {"const": model.id}, {"const": model.spec.version}
    )
    return _document(f"{model.spec.title}: result", _RESULT_DESCRIPTION, body, defs)


def run_output() -> dict[str, Any]:
    """Return ``run_model``'s output schema: the result envelope of any model."""
    defs: dict[str, Any] = {}
    _shared(("manifest", "warning"), defs)
    body = _envelope(
        {"type": "object"},
        {"type": "object"},
        {"type": "string"},
        {"type": "integer", "minimum": 1},
    )
    return _document("run_model: result", _RESULT_DESCRIPTION, body, defs)


def with_notice(schema: Mapping[str, Any]) -> dict[str, Any]:
    """Return a run's hosted output schema: its result, or a large result's notice.

    A hosted run whose canonical result is larger than the server's limit
    returns the notice instead of the data: the model, the result's size and
    hash, its summary, and the REST API's download of the same result.
    """
    head = {key: schema[key] for key in ("$schema", "title", "description")}
    body = {key: value for key, value in schema.items() if key not in head}
    defs: dict[str, Any] = dict(body.pop("$defs", {}))
    defs["result"] = body
    model_id = body["properties"]["model_id"]
    model_version = body["properties"]["model_version"]
    download = _record(
        {
            "method": {"const": "GET"},
            "path": {
                "type": "string",
                "description": "The run's GET form on this server's REST API, "
                "which answers the same result; ?format= gives other formats.",
            },
        }
    )
    defs["notice"] = _record(
        {
            "download": {"anyOf": [download, {"type": "null"}]},
            "model_id": model_id,
            "model_version": model_version,
            "result_bytes": {"type": "integer", "minimum": 0},
            "result_sha256": _SHA256,
            "summary": _TEXT,
        }
    )
    return _document(
        str(head["title"]),
        f"{head['description']} A result larger than the server's limit is "
        "replaced by a notice: its summary, size and hash, and the REST "
        "download that answers it.",
        {"type": "object", "anyOf": [_ref("result"), _ref("notice")]},
        defs,
    )


def search_output() -> dict[str, Any]:
    """Return ``search_models``' output schema: the matching model entries."""
    entry = _record(
        {
            "bound": {"type": "boolean"},
            "cost": {"enum": [*(c.value for c in CostClass), None]},
            "domain": _TEXT,
            "extra": _TEXT_OR_NULL,
            "id": _TEXT,
            "summary": _TEXT,
            "tags": _TEXTS,
            "title": _TEXT,
            "version": {"type": "integer", "minimum": 1},
        }
    )
    body = _record({"models": {"type": "array", "items": _ref("ModelEntry")}})
    return _document(
        "search_models: result",
        "The models found, best first, or every model listed, sorted by id.",
        body,
        {"ModelEntry": entry},
    )


def describe_output() -> dict[str, Any]:
    """Return ``describe_model``'s output schema: ``registry.describe``'s document."""
    defs: dict[str, Any] = {}
    _shared(("model",), defs)
    body = defs.pop("model")
    for dropped in ("example_result", "example_figure"):
        body["properties"].pop(dropped)
        body["required"].remove(dropped)
    used = _references(body)
    while unused := set(defs) - used - set().union(*map(_references, defs.values())):
        for name in unused:
            del defs[name]
    return _document(
        "describe_model: result",
        "A model's specification, its input and output schemas and its card.",
        body,
        defs,
    )


def series_output() -> dict[str, Any]:
    """Return ``get_series``' output schema: the series document."""
    body = _record(
        {
            "attributions": _TEXTS,
            "concept": _TEXT_OR_NULL,
            "frame": {"type": "object"},
            "skipped": {"type": "array", "items": {"type": "object"}},
            "sources": {"type": "array", "items": {"type": "object"}},
        }
    )
    return _document(
        "get_series: result",
        "The frame the target resolved to, with its source records, the "
        "candidates passed over, and the attributions it must be shown with.",
        body,
        {},
    )


def sources_output(*, local: bool) -> dict[str, Any]:
    """Return ``list_sources``' output schema; ``has_key`` only in local mode."""
    properties: dict[str, Any] = {
        "attribution": _TEXT,
        "hosted_allowed": {"type": "boolean"},
        "id": _TEXT,
        "licence": {"enum": [licence.value for licence in LicenceClass]},
        "llm_permitted": {"type": "boolean"},
        "llm_use": {"enum": [use.value for use in LlmUse]},
        "name": _TEXT,
        "notice": _TEXT_OR_NULL,
        "terms_url": {"type": "string", "format": "uri"},
    }
    if local:
        properties["has_key"] = {"type": ["boolean", "null"]}
    body = _record({"sources": {"type": "array", "items": _ref("Source")}})
    return _document(
        "list_sources: result",
        "Every data provider with its licence class, its llm_use class, whether "
        "this server's policy lets its data reach the assistant, its attribution "
        "and its terms page.",
        body,
        {"Source": _record(dict(sorted(properties.items())))},
    )
