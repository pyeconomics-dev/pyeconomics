# tests/models/macro/test_legacy_parity.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""``macro.policy_rule`` against every 0.2.x characterization fixture.

``tests/fixtures/legacy/`` records what ``pyeconomics==0.2.6`` returned (read
its README: "The Phase 3 contract"). Each case's inputs and parameters are mapped
onto ``macro.policy_rule`` (percent to decimal through ``percent_to_decimal``;
``alpha``, ``beta`` and ``okun_factor`` onto the weights and the Okun
coefficient; ``rho`` onto ``smoothing``; ``elb`` with ``apply_elb`` onto
``lower_bound``), run, converted back to percent and rounded to two decimals.
The historical tables are rebuilt by binding the synthetic panel's series as of
each row's date, with explicit as-of rules in place of 0.2.x's forward-fill.

Every value matches, or falls under one of the named differences below; each
test proves its cases are what the difference says, and the counts are
tabulated in the pull request body.

The mapping of 0.2.x's weights: 0.2.x put ``beta * okun_factor`` on the
unemployment gap in its Taylor rule, ``beta`` on it in the balanced-approach
rules, and 1 on its change in the first-difference rule. ``macro.policy_rule``
weighs a gap in output-gap units, so the balanced approach takes ``beta / 2``
at an Okun coefficient of 2, and the first-difference rule 0.5.
"""

from __future__ import annotations

import collections
import datetime as dt
import json
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

import pytest
from catalog_support import meta, month_end, period_ends
from scripted import registry_of, scripted

from pyeconomics.core import (
    AsOf,
    Binding,
    UnitKind,
    VintagePolicy,
    percent_to_decimal,
    run_model,
)
from pyeconomics.core.model import Model
from pyeconomics.data import (
    ObservationFrequency,
    SeasonalAdjustment,
    Series,
    UnitRecord,
    cache,
    catalog,
)
from pyeconomics.data.bindings import bind_model
from pyeconomics.data.catalog.definitions import Candidate, Concept
from pyeconomics.models.macro import policy_rule

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from pyeconomics.core.binding import Bound
    from pyeconomics.data.registry import ProviderRegistry

FIXTURES: Final = Path(__file__).resolve().parents[2] / "fixtures" / "legacy"

#: The named differences between 0.2.x and ``macro.policy_rule``, with why.
DIFFERENCES: Final = {
    "half_way_rounding": (
        "0.2.x rounded every result to two decimals. Where the exact result sits on "
        "a half-way value (x.xx5), 0.2.x's percent arithmetic and pyeconomics' "
        "decimal arithmetic land on either side of it in the last bit, so the two "
        "round apart by 0.01; results are no longer rounded."
    ),
    "lower_bound_after_smoothing": (
        "0.2.x floored the rule's rate at the lower bound and then smoothed it, so "
        "a smoothed rate could fall below the bound; pyeconomics smooths and then "
        "floors, so the prescription never sits below the bound "
        "(elb_floors_the_prescription)."
    ),
    "lagged_gap_held_for_a_quarter": (
        "0.2.x's historical first-difference table took the lagged unemployment gap "
        "before forward-filling the quarterly natural rate, so the second and third "
        "months of a quarter reused the first month's lagged gap; alignment is now "
        "explicit, and each month reads its own unemployment rate a year earlier."
    ),
}

RULES: Final = {
    "taylor_rule": "taylor_1993",
    "balanced_approach_rule": "balanced_approach",
    "balanced_approach_shortfalls_rule": "balanced_approach_shortfalls",
    "first_difference_rule": "first_difference",
}
LEVEL: Final = frozenset(
    {"taylor_1993", "balanced_approach", "balanced_approach_shortfalls"}
)


def load(name: str) -> dict[str, Any]:
    """Read one fixture file; they are read, never edited."""
    loaded: dict[str, Any] = json.loads(
        (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
    )
    return loaded


def _exact(value: float) -> Fraction:
    """The decimal a fixture prints, exactly (every input is a short decimal)."""
    return Fraction(repr(value))


# --- one rule at one point: 0.2.x's parameters on macro.policy_rule's inputs ----


def mapped(
    rule: str, point: Mapping[str, Any], params: Mapping[str, Any]
) -> dict[str, Any]:
    """Map 0.2.x's inputs (percent) and parameters onto the model's inputs."""
    inputs: dict[str, Any] = {
        "calculation": rule,
        "inflation": percent_to_decimal(point["inflation"]),
        "inflation_target": percent_to_decimal(params["inflation_target"]),
        "unemployment": percent_to_decimal(point["unemployment"]),
        "natural_unemployment": percent_to_decimal(point["natural"]),
        "inflation_weight": params["alpha"],
        "smoothing": params["rho"],
        "previous_rate": percent_to_decimal(point["fed_rate"]),
        "okun_coefficient": params.get("okun_factor", 2.0),
    }
    if params["apply_elb"]:
        inputs["lower_bound"] = percent_to_decimal(params["elb"])
    if rule == "taylor_1993":
        inputs["resource_weight"] = params["beta"]
    elif rule in LEVEL:
        inputs["resource_weight"] = params["beta"] / 2.0
    else:
        inputs["resource_weight"] = 0.5
        inputs["unemployment_lagged"] = percent_to_decimal(point["lagged_unemployment"])
        inputs["natural_unemployment_lagged"] = percent_to_decimal(
            point["lagged_natural"]
        )
    if rule in LEVEL:
        inputs["neutral_real_rate"] = percent_to_decimal(point["real_rate"])
    return inputs


def _notional(
    rule: str,
    point: Mapping[str, Any],
    params: Mapping[str, Any],
    lagged_gap: float | None = None,
) -> Fraction:
    """The rule's rate before the lower bound and the smoothing, exactly, in percent.

    ``lagged_gap`` replaces the first-difference rule's lagged gap with the one
    0.2.x's table recorded.
    """
    x = {k: _exact(v) for k, v in point.items()}
    alpha, target = _exact(params["alpha"]), _exact(params["inflation_target"])
    gap = x["natural"] - x["unemployment"]
    if rule == "first_difference":
        lagged = (
            x["lagged_natural"] - x["lagged_unemployment"]
            if lagged_gap is None
            else _exact(lagged_gap)
        )
        return x["fed_rate"] + alpha * (x["inflation"] - target) + gap - lagged
    if rule == "taylor_1993":
        weighted = _exact(params["beta"]) * _exact(params["okun_factor"]) * gap
    elif rule == "balanced_approach":
        weighted = _exact(params["beta"]) * gap
    else:
        weighted = _exact(params["beta"]) * min(gap, Fraction(0))
    return (
        x["real_rate"] + x["inflation"] + alpha * (x["inflation"] - target) + weighted
    )


def exact_prescription(
    rule: str,
    point: Mapping[str, Any],
    params: Mapping[str, Any],
    *,
    legacy: bool,
    lagged_gap: float | None = None,
) -> Fraction:
    """The prescription in percent, exactly: 0.2.x's order of operations, or ours."""
    rho, prev = _exact(params["rho"]), _exact(point["fed_rate"])
    notional = _notional(rule, point, params, lagged_gap if legacy else None)
    bound = _exact(params["elb"]) if params["apply_elb"] else None
    if legacy:
        floored = notional if bound is None else max(notional, bound)
        return rho * prev + (1 - rho) * floored
    smoothed = rho * prev + (1 - rho) * notional
    return smoothed if bound is None else max(smoothed, bound)


