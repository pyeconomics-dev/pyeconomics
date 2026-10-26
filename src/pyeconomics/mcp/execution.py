# src/pyeconomics/mcp/execution.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Where a tool call's run or series executes, and what it returns.

The MCP server hands each run and each series to an :class:`Executor`, which
returns the canonical bytes the tool then sends: a run's ``Result.to_json()``,
a series' document. Two executors exist:

- :class:`LocalExecutor` (``pyeconomics mcp``, over stdio or local HTTP): the run
  goes through :func:`~pyeconomics.surfaces.invoke.invoke` on a thread of the
  server's own process, which is safe since Phase 4 Step 1 made the library's
  warning capture thread-aware;
- the REST server's executor, which :func:`pyeconomics.server.create_app` builds
  for its ``/mcp`` mount: each task goes to the same worker pool, with the same
  budgets, as ``/v1``, so hosted MCP cannot bypass them. A worker's failure comes
  back as a problem already made, which it raises as :class:`Refused`.

Both pass the server's ``llm_use`` policy to the run's bind and the series'
resolution, and check the answer's records before returning it.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

import anyio.to_thread

if TYPE_CHECKING:
    from collections.abc import Mapping

    from pyeconomics.core.model import Model
    from pyeconomics.core.provenance import LlmUsePolicy
    from pyeconomics.surfaces.invoke import BindRequest
    from pyeconomics.surfaces.problems import Problem

__all__ = ["Executor", "LocalExecutor", "Refused"]


class Refused(Exception):  # noqa: N818 - it carries the refusal, not a bug
    """A task failed elsewhere, and its problem was already made there.

    Parameters
    ----------
    problem
        The problem, from the error table.
    error_name
        The error's type name, for the log record.
    """

    def __init__(self, problem: Problem, error_name: str = "") -> None:
        super().__init__(problem.slug)
        self.problem = problem
        self.error_name = error_name


class Executor(Protocol):
    """Runs a model or reads a series for a tool, returning canonical bytes."""

    async def run(
        self,
        model: Model[Any, Any],
        inputs: Mapping[str, Any],
        bind: BindRequest | None,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Return a run's canonical result, ``Result.to_json()`` in UTF-8.

        Raises
        ------
        PyeconomicsError
            As :func:`~pyeconomics.surfaces.invoke.invoke` raises it.
        Refused
            For a problem made elsewhere.
        """
        ...

    async def series(
        self,
        target: str,
        options: Mapping[str, str],
        limit: int,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Return a series' canonical document, at most ``limit`` observations.

        ``options`` holds ``data.get``'s ``start``, ``end``, ``as_of``,
        ``vintage`` and ``provider``, as text.

        Raises
        ------
        PyeconomicsError
            As :func:`pyeconomics.data.get` raises it.
        Refused
            For a problem made elsewhere.
        """
        ...


def _run(
    model_id: str,
    inputs: Mapping[str, Any],
    bind: BindRequest | None,
    policy: LlmUsePolicy,
) -> bytes:
    from pyeconomics.surfaces.envelope import canonical_bytes  # noqa: PLC0415
    from pyeconomics.surfaces.invoke import invoke  # noqa: PLC0415

    return canonical_bytes(invoke(model_id, dict(inputs), bind=bind, llm_use=policy))


def _series(
    target: str, options: Mapping[str, str], limit: int, policy: LlmUsePolicy
) -> bytes:
    from pyeconomics.core import _fields as f  # noqa: PLC0415
    from pyeconomics.core.canonical import canonical_json  # noqa: PLC0415
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here
    from pyeconomics.surfaces.documents import data_document  # noqa: PLC0415
    from pyeconomics.surfaces.gate import check_records  # noqa: PLC0415

    def day(name: str) -> Any:  # noqa: ANN401 - a date or None
        text = options.get(name)
        return None if text is None else f.parse_day(text, name)

    resolved = api.get(
        target,
        start=day("start"),
        end=day("end"),
        as_of=day("as_of"),
        vintage=options.get("vintage"),
        provider=options.get("provider"),
        max_observations=limit,
        llm_use=policy,
    )
    check_records(resolved.sources, policy, subject=target)
    return canonical_json(data_document(resolved))


class LocalExecutor:
    """Runs each task on a thread of this process (stdio and local HTTP)."""

    async def run(
        self,
        model: Model[Any, Any],
        inputs: Mapping[str, Any],
        bind: BindRequest | None,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Run the model through ``invoke`` on a thread; see :class:`Executor`."""
        return await anyio.to_thread.run_sync(_run, model.id, inputs, bind, policy)

    async def series(
        self,
        target: str,
        options: Mapping[str, str],
        limit: int,
        policy: LlmUsePolicy,
    ) -> bytes:
        """Read the series through ``data.get`` on a thread; see :class:`Executor`."""
        return await anyio.to_thread.run_sync(_series, target, options, limit, policy)
