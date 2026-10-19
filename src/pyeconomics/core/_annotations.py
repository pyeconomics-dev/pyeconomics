# src/pyeconomics/core/_annotations.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Reading the metadata of a field's type annotation.

``registry.validate()`` walks a model field's annotation to hold it to the
unit, bounds and length rules, and the binding layer walks the same annotation
to learn a field's unit kind and whether it is an array. Both need the
constraints that ``Field(...)`` and ``Annotated[...]`` stack on a type, so the
two helpers live here, in a module with no import of the model contract.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from annotated_types import GroupedMetadata, MaxLen
from pydantic.fields import FieldInfo

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

__all__ = ["flatten", "max_length"]


def flatten(metadata: Iterable[object]) -> list[object]:
    """Expand ``Field(...)`` objects and grouped constraints into their parts."""
    flat: list[object] = []
    for item in metadata:
        if isinstance(item, FieldInfo):
            flat.extend(flatten(item.metadata))
        elif isinstance(item, GroupedMetadata):
            flat.extend(flatten(item))
        else:
            flat.append(item)
    return flat


def max_length(metadata: Sequence[object]) -> int | None:
    """Return the tightest ``max_length`` in the metadata, or ``None``."""
    lengths = [m.max_length for m in metadata if isinstance(m, MaxLen)]
    return min(lengths) if lengths else None
