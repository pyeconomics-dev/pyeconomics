# src/pyeconomics/data/_released.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The released-id ledgers of the data layer (ADR-0003: a released id is permanent).

Once a release ships a provider id or a catalog concept id, the id is never
deleted, renamed or given to another. Two sections record what each release
shipped, so ``pyeconomics.data.registry.validate()`` can fail when an id goes
missing: :data:`PROVIDERS` (rule ``released``) and :data:`CONCEPTS` (rule
``released-concept``, ADR-0011 decision 15). Both are empty until Phase 3
Step 19 releases the first ids.

A module holds the ledgers rather than a data file because the wheel admits only
Python modules under ``pyeconomics/``. The entries have the shape of
:class:`pyeconomics.core._released.Released`, whose ``canonical_id`` is the id
itself for a provider and for a concept.

Examples
--------
>>> from pyeconomics.data._released import CONCEPTS, PROVIDERS
>>> len(PROVIDERS), len(CONCEPTS)
(0, 0)
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core._released import Released

__all__ = ["CONCEPTS", "PROVIDERS"]

#: Every released provider id and its first package version.
PROVIDERS: Final[Mapping[str, Released]] = MappingProxyType({})

#: Every released catalog concept id and its first package version.
CONCEPTS: Final[Mapping[str, Released]] = MappingProxyType({})
