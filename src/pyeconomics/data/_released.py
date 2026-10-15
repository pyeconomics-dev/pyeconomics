# src/pyeconomics/data/_released.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The released-id ledger of the data layer (ADR-0003: a released id is permanent).

Once a release ships a provider id, the id is never deleted, renamed or given to
another provider. This ledger records every provider id a release shipped, so
``pyeconomics.data.registry.validate()`` can fail when one goes missing. It is
empty until Phase 3 Step 19 releases the first providers; Step 11 adds the
catalog's concept ids as a second section.

A module holds the ledger rather than a data file because the wheel admits only
Python modules under ``pyeconomics/``. The entries have the shape of
:class:`pyeconomics.core._released.Released`, whose ``canonical_id`` is the id
itself for a provider.

Examples
--------
>>> from pyeconomics.data._released import PROVIDERS
>>> len(PROVIDERS)
0
"""

from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core._released import Released

__all__ = ["PROVIDERS"]

#: Every released provider id and its first package version.
PROVIDERS: Final[Mapping[str, Released]] = MappingProxyType({})
