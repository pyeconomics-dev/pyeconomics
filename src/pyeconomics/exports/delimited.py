# src/pyeconomics/exports/delimited.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""CSV exports: RFC 4180, UTF-8 and LF, with a ``#`` metadata block (ADR-0012 6).

The file starts with one ``# label: text`` line per metadata item: the
pyeconomics version, the model and its version or the data's id, the hashes,
then every attribution, required notice and terms page of the data. The header
row and the data follow. Every text cell is quoted, and a text cell that starts
with ``=``, ``+``, ``-``, ``@``, a tab or a carriage return is prefixed with
``'`` (:func:`~pyeconomics.exports.layout.escape_text`). A number is never
quoted or escaped: an integer is written as Python writes it and a float as its
shortest round-trip text, so it reads back equal. A missing value is an empty
cell, a boolean ``true`` or ``false``, a date its ISO 8601 text and an array its
canonical JSON.

``pandas.read_csv(path, comment="#")`` skips the metadata block and reads the
rest.

Examples
--------
>>> from pyeconomics.exports.delimited import csv_cell
>>> values = (-1.5, 2, 1e-07, None, True, "=SUM(A1)", 'a "b" c')
>>> print(",".join(csv_cell(value) for value in values))
-1.5,2,1e-07,,true,"'=SUM(A1)","a ""b"" c"
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pyeconomics.exports.layout import cell_text, escape_text

if TYPE_CHECKING:
    from pyeconomics.exports.layout import Subject

__all__ = ["csv_cell", "metadata_line", "to_csv"]


def _quoted(text: str) -> str:
    escaped = escape_text(text).replace('"', '""')
    return f'"{escaped}"'


def csv_cell(value: object) -> str:
    """Return one cell as CSV text: numbers bare, everything else quoted.

    Raises
    ------
    ValueError
        For a float that is not finite, which no result or frame holds.
    """
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            msg = "a CSV export holds finite numbers only"
            raise ValueError(msg)
        return repr(value)
    return _quoted(cell_text(value))


def metadata_line(label: str, text: str) -> str:
    """Return one ``# label: text`` line; a line break in the text becomes a space."""
    flat = " ".join(text.splitlines())
    return f"# {label}: {flat}"


def to_csv(subject: Subject) -> bytes:
    """Return a subject as CSV bytes, its metadata block first."""
    lines = [metadata_line(label, text) for label, text in subject.header]
    lines.append(",".join(_quoted(name) for name in subject.columns))
    lines.extend(
        ",".join(csv_cell(value) for value in row)
        for row in zip(*subject.columns.values(), strict=True)
    )
    return "".join(f"{line}\n" for line in lines).encode("utf-8")
