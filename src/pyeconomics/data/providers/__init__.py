# src/pyeconomics/data/providers/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Data providers: the contract every source implements (ADR-0011 decision 9).

:mod:`~pyeconomics.data.providers.base` defines :class:`DataProvider`,
:class:`ProviderInfo` and the typed fetch pipeline; :mod:`~.rules` holds the
rules ``pyeconomics.data.registry.validate()`` applies. A provider registers
through the ``pyeconomics.providers`` entry-point group, which
:mod:`pyeconomics.data.registry` reads. The built-in providers arrive from
Phase 3 Step 6.
"""

from __future__ import annotations

from pyeconomics.data.providers.base import (
    MAX_QUERY_SERIES,
    MAX_SEARCH_RESULTS,
    SERIES_ID_PATTERN,
    Access,
    Authentication,
    AuthKind,
    Capability,
    Case,
    DataProvider,
    KeyPlacement,
    KeySlot,
    Platform,
    ProviderInfo,
    Query,
    RateLimit,
    SearchHit,
    current_platform,
    tail,
)

__all__ = [
    "MAX_QUERY_SERIES",
    "MAX_SEARCH_RESULTS",
    "SERIES_ID_PATTERN",
    "Access",
    "AuthKind",
    "Authentication",
    "Capability",
    "Case",
    "DataProvider",
    "KeyPlacement",
    "KeySlot",
    "Platform",
    "ProviderInfo",
    "Query",
    "RateLimit",
    "SearchHit",
    "current_platform",
    "tail",
]
