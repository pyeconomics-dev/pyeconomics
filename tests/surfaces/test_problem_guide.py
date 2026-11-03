# tests/surfaces/test_problem_guide.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The problem guide holds one entry per row of the error table, in its order."""

from __future__ import annotations

import re

from pyeconomics.surfaces.budgets import local_data_command
from pyeconomics.surfaces.problem_guide import EXIT_CODES, GUIDES
from pyeconomics.surfaces.problems import ROWS

#: What no guide may hold: a URL beside the site's own, a host or a path.
_LEAK = re.compile(
    r"https?://(?!pyeconomics\.dev\b)|[A-Za-z]:\\|/home/|/Users/|run\.app"
)


def test_every_row_has_a_guide_in_the_tables_order() -> None:
    assert list(GUIDES) == [row.slug for row in ROWS]


def test_every_guide_says_what_it_means_and_what_to_do() -> None:
    for slug, guide in GUIDES.items():
        assert guide.meaning.endswith("."), slug
        assert guide.action.endswith("."), slug
        assert not _LEAK.search(guide.meaning + guide.action), slug


def test_only_problems_that_point_to_local_mode_carry_its_command() -> None:
    local = {slug for slug, guide in GUIDES.items() if guide.local}
    assert local == {"input-too-large", "budget-exceeded", "not-in-snapshot"}


def test_a_guides_own_command_is_the_local_data_command() -> None:
    commands = {slug: g.command for slug, g in GUIDES.items() if g.command}
    assert commands == {
        "not-in-snapshot": local_data_command("<series-or-concept>"),
    }
    assert all(GUIDES[slug].local for slug in commands)


def test_every_exit_code_the_table_uses_has_a_meaning() -> None:
    assert {row.exit_code for row in ROWS} <= set(EXIT_CODES)
    assert list(EXIT_CODES) == list(range(len(EXIT_CODES)))
