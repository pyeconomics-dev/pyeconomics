# src/pyeconomics/data/catalog/international.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Inputs for policy rules in the euro area, the United Kingdom and Canada.

Inflation comes from Eurostat and the ECB (euro area) and the OECD (the United
Kingdom and Canada), policy rates from the BIS, output gaps from the OECD's
Economic Outlook, and neutral rates from the New York Fed's HLW estimates where
it publishes one (the euro area and Canada). The SDMX sources need the ``sdmx``
extra; a missing extra is recorded and the resolver tries the next candidate.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_NA: Final = SeasonalAdjustment.NOT_APPLICABLE
_SECTION: Final = "Other economies"
_OECD_CPI: Final = "OECD.SDD.TPS/DSD_PRICES@DF_PRICES_ALL/{area}.M.N.CPI.PA._T.N.GY"
_OECD_GAP: Final = "OECD.ECO.MAD/DSD_EO@DF_EO/{area}.GAP.A"
_NOTE_OECD: Final = (
    "The OECD's data are open with acknowledgement; a few series are marked "
    "exceptions, which the resolver treats as library-only."
)


def _cpi(economy: str, name: str, area: str) -> Concept:
    return Concept(
        id=f"{economy}.inflation.cpi.yoy",
        title=f"CPI inflation, {name}",
        definition=(
            f"The twelve-month change in the consumer price index for {name}, "
            "as the OECD publishes it, monthly, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.025 is 2.5%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        candidates=(
            Candidate(
                provider="oecd", series=_OECD_CPI.format(area=area), note=_NOTE_OECD
            ),
        ),
        section=_SECTION,
    )


def _gap(economy: str, name: str, area: str) -> Concept:
    return Concept(
        id=f"{economy}.output_gap.oecd",
        title=f"Output gap, {name}",
        definition=(
            f"The OECD Economic Outlook's output gap for {name}: actual less "
            "potential output as a decimal share of potential, annual, with "
            "the OECD's projections for the years ahead."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal share of potential GDP (-0.01 is 1% below)",
        frequency=ObservationFrequency.ANNUAL,
        seasonal_adjustment=_NA,
        candidates=(
            Candidate(
                provider="oecd", series=_OECD_GAP.format(area=area), note=_NOTE_OECD
            ),
        ),
        section=_SECTION,
    )


def _policy(economy: str, name: str, area: str) -> Concept:
    return Concept(
        id=f"{economy}.policy_rate.headline",
        title=f"Central bank policy rate, {name}",
        definition=(
            f"The policy rate of the central bank of {name} as the Bank for "
            "International Settlements records it, each day, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.04 is 4%)",
        frequency=ObservationFrequency.DAILY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="bis", series=f"BIS/WS_CBPOL/D.{area}"),),
        section=_SECTION,
    )


def _neutral(economy: str, name: str, column: str) -> Concept:
    return Concept(
        id=f"{economy}.neutral_rate.hlw",
        title=f"Natural rate of interest, Holston-Laubach-Williams ({name})",
        definition=(
            "The Holston-Laubach-Williams estimate of the real natural rate of "
            f"interest (r-star) for {name}, quarterly, as published by the "
            "Federal Reserve Bank of New York, as a decimal."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.01 is 1%)",
        frequency=ObservationFrequency.QUARTERLY,
        seasonal_adjustment=_NA,
        candidates=(Candidate(provider="nyfed", series="hlw", column=column),),
        notes=("Earlier editions are separate files (`hlw:2025Q1`), not vintages.",),
        section=_SECTION,
    )


CONCEPTS: Final = (
    Concept(
        id="ea.inflation.hicp.yoy",
        title="HICP inflation, euro area",
        definition=(
            "The twelve-month change in the euro area's harmonised index of "
            "consumer prices, all items, monthly, as a decimal. Eurostat's "
            "index gives the change; the ECB's published annual rate is the "
            "same measure."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.02 is 2%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_NA,
        candidates=(
            Candidate(
                provider="eurostat",
                series="ESTAT/prc_hicp_midx/M.I15.CP00.EA",
                transforms=("yoy",),
            ),
            Candidate(provider="ecb", series="ECB/ICP/M.U2.N.000000.4.ANR"),
        ),
        section=_SECTION,
    ),
    _cpi("gb", "the United Kingdom", "GBR"),
    _cpi("ca", "Canada", "CAN"),
    _policy("ea", "the euro area", "XM"),
    _policy("gb", "the United Kingdom", "GB"),
    _policy("ca", "Canada", "CA"),
    _gap("ea", "the euro area", "EA17"),
    _gap("gb", "the United Kingdom", "GBR"),
    _gap("ca", "Canada", "CAN"),
    _neutral("ea", "euro area", "rstar_Euro_Area"),
    _neutral("ca", "Canada", "rstar_Canada"),
)
