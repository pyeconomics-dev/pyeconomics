# src/pyeconomics/data/catalog/growth.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Penn World Table series by economy, for growth accounting and the Solow model.

The ids follow the dataset-family grammar ``<family>.<set>.<economy>.<frequency>``:
``pwt.rgdpna.us.annual`` is PWT's real GDP at constant national prices for the
United States. One concept per variable and economy keeps each series' unit and
definition exact.
"""

from __future__ import annotations

from typing import Final

from pyeconomics.core import UnitKind
from pyeconomics.data.catalog.definitions import Candidate, Concept
from pyeconomics.data.types import ObservationFrequency, SeasonalAdjustment

__all__ = ["CONCEPTS", "ECONOMIES", "VARIABLES"]

_SECTION: Final = "Penn World Table"

#: The economies the catalog carries, as (ISO 3166 alpha-2 id, PWT's ISO alpha-3, name).
ECONOMIES: Final = (
    ("us", "USA", "the United States"),
    ("gb", "GBR", "the United Kingdom"),
    ("de", "DEU", "Germany"),
    ("fr", "FRA", "France"),
    ("it", "ITA", "Italy"),
    ("jp", "JPN", "Japan"),
    ("ca", "CAN", "Canada"),
)
#: The variables: (PWT column, title, definition, unit kind, unit text).
VARIABLES: Final = (
    (
        "rgdpna",
        "real GDP",
        "real GDP at constant national prices, in millions of 2021 US dollars",
        UnitKind.MONEY,
        "millions of 2021 US dollars",
    ),
    (
        "rnna",
        "real capital stock",
        "the capital stock at constant national prices, in millions of 2021 US dollars",
        UnitKind.MONEY,
        "millions of 2021 US dollars",
    ),
    (
        "rkna",
        "capital services index",
        "the index of capital services at constant national prices (2021 = 1)",
        UnitKind.INDEX_LEVEL,
        "index, 2021 = 1",
    ),
    (
        "emp",
        "employment",
        "the number of persons engaged, in millions",
        UnitKind.COUNT,
        "millions of persons",
    ),
    (
        "hc",
        "human capital index",
        (
            "the human capital index, built from years of schooling and returns to "
            "education"
        ),
        UnitKind.INDEX_LEVEL,
        "index",
    ),
    (
        "labsh",
        "labour share",
        (
            "the share of labour compensation in GDP at current national prices, as "
            "a decimal"
        ),
        UnitKind.RATE,
        "decimal share (0.6 is 60%)",
    ),
    (
        "rtfpna",
        "total factor productivity",
        "total factor productivity at constant national prices (2021 = 1)",
        UnitKind.INDEX_LEVEL,
        "index, 2021 = 1",
    ),
)


def _concepts() -> tuple[Concept, ...]:
    return tuple(
        Concept(
            id=f"pwt.{column}.{economy}.annual",
            title=f"PWT {title}, {name}",
            definition=(
                f"The Penn World Table's {definition} for {name}, annual, "
                "indexed by the last day of each year."
            ),
            unit_kind=kind,
            unit_text=unit,
            frequency=ObservationFrequency.ANNUAL,
            seasonal_adjustment=SeasonalAdjustment.NOT_APPLICABLE,
            candidates=(
                Candidate(provider="penn_world_table", series=f"{code}:{column}"),
            ),
            notes=(
                (
                    "Penn World Table 11.0, CC BY 4.0; cite Feenstra, Inklaar and "
                    "Timmer as the source requires."
                ),
            ),
            section=_SECTION,
        )
        for column, title, definition, kind, unit in VARIABLES
        for economy, code, name in ECONOMIES
    )


CONCEPTS: Final = _concepts()
