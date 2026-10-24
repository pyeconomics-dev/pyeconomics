# src/pyeconomics/cli/output.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Where the command line reads and writes, and how it shows a table.

Every command writes through a :class:`Streams`: bytes to standard output and
standard error, always UTF-8 whatever the operating system's code page, and
bytes from standard input. ``--format json`` writes canonical JSON followed by
one newline; ``--format table`` builds :class:`Grid` blocks, which a terminal
shows as rich tables and anything else (a pipe, a file, ``--out``) as plain
text, with every attribution and notice the data requires below them. A model
run and data also take the export formats (:mod:`pyeconomics.cli.exporting`).

A key never reaches this module: the key commands write only provider ids,
variable names and kinds of source.
"""

from __future__ import annotations

import getpass
import io
import sys

# Cyclopts resolves Streams' type hints when it writes a completion script (the
# context parameter that holds it), so the names they use exist at run time.
from collections.abc import Callable  # noqa: TC003
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, BinaryIO, Final, Literal, TextIO

from pyeconomics.core.canonical import canonical_json

if TYPE_CHECKING:
    from collections.abc import Iterable, Sequence
    from pathlib import Path

    from rich.console import Console
    from rich.table import Table
    from rich.text import Text

__all__ = [
    "PLAIN_WIDTH",
    "DescribeFormat",
    "Format",
    "Grid",
    "RunFormat",
    "Streams",
    "Utf8Text",
    "cell",
    "emit",
    "emit_json",
    "plain_console",
    "render_plain",
    "show",
]

#: The output formats of the commands that print a table or a document.
Format = Literal["table", "json"]
#: The output formats of a model run and of data: a table, canonical JSON, or an
#: export (:mod:`pyeconomics.exports`).
RunFormat = Literal["json", "table", "csv", "xlsx", "parquet", "arrow"]
#: The formats ``models describe`` writes: the card's Markdown, or JSON.
DescribeFormat = Literal["markdown", "json"]

#: The width plain text is laid out in: wide enough that no row wraps.
PLAIN_WIDTH: Final = 4096


class Utf8Text:
    """A text stream that writes UTF-8 to a binary one, and never closes it."""

    def __init__(self, binary: BinaryIO) -> None:
        """Wrap ``binary``."""
        self._binary = binary

    @property
    def encoding(self) -> str:
        """The encoding written: always UTF-8."""
        return "utf-8"

    def write(self, text: str) -> int:
        """Write ``text`` as UTF-8; a lone surrogate becomes ``?``."""
        self._binary.write(text.encode("utf-8", "replace"))
        return len(text)

    def flush(self) -> None:
        """Flush the binary stream."""
        self._binary.flush()

    def isatty(self) -> bool:
        """Say it is not a terminal, so rich writes plain text."""
        return False


@dataclass(frozen=True, slots=True, kw_only=True)
class Streams:
    """Standard input, output and error, and how to ask for a hidden value.

    Attributes
    ----------
    stdin, stdout, stderr
        Binary streams; text is written to them as UTF-8.
    terminal, error_terminal
        The text streams of an interactive terminal behind standard output or
        error, where rich draws its tables and help; ``None`` for a pipe or a
        file, which get plain text.
    interactive
        Whether standard input is a terminal, where a hidden prompt can ask for
        a key.
    ask_secret
        Asks for a value without echoing it: :func:`getpass.getpass`.
    """

    stdin: BinaryIO
    stdout: BinaryIO
    stderr: BinaryIO
    terminal: TextIO | None = None
    error_terminal: TextIO | None = None
    interactive: bool = False
    ask_secret: Callable[[str], str] = field(default=getpass.getpass)

    @classmethod
    def system(cls) -> Streams:
        """Return the process's own streams."""
        return cls(
            stdin=sys.stdin.buffer,
            stdout=sys.stdout.buffer,
            stderr=sys.stderr.buffer,
            terminal=sys.stdout if sys.stdout.isatty() else None,
            error_terminal=sys.stderr if sys.stderr.isatty() else None,
            interactive=sys.stdin.isatty(),
        )

    def write(self, data: bytes) -> None:
        """Write bytes to standard output, after any text rich wrote there."""
        if self.terminal is not None:
            self.terminal.flush()
        self.stdout.write(data)
        self.stdout.flush()

    def error(self, text: str) -> None:
        """Write one line to standard error, as UTF-8."""
        if self.error_terminal is not None:
            self.error_terminal.flush()
        self.stderr.write(f"{text}\n".encode("utf-8", "replace"))
        self.stderr.flush()


