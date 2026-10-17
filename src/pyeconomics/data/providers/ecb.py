# src/pyeconomics/data/providers/ecb.py
# Copyright 2026 Nathan Ramos, CFA
# SPDX-License-Identifier: Apache-2.0
"""European Central Bank: structure-aware SDMX series, behind the sdmx extra.

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

__all__ = ["Ecb"]

TERMS = Terms(
    licence=LicenceClass("hosted-safe"),
    terms_url="https://www.ecb.europa.eu/services/using-our-site/disclaimer/html/index.en.html",
    checked=dt.date(2026, 10, 16),
    attribution="Source: European Central Bank.",
    notice="the information may be obtained free of charge through this website.",
    llm_use=LlmUse("allowed"),
    cache=CachePolicy.ALLOWED,
)


class Ecb(SdmxProvider):
    """European Central Bank's official statistical service."""

    info = ProviderInfo(
        id="ecb",
        name="European Central Bank",
        homepage="https://data-api.ecb.europa.eu",
        terms=TERMS,
        hosts=("data-api.ecb.europa.eu",),
        capabilities=(Capability.FETCH, Capability.SEARCH, Capability.DESCRIBE),
        extra="sdmx",
        platforms=(Platform.LINUX, Platform.MACOS, Platform.WINDOWS),
        rate_limits=(RateLimit(requests=1, per="second"),),
        max_response_bytes=20_000_000,
    )
    root = "/service"
    search_agency = "ECB"
    references = "all"
    cases: ClassVar = cases("ECB/EXR/A.USD.EUR.SP00.A", "exchange")
