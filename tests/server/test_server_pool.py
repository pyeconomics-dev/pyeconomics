# tests/server/test_server_pool.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The worker pool with real spawned processes, on every OS cell (Step 6).

The toy models of tests/server/server_support.py run in the workers, which the
pool's setup installs them in: ``foundations.toy_nap`` sleeps for as long as it
is asked and ``foundations.toy_crash`` ends its process. A run past its budget
must be stopped and answered with ``budget-exceeded``, and its worker replaced
by a new process that runs the next task; one task more than the queue holds is
refused with ``server-busy``; a worker that dies answers ``internal-error`` and
is replaced too. The app answers the same through its routes, with a real pool.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

import pytest
from server_support import (
    LOOPBACK_ONLY,
    broken_setup,
    client,
    install_toys,
    problem,
    service_of,
    use_toys,
)

from pyeconomics.core.canonical import canonical_json
from pyeconomics.server.pool import (
    InlinePool,
    ProcessPool,
    WorkerFailedError,
    make_pool,
    worker_main,
)
from pyeconomics.server.work import Outcome, Task, decode_outcome, encode_task
from pyeconomics.surfaces.service import ServerBusyError

if TYPE_CHECKING:
    from collections.abc import Coroutine, Iterator

pytestmark = LOOPBACK_ONLY

CONFIG = {"mode": "library", "offline": None}
#: Long enough to outlast any budget below, on the slowest runner.
LONG = 60.0


def _nap(seconds: float, budget: float | None = None) -> Task:
    return Task(
        kind="run",
        target="foundations.toy_nap",
        payload=canonical_json({"seconds": seconds}),
        budget=budget,
    )


def _run[T](coroutine: Coroutine[Any, Any, T]) -> T:
    return asyncio.run(coroutine)


def _slept(outcome: Outcome) -> float:
    assert outcome.problem is None, outcome.problem
    slept: float = json.loads(outcome.body)["outputs"]["slept"]
    return slept


@pytest.fixture
def pool() -> Iterator[ProcessPool]:
    started = ProcessPool(workers=1, queue_limit=1, config=CONFIG, setup=install_toys)
    started.start()
    try:
        # One quick task first, so the worker has started before any timing.
        assert _slept(_run(started.submit(_nap(0)))) == 0
        yield started
    finally:
        started.close()


def test_a_task_runs_in_another_process(pool: ProcessPool) -> None:
    (pid,) = pool.pids
    assert pid is not None
    assert pid != os.getpid()
    assert _slept(_run(pool.submit(_nap(0.01)))) == 0.01


def test_a_run_past_its_budget_is_stopped_and_its_worker_replaced(
    pool: ProcessPool,
) -> None:
    (before,) = pool.pids
    started = time.perf_counter()
    outcome = _run(pool.submit(_nap(LONG, budget=0.5)))
    assert time.perf_counter() - started < LONG / 2
    assert outcome.problem is not None
    assert (outcome.problem.slug, outcome.problem.status) == ("budget-exceeded", 422)
    assert outcome.error_name == "BudgetExceededError"
    assert _slept(_run(pool.submit(_nap(0)))) == 0
    (after,) = pool.pids
    assert after not in {None, before}


async def _until_taken(pool: ProcessPool) -> None:
    """Wait, at most 10 seconds, until the worker has taken the queued task."""
    for _ in range(1000):
        if pool._queue.empty():  # noqa: SLF001
            return
        await asyncio.sleep(0.01)
    msg = "the worker never took the task"
    raise AssertionError(msg)


def test_a_full_queue_answers_server_busy(pool: ProcessPool) -> None:
    async def scenario() -> tuple[Outcome, Outcome]:
        running = asyncio.ensure_future(pool.submit(_nap(LONG, budget=2.0)))
        await asyncio.sleep(0.05)  # it is queued, then taken
        await _until_taken(pool)
        waiting = asyncio.ensure_future(pool.submit(_nap(0)))
        await asyncio.sleep(0.05)
        with pytest.raises(ServerBusyError):
            await pool.submit(_nap(0))
        return await running, await waiting

    stopped, served = _run(scenario())
    assert stopped.problem is not None
    assert stopped.problem.slug == "budget-exceeded"
    assert _slept(served) == 0


def test_a_worker_that_dies_answers_internal_error_and_is_replaced(
    pool: ProcessPool,
) -> None:
    (before,) = pool.pids
    crash = Task(kind="run", target="foundations.toy_crash", payload=b'{"seconds": 0}')
    outcome = _run(pool.submit(crash))
    assert outcome.problem is not None
    assert (outcome.problem.slug, outcome.error_name) == (
        "internal-error",
        "WorkerFailedError",
    )
    assert outcome.problem.detail == "An unexpected error stopped the request."
    assert _slept(_run(pool.submit(_nap(0)))) == 0
    assert pool.pids[0] != before


