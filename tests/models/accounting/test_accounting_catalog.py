# tests/models/accounting/test_accounting_catalog.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""DuPont cancellation, historical scoring coefficients and undefined ratios."""

from __future__ import annotations

from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from pyeconomics.core import run_model
from pyeconomics.models.accounting import financial_ratios, scoring_models

POSITIVE = st.floats(1, 1e4)
ALT_NAMES = (
    "working_capital_to_assets",
    "retained_earnings_to_assets",
    "ebit_to_assets",
    "market_equity_to_liabilities",
    "sales_to_assets",
)
M_NAMES = ("dsri", "gmi", "aqi", "sgi", "depi", "sgai", "tata", "lvgi")
F_NAMES = (
    "positive_roa",
    "positive_cfo",
    "improving_roa",
    "cash_exceeds_income",
    "decreasing_leverage",
    "improving_liquidity",
    "no_equity_issuance",
    "improving_margin",
    "improving_turnover",
)


@pytest.mark.invariant("accounting.financial_ratios", "dupont_three_step_equals_roe")
@pytest.mark.invariant("accounting.financial_ratios", "dupont_five_step_equals_roe")
@given(
    revenue=POSITIVE,
    assets=POSITIVE,
    equity=POSITIVE,
    ebit=POSITIVE,
    pretax=POSITIVE,
    net=st.floats(-100, 100),
)
def test_dupont_cancels(  # noqa: PLR0913 - independent DuPont factors
    *,
    revenue: float,
    assets: float,
    equity: float,
    ebit: float,
    pretax: float,
    net: float,
) -> None:
    raw = dict(financial_ratios.spec.examples[0].inputs)
    raw.update(
        revenue=revenue,
        average_assets=assets,
        average_equity=equity,
        ebit=ebit,
        pretax_income=pretax,
        net_income=net,
    )
    out = run_model(financial_ratios, raw).outputs
    assert out.dupont_three_step == pytest.approx(out.roe, abs=1e-9)
    assert out.dupont_five_step == pytest.approx(out.roe, abs=1e-9)


@pytest.mark.invariant("accounting.scoring_models", "z_score_linear_in_ratios")
@given(ratios=st.lists(st.floats(0, 10), min_size=5, max_size=5), scale=st.floats(0, 5))
def test_altman_is_linear(ratios: list[float], scale: float) -> None:
    first = run_model(
        scoring_models,
        {"calculation": "altman_z", **dict(zip(ALT_NAMES, ratios, strict=True))},
    ).outputs.z_score
    second = run_model(
        scoring_models,
        {
            "calculation": "altman_z",
            **dict(zip(ALT_NAMES, [r * scale for r in ratios], strict=True)),
        },
    ).outputs.z_score
    assert second == pytest.approx(scale * first, abs=1e-10)


@pytest.mark.invariant("accounting.scoring_models", "f_score_between_zero_and_nine")
@given(signals=st.lists(st.booleans(), min_size=9, max_size=9))
def test_piotroski_is_a_binary_sum(signals: list[bool]) -> None:
    out = run_model(
        scoring_models,
        {"calculation": "piotroski_f", **dict(zip(F_NAMES, signals, strict=True))},
    ).outputs
    assert 0 <= out.f_score <= 9
    assert out.f_score == sum(signals)
    assert [getattr(out, name) for name in F_NAMES] == list(map(int, signals))


@pytest.mark.invariant("accounting.scoring_models", "m_score_matches_coefficients")
@given(values=st.lists(st.floats(0, 10), min_size=8, max_size=8))
def test_beneish_matches_original_decimal_coefficients(values: list[float]) -> None:
    # Decimal arithmetic is independent of the model's float products/fsum.
    from decimal import Decimal  # noqa: PLC0415 - oracle used only here

    coefficients = list(
        map(
            Decimal, [".920", ".528", ".404", ".892", ".115", "-.172", "4.679", "-.327"]
        )
    )
    expected = Decimal("-4.84") + sum(
        (c * Decimal(str(v)) for c, v in zip(coefficients, values, strict=True)),
        Decimal(0),
    )
    out = run_model(
        scoring_models,
        {"calculation": "beneish_m", **dict(zip(M_NAMES, values, strict=True))},
    ).outputs
    assert out.m_score == pytest.approx(float(expected), abs=1e-10)


def test_zero_denominators_preserve_other_ratios() -> None:
    raw = dict(financial_ratios.spec.examples[0].inputs)
    raw.update(
        current_liabilities=0, average_inventory=0, revenue=0, ebit=0, pretax_income=0
    )
    result = run_model(financial_ratios, raw)
    assert result.outputs.current_ratio is None
    assert result.outputs.inventory_turnover is None
    assert result.outputs.dupont_three_step is None
    assert result.outputs.dupont_five_step is None
    assert result.outputs.roe == 0.3
    assert result.warnings


def test_ratios_outside_bounds_warn() -> None:
    raw = dict(financial_ratios.spec.examples[0].inputs)
    raw.update(current_liabilities=5e-324, average_equity=5e-324)
    result = run_model(financial_ratios, raw)
    assert result.outputs.current_ratio is None
    assert result.outputs.roe is None
    assert any(w.code == "unrepresentable_ratio" for w in result.warnings)


@pytest.mark.parametrize(
    ("score", "zone"), [(1.0, "distress"), (2.0, "grey"), (3.0, "safe")]
)
def test_altman_bands(score: float, zone: str) -> None:
    values: dict[str, Any] = dict.fromkeys(ALT_NAMES, 0)
    values["sales_to_assets"] = score / 0.999
    result = run_model(scoring_models, {"calculation": "altman_z", **values})
    assert result.outputs.zone == zone
