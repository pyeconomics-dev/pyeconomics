# tests/registry/test_warning_context.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``warn()``: recorded in a run's collector, else issued as a warning."""

from __future__ import annotations

import contextvars
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

import pytest

from pyeconomics import core
from pyeconomics.core import (
    ModelWarning,
    collect_warnings,
    find_root,
    library_warnings,
    warn,
)


def test_there_is_exactly_one_warn() -> None:
    from pyeconomics.core import context  # noqa: PLC0415 - the module, by path

    assert core.warn is context.warn
    assert not hasattr(core.warnings, "warn")


def test_outside_a_run_the_warning_goes_through_the_warnings_module() -> None:
    with pytest.warns(ModelWarning, match="the Sharpe ratio") as caught:
        warn("zero_volatility", "the Sharpe ratio is undefined")
    assert isinstance(caught[0].message, ModelWarning)
    assert caught[0].message.code == "zero_volatility"
    assert caught[0].filename == __file__


def helper_that_warns(stacklevel: int) -> None:
    warn("from_helper", "inside a helper", stacklevel=stacklevel)


def test_stacklevel_counts_from_the_code_that_calls_warn() -> None:
    with pytest.warns(ModelWarning) as at_helper:
        helper_that_warns(1)
    assert at_helper[0].lineno != 0
    assert at_helper[0].filename == __file__
    with pytest.warns(ModelWarning) as at_caller:
        helper_that_warns(2)
    assert at_caller[0].filename == __file__
    assert at_caller[0].lineno != at_helper[0].lineno


def test_inside_a_run_the_warning_is_recorded_and_not_issued() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # an issued warning would raise
        with collect_warnings() as recorded:
            warn("zero_volatility", "the Sharpe ratio is undefined")
            warn("several_roots", "two roots")
    assert [(w.code, w.text) for w in recorded] == [
        ("zero_volatility", "the Sharpe ratio is undefined"),
        ("several_roots", "two roots"),
    ]
    assert all(isinstance(w, ModelWarning) for w in recorded)


def test_collectors_nest_and_restore_the_outer_one() -> None:
    with collect_warnings() as outer:
        warn("before", "first")
        with collect_warnings() as inner:
            warn("inside", "second")
        warn("after", "third")
    assert [w.code for w in outer] == ["before", "after"]
    assert [w.code for w in inner] == ["inside"]


def test_the_collector_is_removed_after_the_block() -> None:
    with collect_warnings():
        pass
    with pytest.warns(ModelWarning):
        warn("outside", "no collector is active")


def fail_inside_a_run() -> None:
    with collect_warnings():
        msg = "boom"
        raise RuntimeError(msg)


def test_the_collector_is_removed_when_the_block_raises() -> None:
    with pytest.raises(RuntimeError):
        fail_inside_a_run()
    with pytest.warns(ModelWarning):
        warn("outside", "no collector is active")


def test_a_code_must_be_snake_case_even_inside_a_run() -> None:
    with collect_warnings() as recorded, pytest.raises(ValueError, match="snake_case"):
        warn("Not Snake", "bad code")
    assert recorded == []


def test_a_thread_has_its_own_context() -> None:
    seen: list[str] = []

    def in_thread() -> None:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            warn("from_thread", "issued, not recorded")
        seen.extend(str(w.message) for w in caught)

    with collect_warnings() as recorded:
        thread = threading.Thread(target=in_thread)
        thread.start()
        thread.join()
    assert recorded == []
    assert len(seen) == 1
    assert "[from_thread]" in seen[0]


def test_a_copied_context_keeps_the_collector() -> None:
    with collect_warnings() as recorded:
        contextvars.copy_context().run(warn, "copied", "inside a copied context")
    assert [w.code for w in recorded] == ["copied"]


def test_concurrent_threads_each_record_into_their_own_collector() -> None:
    def task(name: str) -> list[str]:
        with collect_warnings() as recorded:
            warn(name, f"from {name}")
            time.sleep(0.01)  # let the other threads install their collectors
            warn(name, f"again from {name}")
        return [w.code for w in recorded]

    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(task, [f"task_{i}" for i in range(5)]))
    assert results == [[f"task_{i}", f"task_{i}"] for i in range(5)]


def test_find_root_warns_into_the_collector() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        with collect_warnings() as recorded:
            result = find_root(lambda x: (x - 1.0) * (x - 2.0) * (x - 3.0), 0.5, 3.6)
    assert result.candidates == 3
    assert [w.code for w in recorded] == ["several_roots"]


def test_find_root_warns_through_warnings_outside_a_run() -> None:
    with pytest.warns(ModelWarning, match="several_roots"):
        find_root(lambda x: (x - 1.0) * (x - 2.0) * (x - 3.0), 0.5, 3.6)


# --- a library's warnings (Phase 3 Step 17) -----------------------------------------


def test_library_warnings_become_the_models_own_once_each() -> None:
    codes = {"UserWarning": "toy_code"}
    with collect_warnings() as recorded, library_warnings("toylib", codes=codes):
        warnings.warn("rank deficient", RuntimeWarning, stacklevel=1)
        warnings.warn("rank   deficient", RuntimeWarning, stacklevel=1)
        warnings.warn("did not converge", UserWarning, stacklevel=1)
    assert [(w.code, w.text) for w in recorded] == [
        ("toylib_warning", "toylib: RuntimeWarning: rank deficient"),
        ("toy_code", "toylib: UserWarning: did not converge"),
    ]


def test_library_warnings_pass_a_model_warning_through() -> None:
    with warnings.catch_warnings(record=True) as outside:
        warnings.simplefilter("always")
        # Outside a run, warn() issues through the warnings module: the block
        # catches it and must hand it on, not swallow it.
        with library_warnings("toylib"):
            warn("own_code", "the model's own warning")
    assert [w.message.code for w in outside] == ["own_code"]  # type: ignore[union-attr]


def test_library_warnings_record_nothing_when_the_block_raises() -> None:
    def failing() -> None:
        with library_warnings("toylib"):
            warnings.warn("ignored", RuntimeWarning, stacklevel=1)
            msg = "boom"
            raise ValueError(msg)

    with collect_warnings() as recorded, pytest.raises(ValueError, match="boom"):
        failing()
    assert recorded == []


def test_a_caller_may_drop_a_warning_it_has_shown_harmless() -> None:
    with collect_warnings() as recorded, library_warnings("toylib") as caught:
        warnings.warn("casting complex", RuntimeWarning, stacklevel=1)
        warnings.warn("kept", UserWarning, stacklevel=1)
        caught[:] = [w for w in caught if "complex" not in str(w.message)]
    assert [w.text for w in recorded] == ["toylib: UserWarning: kept"]
