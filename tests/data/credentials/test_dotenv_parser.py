# tests/data/credentials/test_dotenv_parser.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The .env parser: literal values, nothing executed, errors by line number only."""

from __future__ import annotations

import secrets

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.data import ConfigError
from pyeconomics.data.credentials import parse_dotenv
from pyeconomics.data.credentials.dotenv import MAX_DOTENV_CHARACTERS


def test_names_values_comments_and_blank_lines() -> None:
    text = (
        "# pyeconomics keys\n"
        "\n"
        "FRED_API_KEY=first_value\n"
        "  BLS_API_KEY = second_value   # registered 2026\n"
        "BEA_API_KEY='single quoted'\n"
        'CENSUS_API_KEY="double # quoted"  # a comment\n'
        "OPENFIGI_API_KEY=\n"
        "EMPTY_QUOTED=''\n"
        "WITH_EQUALS=a=b\n"
        "AFTER_EQUALS= # nothing set\n"
        "TABBED\t=\tvalue\n"
    )
    assert parse_dotenv(text) == {
        "FRED_API_KEY": "first_value",
        "BLS_API_KEY": "second_value",
        "BEA_API_KEY": "single quoted",
        "CENSUS_API_KEY": "double # quoted",
        "OPENFIGI_API_KEY": "",
        "EMPTY_QUOTED": "",
        "WITH_EQUALS": "a=b",
        "AFTER_EQUALS": "",
        "TABBED": "value",
    }


def test_nothing_is_interpolated_expanded_or_unescaped() -> None:
    text = (
        "HOME_REF=$HOME\n"
        "BRACED='${HOME}'\n"
        'COMMAND="$(whoami)"\n'
        "TICKS=`whoami`\n"
        'ESCAPES="a\\nb\\tc"\n'
        "TILDE=~/keys\n"
    )
    assert parse_dotenv(text) == {
        "HOME_REF": "$HOME",
        "BRACED": "${HOME}",
        "COMMAND": "$(whoami)",
        "TICKS": "`whoami`",
        "ESCAPES": "a\\nb\\tc",
        "TILDE": "~/keys",
    }


def test_windows_line_endings_and_a_byte_order_mark() -> None:
    assert parse_dotenv("﻿FIRST=1\r\nSECOND='2'\r\n") == {
        "FIRST": "1",
        "SECOND": "2",
    }


@pytest.mark.parametrize(
    ("line", "problem"),
    [
        ("export FRED_API_KEY={value}", "uses export"),
        ("export\tFRED_API_KEY={value}", "uses export"),
        ("FRED_API_KEY {value}", "is not NAME=VALUE"),
        ("1FRED={value}", "does not start with a variable name"),
        ("FRED-KEY={value}", "does not start with a variable name"),
        ("FRED_API_KEY='{value}", "opens a quote"),
        ('FRED_API_KEY="{value}', "opens a quote"),
        ("FRED_API_KEY='{value}' trailing", "after its closing quote"),
        ("FRED_API_KEY={value} trailing", "with a space, a quote or a #"),
        ("FRED_API_KEY={value}#comment", "with a space, a quote or a #"),
        ("FRED_API_KEY=it's{value}", "with a space, a quote or a #"),
        ("FRED_API_KEY={value}\x00", "control character"),
        ("FRED_API_KEY={value}\rmore", "control character"),
    ],
)
def test_format_errors_name_the_line_and_never_its_content(
    line: str, problem: str
) -> None:
    value = secrets.token_hex(12)
    text = "# header\n\nOTHER=1\n" + line.format(value=value) + "\n"
    with pytest.raises(ConfigError, match=problem) as refused:
        parse_dotenv(text)
    message = str(refused.value)
    leaked = [name for name, text in {"message": message}.items() if value in text]
    assert leaked == []
    assert message.startswith(
        "line 4 of the .env file in the pyeconomics configuration directory "
    )


def test_a_repeated_name_is_an_error_naming_both_lines() -> None:
    with pytest.raises(ConfigError, match=r"line 3 .* set on line 1"):
        parse_dotenv("FRED_API_KEY=a\n# comment\nFRED_API_KEY=b\n")


def test_a_file_that_is_too_long_is_refused() -> None:
    with pytest.raises(ConfigError, match="longer than"):
        parse_dotenv("A=" + "b" * MAX_DOTENV_CHARACTERS)


_NAMES = st.from_regex(r"[A-Za-z_][A-Za-z0-9_]{0,30}", fullmatch=True)
_BARE = st.text(
    st.characters(
        codec="ascii", min_codepoint=0x21, max_codepoint=0x7E, exclude_characters="\"'#"
    ),
    max_size=40,
)
_QUOTED = st.text(
    st.characters(
        codec="ascii", min_codepoint=0x20, max_codepoint=0x7E, exclude_characters='"'
    ),
    max_size=40,
)


@given(st.dictionaries(_NAMES, _BARE, max_size=8))
def test_written_names_and_bare_values_read_back(values: dict[str, str]) -> None:
    lines = [f"{name}={value}" for name, value in values.items()]
    assert parse_dotenv("\n".join(lines)) == values


@given(st.dictionaries(_NAMES, _QUOTED, max_size=8))
def test_double_quoted_values_read_back_literally(values: dict[str, str]) -> None:
    lines = [f'{name}="{value}"' for name, value in values.items()]
    assert parse_dotenv("\n".join(lines)) == values
