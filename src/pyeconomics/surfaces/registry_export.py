# src/pyeconomics/surfaces/registry_export.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``registry.json``: the description every surface is generated from (ADR-0012 8).

:func:`registry_document` describes every registered model, sorted by id, and
:func:`write_registry` writes it as canonical JSON (RFC 8785). The document is
the one the Phase 5 web app builds its pages from, and it validates against
:data:`~pyeconomics.surfaces.registry_schema.REGISTRY_SCHEMA`:

- ``format``: :data:`REGISTRY_FORMAT`, which changes only with an incompatible
  change to the document's shape;
- ``pyeconomics``: the installed package version;
- ``models``: one entry per model, holding the keys of
  :func:`~pyeconomics.core.describe.describe` (the card's Markdown, the LaTeX
  formula, the citations, the input and output JSON Schemas, the examples and
  the bindings among them), plus ``example_result`` and ``example_figure``.

``example_result`` is the result of the model's first example, run through
:func:`~pyeconomics.surfaces.invoke.invoke` on the example's explicit inputs: it
never binds data, so the export reads no source and no key. It is ``null`` only
where the model's own extra is not installed (arch on CPython 3.15, say); a
model whose first example raises anything else fails the export, naming the
model. ``example_figure`` is the Plotly figure of that result's first applicable
chart, as JSON values, with ``layout.template`` removed (a default template is
tens of kilobytes, and every consumer applies its own); it is ``null`` without
the ``plot`` extra, without an applicable chart, or with ``figures=False``.

The document holds no clock, host name, user name, path or environment value:
two exports of the same installation are byte-identical wherever they are
written. A result's manifest does name the installed versions of pyeconomics and
its numerical libraries, which are facts about the installation.

Examples
--------
>>> from pyeconomics.surfaces.registry_export import REGISTRY_FORMAT
>>> REGISTRY_FORMAT
1
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pyeconomics import __version__, registry
from pyeconomics.core import plotting
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import MissingOptionalDependencyError, RegistryError
from pyeconomics.surfaces.invoke import invoke
from pyeconomics.surfaces.registry_schema import REGISTRY_FORMAT

if TYPE_CHECKING:
    import os

    from pyeconomics.core.model import Model
    from pyeconomics.core.results import Result

__all__ = ["REGISTRY_FORMAT", "registry_document", "write_registry"]


def _failure(model: Model[Any, Any], error: Exception) -> RegistryError:
    msg = (
        f"{model.id}: its first example failed, so the registry cannot be "
        f"exported: {type(error).__name__}: {error}"
    )
    return RegistryError(msg)


def _example_result(
    model: Model[Any, Any], inputs: dict[str, Any]
) -> Result[Any, Any] | None:
    """Run the first example through invoke; ``None`` if the model's extra is absent."""
    try:
        return invoke(model.id, inputs)
    except MissingOptionalDependencyError as error:
        if model.spec.extra is not None and error.extra == model.spec.extra:
            return None
        raise _failure(model, error) from error
    except Exception as error:
        raise _failure(model, error) from error


def _figure(result: Result[Any, Any]) -> dict[str, Any] | None:
    """Return the first applicable chart's figure as JSON values, without a template."""
    charts = plotting.applicable(result)
    if not charts:
        return None
    try:
        figure = plotting.figure(result, charts[0].id)
    except MissingOptionalDependencyError:
        return None
    # Plotly's own encoder writes dates, NaN and its array types as JSON; the
    # built-in engine keeps the text the same whether or not orjson is installed.
    values: dict[str, Any] = json.loads(figure.to_json(engine="json"))
    values.get("layout", {}).pop("template", None)
    return values


def _entry(model: Model[Any, Any], *, figures: bool) -> dict[str, Any]:
    try:
        # The card runs the first example too, outside the runner.
        entry = registry.describe(model.id)
    except Exception as error:
        raise _failure(model, error) from error
    result = _example_result(model, entry["examples"][0]["inputs"])
    entry["example_result"] = None if result is None else result.to_dict()
    entry["example_figure"] = (
        _figure(result) if figures and result is not None else None
    )
    return entry


def registry_document(*, figures: bool = True) -> dict[str, Any]:
    """Describe every registered model as one JSON-ready document.

    Parameters
    ----------
    figures
        Include each model's ``example_figure``; ``False`` writes ``null`` for
        every figure and leaves everything else unchanged.

    Raises
    ------
    RegistryError
        If a model's first example fails, naming the model.
    """
    return {
        "format": REGISTRY_FORMAT,
        "pyeconomics": __version__,
        "models": [_entry(model, figures=figures) for model in registry.models()],
    }


def write_registry(path: str | os.PathLike[str], *, figures: bool = True) -> None:
    """Write :func:`registry_document` to ``path`` as canonical JSON bytes.

    The file is UTF-8 with no byte-order mark, no line break and no trailing
    newline: its bytes are exactly ``canonical_json(registry_document())``, so
    its SHA-256 identifies the document.

    Raises
    ------
    RegistryError
        If a model's first example fails, naming the model.
    """
    Path(path).write_bytes(canonical_json(registry_document(figures=figures)))
