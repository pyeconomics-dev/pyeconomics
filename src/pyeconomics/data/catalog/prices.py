# src/pyeconomics/data/catalog/prices.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""United States price indexes and inflation rates.

Price levels come from the statistical agencies that compute them (BEA for the
PCE indexes, BLS for the CPI), with FRED as the library-only fallback on the
user's own key. Year-over-year inflation is the ``yoy`` transform of the level,
so one definition holds across sources and a rate is always a decimal.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept, Tier
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS"]

_SECTION: Final = "Prices and inflation"
_BEA_NOTE: Final = (
    "BEA's API serves current estimates only, so a run on it records "
    "revised_data; ask for a vintage and the resolver prefers FRED's ALFRED."
)


def _level(  # noqa: PLR0913, PLR0917 - an id, its words, its seasonality, two sources
    concept_id: str,
    title: str,
    definition: str,
    seasonal: SeasonalAdjustment,
    originator: Candidate,
    aggregator: Candidate,
) -> Concept:
    return Concept(
        id=concept_id,
        title=title,
        definition=definition,
        unit_kind=UnitKind.INDEX_LEVEL,
        unit_text="index level, base year as the source sets it",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=seasonal,
        candidates=(originator, aggregator),
        section=_SECTION,
    )


def _yoy(  # noqa: PLR0913, PLR0917 - an id, its words, its seasonality, two sources
    concept_id: str,
    title: str,
    definition: str,
    seasonal: SeasonalAdjustment,
    originator: Candidate,
    aggregator: Candidate,
) -> Concept:
    return Concept(
        id=concept_id,
        title=title,
        definition=definition,
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.025 is 2.5%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=seasonal,
        candidates=(originator, aggregator),
        section=_SECTION,
    )


_SA = SeasonalAdjustment.SEASONALLY_ADJUSTED
_NSA = SeasonalAdjustment.NOT_SEASONALLY_ADJUSTED
_YOY = ("yoy",)

CONCEPTS: Final = (
    _level(
        "us.prices.pce",
        "PCE price index",
        "The chain-type price index of US personal consumption expenditures, "
        "monthly and seasonally adjusted, the price measure behind the Federal "
        "Reserve's inflation objective.",
        _SA,
        Candidate(provider="bea", series="NIPA/T20804/M/1", note=_BEA_NOTE),
        Candidate(provider="fred", series="PCEPI", tier=Tier.AGGREGATOR),
    ),
    _level(
        "us.prices.pce_core",
        "Core PCE price index",
        "The PCE price index excluding food and energy, monthly and seasonally "
        "adjusted: the measure the Federal Reserve watches for underlying "
        "inflation.",
        _SA,
        Candidate(provider="bea", series="NIPA/T20804/M/25", note=_BEA_NOTE),
        Candidate(provider="fred", series="PCEPILFE", tier=Tier.AGGREGATOR),
    ),
    _yoy(
        "us.inflation.pce.yoy",
        "PCE inflation, year over year",
        "The change in the PCE price index over the same month a year earlier, "
        "as a decimal. A month whose year-earlier index is missing is missing.",
        _SA,
        Candidate(
            provider="bea",
            series="NIPA/T20804/M/1",
            transforms=_YOY,
            note=_BEA_NOTE,
        ),
        Candidate(
            provider="fred", series="PCEPI", transforms=_YOY, tier=Tier.AGGREGATOR
        ),
    ),
    _yoy(
        "us.inflation.pce_core.yoy",
        "Core PCE inflation, year over year",
        "The change in the core PCE price index (excluding food and energy) over "
        "the same month a year earlier, as a decimal.",
        _SA,
        Candidate(
            provider="bea",
            series="NIPA/T20804/M/25",
            transforms=_YOY,
            note=_BEA_NOTE,
        ),
        Candidate(
            provider="fred",
            series="PCEPILFE",
            transforms=_YOY,
            tier=Tier.AGGREGATOR,
        ),
    ),
    _level(
        "us.prices.cpi",
        "CPI-U, all items",
        "The consumer price index for all urban consumers, all items, US city "
        "average, monthly and seasonally adjusted.",
        _SA,
        Candidate(provider="bls", series="CUSR0000SA0"),
        Candidate(provider="fred", series="CPIAUCSL", tier=Tier.AGGREGATOR),
    ),
    _level(
        "us.prices.cpi_core",
        "CPI-U, all items less food and energy",
        "The consumer price index for all urban consumers excluding food and "
        "energy, US city average, monthly and seasonally adjusted.",
        _SA,
        Candidate(provider="bls", series="CUSR0000SA0L1E"),
        Candidate(provider="fred", series="CPILFESL", tier=Tier.AGGREGATOR),
    ),
    _yoy(
        "us.inflation.cpi.yoy",
        "CPI inflation, year over year",
        "The change in the not-seasonally-adjusted CPI-U for all items over the "
        "same month a year earlier, as a decimal: the twelve-month change the "
        "Bureau of Labor Statistics reports.",
        _NSA,
        Candidate(provider="bls", series="CUUR0000SA0", transforms=_YOY),
        Candidate(
            provider="fred",
            series="CPIAUCNS",
            transforms=_YOY,
            tier=Tier.AGGREGATOR,
        ),
    ),
    _yoy(
        "us.inflation.cpi_core.yoy",
        "Core CPI inflation, year over year",
        "The change in the not-seasonally-adjusted CPI-U excluding food and "
        "energy over the same month a year earlier, as a decimal.",
        _NSA,
        Candidate(provider="bls", series="CUUR0000SA0L1E", transforms=_YOY),
        Candidate(
            provider="fred",
            series="CPILFENS",
            transforms=_YOY,
            tier=Tier.AGGREGATOR,
        ),
    ),
    Concept(
        id="us.inflation.pce_trimmed_mean.yoy",
        title="Trimmed-mean PCE inflation, 12 months",
        definition=(
            "The Federal Reserve Bank of Dallas's trimmed-mean PCE inflation "
            "rate over twelve months, as a decimal: the PCE price index with "
            "the most extreme price changes dropped before averaging."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.025 is 2.5%)",
        frequency=ObservationFrequency.MONTHLY,
        seasonal_adjustment=_SA,
        candidates=(
            Candidate(
                provider="fred",
                series="PCETRIM12M159SFRBDAL",
                tier=Tier.AGGREGATOR,
                note=(
                    "The Dallas Fed publishes the series itself, but no "
                    "provider here reads it, so only FRED carries it."
                ),
            ),
        ),
        notes=(
            (
                "Library mode only: FRED is library-only and the Dallas Fed has no "
                "provider yet, so hosted mode refuses this concept."
            ),
        ),
        section=_SECTION,
    ),
)
