# tests/unit/core/test_context_concurrency.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Concurrent runs keep their own library warnings (issue #157).

``core.library_warnings`` changes the :mod:`warnings` module's process-wide
filters and ``showwarning``. A server or an MCP tool may run two models at once
in one process, so its blocks take turns under a re-entrant lock and record only
their own thread's warnings. Here eight threads run ``econometrics.time_series``
and, where arch installs, ``econometrics.garch`` together, over inputs of which
some raise a library warning and others do not: each result's warnings must
equal those of the same run on its own, and the global filters must be as they
were. Canary keys sit in the environment throughout, and none may reach a
result's warnings or a log record.
"""

from __future__ import annotations

import sys
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
from extra_gaps import excluded_gap
from leakcheck import Canary, LeakCheck, canary

from pyeconomics.core import collect_warnings, library_warnings, run_model
from pyeconomics.data.credentials import key_variable
from pyeconomics.models.econometrics import garch, time_series
from pyeconomics.models.econometrics.garch import OBSERVATIONS_MIN

if TYPE_CHECKING:
    from pyeconomics.core import Model

THREADS = 8
ITERATIONS = 20
#: Seconds any one wait may take before the test fails instead of hanging.
PATIENCE = 60
#: The providers whose key variables hold a canary while the threads run.
PROVIDERS = ("fred", "bls", "bea", "census")

type Case = tuple[Model[Any, Any], dict[str, Any]]
type Warned = tuple[tuple[str, str], ...]


def walk(seed: int) -> list[float]:
    """A short series: white noise for an even seed, a random walk for an odd."""
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(int(rng.integers(12, 40)))
    series: list[float] = (np.cumsum(noise) if seed % 2 else noise).round(3).tolist()
    return series


def returns(seed: int) -> list[float]:
    """About 1% daily returns, just above garch's minimum length."""
    rng = np.random.default_rng(seed)
    count = OBSERVATIONS_MIN + int(rng.integers(0, 40))
    drawn: list[float] = (rng.standard_normal(count) * 0.01).round(6).tolist()
    return drawn


#: An ARMA(3, 3) on a few dozen points: statsmodels warns of its starting
#: parameters or of a failed convergence. The examples run without a warning.
TIME_SERIES_CASES: tuple[Case, ...] = (
    *(
        (time_series, {"calculation": "arima", "series": walk(seed), "ar": 3, "ma": 3})
        for seed in range(3)
    ),
    *((time_series, dict(example.inputs)) for example in time_series.spec.examples),
)
#: The examples, and an EGARCH whose optimizer may stop at its iteration limit.
GARCH_CASES: tuple[Case, ...] = (
    *((garch, dict(example.inputs)) for example in garch.spec.examples),
    (garch, {"calculation": "egarch", "returns": returns(0), "periods_per_year": 252}),
)


def warned(case: Case) -> Warned:
    model, inputs = case
    return tuple((w.code, w.message) for w in run_model(model, inputs).warnings)


@dataclass(frozen=True)
class Planted:
    """Several canaries, searched for together."""

    canaries: tuple[Canary, ...]

    def needles(self) -> tuple[str, ...]:
        return tuple(n for c in self.canaries for n in c.needles())


def test_garch_runs_or_names_its_gap() -> None:
    """arch is missing exactly where its marker leaves it out (#154): CPython 3.15."""
    gap = excluded_gap(garch)
    assert (gap is not None) == (sys.version_info >= (3, 15))
    if gap is not None:
        assert gap.package == "arch"


def test_concurrent_runs_keep_their_own_library_warnings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases = TIME_SERIES_CASES + (GARCH_CASES if excluded_gap(garch) is None else ())
    alone = [warned(case) for case in cases]
    assert any(alone), "no case raised a library warning"
    assert not all(alone), "every case raised a library warning"
    planted = Planted(tuple(canary(provider) for provider in PROVIDERS))
    for provider, held in zip(PROVIDERS, planted.canaries, strict=True):
        monkeypatch.setenv(key_variable(provider), held.value)
    check = LeakCheck(planted)
    filters, shown = list(warnings.filters), warnings.showwarning
    barrier = threading.Barrier(THREADS)

    def together(index: int) -> tuple[int, Warned]:
        barrier.wait(PATIENCE)
        return index, warned(cases[index])

    with check.logs(), check.warnings(), ThreadPoolExecutor(THREADS) as pool:
        for iteration in range(ITERATIONS):
            picked = [(iteration * THREADS + k) % len(cases) for k in range(THREADS)]
            futures = [pool.submit(together, index) for index in picked]
            for future in futures:
                index, found = future.result(PATIENCE)
                assert found == alone[index], f"iteration {iteration}, case {index}"
                check.add("result:warnings", repr(found))
    assert list(warnings.filters) == filters
    assert warnings.showwarning is shown
    check.assert_clean()


def test_another_threads_warning_is_left_to_that_thread() -> None:
    inside, issued = threading.Event(), threading.Event()

    def wrapped() -> list[str]:
        with collect_warnings() as recorded, library_warnings("toylib"):
            inside.set()
            assert issued.wait(PATIENCE)
            warnings.warn("own", RuntimeWarning, stacklevel=1)
        return [w.text for w in recorded]

    def stranger() -> None:
        warnings.warn("stranger", UserWarning, stacklevel=1)

    with warnings.catch_warnings(record=True) as outer:
        warnings.simplefilter("always")
        with ThreadPoolExecutor(2) as pool:
            mine = pool.submit(wrapped)
            assert inside.wait(PATIENCE)
            pool.submit(stranger).result(PATIENCE)
            issued.set()
            assert mine.result(PATIENCE) == ["toylib: RuntimeWarning: own"]
    assert [str(w.message) for w in outer] == ["stranger"]


def test_blocks_on_two_threads_take_turns() -> None:
    inside, release = threading.Event(), threading.Event()
    order: list[str] = []

    def first() -> None:
        with library_warnings("toylib"):
            inside.set()
            assert release.wait(PATIENCE)
            order.append("first")

    def second() -> None:
        with library_warnings("toylib"):
            order.append("second")

    with ThreadPoolExecutor(2) as pool:
        held = pool.submit(first)
        assert inside.wait(PATIENCE)
        waiting = pool.submit(second)
        # The second block waits for the lock; it has not run.
        with pytest.raises(TimeoutError):
            waiting.result(0.2)
        release.set()
        held.result(PATIENCE)
        waiting.result(PATIENCE)
    assert order == ["first", "second"]


def test_a_block_nested_on_one_thread_does_not_wait_for_itself() -> None:
    # Each context manager in one with statement enters inside the one before.
    with (
        collect_warnings() as recorded,
        library_warnings("outer"),
        library_warnings("inner"),
    ):
        warnings.warn("deep", RuntimeWarning, stacklevel=1)
    assert [w.text for w in recorded] == ["inner: RuntimeWarning: deep"]
