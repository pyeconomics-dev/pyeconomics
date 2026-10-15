# src/pyeconomics/data/credentials/dotenv.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
r"""A strict parser for the ``.env`` file in the user's configuration directory.

ADR-0011 decision 12. The key chain reads a key from that file when the
environment does not hold it. The format is deliberately small, so that
nothing in the file is ever executed, interpolated or expanded:

- one ``NAME=VALUE`` per line, with optional spaces around ``=``;
- ``NAME`` is a letter or underscore followed by letters, digits and
  underscores;
- ``VALUE`` is taken literally: bare (no spaces, quotes or ``#``), or inside
  matching single or double quotes on the same line, with no escapes;
- blank lines and lines starting with ``#`` are ignored, as is a ``#``
  comment after a value;
- ``export``, multi-line values and a name set twice are errors.

An error names the line number and what is wrong, never the line itself,
which may hold a key. This module only parses text; the key chain reads the
file.

Examples
--------
>>> parse_dotenv("# keys\nFRED_API_KEY=\nBLS_API_KEY = '' # not yet\n")
{'FRED_API_KEY': '', 'BLS_API_KEY': ''}

"""

from __future__ import annotations

import re
from typing import Final

from pyeconomics.data.errors import ConfigError

__all__ = ["DOTENV_LOCATION", "MAX_DOTENV_CHARACTERS", "parse_dotenv"]

#: How messages name the file, which never print a path.
DOTENV_LOCATION: Final = "the .env file in the pyeconomics configuration directory"
#: The largest file accepted, in characters.
MAX_DOTENV_CHARACTERS: Final = 64 * 1024

_NAME: Final = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Control characters other than the tab, which separates like a space.
_CONTROL: Final = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")
# A bare value: no space, quote or #, then optionally a space and a comment.
_BARE: Final = re.compile(r"(?P<value>[^\s'\"#]*)(?:\s+#.*)?")
_QUOTES: Final = ("'", '"')


def _fail(number: int, problem: str) -> ConfigError:
    return ConfigError(f"line {number} of {DOTENV_LOCATION} {problem}")


def _value(text: str, number: int) -> str:
    """Read the value part of a line, after the ``=``."""
    if text[:1] in _QUOTES:
        end = text.find(text[0], 1)
        if end == -1:
            msg = "opens a quote it does not close (a value must fit on one line)"
            raise _fail(number, msg)
        tail = text[end + 1 :].strip()
        if tail and not tail.startswith("#"):
            raise _fail(number, "has text after its closing quote")
        return text[1:end]
    if text.startswith("#"):
        return ""
    bare = _BARE.fullmatch(text)
    if bare is None:
        msg = "has a value with a space, a quote or a #; put it in quotes"
        raise _fail(number, msg)
    return bare.group("value")


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse a ``.env`` file's text into its names and literal values.

    Parameters
    ----------
    text
        The file's text, as read in UTF-8.

    Returns
    -------
    dict[str, str]
        Each name and its value, in file order. An empty value is kept as
        ``""``; the key chain treats it as unset.

    Raises
    ------
    ConfigError
        If the text is longer than :data:`MAX_DOTENV_CHARACTERS` or a line
        breaks the format; the message names the line number only.

    Examples
    --------
    >>> parse_dotenv("export FRED_API_KEY=x")
    Traceback (most recent call last):
    ...
    pyeconomics.data.errors.ConfigError: line 1 of the .env file in the pyeconomics configuration directory uses export, which pyeconomics does not read

    """  # noqa: E501 - doctest output lines cannot wrap
    if len(text) > MAX_DOTENV_CHARACTERS:
        msg = f"{DOTENV_LOCATION} is longer than {MAX_DOTENV_CHARACTERS} characters"
        raise ConfigError(msg)
    values: dict[str, str] = {}
    first_set: dict[str, int] = {}
    for number, raw in enumerate(text.removeprefix("﻿").split("\n"), start=1):
        line = raw.removesuffix("\r")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if _CONTROL.search(line):
            raise _fail(number, "holds a control character")
        name, equals, rest = stripped.partition("=")
        name = name.strip()
        if name.startswith(("export ", "export\t")):
            raise _fail(number, "uses export, which pyeconomics does not read")
        if not equals:
            raise _fail(number, "is not NAME=VALUE")
        if not _NAME.fullmatch(name):
            raise _fail(number, "does not start with a variable name")
        value = _value(rest.strip(), number)
        if name in first_set:
            msg = f"sets a name already set on line {first_set[name]}"
            raise _fail(number, msg)
        first_set[name] = number
        values[name] = value
    return values
