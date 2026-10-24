# src/pyeconomics/surfaces/documents.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The JSON documents a surface returns for the data API's values.

A model run's document is its result's canonical JSON
(:mod:`~pyeconomics.surfaces.envelope`). The data commands return values of the
data layer instead, and these functions give each one JSON-ready form, which
:func:`~pyeconomics.core.canonical.canonical_json` then writes:

- :func:`data_document`: what ``data.get`` resolved, as the frame with every
  source record and the attributions and notices its data requires (ADR-0005
  rule 2), so the data never travels without them;
- :func:`jsonable`: any other value (a concept's description, a provider's
  terms, search hits, cache entries), read field by field.

Nothing here imports the data layer: it receives the data layer's values, so
``import pyeconomics.surfaces`` still loads no data module.

Examples
--------
>>> import datetime as dt
>>> from pyeconomics.core import LicenceClass
>>> jsonable({"checked": dt.date(2026, 10, 24), "licence": LicenceClass.HOSTED_SAFE})
{'checked': '2026-10-24', 'licence': 'hosted-safe'}
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import enum
import re
from collections.abc import Mapping
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

from pyeconomics.core.provenance import LicenceClass

if TYPE_CHECKING:
    from collections.abc import Sequence

    from pyeconomics.core.provenance import DataSource
    from pyeconomics.data.resolver import Resolved

__all__ = ["attributions", "data_document", "jsonable"]


def jsonable(value: object) -> Any:  # noqa: ANN401, C901, PLR0911 - one branch per kind
    """Return a value as JSON-ready values, recursively.

    A value with a ``to_dict`` method gives what that returns, and a pydantic
    model its JSON dump; a dataclass gives a mapping of its fields; an enum its
    value; a date or a time its ISO 8601 text; a path its text; a mapping, a
    sequence or a set its items.

    Raises
    ------
    TypeError
        For a value of any other type, rather than guess at its text.
    """
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, enum.Enum):
        return jsonable(value.value)
    if isinstance(value, str):
        return value
    if isinstance(value, dt.date):  # a datetime too
        return value.isoformat()
    if isinstance(value, PurePath):
        return str(value)
    if isinstance(value, re.Pattern):
        return value.pattern
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        return jsonable(to_dict())
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: jsonable(getattr(value, field.name))
            for field in dataclasses.fields(value)
        }
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, set | frozenset):
        return sorted(jsonable(item) for item in value)
    msg = f"{type(value).__name__} has no JSON form"
    raise TypeError(msg)


def attributions(sources: Sequence[DataSource]) -> list[str]:
    """Return the attribution and required notices of records, de-duplicated.

    Every attribution first, then every notice, in record order, as
    :meth:`~pyeconomics.core.results.Result.attributions` gives them for a run;
    a value the user supplied needs neither.
    """
    records = [s for s in sources if s.licence is not LicenceClass.USER_SUPPLIED]
    texts = (
        *(record.attribution for record in records),
        *(record.notice for record in records if record.notice),
    )
    return list(dict.fromkeys(texts))


def data_document(resolved: Resolved) -> dict[str, object]:
    """Return what ``data.get`` resolved as one JSON-ready document.

    It holds the ``frame`` (the series or table in its own JSON form), the
    ``concept`` it answers (``null`` for a provider series), one record per
    source read (``sources``), the candidates passed over and why
    (``skipped``), and the ``attributions``: the texts the data must be shown
    with.
    """
    return {
        "concept": resolved.concept,
        "frame": resolved.frame.to_dict(),
        "sources": [record.to_dict() for record in resolved.sources],
        "skipped": [jsonable(skip) for skip in resolved.skipped],
        "attributions": attributions(resolved.sources),
    }
