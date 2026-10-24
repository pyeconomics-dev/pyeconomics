# src/pyeconomics/server/work.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""One task of the worker pool: a model run or a series, rendered in a format.

The app builds a :class:`Task` from a request and hands it to the pool
(:mod:`~pyeconomics.server.pool`). :func:`execute` runs it, in a worker process
or, with no workers, in a thread of the app, and returns an :class:`Outcome`:
the response body's bytes, or the problem the error became
(:func:`~pyeconomics.surfaces.problems.problem_for`). A run goes through
:func:`~pyeconomics.surfaces.invoke.invoke` and nothing else; a series through
:func:`pyeconomics.data.get`. Either is then rendered in the task's format
(:mod:`~pyeconomics.server.formats`).

Between the app and a worker, a task and an outcome each travel as two frames: a
canonical JSON header built from plain values, and the raw bytes of the inputs
or of the body (:func:`encode_task` and :func:`decode_task`,
:func:`encode_outcome` and :func:`decode_outcome`). Nothing is pickled, so a
message can carry nothing but data. Nothing here imports a framework, so a
worker loads none.

Examples
--------
>>> task = Task(kind="run", target="foundations.time_value",
...     payload=b'{"calculation": "present_value", "rate": 0.05, "periods": 10,'
...     b' "future_value": 100}')
>>> outcome = execute(task)
>>> outcome.problem is None, outcome.body.startswith(b'{"inputs":')
(True, True)
>>> execute(Task(kind="run", target="no.such_model")).problem.slug
'model-not-found'
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, Literal

from pyeconomics.core.binding import DEFAULT_PROFILE
from pyeconomics.core.canonical import canonical_json
from pyeconomics.server import formats
from pyeconomics.surfaces.problems import FieldError, Problem, problem_for

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "SERIES_OPTIONS",
    "Outcome",
    "Task",
    "TaskKind",
    "decode_outcome",
    "decode_task",
    "encode_outcome",
    "encode_task",
    "execute",
]

#: What a task does.
TaskKind = Literal["run", "series"]
#: The options of a series task: ``data.get``'s, as text.
SERIES_OPTIONS: Final = ("start", "end", "as_of", "vintage", "provider")


@dataclass(frozen=True, slots=True, kw_only=True)
class Task:
    """A run or a series to execute, as plain values.

    Attributes
    ----------
    kind
        ``run`` or ``series``.
    target
        The model's canonical id, or the series' concept id or
        ``provider:series``.
    export_format
        The format of the body (:data:`~pyeconomics.server.formats.RUN_FORMATS`).
    bind
        A run's bind request as
        :meth:`~pyeconomics.surfaces.invoke.BindRequest.to_dict` gives it, or
        ``None`` for a run on its inputs alone.
    query
        A series' options (:data:`SERIES_OPTIONS`), as the text the caller sent.
    payload
        A run's inputs: the JSON bytes the caller sent, or ``None``.
    budget
        The wall-clock seconds the task may take in a worker, or ``None``.
    """

    kind: TaskKind
    target: str
    export_format: str = formats.DEFAULT_FORMAT
    bind: Mapping[str, Any] | None = None
    query: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))
    payload: bytes | None = None
    budget: float | None = None


@dataclass(frozen=True, slots=True)
class Outcome:
    """What a task produced: a body, or a problem and the error's type name."""

    body: bytes = b""
    problem: Problem | None = None
    error_name: str = ""

    @classmethod
    def failed(cls, error: BaseException) -> Outcome:
        """Return the outcome of a task that raised ``error``."""
        return cls(problem=problem_for(error), error_name=type(error).__qualname__)


def _run(task: Task) -> bytes:
    from pyeconomics.surfaces.invoke import BindRequest, invoke  # noqa: PLC0415

    request = None
    if task.bind is not None:
        values = task.bind
        request = BindRequest(
            as_of=values.get("as_of"),
            vintage=values.get("vintage"),
            profile=values.get("profile") or DEFAULT_PROFILE,
            concepts=values.get("concepts") or {},
            parameters=values.get("parameters") or {},
        )
    result = invoke(task.target, task.payload, bind=request)
    return formats.render_result(result, task.export_format, request)


def _series(task: Task) -> bytes:
    from pyeconomics.core import _fields as f  # noqa: PLC0415
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    def day(name: str) -> Any:  # noqa: ANN401 - a date or None
        text = task.query.get(name)
        return None if text is None else f.parse_day(text, name)

    resolved = api.get(
        task.target,
        start=day("start"),
        end=day("end"),
        as_of=day("as_of"),
        vintage=task.query.get("vintage"),
        provider=task.query.get("provider"),
    )
    return formats.render_data(resolved, task.export_format)


def execute(task: Task) -> Outcome:
    """Run a task and render its body; any error becomes the outcome's problem."""
    try:
        body = _run(task) if task.kind == "run" else _series(task)
    except Exception as error:  # noqa: BLE001 - every failure becomes a problem
        return Outcome.failed(error)
    return Outcome(body=body)


# --- the messages between the app and a worker ---------------------------------


def encode_task(task: Task) -> tuple[bytes, bytes]:
    """Return a task as its two frames: a JSON header and the inputs' bytes."""
    header = {
        "kind": task.kind,
        "target": task.target,
        "format": task.export_format,
        "bind": None if task.bind is None else dict(task.bind),
        "query": dict(task.query),
        "inputs": task.payload is not None,
    }
    return canonical_json(header), task.payload or b""


def decode_task(header: bytes, payload: bytes) -> Task:
    """Return the task two frames describe; the budget stays with the pool."""
    values = json.loads(header)
    return Task(
        kind=values["kind"],
        target=values["target"],
        export_format=values["format"],
        bind=values["bind"],
        query=MappingProxyType(dict(values["query"])),
        payload=payload if values["inputs"] else None,
    )


def encode_outcome(outcome: Outcome) -> tuple[bytes, bytes]:
    """Return an outcome as its two frames: a JSON header and the body's bytes."""
    problem = outcome.problem
    header: dict[str, object] = {"error": outcome.error_name, "problem": None}
    if problem is not None:
        header["problem"] = {
            "slug": problem.slug,
            "title": problem.title,
            "status": problem.status,
            "detail": problem.detail,
            "exit_code": problem.exit_code,
            "errors": [error.to_dict() for error in problem.errors],
            "licence": problem.licence,
            "terms": problem.terms,
            "retry_after": problem.retry_after,
        }
    return canonical_json(header), outcome.body


def decode_outcome(header: bytes, body: bytes) -> Outcome:
    """Return the outcome two frames describe."""
    values = json.loads(header)
    sent = values["problem"]
    if sent is None:
        return Outcome(body=body)
    problem = Problem(
        slug=sent["slug"],
        title=sent["title"],
        status=sent["status"],
        detail=sent["detail"],
        exit_code=sent["exit_code"],
        errors=tuple(
            FieldError(
                location=tuple(error["loc"]),
                message=error["msg"],
                error_type=error["type"],
            )
            for error in sent["errors"]
        ),
        licence=sent["licence"],
        terms=sent["terms"],
        retry_after=sent["retry_after"],
    )
    return Outcome(problem=problem, error_name=values["error"])
