# src/pyeconomics/cli/data_commands.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``pyeconomics data``: the data API on the command line.

Each command wraps one function of :mod:`pyeconomics.data.api` unchanged, so the
mode, key, licence, cache and offline rules are the library's own. A target is a
catalog concept id (``us.unemployment.rate``), a provider series
(``fred:UNRATE``) or, for ``describe``, a provider id: never a URL.

``data get --format json`` writes the frame's canonical JSON with its source
records and the attributions and notices the data requires
(:func:`~pyeconomics.surfaces.documents.data_document`); ``--format table``
prints the observations with the same texts below them; ``--format csv``,
``xlsx``, ``parquet`` and ``arrow`` write an export of the frame with the same
texts and its source records (:mod:`pyeconomics.cli.exporting`). The data layer is
imported when a data command runs, never when the command line starts.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any

from cyclopts import Parameter

from pyeconomics.cli.context import ContextParameter
from pyeconomics.cli.exporting import (
    EXPORT_FORMATS,
    refuse_binary_terminal,
    write_export,
)
from pyeconomics.cli.output import Block, Format, Grid, RunFormat, cell, emit_json, show
from pyeconomics.core import _fields as f
from pyeconomics.surfaces.documents import attributions, data_document, jsonable

__all__ = [
    "describe_data",
    "document_blocks",
    "get_data",
    "list_sources",
    "list_vintages",
    "search_data",
]

FormatOption = Annotated[Format, Parameter(name="--format")]
OutOption = Annotated[
    Path | None,
    Parameter(name="--out", help="Write the output to this file instead."),
]


def _day(text: str | None, what: str) -> Any:  # noqa: ANN401 - a date or None
    return None if text is None else f.parse_day(text, what)


