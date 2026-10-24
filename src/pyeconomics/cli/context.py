# src/pyeconomics/cli/context.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""What one run of the command line shares with the command it runs.

The launcher hands each command a :class:`Context`: the streams to read and
write, whether ``--debug`` was asked for, and the application itself (for the
completion script). A command declares it as a keyword-only parameter of type
:data:`ContextParameter`, which Cyclopts leaves unparsed, so it never becomes an
option.
"""

from typing import Annotated

from cyclopts import App, Parameter

from pyeconomics.cli.output import Streams

__all__ = ["Context", "ContextParameter", "UsageError"]


class Context:
    """The streams, the ``--debug`` flag and the application of one run.

    A plain class, not a dataclass: Cyclopts reads a dataclass parameter's
    fields as options, even one it does not parse.
    """

    __slots__ = ("app", "debug", "streams")

    def __init__(self, *, streams: Streams, debug: bool = False) -> None:
        """Hold the run's streams and its ``--debug`` flag."""
        self.streams = streams
        self.debug = debug
        self.app: App | None = None


#: A command's context parameter: passed by the launcher, never parsed, and
#: never read as a class whose fields are options (``accepts_keys=False``).
ContextParameter = Annotated[Context, Parameter(parse=False, accepts_keys=False)]


class UsageError(Exception):
    """A command was called in a way it cannot be: exit code 2, as a parse error.

    It is raised only for a mistake in how the command line was written, never
    for invalid inputs or data, which go through the error table.
    """
