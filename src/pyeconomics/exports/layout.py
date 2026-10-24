# src/pyeconomics/exports/layout.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What an export writes: a value's rows, its provenance and its metadata.

:func:`subject` reads any exportable value into a :class:`Subject`, which every
writer shares:

- a :class:`~pyeconomics.core.results.Result` is one row and a
  :class:`~pyeconomics.core.results.BatchResult` one row per run, in
  :mod:`pyeconomics.core.tables`' columns (``inputs.<field>``,
  ``outputs.<field>``, ``result_sha256``);
- a data frame (a :class:`~pyeconomics.data.types.Series` or
  :class:`~pyeconomics.data.types.Table`, or what ``data.get`` resolved) is one
  row per observation: ``date``, then ``realtime_start`` and ``realtime_end``
  when it carries vintages, then ``value`` or the table's columns;
- identifier or filing :class:`~pyeconomics.data.records.Records` are one row per
  record.

Its provenance is the attribution and the required notice of every source the
value's data came from (ADR-0005 rule 2), and the terms pages; a value the user
supplied needs none. Its manifest is the result's manifest, or for data the
frame's metadata and source records. The data layer is imported only to export
its values, so exporting a result loads no data module.

Examples
--------
>>> escape_text("=1+1"), escape_text("-3"), escape_text("net")
("'=1+1", "'-3", 'net')
"""

from __future__ import annotations

import datetime as dt
import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final, Literal

from pyeconomics.core import tables
from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError
from pyeconomics.core.provenance import LicenceClass
from pyeconomics.core.results import BatchResult, Result
from pyeconomics.surfaces.documents import jsonable

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence

    from pyeconomics.core.provenance import DataSource

__all__ = [
    "FORMATS",
    "FORMULA_PREFIXES",
    "ExportFormat",
    "Subject",
    "cell_text",
    "escape_text",
    "subject",
]

#: What :func:`~pyeconomics.exports.export` writes.
ExportFormat = Literal["csv", "xlsx", "parquet", "arrow", "json"]
#: Every export format, in the order the documentation lists them.
FORMATS: Final[tuple[ExportFormat, ...]] = ("csv", "xlsx", "parquet", "arrow", "json")

#: The first characters that make a spreadsheet read a text cell as a formula
#: (ROADMAP §5 threat 6); such a cell is written with a leading ``'``.
FORMULA_PREFIXES: Final = ("=", "+", "-", "@", "\t", "\r")

_INDEX_COLUMNS: Final = ("date", "realtime_start", "realtime_end")

SubjectKind = Literal["result", "batch", "frame", "records"]


def escape_text(text: str) -> str:
    """Prefix a text cell with ``'`` when it starts like a formula.

    Only text is escaped: a number is written as a number, so ``-3`` the number
    stays a number and ``"-3"`` the text becomes ``'-3``.
    """
    return f"'{text}" if text.startswith(FORMULA_PREFIXES) else text


def cell_text(value: object) -> str:
    """Return a non-numeric cell value as text, before escaping.

    A date is its ISO 8601 text, an enum its value, and an array or a mapping its
    canonical JSON.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, dt.date):  # a datetime too
        return value.isoformat()
    if isinstance(value, enum.Enum):
        return cell_text(value.value)
    return canonical_json(jsonable(value)).decode("utf-8")


@dataclass(frozen=True, slots=True)
class Subject:
    """An exportable value read for the writers.

    Attributes
    ----------
    kind
        ``result``, ``batch``, ``frame`` or ``records``.
    columns
        The rows as columns of Python values, every column one value per row.
    header
        The metadata lines a CSV export starts with, as ``(label, text)``: the
        package version, the model or the data, the hashes, then every
        attribution, notice and terms page.
    attributions
        Every attribution, then every required notice, de-duplicated in source
        order, as :meth:`~pyeconomics.core.results.Result.attributions` gives them.
    terms
        The terms pages of the sources, de-duplicated.
    manifest
        The manifest as JSON-ready values: a result's own, each run's for a batch,
        the metadata and source records for data.
    document
        The JSON export: canonical JSON with the manifest embedded.
    version
        The pyeconomics version that wrote it.
    """

    kind: SubjectKind
    columns: dict[str, list[object]]
    header: tuple[tuple[str, str], ...]
    attributions: tuple[str, ...]
    terms: tuple[str, ...]
    manifest: dict[str, object]
    document: bytes
    version: str

    @property
    def rows(self) -> int:
        """The number of rows."""
        return len(next(iter(self.columns.values()), []))


