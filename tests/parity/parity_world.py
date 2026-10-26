# tests/parity/parity_world.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""A stand-in world in which every bound model's default profile binds (Step 10).

The catalog world (``tests/data/catalog/catalog_world.py``) stands in for every
installed provider with its real metadata, answering synthetic frames shaped as
each catalog candidate's source delivers them, so the resolver's gates, the
concepts' transforms and the binding layer run for real. Its histories are short
and straight, which is enough for the catalog but not for the models: a filter
reads 120 quarters, a GARCH 1,000 days, a regression collinear lines.

:func:`parity_world` gives the stand-ins what every bound model needs at
:data:`AS_OF`, combining what the domain tests give their own models
(tests/models/macro/test_launch_bindings.py, tests/models/asset_pricing/
test_factor_bindings.py, tests/models/equity/test_market_bindings.py):

- histories from 1960 (monthly and quarterly), 1950 (annual) and 2020 (daily);
- each series and table column its own wave, so regressions have something to
  fit, and the fiscal series scaled to shares of a stand-in GDP;
- Treasury's par curves every business day, rising with the tenor; the Board's
  Svensson parameters, Damodaran's year-end figures and Shiller's history at
  plausible levels;
- the Ken French files' real layouts (the factor columns, 25 portfolios, 12
  industries), with returns that differ by column.

