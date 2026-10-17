# src/pyeconomics/data/providers/oecd.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""Organisation for Economic Co-operation and Development: official SDMX series.

Use agency/flow/key ids; search returns dataflows, whose structures define
ordered dimension codes. Source terms checked 2026-10-16. Dataset restrictions
travel with series metadata and are enforced by hosted mode.
"""

from __future__ import annotations

import datetime as dt
from typing import ClassVar

from pyeconomics.core.provenance import LicenceClass, LlmUse
from pyeconomics.data.providers._sdmx import SdmxProvider, cases
from pyeconomics.data.providers.base import (
    Capability,
    Platform,
    ProviderInfo,
    RateLimit,
)
from pyeconomics.data.terms import CachePolicy, Terms

__all__ = ["Oecd"]

TERMS = Terms(
    licence=LicenceClass("hosted-safe"),
    terms_url="https://www.oecd.org/en/about/terms-conditions.html",
    checked=dt.date(2026, 10, 16),
    attribution="Source: OECD.",
    notice="OECD (year), (dataset name),(data source) DOI or URL (accessed on (date)).",
    llm_use=LlmUse("allowed"),
    cache=CachePolicy.ALLOWED,
)


class Oecd(SdmxProvider):
    """Read OECD public statistics with dataset-specific licence gates."""

    info = ProviderInfo(
        id="oecd",
        name=("Organisation for Economic Co-operation and Development"),
        homepage="https://sdmx.oecd.org",
        terms=TERMS,
        hosts=("sdmx.oecd.org",),
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
        extra="sdmx",
        platforms=(Platform.LINUX, Platform.MACOS, Platform.WINDOWS),
        rate_limits=(
            RateLimit(requests=1, per="second"),
            RateLimit(requests=60, per="hour"),
        ),
        max_response_bytes=20_000_000,
    )
    root = "/public/rest/v1"
    search_agency = "all"
    references = "all"
    cases: ClassVar = cases(
        "OECD.SDD.STES/DSD_STES@DF_FINMARK/USA.M.IR3TIB.PA._Z._Z._Z._Z.N",
        "financial",
        start=dt.date(2025, 1, 1),
        end=dt.date(2026, 10, 16),
    )
