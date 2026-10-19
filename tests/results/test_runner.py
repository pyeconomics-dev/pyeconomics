# tests/results/test_runner.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``run``, ``run_batch`` and the results they return."""

from __future__ import annotations

import dataclasses
import itertools
import sys
import warnings
from typing import TYPE_CHECKING, Any

import pandas as pd
import pytest
import toy_models as tm
import toy_results_models as rm

import pyeconomics
from pyeconomics.core import (
    MAX_BATCH_ROWS,
    ConvergenceError,
    DomainError,
    InputError,
    MissingOptionalDependencyError,
    ModelNotFoundError,
    PyeconomicsDeprecationWarning,
    Registry,
    Result,
    canonical_json,
    run_model,
    run_model_batch,
)
from pyeconomics.core import registry as core_registry

if TYPE_CHECKING:
    from collections.abc import Iterator

ZERO = {"face_value": 100, "rate": 0.05, "years": 10}
ZERO_ID = "fixed_income.toy_zero_coupon"


@pytest.fixture(autouse=True)
def installed_toys(monkeypatch: pytest.MonkeyPatch) -> Registry:
    """Make the toy models the installed registry, as an entry point would."""
    registry = Registry.from_models(
        *tm.ALL_MODELS, *rm.ALL_MODELS, distribution="toy-dist", extras=tm.EXTRAS
    )
    monkeypatch.setattr(core_registry._CACHE, "registry", registry)  # noqa: SLF001
    return registry


# --- run ------------------------------------------------------------------------


def test_run_returns_a_result_with_inputs_outputs_warnings_and_manifest() -> None:
    result = pyeconomics.run(ZERO_ID, **ZERO)
    assert isinstance(result, Result)
    assert result.model_id == ZERO_ID
    assert result.model_version == 1
    assert result.inputs.face_value == 100
    assert result.outputs.price == pytest.approx(100 / 1.05**10)
    assert result.warnings == ()
    assert result.manifest.model_id == ZERO_ID
    assert result.manifest.data_sources == ()  # it read no data: no binding, no record


def test_inputs_may_be_a_mapping_an_input_model_or_keywords() -> None:
    by_keywords = pyeconomics.run(ZERO_ID, **ZERO)
    by_mapping = pyeconomics.run(ZERO_ID, ZERO)
    by_model = pyeconomics.run(ZERO_ID, tm.ZeroCouponInputs(**ZERO))
    assert by_keywords == by_mapping == by_model
    assert by_keywords.to_json() == by_mapping.to_json() == by_model.to_json()


def test_inputs_and_keywords_together_are_refused() -> None:
    with pytest.raises(TypeError, match="not both"):
        pyeconomics.run(ZERO_ID, ZERO, rate=0.04)


def test_two_runs_give_identical_bytes_and_hashes() -> None:
    first = pyeconomics.run(ZERO_ID, **ZERO)
    second = pyeconomics.run(ZERO_ID, **ZERO)
    assert first.to_json().encode() == second.to_json().encode()
    assert first.manifest == second.manifest
    assert first.manifest.result_sha256 == second.manifest.result_sha256
    assert first.manifest.inputs_sha256 == second.manifest.inputs_sha256


def test_different_inputs_give_different_hashes() -> None:
    first = pyeconomics.run(ZERO_ID, **ZERO)
    second = pyeconomics.run(ZERO_ID, **{**ZERO, "rate": 0.04})
    assert first.manifest.inputs_sha256 != second.manifest.inputs_sha256
    assert first.manifest.result_sha256 != second.manifest.result_sha256


def test_equivalent_spellings_of_the_inputs_hash_alike() -> None:
    # 100 and 100.0, and a dict in another order, validate to the same inputs.
    a = pyeconomics.run(ZERO_ID, face_value=100, rate=0.05, years=10)
    b = pyeconomics.run(ZERO_ID, years=10.0, rate=0.05, face_value=100.0)
    assert a.manifest.inputs_sha256 == b.manifest.inputs_sha256
    assert a.to_json() == b.to_json()


