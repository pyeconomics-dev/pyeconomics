# src/pyeconomics/server/formats.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``?format=`` of a run or a series: its bytes, media type and file name.

A run answers ``json`` by default: the result's canonical bytes
(:func:`~pyeconomics.surfaces.envelope.canonical_bytes`), never re-serialized.
Every other format comes from :mod:`pyeconomics.exports`, so a download carries
the same attributions, notices and manifest as the command line's: ``csv``,
``xlsx``, ``parquet`` and ``arrow`` (the last two need pyarrow, and answer the
``missing-extra`` problem without it), and for a run ``bundle``, its
reproducibility zip. A series answers ``json`` with the document ``pyeconomics
data get --format json`` prints, or one of the four exports.

Nothing here imports a framework: the worker processes render with it.

Examples
--------
>>> MEDIA_TYPES["csv"], disposition("csv", "foundations.time_value")
('text/csv; charset=utf-8', 'attachment; filename="foundations.time_value.csv"')
>>> disposition("json", "foundations.time_value") is None
True
>>> file_stem("oecd:OECD.SDD/DSD@DF/GBR.M")
'oecd_OECD.SDD_DSD_DF_GBR.M'
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from pyeconomics.core.canonical import canonical_json
from pyeconomics.core.errors import InputError

if TYPE_CHECKING:
    from pyeconomics.core.results import Result
    from pyeconomics.surfaces.invoke import BindRequest

__all__ = [
    "DEFAULT_FORMAT",
    "EXTENSIONS",
    "MEDIA_TYPES",
    "RUN_FORMATS",
    "SERIES_FORMATS",
    "choose",
    "disposition",
    "file_stem",
    "render_data",
    "render_result",
]

#: The format a run or a series answers when none is asked for.
DEFAULT_FORMAT: Final = "json"
#: A run's formats, in the order the documentation lists them.
RUN_FORMATS: Final = ("json", "csv", "xlsx", "parquet", "arrow", "bundle")
#: A series' formats: a run's but the bundle, which reruns a model.
SERIES_FORMATS: Final = ("json", "csv", "xlsx", "parquet", "arrow")
#: Each format's media type.
MEDIA_TYPES: Final = MappingProxyType(
    {
        "json": "application/json",
        "csv": "text/csv; charset=utf-8",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "parquet": "application/vnd.apache.parquet",
        "arrow": "application/vnd.apache.arrow.file",
        "bundle": "application/zip",
    }
)
#: Each format's file name extension.
EXTENSIONS: Final = MappingProxyType(
    {
        "json": "json",
        "csv": "csv",
        "xlsx": "xlsx",
        "parquet": "parquet",
        "arrow": "arrow",
        "bundle": "zip",
    }
)

_UNSAFE: Final = re.compile(r"[^A-Za-z0-9._-]+")


def choose(text: str | None, formats: tuple[str, ...]) -> str:
    """Return the format a ``?format=`` value names, the default when absent.

    Raises
    ------
    InputError
        For a format the route does not answer in; the message lists them.
    """
    if text is None:
        return DEFAULT_FORMAT
    if text not in formats:
        msg = f"format is one of {', '.join(formats)}"
        raise InputError(msg)
    return text


def file_stem(name: str) -> str:
    """Return a download's file name stem: unsafe runs as ``_``, no leading dot."""
    return _UNSAFE.sub("_", name).strip("._-") or "pyeconomics"


def disposition(export_format: str, name: str) -> str | None:
    """Return a download's ``Content-Disposition``; ``None`` for JSON, shown inline."""
    if export_format == DEFAULT_FORMAT:
        return None
    return f'attachment; filename="{file_stem(name)}.{EXTENSIONS[export_format]}"'


def render_result(
    result: Result[Any, Any], export_format: str, request: BindRequest | None
) -> bytes:
    """Return a run's bytes in a format; a bundle records the bind request."""
    if export_format == DEFAULT_FORMAT:
        from pyeconomics.surfaces.envelope import canonical_bytes  # noqa: PLC0415

        return canonical_bytes(result)
    if export_format == "bundle":
        from pyeconomics.exports.bundle import (  # noqa: PLC0415 - loads with a bundle
            bundle_bytes,
            bundle_members,
        )

        return bundle_bytes(bundle_members(result, request))
    from pyeconomics.exports import export_bytes  # noqa: PLC0415 - loads with an export

    return export_bytes(result, export_format)


def render_data(resolved: Any, export_format: str) -> bytes:  # noqa: ANN401 - Resolved
    """Return what ``data.get`` resolved in a format.

    JSON is the frame with its source records and attributions
    (:func:`~pyeconomics.surfaces.documents.data_document`), as canonical JSON.
    """
    if export_format == DEFAULT_FORMAT:
        from pyeconomics.surfaces.documents import data_document  # noqa: PLC0415

        return canonical_json(data_document(resolved))
    from pyeconomics.exports import export_bytes  # noqa: PLC0415 - loads with an export

    return export_bytes(resolved, export_format)
