# src/pyeconomics/server/pool.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The worker pool: spawned processes that run tasks under their budgets.

ADR-0012 decision 10: runs and series fetches execute in worker processes,
spawned and never forked, so a run past its budget can be stopped by ending its
process, which nothing can do to a thread. :func:`make_pool` builds one of two:

- :class:`ProcessPool`: ``workers`` processes, each running one task at a time.
  Tasks wait for a free worker in a bounded queue, and one more than it holds is
  refused with :class:`~pyeconomics.surfaces.service.ServerBusyError` (503). A
  task with a budget has that many seconds of wall-clock time from the moment
  its worker receives it; past them the worker is terminated, the task answers
  :class:`~pyeconomics.surfaces.budgets.BudgetExceededError`, and a new worker
  starts in its place. A worker that dies answers ``internal-error`` and is
  replaced the same way.
- :class:`InlinePool` (``workers=0``): every task runs in a thread of the app's
  own process, with no budget and no queue. The tests use it, so that the
  registry a test installs is the one that runs.

A process pool starts its workers when the app's lifespan starts
(:meth:`ProcessPool.start`), never at import. Each worker configures the data
layer once (:func:`pyeconomics.data.configure`, with the app's data mode and
offline setting: configuration is process-wide, never per request), then imports
the models, the data layer and the exports before it reports ready, so no budget
pays for an import. A worker's messages are bytes and canonical JSON headers
(:mod:`~pyeconomics.server.work`), never a pickle.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import logging
import multiprocessing
import queue
import signal
import sys
import threading
import warnings
from concurrent.futures import Future
from typing import TYPE_CHECKING, Any, Final, Protocol

from pyeconomics.core.canonical import canonical_json
from pyeconomics.server import logs
from pyeconomics.server.work import (
    Outcome,
    Task,
    decode_outcome,
    decode_task,
    encode_outcome,
    encode_task,
    execute,
)
from pyeconomics.surfaces.budgets import BudgetExceededError
from pyeconomics.surfaces.problems import scrub
from pyeconomics.surfaces.service import ServerBusyError

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from multiprocessing.process import BaseProcess

__all__ = [
    "InlinePool",
    "Pool",
    "ProcessPool",
    "WorkerFailedError",
    "make_pool",
    "worker_main",
]

#: How long a new worker may take to import everything and report ready.
START_TIMEOUT: Final = 120.0
#: How long a worker may take to exit once asked, before it is terminated.
GRACE: Final = 5.0
#: How often an idle pool thread checks whether the pool is closing.
_POLL: Final = 0.1
_READY: Final = {"ready": True}
_LOGGER: Final = logging.getLogger(logs.LOGGER)


class _Pipe(Protocol):
    """One end of a pipe: a ``multiprocessing`` connection on every system."""

    def send_bytes(self, buf: bytes) -> None:
        """Send one frame."""

    def recv_bytes(self) -> bytes:
        """Receive one frame."""

    def poll(self, timeout: float | None = ...) -> bool:
        """Wait up to ``timeout`` seconds for a frame."""

    def close(self) -> None:
        """Close this end."""


class WorkerFailedError(RuntimeError):
    """A worker process died, or could not start, while it held a task."""


class Pool(Protocol):
    """What the app needs of a pool."""

    def start(self) -> None:
        """Start the workers."""

    async def submit(self, task: Task) -> Outcome:
        """Run a task and return its outcome."""

    def close(self) -> None:
        """Stop the workers."""


class InlinePool:
    """Runs every task in a thread of the app's process: no budget, no queue."""

    def start(self) -> None:
        """Nothing to start."""

    async def submit(self, task: Task) -> Outcome:
        """Run a task in a thread and return its outcome."""
        return await asyncio.to_thread(execute, task)

    def close(self) -> None:
        """Nothing to stop."""


