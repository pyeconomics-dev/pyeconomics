# tests/cli/cli_support.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Run the command line in-process and keep what it wrote (tests/cli).

:func:`cli` calls :func:`pyeconomics.cli.main` with in-memory streams and
returns an :class:`Outcome`: the exit code, standard output as bytes and
standard error as text. A :class:`FakeTerminal` stands in for an interactive
terminal, where tables are drawn with rich. A command that asks for a hidden
value without a prompt function fails the test.

:func:`install_world` makes the toy bound models and the scripted providers of
tests/data/bindings/bound_support.py the installed registries, as an entry point
would give them, so a bound run or a data command reads no network.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

import bound_support as bs

from pyeconomics.cli import main
from pyeconomics.cli.output import Streams
from pyeconomics.core import registry as core_registry

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

__all__ = ["FakeTerminal", "Outcome", "cli", "install_world"]


@dataclass(frozen=True)
class Outcome:
    """What one command line returned and wrote."""

    code: int
    stdout: bytes
    stderr: str

    @property
    def text(self) -> str:
        """Standard output as text: it is always UTF-8."""
        return self.stdout.decode("utf-8")


class FakeTerminal(io.StringIO):
    """A text stream that says it is an interactive terminal."""

    def isatty(self) -> bool:
        """Say it is a terminal, so rich draws its tables."""
        return True


def _no_prompt(prompt: str) -> NoReturn:
    msg = f"the command asked for a hidden value: {prompt!r}"
    raise AssertionError(msg)


def cli(
    *args: str,
    stdin: bytes = b"",
    interactive: bool = False,
    ask: Callable[[str], str] | None = None,
    terminal: io.StringIO | None = None,
) -> Outcome:
    """Run ``pyeconomics <args>`` in-process with in-memory streams."""
    out, err = io.BytesIO(), io.BytesIO()
    streams = Streams(
        stdin=io.BytesIO(stdin),
        stdout=out,
        stderr=err,
        terminal=terminal,
        interactive=interactive,
        ask_secret=ask or _no_prompt,
    )
    code = main(list(args), streams=streams)
    return Outcome(code, out.getvalue(), err.getvalue().decode("utf-8"))


def install_world(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make the toy bound models and the scripted providers the installed ones."""
    from pyeconomics.data import registry as provider_registry  # noqa: PLC0415

    monkeypatch.setattr(core_registry._CACHE, "registry", bs.model_registry())  # noqa: SLF001
    monkeypatch.setattr(provider_registry._CACHE, "registry", bs.world())  # noqa: SLF001
