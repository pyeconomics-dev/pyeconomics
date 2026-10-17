# src/pyeconomics/data/providers/imf.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""International Monetary Fund: structure-aware SDMX series, behind the sdmx extra.

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

__all__ = ["Imf"]

TERMS = Terms(
    licence=LicenceClass("library-only"),
    terms_url="https://www.imf.org/en/about/copyright-and-terms",
    checked=dt.date(2026, 10, 16),
    attribution="Source: International Monetary Fund.",
    notice=(
        "For any potential commercial reuse of IMF Data, email "
        "copyright@imf.org to request permission."
    ),
    llm_use=LlmUse("forbidden"),
    cache=CachePolicy.ALLOWED,
)


class Imf(SdmxProvider):
    """International Monetary Fund's official statistical service."""

    info = ProviderInfo(
        id="imf",
        name="International Monetary Fund",
        homepage="https://api.imf.org",
        terms=TERMS,
        hosts=("api.imf.org",),
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
        extra="sdmx",
        platforms=(Platform.LINUX, Platform.MACOS, Platform.WINDOWS),
        rate_limits=(RateLimit(requests=1, per="second"),),
        max_response_bytes=20_000_000,
    )
    root = "/external/sdmx/2.1"
    search_agency = "all"
    references = "all"
    cases: ClassVar = cases("IMF.STA/CPI/USA.CPI._T.IX.A", "consumer")