:func:`bound_cases` lists every bound model's default-profile runs, and
:data:`GIVEN` the inputs that are not data for each.
"""

from __future__ import annotations

import datetime as dt
import math
import zlib
from dataclasses import replace
from typing import TYPE_CHECKING, Any, Final

import catalog_world
import numpy as np
from catalog_support import month_end

from pyeconomics import registry
from pyeconomics.core import UnitKind
from pyeconomics.core.binding import DEFAULT_PROFILE, calculations
from pyeconomics.data import ObservationFrequency, Series, Table

if TYPE_CHECKING:
    import pytest
    from pydantic import BaseModel

    from pyeconomics.core.model import Model
    from pyeconomics.data.registry import ProviderRegistry

__all__ = ["AS_OF", "GIVEN", "BoundCase", "bound_cases", "parity_world"]

#: The evaluation date of every bound run: the Treasury curves answer around it.
AS_OF: Final = dt.date(2026, 3, 15)

#: Five years of an asset's monthly returns, for the factor regressions.
_ASSET_RETURNS: Final = tuple(
    float(value) for value in 0.004 + 0.01 * np.sin(np.arange(60) / 3.0)
)

#: The inputs that are not data, by model and calculation.
GIVEN: Final[dict[tuple[str, str | None], dict[str, Any]]] = {
    ("asset_pricing.factor_regression", "capm"): {
        "returns": _ASSET_RETURNS,
        "periods_per_year": 12,
        "market_premium": 0.005,
    },
    **{
        ("asset_pricing.factor_regression", name): {
            "returns": _ASSET_RETURNS,
            "periods_per_year": 12,
        }
        for name in ("ff3", "carhart")
    },
    ("portfolio.black_litterman", None): {"market_weights": (1 / 12,) * 12},
    ("fixed_income.curve_fitting", "fit"): {"form": "nelson_siegel"},
    ("fixed_income.interest_rate_tree", "calibrate"): {"volatility": 0.1, "years": 10},
    ("fixed_income.interest_rate_tree", "value"): {
        "volatility": 0.1,
        "maturity_years": 10,
        "coupon_rate": 0.045,
        "option": "call",
        "exercise_years": [5],
        "exercise_prices": [100],
    },
    ("fixed_income.interest_rate_tree", "oas"): {
        "volatility": 0.1,
        "maturity_years": 5,
        "coupon_rate": 0.045,
        "price": 101.0,
    },
    ("fixed_income.interest_rate_tree", "effective"): {
        "volatility": 0.1,
        "maturity_years": 7,
        "coupon_rate": 0.04,
    },
    **{
        ("macro.output_gap", name): {"frequency": "quarterly"}
        for name in ("hp", "hamilton", "baxter_king", "christiano_fitzgerald")
    },
    ("macro.okun_law", "difference"): {"periods_per_year": 4},
    ("macro.neutral_rate", "constant"): {"real_rate": 0.005},
    ("macro.policy_rule", "path"): {
        "rule": "taylor_1993",
        "inflation_path": (0.03, 0.028, 0.026, 0.024, 0.022),
        "inflation_low_path": (0.025, 0.022, 0.02, 0.018, 0.016),
        "inflation_high_path": (0.035, 0.034, 0.032, 0.03, 0.028),
        "output_gap_path": (0.01, 0.008, 0.006, 0.004, 0.002),
        "output_gap_low_path": (0.0, -0.002, -0.004, -0.006, -0.008),
        "output_gap_high_path": (0.02, 0.018, 0.016, 0.014, 0.012),
    },
    **{
        ("econometrics.garch", name): {"periods_per_year": 252}
        for name in ("garch", "gjr", "egarch")
    },
}

# --- the histories --------------------------------------------------------------

_DAILY_FROM: Final = dt.date(2020, 1, 1)
_DAILY_TO: Final = dt.date(2026, 10, 12)


def _month_ends(
    first: tuple[int, int], last: tuple[int, int], step: int
) -> list[dt.date]:
    out = []
    line = first[0] * 12 + first[1] - 1
    while line <= last[0] * 12 + last[1] - 1:
        year, month = divmod(line, 12)
        out.append(month_end(year, month + 1))
        line += step
    return out


def _dates(frequency: ObservationFrequency, year_end: int) -> list[dt.date]:
    if frequency is ObservationFrequency.MONTHLY:
        return _month_ends((1960, 1), (2026, 9), 1)
    if frequency is ObservationFrequency.QUARTERLY:
        return _month_ends((1960, 3), (2026, 9), 3)
    if frequency is ObservationFrequency.ANNUAL:
        return _month_ends((1950, year_end), (2025, year_end), 12)
    days = [
        _DAILY_FROM + dt.timedelta(days=i)
        for i in range((_DAILY_TO - _DAILY_FROM).days + 1)
    ]
    if frequency in {ObservationFrequency.DAILY, ObservationFrequency.IRREGULAR}:
        return days
    return [day for day in days if day.weekday() < 5]


# --- the values -------------------------------------------------------------------

#: Treasury's par curves: a level rising with the tenor.
_CURVES: Final = {"treasury:par_nominal": 0.035, "treasury:par_real": 0.015}
#: Columns held at one value: the Board's Svensson parameters, Damodaran's figures.
_FIXED: Final = {
    "BETA0": 0.045,
    "BETA1": -0.01,
    "BETA2": -0.02,
    "BETA3": 0.015,
    "TAU1": 1.5,
    "TAU2": 9.0,
    "s_p_500_3": 5000.0,
    "dividends_buybacks_6": 160.0,
    "analyst_growth_estimate_14": 0.06,
}
#: Shiller's columns, growing slowly from these levels.
_SHILLER: Final = {"price": 1000.0, "earnings": 50.0, "cpi": 150.0}
#: Net lending and interest as shares of a stand-in GDP of about 100.
_FISCAL: Final = {"bea:NIPA/T30200/Q/49": -0.05, "bea:NIPA/T30200/Q/33": 0.02}
#: The Ken French files' columns, as the real files name them.
_FRENCH_LAYOUTS: Final = {
    "ff3": ("Mkt-RF", "SMB", "HML", "RF"),
    "ff5": ("Mkt-RF", "SMB", "HML", "RMW", "CMA", "RF"),
    "momentum": ("Mom",),
}
_FRENCH_WIDTHS: Final = {"size_bm25": 25, "industry12": 12}
_RATES: Final = {UnitKind.RATE, UnitKind.RATIO, UnitKind.RETURN}

_original_frame = catalog_world._frame  # noqa: SLF001 - wrapped below


def _wave(
    values: tuple[float | None, ...], key: str, *, rate: bool
) -> tuple[float | None, ...]:
    """Give a series its own wave and noise: additive for a rate, else relative.

    A line plus a sine is an exact autoregression, so a regression on it has
    almost no residuals and whether its standard errors are defined comes down
    to the platform's rounding; seeded noise, a tenth of the wave, keeps every
    fit well posed on every platform.
    """
    seed = zlib.crc32(key.encode())
    phase = seed % 628 / 100
    noise = np.random.default_rng(seed).normal(0.0, 0.1, len(values))
    out: list[float | None] = []
    for i, value in enumerate(values):
        if value is None:
            out.append(None)
            continue
        wave = math.sin(i / 4 + phase) + float(noise[i])
        out.append(value + 0.004 * wave if rate else value * (1 + 0.02 * wave))
    return tuple(out)


def _returns(name: str, count: int) -> tuple[float, ...]:
    """Returns that differ by column: seeded draws around 0.5% a period."""
    rng = np.random.default_rng(zlib.crc32(name.encode()))
    if name.endswith(":RF"):
        return tuple(float(v) for v in rng.uniform(0.0, 0.004, count))
    return tuple(float(v) for v in rng.normal(0.005, 0.04, count))


def _french(frame: Table, series_key: str) -> Table:
    count = len(frame.index)
    stem = series_key.split(":", maxsplit=1)[0]
    template = frame.columns[0]
    width = _FRENCH_WIDTHS.get(stem)
    names = (
        tuple(f"p{k + 1}" for k in range(width))
        if width is not None
        else _FRENCH_LAYOUTS[stem]
    )
    return replace(
        frame,
        columns=tuple(replace(template, name=name) for name in names),
        data=tuple(_returns(f"{series_key}:{name}", count) for name in names),
    )


def _source_tenor(name: str) -> float:
    """Read Treasury's column name (BC_3MONTH, TC_10YEAR) as years."""
    count = int("".join(ch for ch in name if ch.isdigit()))
    return count / 12 if name.endswith("MONTH") else float(count)


