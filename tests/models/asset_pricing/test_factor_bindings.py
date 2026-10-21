# tests/models/asset_pricing/test_factor_bindings.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""The four Step 16 models bind every profile through the catalog, offline.

The providers are the catalog world's stand-ins (``catalog_world.py``), so the
resolver's gates, the concepts and the binding layer run for real. This module
gives the Ken French stand-ins what the models need: monthly history from 1990
(enough for a 120-month window), returns that differ by column (the stand-ins'
straight lines would make every factor collinear), and the 25 size and
book-to-market portfolios and 12 industries the real files hold.
"""

from __future__ import annotations

import datetime as dt
import zlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any

import catalog_world
import numpy as np
import pytest
from catalog_support import month_end
from pydantic import BaseModel

from pyeconomics.core import AsOf, InputError, run_model
from pyeconomics.core.binding import REVISED_DATA, calculations
from pyeconomics.data import ObservationFrequency, Series, Table
from pyeconomics.data.bindings import bind_model
from pyeconomics.models.asset_pricing import factor_model_tests, factor_regression
from pyeconomics.models.portfolio import black_litterman, risk_based_allocation

if TYPE_CHECKING:
    from pyeconomics.core import Model
    from pyeconomics.data.registry import ProviderRegistry

AS_OF = dt.date(2026, 3, 15)
#: The world's monthly stand-ins end in September 2026, so the windows end in
#: February 2026, the last month on or before the date.
LAST_MONTH = month_end(2026, 2)
RETURNS = tuple(0.004 + 0.01 * np.sin(np.arange(60) / 3.0))
GIVEN: dict[tuple[str, str | None], dict[str, Any]] = {
    ("asset_pricing.factor_regression", "capm"): {
        "returns": RETURNS,
        "periods_per_year": 12,
        "market_premium": 0.005,
    },
    **{
        ("asset_pricing.factor_regression", name): {
            "returns": RETURNS,
            "periods_per_year": 12,
        }
        for name in ("ff3", "carhart", "ff5", "ff6")
    },
    ("asset_pricing.factor_model_tests", "grs"): {},
    ("asset_pricing.factor_model_tests", "fama_macbeth"): {},
    ("portfolio.black_litterman", None): {"market_weights": (1 / 12,) * 12},
    **{
        ("portfolio.risk_based_allocation", name): {}
        for name in (
            "inverse_volatility",
            "equal_risk_contribution",
            "hierarchical_risk_parity",
        )
    },
}
#: Each profile of the factor regression binds the calculations it names.
SERVED = {
    "default": {"capm", "ff3", "carhart"},
    "ff5": {"capm", "ff3", "carhart", "ff5", "ff6"},
}
_WIDTHS = {"size_bm25": 25, "industry12": 12}
#: The factor files' columns, as the real files name them.
_LAYOUTS = {
    "ff3": ("Mkt-RF", "SMB", "HML", "RF"),
    "ff5": ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"),
    "momentum": ("Mom",),
}

_original_dates = catalog_world._dates  # noqa: SLF001 - lengthened below
_original_frame = catalog_world._frame  # noqa: SLF001


def _long_dates(frequency: ObservationFrequency, year_end: int) -> list[dt.date]:
    """Monthly data from 1990, so a window of 120 months fits."""
    if frequency is ObservationFrequency.MONTHLY:
        return [month_end(1990 + k // 12, k % 12 + 1) for k in range(441)]
    return _original_dates(frequency, year_end)


def _wavy(name: str, count: int) -> tuple[float, ...]:
    """Returns that differ by column: a seeded random walk around 0.5% a month."""
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    if name == "RF":
        return tuple(float(v) for v in rng.uniform(0.0, 0.004, count))
    return tuple(float(v) for v in rng.normal(0.005, 0.04, count))


def _frame(
    info_id: str,
    terms: object,
    users: list[Any],
    series_key: str,
    *,
    vintaged: bool,
) -> Series | Table:
    frame = _original_frame(info_id, terms, users, series_key, vintaged=vintaged)
    if info_id != "ken_french" or not isinstance(frame, Table):
        return frame
    count = len(frame.index)
    width = _WIDTHS.get(series_key.split(":", maxsplit=1)[0])
    if width is not None:
        template = frame.columns[0]
        columns = tuple(replace(template, name=f"p{k + 1}") for k in range(width))
        data = tuple(_wavy(f"{series_key}:{k}", count) for k in range(width))
        return replace(frame, columns=columns, data=data)
    names = _LAYOUTS[series_key.split(":", maxsplit=1)[0]]
    template = frame.columns[0]
    return replace(
        frame,
        columns=tuple(replace(template, name=name) for name in names),
        data=tuple(_wavy(f"{series_key}:{name}", count) for name in names),
    )


@pytest.fixture
def world(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """Every installed provider's stand-in, with Ken French returns that vary."""
    monkeypatch.setattr(catalog_world, "_dates", _long_dates)
    monkeypatch.setattr(catalog_world, "_frame", _frame)
    return catalog_world.world_registry()


