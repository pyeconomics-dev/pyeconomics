# src/pyeconomics/cli/exporting.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Exports on the command line: the export formats, bundles and batches (Step 5).

- ``--format csv|xlsx|parquet|arrow`` on ``models run`` and ``data get`` writes
  :func:`pyeconomics.exports.export`'s bytes, to ``--out`` or standard output. A
  binary format (``xlsx``, ``parquet``, ``arrow``) is written to standard output
  only when it is not a terminal: redirect it, pipe it or name ``--out``.
- ``models run ID --bundle PATH`` also writes the run's reproducibility bundle.
- ``models run ID --batch FILE`` runs the model once per row of a CSV file
  (a header row of field names; an empty cell leaves the field out) or a JSON
  Lines file (one object per line), read within the codec's limit, through
  :func:`~pyeconomics.surfaces.invoke.invoke_batch`.
- ``bundle check FILE`` verifies a bundle while executing nothing from it
  (:func:`pyeconomics.exports.check_bundle`).

The exports load when a command writes one, never when the command line starts.
"""

import csv
import io
import re
from pathlib import Path
from typing import Annotated, Any, Final

from cyclopts import Parameter

from pyeconomics.cli.context import Context, ContextParameter, UsageError
from pyeconomics.cli.output import Block, Format, Grid, cell, emit, emit_json, show
from pyeconomics.core.errors import InputError
from pyeconomics.surfaces import codec
from pyeconomics.surfaces.documents import jsonable

__all__ = [
    "BINARY_FORMATS",
    "EXPORT_FORMATS",
    "batch_blocks",
    "check_bundle",
    "read_batch",
    "refuse_binary_terminal",
    "write_bundle_file",
    "write_export",
]

#: The ``--format`` values :mod:`pyeconomics.exports` writes.
EXPORT_FORMATS: Final = frozenset({"csv", "xlsx", "parquet", "arrow"})
#: The export formats whose bytes are not text.
BINARY_FORMATS: Final = frozenset({"xlsx", "parquet", "arrow"})

_FIELD: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_BOM: Final = "﻿"


def refuse_binary_terminal(
    context: Context, output_format: str, out: Path | None
) -> None:
    """Refuse to write a binary format to a terminal, before anything runs.

    Raises
    ------
    UsageError
        For ``xlsx``, ``parquet`` or ``arrow`` with no ``--out`` while standard
        output is a terminal.
    """
    if output_format in BINARY_FORMATS and out is None and context.streams.terminal:
        msg = (
            f"--format {output_format} writes binary data: name a file with --out, "
            "or redirect standard output"
        )
        raise UsageError(msg)


def write_export(
    context: Context, value: object, output_format: str, out: Path | None
) -> None:
    """Write a value in an export format to ``--out`` or standard output."""
    from pyeconomics.exports import export_bytes  # noqa: PLC0415 - loads with an export

    emit(context.streams, export_bytes(value, output_format), out)


def write_bundle_file(result: Any, path: Path, request: Any) -> None:  # noqa: ANN401
    """Write a run's bundle to ``--bundle``; a failure names no path.

    Raises
    ------
    InputError
        If the file cannot be written.
    """
    from pyeconomics.exports import write_bundle  # noqa: PLC0415 - loads with a bundle

    failure = ""
    try:
        write_bundle(result, path, request)
    except OSError as error:
        failure = type(error).__name__
    if failure:
        msg = f"the --bundle file cannot be written ({failure})"
        raise InputError(msg)


def _read(context: Context, source: str, option: str) -> str:
    """Read a file or standard input (``-``) as text, within the codec's limit."""
    limit = codec.MAX_INPUT_BYTES
    if source == "-":
        data = context.streams.stdin.read(limit + 1)
    else:
        failure, data = "", b""
        try:
            with Path(source).open("rb") as handle:
                data = handle.read(limit + 1)
        except OSError as error:
            failure = type(error).__name__
        if failure:
            msg = f"the {option} file cannot be read ({failure})"
            raise InputError(msg)
    if len(data) > limit:
        raise codec.InputTooLargeError(len(data), limit)
    try:
        return data.decode("utf-8").removeprefix(_BOM)
    except UnicodeDecodeError:
        msg = f"the {option} file is not UTF-8 text"
        raise InputError(msg) from None