def _curve(frame: Table, level: float) -> Table:
    """A curve every business day of 2025 on: higher at longer tenors, drifting."""
    first = dt.date(2025, 1, 1)
    days = tuple(
        day
        for day in (first + dt.timedelta(days=i) for i in range(650))
        if day.weekday() < 5
    )
    data = tuple(
        tuple(
            level + 0.012 * (1 - math.exp(-_source_tenor(column.name) / 6)) + 1e-5 * i
            for i in range(len(days))
        )
        for column in frame.columns
    )
    realtime = None if frame.realtime is None else (frame.realtime[0],) * len(days)
    return replace(frame, index=days, data=data, realtime=realtime)


def _table(frame: Table, key: str) -> Table:
    data: list[tuple[float | None, ...]] = []
    for n, (column, values) in enumerate(zip(frame.columns, frame.data, strict=True)):
        if column.name in _FIXED:
            data.append(tuple(_FIXED[column.name] for _ in values))
        elif key == "shiller:us_equity" and column.name in _SHILLER:
            base = _SHILLER[column.name]
            data.append(tuple(base * (1 + 0.002 * i) for i in range(len(values))))
        else:
            rate = column.unit.kind in _RATES
            data.append(_wave(values, f"{key}:{n}", rate=rate))
    return replace(frame, data=tuple(data))


def _frame(
    info_id: str,
    terms: object,
    users: list[Any],
    series_key: str,
    *,
    vintaged: bool,
) -> Series | Table:
    frame = _original_frame(info_id, terms, users, series_key, vintaged=vintaged)
    key = f"{info_id}:{series_key}"
    if any("changes_only" in t for _, c in users for t in c.transforms):
        return frame  # a step series: its steps are what the concept reads
    if isinstance(frame, Table):
        if key in _CURVES:
            return _curve(frame, _CURVES[key])
        if info_id == "ken_french":
            return _french(frame, series_key)
        return _table(frame, key)
    values = _wave(frame.values, key, rate=frame.meta.unit.kind in _RATES)
    scale = _FISCAL.get(key)
    if scale is not None:
        values = tuple(None if v is None else v * scale for v in values)
    return replace(frame, values=values)


def parity_world(monkeypatch: pytest.MonkeyPatch) -> ProviderRegistry:
    """Make the long, wavy stand-ins the installed providers, and return them."""
    from pyeconomics.data import registry as data_registry  # noqa: PLC0415

    monkeypatch.setattr(catalog_world, "_dates", _dates)
    monkeypatch.setattr(catalog_world, "_frame", _frame)
    world = catalog_world.world_registry()
    monkeypatch.setattr(data_registry._CACHE, "registry", world)  # noqa: SLF001
    return world


# --- the runs --------------------------------------------------------------------

#: One bound run: a model, its calculation (``None`` for a single one).
BoundCase = tuple[str, str | None]


def _default_fields(model: Model[Any, Any]) -> set[str]:
    return {b.field for b in model.spec.bindings if b.profile == DEFAULT_PROFILE}


def _served(model: Model[Any, Any], member: type[BaseModel]) -> bool:
    """Whether the default profile serves a calculation.

    It does when it binds some of the calculation's fields and none of the
    calculation's required fields is bound only by another profile: the Solow
    steady state binds no data, and the five-factor regression needs factors
    only the ``ff5`` profile binds.
    """
    fields = _default_fields(model)
    elsewhere = {b.field for b in model.spec.bindings} - fields
    required = {
        name for name, info in member.model_fields.items() if info.is_required()
    }
    return bool(fields & set(member.model_fields)) and not required & elsewhere


def bound_cases() -> list[BoundCase]:
    """Every bound model's default-profile runs: one per calculation it serves."""
    cases: list[BoundCase] = []
    for model in registry.models():
        if not _default_fields(model):
            continue
        family = calculations(model.spec.inputs)
        if not family:
            cases.append((model.id, None))
            continue
        cases.extend(
            (model.id, name)
            for name, member in sorted(family.items())
            if _served(model, member)
        )
    return cases


def inputs_for(case: BoundCase) -> dict[str, Any]:
    """The inputs a bound run sends beside its bind: the calculation and ``GIVEN``."""
    model_id, calculation = case
    given = dict(GIVEN.get(case, {}))
    if calculation is not None:
        given["calculation"] = calculation
    del model_id
    return given
