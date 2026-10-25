# src/pyeconomics/server/openapi.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The REST API's OpenAPI 3.1 document, with each model's own schemas.

FastAPI builds the paths and operations from the app's routes; each route
supplies its parameters, request body and responses (``openapi_extra``) as
references into ``components.schemas``, which :func:`components` fills
afterwards. They are added after FastAPI's own pass because that pass drops
every ``null`` from what it validates, and a model's schemas hold meaningful
nulls (a ``null`` default, an optional field).

Each model contributes the schemas :mod:`pyeconomics.core.schema` builds,
unchanged but for where they live (:func:`model_components`):

- ``<id>.input``: the run's request body, the model's input schema;
- ``<id>.output``: the model's output schema;
- ``<id>.result``: the run's response, a result whose ``inputs`` and
  ``outputs`` are those two;
- ``<id>.input.<Name>`` and ``<id>.output.<Name>``: the documents' ``$defs``,
  each ``#/$defs/<Name>`` reference rewritten to point here, and the
  documents' ``$schema`` and ``$id`` dropped, since an embedded ``$id`` would
  change what those references resolve against.

The shared shapes (a problem, a manifest, a listing entry, a model's
description, a source) come from the same definitions ``registry.json``'s schema
uses where it has them. :func:`openapi_document` returns the document of a local
app with no workers, which the mode does not change; ``pyeconomics registry
export`` writes it as ``openapi.json`` (:func:`write_openapi`), canonical JSON
with no clock, host or path in it.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from pyeconomics import __version__
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.schema import input_schema, output_schema
from pyeconomics.core.spec import CostClass
from pyeconomics.server import formats
from pyeconomics.server.settings import MODES
from pyeconomics.surfaces import registry_schema
from pyeconomics.surfaces.budgets import GET_INPUTS_LIMIT
from pyeconomics.surfaces.problems import MAX_FIELD_ERRORS

if TYPE_CHECKING:
    import os
    from collections.abc import Iterable, Mapping

    from fastapi import FastAPI

    from pyeconomics.core.model import Model

__all__ = [
    "OPENAPI_VERSION",
    "PROBLEM_MEDIA_TYPE",
    "REF",
    "TAGS",
    "components",
    "describe_operation",
    "document",
    "list_operation",
    "model_components",
    "openapi_document",
    "operation_id",
    "ref",
    "run_operation",
    "series_operation",
    "service_operation",
    "sources_operation",
    "write_openapi",
]

#: The OpenAPI version of the document.
OPENAPI_VERSION: Final = "3.1.0"
#: Where every schema lives.
REF: Final = "#/components/schemas/"
#: A problem's media type (RFC 9457).
PROBLEM_MEDIA_TYPE: Final = "application/problem+json"
#: The tags that group the generic operations; each domain tags its runs.
TAGS: Final = (
    {"name": "models", "description": "List, search and describe the models."},
    {"name": "data", "description": "Series from the catalog and its providers."},
    {"name": "service", "description": "Health and version."},
)

_DEFS: Final = "#/$defs/"
_TEXT: Final = {"type": "string"}
_TEXTS: Final = {"type": "array", "items": _TEXT}
_TEXT_OR_NULL: Final = {"type": ["string", "null"]}
#: registry_schema's definitions this document shares, by the name used here.
_SHARED: Final = {
    "alias": "Alias",
    "binding": "Binding",
    "changelog_entry": "ChangelogEntry",
    "chart": "Chart",
    "example": "Example",
    "invariant": "Invariant",
    "manifest": "Manifest",
    "reference": "Reference",
    "warning": "ResultWarning",
}


def ref(name: str) -> dict[str, str]:
    """Return a reference to a schema in ``components.schemas``."""
    return {"$ref": REF + name}


def _record(properties: dict[str, Any], *, closed: bool = True) -> dict[str, Any]:
    schema: dict[str, Any] = {
        "type": "object",
        "required": list(properties),
        "properties": properties,
    }
    if closed:
        schema["additionalProperties"] = False
    return schema


def _rewrite(value: Any, names: Mapping[str, str]) -> Any:  # noqa: ANN401 - JSON values
    """Point each ``#/$defs/<Name>`` reference, and discriminator mapping, here."""
    if isinstance(value, list):
        return [_rewrite(item, names) for item in value]
    if not isinstance(value, dict):
        return value
    rewritten: dict[str, Any] = {}
    for key, item in value.items():
        if key == "$ref" and isinstance(item, str) and item.startswith(_DEFS):
            rewritten[key] = REF + names[item.removeprefix(_DEFS)]
        elif key == "discriminator" and isinstance(item, dict):
            mapping = {
                tag: REF + names[target.removeprefix(_DEFS)]
                if isinstance(target, str) and target.startswith(_DEFS)
                else target
                for tag, target in item.get("mapping", {}).items()
            }
            rewritten[key] = {**item, "mapping": mapping} if mapping else dict(item)
        else:
            rewritten[key] = _rewrite(item, names)
    return rewritten