def _csv_rows(text: str) -> list[object]:
    try:
        records = list(csv.reader(io.StringIO(text, newline="")))
    except csv.Error as error:
        msg = f"the --batch file is not CSV ({error})"
        raise InputError(msg) from None
    records = [record for record in records if record]
    if not records:
        return []
    header, *lines = records
    for name in header:
        if not _FIELD.fullmatch(name):
            msg = "the --batch file's header row holds a name that is not a field"
            raise InputError(msg)
    if len(set(header)) != len(header):
        msg = "the --batch file's header row repeats a field"
        raise InputError(msg)
    rows: list[object] = []
    for index, line in enumerate(lines):
        if len(line) != len(header):
            cells, fields = len(line), len(header)
            msg = f"row {index} of the batch has {cells} cells for {fields} fields"
            raise InputError(msg)
        rows.append([f"{n}={v}" for n, v in zip(header, line, strict=True) if v != ""])
    return rows


def read_batch(context: Context, source: str) -> list[object]:
    """Read a ``--batch`` file's rows: JSON Lines text, or CSV field values.

    A file whose first character (after white space) is ``{`` is JSON Lines;
    any other is CSV with a header row of field names. Each row is left for
    :func:`~pyeconomics.surfaces.invoke.invoke_batch` to decode: a JSON line as
    text, a CSV row as ``field=value`` pairs typed by the model's schema.

    Raises
    ------
    InputTooLargeError
        If the file is larger than the codec's limit.
    InputError
        If it cannot be read, holds no row, or is not CSV with a header of
        field names.
    """
    text = _read(context, source, "--batch")
    if text.lstrip().startswith("{"):
        rows: list[object] = [line for line in text.splitlines() if line.strip()]
    else:
        rows = _csv_rows(text)
    if not rows:
        msg = "the --batch file holds no rows"
        raise InputError(msg)
    return rows


def batch_blocks(batch: Any) -> list[Block]:  # noqa: ANN401 - a BatchResult
    """Return a batch as a table: one row per run, then the row count."""
    from pyeconomics.core.tables import columns_of  # noqa: PLC0415 - loads pandas

    columns = columns_of(batch)
    rows = tuple(
        tuple(cell(jsonable(value)) for value in row)
        for row in zip(*columns.values(), strict=True)
    )
    title = f"{batch.model_id}, version {batch.model_version}"
    return [Grid(title, tuple(columns), rows), f"{len(batch)} rows."]


def check_bundle(
    bundle: Path,
    /,
    *,
    output_format: Annotated[Format, Parameter(name="--format")] = "table",
    context: ContextParameter,
) -> None:
    """Verify a reproducibility bundle without running anything from it.

    It reads the bundle's JSON members only and checks the result's hashes,
    after refusing unsafe member names and oversized archives.

    Parameters
    ----------
    bundle
        The bundle's zip file.
    output_format
        table, or json for the report.
    """
    from pyeconomics.exports import check_bundle as verify  # noqa: PLC0415

    report = verify(bundle)
    if output_format == "json":
        emit_json(context.streams, report.to_dict(), None)
        return
    blocks: list[Block] = [
        Grid(
            "Bundle",
            ("Field", "Value"),
            (
                ("model", f"{report.model_id}, version {report.model_version}"),
                ("pyeconomics", report.package_version),
                ("result_sha256", report.result_sha256),
                ("inputs_sha256", report.inputs_sha256),
                ("bound", "yes" if report.bound else "no"),
                ("data sources", str(report.sources)),
            ),
        ),
        Grid(
            "Members",
            ("Member", "Bytes"),
            tuple((name, str(size)) for name, size in report.members),
        ),
        (
            "Verified without running anything from it. reproduce.py is a "
            "program: read it before you run a bundle someone else made."
        ),
    ]
    show(context.streams, blocks, None)
