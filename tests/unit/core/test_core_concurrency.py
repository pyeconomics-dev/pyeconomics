# tests/unit/core/test_core_concurrency.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The core's process-wide state under concurrent threads (Phase 4 Step 1).

The installed registry is discovered once, under a re-entrant lock, however
many threads ask for it first: the second waits for the first discovery and
never sees it half done (which would raise the "used the registry while it was
being discovered" error). :mod:`pyeconomics.core.random` keeps no state, so
threads drawing from the same seed draw the same numbers. Warnings are in
``test_context_concurrency.py``.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from pyeconomics.core import generator
from pyeconomics.core import registry as core_registry

if TYPE_CHECKING:
    from collections.abc import Iterable

    import pytest

    from pyeconomics.core.registry import Registry

THREADS = 8
#: Seconds any one wait may take before the test fails instead of hanging.
PATIENCE = 60


def test_the_first_discovery_from_two_threads_at_once_runs_once(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = core_registry.discover
    calls: list[int] = []
    barrier = threading.Barrier(2)

    def slow(entry_points: Iterable[object] | None = None) -> Registry:
        calls.append(threading.get_ident())
        # Hold the discovery open while the other thread arrives at the lock.
        time.sleep(0.2)
        return real(entry_points)  # type: ignore[arg-type]

    def first_use(_index: int) -> Registry:
        barrier.wait(PATIENCE)
        return core_registry.installed()

    monkeypatch.setattr(core_registry, "discover", slow)
    core_registry.refresh()
    try:
        with ThreadPoolExecutor(2) as pool:
            found = [
                f.result(PATIENCE) for f in [pool.submit(first_use, i) for i in (0, 1)]
            ]
    finally:
        core_registry.refresh()
    assert len(calls) == 1
    assert found[0] is found[1]
    assert "econometrics.garch" in found[0].ids()


def test_threads_drawing_from_one_seed_draw_the_same_numbers() -> None:
    alone = generator(7).standard_normal(1_000).tolist()
    barrier = threading.Barrier(THREADS)

    def draw(_index: int) -> list[float]:
        barrier.wait(PATIENCE)
        found: list[float] = generator(7).standard_normal(1_000).tolist()
        return found

    with ThreadPoolExecutor(THREADS) as pool:
        drawn = [
            f.result(PATIENCE) for f in [pool.submit(draw, i) for i in range(THREADS)]
        ]
    assert all(found == alone for found in drawn)