def _half_way(value: Fraction) -> bool:
    """Whether a percent value lies exactly half-way between two hundredths."""
    thousandths = value * 1000
    return thousandths.denominator == 1 and thousandths.numerator % 10 == 5


def classify(  # noqa: PLR0913 - a value, its inputs and what 0.2.x recorded
    rule: str,
    point: Mapping[str, Any],
    params: Mapping[str, Any],
    ours: float,
    expected: float,
    *,
    lagged_gap: float | None = None,
) -> str:
    """Name the difference a value falls under, proving it; "match" if none.

    ``lagged_gap`` is the lagged unemployment gap 0.2.x's historical
    first-difference table recorded for the row.
    """
    ours_percent = ours * 100
    if round(ours_percent, 2) == expected:
        return "match"
    ours_exact = exact_prescription(rule, point, params, legacy=False)
    legacy_exact = exact_prescription(
        rule, point, params, legacy=True, lagged_gap=lagged_gap
    )
    assert abs(Fraction(ours_percent) - ours_exact) < Fraction(1, 10**9)
    held = lagged_gap is not None and _exact(lagged_gap) != _exact(
        point["lagged_natural"]
    ) - _exact(point["lagged_unemployment"])
    if held:
        # 0.2.x's recorded lagged gap, in its order of operations, gives its value.
        assert abs(float(legacy_exact) - expected) <= 0.005 + 1e-9
        return "lagged_gap_held_for_a_quarter"
    if ours_exact != legacy_exact:
        # 0.2.x's order of operations, rounded as 0.2.x rounded, gives its value.
        assert abs(float(legacy_exact) - expected) <= 0.005 + 1e-9
        assert params["apply_elb"]
        assert params["rho"] > 0
        assert _notional(rule, point, params) < _exact(params["elb"])
        return "lower_bound_after_smoothing"
    assert _half_way(ours_exact), (
        rule,
        dict(point),
        dict(params),
        ours_percent,
        expected,
    )
    assert abs(ours_exact - _exact(expected)) == Fraction(1, 200)
    return "half_way_rounding"