@dataclass(frozen=True, slots=True)
class _Provenance:
    """The attributions, notices and terms pages of a value's sources."""

    attributions: tuple[str, ...]
    notices: tuple[str, ...]
    terms: tuple[str, ...]

    @classmethod
    def of(
        cls, sources: Iterable[tuple[LicenceClass, str, str | None, str | None]]
    ) -> _Provenance:
        """Collect ``(licence, attribution, notice, terms_url)`` per source."""
        kept = [s for s in sources if s[0] is not LicenceClass.USER_SUPPLIED]
        return cls(
            tuple(dict.fromkeys(s[1] for s in kept)),
            tuple(dict.fromkeys(s[2] for s in kept if s[2])),
            tuple(dict.fromkeys(s[3] for s in kept if s[3])),
        )

    @classmethod
    def of_records(cls, records: Iterable[DataSource]) -> _Provenance:
        """Collect the provenance of data source records."""
        return cls.of(
            (r.licence, r.attribution, r.notice, r.terms_url) for r in records
        )

    def lines(self) -> tuple[tuple[str, str], ...]:
        """Return the header lines: attributions, notices, then terms pages."""
        return (
            *(("attribution", text) for text in self.attributions),
            *(("notice", text) for text in self.notices),
            *(("terms", url) for url in self.terms),
        )

    @property
    def texts(self) -> tuple[str, ...]:
        """Every attribution, then every notice."""
        return (*self.attributions, *self.notices)


def _of_result(result: Result[Any, Any]) -> Subject:
    manifest = result.manifest
    provenance = _Provenance.of_records(manifest.data_sources)
    header = (
        ("pyeconomics", manifest.package_version),
        ("model", f"{result.model_id} version {result.model_version}"),
        ("inputs_sha256", manifest.inputs_sha256),
        ("result_sha256", manifest.result_sha256),
        *provenance.lines(),
    )
    return Subject(
        kind="result",
        columns=tables.columns_of([result]),
        header=header,
        attributions=provenance.texts,
        terms=provenance.terms,
        manifest=manifest.to_dict(),
        document=result.to_json().encode("utf-8"),
        version=manifest.package_version,
    )


def _of_batch(batch: BatchResult) -> Subject:
    from pyeconomics import __version__  # noqa: PLC0415 - the package is loaded

    records = [record for result in batch for record in result.manifest.data_sources]
    provenance = _Provenance.of_records(records)
    header = (
        ("pyeconomics", __version__),
        ("model", f"{batch.model_id} version {batch.model_version}"),
        ("rows", str(len(batch))),
        *provenance.lines(),
    )
    manifests = [result.manifest.to_dict() for result in batch]
    document = {
        "model_id": batch.model_id,
        "model_version": batch.model_version,
        "attributions": list(provenance.texts),
        "results": [result.to_dict() for result in batch],
    }
    return Subject(
        kind="batch",
        columns=tables.columns_of(batch),
        header=header,
        attributions=provenance.texts,
        terms=provenance.terms,
        manifest={
            "model_id": batch.model_id,
            "model_version": batch.model_version,
            "manifests": manifests,
        },
        document=canonical_json(document),
        version=__version__,
    )


def _frame_columns(frame: Any) -> dict[str, list[object]]:  # noqa: ANN401 - a frame
    columns: dict[str, list[object]] = {"date": list(frame.index)}
    if frame.realtime is not None:
        columns["realtime_start"] = [p.realtime_start for p in frame.realtime]
        columns["realtime_end"] = [p.realtime_end for p in frame.realtime]
    if not hasattr(frame, "columns"):
        columns["value"] = list(frame.values)
        return columns
    for column, values in zip(frame.columns, frame.data, strict=True):
        if column.name in _INDEX_COLUMNS:
            msg = (
                f"the table's column {column.name!r} takes the name of an export's "
                "index column"
            )
            raise InputError(msg)
        columns[column.name] = list(values)
    return columns


