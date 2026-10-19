# src/pyeconomics/registry.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The model registry: every registered model, found by id.

Models register through the ``pyeconomics.models`` entry-point group. The first
call here discovers them; ``import pyeconomics`` does not. An alias of a renamed
model resolves to the canonical model and warns with
:class:`~pyeconomics.core.warnings.PyeconomicsDeprecationWarning`.

Examples
--------
>>> from pyeconomics import registry
>>> registry.refresh()
>>> registry.validate() is None
True
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pyeconomics.core import registry as _core
from pyeconomics.core.describe import describe as _describe
from pyeconomics.core.registry import refresh, validate

if TYPE_CHECKING:
    from pyeconomics.core.model import Model

__all__ = [
    "describe",
    "domains",
    "get",
    "ids",
    "models",
    "refresh",
    "resolve",
    "validate",
]

# The facade's own frames sit between the caller and Registry.get, so the
# deprecation warning is aimed one frame further out.
_CALLER = 3


def ids() -> tuple[str, ...]:
    """Return every canonical model id, sorted."""
    return _core.installed().ids()


def get(model_id: str) -> Model[Any, Any]:
    """Return the model with this id or alias.

    An alias issues ``PyeconomicsDeprecationWarning`` naming the canonical id
    and the release that removes it.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id; the error lists close matches.
    """
    return _core.installed().get(model_id, stacklevel=_CALLER)


def resolve(model_id: str) -> Model[Any, Any]:
    """Resolve an id or alias to the canonical model; see :func:`get`."""
    return _core.installed().resolve(model_id, stacklevel=_CALLER)


def models(domain: str | None = None) -> tuple[Model[Any, Any], ...]:
    """Return the registered models, sorted by id, optionally of one domain."""
    return _core.installed().models(domain)


def domains() -> tuple[str, ...]:
    """Return the domains that have a registered model."""
    return _core.installed().domains()


def describe(model_id: str) -> dict[str, Any]:
    """Describe a model as JSON-ready values.

    The dictionary holds the specification, the input and output JSON Schemas
    and the card's Markdown (see :mod:`pyeconomics.core.describe` for the keys);
    :func:`~pyeconomics.core.canonical.canonical_json` accepts it. An alias
    resolves to the canonical model and warns.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    """
    model = _core.installed().resolve(model_id, stacklevel=_CALLER)
    if not model.spec.bindings:
        return _describe(model)
    # The card's "Data" section lists the sources that can fill each bound
    # concept, which only the data layer can read: import it for a bound model.
    from pyeconomics.data.bindings import candidate_notes  # noqa: PLC0415

    return _describe(model, candidate_notes(model))