@dataclass(frozen=True, slots=True)
class Grid:
    """A table to show: a title, column headings and rows of cell text."""

    title: str | None
    columns: tuple[str, ...]
    rows: tuple[tuple[str, ...], ...]


#: What a table format shows, in order: tables and paragraphs of plain text.
Block = Grid | str


def cell(value: object) -> str:
    """Return a value as table text: JSON's spelling, nothing for a missing value."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return canonical_json(value).decode("utf-8")


def _text(value: str) -> Text:
    from rich.text import Text  # noqa: PLC0415 - rich loads with the command line

    return Text(value)


def _table(grid: Grid, *, plain: bool) -> Table:
    from rich import box  # noqa: PLC0415 - rich loads with the command line
    from rich.table import Table  # noqa: PLC0415

    table = Table(
        *grid.columns,
        title=None if plain or grid.title is None else _text(grid.title),
        title_justify="left",
        box=None if plain else box.ROUNDED,
        show_edge=not plain,
        pad_edge=not plain,
        header_style="" if plain else "bold",
        highlight=False,
    )
    for row in grid.rows:
        table.add_row(*(_text(item) for item in row))
    return table


def plain_console(file: TextIO | Utf8Text, *, width: int | None = None) -> Console:
    """Return a rich console that writes plain text: no colour, markup or emoji."""
    from rich.console import Console  # noqa: PLC0415 - rich loads with the command line

    return Console(
        file=file,  # type: ignore[arg-type] # ty: ignore[invalid-argument-type] - a text stream
        width=width,
        color_system=None,
        force_terminal=False,
        force_interactive=False,
        highlight=False,
        markup=False,
        emoji=False,
        legacy_windows=False,
        soft_wrap=False,
    )


def render_plain(blocks: Iterable[Block]) -> str:
    """Lay blocks out as plain text: titles, aligned columns, blank lines between."""
    buffer = io.StringIO()
    console = plain_console(buffer, width=PLAIN_WIDTH)
    first = True
    for block in blocks:
        if not first:
            console.print()
        first = False
        if isinstance(block, str):
            console.print(block)
            continue
        if block.title is not None:
            console.print(block.title)
        console.print(_table(block, plain=True))
    lines = (line.rstrip() for line in buffer.getvalue().splitlines())
    return "".join(f"{line}\n" for line in lines)


def _render_terminal(streams: Streams, blocks: Sequence[Block]) -> None:
    from rich.console import Console  # noqa: PLC0415 - rich loads with the command line

    console = Console(file=streams.terminal, highlight=False, markup=False, emoji=False)
    for index, block in enumerate(blocks):
        if index:
            console.print()
        console.print(block if isinstance(block, str) else _table(block, plain=False))
    if streams.terminal is not None:
        streams.terminal.flush()


def emit(streams: Streams, data: bytes, out: Path | None) -> None:
    """Write bytes to ``out``, or to standard output when it is ``None``."""
    if out is None:
        streams.write(data)
    else:
        out.write_bytes(data)


def emit_json(streams: Streams, document: object, out: Path | None) -> None:
    """Write a document as canonical JSON followed by one newline."""
    emit(streams, canonical_json(document) + b"\n", out)


def show(streams: Streams, blocks: Sequence[Block], out: Path | None) -> None:
    """Show blocks: rich tables on a terminal, plain text anywhere else."""
    if out is None and streams.terminal is not None:
        _render_terminal(streams, blocks)
    else:
        emit(streams, render_plain(blocks).encode("utf-8", "replace"), out)