def _of_frame(
    frame: Any,  # noqa: ANN401 - a Series or a Table
    sources: Sequence[DataSource] | None,
    concept: str | None,
    skipped: Sequence[object],
) -> Subject:
    from pyeconomics import __version__  # noqa: PLC0415 - the package is loaded

    meta = frame.meta
    terms = meta.terms
    if sources:
        provenance = _Provenance.of_records(sources)
    else:
        provenance = _Provenance.of(
            [(terms.licence, terms.attribution, terms.notice, terms.terms_url)]
        )
    identifier = getattr(meta, "series_id", None) or meta.table_id
    header = (
        ("pyeconomics", __version__),
        ("data", f"{meta.provider}:{identifier}"),
        ("title", meta.title),
        ("frame_sha256", _sha256(frame.canonical_json())),
        *provenance.lines(),
    )
    manifest: dict[str, object] = {
        "type": "table" if hasattr(frame, "columns") else "series",
        "meta": meta.to_dict(),
    }
    if hasattr(frame, "columns"):
        manifest["columns"] = [column.to_dict() for column in frame.columns]
    record_list = [record.to_dict() for record in sources or ()]
    manifest |= {
        "concept": concept,
        "sources": record_list,
        "skipped": [jsonable(skip) for skip in skipped],
    }
    document = {
        "concept": concept,
        "frame": frame.to_dict(),
        "sources": record_list,
        "skipped": [jsonable(skip) for skip in skipped],
        "attributions": list(provenance.texts),
    }
    return Subject(
        kind="frame",
        columns=_frame_columns(frame),
        header=header,
        attributions=provenance.texts,
        terms=provenance.terms,
        manifest=manifest,
        document=canonical_json(document),
        version=__version__,
    )


def _of_records(records: Any) -> Subject:  # noqa: ANN401 - Records
    from pyeconomics import __version__  # noqa: PLC0415 - the package is loaded

    terms = records.terms
    provenance = _Provenance.of(
        [(terms.licence, terms.attribution, terms.notice, terms.terms_url)]
    )
    rows = [row.model_dump(mode="python") for row in records.rows]
    names: dict[str, None] = {}
    for row in rows:
        names.update(dict.fromkeys(row))
    header = (
        ("pyeconomics", __version__),
        ("data", f"{records.provider} records"),
        ("records_sha256", _sha256(records.canonical_json())),
        *provenance.lines(),
    )
    manifest = {
        "type": "records",
        "provider": records.provider,
        "terms": terms.to_dict(),
        "retrieved_at": records.retrieved_at.isoformat(),
    }
    document = {
        "records": records.model_dump(mode="json"),
        "attributions": list(provenance.texts),
    }
    return Subject(
        kind="records",
        columns={name: [row.get(name) for row in rows] for name in names},
        header=header,
        attributions=provenance.texts,
        terms=provenance.terms,
        manifest=manifest,
        document=canonical_json(document),
        version=__version__,
    )


def _sha256(data: bytes) -> str:
    import hashlib  # noqa: PLC0415 - only frames and records need it

    return hashlib.sha256(data).hexdigest()


def subject(value: object) -> Subject:
    """Read an exportable value: a result, a batch, a frame or records.

    Raises
    ------
    TypeError
        For a value of any other type.
    InputError
        For a table with a column named like an index column (``date``,
        ``realtime_start``, ``realtime_end``).
    """
    if isinstance(value, Result):
        return _of_result(value)
    if isinstance(value, BatchResult):
        return _of_batch(value)
    # The data layer's types, imported only to export its values.
    from pyeconomics.data.records import Records  # noqa: PLC0415
    from pyeconomics.data.resolver import Resolved  # noqa: PLC0415
    from pyeconomics.data.types import Series, Table  # noqa: PLC0415

    if isinstance(value, Resolved):
        return _of_frame(value.frame, value.sources, value.concept, value.skipped)
    if isinstance(value, Series | Table):
        return _of_frame(value, None, None, ())
    if isinstance(value, Records):
        return _of_records(value)
    msg = (
        "export takes a Result, a BatchResult, a Series, a Table, what data.get "
        f"resolved or Records, not {type(value).__name__}"
    )
    raise TypeError(msg)