def search_data(
    text: str,
    /,
    *,
    limit: int = 20,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Search the catalog's concepts, then the series of providers that search.

    A provider that cannot be asked (no key, offline, hosted mode) is listed
    with the reason and never stops the others.

    Parameters
    ----------
    text
        Words to look for.
    limit
        At most this many hits, from 1 to 100.
    output_format
        table, or json for the hits and the providers passed over.
    """
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    found = api.search(text, limit)
    if output_format == "json":
        document = {
            "hits": jsonable(found.hits),
            "skipped": [
                {"provider": provider, "reason": reason}
                for provider, reason in found.skipped
            ],
        }
        emit_json(context.streams, document, out)
        return
    blocks: list[Block] = [
        Grid(
            "Matches",
            ("Kind", "Id", "Title", "Frequency", "Unit"),
            tuple(
                (
                    hit.kind,
                    hit.id,
                    hit.title,
                    cell(jsonable(hit.frequency)),
                    cell(hit.unit),
                )
                for hit in found.hits
            ),
        )
    ]
    if found.skipped:
        blocks.append(
            "\n".join(
                f"Not asked: {provider} ({reason})"
                for provider, reason in found.skipped
            )
        )
    show(context.streams, blocks, out)


def _frame_grid(frame: Any) -> Grid:  # noqa: ANN401 - a Series or a Table
    meta = frame.meta
    realtime = frame.realtime
    periods = ("Realtime start", "Realtime end") if realtime is not None else ()
    if hasattr(frame, "columns"):
        columns = tuple(column.name for column in frame.columns)
        values = (
            list(zip(*frame.data, strict=True))
            if frame.data
            else [()] * len(frame.index)
        )
        title = meta.title
    else:
        columns = ("Value",)
        values = [(value,) for value in frame.values]
        title = f"{meta.title} ({meta.unit.text})"
    rows = []
    for position, day in enumerate(frame.index):
        row = [day.isoformat(), *(cell(value) for value in values[position])]
        if realtime is not None:
            period = realtime[position]
            row += [
                cell(jsonable(period.realtime_start)),
                cell(jsonable(period.realtime_end)),
            ]
        rows.append(tuple(row))
    return Grid(title, ("Date", *columns, *periods), tuple(rows))


def _sources_grid(records: Sequence[Any]) -> Grid:
    return Grid(
        "Sources",
        ("Provider", "Series", "Vintage", "Licence", "Cached"),
        tuple(
            (
                record.provider,
                record.series_id,
                cell(record.vintage),
                record.licence.value,
                "yes" if record.cache_hit else "no",
            )
            for record in records
        ),
    )


def get_data(  # noqa: PLR0913 - the data API's options
    target: str,
    /,
    *,
    start: Annotated[str | None, Parameter(metavar="DATE")] = None,
    end: Annotated[str | None, Parameter(metavar="DATE")] = None,
    as_of: Annotated[str | None, Parameter(metavar="DATE")] = None,
    vintage: str | None = None,
    provider: str | None = None,
    output_format: Annotated[RunFormat, Parameter(name="--format")] = "json",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Get the data a concept or a provider series names.

    Parameters
    ----------
    target
        A concept id, such as us.unemployment.rate, or provider:series, such as
        fred:UNRATE.
    start
        The first observation date, YYYY-MM-DD.
    end
        The last observation date, YYYY-MM-DD.
    as_of
        Read the data as published on this date.
    vintage
        A vintage label, such as latest or a date, in place of --as-of.
    provider
        For a concept, use only this provider's candidates.
    output_format
        json for the frame, its source records and attributions; table; or an
        export: csv, xlsx, parquet or arrow.
    """
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    refuse_binary_terminal(context, output_format, out)
    resolved = api.get(
        target,
        start=_day(start, "start"),
        end=_day(end, "end"),
        as_of=_day(as_of, "as_of"),
        vintage=vintage,
        provider=provider,
    )
    if output_format == "json":
        emit_json(context.streams, data_document(resolved), out)
        return
    if output_format in EXPORT_FORMATS:
        write_export(context, resolved, output_format, out)
        return
    blocks: list[Block] = [_frame_grid(resolved.frame), _sources_grid(resolved.sources)]
    if resolved.skipped:
        blocks.append(
            "\n".join(
                f"Passed over: {skip.provider} ({skip.reason}: {skip.detail})"
                for skip in resolved.skipped
            )
        )
    texts = attributions(resolved.sources)
    if texts:
        blocks.append("\n".join(texts))
    show(context.streams, blocks, out)


def _records_grid(title: str, records: Sequence[Mapping[str, object]]) -> Grid:
    columns: dict[str, None] = {}
    for record in records:
        columns.update(dict.fromkeys(record))
    names = tuple(columns)
    return Grid(
        title,
        names,
        tuple(tuple(cell(record.get(name)) for name in names) for record in records),
    )


def document_blocks(title: str, document: Mapping[str, object]) -> list[Block]:
    """Lay a JSON document out as tables: its fields, then each list of records.

    A nested object's fields are named with dots (``concept.title``); a list of
    objects becomes a table of its own; any other value is shown as JSON text.
    """
    rows: list[tuple[str, str]] = []
    tables: list[Block] = []

    def walk(prefix: str, mapping: Mapping[str, object]) -> None:
        for key, value in mapping.items():
            name = f"{prefix}{key}"
            if isinstance(value, Mapping):
                walk(f"{name}.", value)
            elif (
                isinstance(value, list)
                and value
                and all(isinstance(item, Mapping) for item in value)
            ):
                tables.append(_records_grid(name, value))
            else:
                rows.append((name, cell(value)))

    walk("", document)
    return [Grid(title, ("Field", "Value"), tuple(rows)), *tables]


def describe_data(
    target: str,
    /,
    *,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """Describe a concept (its candidates), a provider series or a provider.

    A concept or a provider is described from metadata, offline; a provider
    series is described by its provider, which is a request.

    Parameters
    ----------
    target
        A concept id, provider:series, or a provider id such as fred.
    output_format
        table, or json for every field.
    """
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    document = jsonable(api.describe(target))
    if output_format == "json":
        emit_json(context.streams, document, out)
        return
    show(context.streams, document_blocks(target, document), out)


def list_vintages(
    target: str,
    /,
    *,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """List the dates a series changed, oldest first.

    Parameters
    ----------
    target
        A concept id or provider:series of a source that keeps vintages.
    output_format
        table, or json for the dates as a list.
    """
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    dates = [day.isoformat() for day in api.vintages(target)]
    if output_format == "json":
        emit_json(context.streams, dates, out)
        return
    grid = Grid("Vintages", ("Vintage",), tuple((day,) for day in dates))
    show(context.streams, [grid, f"{len(dates)} vintages of {target}."], out)


def list_sources(
    *,
    check_keys: Annotated[bool, Parameter(negative="")] = False,
    output_format: FormatOption = "table",
    out: OutOption = None,
    context: ContextParameter,
) -> None:
    """List the data providers with their licence classes, keys and extras.

    It reads metadata only and makes no request.

    Parameters
    ----------
    check_keys
        Also say whether a key is configured for each provider that uses one;
        its value is never read into the output.
    output_format
        table, or json for every field, attributions and notices included.
    """
    from pyeconomics.data import api  # noqa: PLC0415 - the data layer loads here

    infos = api.sources(check_keys=check_keys)
    if output_format == "json":
        emit_json(context.streams, jsonable(infos), out)
        return
    configured = ("Configured",) if check_keys else ()
    rows = []
    for info in infos:
        key = ""
        if info.key_variable is not None:
            need = "required" if info.key_required else "optional"
            key = f"{info.key_variable} ({need})"
        row = [info.id, info.name, info.licence.value, key]
        if check_keys:
            row.append(
                ""
                if info.key_configured is None
                else ("yes" if info.key_configured else "no")
            )
        row.append(cell(info.extra))
        rows.append(tuple(row))
    grid = Grid(
        "Sources", ("Id", "Name", "Licence", "Key", *configured, "Extra"), tuple(rows)
    )
    show(context.streams, [grid], out)
