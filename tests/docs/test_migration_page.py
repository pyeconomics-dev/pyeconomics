# tests/docs/test_migration_page.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""docs/migration.md against the 0.2.x characterization fixtures.

Each worked example shows a 0.2.x call in a ``text`` block and its 1.0 form in the
``python`` block after it. Here the 0.2.x block must be a recorded case with the
result the page shows, and the 1.0 block must carry that case's inputs as decimals
and give the same number at two decimals, so the page cannot drift from what
``pyeconomics==0.2.6`` returned. The fixtures are read, never edited.

The table of public names must list everything 0.2.x exported and every option its
dataclasses had (read from the fixtures), and what it names in 1.0 must exist.
"""

from __future__ import annotations

import importlib.util
import json
import math
import re
from pathlib import Path
from typing import Any, Final

import pytest

import pyeconomics
from pyeconomics import data
from pyeconomics.core import percent_to_decimal
from pyeconomics.core.binding import calculations
from pyeconomics.models.macro import policy_rule

ROOT: Final = Path(__file__).resolve().parents[2]
PAGE: Final = ROOT / "docs" / "migration.md"
FIXTURES: Final = ROOT / "tests" / "fixtures" / "legacy"

#: ``__all__`` of pyeconomics 0.2.6 (legacy/0.2.x: pyeconomics/__init__.py).
PUBLIC: Final = (
    "BalancedApproachRuleParameters",
    "EconomicIndicators",
    "FirstDifferenceRuleParameters",
    "FredClient",
    "TaylorRuleParameters",
    "balanced_approach_rule",
    "calculate_historical_policy_rates",
    "calculate_policy_rule_estimates",
    "fetch_historical_fed_funds_rate",
    "first_difference_rule",
    "fred_client",
    "historical_balanced_approach_rule",
    "historical_first_difference_rule",
    "historical_taylor_rule",
    "load_from_cache",
    "plot_historical_bar_basr_rule",
    "plot_historical_fdr",
    "plot_historical_rule_estimates",
    "plot_historical_taylor_rule",
    "print_fred_series_names",
    "print_verbose_output",
    "save_to_cache",
    "taylor_rule",
    "verbose_balanced_approach_rule",
    "verbose_first_difference_rule",
    "verbose_taylor_rule",
)
#: ``FredClient``'s public methods (legacy/0.2.x: pyeconomics/api/fred_api.py).
METHODS: Final = (
    "fetch_data",
    "get_data_or_fetch",
    "get_historical_value",
    "get_latest_value",
    "get_series_name",
    "reset_instance",
)
#: The rule each 0.2.x function and shortfalls option is, and its fixture.
RULES: Final = {
    ("taylor_rule", False): ("taylor_1993", "taylor_rule"),
    ("balanced_approach_rule", False): ("balanced_approach", "balanced_approach_rule"),
    ("balanced_approach_rule", True): (
        "balanced_approach_shortfalls",
        "balanced_approach_shortfalls_rule",
    ),
    ("first_difference_rule", False): ("first_difference", "first_difference_rule"),
}
#: Each ``EconomicIndicators`` rate and the input it became.
FIELDS: Final = {
    "current_inflation_rate": "inflation",
    "current_unemployment_rate": "unemployment",
    "natural_unemployment_rate": "natural_unemployment",
    "long_term_real_interest_rate": "neutral_real_rate",
    "current_fed_rate": "previous_rate",
    "lagged_unemployment_rate": "unemployment_lagged",
    "lagged_natural_unemployment_rate": "natural_unemployment_lagged",
}
#: The 0.2.x parameters' defaults the examples leave out.
DEFAULTS: Final[dict[str, object]] = {
    "alpha": 0.5,
    "apply_elb": False,
    "elb": 0.125,
    "inflation_target": 2.0,
    "rho": 0.0,
    "use_shortfalls_rule": False,
    "verbose": False,
}
_EXAMPLE: Final = re.compile(
    r"^```text\n(>>> (\w+)\(\n.*?)^```\n\n```python\n(.*?)^```",
    re.MULTILINE | re.DOTALL,
)
_ARGUMENT: Final = re.compile(r"(\w+)=(True|False|-?\d+\.?\d*)")
_CALCULATION: Final = re.compile(r'calculation="(\w+)"')
_NUMBER: Final = re.compile(r"^(-?\d+\.\d+)$", re.MULTILINE)


def _value(text: str) -> bool | float:
    return text == "True" if text in {"True", "False"} else float(text)


def _load(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(
        (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
    )
    return loaded


def _examples() -> list[tuple[str, dict[str, Any], float, dict[str, Any], float]]:
    """Each example: the function, its arguments and number, then 1.0's."""
    found = []
    for old, function, new in _EXAMPLE.findall(PAGE.read_text(encoding="utf-8")):
        shown = _NUMBER.findall(old)
        arguments = {k: _value(v) for k, v in _ARGUMENT.findall(old)}
        run = {k: _value(v) for k, v in _ARGUMENT.findall(new)}
        run["calculation"] = _CALCULATION.findall(new)[0]
        found.append(
            (
                function,
                arguments,
                float(shown[-1]),
                run,
                float(_NUMBER.findall(new)[-1]),
            )
        )
    return found


