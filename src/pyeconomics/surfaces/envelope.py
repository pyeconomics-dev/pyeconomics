# src/pyeconomics/surfaces/envelope.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The result envelope: canonical bytes, an entity tag and a summary (ADR-0012 3).

Every surface returns :func:`canonical_bytes`, the UTF-8 encoding of
``Result.to_json()``, unchanged: the REST API as its body, the command line
followed by one newline, MCP as a tool's text content. A presentation goes beside
those bytes, never in their place; :func:`summary` is the one-paragraph text every
surface shares for it, and :func:`summary_of` writes the same text from a result's
canonical document, for a surface that holds the bytes rather than the result (the
MCP server, whose hosted runs come back from a worker as bytes).

:func:`etag` is the HTTP entity tag of a cacheable run: weak, because two runs
with the same ``result_sha256`` (the same inputs, outputs and warnings) can still
differ in bytes by their data records and dependency versions (ADR-0012 decision
12; RFC 9110 section 8.8.1).

Examples
--------
>>> from pyeconomics.surfaces.envelope import etag
>>> callable(etag)
True
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LicenceClass

if TYPE_CHECKING:
    from pyeconomics.core.results import Result

__all__ = ["MAX_SUMMARY_OUTPUTS", "canonical_bytes", "etag", "summary", "summary_of"]

#: The most outputs a summary names; the rest are counted.
MAX_SUMMARY_OUTPUTS: Final = 12


def canonical_bytes(result: Result[Any, Any]) -> bytes:
    """Return the bytes every surface returns: ``result.to_json()`` in UTF-8."""
    return result.to_json().encode("utf-8")


def etag(result: Result[Any, Any]) -> str:
    """Return the weak entity tag of a result: ``W/"<result_sha256>"``."""
    return f'W/"{result.manifest.result_sha256}"'


def _value(value: object) -> str:
    """Describe one output value in a few words."""
    if value is None:
        return "undefined"
    if isinstance(value, list):
        if value and all(isinstance(item, list) for item in value):
            return f"{len(value)} rows"
        return f"{len(value)} values"
    if isinstance(value, dict):
        return f"{len(value)} entries"
    if isinstance(value, str):
        return value
    return canonical_json(value).decode("utf-8")


def summary(result: Result[Any, Any]) -> str:
    """Return a one-paragraph text summary of a result.

    It names the model, each output (an array by its length), the warning codes
    and the providers the data came from.

    Examples
    --------
    >>> from pyeconomics import run
    >>> inputs = {"calculation": "present_value", "rate": 0.05, "periods": 10,
    ...           "future_value": 100}
    >>> print(summary(run("foundations.time_value", inputs)))  # doctest: +ELLIPSIS
    Time value of money (foundations.time_value, version 2): calculation = present_value, present_value = 61.39...
    """  # noqa: E501 - doctest output lines cannot wrap
    document = {
        "model_id": result.model_id,
        "model_version": result.model_version,
        "outputs": result.outputs.model_dump(mode="json"),
        "warnings": [{"code": warning.code} for warning in result.warnings],
        "manifest": {
            "data_sources": [r.to_dict() for r in result.manifest.data_sources]
        },
    }
    return summary_of(document, result.model.spec.title)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def summary_of(document: Mapping[str, Any], title: str) -> str:
    """Return :func:`summary`'s text from a result's canonical document.

    ``document`` is ``json.loads`` of a result's canonical bytes, and ``title``
    its model's title. The outputs are named in the document's order, which is
    alphabetical in canonical JSON.

    Examples
    --------
    >>> summary_of(
    ...     {"model_id": "foundations.toy", "model_version": 1,
    ...      "outputs": {"value": 2.5}, "warnings": [], "manifest": {}},
    ...     "A toy",
    ... )
    'A toy (foundations.toy, version 1): value = 2.5.'
    """
    outputs = _mapping(document.get("outputs"))
    named = [
        f"{name} = {_value(value)}"
        for name, value in list(outputs.items())[:MAX_SUMMARY_OUTPUTS]
    ]
    more = len(outputs) - len(named)
    if more:
        named.append(f"and {more} more")
    text = (
        f"{title} ({document.get('model_id')}, version "
        f"{document.get('model_version')}): {', '.join(named)}."
    )
    warnings = [_mapping(w).get("code") for w in document.get("warnings") or ()]
    codes = ", ".join(dict.fromkeys(str(code) for code in warnings if code))
    if codes:
        text += f" Warnings: {codes}."
    records = _mapping(document.get("manifest")).get("data_sources") or ()
    providers = sorted(
        {
            str(_mapping(record).get("provider"))
            for record in records
            if _mapping(record).get("licence") != LicenceClass.USER_SUPPLIED.value
        }
    )
    if providers:
        text += f" Data from {', '.join(providers)}."
    return text
