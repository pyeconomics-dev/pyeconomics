# src/pyeconomics/cli/__init__.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The ``pyeconomics`` command line (ADR-0012 decision 5).

The console script ``pyeconomics`` calls :func:`main`. Its commands:

- ``models list|search|describe|run``: the registry, with each model's run
  options generated from its input schema when ``models run ID`` is parsed;
- ``data search|get|describe|vintages|sources``: the data API;
- ``keys set|list|delete``: providers' keys in the OS keyring, read from a
  hidden prompt or standard input, never an argument;
- ``cache ls|info|clear|path`` and ``registry export``;
- ``completion`` and ``--install-completion``, ``--version``, ``--debug``.

Every run goes through :func:`pyeconomics.surfaces.invoke`, every failure
through the error table (:mod:`pyeconomics.surfaces.problems`), and output is
UTF-8 on every operating system. Importing this package loads neither Cyclopts
nor rich: they load when :func:`main` or :func:`build_app` builds the command
line, so the core still imports where they are absent.

Examples
--------
>>> import io
>>> from pyeconomics.cli import main
>>> from pyeconomics.cli.output import Streams
>>> out = io.BytesIO()
>>> streams = Streams(stdin=io.BytesIO(), stdout=out, stderr=io.BytesIO())
>>> main(["--version"], streams=streams)
0
>>> out.getvalue().decode().startswith("pyeconomics 1.0.0")
True
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from cyclopts import App

    from pyeconomics.cli.output import Streams

__all__ = ["build_app", "main"]


def main(argv: Sequence[str] | None = None, *, streams: Streams | None = None) -> int:
    """Run the command line and return its exit code.

    Parameters
    ----------
    argv
        The arguments, without the program's name; ``sys.argv[1:]`` by default.
    streams
        Where to read and write; the process's own streams by default.
    """
    from pyeconomics.cli.app import launch  # noqa: PLC0415 - Cyclopts loads here

    return launch(argv, streams=streams)


def build_app(streams: Streams | None = None) -> App:
    """Build the command line's application without running it.

    The Pyodide job builds it this way to show the CLI imports there.
    """
    from pyeconomics.cli.app import build  # noqa: PLC0415 - Cyclopts loads here
    from pyeconomics.cli.context import Context  # noqa: PLC0415
    from pyeconomics.cli.output import Streams as SystemStreams  # noqa: PLC0415

    return build(Context(streams=streams or SystemStreams.system()))