def test_a_closed_pool_takes_no_task() -> None:
    pool = ProcessPool(workers=1, queue_limit=1, config=CONFIG, setup=install_toys)
    with pytest.raises(WorkerFailedError):
        _run(pool.submit(_nap(0)))  # never started
    pool.start()
    pool.start()  # a second start changes nothing
    pool.close()
    with pytest.raises(WorkerFailedError):
        _run(pool.submit(_nap(0)))
    assert pool.pids == (None,)


def test_a_worker_that_cannot_start_answers_internal_error() -> None:
    pool = ProcessPool(workers=1, queue_limit=1, config=CONFIG, setup=broken_setup)
    pool.start()
    try:
        outcome = _run(pool.submit(_nap(0)))
    finally:
        pool.close()
    assert outcome.problem is not None
    assert outcome.problem.slug == "internal-error"


def test_make_pool_runs_inline_with_no_workers(monkeypatch: pytest.MonkeyPatch) -> None:
    use_toys(monkeypatch)
    inline = make_pool(workers=0, queue_limit=1, config=CONFIG)
    assert isinstance(inline, InlinePool)
    inline.start()
    assert _slept(_run(inline.submit(_nap(0)))) == 0
    inline.close()
    assert isinstance(make_pool(workers=2, queue_limit=1, config=CONFIG), ProcessPool)


class _Pipe:
    """One end of an in-memory pipe, for running worker_main in a thread."""

    def __init__(self, inbox: list[bytes], outbox: list[bytes]) -> None:
        self.inbox, self.outbox = inbox, outbox

    def send_bytes(self, buf: bytes) -> None:
        self.outbox.append(bytes(buf))

    def recv_bytes(self) -> bytes:
        if not self.inbox:
            raise EOFError
        return self.inbox.pop(0)

    def poll(self, timeout: float | None = None) -> bool:
        del timeout
        return bool(self.inbox)

    def close(self) -> None:
        """Nothing to close."""


def test_worker_main_serves_tasks_until_end_of_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import signal  # noqa: PLC0415
    import warnings  # noqa: PLC0415

    from pyeconomics.server import logs  # noqa: PLC0415

    use_toys(monkeypatch)
    handlers: list[object] = []
    monkeypatch.setattr(signal, "signal", lambda *_: None)
    monkeypatch.setattr(warnings, "showwarning", warnings.showwarning)
    monkeypatch.setattr(logs, "configure", lambda *_: handlers.append(1))
    tasks: list[bytes] = list(encode_task(_nap(0.01)))
    results: list[bytes] = []
    worker_main(_Pipe(tasks, []), _Pipe([], results), CONFIG, None)
    assert handlers == [1]
    assert json.loads(results[0]) == {"ready": True}
    outcome = decode_outcome(results[1], results[2])
    assert _slept(outcome) == 0.01


def test_the_app_answers_a_budget_kill_and_a_full_queue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    use_toys(monkeypatch)
    nap = "/v1/models/foundations.toy_nap/run"
    with client(
        mode="hosted", workers=1, queue_limit=1, worker_setup=install_toys
    ) as api:
        pool = service_of(api).pool
        assert api.post(nap, content=b'{"seconds": 0}').status_code == 200
        with ThreadPoolExecutor(max_workers=2) as threads:
            # The hosted budget of an instant model is 2 seconds.
            running = threads.submit(
                api.post, nap, content=canonical_json({"seconds": LONG})
            )
            time.sleep(0.5)  # the idle worker takes it at once
            waiting = threads.submit(api.post, nap, content=b'{"seconds": 0}')
            deadline = time.monotonic() + 10
            while pool._queue.empty() and time.monotonic() < deadline:  # noqa: SLF001
                time.sleep(0.01)
            refused = api.post(nap, content=b'{"seconds": 0}')
            stopped, served = running.result(), waiting.result()
    assert refused.status_code == 503
    assert problem(refused)["type"].endswith("/server-busy")
    assert stopped.status_code == 422
    stopped_problem = problem(stopped)
    assert stopped_problem["type"].endswith("/budget-exceeded")
    assert stopped_problem["detail"].endswith(
        "run it locally: pyeconomics models run foundations.toy_nap --inputs FILE"
    )
    assert served.status_code == 200


def test_a_workers_warnings_are_single_scrubbed_lines(
    caplog: pytest.LogCaptureFixture,
) -> None:
    from pyeconomics.server import pool as pool_module  # noqa: PLC0415

    with caplog.at_level(logging.WARNING, "pyeconomics.server"):
        pool_module._show_warning(  # noqa: SLF001
            "C:/Users/someone/x.toml is old", UserWarning, "/somewhere/file.py", 3
        )
    (record,) = caplog.records
    assert record.getMessage() == "UserWarning: <path> is old"
