# tests/server/test_server_settings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The server's settings, its messages to workers and its formats (Step 6).

- ``ServerSettings`` refuses a negative worker count, an empty queue and a
  budget that is not a positive number of seconds; the worker count and the
  commit come from the environment when unset; each mode has its budgets.
- A task and an outcome travel to and from a worker as a JSON header and raw
  bytes, and come back equal, a problem's field errors included.
- ``?format=`` values, media types and download names.
- ``create_app`` refuses an unknown mode.
"""

from __future__ import annotations

import math
import os

import pytest

from pyeconomics.core.errors import InputError
from pyeconomics.core.spec import CostClass
from pyeconomics.data.errors import ConfigError
from pyeconomics.server import ServerSettings, create_app, formats
from pyeconomics.server.settings import budgets_for, data_mode, git_sha, worker_count
from pyeconomics.server.work import (
    Outcome,
    Task,
    decode_outcome,
    decode_task,
    encode_outcome,
    encode_task,
    execute,
)
from pyeconomics.surfaces.budgets import HOSTED_BUDGETS
from pyeconomics.surfaces.problems import FieldError, Problem


@pytest.mark.parametrize(
    "fields",
    [
        {"workers": -1},
        {"workers": True},
        {"queue_limit": 0},
        {"budgets": {CostClass.LIGHT: 0}},
        {"budgets": {CostClass.LIGHT: math.inf}},
        {"budgets": {CostClass.LIGHT: True}},
        {"budgets": {CostClass.LIGHT: "1"}},
    ],
)
def test_bad_settings_are_refused(fields: dict[str, object]) -> None:
    with pytest.raises(InputError):
        ServerSettings(**fields)  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


def test_budgets_are_held_by_cost_class() -> None:
    settings = ServerSettings(budgets={"light": 3})  # type: ignore[dict-item] # ty: ignore[invalid-argument-type]
    assert settings.budgets == {CostClass.LIGHT: 3.0}
    assert budgets_for("local", settings) == {CostClass.LIGHT: 3.0}
    assert budgets_for("hosted", ServerSettings()) is HOSTED_BUDGETS
    assert budgets_for("local", ServerSettings()) is None
    assert (data_mode("local"), data_mode("hosted")) == ("library", "hosted")


def test_the_worker_count_comes_from_the_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert worker_count(ServerSettings(workers=3)) == 3
    monkeypatch.setenv("PYECONOMICS_WORKERS", " 2 ")
    assert worker_count(ServerSettings()) == 2
    monkeypatch.setenv("PYECONOMICS_WORKERS", "")
    expected = getattr(os, "process_cpu_count", os.cpu_count)() or 1
    assert worker_count(ServerSettings()) == expected
    monkeypatch.setenv("PYECONOMICS_WORKERS", "-1")
    with pytest.raises(ConfigError, match="PYECONOMICS_WORKERS"):
        worker_count(ServerSettings())


def test_a_commit_is_hexadecimal_or_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    assert git_sha(ServerSettings(git_sha="ABCDEF1")) == "unknown"
    assert git_sha(ServerSettings(git_sha=" abcdef1 ")) == "abcdef1"
    monkeypatch.setenv("PYECONOMICS_GIT_SHA", "/home/someone/repo")
    assert git_sha(ServerSettings()) == "unknown"


def test_create_app_refuses_an_unknown_mode() -> None:
    with pytest.raises(InputError, match="local, hosted"):
        create_app(mode="cloud", settings=ServerSettings(workers=0))  # type: ignore[arg-type] # ty: ignore[invalid-argument-type]


def test_a_task_travels_to_a_worker_unchanged() -> None:
    task = Task(
        kind="series",
        target="oecd:A/B",
        export_format="csv",
        bind={"as_of": "2024-03-20", "concepts": {}, "parameters": {}},
        query={"start": "2024-01-01"},
        payload=b"\x00{}",
        budget=2.0,
    )
    header, payload = encode_task(task)
    assert payload == b"\x00{}"
    back = decode_task(header, payload)
    assert back == Task(
        kind="series",
        target="oecd:A/B",
        export_format="csv",
        bind=task.bind,
        query={"start": "2024-01-01"},
        payload=b"\x00{}",
    )
    none = decode_task(*encode_task(Task(kind="run", target="a.b")))
    assert (none.payload, none.bind) == (None, None)


def test_an_outcome_travels_back_unchanged() -> None:
    problem = Problem(
        slug="invalid-input",
        title="The inputs are not valid",
        status=422,
        detail="rate: too high",
        exit_code=3,
        errors=(FieldError(location=("rate", 0), message="too high", error_type="x"),),
        licence="library-only",
        terms="https://www.example.org/terms",
        retry_after=1.5,
    )
    failed = Outcome(problem=problem, error_name="InputError")
    assert decode_outcome(*encode_outcome(failed)) == failed
    body = Outcome(body=b"\x89PNG")
    assert decode_outcome(*encode_outcome(body)) == body


def test_execute_turns_every_error_into_a_problem() -> None:
    outcome = execute(Task(kind="series", target="https://example.org/x"))
    assert outcome.problem is not None
    assert (outcome.problem.slug, outcome.error_name) == ("invalid-input", "InputError")


def test_formats_name_their_media_types_and_downloads() -> None:
    assert formats.choose(None, formats.RUN_FORMATS) == "json"
    assert formats.choose("bundle", formats.RUN_FORMATS) == "bundle"
    with pytest.raises(InputError, match="json, csv"):
        formats.choose("bundle", formats.SERIES_FORMATS)
    assert set(formats.MEDIA_TYPES) == set(formats.RUN_FORMATS)
    assert set(formats.EXTENSIONS) == set(formats.RUN_FORMATS)
    assert formats.disposition("bundle", "a.b") == 'attachment; filename="a.b.zip"'
    assert formats.file_stem('../"evil"') == "evil"
    assert formats.file_stem("///") == "pyeconomics"
