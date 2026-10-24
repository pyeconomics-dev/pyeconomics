# src/pyeconomics/cli/cache_commands.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics cache``: inspect and clear the local data cache.

The commands wrap :func:`~pyeconomics.data.cache.entries`,
:func:`~pyeconomics.data.cache.info`, :func:`~pyeconomics.data.cache.clear` and
:func:`~pyeconomics.data.cache.path`. None of them shows a payload or creates the
cache: a cache that does not exist yet has no entries.
"""

from pathlib import Path
from typing import Annotated

from cyclopts import Parameter

from pyeconomics.cli.context import ContextParameter
from pyeconomics.cli.output import Format, Grid, cell, emit_json, show
from pyeconomics.surfaces.documents import jsonable

__all__ = ["cache_info", "cache_path", "clear_cache", "list_entries"]

FormatOption = Annotated[Format, Parameter(name="--format")]
OutOption = Annotated[
    Path | None,
    Parameter(name="--out", help="Write the output to this file instead."),
]


def list_entries(
    *,
    provider: str | None = None,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """List the cached entries: their keys, times and sizes, never a payload.

    Parameters
    ----------
    provider
        Only this provider's entries.
    output_format
        table, or json for every field.
    """
    from pyeconomics.data import cache  # noqa: PLC0415 - the data layer loads here

    entries = cache.entries(provider)
    if output_format == "json":
        emit_json(context.streams, jsonable(entries), out)
        return
    grid = Grid(
        "Cache",
        (
            "Provider",
            "Dataset",
            "Series",
            "Vintage",
            "Retrieved",
            "Expires",
            "Licence",
            "Bytes",
        ),
        tuple(
            (
                entry.provider,
                entry.dataset,
                entry.series,
                entry.vintage,
                cell(jsonable(entry.retrieved_at)),
                cell(jsonable(entry.expires_at)) or "closed vintage",
                entry.licence,
                cell(entry.size_bytes),
            )
            for entry in entries
        ),
    )
    count = len(entries)
    show(
        context.streams,
        [grid, f"{count} cached entr{'y' if count == 1 else 'ies'}."],
        out,
    )


def cache_info(
    *,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Describe the cache: its file, size, entry count and schema version.

    Parameters
    ----------
    output_format
        table, or json for every field.
    """
    from pyeconomics.data import cache  # noqa: PLC0415 - the data layer loads here

    document = jsonable(cache.info())
    if output_format == "json":
        emit_json(context.streams, document, out)
        return
    grid = Grid(
        "Cache",
        ("Field", "Value"),
        tuple((name, cell(value)) for name, value in document.items()),
    )
    show(context.streams, [grid], out)


def clear_cache(*, provider: str | None = None, context: ContextParameter) -> None:
    """Delete the cached entries of one provider, or all of them.

    Parameters
    ----------
    provider
        Only this provider's entries.
    """
    from pyeconomics.data import cache  # noqa: PLC0415 - the data layer loads here

    count = cache.clear(provider)
    noun = "entry" if count == 1 else "entries"
    context.streams.write(f"Deleted {count} cached {noun}.\n".encode())


def cache_path(*, context: ContextParameter) -> None:
    """Print the cache file's path; nothing is created."""
    from pyeconomics.data import cache  # noqa: PLC0415 - the data layer loads here

    context.streams.write(f"{cache.path()}\n".encode())
