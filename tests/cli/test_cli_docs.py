# tests/cli/test_cli_docs.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The examples in docs/cli.md, run in-process (Phase 4 Step 4).

Each ``$ pyeconomics ...`` line of a ``console`` block runs with isolated
settings and keys in an empty working directory and must exit 0. A ``shell``
block holds examples that read live data: each runs offline, where it must
stop at the data with exit code 7, so its command line is proved valid without
the network. A ``text`` block is an illustration and does not run. The page's
exit code table must list every code the error table gives.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path

import pytest
from cli_support import cli

from pyeconomics.surfaces.problems import ROWS

PAGE = Path(__file__).resolve().parents[2] / "docs" / "cli.md"
_FENCE = re.compile(r"^```(\w+)\n(.*?)^```", re.MULTILINE | re.DOTALL)


def commands(language: str) -> list[tuple[str, ...]]:
    """The arguments of each ``$ pyeconomics`` line in a language's blocks."""
    text = PAGE.read_text(encoding="utf-8")
    return [
        tuple(shlex.split(line.removeprefix("$ "))[1:])
        for block_language, body in _FENCE.findall(text)
        if block_language == language
        for line in body.splitlines()
        if line.startswith("$ pyeconomics")
    ]


@pytest.mark.usefixtures("home")
@pytest.mark.parametrize("arguments", commands("console"), ids=" ".join)
def test_each_console_example_succeeds(arguments: tuple[str, ...]) -> None:
    outcome = cli(*arguments)
    assert outcome.code == 0, outcome.stderr


@pytest.mark.usefixtures("home")
@pytest.mark.parametrize("arguments", commands("shell"), ids=" ".join)
def test_each_live_example_stops_only_at_the_data(
    monkeypatch: pytest.MonkeyPatch, arguments: tuple[str, ...]
) -> None:
    monkeypatch.setenv("PYECONOMICS_OFFLINE", "1")
    outcome = cli(*arguments)
    assert outcome.code == 7, outcome.stderr


def test_the_page_has_examples_of_each_kind() -> None:
    console = {arguments[0] for arguments in commands("console") if arguments}
    assert {"models", "data", "keys", "cache", "registry", "completion"} <= console
    assert any(arguments[:2] == ("models", "run") for arguments in commands("shell"))


def test_the_exit_code_table_lists_every_code() -> None:
    text = PAGE.read_text(encoding="utf-8")
    listed = {int(code) for code in re.findall(r"^\| (\d) \|", text, re.MULTILINE)}
    assert listed == {row.exit_code for row in ROWS} | {0, 2}
