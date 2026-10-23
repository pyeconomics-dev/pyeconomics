# tests/data/test_data_concurrency.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The data layer's process-wide state under concurrent threads (Phase 4 Step 1).

A server's worker or an MCP server's tool threads may resolve keys, read the
settings and fetch at once in one process. The redaction factory is installed
once however many threads ask; each thread's key resolution returns its own
provider's key and logs none; ``withheld``, ``cache.memo`` and ``cache.bypass``
belong to the thread that opened them; the settings are read once and
``configure``'s overrides, process-wide by design, reach every thread. The
cache store's concurrent writers are tested in
``tests/data/cache/test_cache_concurrency.py``.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from leakcheck import Canary, LeakCheck, canary

from pyeconomics.data import cache, config, redaction
from pyeconomics.data.credentials import (
    has_key,
    key_variable,
    resolve_key,
    withheld,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

THREADS = 8
ROUNDS = 25
#: Seconds any one wait may take before the test fails instead of hanging.
PATIENCE = 30
PROVIDERS = ("fred", "bls", "bea", "census")


@dataclass(frozen=True)
class Planted:
    """Several canaries, searched for together."""

    canaries: tuple[Canary, ...]

    def needles(self) -> tuple[str, ...]:
        return tuple(n for c in self.canaries for n in c.needles())


def together[T](call: Callable[[int], T], threads: int = THREADS) -> list[T]:
    """Run ``call(index)`` on ``threads`` threads released at the same moment."""
    barrier = threading.Barrier(threads)

    def released(index: int) -> T:
        barrier.wait(PATIENCE)
        return call(index)

    with ThreadPoolExecutor(threads) as pool:
        futures = [pool.submit(released, index) for index in range(threads)]
        return [future.result(PATIENCE) for future in futures]


def test_the_redaction_factory_is_installed_once_from_many_threads() -> None:
    # The isolation fixture restores the log-record factory afterwards.
    logging.setLogRecordFactory(logging.LogRecord)
    together(lambda _index: redaction.install())
    factory = logging.getLogRecordFactory()
    assert redaction.installed()
    assert factory.previous is logging.LogRecord  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]


def test_records_logged_from_many_threads_are_scrubbed() -> None:
    planted = canary()
    check = LeakCheck(planted)
    logging.setLogRecordFactory(logging.LogRecord)
    logger = logging.getLogger("pyeconomics.test_data_concurrency")

    def log(index: int) -> None:
        redaction.install()
        for _ in range(ROUNDS):
            logger.debug("thread %d sends %s", index, planted.value)

    with check.logs(logger.name):
        together(log)
    assert sum(len(texts) for texts in check.sinks.values()) >= THREADS * ROUNDS
    check.assert_clean()


def test_resolve_key_from_many_threads_returns_each_providers_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planted = {provider: canary(provider) for provider in PROVIDERS}
    for provider, held in planted.items():
        monkeypatch.setenv(key_variable(provider), held.value)
    check = LeakCheck(Planted(tuple(planted.values())))

    def resolve(index: int) -> list[bool]:
        provider = PROVIDERS[index % len(PROVIDERS)]
        return [resolve_key(provider) == planted[provider].held for _ in range(ROUNDS)]

    logging.setLogRecordFactory(logging.LogRecord)
    with check.logs():
        answers = together(resolve)
    assert all(all(row) for row in answers)
    assert redaction.installed()
    for held in planted.values():
        check.add("scrub_text", redaction.scrub_text(f"key={held.value}"))
    check.assert_clean()


def test_withheld_hides_a_key_on_its_own_thread_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(key_variable("bls"), canary("bls").value)
    inside, checked = threading.Event(), threading.Event()

    def hiding() -> bool:
        with withheld("bls"):
            inside.set()
            assert checked.wait(PATIENCE)
            return has_key("bls")

    with ThreadPoolExecutor(2) as pool:
        hidden = pool.submit(hiding)
        assert inside.wait(PATIENCE)
        elsewhere = pool.submit(has_key, "bls").result(PATIENCE)
        checked.set()
        assert hidden.result(PATIENCE) is False
    assert elsewhere is True


def test_the_settings_are_read_once_from_many_threads() -> None:
    seen = together(lambda _index: config.settings())
    assert len({id(found) for found in seen}) == 1


def test_configure_reaches_every_thread() -> None:
    # Process-wide by design: a surface configures once, at start.
    config.configure(offline=True)
    assert all(together(lambda _index: config.settings().offline))


def test_a_memo_and_a_bypass_belong_to_the_thread_that_opened_them() -> None:
    inside, checked = threading.Event(), threading.Event()

    def opened() -> tuple[bool, bool]:
        with cache.memo(), cache.bypass():
            inside.set()
            assert checked.wait(PATIENCE)
            return cache._MEMO.get() is not None, cache._BYPASS.get()  # noqa: SLF001

    def elsewhere() -> tuple[bool, bool]:
        return cache._MEMO.get() is not None, cache._BYPASS.get()  # noqa: SLF001

    with ThreadPoolExecutor(2) as pool:
        mine = pool.submit(opened)
        assert inside.wait(PATIENCE)
        other = pool.submit(elsewhere).result(PATIENCE)
        checked.set()
        assert mine.result(PATIENCE) == (True, True)
    assert other == (False, False)
