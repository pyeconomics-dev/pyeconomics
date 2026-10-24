# src/pyeconomics/surfaces/registry_schema.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The JSON Schema (2020-12) of ``registry.json`` (ADR-0012 decision 8).

:data:`REGISTRY_SCHEMA` is the contract between
:mod:`~pyeconomics.surfaces.registry_export` and what reads its document: the
Phase 5 web app, generated clients and anyone mirroring the catalog. It lives in
a Python module, not a ``.json`` file, because the wheel holds only ``.py`` files
(``scripts/checks/dist_contents.py``).

Every key an entry carries is required and no other is allowed, so a key added
to :func:`~pyeconomics.core.describe.describe` fails validation until the schema
names it, and the snapshot test of this schema then asks for a reviewed update.
A model's own input and output schemas are carried as objects: each is a
2020-12 document in its own right, with its own ``$id``
(:mod:`pyeconomics.core.schema`), and the per-model snapshots guard them.

Examples
--------
>>> from pyeconomics.surfaces.registry_schema import REGISTRY_SCHEMA, REGISTRY_SCHEMA_ID
>>> REGISTRY_SCHEMA["$id"] == REGISTRY_SCHEMA_ID
True
>>> REGISTRY_SCHEMA["required"]
['format', 'pyeconomics', 'models']
"""

from __future__ import annotations

from typing import Any, Final

from pyeconomics.core.binding import AsOf, VintagePolicy
from pyeconomics.core.manifest import MANIFEST_SCHEMA_VERSION
from pyeconomics.core.schema import SCHEMA_DIALECT
from pyeconomics.core.spec import MODEL_ID, ChartKind, CostClass, Evidence

__all__ = ["REGISTRY_FORMAT", "REGISTRY_SCHEMA", "REGISTRY_SCHEMA_ID"]

#: The version of the document's shape; it changes only with an incompatible
#: change, and then so does :data:`REGISTRY_SCHEMA_ID`.
REGISTRY_FORMAT: Final = 1

#: The stable ``$id`` of the schema of format 1.
REGISTRY_SCHEMA_ID: Final = "https://pyeconomics.dev/schemas/registry/1.json"

_TEXT: Final = {"type": "string"}
_TEXT_OR_NULL: Final = {"type": ["string", "null"]}
_TEXTS: Final = {"type": "array", "items": _TEXT}
_OBJECT: Final = {"type": "object"}
_COUNT: Final = {"type": "integer", "minimum": 1}
_SHA256: Final = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
_MODEL_ID: Final = {"type": "string", "pattern": f"^{MODEL_ID.pattern}$"}


def _record(properties: dict[str, Any]) -> dict[str, Any]:
    """Return a closed object schema whose properties are all required."""
    return {
        "type": "object",
        "required": list(properties),
        "properties": properties,
        "additionalProperties": False,
    }


def _values(enum: type[Any], *, nullable: bool = False) -> dict[str, Any]:
    values: list[str | None] = [member.value for member in enum]
    if nullable:
        values.append(None)
    return {"enum": values}


def _array(definition: str) -> dict[str, Any]:
    return {"type": "array", "items": {"$ref": f"#/$defs/{definition}"}}


_DEFINITIONS: Final = {
    "reference": _record(
        {
            "key": _TEXT,
            "citation": _TEXT,
            "doi": _TEXT_OR_NULL,
            "url": _TEXT_OR_NULL,
            "locator": _TEXT_OR_NULL,
            "isbn": _TEXT_OR_NULL,
        }
    ),
    "invariant": _record({"id": _TEXT, "statement": _TEXT}),
    "example": _record({"name": _TEXT, "note": _TEXT_OR_NULL, "inputs": _OBJECT}),
    "chart": _record(
        {
            "id": _TEXT,
            "title": _TEXT,
            "kind": _values(ChartKind),
            "x": _TEXT,
            "y": {**_TEXTS, "minItems": 1},
            "x_label": _TEXT_OR_NULL,
            "y_label": _TEXT_OR_NULL,
            "calculation": _TEXT_OR_NULL,
        }
    ),
    "alias": _record({"id": _MODEL_ID, "removed_in": _TEXT}),
    "binding": _record(
        {
            "field": _TEXT,
            "concept": _TEXT,
            "transform": _TEXT_OR_NULL,
            "as_of": _values(AsOf),
            "window": {"type": ["integer", "null"], "minimum": 1},
            "vintage": _values(VintagePolicy),
            "profile": _TEXT,
            "tenors": _TEXT_OR_NULL,
            "columns": _TEXTS,
        }
    ),
    "changelog_entry": _record({"version": _COUNT, "note": _TEXT}),
    "warning": _record({"code": _TEXT, "message": _TEXT}),
    "manifest": _record(
        {
            "schema_version": {"const": MANIFEST_SCHEMA_VERSION},
            "model_id": _MODEL_ID,
            "model_version": _COUNT,
            "package_version": _TEXT,
            "dependencies": {"type": "object", "additionalProperties": _TEXT},
            "seed": {"type": ["integer", "null"], "minimum": 0},
            "bit_generator": _TEXT_OR_NULL,
            "data_sources": {"type": "array", "items": _OBJECT},
            "inputs_sha256": _SHA256,
            "result_sha256": _SHA256,
        }
    ),
    "result": _record(
        {
            "model_id": _MODEL_ID,
            "model_version": _COUNT,
            "inputs": _OBJECT,
            "outputs": _OBJECT,
            "warnings": _array("warning"),
            "manifest": {"$ref": "#/$defs/manifest"},
        }
    ),
    "figure": {
        "type": "object",
        "description": "A Plotly figure as JSON, with no layout.template.",
        "required": ["data", "layout"],
        "properties": {
            "data": {"type": "array", "items": _OBJECT},
            "layout": {"type": "object", "not": {"required": ["template"]}},
        },
    },
    "model": _record(
        {
            "id": _MODEL_ID,
            "version": _COUNT,
            "domain": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
            "title": _TEXT,
            "summary": _TEXT,
            "tags": _TEXTS,
            "formula": {**_TEXTS, "description": "LaTeX, one line per item."},
            "assumptions": _TEXTS,
            "limitations": _TEXTS,
            "evidence": _values(Evidence, nullable=True),
            "cost": _values(CostClass, nullable=True),
            "references": _array("reference"),
            "invariants": _array("invariant"),
            "no_invariants_reason": _TEXT_OR_NULL,
            "examples": {**_array("example"), "minItems": 1},
            "charts": _array("chart"),
            "aliases": _array("alias"),
            "bindings": _array("binding"),
            "extra": _TEXT_OR_NULL,
            "changelog": _array("changelog_entry"),
            "input_schema": {
                **_OBJECT,
                "description": "The model's JSON Schema 2020-12 input document.",
            },
            "output_schema": {
                **_OBJECT,
                "description": "The model's JSON Schema 2020-12 output document.",
            },
            "card": {**_TEXT, "description": "The model card as MyST Markdown."},
            "example_result": {
                "description": "The first example's result; null without the "
                "model's extra.",
                "oneOf": [{"$ref": "#/$defs/result"}, {"type": "null"}],
            },
            "example_figure": {
                "description": "The first applicable chart of example_result; null "
                "without the plot extra or an applicable chart.",
                "oneOf": [{"$ref": "#/$defs/figure"}, {"type": "null"}],
            },
        }
    ),
}

#: The JSON Schema 2020-12 document ``registry.json`` validates against.
REGISTRY_SCHEMA: Final[dict[str, Any]] = {
    "$schema": SCHEMA_DIALECT,
    "$id": REGISTRY_SCHEMA_ID,
    "title": "pyeconomics model registry",
    "description": "Every registered model, as the surfaces and the web app are "
    "generated from it (ADR-0012 decision 8).",
    **_record(
        {
            "format": {"const": REGISTRY_FORMAT},
            "pyeconomics": {**_TEXT, "description": "The installed package version."},
            "models": {
                **_array("model"),
                "description": "One entry per registered model, sorted by id.",
            },
        }
    ),
    "$defs": _DEFINITIONS,
}
