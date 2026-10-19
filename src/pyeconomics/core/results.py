# src/pyeconomics/core/results.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Results: what a model run returns, with the provenance to reproduce it.

A :class:`Result` is immutable and holds the validated inputs, the validated
outputs, the warnings the run recorded and a
:class:`~pyeconomics.core.manifest.Manifest`. Its canonical JSON
(:meth:`Result.to_json`) is the same bytes on every run of the same inputs and
the same data records in the same environment, which is what the cross-surface
parity tests compare. A
:class:`BatchResult` is the same for many input rows.

Build results with :func:`pyeconomics.run` and :func:`pyeconomics.run_batch`
(or :func:`~pyeconomics.core.runner.run_model` for a model object).

Examples
--------
>>> from pyeconomics.core.results import Result
>>> hasattr(Result, "to_json"), hasattr(Result, "plot")
(True, True)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from pyeconomics.core import tables
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.manifest import Manifest
from pyeconomics.core.model import Model, ModelInputs, ModelOutputs
from pyeconomics.core.provenance import LicenceClass

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Sequence
    from os import PathLike

    import pandas as pd

    from pyeconomics.core.cards import ModelCard
    from pyeconomics.core.provenance import DataSource

__all__ = ["BatchResult", "Result", "ResultWarning"]


@dataclass(frozen=True, slots=True)
class ResultWarning:
    """A warning a run recorded: a stable code and a sentence for people."""

    code: str
    message: str

    def to_dict(self) -> dict[str, str]:
        """Return the warning as JSON-ready values."""
        return {"code": self.code, "message": self.message}