def _point(inputs: Mapping[str, Any]) -> dict[str, Any]:
    """Name a fixture's ``EconomicIndicators`` fields as the mapping reads them."""
    point = {
        "inflation": inputs["current_inflation_rate"],
        "unemployment": inputs["current_unemployment_rate"],
        "natural": inputs["natural_unemployment_rate"],
        "fed_rate": inputs["current_fed_rate"],
        "real_rate": inputs["long_term_real_interest_rate"],
        "lagged_unemployment": inputs["lagged_unemployment_rate"],
        "lagged_natural": inputs["lagged_natural_unemployment_rate"],
    }
    return {k: v for k, v in point.items() if v is not None}


def _tally(counts: collections.Counter[str], outcome: str) -> None:
    assert outcome == "match" or outcome in DIFFERENCES
    counts[outcome] += 1


# --- the current-value rules ---------------------------------------------------


@pytest.mark.parametrize("name", sorted(RULES))
def test_every_case_of_a_rule_matches_or_has_a_named_difference(name: str) -> None:
    fixture = load(name)
    rule = RULES[name]
    counts: collections.Counter[str] = collections.Counter()
    for case in fixture["cases"]:
        assert "error" not in case, "0.2.x raised for no recorded case"
        point, params = _point(case["inputs"]), case["parameters"]
        result = run_model(policy_rule, mapped(rule, point, params))
        _tally(
            counts,
            classify(
                rule, point, params, result.outputs.prescribed_rate, case["result"]
            ),
        )
    assert sum(counts.values()) == fixture["case_count"] == len(fixture["cases"])
    assert counts["match"] > 0.8 * fixture["case_count"]


def test_the_combined_estimates_match_rule_by_rule() -> None:
    fixture = load("calculate_policy_rule_estimates")
    labels = {
        "Taylor Rule (TR)": "taylor_rule",
        "Balanced Approach Rule (BAR)": "balanced_approach_rule",
        "Balanced Approach Shortfalls Rule (BASR)": "balanced_approach_shortfalls_rule",
        "First Difference Rule (FDR)": "first_difference_rule",
    }
    defaults: dict[str, dict[str, float]] = {
        "taylor_rule": {"alpha": 0.5, "beta": 0.5, "okun_factor": 2.0},
        "balanced_approach_rule": {"alpha": 0.5, "beta": 2.0},
        "balanced_approach_shortfalls_rule": {"alpha": 0.5, "beta": 2.0},
        "first_difference_rule": {"alpha": 0.5},
    }
    counts: collections.Counter[str] = collections.Counter()
    for case in fixture["cases"]:
        point = _point(case["inputs"])
        table = case["result"]
        for label, row in zip(table["index"], table["data"], strict=True):
            name = labels[label]
            params = {**defaults[name], **case["arguments"]}
            outputs = run_model(policy_rule, mapped(RULES[name], point, params)).outputs
            _tally(
                counts,
                classify(RULES[name], point, params, outputs.prescribed_rate, row[0]),
            )
    assert sum(counts.values()) == 4 * fixture["case_count"]


