# src/pyeconomics/exports/columnar.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Parquet and Arrow IPC exports, through pyarrow imported lazily (ADR-0008 8).

pyarrow is never a dependency of pyeconomics, not even through an extra: these
writers import it when they run, and without it raise
:class:`~pyeconomics.core.errors.MissingOptionalDependencyError` naming it (exit
code 8 on the command line). The columns are :mod:`pyeconomics.core.tables`'
for a result (an array stays a list in its cell) and the frame's or the
records' for data; the schema metadata holds three keys:

- ``pyeconomics.manifest``: the manifest as canonical JSON;
- ``pyeconomics.attributions``: the attributions and required notices as a
  canonical JSON list;
- ``pyeconomics.version``: the pyeconomics version that wrote it.

An Arrow IPC export is the IPC *file* format (``.arrow``, Feather version 2),
which ``pyarrow.ipc.open_file`` and ``pandas.read_feather`` read.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core import tables
from pyeconomics.core._optional import import_optional
from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from pyeconomics.exports.layout import Subject

__all__ = [
    "ATTRIBUTIONS_METADATA_KEY",
    "MANIFEST_METADATA_KEY",
    "VERSION_METADATA_KEY",
    "arrow_table",
    "to_arrow_ipc",
    "to_parquet",
]

#: The schema metadata key of the manifest (the key ``Result.to_arrow`` uses).
MANIFEST_METADATA_KEY: Final = tables.MANIFEST_METADATA_KEY
#: The schema metadata key of the attributions and notices.
ATTRIBUTIONS_METADATA_KEY: Final = "pyeconomics.attributions"
#: The schema metadata key of the pyeconomics version.
VERSION_METADATA_KEY: Final = "pyeconomics.version"


def arrow_table(subject: Subject) -> Any:  # noqa: ANN401 - a pyarrow Table
    """Return a subject as an Arrow table with its metadata; needs pyarrow."""
    table = tables.to_arrow(subject.columns)
    return table.replace_schema_metadata(
        {
            MANIFEST_METADATA_KEY: canonical_json(subject.manifest).decode("utf-8"),
            ATTRIBUTIONS_METADATA_KEY: canonical_json(
                list(subject.attributions)
            ).decode("utf-8"),
            VERSION_METADATA_KEY: subject.version,
        }
    )


def to_parquet(subject: Subject) -> bytes:
    """Return a subject as Parquet bytes; needs pyarrow."""
    table = arrow_table(subject)
    pyarrow = import_optional("pyarrow")
    parquet = import_optional("pyarrow.parquet")
    sink = pyarrow.BufferOutputStream()
    parquet.write_table(table, sink)
    return bytes(sink.getvalue().to_pybytes())


def to_arrow_ipc(subject: Subject) -> bytes:
    """Return a subject as Arrow IPC file bytes; needs pyarrow."""
    table = arrow_table(subject)
    pyarrow = import_optional("pyarrow")
    ipc = import_optional("pyarrow.ipc")
    sink = pyarrow.BufferOutputStream()
    with ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    return bytes(sink.getvalue().to_pybytes())
