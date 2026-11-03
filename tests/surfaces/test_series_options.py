# tests/surfaces/test_series_options.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Every surface takes the same series options (Phase 5 Step 9).

``surfaces.series.SERIES_OPTIONS`` is the one list: the REST route reads it from
its query, MCP's ``get_series`` from its arguments, and both hand the text to
``series_arguments``, which gives ``data.get`` its keyword arguments. Each
surface's description of the options (the OpenAPI parameters, the tool's input
schema, the command's signature) must name exactly those options, so an option
cannot reach one surface and miss another.
"""

from __future__ import annotations

import datetime as dt
import inspect

import pytest

from pyeconomics.cli.data_commands import get_data
from pyeconomics.core import InputError
from pyeconomics.data import api
from pyeconomics.mcp import schemas
from pyeconomics.surfaces.series import (
    DATE_OPTIONS,
    SERIES_OPTIONS,
    SeriesArguments,
    series_arguments,
)


def test_the_options_are_data_gets_keyword_arguments() -> None:
    assert SeriesArguments.__optional_keys__ == frozenset(SERIES_OPTIONS)
    parameters = inspect.signature(api.get).parameters
    for name in SERIES_OPTIONS:
        assert parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert set(SERIES_OPTIONS) > DATE_OPTIONS


def test_the_text_of_each_option_becomes_its_argument() -> None:
    sent = {
        "start": "2020-01-01",
        "end": "2020-12-31",
        "as_of": "2021-03-01",
        "vintage": "latest",
        "provider": "bls",
        "transform": "yoy",
        "format": "csv",
    }
    assert series_arguments(sent) == {
        "start": dt.date(2020, 1, 1),
        "end": dt.date(2020, 12, 31),
        "as_of": dt.date(2021, 3, 1),
        "vintage": "latest",
        "provider": "bls",
        "transform": "yoy",
    }
    assert series_arguments({}) == {}


@pytest.mark.parametrize("name", sorted(DATE_OPTIONS))
def test_a_date_option_that_is_not_a_date_is_an_input_error(name: str) -> None:
    with pytest.raises(InputError, match=name):
        series_arguments({name: "soon"})


def test_the_tools_input_schema_names_the_options() -> None:
    properties = schemas.series_input()["properties"]
    assert tuple(properties) == ("target", *SERIES_OPTIONS)


def test_the_openapi_operation_names_the_options() -> None:
    pytest.importorskip("fastapi")
    from pyeconomics.server.openapi import series_operation  # noqa: PLC0415

    names = [parameter["name"] for parameter in series_operation()["parameters"]]
    assert names == ["target", *SERIES_OPTIONS, "format"]


def test_the_command_takes_the_options() -> None:
    parameters = inspect.signature(get_data).parameters
    assert set(SERIES_OPTIONS) <= set(parameters)
