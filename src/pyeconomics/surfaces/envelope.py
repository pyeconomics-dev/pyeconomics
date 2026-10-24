# src/pyeconomics/surfaces/envelope.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The result envelope: canonical bytes, an entity tag and a summary (ADR-0012 3).

Every surface returns :func:`canonical_bytes`, the UTF-8 encoding of
``Result.to_json()``, unchanged: the REST API as its body, the command line
followed by one newline, MCP as a tool's text content. A presentation goes beside
those bytes, never in their place; :func:`summary` is the one-paragraph text every
surface shares for it.

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

from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.provenance import LicenceClass

if TYPE_CHECKING:
    from pyeconomics.core.results import Result

__all__ = ["MAX_SUMMARY_OUTPUTS", "canonical_bytes", "etag", "summary"]

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
    outputs = result.outputs.model_dump(mode="json")
    named = [
        f"{name} = {_value(value)}"
        for name, value in list(outputs.items())[:MAX_SUMMARY_OUTPUTS]
    ]
    more = len(outputs) - len(named)
    if more:
        named.append(f"and {more} more")
    text = (
        f"{result.model.spec.title} ({result.model_id}, version "
        f"{result.model_version}): {', '.join(named)}."
    )
    if result.warnings:
        codes = ", ".join(dict.fromkeys(w.code for w in result.warnings))
        text += f" Warnings: {codes}."
    providers = sorted(
        {
            record.provider
            for record in result.manifest.data_sources
            if record.licence is not LicenceClass.USER_SUPPLIED
        }
    )
    if providers:
        text += f" Data from {', '.join(providers)}."
    return text