# --- the historical tables: the panel bound as of each date -------------------

#: The 0.2.x series the panel holds, as test-only concepts that name each one.
PANEL_CONCEPTS: Final = {
    "PCETRIM12M159SFRBDAL": ("us.legacy.inflation", ObservationFrequency.MONTHLY),
    "UNRATE": ("us.legacy.unemployment", ObservationFrequency.MONTHLY),
    "NROU": ("us.legacy.natural_unemployment", ObservationFrequency.QUARTERLY),
    "DFII10": ("us.legacy.real_rate", ObservationFrequency.MONTHLY),
    "DFEDTARU": ("us.legacy.fed_target", ObservationFrequency.MONTHLY),
}

#: The legacy profile: each field read from the panel by an explicit rule. A
#: quarterly series is read for the quarter that contains the date, which is what
#: 0.2.x's forward-fill of first-of-quarter values gave each month.
LEGACY_BINDINGS: Final = (
    Binding("inflation", "us.legacy.inflation", profile="legacy"),
    Binding("unemployment", "us.legacy.unemployment", profile="legacy"),
    Binding(
        "natural_unemployment",
        "us.legacy.natural_unemployment",
        as_of=AsOf.PERIOD,
        profile="legacy",
    ),
    Binding("neutral_real_rate", "us.legacy.real_rate", profile="legacy"),
    Binding("previous_rate", "us.legacy.fed_target", profile="legacy"),
    Binding(
        "unemployment_lagged",
        "us.legacy.unemployment",
        transform="lag(periods=12)",
        profile="legacy",
    ),
    Binding(
        "natural_unemployment_lagged",
        "us.legacy.natural_unemployment",
        transform="lag(periods=4)",
        as_of=AsOf.PERIOD,
        profile="legacy",
    ),
)
LEGACY_MODEL: Final = Model(
    replace(policy_rule.spec, bindings=LEGACY_BINDINGS), policy_rule.compute
)
RATE: Final = UnitRecord(text="Decimal", kind=UnitKind.RATE)


def _panel_series(series_id: str, frequency: ObservationFrequency) -> Series:
    """One panel series as a provider delivers it: period-end dates, decimals."""
    raw = load("synthetic_panel")["series"][series_id]
    starts = [dt.date.fromisoformat(stamp[:10]) for stamp in raw["index"]]
    if frequency is ObservationFrequency.MONTHLY:
        index = tuple(month_end(day.year, day.month) for day in starts)
    else:
        first = starts[0]
        index = period_ends(frequency, (first.year, first.month + 2), len(starts))
    values = tuple(percent_to_decimal(v) for v in raw["values"])
    return Series(
        index,
        values,
        meta(
            frequency,
            provider="fred",
            series_id=series_id,
            unit=RATE,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        ),
    )


