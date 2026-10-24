# src/pyeconomics/surfaces/listing.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""List and search the registered models, as every surface shows them.

``pyeconomics models list`` and ``models search`` print these entries; the REST
API's ``GET /v1/models`` (``?domain=``, ``?q=``) and the MCP server's discovery
tools return the same ones, so a model is found the same way everywhere. Each
entry is JSON-ready and holds what a person needs to choose a model, read from
its specification alone: no example runs, no card is built and no data module
is imported.

:func:`search_models` matches words of the query against each model's id,
title, tags, domain and summary, offline, and ranks the matches: a word in the
id or title counts most, then a tag, then the domain or the summary.

Examples
--------
>>> [entry["id"] for entry in search_models("present value annuity", 2)]
['foundations.time_value', ...]
>>> list_models("macro")[0]["domain"]
'macro'
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, Final

from pyeconomics import registry
from pyeconomics.core import _fields as f

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.core.model import Model

__all__ = ["MAX_SEARCH_RESULTS", "list_models", "model_entry", "search_models"]

#: The most entries a search returns.
MAX_SEARCH_RESULTS: Final = 100
_MIN_TOKEN: Final = 2


def model_entry(model: Model[Any, Any]) -> dict[str, object]:
    """Describe one model in a few JSON-ready fields.

    ``bound`` says whether the model declares data bindings, so ``models run``
    can read its inputs from the catalog; ``extra`` names the optional extra it
    needs, if any.
    """
    spec = model.spec
    return {
        "id": model.id,
        "version": spec.version,
        "domain": spec.domain,
        "title": spec.title,
        "summary": spec.summary,
        "tags": list(spec.tags),
        "cost": None if spec.cost is None else spec.cost.value,
        "extra": spec.extra,
        "bound": bool(spec.bindings),
    }


def list_models(domain: str | None = None) -> list[dict[str, object]]:
    """Return every registered model's entry, sorted by id, optionally of one domain.

    Raises
    ------
    InputError
        If ``domain`` is not one of the domains; the message lists them.
    """
    return [model_entry(model) for model in registry.models(domain)]


def _tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", text.lower()) if len(t) >= _MIN_TOKEN]


def _score(model: Model[Any, Any], tokens: Sequence[str]) -> int:
    spec = model.spec
    name = f"{model.id} {spec.title}".lower().replace("_", " ")
    tags = " ".join(spec.tags).lower()
    total = 0
    for token in tokens:
        if token in name:
            total += 3
        if token in tags:
            total += 2
        if token in spec.domain.lower():
            total += 1
        if token in spec.summary.lower():
            total += 1
    return total


def search_models(text: str, limit: int = 20) -> list[dict[str, object]]:
    """Return the entries of the models that match ``text``, best first.

    Parameters
    ----------
    text
        Words to look for; words shorter than two characters are ignored.
    limit
        At most this many entries, from 1 to :data:`MAX_SEARCH_RESULTS`.

    Raises
    ------
    InputError
        For empty text, or a limit outside its range.
    """
    f.text(text, "search text", max_length=256)
    if isinstance(limit, bool) or not 1 <= limit <= MAX_SEARCH_RESULTS:
        msg = f"limit must be between 1 and {MAX_SEARCH_RESULTS}"
        raise f.fail(msg)
    tokens = _tokens(text)
    scored = [(_score(model, tokens), model) for model in registry.models()]
    ranked = sorted(
        (item for item in scored if item[0] > 0),
        key=lambda item: (-item[0], item[1].id),
    )
    return [model_entry(model) for _, model in ranked[:limit]]