def test_an_unknown_id_names_close_matches() -> None:
    with pytest.raises(ModelNotFoundError, match="toy_zero_coupon"):
        pyeconomics.run("fixed_income.toy_zero_coupo", **ZERO)


def test_an_alias_warns_and_runs_the_canonical_model() -> None:
    inputs = {
        "calculation": "present_value",
        "future_value": 100,
        "rate": 0.05,
        "years": 10,
    }
    with pytest.warns(PyeconomicsDeprecationWarning) as caught:
        result = pyeconomics.run("foundations.toy_tvm", inputs)
    assert result.model_id == "foundations.toy_time_value"
    assert caught[0].filename == __file__  # points at the caller of run
    with pytest.warns(PyeconomicsDeprecationWarning):
        batch = pyeconomics.run_batch("foundations.toy_tvm", [inputs])
    assert batch.model_id == "foundations.toy_time_value"


def test_invalid_inputs_raise_input_error() -> None:
    with pytest.raises(InputError, match="face_value"):
        pyeconomics.run(ZERO_ID, **{**ZERO, "face_value": -1})
    with pytest.raises(InputError, match="rate"):
        pyeconomics.run(ZERO_ID, **{**ZERO, "rate": float("nan")})
    with pytest.raises(InputError, match="extra"):
        pyeconomics.run(ZERO_ID, **ZERO, surprise=1)


def test_model_errors_propagate_unchanged() -> None:
    with pytest.raises(DomainError, match="no defined result"):
        pyeconomics.run("foundations.toy_failing", x=1, mode="domain")
    with pytest.raises(ConvergenceError, match="no root"):
        pyeconomics.run("foundations.toy_failing", x=1, mode="convergence")
    with pytest.raises(MissingOptionalDependencyError, match="pyeconomics\\[toy\\]"):
        pyeconomics.run("econometrics.toy_extra", **ZERO)


def test_an_out_of_bounds_output_is_a_model_bug_not_an_input_error() -> None:
    from pydantic import ValidationError  # noqa: PLC0415

    with pytest.raises(ValidationError):
        pyeconomics.run("foundations.toy_failing", x=1, mode="bad_output")


def test_warnings_are_collected_into_the_result_not_raised() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # a leaked warning would raise
        result = pyeconomics.run("foundations.toy_mean_return", returns=[0, 0])
    assert [(w.code, w.message) for w in result.warnings] == [
        ("all_zero", "every return is zero")
    ]
    assert result.to_dict()["warnings"] == [
        {"code": "all_zero", "message": "every return is zero"}
    ]


def test_warnings_are_part_of_the_result_hash() -> None:
    quiet = pyeconomics.run("foundations.toy_mean_return", returns=[0.1])
    loud = pyeconomics.run("foundations.toy_mean_return", returns=[0, 0])
    assert quiet.warnings == ()
    assert loud.manifest.result_sha256 != quiet.manifest.result_sha256


def test_a_null_output_and_its_warning() -> None:
    result = pyeconomics.run("foundations.toy_dated", start="2026-01-31", days=0)
    assert result.outputs.per_day is None
    assert [w.code for w in result.warnings] == ["zero_days"]
    assert result.to_dict()["outputs"]["per_day"] is None
    assert b'"per_day":null' in result.to_json().encode()


def test_dates_are_iso_strings_in_json_and_dates_in_the_result() -> None:
    result = pyeconomics.run("foundations.toy_dated", start="2026-01-31", days=30)
    assert str(result.outputs.end) == "2026-03-02"
    outputs = result.to_dict()["outputs"]
    assert outputs["end"] == "2026-03-02"
    assert outputs["dates"] == ["2026-01-31", "2026-03-02"]