def _embedded(document: dict[str, Any], name: str) -> dict[str, dict[str, Any]]:
    """Return a schema document as components: itself under ``name``, its defs below."""
    body = copy.deepcopy(document)
    body.pop("$schema", None)
    body.pop("$id", None)
    definitions: dict[str, Any] = body.pop("$defs", {})
    names = {definition: f"{name}.{definition}" for definition in definitions}
    found = {name: _rewrite(body, names)}
    for definition, schema in definitions.items():
        found[names[definition]] = _rewrite(schema, names)
    return found


def model_components(model: Model[Any, Any]) -> dict[str, dict[str, Any]]:
    """Return a model's schemas as components: input, output and result."""
    found = {
        **_embedded(input_schema(model), f"{model.id}.input"),
        **_embedded(output_schema(model), f"{model.id}.output"),
    }
    found[f"{model.id}.result"] = {
        "title": f"{model.spec.title}: result",
        "description": "The run's result as canonical JSON (RFC 8785): the "
        "validated inputs and outputs, the warnings and the manifest.",
        **_record(
            {
                "inputs": ref(f"{model.id}.input"),
                "manifest": ref("Manifest"),
                "model_id": {"const": model.id},
                "model_version": {"const": model.version},
                "outputs": ref(f"{model.id}.output"),
                "warnings": {"type": "array", "items": ref("ResultWarning")},
            }
        ),
    }
    return found


def _shared() -> dict[str, dict[str, Any]]:
    """Return registry_schema's shared definitions, pointed at the components."""
    definitions = registry_schema.REGISTRY_SCHEMA["$defs"]
    names = {**_SHARED, "model": "ModelDescription"}
    found = {name: _rewrite(definitions[key], names) for key, name in _SHARED.items()}
    description = copy.deepcopy(definitions["model"])
    for dropped in ("example_result", "example_figure"):
        description["properties"].pop(dropped)
        description["required"].remove(dropped)
    found["ModelDescription"] = _rewrite(description, names)
    return found


