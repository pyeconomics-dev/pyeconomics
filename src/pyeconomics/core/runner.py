# src/pyeconomics/core/runner.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Running models: ``run`` and ``run_batch`` (re-exported by ``pyeconomics``).

:func:`run_model` validates the inputs, runs the model's ``compute`` with a
warning collector installed, validates the outputs and returns a
:class:`~pyeconomics.core.results.Result`. :func:`run` first looks the model up by
id in the installed registry (an alias warns and resolves to the canonical model).
:class:`~pyeconomics.core.errors.InputError`, ``DomainError`` and
``ConvergenceError`` propagate unchanged. A model's data is bound first
(``pyeconomics.bind``) and the :class:`~pyeconomics.core.binding.Bound` it returns
is run like any inputs: the result's manifest then records every series,
vintage and retrieval time.

:func:`run_batch` evaluates a scalar model over the rows of a table: a pandas or
Polars DataFrame, anything exposing the Arrow PyCapsule stream interface, or an
iterable of mappings. A batch holds at most :data:`MAX_BATCH_ROWS` rows, so it is
never an unbounded workload; a longer one is refused before any row runs.

Examples
--------
>>> from pyeconomics.core.runner import MAX_BATCH_ROWS
>>> MAX_BATCH_ROWS
100000
"""

from __future__ import annotations

import itertools
from collections.abc import Iterable, Mapping
from typing import TYPE_CHECKING, Any, Final, cast

import pandas as pd

from pyeconomics.core._optional import import_optional
from pyeconomics.core.binding import REVISED_DATA, Bound
from pyeconomics.core.context import collect_warnings
from pyeconomics.core.errors import InputError
from pyeconomics.core.results import BatchResult, Result, ResultWarning

if TYPE_CHECKING:
    from collections.abc import Iterator, Sized

    from pyeconomics.core.model import Model

__all__ = ["MAX_BATCH_ROWS", "run", "run_batch", "run_model", "run_model_batch"]

#: The most rows one ``run_batch`` call accepts.
MAX_BATCH_ROWS: Final = 100_000


def run_model(
    model: Model[Any, Any], inputs: object = None, /, **fields: object
) -> Result[Any, Any]:
    """Run a model object and return its :class:`~pyeconomics.core.results.Result`.

    Parameters
    ----------
    model
        The model to run.
    inputs
        An input model instance or a mapping of field values; a
        :class:`~pyeconomics.core.binding.Bound` from ``pyeconomics.bind``, whose
        data records go into the result's manifest; or leave it out and pass the
        fields as keywords.
    **fields
        The input fields as keywords.

    Raises
    ------
    InputError
        If the inputs fail validation, or a ``Bound`` was bound for another model.
    TypeError
        If both ``inputs`` and keyword fields are given.
    DomainError, ConvergenceError
        As the model raises them.
    """
    validated = model.parse_inputs(inputs, **fields)
    with collect_warnings() as recorded:
        raw = model.compute(validated)
    outputs = model.validate_outputs(raw)
    warnings = [ResultWarning(w.code, w.text) for w in recorded]
    if not isinstance(inputs, Bound):
        return Result.build(model, validated, outputs, warnings)
    if inputs.revised:
        warnings.append(_revised_warning(inputs.revised))
    return Result.build(model, validated, outputs, warnings, inputs.sources)


def _revised_warning(fields: tuple[str, ...]) -> ResultWarning:
    """Say which inputs are revised data: nothing passes it off as real-time."""
    names = ", ".join(fields)
    return ResultWarning(
        REVISED_DATA,
        f"The values of {names} are revised data: the latest values, not those "
        "published on the evaluation date, so a historical evaluation on them uses "
        "information that was not yet available.",
    )


def run(model_id: str, inputs: object = None, /, **fields: object) -> Result[Any, Any]:
    """Run the registered model ``model_id`` and return its result.

    An alias of a renamed model warns with ``PyeconomicsDeprecationWarning`` and
    runs the canonical model; the result carries the canonical id.

    Parameters
    ----------
    model_id
        A model id or alias.
    inputs
        An input model instance or a mapping of field values; a
        :class:`~pyeconomics.core.binding.Bound` from ``pyeconomics.bind``; or
        leave it out and pass the fields as keywords.
    **fields
        The input fields as keywords.

    Raises
    ------
    ModelNotFoundError
        If no model or alias has the id.
    InputError
        If the inputs fail validation, or a ``Bound`` was bound for another
        model.
    DomainError, ConvergenceError
        As the model raises them.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - avoids a cycle

    model = installed().resolve(model_id, stacklevel=3)
    return run_model(model, inputs, **fields)


