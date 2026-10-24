# src/pyeconomics/exports/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exports and reproducibility bundles (ADR-0012 decisions 6 and 7).

:func:`export` writes a result, a batch, a data frame (or what ``data.get``
resolved) or records as CSV, XLSX, Parquet, Arrow IPC or JSON, each carrying the
attribution and every required notice of the data (ADR-0005 rule 2) and the
manifest:

- :mod:`~pyeconomics.exports.delimited`: CSV with a ``#`` metadata block;
- :mod:`~pyeconomics.exports.spreadsheet`: XLSX with ``data`` and ``manifest``
  sheets;
- :mod:`~pyeconomics.exports.columnar`: Parquet and Arrow, through pyarrow;
- :mod:`~pyeconomics.exports.document`: canonical JSON.

Text cells that start like a spreadsheet formula are escaped in CSV and XLSX
(:func:`~pyeconomics.exports.layout.escape_text`); numbers never are.
:func:`write_bundle` writes a deterministic zip that reruns a result, and
:func:`check_bundle` verifies one without running anything from it
(:mod:`~pyeconomics.exports.bundle`). No export or bundle holds a key, a path, a
host or anything of the machine that wrote it.

Examples
--------
>>> import io
>>> from pyeconomics import run
>>> result = run("foundations.time_value", {"calculation": "present_value",
...     "rate": 0.05, "periods": 10, "future_value": 100})
>>> buffer = io.BytesIO()
>>> export(result, "csv", buffer)
>>> buffer.getvalue().splitlines()[0].decode()  # doctest: +ELLIPSIS
'# pyeconomics: ...'
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import IO, TYPE_CHECKING, Final

from pyeconomics.core.errors import InputError
from pyeconomics.exports import columnar, delimited, document, spreadsheet
from pyeconomics.exports.bundle import BundleReport, check_bundle, write_bundle
from pyeconomics.exports.layout import FORMATS, ExportFormat, subject

if TYPE_CHECKING:
    from collections.abc import Callable
    from os import PathLike

    from pyeconomics.exports.layout import Subject

__all__ = [
    "BINARY_FORMATS",
    "FORMATS",
    "BundleReport",
    "ExportFormat",
    "check_bundle",
    "export",
    "export_bytes",
    "write_bundle",
]

#: The formats whose bytes are not text.
BINARY_FORMATS: Final = frozenset({"xlsx", "parquet", "arrow"})

_WRITERS: Final[dict[str, Callable[[Subject], bytes]]] = {
    "csv": delimited.to_csv,
    "xlsx": spreadsheet.to_xlsx,
    "parquet": columnar.to_parquet,
    "arrow": columnar.to_arrow_ipc,
    "json": document.to_json,
}


def export_bytes(value: object, export_format: ExportFormat | str) -> bytes:
    """Return a value exported in a format, as bytes; see :func:`export`."""
    writer = _WRITERS.get(export_format)
    if writer is None:
        msg = f"the export formats are {', '.join(FORMATS)}, not {export_format!r}"
        raise InputError(msg)
    return writer(subject(value))


def export(
    value: object,
    export_format: ExportFormat | str,
    target: str | PathLike[str] | IO[bytes],
) -> None:
    """Export a result, a batch, a frame or records to a path or a binary stream.

    Parameters
    ----------
    value
        A :class:`~pyeconomics.core.results.Result`, a
        :class:`~pyeconomics.core.results.BatchResult`, a
        :class:`~pyeconomics.data.types.Series` or
        :class:`~pyeconomics.data.types.Table`, what ``data.get`` resolved, or
        :class:`~pyeconomics.data.records.Records`.
    export_format
        ``csv``, ``xlsx``, ``parquet``, ``arrow`` or ``json``.
    target
        A file path, or a binary stream to write to.

    Raises
    ------
    InputError
        For an unknown format, or a value XLSX cannot hold.
    MissingOptionalDependencyError
        For Parquet or Arrow without ``pyarrow``.
    TypeError
        For a value that is none of the types above.
    """
    data = export_bytes(value, export_format)
    if isinstance(target, str | os.PathLike):
        Path(target).write_bytes(data)
    else:
        target.write(data)