class _Worker:
    """One worker process and its two one-way pipes, driven by one pool thread.

    One-way pipes are operating-system pipes everywhere, never a socket pair.
    """

    def __init__(
        self,
        index: int,
        config: Mapping[str, object],
        setup: Callable[[], object] | None,
        start_timeout: float,
    ) -> None:
        self.index = index
        self.config = dict(config)
        self.setup = setup
        self.start_timeout = start_timeout
        self.process: BaseProcess | None = None
        self._tasks: _Pipe | None = None
        self._results: _Pipe | None = None

    @property
    def alive(self) -> bool:
        """Whether the worker's process is running."""
        return self.process is not None and self.process.is_alive()

    def start(self) -> bool:
        """Start the process and wait until it reports ready; ``False`` if it fails."""
        context = multiprocessing.get_context("spawn")
        task_reader, task_writer = context.Pipe(duplex=False)
        result_reader, result_writer = context.Pipe(duplex=False)
        process = context.Process(
            target=worker_main,
            args=(task_reader, result_writer, self.config, self.setup),
            name=f"pyeconomics-worker-{self.index}",
            daemon=True,
        )
        self.process, self._tasks, self._results = process, task_writer, result_reader
        ready = False
        try:
            try:
                process.start()
            finally:
                # Keep only the parent's ends, so a dead worker reads as end of file.
                task_reader.close()
                result_writer.close()
            if result_reader.poll(self.start_timeout):
                ready = json.loads(result_reader.recv_bytes()) == _READY
        except Exception:  # noqa: BLE001 - a worker that cannot start is replaced later
            ready = False
        if not ready:
            _LOGGER.error("worker %d did not start", self.index)
            self.stop()
        return ready

    def run(self, task: Task) -> Outcome:
        """Run a task in the process, holding it to its budget."""
        if not self.alive and not self.start():
            return Outcome.failed(WorkerFailedError())
        tasks, results = self._tasks, self._results
        if tasks is None or results is None:  # pragma: no cover - start set them
            return Outcome.failed(WorkerFailedError())
        try:
            header, payload = encode_task(task)
            tasks.send_bytes(header)
            tasks.send_bytes(payload)
            if not results.poll(task.budget):
                self.stop()
                seconds = task.budget or 0.0
                return Outcome.failed(BudgetExceededError(task.target, seconds))
            return decode_outcome(results.recv_bytes(), results.recv_bytes())
        except (EOFError, OSError, ValueError):
            self.stop()
            return Outcome.failed(WorkerFailedError())

    def interrupt(self) -> None:
        """Terminate the process, so a thread waiting on it sees end of file."""
        process = self.process
        if process is not None and process.is_alive():
            process.terminate()

    def stop(self) -> None:
        """Terminate the process, wait for it, and close the pipes."""
        process, self.process = self.process, None
        if process is not None:
            if process.is_alive():
                process.terminate()
                process.join(GRACE)
            if process.is_alive():  # pragma: no cover - terminate is enough
                process.kill()
                process.join(GRACE)
            with contextlib.suppress(ValueError):
                process.close()
        self._close_pipes()

    def shutdown(self) -> None:
        """Ask the process to exit by closing its task pipe; stop it if it lingers."""
        if self._tasks is not None:
            self._tasks.close()
            self._tasks = None
        process = self.process
        if process is not None:
            process.join(GRACE)
        self.stop()

    def _close_pipes(self) -> None:
        for pipe in (self._tasks, self._results):
            if pipe is not None:
                with contextlib.suppress(OSError):
                    pipe.close()
        self._tasks = self._results = None


