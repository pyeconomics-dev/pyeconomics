# src/pyeconomics/data/catalog/projections.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Forecast concepts: the FOMC's Summary of Economic Projections and the SPF.

The SEP is published meeting by meeting, so its concepts take the meeting date
as a parameter. The Survey of Professional Forecasters is published quarterly
and each survey is a vintage, so a run as of a past date reads the survey that
was out then.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import (
    Candidate,
    Concept,
    Parameter,
    Shape,
)
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS", "SPF_HORIZONS", "SPF_VARIABLES"]

_SECTION: Final = "Projections and surveys"
_MEETING: Final = Parameter(
    name="meeting",
    pattern=r"\d{4}-\d{2}-\d{2}",
    summary="The date of the FOMC meeting whose projections to read.",
    example="2026-09-16",
)

#: The SPF variables, as (concept name, source code, words, seasonal adjustment).
SPF_VARIABLES: Final = (
    ("cpi", "CPI", "CPI inflation", SeasonalAdjustment.NOT_APPLICABLE),
    ("core_cpi", "CORECPI", "core CPI inflation", SeasonalAdjustment.NOT_APPLICABLE),
    ("pce", "PCE", "PCE inflation", SeasonalAdjustment.NOT_APPLICABLE),
    ("core_pce", "COREPCE", "core PCE inflation", SeasonalAdjustment.NOT_APPLICABLE),
    (
        "unemployment",
        "UNEMP",
        "unemployment rate",
        SeasonalAdjustment.SEASONALLY_ADJUSTED,
    ),
)
#: The SPF horizons, as (quarters after the survey quarter, source code).
SPF_HORIZONS: Final = ((0, "2"), (1, "3"), (2, "4"), (3, "5"), (4, "6"))

_SPF_NOTE: Final = (
    "The Philadelphia Fed publishes each survey on a date; the data layer "
    "treats each survey as a vintage, so an as-of run reads the survey out then."
)


def _spf() -> tuple[Concept, ...]:
    concepts: list[Concept] = []
    for name, code, words, seasonal in SPF_VARIABLES:
        inflation = name != "unemployment"
        measure = (
            "annualised quarter-over-quarter rate" if inflation else "quarterly average"
        )
        for ahead, horizon in SPF_HORIZONS:
            when = (
                "the survey quarter"
                if ahead == 0
                else f"{ahead} quarter{'s' if ahead > 1 else ''} after it"
            )
            concepts.append(
                Concept(
                    id=f"us.spf.{name}.median_h{ahead}",
                    title=f"SPF median {words}, {ahead} quarters ahead"
                    if ahead
                    else f"SPF median {words}, survey quarter",
                    definition=(
                        f"The median forecast of {words} ({measure}) in the "
                        f"Survey of Professional Forecasters for {when}, as a "
                        "decimal, indexed by the quarter forecast."
                    ),
                    unit_kind=UnitKind.RATE,
                    unit_text="decimal (0.025 is 2.5%)",
                    frequency=ObservationFrequency.QUARTERLY,
                    seasonal_adjustment=seasonal,
                    candidates=(
                        Candidate(
                            provider="philadelphia_fed",
                            series=f"spf:median:{code}:{horizon}",
                            note=_SPF_NOTE,
                        ),
                    ),
                    section=_SECTION,
                )
            )
    for name, code, words in (
        ("cpi", "CPI10", "ten-year CPI inflation"),
        ("pce", "PCE10", "ten-year PCE inflation"),
    ):
        concepts.append(
            Concept(
                id=f"us.spf.{name}.median_10y",
                title=f"SPF median {words}",
                definition=(
                    f"The median forecast of {words}, average over the next ten "
                    "years, in the Survey of Professional Forecasters, as a "
                    "decimal, indexed by the survey quarter."
                ),
                unit_kind=UnitKind.RATE,
                unit_text="decimal per year (0.023 is 2.3%)",
                frequency=ObservationFrequency.QUARTERLY,
                seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
                candidates=(
                    Candidate(
                        provider="philadelphia_fed",
                        series=f"spf:median:{code}",
                        note=_SPF_NOTE,
                    ),
                ),
                section=_SECTION,
            )
        )
    return tuple(concepts)


CONCEPTS: Final = (
    Concept(
        id="us.sep.medians",
        title="SEP medians",
        definition=(
            "The median projections in one FOMC meeting's Summary of Economic "
            "Projections: real GDP growth, unemployment, PCE and core PCE "
            "inflation and the federal funds rate, for each projection year and "
            "the longer run, as decimals. The table has one row, dated the "
            "meeting."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal (0.025 is 2.5%)",
        frequency=ObservationFrequency.IRREGULAR,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        shape=Shape.TABLE,
        candidates=(
            Candidate(
                provider="fed_board",
                series="sep:{meeting}",
                keep=r"_median_",
                note="Columns are named variable, statistic and horizon.",
            ),
        ),
        parameters=(_MEETING,),
        notes=("Name the meeting; nothing here guesses the latest.",),
        section=_SECTION,
    ),
    Concept(
        id="us.sep.policy_rate_longer_run",
        title="SEP longer-run federal funds rate",
        definition=(
            "The median longer-run federal funds rate in one FOMC meeting's "
            "Summary of Economic Projections, as a decimal: the committee's "
            "view of the neutral nominal rate. One observation, dated the "
            "meeting."
        ),
        unit_kind=UnitKind.RATE,
        unit_text="decimal per year (0.03 is 3%)",
        frequency=ObservationFrequency.IRREGULAR,
        seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
        candidates=(
            Candidate(
                provider="fed_board",
                series="sep:{meeting}",
                column="federal_funds_rate_median_Longer_run",
            ),
        ),
        parameters=(_MEETING,),
        section=_SECTION,
    ),
    *_spf(),
)
