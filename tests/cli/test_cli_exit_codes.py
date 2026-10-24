# tests/cli/test_cli_exit_codes.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""One command into each exit code (ADR-0012 decisions 4 and 5).

0 success, 1 internal error, 2 usage, 3 invalid input, 4 no defined result, 5
not found, 6 not permitted, 7 data unavailable, 8 missing extra. Every code but
0 and 2 comes from the error table (``surfaces.problems.ROWS``), and its
problem's ``cli_message`` is what standard error says; a usage error is
Cyclopts' parse error, reported as ``usage-error``. None reaches the network.
"""

from __future__ import annotations

import sys

import pytest
from cli_support import cli

from pyeconomics.surfaces.problems import ROWS

TVM = "foundations.time_value"
#: Each case: its id, the command line, the environment it needs, the exit code
#: and the first word standard error says (empty for a success).
CASES: list[tuple[str, tuple[str, ...], dict[str, str], int, str]] = [
    ("success", ("--version",), {}, 0, ""),
    (
        "internal",
        ("cache", "path"),
        {"PYECONOMICS_OFFLINE": "maybe"},
        1,
        "invalid-configuration",
    ),
    ("usage", ("models", "list", "--no-such-option"), {}, 2, "usage-error"),
    (
        "invalid-input",
        ("models", "run", TVM, "--calculation", "present_value", "--rate", "7"),
        {},
        3,
        "invalid-input",
    ),
    (
        "no-defined-result",
        (
            "models",
            "run",
            "derivatives.binomial_tree",
            "--option-type",
            "put",
            "--spot",
            "50",
            "--strike",
            "50",
            "--years",
            "1",
            "--risk-free-rate",
            "0.5",
            "--volatility",
            "0.01",
            "--steps",
            "2",
        ),
        {},
        4,
        "no-defined-result",
    ),
    ("not-found", ("models", "run", "foundations.nothing"), {}, 5, "model-not-found"),
    (
        "not-permitted",
        ("data", "get", "fred:UNRATE"),
        {"PYECONOMICS_MODE": "hosted"},
        6,
        "licence-refused",
    ),
    (
        "data-unavailable",
        ("data", "get", "treasury:par_nominal"),
        {"PYECONOMICS_OFFLINE": "1"},
        7,
        "offline-cache-miss",
    ),
    ("missing-extra", ("keys", "delete", "fred"), {}, 8, "missing-extra"),
]


@pytest.mark.parametrize(
    ("arguments", "environment", "code", "slug"),
    [case[1:] for case in CASES],
    ids=[case[0] for case in CASES],
)
def test_each_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    arguments: tuple[str, ...],
    environment: dict[str, str],
    code: int,
    slug: str,
) -> None:
    for name, value in environment.items():
        monkeypatch.setenv(name, value)
    if code == 8:
        monkeypatch.setitem(sys.modules, "keyring", None)
    outcome = cli(*arguments)
    assert outcome.code == code
    if slug:
        assert outcome.stderr.startswith(f"{slug}: ")
        assert len(outcome.stderr.splitlines()) == 1
    else:
        assert outcome.stderr == ""


def test_every_exit_code_of_the_table_is_driven() -> None:
    driven = {case[3] for case in CASES}
    assert {row.exit_code for row in ROWS} | {0, 2} <= driven
    assert driven == set(range(9))