class ProcessPool:
    """Spawned worker processes behind a bounded queue.

    Parameters
    ----------
    workers
        How many processes, each running one task at a time.
    queue_limit
        How many tasks may wait for a free worker.
    config
        What each worker configures the data layer with: ``mode`` (``library``
        or ``hosted``) and ``offline`` (``None`` keeps the configured setting).
    setup
        A function each worker calls once before its first task; it must be
        importable by name, since the workers are spawned.
    start_timeout
        How long a new worker may take to report ready.
    """

    def __init__(
        self,
        *,
        workers: int,
        queue_limit: int,
        config: Mapping[str, object],
        setup: Callable[[], object] | None = None,
        start_timeout: float = START_TIMEOUT,
    ) -> None:
        self._queue: queue.Queue[tuple[Task, Future[Outcome]]] = queue.Queue(
            maxsize=queue_limit
        )
        self._limit = queue_limit
        self._workers = tuple(
            _Worker(index, config, setup, start_timeout) for index in range(workers)
        )
        self._threads: list[threading.Thread] = []
        self._stopping = threading.Event()

    @property
    def pids(self) -> tuple[int | None, ...]:
        """Each worker's process id, ``None`` while it has no process."""
        return tuple(
            None if worker.process is None else worker.process.pid
            for worker in self._workers
        )

    def start(self) -> None:
        """Start one thread per worker; each starts its process."""
        if self._threads:
            return
        for worker in self._workers:
            thread = threading.Thread(
                target=self._drive,
                args=(worker,),
                name=f"pyeconomics-pool-{worker.index}",
                daemon=True,
            )
            self._threads.append(thread)
            thread.start()

    def _drive(self, worker: _Worker) -> None:
        worker.start()
        while not self._stopping.is_set():
            try:
                task, future = self._queue.get(timeout=_POLL)
            except queue.Empty:
                continue
            if not future.set_running_or_notify_cancel():
                continue
            try:
                outcome = worker.run(task)
            except Exception as error:  # noqa: BLE001 - the thread must outlive any task
                outcome = Outcome.failed(error)
            future.set_result(outcome)
            if not worker.alive and not self._stopping.is_set():
                worker.start()  # replace a worker that was stopped or died
        worker.shutdown()

    async def submit(self, task: Task) -> Outcome:
        """Queue a task for the next free worker and wait for its outcome.

        Raises
        ------
        ServerBusyError
            If the queue is full.
        WorkerFailedError
            If the pool is not running.
        """
        if not self._threads or self._stopping.is_set():
            raise WorkerFailedError
        future: Future[Outcome] = Future()
        try:
            self._queue.put_nowait((task, future))
        except queue.Full:
            raise ServerBusyError(self._limit) from None
        return await asyncio.wrap_future(future)

    def close(self) -> None:
        """Stop taking tasks, cancel those still queued, and stop every worker."""
        self._stopping.set()
        while True:
            try:
                _, future = self._queue.get_nowait()
            except queue.Empty:
                break
            future.cancel()
        for worker, thread in zip(self._workers, self._threads, strict=False):
            thread.join(GRACE + _POLL)
            if thread.is_alive():
                worker.interrupt()  # a task without a budget is still running
                thread.join(GRACE)
        self._threads.clear()


def make_pool(
    *,
    workers: int,
    queue_limit: int,
    config: Mapping[str, object],
    setup: Callable[[], object] | None = None,
) -> Pool:
    """Return an inline pool for ``workers=0``, else a process pool."""
    if workers == 0:
        return InlinePool()
    return ProcessPool(
        workers=workers, queue_limit=queue_limit, config=config, setup=setup
    )


# --- the worker process ---------------------------------------------------------


def _show_warning(  # noqa: PLR0913, PLR0917 - warnings.showwarning's signature
    message: Warning | str,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: object = None,
    line: str | None = None,
) -> None:
    """Log a warning as one scrubbed line, never its source file and line."""
    del filename, lineno, file, line
    _LOGGER.warning("%s: %s", category.__name__, scrub(str(message)))


def _warm_up() -> None:
    """Import the models, the data layer and the exports before the first task."""
    from pyeconomics.core.registry import installed  # noqa: PLC0415

    installed()
    for module in ("pyeconomics.data.bindings", "pyeconomics.exports"):
        importlib.import_module(module)


def worker_main(
    tasks: _Pipe,
    results: _Pipe,
    config: Mapping[str, Any],
    setup: Callable[[], object] | None,
) -> None:
    """Serve tasks until the app closes the task pipe: a worker process's entry.

    Parameters
    ----------
    tasks
        Where the app sends each task's two frames.
    results
        Where the worker sends the ready message, then each outcome's two frames.
    config
        ``mode`` and ``offline`` for :func:`pyeconomics.data.configure`.
    setup
        Called once before the first task, if given.
    """
    # Ctrl+C (and Ctrl+Break on Windows) reaches every process of the console;
    # the app stops its workers once its requests have finished.
    for name in ("SIGINT", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), signal.SIG_IGN)
    logs.configure(sys.stderr, logging.WARNING)
    warnings.showwarning = _show_warning  # ty: ignore[invalid-assignment]
    from pyeconomics import data  # noqa: PLC0415 - the data layer loads here

    data.configure(mode=config["mode"], offline=config.get("offline"))
    if setup is not None:
        setup()
    _warm_up()
    results.send_bytes(canonical_json(_READY))
    while True:
        try:
            header = tasks.recv_bytes()
            payload = tasks.recv_bytes()
        except (EOFError, OSError):
            return
        head, body = encode_outcome(execute(decode_task(header, payload)))
        results.send_bytes(head)
        results.send_bytes(body)