@pytest.fixture
def panel(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """A scripted ``fred`` serving the panel, and the concepts that name it."""
    concepts = dict(catalog.CONCEPTS)
    for series_id, (concept_id, frequency) in PANEL_CONCEPTS.items():
        concepts[concept_id] = Concept(
            id=concept_id,
            title=f"0.2.x series {series_id}",
            definition=f"The synthetic panel's {series_id}, as a decimal.",
            unit_kind=UnitKind.RATE,
            frequency=frequency,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            candidates=(Candidate(provider="fred", series=series_id),),
        )
    monkeypatch.setattr(catalog, "CONCEPTS", MappingProxyType(concepts))
    script = {
        series_id: _panel_series(series_id, frequency)
        for series_id, (_, frequency) in PANEL_CONCEPTS.items()
    }
    return registry_of(scripted("fred", script))


def _rows(
    table: Mapping[str, Any],
) -> Iterator[tuple[dt.date, dict[str, float | None]]]:
    """Each row of a split table, dated by its month's last day."""
    for stamp, row in zip(table["index"], table["data"], strict=True):
        day = dt.date.fromisoformat(stamp[:10])
        yield (
            month_end(day.year, day.month),
            dict(zip(table["columns"], row, strict=True)),
        )


def _bind(registry: ProviderRegistry, day: dt.date, rule: str) -> Bound:
    # The panel is not cached: a store round trip per series would only slow the
    # rebuild of several thousand rows.
    with cache.bypass():
        return bind_model(
            LEGACY_MODEL,
            as_of=day,
            profile="legacy",
            vintage=VintagePolicy.LATEST,
            overrides={"calculation": rule},
            registry=registry,
        )


#: Bound points by (date, rule family): the level rules read the same fields.
_POINTS: dict[tuple[dt.date, str], dict[str, float]] = {}


def _bound_point(
    registry: ProviderRegistry, day: dt.date, rule: str
) -> dict[str, float]:
    family = "first_difference" if rule == "first_difference" else "taylor_1993"
    key = (day, family)
    if key not in _POINTS:
        _POINTS[key] = _point_of(_bind(registry, day, family))
    return _POINTS[key]


def _percent(value: object) -> float:
    assert isinstance(value, float)
    return round(value * 100, 2)


#: Each historical fixture: its rule, the unadjusted and adjusted columns.
HISTORICAL: Final = {
    "historical_taylor_rule": ("taylor_rule", "TaylorRule", "AdjustedTaylorRule"),
    "historical_balanced_approach_rule": (
        "balanced_approach_rule",
        "BalancedApproachRule",
        "AdjustedBalancedApproachRule",
    ),
    "historical_balanced_approach_shortfalls_rule": (
        "balanced_approach_shortfalls_rule",
        "BalancedApproachShortfallsRule",
        "AdjustedBalancedApproachShortfallsRule",
    ),
    "historical_first_difference_rule": (
        "first_difference_rule",
        "FirstDifferenceRule",
        "AdjustedFirstDifferenceRule",
    ),
}
#: The panel's columns as 0.2.x named them, and the bound field each one is.
INPUT_COLUMNS: Final = {
    "Inflation": "inflation",
    "UnemploymentRate": "unemployment",
    "NaturalUnemploymentRate": "natural_unemployment",
    "RealInterestRate": "neutral_real_rate",
    "FedRate": "previous_rate",
    "LaggedUnemploymentRate": "unemployment_lagged",
    "LaggedNaturalUnemploymentRate": "natural_unemployment_lagged",
}


#: The bound fields, named as the mapping's point names them.
_POINT_NAMES: Final = {
    "inflation": "inflation",
    "unemployment": "unemployment",
    "natural_unemployment": "natural",
    "previous_rate": "fed_rate",
    "neutral_real_rate": "real_rate",
    "unemployment_lagged": "lagged_unemployment",
    "natural_unemployment_lagged": "lagged_natural",
}


def _point_of(bound: Bound) -> dict[str, float]:
    """The bound values in 0.2.x's percent, as the point the mapping reads."""
    assert bound.revised  # the panel keeps no vintages: labelled revised data
    return {
        _POINT_NAMES[field]: _percent(value)
        for field, value in bound.values.items()
        if field in _POINT_NAMES
    }


def _historical(
    registry: ProviderRegistry, name: str, counts: collections.Counter[str]
) -> dict[dt.date, dict[str, float]]:
    """Rebuild one historical fixture row by row; return our values by date."""
    legacy_name, plain_column, adjusted_column = HISTORICAL[name]
    rule = RULES[legacy_name]
    fixture = load(name)
    ours: dict[dt.date, dict[str, float]] = {}
    for case in fixture["cases"]:
        params = case["arguments"]
        for day, row in _rows(case["result"]):
            point = _bound_point(registry, day, rule)
            for column, field in INPUT_COLUMNS.items():
                if column in row:
                    assert point[_POINT_NAMES[field]] == row[column], (day, column)
            plain = {**params, "rho": 0.0, "apply_elb": False}
            for column, settings in ((plain_column, plain), (adjusted_column, params)):
                result = run_model(policy_rule, mapped(rule, point, settings))
                value = result.outputs.prescribed_rate
                expected = row[column]
                assert expected is not None
                recorded = row.get("LaggedUnemploymentGap")
                _tally(
                    counts,
                    classify(
                        rule, point, settings, value, expected, lagged_gap=recorded
                    ),
                )
                ours.setdefault(day, {})[f"{column}:{params['rho']}"] = value
    return ours


@pytest.mark.parametrize("name", sorted(HISTORICAL))
def test_each_historical_table_is_rebuilt_from_the_bound_panel(
    panel: ProviderRegistry, name: str
) -> None:
    counts: collections.Counter[str] = collections.Counter()
    _historical(panel, name, counts)
    fixture = load(name)
    rows = sum(len(case["result"]["index"]) for case in fixture["cases"])
    assert sum(counts.values()) == 2 * rows


def test_a_date_before_the_real_rate_begins_cannot_be_bound(
    panel: ProviderRegistry,
) -> None:
    # 0.2.x dropped the rows before DFII10's first month; a bind refuses them.
    from pyeconomics.data import DataError  # noqa: PLC0415

    with pytest.raises(DataError, match="real_rate"):
        _bind(panel, dt.date(2002, 12, 31), "taylor_1993")


def test_the_combined_historical_table_matches_its_rules(
    panel: ProviderRegistry,
) -> None:
    fixture = load("calculate_historical_policy_rates")
    # The combined table drops the column; the first-difference table recorded it.
    recorded = {
        day: row["LaggedUnemploymentGap"]
        for day, row in _rows(
            load("historical_first_difference_rule")["cases"][0]["result"]
        )
    }
    counts: collections.Counter[str] = collections.Counter()
    for case in fixture["cases"]:
        rho = case["arguments"]["rho"]
        for day, row in _rows(case["result"]):
            for legacy_name, plain, adjusted in HISTORICAL.values():
                if row[plain] is None:
                    continue
                rule = RULES[legacy_name]
                point = _bound_point(panel, day, rule)
                defaults = (
                    {"alpha": 0.5, "beta": 0.5, "okun_factor": 2.0}
                    if rule == "taylor_1993"
                    else {"alpha": 0.5, "beta": 2.0}
                    if rule in LEVEL
                    else {"alpha": 0.5}
                )
                base = {**defaults, "inflation_target": 2.0, "elb": 0.125}
                settings = {**base, **case["arguments"]}
                for column, chosen in (
                    (plain, {**base, "rho": 0.0, "apply_elb": False}),
                    (adjusted, settings),
                ):
                    outputs = run_model(
                        policy_rule, mapped(rule, point, chosen)
                    ).outputs
                    gap = recorded.get(day) if rule == "first_difference" else None
                    expected = row[column]
                    assert expected is not None
                    _tally(
                        counts,
                        classify(
                            rule,
                            point,
                            chosen,
                            outputs.prescribed_rate,
                            expected,
                            lagged_gap=gap,
                        ),
                    )
            assert row["FedRate"] is not None
        assert rho in {0.0, 0.7}
    assert counts["match"] > 0


def test_every_difference_is_named_with_its_reason() -> None:
    assert set(DIFFERENCES) == {
        "half_way_rounding",
        "lagged_gap_held_for_a_quarter",
        "lower_bound_after_smoothing",
    }
    assert all(len(reason) > 80 for reason in DIFFERENCES.values())
