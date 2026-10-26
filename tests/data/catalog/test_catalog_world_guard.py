# tests/data/catalog/test_catalog_world_guard.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The stand-in world refuses to run against the user's cache (Phase 4 Step 9)."""

from __future__ import annotations

import catalog_world
import pytest

from pyeconomics.data import api, cache
from pyeconomics.data import registry as data_registry


def test_the_world_needs_a_cache_of_its_own(monkeypatch: pytest.MonkeyPatch) -> None:
    world = catalog_world.world_registry()
    monkeypatch.setattr(data_registry._CACHE, "registry", world)  # noqa: SLF001
    monkeypatch.delenv("PYECONOMICS_CACHE_DIR")
    # bypass: with the variable gone, nothing may touch the user's cache here.
    with cache.bypass(), pytest.raises(RuntimeError, match="PYECONOMICS_CACHE_DIR"):
        api.get("cbo:quarterly:noncyclical_rate_of_unemployment")