def test_a_result_is_immutable() -> None:
    result = pyeconomics.run(ZERO_ID, **ZERO)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.outputs = result.inputs  # type: ignore[misc]  # ty: ignore[invalid-assignment]
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.manifest.seed = 3  # type: ignore[misc]  # ty: ignore[invalid-assignment]
    with pytest.raises((TypeError, ValueError)):
        result.outputs.price = 0.0
    with pytest.raises(TypeError):
        result.manifest.dependencies["numpy"] = "0"  # type: ignore[index]  # ty: ignore[invalid-assignment]
    assert isinstance(result.warnings, tuple)
    assert isinstance(result.manifest.data_sources, tuple)


def test_the_result_dict_is_json_ready() -> None:
    result = pyeconomics.run(ZERO_ID, **ZERO)
    data = result.to_dict()
    assert set(data) == {
        "model_id",
        "model_version",
        "inputs",
        "outputs",
        "warnings",
        "manifest",
    }
    assert canonical_json(data) == result.to_json().encode()


def test_run_model_runs_a_model_object_that_is_not_registered() -> None:
    result = run_model(rm.noisy, seed=7, n=5)
    assert result.model_id == "foundations.toy_noisy"
    assert result.model is rm.noisy


def test_a_stochastic_model_records_its_seed_and_bit_generator() -> None:
    first = pyeconomics.run("foundations.toy_noisy", seed=7, n=5)
    again = pyeconomics.run("foundations.toy_noisy", seed=7, n=5)
    other = pyeconomics.run("foundations.toy_noisy", seed=8, n=5)
    assert (first.manifest.seed, first.manifest.bit_generator) == (7, "PCG64")
    assert first.to_json() == again.to_json()
    assert first.outputs.mean != other.outputs.mean
    default = pyeconomics.run("foundations.toy_noisy")
    assert default.manifest.seed == 0  # the documented default is recorded
    plain = pyeconomics.run(ZERO_ID, **ZERO)
    assert plain.manifest.seed is None
    assert plain.manifest.bit_generator is None


def test_a_field_named_seed_that_is_not_an_integer_seed_is_not_recorded() -> None:
    from pyeconomics.core.manifest import Manifest  # noqa: PLC0415

    for seed in (True, -1, 2**53, "7", None):
        manifest = Manifest.create(
            model_id="a.b", model_version=1, inputs={"seed": seed}, body={}
        )
        assert (manifest.seed, manifest.bit_generator) == (None, None)


# --- run_batch ------------------------------------------------------------------

ROWS = [
    {"face_value": 100, "rate": 0.05, "years": 10},
    {"face_value": 200, "rate": 0.04, "years": 5},
    {"face_value": 300, "rate": 0.03, "years": 2},
]


def test_run_batch_over_an_iterable_of_mappings() -> None:
    batch = pyeconomics.run_batch(ZERO_ID, iter(ROWS))
    assert len(batch) == 3
    assert [r.outputs.price for r in batch] == pytest.approx(
        [100 / 1.05**10, 200 / 1.04**5, 300 / 1.03**2]
    )
    assert batch.results[0] == pyeconomics.run(ZERO_ID, **ROWS[0])
    assert batch.model_id == ZERO_ID


def test_run_batch_over_a_pandas_dataframe() -> None:
    frame = pd.DataFrame(ROWS)
    batch = pyeconomics.run_batch(ZERO_ID, frame)
    assert [r.to_json() for r in batch] == [
        pyeconomics.run(ZERO_ID, **row).to_json() for row in ROWS
    ]


def test_run_batch_over_a_polars_dataframe() -> None:
    polars = pytest.importorskip("polars")
    batch = pyeconomics.run_batch(ZERO_ID, polars.DataFrame(ROWS))
    assert len(batch) == 3
    assert batch.results[1].inputs.face_value == 200


def test_run_batch_over_an_arrow_table_and_a_stream() -> None:
    pyarrow = pytest.importorskip("pyarrow")
    table = pyarrow.Table.from_pylist(ROWS)
    assert len(pyeconomics.run_batch(ZERO_ID, table)) == 3

    class Streams:
        """Anything exposing the Arrow PyCapsule stream interface."""

        def __arrow_c_stream__(self, requested_schema: object = None) -> object:
            return table.__arrow_c_stream__(requested_schema)

    batch = pyeconomics.run_batch(ZERO_ID, Streams())
    assert [r.outputs.price for r in batch] == [
        r.outputs.price for r in pyeconomics.run_batch(ZERO_ID, ROWS)
    ]