@dataclass(frozen=True, slots=True)
class Result[I: ModelInputs, O: ModelOutputs]:
    """The outcome of one model run.

    Attributes
    ----------
    model_id, model_version
        The model that ran (the canonical id, even if the run named an alias).
    inputs
        The validated inputs, as the model's input class.
    outputs
        The validated outputs, as the model's output class.
    warnings
        The warnings the model recorded through ``pyeconomics.core.warn``.
    manifest
        The provenance and fingerprints, with the records of the data a bound run
        read; see :class:`~pyeconomics.core.manifest.Manifest`.
    model
        The model object, for :meth:`card` and :meth:`plot`.
    """

    model_id: str
    model_version: int
    inputs: I
    outputs: O
    warnings: tuple[ResultWarning, ...]
    manifest: Manifest
    model: Model[I, O] = field(repr=False, compare=False)

    @classmethod
    def build(
        cls,
        model: Model[I, O],
        inputs: I,
        outputs: O,
        warnings: Sequence[ResultWarning] = (),
        data_sources: Iterable[DataSource] = (),
    ) -> Result[I, O]:
        """Assemble a result and its manifest from a run's parts.

        ``data_sources`` are the records of the data a bound run read; they go
        into the manifest, not into the hashed body.
        """
        inputs_json = inputs.model_dump(mode="json")
        body = {
            "model_id": model.id,
            "model_version": model.version,
            "inputs": inputs_json,
            "outputs": outputs.model_dump(mode="json"),
            "warnings": [warning.to_dict() for warning in warnings],
        }
        manifest = Manifest.create(
            model_id=model.id,
            model_version=model.version,
            inputs=inputs_json,
            body=body,
            data_sources=data_sources,
        )
        return cls(
            model_id=model.id,
            model_version=model.version,
            inputs=inputs,
            outputs=outputs,
            warnings=tuple(warnings),
            manifest=manifest,
            model=model,
        )

    def attributions(self) -> tuple[str, ...]:
        """Return the attribution and required notices of the data the run read.

        The texts of the manifest's records, de-duplicated and in record order:
        every attribution first, then every required notice. A value the caller
        supplied needs neither. Exports print these wherever the data appears
        (ADR-0005); a run that read no data returns an empty tuple.
        """
        records = [
            record
            for record in self.manifest.data_sources
            if record.licence is not LicenceClass.USER_SUPPLIED
        ]
        attributions = (record.attribution for record in records)
        notices = (record.notice for record in records if record.notice)
        return tuple(dict.fromkeys((*attributions, *notices)))

    def to_dict(self) -> dict[str, Any]:
        """Return the result as JSON-ready values (dates are ISO 8601 strings)."""
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "inputs": self.inputs.model_dump(mode="json"),
            "outputs": self.outputs.model_dump(mode="json"),
            "warnings": [warning.to_dict() for warning in self.warnings],
            "manifest": self.manifest.to_dict(),
        }

    def to_json(self) -> str:
        """Return the result as canonical JSON (RFC 8785).

        The text is the UTF-8 decoding of
        :func:`~pyeconomics.core.canonical.canonical_json` of :meth:`to_dict`;
        encode it to compare bytes.
        """
        return canonical_json(self.to_dict()).decode("utf-8")

    def to_pandas(self) -> pd.DataFrame:
        """Return a one-row DataFrame; see :mod:`pyeconomics.core.tables`."""
        return tables.to_pandas(tables.columns_of([self]))

    def to_polars(self) -> Any:  # noqa: ANN401 - a polars object
        """Return a one-row Polars DataFrame.

        Raises
        ------
        MissingOptionalDependencyError
            If ``polars`` is not installed.
        """
        return tables.to_polars(tables.columns_of([self]))

    def to_arrow(self) -> Any:  # noqa: ANN401 - a pyarrow object
        """Return a one-row Arrow table whose schema metadata holds the manifest.

        The manifest is canonical JSON under the key ``pyeconomics.manifest``.

        Raises
        ------
        MissingOptionalDependencyError
            If ``pyarrow`` is not installed.
        """
        manifest = canonical_json(self.manifest.to_dict()).decode("utf-8")
        return tables.to_arrow(tables.columns_of([self]), manifest=manifest)

    def to_parquet(self, path: str | PathLike[str]) -> None:
        """Write the result as a Parquet file, with the manifest in its metadata.

        Raises
        ------
        MissingOptionalDependencyError
            If ``pyarrow`` is not installed.
        """
        tables.to_parquet(self.to_arrow(), path)

    def card(self) -> ModelCard:
        """Return the model card of the model that produced this result."""
        from pyeconomics.core.cards import ModelCard  # noqa: PLC0415 - avoids a cycle

        return ModelCard.from_model(self.model)

    def plot(self, chart: str | None = None) -> Any:  # noqa: ANN401 - a Plotly figure
        """Return a Plotly figure of one of the model's charts.

        Parameters
        ----------
        chart
            The id of a chart in the model's specification. It may be left out
            when the model has exactly one chart for this result's calculation.

        Raises
        ------
        MissingOptionalDependencyError
            If Plotly is not installed; install ``pyeconomics[plot]``.
        ValueError
            If the model has no matching chart, or several and none was named.
        """
        from pyeconomics.core.plotting import figure  # noqa: PLC0415 - lazy Plotly

        return figure(self, chart)


@dataclass(frozen=True, slots=True)
class BatchResult:
    """The results of one model over many input rows, in row order."""

    model_id: str
    model_version: int
    results: tuple[Result[Any, Any], ...]

    def __len__(self) -> int:
        """Return the number of rows."""
        return len(self.results)

    def __iter__(self) -> Iterator[Result[Any, Any]]:
        """Iterate over the rows' results."""
        return iter(self.results)

    def to_pandas(self) -> pd.DataFrame:
        """Return a DataFrame: input columns, output columns and result hashes."""
        return tables.to_pandas(tables.columns_of(self.results))

    def to_polars(self) -> Any:  # noqa: ANN401 - a polars object
        """Return a Polars DataFrame; needs ``polars``."""
        return tables.to_polars(tables.columns_of(self.results))

    def to_arrow(self) -> Any:  # noqa: ANN401 - a pyarrow object
        """Return an Arrow table; needs ``pyarrow``."""
        return tables.to_arrow(tables.columns_of(self.results))