def _case(fixture: dict[str, Any], arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the one recorded case these arguments are."""
    parameters = {
        **DEFAULTS,
        **{k: v for k, v in arguments.items() if k in DEFAULTS},
    }
    rates = {k: v for k, v in arguments.items() if k in FIELDS}
    hits = [
        case
        for case in fixture["cases"]
        if {k: case["inputs"][k] for k in FIELDS if case["inputs"][k] is not None}
        == rates
        and all(
            case["parameters"][k] == v
            for k, v in parameters.items()
            if k in case["parameters"]
        )
    ]
    assert len(hits) == 1, (arguments, len(hits))
    case: dict[str, Any] = hits[0]
    return case


def test_the_page_works_all_four_rules() -> None:
    examples = _examples()
    assert len(examples) == 4
    rules = {
        RULES[function, bool(arguments.get("use_shortfalls_rule"))][0]
        for function, arguments, *_ in examples
    }
    assert rules == {
        "taylor_1993",
        "balanced_approach",
        "balanced_approach_shortfalls",
        "first_difference",
    }


@pytest.mark.parametrize(
    "example", _examples(), ids=lambda example: example[3]["calculation"]
)
def test_an_example_equals_its_fixture(
    example: tuple[str, dict[str, Any], float, dict[str, Any], float],
) -> None:
    function, arguments, old_number, inputs, new_number = example
    shortfalls = bool(arguments.get("use_shortfalls_rule"))
    calculation, name = RULES[function, shortfalls]
    assert inputs["calculation"] == calculation
    case = _case(_load(name), arguments)
    assert case["result"] == old_number == new_number
    for old, new in FIELDS.items():
        if old in arguments:
            assert math.isclose(inputs[new], percent_to_decimal(arguments[old]))
    assert inputs["smoothing"] == case["parameters"]["rho"]
    assert case["parameters"]["apply_elb"]
    bound = percent_to_decimal(case["parameters"]["elb"])
    assert math.isclose(inputs["lower_bound"], bound)
    result = pyeconomics.run("macro.policy_rule", inputs)
    assert round(result.outputs.prescribed_rate * 100, 2) == case["result"]
    assert result.outputs.prescribed_rate > bound
    assert not result.warnings


def _table_names() -> set[str]:
    text = PAGE.read_text(encoding="utf-8")
    return set(re.findall(r"^\| `([^`]+)` ", text, re.MULTILINE))


def test_the_table_lists_every_public_name_and_method() -> None:
    names = _table_names()
    assert set(PUBLIC) <= names
    assert {f"FredClient.{method}" for method in METHODS} <= names


def test_the_table_lists_every_option_the_dataclasses_had() -> None:
    names = _table_names()
    for fixture in (
        "taylor_rule",
        "balanced_approach_rule",
        "first_difference_rule",
    ):
        case = _load(fixture)["cases"][0]
        assert set(case["inputs"]) | set(case["parameters"]) <= names, fixture


def test_every_concept_the_page_names_exists() -> None:
    text = PAGE.read_text(encoding="utf-8")
    named = set(re.findall(r"\b(us\.[a-z_]+\.[a-z_0-9.]+)\b", text))
    named = {name.removesuffix(".") for name in named}
    assert {"us.unemployment.noncyclical_rate", "us.treasury.real_10y"} <= named
    assert named <= set(data.catalog.ids())


def test_the_inputs_the_table_names_exist() -> None:
    fields: set[str] = set()
    for member in calculations(policy_rule.spec.inputs).values():
        fields |= set(member.model_fields)
    for new in (
        *FIELDS.values(),
        "inflation_target",
        "inflation_weight",
        "resource_weight",
        "okun_coefficient",
        "smoothing",
        "lower_bound",
    ):
        assert new in fields, new
        assert f"`{new}`" in PAGE.read_text(encoding="utf-8"), new


def test_the_outputs_the_table_names_exist() -> None:
    result = pyeconomics.run(
        "macro.policy_rule",
        calculation="taylor_1993",
        inflation=0.03,
        unemployment=0.04,
        natural_unemployment=0.04,
        neutral_real_rate=0.01,
    )
    text = PAGE.read_text(encoding="utf-8")
    for name in ("inflation_gap_term", "resource_gap_term", "unconstrained_rate"):
        assert f"`{name}`" in text
        assert hasattr(result.outputs, name)


def test_the_page_gives_the_end_of_life_in_adr_0003s_words() -> None:
    text = " ".join(PAGE.read_text(encoding="utf-8").split())
    assert (
        "0.2.x receives security fixes only and reaches end-of-life when pyeconomics "
        "1.0.0 is released" in text
    )


def test_the_page_names_each_difference_the_parity_test_proves() -> None:
    path = ROOT / "tests" / "models" / "macro" / "test_legacy_parity.py"
    spec = importlib.util.spec_from_file_location("legacy_parity_differences", path)
    assert spec is not None
    assert spec.loader is not None
    parity = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(parity)
    text = " ".join(PAGE.read_text(encoding="utf-8").split()).casefold()
    words = {
        "half_way_rounding": "half-way",
        "lower_bound_after_smoothing": "smooths and then floors",
        "lagged_gap_held_for_a_quarter": "lagged gap",
    }
    assert set(words) == set(parity.DIFFERENCES)
    assert all(word in text for word in words.values())