def components(models: Iterable[Model[Any, Any]]) -> dict[str, dict[str, Any]]:
    """Return every schema the operations refer to, sorted by name."""
    field_error = _record(
        {
            "loc": {"type": "array", "items": {"type": ["string", "integer"]}},
            "msg": _TEXT,
            "type": _TEXT,
        }
    )
    found: dict[str, dict[str, Any]] = {
        **_shared(),
        "FieldError": {
            "description": "One field's validation error, without its value.",
            **field_error,
        },
        "Problem": {
            "description": "An RFC 9457 problem. The type is "
            "https://pyeconomics.dev/problems/<slug>; the extension members "
            "appear only when they apply.",
            "type": "object",
            "required": ["type", "title", "status", "detail"],
            "properties": {
                "type": {"type": "string", "format": "uri"},
                "title": _TEXT,
                "status": {"type": "integer"},
                "detail": _TEXT,
                "errors": {
                    "type": "array",
                    "items": ref("FieldError"),
                    "maxItems": MAX_FIELD_ERRORS,
                },
                "licence": _TEXT,
                "terms": {"type": "string", "format": "uri"},
                "retry_after": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "ModelEntry": {
            "description": "A model as a listing shows it.",
            **_record(
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
            ),
        },
        "SeriesDocument": {
            "description": "The frame a series target resolved to, with its "
            "source records and the attributions it must be shown with.",
            **_record(
                {
                    "attributions": _TEXTS,
                    "concept": _TEXT_OR_NULL,
                    "frame": {"type": "object"},
                    "skipped": {"type": "array", "items": {"type": "object"}},
                    "sources": {"type": "array", "items": {"type": "object"}},
                }
            ),
        },
        "Source": {
            "description": "A data provider, from its metadata.",
            **_record(
                {
                    "attribution": _TEXT,
                    "automated_collection": {"type": "boolean"},
                    "cache": _TEXT,
                    "capabilities": _TEXTS,
                    "disabled": {"type": "boolean"},
                    "extra": _TEXT_OR_NULL,
                    "homepage": _TEXT,
                    "hosted_allowed": {"type": "boolean"},
                    "id": _TEXT,
                    "key_configured": {"type": ["boolean", "null"]},
                    "key_required": {"type": "boolean"},
                    "key_variable": _TEXT_OR_NULL,
                    "licence": _TEXT,
                    "llm_use": _TEXT,
                    "name": _TEXT,
                    "never_paid": {"type": "boolean"},
                    "notice": _TEXT_OR_NULL,
                    "platforms": _TEXTS,
                    "terms_checked": {"type": "string", "format": "date"},
                    "terms_url": {"type": "string", "format": "uri"},
                }
            ),
        },
        "Health": _record({"status": {"const": "ok"}}),
        "Version": _record(
            {
                "git_sha": _TEXT,
                "mode": {"enum": list(MODES)},
                "pyeconomics": _TEXT,
            }
        ),
    }
    for model in models:
        found.update(model_components(model))
    return dict(sorted(found.items()))


# --- operations -------------------------------------------------------------------


def _query(name: str, description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {"name": name, "in": "query", "description": description, "schema": schema}


def _path(name: str, description: str) -> dict[str, Any]:
    return {
        "name": name,
        "in": "path",
        "required": True,
        "description": description,
        "schema": _TEXT,
    }


def _problems() -> dict[str, Any]:
    problem = {
        "description": "A problem (RFC 9457) from the error table; never cached.",
        "headers": {
            "Cache-Control": _header("no-store."),
            "Retry-After": _header(
                "Seconds to wait, on a rate limit (429 or 503) or a busy server."
            ),
        },
        "content": {PROBLEM_MEDIA_TYPE: {"schema": ref("Problem")}},
    }
    return {"4XX": problem, "5XX": copy.deepcopy(problem)}


def _header(description: str) -> dict[str, Any]:
    return {"description": description, "schema": _TEXT}


def _json(description: str, schema: dict[str, Any]) -> dict[str, Any]:
    return {
        "200": {
            "description": description,
            "content": {"application/json": {"schema": schema}},
        },
        **_problems(),
    }


def _downloads(json_schema: dict[str, Any], kinds: tuple[str, ...]) -> dict[str, Any]:
    content: dict[str, Any] = {"application/json": {"schema": json_schema}}
    for kind in kinds:
        media = formats.MEDIA_TYPES[kind].partition(";")[0]
        content[media] = {"schema": _TEXT} if kind == "csv" else {}
    return content


def operation_id(model: Model[Any, Any], method: str) -> str:
    """Return a run operation's id: ``run_<domain>_<name>``, ``..._get`` for GET."""
    stem = "run_" + model.id.replace(".", "_")
    return stem if method == "POST" else f"{stem}_get"


def _format_parameter(kinds: tuple[str, ...]) -> dict[str, Any]:
    return _query(
        "format",
        "json (the default), or a download: "
        + ", ".join(kind for kind in kinds if kind != "json")
        + ". Parquet and Arrow need pyarrow.",
        {"enum": list(kinds), "default": formats.DEFAULT_FORMAT},
    )


def _bind_parameters() -> list[dict[str, Any]]:
    assignment = {"type": "array", "items": _TEXT}
    return [
        _query(
            "as_of",
            "Bind the model's data as published on this date (YYYY-MM-DD).",
            {"type": "string", "format": "date"},
        ),
        _query(
            "vintage",
            "Bind with this vintage policy for every binding.",
            {"enum": ["real_time", "latest"]},
        ),
        _query("profile", "Bind this named set of bindings.", _TEXT),
        {
            **_query(
                "concept", "FIELD=ID: bind a field to another concept.", assignment
            ),
            "explode": True,
        },
        {
            **_query("param", "NAME=VALUE: a concept parameter.", assignment),
            "explode": True,
        },
    ]


def run_operation(model: Model[Any, Any], method: str) -> dict[str, Any]:
    """Return a model's run operation, POST or GET, as ``openapi_extra``.

    The GET form is cacheable: it answers an entity tag and ``Cache-Control``,
    and ``304`` when ``If-None-Match`` names the tag. The POST form is
    ``no-store``.
    """
    parameters = [_format_parameter(formats.RUN_FORMATS), *_bind_parameters()]
    answered: dict[str, Any] = {
        "description": "The result's canonical JSON, or a download of it.",
        "headers": {
            "Cache-Control": _header(
                "no-store for a POST run, or a run whose data may not be "
                "stored; public with a max-age otherwise."
            ),
        },
        "content": _downloads(ref(f"{model.id}.result"), formats.RUN_FORMATS[1:]),
    }
    operation: dict[str, Any] = {
        "parameters": parameters,
        "responses": {"200": answered, **_problems()},
    }
    if method == "POST":
        operation["requestBody"] = {
            "description": "The model's inputs as JSON; empty for a bound run that "
            "takes every input from its data.",
            "required": False,
            "content": {"application/json": {"schema": ref(f"{model.id}.input")}},
        }
    else:
        parameters.insert(
            0,
            _query(
                "inputs",
                "The inputs' canonical JSON in base64url without padding (RFC "
                "4648 section 5); the bytes equal the POST form's.",
                {
                    "type": "string",
                    "pattern": "^[A-Za-z0-9_-]*$",
                    "maxLength": GET_INPUTS_LIMIT,
                },
            ),
        )
        parameters.append(
            {
                "name": "If-None-Match",
                "in": "header",
                "description": "Entity tags already held; a match answers 304.",
                "schema": _TEXT,
            }
        )
        answered["headers"]["ETag"] = _header(
            'The weak entity tag W/"<result_sha256>".'
        )
        operation["responses"]["304"] = {
            "description": "Not modified: the entity tag in If-None-Match matched.",
            "headers": {
                "ETag": _header('The weak entity tag W/"<result_sha256>".'),
                "Cache-Control": _header("public, with a max-age."),
            },
        }
    return operation


def list_operation(domains: Iterable[str]) -> dict[str, Any]:
    """Return ``GET /v1/models`` as ``openapi_extra``."""
    return {
        "parameters": [
            _query("q", "Words to search for; ranks the matches.", _TEXT),
            _query("domain", "Only this domain's models.", {"enum": list(domains)}),
            _query(
                "limit",
                "With q, at most this many models.",
                {"type": "integer", "minimum": 1, "maximum": 100, "default": 20},
            ),
        ],
        "responses": _json(
            "The models, sorted by id, or the matches, best first.",
            {"type": "array", "items": ref("ModelEntry")},
        ),
    }


def describe_operation() -> dict[str, Any]:
    """Return ``GET /v1/models/{model_id}`` as ``openapi_extra``."""
    return {
        "parameters": [_path("model_id", "The model's id.")],
        "responses": _json(
            "The model's description: registry.describe's canonical JSON.",
            ref("ModelDescription"),
        ),
    }


def series_operation() -> dict[str, Any]:
    """Return ``GET /v1/series/{target}`` as ``openapi_extra``."""
    date = {"type": "string", "format": "date"}
    return {
        "parameters": [
            _path(
                "target",
                "A concept id (us.unemployment.rate) or provider:series "
                "(fred:UNRATE); never a URL.",
            ),
            _query("start", "The first observation date.", date),
            _query("end", "The last observation date.", date),
            _query("as_of", "Read the data as published on this date.", date),
            _query("vintage", "A vintage label, in place of as_of.", _TEXT),
            _query(
                "provider", "For a concept, only this provider's candidates.", _TEXT
            ),
            _format_parameter(formats.SERIES_FORMATS),
        ],
        "responses": {
            "200": {
                "description": "The frame with its sources and attributions, or a "
                "download of it.",
                "content": _downloads(
                    ref("SeriesDocument"), formats.SERIES_FORMATS[1:]
                ),
            },
            **_problems(),
        },
    }


def sources_operation() -> dict[str, Any]:
    """Return ``GET /v1/sources`` as ``openapi_extra``."""
    return {
        "responses": _json(
            "Every data provider, from its metadata; no request is made.",
            {"type": "array", "items": ref("Source")},
        )
    }


def service_operation(schema: str) -> dict[str, Any]:
    """Return ``GET /healthz`` or ``GET /version`` as ``openapi_extra``."""
    return {"responses": _json("The answer.", ref(schema))}


# --- the document -----------------------------------------------------------------


def document(app: FastAPI, models: Iterable[Model[Any, Any]]) -> dict[str, Any]:
    """Return an app's OpenAPI document, its components added."""
    from fastapi.openapi.utils import get_openapi  # noqa: PLC0415

    built = get_openapi(
        title="pyeconomics",
        version=__version__,
        openapi_version=OPENAPI_VERSION,
        summary="Open economics and finance models and data.",
        description="Every model's run, with its own input and output schemas, "
        "returns the bytes of the Python API's Result.to_json(); every error is "
        "an RFC 9457 problem from one error table.",
        routes=app.routes,
        tags=[dict(tag) for tag in TAGS],
        license_info={"name": "Apache-2.0", "identifier": "Apache-2.0"},
    )
    built.setdefault("components", {})["schemas"] = components(models)
    return built


def openapi_document() -> dict[str, Any]:
    """Return the OpenAPI document of every installed model's API."""
    from pyeconomics.server.app import create_app  # noqa: PLC0415
    from pyeconomics.server.settings import ServerSettings  # noqa: PLC0415

    return create_app(mode="local", settings=ServerSettings(workers=0)).openapi()


def write_openapi(path: str | os.PathLike[str]) -> None:
    """Write :func:`openapi_document` to ``path`` as canonical JSON bytes."""
    Path(path).write_bytes(canonical_json(openapi_document()))