def _arrow_rows(source: object) -> Iterator[Mapping[str, object]]:
    """Read rows from an Arrow stream, stopping once the batch is too long."""
    pyarrow = import_optional("pyarrow")
    reader = pyarrow.RecordBatchReader.from_stream(source)
    seen = 0
    for batch in reader:
        seen += batch.num_rows
        if seen > MAX_BATCH_ROWS:
            raise _refuse()
        yield from batch.to_pylist()


def _refuse() -> InputError:
    return InputError(f"run_batch accepts at most {MAX_BATCH_ROWS} rows")


def _rows(rows: object) -> list[object]:
    """Read at most :data:`MAX_BATCH_ROWS` rows from a table or an iterable."""
    source: Iterable[object]
    iter_rows = getattr(rows, "iter_rows", None)  # a Polars DataFrame
    if isinstance(rows, pd.DataFrame):
        if len(rows) > MAX_BATCH_ROWS:
            raise _refuse()
        source = rows.to_dict("records")
    elif callable(iter_rows):
        if len(cast("Sized", rows)) > MAX_BATCH_ROWS:
            raise _refuse()
        source = cast("Iterable[object]", iter_rows(named=True))
    elif hasattr(rows, "__arrow_c_stream__"):
        source = _arrow_rows(rows)
    elif isinstance(rows, Mapping):
        msg = "run_batch takes a table or an iterable of mappings, not one mapping"
        raise InputError(msg)
    elif isinstance(rows, Iterable):
        source = rows
    else:
        kind = type(rows).__name__
        msg = f"run_batch needs a table or an iterable of mappings, not {kind}"
        raise InputError(msg)
    taken = list(itertools.islice(source, MAX_BATCH_ROWS + 1))
    if len(taken) > MAX_BATCH_ROWS:
        raise _refuse()
    return taken


def run_model_batch(model: Model[Any, Any], rows: object) -> BatchResult:
    """Run a model object over the rows of a table; see :func:`run_batch`."""
    results = []
    for index, row in enumerate(_rows(rows)):
        if not isinstance(row, Mapping):
            msg = f"row {index} is a {type(row).__name__}, not a mapping of fields"
            raise InputError(msg)
        try:
            results.append(run_model(model, dict(row)))
        except Exception as error:
            error.add_note(f"in row {index} of the batch")
            raise
    return BatchResult(model.id, model.version, tuple(results))


def run_batch(model_id: str, rows: object) -> BatchResult:
    """Run the registered model ``model_id`` once per row of a table.

    Parameters
    ----------
    model_id
        A model id or alias.
    rows
        A pandas or Polars DataFrame, any object exposing the Arrow PyCapsule
        stream interface (this needs ``pyarrow``), or an iterable of mappings.
        Each row holds one run's input fields; at most
        :data:`MAX_BATCH_ROWS` rows.

    Returns
    -------
    BatchResult
        The rows' results, with ``to_pandas``, ``to_polars`` and ``to_arrow``.

    Raises
    ------
    InputError
        For more than :data:`MAX_BATCH_ROWS` rows, a row that is not a mapping
        or fails validation. The error carries a note naming the row.
    DomainError, ConvergenceError
        As the model raises them, with a note naming the row.
    ModelNotFoundError
        If no model or alias has the id.
    """
    from pyeconomics.core.registry import installed  # noqa: PLC0415 - avoids a cycle

    model = installed().resolve(model_id, stacklevel=3)
    return run_model_batch(model, rows)