def test_run_batch_over_arrow_without_pyarrow_names_the_package(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Streams:
        def __arrow_c_stream__(self, requested_schema: object = None) -> object:
            raise AssertionError  # pragma: no cover - never reached

    monkeypatch.setitem(sys.modules, "pyarrow", None)
    with pytest.raises(MissingOptionalDependencyError, match="pyarrow"):
        pyeconomics.run_batch(ZERO_ID, Streams())


def test_a_union_model_batches_rows_of_different_calculations() -> None:
    rows = [
        {"calculation": "present_value", "future_value": 100, "rate": 0.05, "years": 2},
        {"calculation": "future_value", "present_value": 100, "rate": 0.05, "years": 2},
    ]
    batch = pyeconomics.run_batch("foundations.toy_time_value", rows)
    assert [r.outputs.calculation for r in batch] == ["present_value", "future_value"]


def test_an_empty_batch_is_empty() -> None:
    batch = pyeconomics.run_batch(ZERO_ID, [])
    assert len(batch) == 0
    assert batch.to_pandas().columns.tolist() == ["result_sha256"]


def test_a_batch_is_bounded_before_any_row_runs() -> None:
    assert MAX_BATCH_ROWS == 100_000
    calls: list[int] = []

    def counting_rows() -> Iterator[dict[str, Any]]:
        for index in itertools.count():  # an endless generator
            calls.append(index)
            yield ROWS[0]

    with pytest.raises(InputError, match="at most 100000 rows"):
        pyeconomics.run_batch(ZERO_ID, counting_rows())
    assert len(calls) == MAX_BATCH_ROWS + 1  # it read one past the bound, no more
    too_many = pd.DataFrame({"face_value": [1.0] * (MAX_BATCH_ROWS + 1)})
    with pytest.raises(InputError, match="at most 100000 rows"):
        pyeconomics.run_batch(ZERO_ID, too_many)


def test_the_bound_applies_to_polars_and_arrow_too() -> None:
    polars = pytest.importorskip("polars")
    pyarrow = pytest.importorskip("pyarrow")
    rows = {"face_value": [1.0] * (MAX_BATCH_ROWS + 1)}
    with pytest.raises(InputError, match="at most 100000 rows"):
        pyeconomics.run_batch(ZERO_ID, polars.DataFrame(rows))
    with pytest.raises(InputError, match="at most 100000 rows"):
        pyeconomics.run_batch(ZERO_ID, pyarrow.table(rows))


def test_a_batch_of_exactly_the_bound_is_accepted() -> None:
    rows = itertools.repeat({"x": 0.5}, MAX_BATCH_ROWS)
    batch = run_model_batch(rm.failing, rows)
    assert len(batch) == MAX_BATCH_ROWS


def test_a_bad_row_is_named_in_a_note() -> None:
    rows = [ROWS[0], {**ROWS[1], "rate": 99}, ROWS[2]]
    with pytest.raises(InputError, match="rate") as caught:
        pyeconomics.run_batch(ZERO_ID, rows)
    assert "in row 1 of the batch" in caught.value.__notes__
    with pytest.raises(DomainError) as domain:
        pyeconomics.run_batch(
            "foundations.toy_failing",
            [{"x": 1}, {"x": 1}, {"x": 1, "mode": "domain"}],
        )
    assert domain.value.__notes__ == ["in row 2 of the batch"]


def test_rows_must_be_mappings_and_the_source_iterable() -> None:
    with pytest.raises(InputError, match="row 1 is a list"):
        pyeconomics.run_batch(ZERO_ID, [ROWS[0], [1, 2, 3]])
    with pytest.raises(InputError, match="not one mapping"):
        pyeconomics.run_batch(ZERO_ID, ROWS[0])
    with pytest.raises(InputError, match="not int"):
        pyeconomics.run_batch(ZERO_ID, 5)