def _cases() -> list[tuple[Model[Any, Any], str, str | None]]:
    cases = []
    for model in (
        factor_regression,
        factor_model_tests,
        black_litterman,
        risk_based_allocation,
    ):
        profiles = dict.fromkeys(b.profile for b in model.spec.bindings)
        family = calculations(model.spec.inputs)
        for profile in profiles:
            for calculation in family or [None]:
                if model is factor_regression and calculation not in SERVED[profile]:
                    continue
                cases.append((model, profile, calculation))
    return cases


@pytest.mark.parametrize(
    ("model", "profile", "calculation"),
    _cases(),
    ids=lambda value: getattr(value, "id", value),
)
def test_every_profile_binds_and_runs(
    model: Model[Any, Any],
    profile: str,
    calculation: str | None,
    world: ProviderRegistry,
) -> None:
    given = dict(GIVEN[model.id, calculation])
    if calculation is not None:
        given["calculation"] = calculation
    bound = bind_model(
        model, profile=profile, as_of=AS_OF, overrides=given, registry=world
    )
    result = run_model(model, bound)
    members = (
        [calculations(model.spec.inputs)[calculation]]
        if calculation is not None
        else [
            m
            for m in model.spec.input_models
            if isinstance(m, type) and issubclass(m, BaseModel)
        ]
    )
    taken = {name for member in members for name in member.model_fields}
    expected = {
        binding.field
        for binding in model.spec.bindings
        if binding.profile == profile and binding.field in taken
    }
    bound_fields = {
        r.field for r in result.manifest.data_sources if r.provider != "user"
    }
    assert bound_fields == expected - set(given)
    for record in result.manifest.data_sources:
        if record.provider == "user":
            continue
        assert record.observation_end == LAST_MONTH
        assert REVISED_DATA in record.warnings  # Ken French keeps no vintages


def test_the_factor_tests_read_ten_years_of_25_portfolios_and_three_factors(
    world: ProviderRegistry,
) -> None:
    bound = bind_model(
        factor_model_tests,
        as_of=AS_OF,
        overrides={"calculation": "grs"},
        registry=world,
    )
    returns, factors = bound.values["returns"], bound.values["factors"]
    assert isinstance(returns, tuple)
    assert isinstance(factors, tuple)
    assert len(returns) == len(factors) == 120
    assert {len(row) for row in returns} == {25}
    assert {len(row) for row in factors} == {3}
    risk_free = bound.values["risk_free"]
    assert isinstance(risk_free, tuple)
    assert len(risk_free) == 120
    result = run_model(factor_model_tests, bound)
    assert result.outputs.denominator_degrees_of_freedom == 120 - 25 - 3


def test_the_factor_bindings_window_is_five_years(world: ProviderRegistry) -> None:
    binding = next(b for b in factor_regression.spec.bindings if b.field == "market")
    assert binding.as_of is AsOf.WINDOW
    assert binding.window == 60
    bound = bind_model(
        factor_regression,
        as_of=AS_OF,
        overrides=GIVEN["asset_pricing.factor_regression", "ff3"]
        | {"calculation": "ff3"},
        registry=world,
    )
    by_field = {r.field: r for r in bound.sources}
    assert by_field["size"].concept == "factors.ff3_smb.us.monthly"
    assert by_field["market"].observation_start == month_end(2021, 3)


def test_the_five_factor_calculations_need_the_ff5_profile(
    world: ProviderRegistry,
) -> None:
    bound = bind_model(
        factor_regression,
        as_of=AS_OF,
        overrides=GIVEN["asset_pricing.factor_regression", "ff5"]
        | {"calculation": "ff5"},
        registry=world,
    )
    assert "profitability" not in bound.values
    with pytest.raises(InputError, match="profitability"):
        run_model(factor_regression, bound)


def test_the_cards_carry_the_ken_french_notice() -> None:
    from pyeconomics.core import ModelCard  # noqa: PLC0415
    from pyeconomics.data.bindings import candidate_notes  # noqa: PLC0415

    for model in (
        factor_regression,
        factor_model_tests,
        black_litterman,
        risk_based_allocation,
    ):
        notes = candidate_notes(model)
        assert notes
        for candidates in notes.values():
            assert [c.provider for c in candidates] == ["ken_french"]
            assert all("Fama" in (c.notice or "") for c in candidates)
        card = ModelCard.from_model(model, candidates=notes).to_markdown()
        assert "library-only" in card
